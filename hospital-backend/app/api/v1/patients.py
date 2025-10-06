w"""
Patient management API endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
import logging

from ...models.patient import Patient, PatientCreate, PatientUpdate, PatientWithVitals, VitalSigns
from ...core.database import get_db_connection, get_timescale_connection
from ...core.db_utils import fetch_all, fetch_one, execute_query
from ...services.audit import log_audit_event
from ...utils.transformers import transform_patient_to_camel
from ...services.websocket_manager import connection_manager
from ...utils.edit_window import is_within_edit_window, check_edit_permission

router = APIRouter()
logger = logging.getLogger(__name__)

async def get_patient_current_vitals(patient_id: str) -> dict:
    """Get the most recent vitals for a patient from TimescaleDB"""
    try:
        async with get_timescale_connection() as conn:
            # Get most recent vitals (within last hour to ensure freshness)
            vitals_query = """
            SELECT 
                vitaltype,
                value,
                unit,
                time,
                quality
            FROM vitals_timeseries 
            WHERE patientid = $1 
            AND time >= NOW() - INTERVAL '1 hour'
            ORDER BY time DESC
            """
            
            vitals_rows = await conn.fetch(vitals_query, patient_id)
            
            # Convert to the expected format
            current_vitals = {}
            latest_time = None
            
            for row in vitals_rows:
                vital_type = row['vitaltype']
                if vital_type not in current_vitals:  # Get most recent for each type
                    current_vitals[vital_type] = {
                        'value': float(row['value']),
                        'unit': row['unit'],
                        'timestamp': row['time'],
                        'quality': row['quality']
                    }
                    if latest_time is None or row['time'] > latest_time:
                        latest_time = row['time']
            
            # Format for frontend compatibility
            formatted_vitals = {
                'timestamp': latest_time,
                'heartRate': current_vitals.get('heartRate', {}).get('value'),
                'bloodPressureSystolic': current_vitals.get('bloodPressureSystolic', {}).get('value'),
                'bloodPressureDiastolic': current_vitals.get('bloodPressureDiastolic', {}).get('value'),
                'temperature': current_vitals.get('temperature', {}).get('value'),
                'oxygenSaturation': current_vitals.get('oxygenSaturation', {}).get('value'),
                'respiratoryRate': current_vitals.get('respiratoryRate', {}).get('value'),
                'quality': max([v.get('quality', 0) for v in current_vitals.values()]) if current_vitals else 0
            }
            
            return formatted_vitals
            
    except Exception as e:
        logger.error(f"Error getting current vitals for {patient_id}: {e}")
        return None

async def get_patient_vital_history(patient_id: str, hours: int = 24) -> list:
    """Get vital signs history for a patient from TimescaleDB"""
    try:
        async with get_timescale_connection() as conn:
            # Get vitals history aggregated by time buckets (every 5 minutes)
            history_query = """
            SELECT 
                time_bucket('5 minutes', time) AS bucket,
                vitaltype,
                AVG(value) as avg_value,
                MIN(value) as min_value,
                MAX(value) as max_value,
                AVG(quality) as avg_quality,
                unit
            FROM vitals_timeseries 
            WHERE patientid = $1 
            AND time >= NOW() - INTERVAL '%s hours'
            GROUP BY bucket, vitaltype, unit
            ORDER BY bucket DESC, vitaltype
            """ % hours
            
            history_rows = await conn.fetch(history_query, patient_id)
            
            # Group by time bucket
            history_by_time = {}
            for row in history_rows:
                bucket = row['bucket']
                if bucket not in history_by_time:
                    history_by_time[bucket] = {'timestamp': bucket}
                
                vital_type = row['vitaltype']
                history_by_time[bucket][vital_type] = {
                    'value': float(row['avg_value']),
                    'min': float(row['min_value']),
                    'max': float(row['max_value']),
                    'quality': float(row['avg_quality']),
                    'unit': row['unit']
                }
            
            # Convert to list and format for frontend
            history_list = []
            for timestamp, vitals in sorted(history_by_time.items(), reverse=True):
                formatted_entry = {
                    'timestamp': timestamp,
                    'heartRate': vitals.get('heartRate', {}).get('value'),
                    'bloodPressureSystolic': vitals.get('bloodPressureSystolic', {}).get('value'), 
                    'bloodPressureDiastolic': vitals.get('bloodPressureDiastolic', {}).get('value'),
                    'temperature': vitals.get('temperature', {}).get('value'),
                    'oxygenSaturation': vitals.get('oxygenSaturation', {}).get('value'),
                    'respiratoryRate': vitals.get('respiratoryRate', {}).get('value')
                }
                history_list.append(formatted_entry)
            
            return history_list[:100]  # Limit to 100 most recent entries
            
    except Exception as e:
        logger.error(f"Error getting vital history for {patient_id}: {e}")
        return []

@router.get("/")
async def get_all_patients(
    status: Optional[str] = Query(None, description="Filter by patient status"),
    room_number: Optional[str] = Query(None, description="Filter by room number"),
    limit: int = Query(100, description="Maximum number of patients to return")
):
    """
    Get all patients with optional filtering
    """
    try:
        async with get_db_connection() as conn:
            query = """
                SELECT p.id, p.firstname, p.lastname, p.dateofbirth, p.gender, 
                       p.phonenumber, p.emergencycontactname, p.emergencycontactphone, p.bloodtype, p.allergies,
                       p.medicalhistory, p.admissiondate, p.dischargedate, 
                       p.roomnumber, p.bednumber, p.assigneddeviceid, p.attendingphysician, p.nurseincharge,
                       p.status, p.createdat, p.updatedat, TRIM(COALESCE(s.firstname, '') || ' ' || COALESCE(s.lastname, '')) as attendingphysicianname
                FROM patients p
                LEFT JOIN staff s ON p.attendingphysician = s.id
                WHERE 1=1"""
            params = []
            
            param_count = 0
            if status is not None and status != "":
                param_count += 1
                query += f" AND p.status = ${param_count}"
                params.append(status)
            
            if room_number is not None and room_number != "":
                param_count += 1
                query += f" AND p.roomnumber = ${param_count}"
                params.append(room_number)
            
            param_count += 1
            query += f" ORDER BY p.createdat DESC LIMIT ${param_count}"
            params.append(limit)
            
            rows = await conn.fetch(query, *params) if params else await conn.fetch(query)
            
            patients = []
            for row in rows:
                patient_dict = dict(row) if hasattr(row, 'keys') else row
                # Transform to camelCase for frontend compatibility
                transformed_dict = transform_patient_to_camel(patient_dict)
                patients.append(transformed_dict)
            
            logger.info(f"📋 Retrieved {len(patients)} patients")
            return JSONResponse(content=patients)
            
    except Exception as e:
        logger.error(f"❌ Get patients error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve patients")

@router.get("/{patient_id}")
async def get_patient(patient_id: str):
    """
    Get a specific patient with current vital signs
    """
    try:
        async with get_db_connection() as conn:
            # Get patient details with attending physician name and device status
            patient_query = """
                SELECT p.id, p.firstname, p.lastname, p.dateofbirth, p.gender,
                       p.phonenumber, p.emergencycontactname, p.emergencycontactphone, p.bloodtype, p.allergies,
                       p.medicalhistory, p.admissiondate, p.dischargedate,
                       p.roomnumber, p.bednumber, p.assigneddeviceid, p.attendingphysician, p.nurseincharge,
                       p.status, p.createdat, p.updatedat, TRIM(COALESCE(s.firstname, '') || ' ' || COALESCE(s.lastname, '')) as attendingphysicianname,
                       d.status as devicestatus, d.batterylevel as devicebattery, d.lastseen as devicelastseen
                FROM patients p
                LEFT JOIN staff s ON p.attendingphysician = s.id
                LEFT JOIN devices d ON p.assigneddeviceid = d.id
                WHERE p.id = $1
            """
            patient_row = await conn.fetchrow(patient_query, patient_id)
            
            if not patient_row:
                raise HTTPException(status_code=404, detail="Patient not found")
            
            patient_dict = dict(patient_row) if hasattr(patient_row, 'keys') else patient_row
            
            # Map device status to frontend values
            if patient_dict.get('devicestatus'):
                device_status = patient_dict['devicestatus']
                device_battery = patient_dict.get('devicebattery', 100)
                device_last_seen = patient_dict.get('devicelastseen')
                
                # Determine device status based on backend status, battery, and last seen
                if device_status in ['active', 'connected']:
                    if device_battery and device_battery < 20:
                        patient_dict['devicestatus'] = 'low_battery'
                    elif device_last_seen:
                        from datetime import datetime, timedelta
                        last_seen_dt = device_last_seen if isinstance(device_last_seen, datetime) else datetime.fromisoformat(str(device_last_seen))
                        if datetime.now() - last_seen_dt > timedelta(minutes=5):
                            patient_dict['devicestatus'] = 'disconnected'
                        else:
                            patient_dict['devicestatus'] = 'connected'
                    else:
                        patient_dict['devicestatus'] = 'connected'
                else:
                    patient_dict['devicestatus'] = 'offline'
            else:
                # No device assigned
                patient_dict['devicestatus'] = None
            
            # Get current vital signs from TimescaleDB
            current_vitals_dict = await get_patient_current_vitals(patient_id)
            current_vitals_row = None
            if current_vitals_dict and current_vitals_dict.get('timestamp'):
                # Format as expected by VitalSigns model (camelCase)
                current_vitals_row = {
                    'patientid': patient_id,
                    'deviceId': patient_dict.get('assigneddeviceid', ''),
                    'timestamp': current_vitals_dict['timestamp'],
                    'heartRate': int(current_vitals_dict['heartRate']) if current_vitals_dict['heartRate'] else None,
                    'bloodPressureSystolic': int(current_vitals_dict['bloodPressureSystolic']) if current_vitals_dict['bloodPressureSystolic'] else None,
                    'bloodPressureDiastolic': int(current_vitals_dict['bloodPressureDiastolic']) if current_vitals_dict['bloodPressureDiastolic'] else None,
                    'temperature': current_vitals_dict['temperature'],
                    'oxygenSaturation': int(current_vitals_dict['oxygenSaturation']) if current_vitals_dict['oxygenSaturation'] else None,
                    'respiratoryRate': int(current_vitals_dict['respiratoryRate']) if current_vitals_dict['respiratoryRate'] else None,
                    'glucoseLevel': current_vitals_dict.get('glucoseLevel'),
                    'id': 0
                }
            
            # Get recent vital signs history from TimescaleDB  
            recent_vitals_list = await get_patient_vital_history(patient_id, 24)
            recent_vitals_rows = []
            for i, vital_dict in enumerate(recent_vitals_list):
                if vital_dict.get('timestamp'):
                    row = {
                        'id': i,
                        'patientid': patient_id,
                        'deviceId': patient_dict.get('assigneddeviceid', ''),
                        'timestamp': vital_dict['timestamp'],
                        'heartRate': int(vital_dict['heartRate']) if vital_dict['heartRate'] else None,
                        'bloodPressureSystolic': int(vital_dict['bloodPressureSystolic']) if vital_dict['bloodPressureSystolic'] else None,
                        'bloodPressureDiastolic': int(vital_dict['bloodPressureDiastolic']) if vital_dict['bloodPressureDiastolic'] else None,
                        'temperature': vital_dict['temperature'],
                        'oxygenSaturation': int(vital_dict['oxygenSaturation']) if vital_dict['oxygenSaturation'] else None,
                        'respiratoryRate': int(vital_dict['respiratoryRate']) if vital_dict['respiratoryRate'] else None,
                        'glucoseLevel': vital_dict.get('glucoseLevel')
                    }
                    recent_vitals_rows.append(row)
            
            # Get medications
            medications_query = """
                SELECT m.*, (s.firstname || ' ' || s.lastname) as prescribedbyname
                FROM medications m
                LEFT JOIN staff s ON m.prescribedBy = s.id
                WHERE m.patientid = ? 
                ORDER BY m.createdAt DESC
            """
            medications_rows = await fetch_all(conn, medications_query, (patient_id,))
            
            # Get investigations
            investigations_query = """
                SELECT i.*, (s.firstname || ' ' || s.lastname) as performedbyname
                FROM investigations i
                LEFT JOIN staff s ON i.performedBy = s.id
                WHERE i.patientid = ? 
                ORDER BY i.createdAt DESC
            """
            investigations_rows = await fetch_all(conn, investigations_query, (patient_id,))
            
            # Get therapy
            therapy_query = """
                SELECT t.*, (s.firstname || ' ' || s.lastname) as performedbyname
                FROM therapy t
                LEFT JOIN staff s ON t.performedBy = s.id
                WHERE t.patientid = ? 
                ORDER BY t.createdAt DESC
            """
            therapy_rows = await fetch_all(conn, therapy_query, (patient_id,))
            
            # Get patient notes
            notes_query = """
                SELECT pn.*, (s.firstname || ' ' || s.lastname) as authorname
                FROM patientnotes pn
                LEFT JOIN staff s ON pn."createdBy" = s.id
                WHERE pn.patientid = ?
                ORDER BY pn.timestamp DESC
            """
            notes_rows = await fetch_all(conn, notes_query, (patient_id,))
            
            # Build response
            current_vitals = None
            if current_vitals_row:
                vitals_dict = dict(current_vitals_row) if hasattr(current_vitals_row, 'keys') else current_vitals_row
                current_vitals = VitalSigns(**vitals_dict)
            
            recent_vitals = []
            for row in recent_vitals_rows or []:
                vitals_dict = dict(row) if hasattr(row, 'keys') else row
                recent_vitals.append(VitalSigns(**vitals_dict))
            
            # Process medications
            medications = []
            for row in medications_rows or []:
                med_dict = dict(row) if hasattr(row, 'keys') else row
                medications.append(med_dict)
            
            # Process investigations
            investigations = []
            for row in investigations_rows or []:
                inv_dict = dict(row) if hasattr(row, 'keys') else row
                investigations.append(inv_dict)
            
            # Process therapy
            therapies = []
            for row in therapy_rows or []:
                therapy_dict = dict(row) if hasattr(row, 'keys') else row
                therapies.append(therapy_dict)
            
            # Process notes
            notes = []
            for row in notes_rows or []:
                note_dict = dict(row) if hasattr(row, 'keys') else row
                notes.append(note_dict)
            
            # Build the complete patient data
            complete_patient_data = {
                **patient_dict,
                'currentVitals': current_vitals.dict() if current_vitals else None,
                'recentVitals': [v.dict() for v in recent_vitals],
                'medications': medications,
                'investigations': investigations,
                'therapies': therapies,
                'notes': notes,
                'caseSheet': []  # Frontend fetches case entries separately via /case-entries
            }
            
            # Transform to camelCase for frontend compatibility
            transformed_data = transform_patient_to_camel(complete_patient_data)
            
            return transformed_data
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get patient error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve patient")

@router.post("/", response_model=Patient)
async def create_patient(patient_data: PatientCreate, created_by: str):
    """
    Create a new patient
    """
    try:
        # Generate clean MRN (Medical Record Number): Year + sequential 6-digit number
        year = datetime.now().year
        sequential = str(uuid.uuid4().int)[:6].zfill(6)
        patient_id = f"{year}{sequential}"
        
        async with get_db_connection() as conn:
            query = """
                INSERT INTO patients (
                    id, firstName, lastName, dateOfBirth, gender, phoneNumber,
                    emergencyContactName, emergencyContactPhone, bloodType, allergies,
                    medicalHistory, roomNumber, bedNumber,
                    attendingPhysician, nurseInCharge, admissionDate, createdAt, updatedat
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
            """
            
            now = datetime.now()
            await conn.execute(query,
                patient_id, patient_data.firstName, patient_data.lastName,
                patient_data.dateOfBirth, patient_data.gender, patient_data.phoneNumber,
                patient_data.emergencyContactName, patient_data.emergencyContactPhone,
                patient_data.bloodType, patient_data.allergies, patient_data.medicalHistory,
                patient_data.roomNumber, patient_data.bedNumber,
                patient_data.attendingPhysician, patient_data.nurseInCharge, now, now, now
            )
                        
            # Log audit event
            await log_audit_event(
                user_id=created_by,
                action="PATIENT_CREATED",
                resource_type="PATIENT",
                resource_id=patient_id,
                details=f"Created patient: {patient_data.firstName} {patient_data.lastName}"
            )
            
            # Get the created patient
            created_row = await fetch_one(conn, "SELECT * FROM patients WHERE id = ?", (patient_id,))
            patient_dict = dict(created_row) if hasattr(created_row, 'keys') else created_row
            
            logger.info(f"✅ Created patient: {patient_id} - {patient_data.firstName} {patient_data.lastName}")
            return Patient(**patient_dict)
            
    except Exception as e:
        logger.error(f"❌ Create patient error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create patient")

@router.put("/{patient_id}", response_model=Patient)
async def update_patient(patient_id: str, patient_data: PatientUpdate, updated_by: str):
    """
    Update an existing patient
    """
    try:
        async with get_db_connection() as conn:
            # Check if patient exists
            existing = await conn.fetchrow("SELECT * FROM patients WHERE id = $1", patient_id)
            if not existing:
                raise HTTPException(status_code=404, detail="Patient not found")
            
            # Build update query for non-None fields
            update_fields = []
            params = []
            param_count = 0
            
            for field, value in patient_data.model_dump(exclude_unset=True).items():
                if value is not None:
                    param_count += 1
                    update_fields.append(f"{field} = ${param_count}")
                    params.append(value)
            
            if not update_fields:
                raise HTTPException(status_code=400, detail="No fields to update")
            
            param_count += 1
            update_fields.append(f"updatedat = ${param_count}")
            params.append(datetime.now())
            
            param_count += 1
            params.append(patient_id)
            
            query = f"UPDATE patients SET {', '.join(update_fields)} WHERE id = ${param_count}"
            await conn.execute(query, *params)
                        
            # Log audit event
            await log_audit_event(
                user_id=updated_by,
                action="PATIENT_UPDATED",
                resource_type="PATIENT",
                resource_id=patient_id,
                details=f"Updated patient fields: {list(patient_data.dict(exclude_unset=True).keys())}"
            )
            
            # Get updated patient
            updated_row = await fetch_one(conn, "SELECT * FROM patients WHERE id = ?", (patient_id,))
            patient_dict = dict(updated_row) if hasattr(updated_row, 'keys') else updated_row
            
            logger.info(f"✅ Updated patient: {patient_id}")
            return Patient(**patient_dict)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Update patient error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update patient")

@router.post("/{patient_id}/discharge-request")
async def doctor_request_discharge(patient_id: str, discharge_data: dict):
    """
    Step 1: Doctor requests discharge
    """
    try:
        async with get_db_connection() as conn:
            existing = await conn.fetchrow("SELECT * FROM patients WHERE id = $1 AND status = 'active'", patient_id)
            if not existing:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            # Update patient status to pending discharge
            await conn.execute(
                "UPDATE patients SET status = $1, updatedat = $2 WHERE id = $3",
                'pending_discharge', datetime.now(), patient_id
            )
            
            # Log for admin notification
            await log_audit_event(
                user_id=discharge_data.get('doctorId'),
                action="DISCHARGE_REQUESTED",
                resource_type="PATIENT", 
                resource_id=patient_id,
                details=f"Doctor requested discharge: {discharge_data.get('reason', '')}"
            )
            
            logger.info(f"🏥 Doctor requested discharge for patient: {patient_id}")
            return {"message": "Discharge request sent to admin", "status": "pending_admin_approval"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Doctor discharge request error: {e}")
        raise HTTPException(status_code=500, detail="Failed to request discharge")

@router.post("/{patient_id}/discharge-approve")
async def admin_approve_discharge(patient_id: str, approval_data: dict):
    """
    Step 2: Admin approves discharge
    """
    try:
        async with get_db_connection() as conn:
            existing = await conn.fetchrow("SELECT * FROM patients WHERE id = $1 AND status = 'pending_discharge'", patient_id)
            if not existing:
                raise HTTPException(status_code=404, detail="Patient not pending discharge")
            
            # Update to approved status
            await conn.execute(
                "UPDATE patients SET status = $1, updatedat = $2 WHERE id = $3",
                'discharge_approved', datetime.now(), patient_id
            )
            
            await log_audit_event(
                user_id=approval_data.get('adminId'),
                action="DISCHARGE_APPROVED", 
                resource_type="PATIENT",
                resource_id=patient_id,
                details="Admin approved discharge - ready for nurse completion"
            )
            
            logger.info(f"✅ Admin approved discharge for patient: {patient_id}")
            return {"message": "Discharge approved - nurse can complete", "status": "ready_for_nurse"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Admin discharge approval error: {e}")
        raise HTTPException(status_code=500, detail="Failed to approve discharge")

@router.post("/{patient_id}/discharge-complete")
async def nurse_complete_discharge(patient_id: str, completion_data: dict):
    """
    Step 3: Nurse removes watch and completes discharge with summary
    """
    try:
        async with get_db_connection() as conn:
            existing = await conn.fetchrow("SELECT * FROM patients WHERE id = $1 AND status = 'discharge_approved'", patient_id)
            if not existing:
                raise HTTPException(status_code=404, detail="Patient not approved for discharge")
            
            now = datetime.now()
            
            # Complete discharge
            await conn.execute(
                "UPDATE patients SET status = $1, dischargedate = $2, updatedat = $3 WHERE id = $4",
                'discharged', now, now, patient_id
            )
            
            # Remove watch
            await execute_query(conn,
                "UPDATE deviceassignments SET status = ?, unassignedat = ? WHERE patientid = ? AND status = ?",
                ('inactive', now, patient_id, 'active')
            )
            await execute_query(conn,
                "UPDATE devices SET status = ? WHERE id IN (SELECT deviceid FROM deviceassignments WHERE patientid = ? AND status = 'active')",
                ('available', patient_id)
            )
            
            # Generate discharge summary
            discharge_summary = await generate_discharge_summary(conn, patient_id, completion_data)
            
            await log_audit_event(
                user_id=completion_data.get('nurseId'),
                action="DISCHARGE_COMPLETED",
                resource_type="PATIENT",
                resource_id=patient_id,
                details=f"Nurse completed discharge - watch removed, summary generated"
            )
            
            logger.info(f"🏥 Nurse completed discharge for patient: {patient_id}")
            return {
                "message": "Patient discharged successfully",
                "dischargedate": now.isoformat(),
                "status": "discharged",
                "dischargeSummary": discharge_summary
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Nurse discharge completion error: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete discharge")

async def generate_discharge_summary(conn, patient_id: str, completion_data: dict):
    """
    Generate comprehensive discharge summary for patient
    """
    try:
        # Get patient details
        patient = await fetch_one(conn, "SELECT * FROM patients WHERE id = ?", (patient_id,))
        if not patient:
            return {"error": "Patient not found"}
        
        patient_dict = dict(patient) if hasattr(patient, 'keys') else patient
        
        # Get attending physician name
        physician = await fetch_one(conn, "SELECT name FROM staff WHERE id = ?", (patient_dict.get('attendingphysician'),))
        physician_name = physician['name'] if physician else "Unknown Doctor"
        
        # Get final medications (active at discharge)
        medications = await fetch_all(conn, 
            "SELECT name, dosage, frequency, route FROM medications WHERE patientid = ? AND status = 'active'", 
            (patient_id,))
        
        # Get completed investigations
        investigations = await fetch_all(conn, 
            "SELECT name, results FROM investigations WHERE patientid = ? AND status = 'completed' AND results IS NOT NULL", 
            (patient_id,))
        
        # Get latest clinical notes
        notes = await fetch_all(conn, 
            "SELECT pn.content, s.firstname || ' ' || s.lastname as authorname, pn.timestamp FROM patientnotes pn JOIN staff s ON pn.authorid = s.id WHERE pn.patientid = ? ORDER BY pn.timestamp DESC LIMIT 3", 
            (patient_id,))
        
        # Format discharge summary
        summary = {
            "patientInfo": {
                "name": " ".join(filter(None, [patient_dict.get('firstname', ''), patient_dict.get('lastname', '')])),
                "id": patient_id,
                "dateOfBirth": patient_dict.get('dateofbirth'),
                "gender": patient_dict.get('gender'),
                "bloodType": patient_dict.get('bloodtype')
            },
            "admissionInfo": {
                "admissionDate": patient_dict.get('admissiondate'),
                "dischargedate": patient_dict.get('dischargedate'),
                "attendingPhysician": physician_name,
                "roomNumber": patient_dict.get('roomnumber'),
                "bedNumber": patient_dict.get('bednumber')
            },
            "medicalSummary": {
                "primaryDiagnosis": patient_dict.get('medicalhistory', 'Not specified'),
                "allergies": patient_dict.get('allergies', 'None known')
            },
            "dischargeMedications": [
                {
                    "name": med['name'],
                    "dosage": med['dosage'],
                    "frequency": med['frequency'],
                    "route": med['route'],
                    "instructions": f"Take {med['dosage']} {med['frequency']} by {med['route']}"
                }
                for med in medications
            ],
            "keyInvestigations": [
                {
                    "test": inv['name'],
                    "result": inv['results']
                }
                for inv in investigations
            ],
            "clinicalNotes": [
                {
                    "note": note['content'],
                    "author": note['authorname'],
                    "date": note['timestamp']
                }
                for note in notes
            ],
            "dischargeInstructions": {
                "followUp": completion_data.get('followUpInstructions', 'Follow up with primary care physician in 1-2 weeks'),
                "activityLevel": completion_data.get('activityLevel', 'Resume normal activities as tolerated'),
                "dietInstructions": completion_data.get('dietInstructions', 'Regular diet unless otherwise specified'),
                "returnToHospitalIf": [
                    "Chest pain or difficulty breathing",
                    "Fever over 101.5°F (38.6°C)",
                    "Unusual bleeding or swelling",
                    "Any concerning symptoms"
                ]
            },
            "emergencyContact": {
                "name": patient_dict.get('emergencycontactname'),
                "phone": patient_dict.get('emergencycontactphone')
            },
            "generatedBy": {
                "nurse": completion_data.get('nurseId'),
                "timestamp": datetime.now().isoformat(),
                "hospitalName": "Advanced Medical Center"
            }
        }
        
        logger.info(f"📋 Generated discharge summary for patient: {patient_id}")
        return summary
        
    except Exception as e:
        logger.error(f"❌ Error generating discharge summary: {e}")
        return {"error": "Could not generate discharge summary"}

@router.get("/{patient_id}/discharge-summary")
async def get_discharge_summary(patient_id: str):
    """
    Get discharge summary for a discharged patient
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient is discharged
            patient = await fetch_one(conn, "SELECT * FROM patients WHERE id = ? AND status = 'discharged'", (patient_id,))
            if not patient:
                raise HTTPException(status_code=404, detail="Discharged patient not found")
            
            # Generate summary (can be called anytime for discharged patients)
            discharge_summary = await generate_discharge_summary(conn, patient_id, {})
            
            logger.info(f"📋 Retrieved discharge summary for patient: {patient_id}")
            return {
                "patientid": patient_id,
                "dischargeSummary": discharge_summary,
                "generated": datetime.now().isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get discharge summary error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve discharge summary")

@router.post("/{patient_id}/vitals-test")  # New test endpoint
async def record_vital_signs_test(patient_id: str, vitals_data: dict):
    """Test endpoint for vitals recording"""
    try:
        logger.info(f"🔍 Test endpoint called for patient: {patient_id}")
        logger.info(f"🔍 Raw data received: {vitals_data}")
        
        # Direct database operations (same as working test)
        async with get_db_connection() as conn:
            patient = await conn.fetchrow("SELECT id FROM patients WHERE id = $1 AND status = 'active'", patient_id)
            if not patient:
                raise HTTPException(status_code=404, detail="Active patient not found")
        
        # Insert sample vitals into TimescaleDB
        timestamp = datetime.now()
        device_id = vitals_data.get("deviceId", "TEST_DEVICE")
        
        async with get_timescale_connection() as ts_conn:
            await ts_conn.execute("""
                INSERT INTO vitals_timeseries 
                (time, patientid, deviceid, vitaltype, value, unit, quality)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, 
                timestamp,
                patient_id,
                device_id,
                'heartRate',
                float(vitals_data.get('heartRate', 75)),
                'bpm',
                95
            )
        
        return {"success": True, "message": "Test vitals recorded", "patient_id": patient_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Test vitals error: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Test failed")

@router.get("/{patient_id}/vitals")
async def get_patient_vitals(patient_id: str, hours: int = 24):
    """
    Get vitals data for a patient from TimescaleDB
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists
            patient = await conn.fetchrow("SELECT id FROM patients WHERE id = $1", patient_id)
            if not patient:
                raise HTTPException(status_code=404, detail="Patient not found")
            
        async with get_timescale_connection() as ts_conn:
            # Get vitals from last N hours
            vitals_query = """
                SELECT vitaltype, value, unit, time, quality, deviceid 
                FROM vitals_timeseries 
                WHERE patientid = $1 
                AND time >= NOW() - INTERVAL '%s hours'
                ORDER BY time DESC
                LIMIT 1000
            """ % hours
            
            rows = await ts_conn.fetch(vitals_query, patient_id)
            
            # Group by vital type for latest values and history
            vitals_data = {}
            vitals_history = []
            
            for row in rows:
                vital_type = row['vitaltype']
                vitals_history.append({
                    'type': vital_type,
                    'value': row['value'],
                    'unit': row['unit'],
                    'timestamp': row['time'].isoformat(),
                    'deviceId': row['deviceid'],
                    'quality': row['quality']
                })
                
                # Keep latest value for each vital type
                if vital_type not in vitals_data:
                    vitals_data[vital_type] = {
                        'value': row['value'],
                        'unit': row['unit'],
                        'timestamp': row['time'].isoformat(),
                        'deviceId': row['deviceid']
                    }
            
            logger.info(f"📊 Retrieved {len(vitals_history)} vitals for patient {patient_id}")
            return {
                'patientid': patient_id,
                'currentVitals': vitals_data,
                'history': vitals_history,
                'hoursRequested': hours
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get vitals error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve vitals")

@router.post("/{patient_id}/vitals")  # Fixed endpoint
async def record_vital_signs(patient_id: str, vitals_data: dict):
    """
    Record new vital signs for a patient
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists
            patient = await conn.fetchrow("SELECT id FROM patients WHERE id = $1 AND status = 'active'", patient_id)
            if not patient:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            # Insert vitals into TimescaleDB 
            timestamp_str = vitals_data.get('timestamp')
            if timestamp_str:
                from datetime import datetime
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                timestamp = datetime.now()
                
            device_id = vitals_data.get('deviceId', '')
            
            logger.info(f"📊 Processing vitals for patient {patient_id}, device {device_id}")
            
            async with get_timescale_connection() as ts_conn:
                # Insert all vital signs that the frontend expects - comprehensive monitoring
                vital_mappings = [
                    # Basic vitals
                    ('heartRate', vitals_data.get('heartRate'), 'bpm'),
                    ('bloodPressureSystolic', vitals_data.get('bloodPressureSystolic'), 'mmHg'),
                    ('bloodPressureDiastolic', vitals_data.get('bloodPressureDiastolic'), 'mmHg'),
                    ('bloodPressureValue', vitals_data.get('bloodPressureValue'), 'mmHg'),  # systolic value
                    ('temperature', vitals_data.get('temperature'), '°F'),
                    ('oxygenSat', vitals_data.get('oxygenSat') or vitals_data.get('oxygenSaturation'), '%'),
                    ('respiratoryRate', vitals_data.get('respiratoryRate'), 'breaths/min'),
                    
                    # Advanced monitoring
                    ('ecg', vitals_data.get('ecg'), 'mV'),
                    ('eeg', vitals_data.get('eeg'), 'μV'),
                    ('bioimpedance', vitals_data.get('bioimpedance'), 'Ohms'),
                    ('tremor', vitals_data.get('tremor'), 'intensity_0-10'),
                    
                    # Additional medical vitals
                    ('glucoseLevel', vitals_data.get('glucoseLevel'), 'mg/dL'),
                    ('skinTemperature', vitals_data.get('skinTemperature'), '°F'),
                ]
                
                # Insert each vital sign that has a value
                for vital_type, value, unit in vital_mappings:
                    if value is not None:
                        await ts_conn.execute("""
                            INSERT INTO vitals_timeseries 
                            (time, patientid, deviceid, vitaltype, value, unit, quality)
                            VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """, 
                            timestamp,
                            patient_id,
                            device_id,
                            vital_type,
                            float(value),
                            unit,
                            95  # Default quality indicator (integer)
                        )
                        
            logger.info(f"✅ Recorded vital signs for patient: {patient_id} in TimescaleDB")
            return {"success": True, "message": "Vitals recorded successfully", "patient_id": patient_id}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Record vitals error: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to record vital signs")

@router.put("/{patient_id}/vitals")
async def update_vital_signs(patient_id: str, vitals_data: dict):
    """
    Update/record vital signs for a patient (PUT endpoint for frontend compatibility)
    """
    # Use the same logic as POST endpoint for consistency
    return await record_vital_signs(patient_id, vitals_data)

@router.post("/{patient_id}/medications")
async def add_medication(patient_id: str, medication_data: dict, created_by: str = Query(..., description="ID of the user creating the medication")):
    """Add a new medication for a patient"""
    try:
        async with get_db_connection() as conn:
            # Generate patient-specific ID using correct column name
            count_result = await conn.fetchval('SELECT COUNT(*) FROM medications WHERE patientid = $1', patient_id)
            next_med_number = (count_result or 0) + 1
            medication_id = f"{patient_id}-MED{next_med_number}"
            
            # Insert medication using correct lowercase column names
            await conn.execute("""
                INSERT INTO medications (
                    id, patientid, name, dosage, frequency, route, duration, status, startdate, prescribedby
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
                medication_id,
                patient_id,
                medication_data.get('name', ''),
                medication_data.get('dosage', ''),
                medication_data.get('frequency', ''),
                medication_data.get('route', ''),
                medication_data.get('duration', ''),
                medication_data.get('status', 'active'),
                medication_data.get('startDate') or datetime.now(),
                created_by
            )

            # Auto-schedule medication administrations based on frequency
            await auto_schedule_medication(conn, medication_id, patient_id, medication_data)

            return {"message": "Medication added successfully", "id": medication_id}
            
    except Exception as e:
        logger.error(f"Add medication error: {e}")
        raise HTTPException(status_code=500, detail="Failed to add medication")

@router.post("/{patient_id}/simple-test")
async def simple_test_endpoint(patient_id: str):
    """Ultra simple test endpoint"""
    logger.info(f"🚀 SIMPLE TEST: Called with patient_id={patient_id}")
    return {"success": True, "message": "Simple test worked", "patient_id": patient_id}

@router.post("/{patient_id}/investigations")
async def add_investigation(patient_id: str, investigation_data: dict, created_by: str = Query(..., description="ID of the user creating the investigation")):
    """
    Add a new investigation for a patient
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists
            patient = await conn.fetchrow("SELECT id FROM patients WHERE id = $1 AND status = 'active'", patient_id)
            if not patient:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            # Generate patient-specific investigation ID (PAT20250911005-LAB1, PAT20250911005-LAB2, etc.)
            count_result = await conn.fetchval('SELECT COUNT(*) FROM investigations WHERE patientid = $1', patient_id)
            next_inv_number = (count_result or 0) + 1
            investigation_id = f"{patient_id}-LAB{next_inv_number}"
            
            await conn.execute("""
                INSERT INTO investigations (
                    id, patientid, type, name, scheduledat, priority, status, 
                    performedby
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, 
                investigation_id,
                patient_id, 
                investigation_data.get('type'), 
                investigation_data.get('name'),
                investigation_data.get('scheduledAt') or investigation_data.get('scheduledat'),
                investigation_data.get('priority', 'routine'), 
                'pending',
                created_by
            )
                        
            # Log audit event
            await log_audit_event(
                user_id=created_by,
                action="INVESTIGATION_ADDED",
                resource_type="INVESTIGATION",
                resource_id=patient_id,
                details=f"Added investigation: {investigation_data.get('name')} for patient {patient_id}"
            )
            
            logger.info(f"🧪 Added investigation {investigation_data.get('name')} for patient: {patient_id}")
            return {"message": "Investigation added successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Add investigation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to add investigation")

@router.post("/{patient_id}/therapies")
async def add_therapy(patient_id: str, therapy_data: dict, created_by: str = Query(..., description="ID of the user creating the therapy")):
    """
    Add a new therapy session for a patient
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists
            patient = await conn.fetchrow("SELECT id FROM patients WHERE id = $1 AND status = 'active'", patient_id)
            if not patient:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            # Generate patient-specific therapy ID (PAT20250911005-THER1, PAT20250911005-THER2, etc.)
            count_result = await conn.fetchval('SELECT COUNT(*) FROM therapy WHERE patientid = $1', patient_id)
            next_therapy_number = (count_result or 0) + 1
            therapy_id = f"{patient_id}-THER{next_therapy_number}"
            
            await conn.execute("""
                INSERT INTO therapy (
                    id, patientid, type, description, frequency, duration, status,
                    startdate, performedby, createdat, updatedat
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
            """, 
                therapy_id, patient_id, therapy_data.get('type'), therapy_data.get('description'),
                therapy_data.get('frequency'), therapy_data.get('duration'), 'active',
                therapy_data.get('startDate'), created_by
            )
                        
            # Log audit event
            await log_audit_event(
                user_id=created_by,
                action="THERAPY_ADDED",
                resource_type="THERAPY",
                resource_id=patient_id,
                details=f"Added therapy: {therapy_data.get('type')} for patient {patient_id}"
            )
            
            logger.info(f"🏃 Added therapy {therapy_data.get('type')} for patient: {patient_id}")
            return {"message": "Therapy added successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Add therapy error: {e}")
        raise HTTPException(status_code=500, detail="Failed to add therapy")

@router.post("/{patient_id}/notes")
async def add_note(patient_id: str, note_data: dict, created_by: str = Query(..., description="ID of the user creating the note")):
    """
    Add a new note for a patient
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists
            patient = await conn.fetchrow("SELECT id FROM patients WHERE id = $1 AND status = 'active'", patient_id)
            if not patient:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            # Validate required fields
            content = note_data.get('content')
            if not content or not content.strip():
                raise HTTPException(status_code=400, detail="Note content is required")
            
            # Generate patient-specific note ID (PAT20250911005-NOTE1, PAT20250911005-NOTE2, etc.)
            count_result = await conn.fetchval('SELECT COUNT(*) FROM patientnotes WHERE patientid = $1', patient_id)
            next_note_number = (count_result or 0) + 1
            patient_note_id = f"{patient_id}-NOTE{next_note_number}"
            
            # Insert the note with custom patient-specific ID
            await conn.execute("""
                INSERT INTO patientnotes (
                    id, patientid, content, authorid
                ) VALUES ($1, $2, $3, $4)
            """,
                patient_note_id, patient_id, content.strip(), created_by
            )

            logger.info(f"✅ Note added successfully: {patient_note_id}")
            return {"message": "Note added successfully", "noteId": patient_note_id}
            
            logger.info(f"🔍 DEBUG - Created note with patient-specific ID: {patient_note_id} for patient: {patient_id}")
            logger.info(f"🔍 DEBUG - Note creation query result: {created_note}")
            logger.info(f"🔍 DEBUG - Patient ID type: {type(patient_id)}, value: {patient_id}")
            
            # ALWAYS return note data if we have it
            if created_note:
                try:
                    # Handle different row types (dict, Row, NamedTuple)
                    if hasattr(created_note, 'keys'):
                        note_dict = dict(created_note)
                    elif hasattr(created_note, '_asdict'):
                        note_dict = created_note._asdict()
                    elif isinstance(created_note, (list, tuple)):
                        # Handle tuple/list format - note: authorName/authorRole now added by repository
                        keys = ['id', 'patientid', 'content', 'createdBy', 'timestamp', 'editedAt', 'isEdited']
                        note_dict = dict(zip(keys, created_note))
                    else:
                        note_dict = dict(created_note)
                    
                    logger.info(f"📝 Successfully created note {note_dict.get('id')} for patient: {patient_id}")
                    logger.info(f"🔍 DEBUG - Returning note dict keys: {list(note_dict.keys())}")
                    return {
                        "message": "Note added successfully",
                        "note": note_dict
                    }
                except Exception as e:
                    logger.error(f"❌ Error converting note to dict: {e}")
                    logger.error(f"❌ Note object type: {type(created_note)}")
                    logger.error(f"❌ Note object: {created_note}")
                    # Even if conversion fails, try to return basic data
                    return {
                        "message": "Note added successfully", 
                        "note": {
                            "id": patient_note_id,
                            "patientid": patient_id,
                            "createdBy": created_by,
                            "content": note_data.get('content'),
                            "timestamp": now.isoformat(),
                            "canEdit": True  # Since it's just created
                        }
                    }
            else:
                logger.error(f"❌ CRITICAL: Note was inserted but not found in any query for patient: {patient_id}")
                # Return a minimal note object so frontend doesn't break
                return {
                    "message": "Note added successfully",
                    "note": {
                        "id": patient_note_id,
                        "patientid": patient_id,
                        "createdBy": created_by,
                        "content": note_data.get('content'),
                        "timestamp": now.isoformat(),
                        "canEdit": True
                    }
                }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Add note error: {e}")
        raise HTTPException(status_code=500, detail="Failed to add note")

@router.post("/{patient_id}/case-entries")
async def add_case_entry(patient_id: str, case_data: dict):
    """
    Add a new case sheet entry for a patient
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists
            patient = await fetch_one(conn, "SELECT id FROM patients WHERE id = ? AND status = 'active'", (patient_id,))
            if not patient:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            query = """
                INSERT INTO caseSheetEntries (
                    patientid, entryType, description, performedBy, timestamp
                ) VALUES (?, ?, ?, ?, ?)
            """
            
            now = datetime.now()
            await execute_query(conn, query, (
                patient_id, case_data.get('entryType'), case_data.get('description'),
                case_data.get('performedBy'), now
            ))
            
            logger.info(f"📋 Added case entry ({case_data.get('entryType')}) for patient: {patient_id}")
            return {"message": "Case entry added successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Add case entry error: {e}")
        raise HTTPException(status_code=500, detail="Failed to add case entry")

@router.get("/{patient_id}/case-entries")
async def get_case_entries(patient_id: str):
    """
    Get comprehensive case sheet with complete clinical history timeline
    Includes: medications, investigations, therapies, vital alerts, device changes, 
    admissions, discharges, notes, and all clinical activities
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists
            patient = await conn.fetchrow("SELECT id FROM patients WHERE id = $1", patient_id)
            if not patient:
                raise HTTPException(status_code=404, detail="Patient not found")
            
            all_entries = []
            
            # 1. Case sheet entries (manual entries only, exclude duplicates)
            # Exclude entries that duplicate medications, investigations, therapies, and notes
            case_entries_query = """
                SELECT
                    c."entryType" as entry_type,
                    c.timestamp as event_time,
                    c."entryType" as sub_type,
                    c.description,
                    COALESCE(c."createdBy", 'Unknown') as performedBy,
                    c."createdBy" as performedBy_id,
                    c."createdAt",
                    c.id::text as record_id
                FROM "caseEntries" c
                WHERE c."patientId" = $1 AND c."deletedAt" IS NULL
            """
            case_entries = await conn.fetch(case_entries_query, patient_id)
            for entry in case_entries:
                all_entries.append(dict(entry))
            
            # 2. Medication administrations only (prescriptions are in dedicated Medications tab)
            # Only include actual administration events, not routine prescriptions
            medications_query = """
                SELECT
                    'medication_administration' as entry_type,
                    COALESCE(ma."performedAt", ma.scheduledtime) as event_time,
                    ma.status as sub_type,
                    (m.name || ' - ' || COALESCE(ma.dosagegiven, m.dosage) ||
                     CASE WHEN ma.notes IS NOT NULL THEN ' (' || ma.notes || ')' ELSE '' END) as description,
                    COALESCE(ma."performedBy", 'System') as performedBy,
                    ma."performedBy" as performedBy_id,
                    ma.createdat,
                    ma.id::text as record_id
                FROM medicationadministrations ma
                JOIN medications m ON ma.medicationid::text = m.id::text
                WHERE ma.patientid = $1
                AND (ma.notes IS NULL OR ma.notes NOT ILIKE '%Auto-scheduled%')
            """
            med_entries = await conn.fetch(medications_query, patient_id)
            for entry in med_entries:
                all_entries.append(dict(entry))
            
            # 3. Investigation results only (routine orders are in dedicated Investigations tab)
            # Only include completed investigations with results or critical status changes
            investigations_query = """
                SELECT
                    'investigation' as entry_type,
                    COALESCE(i.completedat, i.scheduledat, i.createdat) as event_time,
                    i.status as sub_type,
                    (i.name ||
                     CASE WHEN i.results IS NOT NULL THEN ' - ' || i.results
                          WHEN i.status = 'cancelled' THEN ' - Cancelled'
                          WHEN i.status = 'critical' THEN ' - Critical'
                          ELSE ' - ' || i.status END) as description,
                    COALESCE(i.performedby, 'System') as performedBy,
                    i.performedby as performedBy_id,
                    i.createdat,
                    i.id::text as record_id
                FROM investigations i
                WHERE i.patientid = $1
            """
            inv_entries = await conn.fetch(investigations_query, patient_id)
            for entry in inv_entries:
                all_entries.append(dict(entry))
            
            # 4. Therapy sessions only (routine prescriptions are in dedicated Therapy tab)
            # Only include actual therapy sessions and significant therapy events
            therapies_query = """
                SELECT
                    'therapy_session' as entry_type,
                    COALESCE(ts.completedat, ts.scheduleddate) as event_time,
                    ts.status as sub_type,
                    (th.type || ' session #' || ts.sessionnumber ||
                     CASE WHEN ts.sessionnotes IS NOT NULL THEN ' (' || ts.sessionnotes || ')' ELSE '' END) as description,
                    COALESCE(ts.performedby, 'System') as performedBy,
                    ts.performedby as performedBy_id,
                    ts.createdat,
                    ts.id::text as record_id
                FROM therapysessions ts
                JOIN therapy th ON ts.therapyid::text = th.id::text
                WHERE ts.patientid = $1
            """
            therapy_entries = await conn.fetch(therapies_query, patient_id)
            for entry in therapy_entries:
                all_entries.append(dict(entry))
            
            # 5. Patient notes
            notes_query = """
                SELECT
                    'note' as entry_type,
                    pn.timestamp as event_time,
                    CASE WHEN pn.isedited THEN 'edited' ELSE 'added' END as sub_type,
                    (CASE WHEN LENGTH(pn.content) > 100 THEN LEFT(pn.content, 100) || '...'
                          ELSE pn.content END) as description,
                    COALESCE(s.firstname || ' ' || s.lastname, pn.authorid) as performedBy,
                    pn.authorid as performedBy_id,
                    pn.timestamp as createdat,
                    pn.id::text as record_id
                FROM patientnotes pn
                LEFT JOIN staff s ON pn.authorid = s.id
                WHERE pn.patientid = $1
            """
            notes_entries = await conn.fetch(notes_query, patient_id)
            for entry in notes_entries:
                all_entries.append(dict(entry))
            
            # 6. Device assignments and changes
            device_query = """
                SELECT 
                    'device' as entry_type,
                    da.assignedat as event_time,
                    CASE WHEN da.unassignedat IS NOT NULL THEN 'unassigned' ELSE 'assigned' END as sub_type,
                    (CASE WHEN da.unassignedat IS NOT NULL
                          THEN 'Unassigned ' || d.devicetype || ' (' || d.serialnumber || ')'
                          ELSE 'Assigned ' || d.devicetype || ' (' || d.serialnumber || ')' END ||
                     CASE WHEN da.notes IS NOT NULL THEN ' - ' || da.notes ELSE '' END) as description,
                    (s.firstname || ' ' || s.lastname) as performedBy,
                    da.assignedby as performedBy_id,
                    da.assignedat as createdat,
                    da.id::text as record_id
                FROM deviceassignments da
                JOIN devices d ON da.deviceid = d.id
                LEFT JOIN staff s ON da.assignedby = s.id
                WHERE da.patientid = $1
            """
            device_entries = await conn.fetch(device_query, patient_id)
            for entry in device_entries:
                all_entries.append(dict(entry))
            
            # 7. Admission and discharge events
            admission_query = """
                SELECT 
                    'admission' as entry_type,
                    p.createdat as event_time,
                    'admitted' as sub_type,
                    ('Admitted to ' || COALESCE(p.roomnumber, 'unassigned room') ||
                     CASE WHEN p.bednumber IS NOT NULL THEN ' - Bed ' || p.bednumber ELSE '' END ||
                     CASE WHEN p.attendingphysician IS NOT NULL THEN ' - ' || p.attendingphysician ELSE '' END) as description,
                    COALESCE(p.nurseincharge, 'System') as performedBy,
                    NULL as performedBy_id,
                    p.createdat,
                    p.id as record_id
                FROM patients p
                WHERE p.id = $1
                
                UNION ALL
                
                SELECT 
                    'discharge' as entry_type,
                    p.dischargedate as event_time,
                    'discharged' as sub_type,
                    'Patient discharged' as description,
                    'System' as performedBy,
                    NULL as performedBy_id,
                    p.dischargedate as createdat,
                    p.id as record_id
                FROM patients p
                WHERE p.id = $1 AND p.dischargedate IS NOT NULL
            """
            admission_entries = await conn.fetch(admission_query, patient_id)
            for entry in admission_entries:
                all_entries.append(dict(entry))
            
            # Audit entries are excluded from case sheet timeline - they're for compliance tracking only
            
            # Sort all entries by event time (most recent first)
            all_entries.sort(key=lambda x: x['event_time'] if x['event_time'] else x['createdat'], reverse=True)
            
            # Format entries for consistent display
            formatted_entries = []
            for entry in all_entries:
                formatted_entry = {
                    'id': entry.get('record_id'),
                    'entryType': entry['entry_type'],
                    'subType': entry.get('sub_type'),
                    'description': entry['description'],
                    'performedBy': entry.get('performedBy', 'System'),
                    'performedById': entry.get('performedBy_id'),
                    'timestamp': entry['event_time'] if entry['event_time'] else entry['createdat'],
                    'createdAt': entry['createdat']
                }
                formatted_entries.append(formatted_entry)
            
            logger.info(f"📋 Retrieved {len(formatted_entries)} case entries (complete history) for patient: {patient_id}")
            return formatted_entries
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get case entries error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve case entries")

@router.get("/{patient_id}/medications")
async def get_medications(patient_id: str):
    """
    Get all medications for a patient with administration history
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists
            patient = await conn.fetchrow("SELECT id FROM patients WHERE id = $1", patient_id)
            if not patient:
                raise HTTPException(status_code=404, detail="Patient not found")
            
            # Get medications with prescriber info
            medications_query = """
                SELECT m.*, (s.firstname || ' ' || s.lastname) as prescribedbyname
                FROM medications m
                LEFT JOIN staff s ON m.prescribedby = s.id
                WHERE m.patientid = $1 
                ORDER BY m.createdat DESC
            """
            
            med_rows = await conn.fetch(medications_query, patient_id)
            medications = []
            
            for med_row in med_rows:
                med_dict = dict(med_row)
                
                # Get administration history for this medication
                administrations_query = """
                    SELECT
                        ma.id,
                        ma.scheduledtime,
                        ma."performedAt",
                        ma.status,
                        ma.dosagegiven,
                        ma.route,
                        ma."performedBy",
                        ma.notes,
                        (s.firstname || ' ' || s.lastname) as "performedByName"
                    FROM medicationadministrations ma
                    LEFT JOIN staff s ON ma."performedBy" = s.id
                    WHERE ma.medicationid::text = $1::text AND ma.patientid = $2
                    ORDER BY ma.scheduledtime DESC
                """
                
                admin_rows = await conn.fetch(administrations_query, str(med_dict['id']), patient_id)
                administrations = [dict(admin_row) for admin_row in admin_rows]
                
                # Calculate administration stats
                total_scheduled = len([a for a in administrations if a['status'] in ['scheduled', 'due', 'administered', 'skipped']])
                total_administered = len([a for a in administrations if a['status'] == 'administered'])
                total_overdue = len([a for a in administrations if a['status'] == 'overdue'])
                total_skipped = len([a for a in administrations if a['status'] == 'skipped'])
                
                # Get next due administration
                next_due = None
                for admin in administrations:
                    if admin['status'] in ['scheduled', 'due'] and admin['scheduledtime']:
                        if not next_due or admin['scheduledtime'] < next_due['scheduledtime']:
                            next_due = admin
                
                # Add administration data to medication
                med_dict.update({
                    'administrations': administrations,
                    'administrationStats': {
                        'totalScheduled': total_scheduled,
                        'totalAdministered': total_administered,
                        'totalOverdue': total_overdue,
                        'totalSkipped': total_skipped,
                        'adherenceRate': round((total_administered / total_scheduled * 100) if total_scheduled > 0 else 0, 1)
                    },
                    'nextDue': next_due
                })
                
                medications.append(med_dict)
            
            logger.info(f"💊 Retrieved {len(medications)} medications with administration history for patient: {patient_id}")
            return medications
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get medications error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve medications")

@router.get("/{patient_id}/investigations")
async def get_investigations(patient_id: str):
    """
    Get all investigations for a patient
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists
            patient = await fetch_one(conn, "SELECT id FROM patients WHERE id = ? AND status = 'active'", (patient_id,))
            if not patient:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            query = """
                SELECT * FROM investigations 
                WHERE patientid = ? 
                ORDER BY createdAt DESC
            """
            
            rows = await fetch_all(conn, query, (patient_id,))
            investigations = []
            for row in rows:
                inv_dict = dict(row) if hasattr(row, 'keys') else row
                investigations.append(inv_dict)
            
            logger.info(f"🧪 Retrieved {len(investigations)} investigations for patient: {patient_id}")
            return investigations
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get investigations error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve investigations")

@router.get("/{patient_id}/therapies")
async def get_therapies(patient_id: str):
    """
    Get all therapies for a patient
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists
            patient = await fetch_one(conn, "SELECT id FROM patients WHERE id = ? AND status = 'active'", (patient_id,))
            if not patient:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            query = """
                SELECT * FROM therapy 
                WHERE patientid = ? 
                ORDER BY createdAt DESC
            """
            
            rows = await fetch_all(conn, query, (patient_id,))
            therapies = []
            for row in rows:
                therapy_dict = dict(row) if hasattr(row, 'keys') else row
                therapies.append(therapy_dict)
            
            logger.info(f"🏃 Retrieved {len(therapies)} therapies for patient: {patient_id}")
            return therapies
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get therapies error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve therapies")

@router.get("/{patient_id}/notes")
async def get_notes(patient_id: str):
    """
    Get all notes for a patient
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists
            patient = await conn.fetchrow("SELECT id FROM patients WHERE id = $1 AND status = 'active'", patient_id)
            if not patient:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            rows = await conn.fetch("""
                SELECT pn.*, (s.firstname || ' ' || s.lastname) as authorname 
                FROM patientnotes pn
                LEFT JOIN staff s ON pn.authorid = s.id
                WHERE pn.patientid = $1 
                ORDER BY pn.timestamp DESC
            """, patient_id)
            notes = []
            for row in rows:
                note_dict = dict(row) if hasattr(row, 'keys') else row
                notes.append(note_dict)
            
            logger.info(f"📝 Retrieved {len(notes)} notes for patient: {patient_id}")
            return notes
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get notes error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve notes")

@router.put("/{patient_id}/medications/{medication_id}")
async def update_medication(patient_id: str, medication_id: str, medication_data: dict):
    """
    Update a specific medication for a patient
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists
            patient = await fetch_one(conn, "SELECT id FROM patients WHERE id = ? AND status = 'active'", (patient_id,))
            if not patient:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            # Build update query dynamically based on provided fields
            update_fields = []
            values = []
            
            for field in ['name', 'dosage', 'frequency', 'route', 'status', 'startDate', 'endDate']:
                if field in medication_data:
                    update_fields.append(f"{field} = ?")
                    values.append(medication_data[field])
            
            if not update_fields:
                raise HTTPException(status_code=400, detail="No fields to update")
            
            update_fields.append("updatedat = ?")
            values.append(datetime.now())
            # Handle both integer IDs (legacy) and patient-specific IDs (PAT-xxx-MEDx)
            values.append(medication_id)
            
            query = f"""
                UPDATE medications 
                SET {', '.join(update_fields)}
                WHERE id = ? AND patientid = ?
            """
            values.append(patient_id)
            
            result = await execute_query(conn, query, tuple(values))
            
            # Send real-time medication update to WebSocket subscribers
            try:
                await connection_manager.send_medication_update(patient_id, {
                    'medication_id': medication_id,
                    'action': 'updated',
                    'updates': medication_data,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as ws_error:
                logger.warning(f"⚠️ WebSocket notification failed for medication update: {ws_error}")
            
            logger.info(f"💊 Updated medication {medication_id} for patient: {patient_id}")
            return {"message": "Medication updated successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Update medication error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update medication")

@router.delete("/{patient_id}/medications/{medication_id}")
async def delete_medication(patient_id: str, medication_id: str):
    """
    Delete a specific medication for a patient
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists
            patient = await fetch_one(conn, "SELECT id FROM patients WHERE id = ? AND status = 'active'", (patient_id,))
            if not patient:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            query = "DELETE FROM medications WHERE id = ? AND patientid = ?"
            # Handle both integer IDs (from database) and string IDs (frontend-generated)
            try:
                await execute_query(conn, query, (int(medication_id), patient_id))
            except ValueError:
                # If it's a frontend-generated ID, we can't delete it since it doesn't exist in DB
                raise HTTPException(status_code=404, detail="Medication not found - frontend-generated ID cannot be deleted")
            
            logger.info(f"💊 Deleted medication {medication_id} for patient: {patient_id}")
            return {"message": "Medication deleted successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Delete medication error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete medication")

@router.post("/{patient_id}/medications/{medication_id}/administer")
async def administer_medication(patient_id: str, medication_id: str, admin_data: dict):
    """
    Record medication administration for a patient
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists
            patient = await conn.fetchrow("SELECT id FROM patients WHERE id = $1 AND status = 'active'", patient_id)
            if not patient:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            # Verify medication exists and is active - handle both integer and patient-specific IDs
            medication = await conn.fetchrow(
                "SELECT * FROM medications WHERE id = $1 AND patientid = $2 AND status = 'active'", 
                medication_id, patient_id)
            if not medication:
                raise HTTPException(status_code=404, detail="Active medication not found")
            
            # Update medication's updatedat timestamp to record administration
            now = datetime.now()
            await conn.execute(
                "UPDATE medications SET updatedat = $1 WHERE id = $2 AND patientid = $3",
                now, medication_id, patient_id)
            
            # Log audit event
            await log_audit_event(
                user_id=admin_data.get('userId', 'system'),
                action="MEDICATION_ADMINISTERED", 
                resource_type="MEDICATION",
                resource_id=patient_id,
                details=f"Administered medication {medication['name']} to patient {patient_id}"
            )
            
            logger.info(f"💊 Recorded administration of medication {medication_id} for patient: {patient_id}")
            return {"message": "Medication administration recorded successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Record medication administration error: {e}")
        raise HTTPException(status_code=500, detail="Failed to record medication administration")

@router.put("/{patient_id}/investigations/{investigation_id}")
async def update_investigation(patient_id: str, investigation_id: str, investigation_data: dict):
    """
    Update a specific investigation for a patient
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists
            patient = await fetch_one(conn, "SELECT id FROM patients WHERE id = ? AND status = 'active'", (patient_id,))
            if not patient:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            # Build update query dynamically based on provided fields
            update_fields = []
            values = []
            
            for field in ['type', 'name', 'scheduledAt', 'completedAt', 'priority', 'status', 'performedBy', 'results', 'notes']:
                if field in investigation_data:
                    update_fields.append(f"{field} = ?")
                    values.append(investigation_data[field])
            
            if not update_fields:
                raise HTTPException(status_code=400, detail="No fields to update")
            
            update_fields.append("updatedat = ?")
            values.append(datetime.now())
            # Handle both integer IDs (legacy) and patient-specific IDs (PAT-xxx-LABx)
            values.append(investigation_id)
            
            query = f"""
                UPDATE investigations 
                SET {', '.join(update_fields)}
                WHERE id = ? AND patientid = ?
            """
            values.append(patient_id)
            
            await execute_query(conn, query, tuple(values))
            
            logger.info(f"🧪 Updated investigation {investigation_id} for patient: {patient_id}")
            return {"message": "Investigation updated successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Update investigation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update investigation")

@router.delete("/{patient_id}/investigations/{investigation_id}")
async def delete_investigation(patient_id: str, investigation_id: str):
    """
    Delete a specific investigation for a patient
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists
            patient = await fetch_one(conn, "SELECT id FROM patients WHERE id = ? AND status = 'active'", (patient_id,))
            if not patient:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            query = "DELETE FROM investigations WHERE id = ? AND patientid = ?"
            try:
                await execute_query(conn, query, (int(investigation_id), patient_id))
            except ValueError:
                raise HTTPException(status_code=404, detail="Investigation not found - frontend-generated ID cannot be deleted")
            
            logger.info(f"🧪 Deleted investigation {investigation_id} for patient: {patient_id}")
            return {"message": "Investigation deleted successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Delete investigation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete investigation")

@router.put("/{patient_id}/therapies/{therapy_id}")
async def update_therapy(patient_id: str, therapy_id: str, therapy_data: dict):
    """
    Update a specific therapy for a patient
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists
            patient = await fetch_one(conn, "SELECT id FROM patients WHERE id = ? AND status = 'active'", (patient_id,))
            if not patient:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            # Build update query dynamically based on provided fields
            update_fields = []
            values = []
            
            for field in ['type', 'description', 'startDate', 'endDate', 'frequency', 'duration', 'status', 'performedBy', 'notes']:
                if field in therapy_data:
                    update_fields.append(f"{field} = ?")
                    values.append(therapy_data[field])
            
            if not update_fields:
                raise HTTPException(status_code=400, detail="No fields to update")
            
            update_fields.append("updatedat = ?")
            values.append(datetime.now())
            # Handle both integer IDs (legacy) and patient-specific IDs (PAT-xxx-THERx)
            values.append(therapy_id)
            
            query = f"""
                UPDATE therapy 
                SET {', '.join(update_fields)}
                WHERE id = ? AND patientid = ?
            """
            values.append(patient_id)
            
            await execute_query(conn, query, tuple(values))
            
            logger.info(f"🏃 Updated therapy {therapy_id} for patient: {patient_id}")
            return {"message": "Therapy updated successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Update therapy error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update therapy")

@router.delete("/{patient_id}/therapies/{therapy_id}")
async def delete_therapy(patient_id: str, therapy_id: str):
    """
    Delete a specific therapy for a patient
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists
            patient = await fetch_one(conn, "SELECT id FROM patients WHERE id = ? AND status = 'active'", (patient_id,))
            if not patient:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            query = "DELETE FROM therapy WHERE id = ? AND patientid = ?"
            try:
                await execute_query(conn, query, (int(therapy_id), patient_id))
            except ValueError:
                raise HTTPException(status_code=404, detail="Therapy not found - frontend-generated ID cannot be deleted")
            
            logger.info(f"🏃 Deleted therapy {therapy_id} for patient: {patient_id}")
            return {"message": "Therapy deleted successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Delete therapy error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete therapy")

@router.post("/{patient_id}/therapies/{therapy_id}/sessions")
async def add_therapy_session(patient_id: str, therapy_id: str, session_data: dict):
    """
    Add a therapy session for a specific therapy
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient and therapy exist
            patient = await fetch_one(conn, "SELECT id FROM patients WHERE id = ? AND status = 'active'", (patient_id,))
            if not patient:
                raise HTTPException(status_code=404, detail="Patient not found")

            therapy = await fetch_one(conn, "SELECT id FROM therapy WHERE id = ? AND patientid = ?", (therapy_id, patient_id))
            if not therapy:
                raise HTTPException(status_code=404, detail="Therapy not found")

            # Generate session ID and get session number
            session_count = await fetch_one(conn, "SELECT COUNT(*) as count FROM therapysessions WHERE therapyid = ?", (therapy_id,))
            session_number = (session_count['count'] if session_count else 0) + 1
            session_id = f"session_{therapy_id}_{session_number}"

            # Insert therapy session
            await execute_query(conn, """
                INSERT INTO therapysessions (
                    id, therapyid, patientid, sessionnumber, completedAt,
                    performedby, sessionnotes, duration, status
                ) VALUES (?, ?, ?, ?, NOW(), ?, ?, ?, 'completed')
            """, (
                session_id, therapy_id, patient_id, session_number,
                session_data.get('therapist', 'Unknown'),
                session_data.get('notes', ''),
                session_data.get('duration', '30 minutes')
            ))

            logger.info(f"✅ Therapy session added: {session_id} for therapy {therapy_id}")

            return {
                "success": True,
                "sessionId": session_id,
                "sessionNumber": session_number,
                "message": "Therapy session added successfully"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Add therapy session error: {e}")
        raise HTTPException(status_code=500, detail="Failed to add therapy session")

@router.put("/{patient_id}/notes/{note_id}")
async def update_note(patient_id: str, note_id: str, note_data: dict):
    """
    Update a specific note for a patient
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists
            patient = await fetch_one(conn, "SELECT id FROM patients WHERE id = ? AND status = 'active'", (patient_id,))
            if not patient:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            # Check if note exists first and get the actual database ID
            # Frontend might send temporary IDs, so we need to find the note by other means
            existing_note = None
            
            # Handle patient-specific IDs (PAT-xxx-NOTEx) and legacy integer IDs
            if note_id.isdigit():
                # Legacy integer database ID
                query_find = "SELECT id FROM patientnotes WHERE id = ? AND patientid = ?"
                try:
                    existing_note = await fetch_one(conn, query_find, (int(note_id), patient_id))
                except ValueError:
                    existing_note = None
            elif note_id.startswith(patient_id) and "-NOTE" in note_id:
                # Patient-specific ID (PAT-xxx-NOTEx)
                query_find = "SELECT id FROM patientnotes WHERE id = ? AND patientid = ?"
                existing_note = await fetch_one(conn, query_find, (note_id, patient_id))
            else:
                # Handle temporary frontend IDs - find most recent note for this patient
                # This is a fallback for optimistic UI updates with temporary IDs
                query_find = """
                    SELECT id FROM patientnotes
                    WHERE patientid = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """
                existing_note = await fetch_one(conn, query_find, (patient_id,))
                if existing_note:
                    logger.info(f"Found most recent note {existing_note['id']} for temp ID {note_id}")
                else:
                    logger.warning(f"Unknown note ID format and no recent notes: {note_id}")
                    raise HTTPException(
                        status_code=404,
                        detail="Note not found - invalid ID format."
                    )
            
            if not existing_note:
                raise HTTPException(status_code=404, detail="Note not found or cannot be updated")
            
            note_db_id = existing_note['id'] if hasattr(existing_note, 'keys') else existing_note[0]
            
            query = """
                UPDATE patientnotes 
                SET content = ?, editedAt = ?, isEdited = true
                WHERE id = ? AND patientid = ?
            """
            
            await execute_query(conn, query, (
                note_data.get('content'), datetime.now(), note_db_id, patient_id
            ))
            
            logger.info(f"📝 Updated note {note_db_id} (original ID: {note_id}) for patient: {patient_id}")
            return {"message": "Note updated successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Update note error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update note")

@router.delete("/{patient_id}/notes/{note_id}")
async def delete_note(patient_id: str, note_id: str):
    """
    Delete a specific note for a patient
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists
            patient = await fetch_one(conn, "SELECT id FROM patients WHERE id = ? AND status = 'active'", (patient_id,))
            if not patient:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            # Handle both database IDs and frontend-generated IDs
            if note_id.isdigit():
                # Standard database ID
                query = "DELETE FROM patientnotes WHERE id = ? AND patientid = ?"
                await execute_query(conn, query, (int(note_id), patient_id))
            else:
                # Frontend-generated ID - can't delete as it doesn't exist in database
                raise HTTPException(status_code=404, detail="Note not found - frontend-generated ID cannot be deleted")
            
            logger.info(f"📝 Deleted note {note_id} for patient: {patient_id}")
            return {"message": "Note deleted successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Delete note error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete note")


async def auto_schedule_medication(conn, medication_id: str, patient_id: str, medication_data: dict):
    """
    Automatically schedule medication administrations based on frequency
    """
    import uuid
    import re

    try:
        frequency = medication_data.get('frequency', '').lower()
        start_date = medication_data.get('startDate') or datetime.now()
        duration_str = medication_data.get('duration', '')

        # Parse frequency to determine doses per day and times
        doses_per_day = 1
        times = ['09:00']  # Default morning dose

        # Parse common frequency patterns
        if 'once daily' in frequency or 'daily' in frequency or frequency == '1':
            doses_per_day = 1
            times = ['09:00']
        elif 'twice daily' in frequency or 'bid' in frequency or frequency == '2':
            doses_per_day = 2
            times = ['09:00', '21:00']  # Morning and evening
        elif 'three times' in frequency or 'tid' in frequency or frequency == '3':
            doses_per_day = 3
            times = ['08:00', '14:00', '20:00']  # Breakfast, lunch, dinner
        elif 'four times' in frequency or 'qid' in frequency or frequency == '4':
            doses_per_day = 4
            times = ['08:00', '12:00', '17:00', '22:00']
        elif 'every 6 hours' in frequency or 'q6h' in frequency:
            doses_per_day = 4
            times = ['06:00', '12:00', '18:00', '00:00']
        elif 'every 8 hours' in frequency or 'q8h' in frequency:
            doses_per_day = 3
            times = ['08:00', '16:00', '00:00']
        elif 'every 12 hours' in frequency or 'q12h' in frequency:
            doses_per_day = 2
            times = ['08:00', '20:00']
        else:
            # Try to extract number
            numbers = re.findall(r'\d+', frequency)
            if numbers:
                doses_per_day = min(int(numbers[0]), 6)  # Cap at 6 doses per day
                if doses_per_day == 1:
                    times = ['09:00']
                elif doses_per_day == 2:
                    times = ['09:00', '21:00']
                elif doses_per_day == 3:
                    times = ['08:00', '14:00', '20:00']
                elif doses_per_day == 4:
                    times = ['08:00', '12:00', '17:00', '22:00']
                elif doses_per_day == 5:
                    times = ['08:00', '11:00', '14:00', '17:00', '21:00']
                elif doses_per_day >= 6:
                    times = ['08:00', '10:00', '12:00', '15:00', '18:00', '21:00']

        # Parse duration to determine how many days to schedule
        duration_days = 7  # Default 1 week
        if duration_str:
            duration_lower = duration_str.lower()
            if 'day' in duration_lower:
                days_match = re.search(r'(\d+)', duration_lower)
                if days_match:
                    duration_days = int(days_match.group(1))
            elif 'week' in duration_lower:
                weeks_match = re.search(r'(\d+)', duration_lower)
                if weeks_match:
                    duration_days = int(weeks_match.group(1)) * 7
            elif 'month' in duration_lower:
                months_match = re.search(r'(\d+)', duration_lower)
                if months_match:
                    duration_days = int(months_match.group(1)) * 30

        # Cap duration to reasonable limits
        duration_days = min(duration_days, 90)  # Max 3 months

        logger.info(f"📅 Scheduling {medication_id}: {doses_per_day} doses/day for {duration_days} days")

        # Create scheduled administrations
        current_date = start_date.date() if isinstance(start_date, datetime) else start_date

        for day in range(duration_days):
            schedule_date = current_date + timedelta(days=day)

            for time_str in times:
                hour, minute = map(int, time_str.split(':'))
                scheduled_time = datetime.combine(schedule_date, datetime.min.time().replace(hour=hour, minute=minute))

                # Only schedule future doses
                if scheduled_time > datetime.now():
                    admin_id = str(uuid.uuid4())

                    await conn.execute("""
                        INSERT INTO medicationadministrations (
                            id, medicationid, patientid, scheduledtime, dosagegiven,
                            route, status, notes, createdat, updatedat
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                        admin_id,
                        medication_id,
                        patient_id,
                        scheduled_time,
                        medication_data.get('dosage', ''),
                        medication_data.get('route', 'PO'),
                        'scheduled',
                        f'Auto-scheduled based on frequency: {frequency}',
                        datetime.now(),
                        datetime.now()
                    )

        logger.info(f"✅ Auto-scheduled medication administrations for {medication_id}")

    except Exception as e:
        logger.error(f"❌ Auto-schedule medication error: {e}")
        # Don't raise exception as this is a supporting function


@router.post("/{patient_id}/medications/{medication_id}/schedule")
async def schedule_existing_medication(
    patient_id: str,
    medication_id: str,
    created_by: str = Query(..., description="ID of the user scheduling the medication")
):
    """Schedule an existing medication for administration"""
    try:
        async with get_db_connection() as conn:
            # Get medication details
            medication = await conn.fetchrow(
                "SELECT * FROM medications WHERE id = $1 AND patientid = $2 AND status = 'active'",
                medication_id, patient_id
            )

            if not medication:
                raise HTTPException(status_code=404, detail="Active medication not found")

            # Convert to dict for auto_schedule_medication
            medication_data = {
                'frequency': medication['frequency'],
                'startDate': medication['startdate'],
                'duration': medication['duration'],
                'dosage': medication['dosage'],
                'route': medication['route']
            }

            # Auto-schedule the medication
            await auto_schedule_medication(conn, medication_id, patient_id, medication_data)

            return {"message": f"Medication {medication_id} scheduled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Schedule existing medication error: {e}")
        raise HTTPException(status_code=500, detail="Failed to schedule medication")