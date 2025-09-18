"""
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
                       p.status, p.createdat, p.updatedat, s.firstname || ' ' || s.lastname as attendingphysicianname
                FROM patients p
                LEFT JOIN staff s ON p.attendingphysician = s.id
                WHERE 1=1"""
            params = []
            
            if status is not None and status != "":
                query += " AND p.status = ?"
                params.append(status)
            
            if room_number is not None and room_number != "":
                query += " AND p.roomNumber = ?"
                params.append(room_number)
            
            query += " ORDER BY p.createdAt DESC LIMIT ?"
            params.append(limit)
            
            rows = await fetch_all(conn, query, tuple(params))
            
            patients = []
            for row in rows:
                patient_dict = dict(row) if hasattr(row, 'keys') else row
                # Transform to camelCase for frontend compatibility
                transformed_dict = transform_patient_to_camel(patient_dict)
                patients.append(transformed_dict)
            
            # Debug logging to check device assignments
            for patient in patients:
                if patient.get('firstName') == 'Sarah' and patient.get('lastName') == 'Johnson':
                    logger.info(f"🔍 Sarah Johnson patient data: assignedDeviceId={patient.get('assignedDeviceId')}")

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
            # Simple patient query first - avoid complex JOINs that might hang
            patient_query = "SELECT * FROM patients WHERE id = ?"
            patient_row = await fetch_one(conn, patient_query, (patient_id,))

            if not patient_row:
                raise HTTPException(status_code=404, detail="Patient not found")

            patient_dict = dict(patient_row) if hasattr(patient_row, 'keys') else patient_row

            # Get medications
            medications_query = "SELECT m.*, s.name as prescribedbyname FROM medications m LEFT JOIN staff s ON m.prescribedby = s.id WHERE m.patientid = ? ORDER BY m.createdat DESC"
            medications_rows = await fetch_all(conn, medications_query, (patient_id,))

            # Get investigations
            investigations_query = "SELECT i.*, s.name as performedbyname FROM investigations i LEFT JOIN staff s ON i.performedby = s.id WHERE i.patientid = ? ORDER BY i.createdat DESC"
            investigations_rows = await fetch_all(conn, investigations_query, (patient_id,))

            # Get therapy
            therapy_query = "SELECT t.*, s.name as performedbyname FROM therapy t LEFT JOIN staff s ON t.performedby = s.id WHERE t.patientid = ? ORDER BY t.createdat DESC"
            therapy_rows = await fetch_all(conn, therapy_query, (patient_id,))

            # Get patient notes
            notes_query = "SELECT pn.*, s.name as authorname FROM patient_notes pn LEFT JOIN staff s ON pn.authorid = s.id WHERE pn.patientid = ? ORDER BY pn.createdat DESC"
            notes_rows = await fetch_all(conn, notes_query, (patient_id,))

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

            # Create complete patient data with actual clinical data
            complete_patient_data = {
                **patient_dict,
                'currentVitals': None,
                'recentVitals': [],
                'medications': medications,
                'investigations': investigations,
                'therapies': therapies,
                'notes': notes
            }

            # Transform to camelCase for frontend compatibility
            transformed_data = transform_patient_to_camel(complete_patient_data)

            return transformed_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get patient error: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
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
                    medicalHistory, currentMedications, roomNumber, bedNumber,
                    attendingPhysician, nurseInCharge, admissionDate, createdAt, updatedat
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            now = datetime.now()
            await conn.execute(query, (
                patient_id, patient_data.firstName, patient_data.lastName,
                patient_data.dateOfBirth, patient_data.gender, patient_data.phoneNumber,
                patient_data.emergencyContactName, patient_data.emergencyContactPhone,
                patient_data.bloodType, patient_data.allergies, patient_data.medicalHistory,
                patient_data.currentMedications, patient_data.roomNumber, patient_data.bedNumber,
                patient_data.attendingPhysician, patient_data.nurseInCharge, now, now, now
            ))
                        
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
            existing = await fetch_one(conn, "SELECT * FROM patients WHERE id = ?", (patient_id,))
            if not existing:
                raise HTTPException(status_code=404, detail="Patient not found")
            
            # Build update query for non-None fields
            update_fields = []
            params = []
            
            for field, value in patient_data.dict(exclude_unset=True).items():
                if value is not None:
                    update_fields.append(f"{field} = ?")
                    params.append(value)
            
            if not update_fields:
                raise HTTPException(status_code=400, detail="No fields to update")
            
            update_fields.append("updatedat = ?")
            params.append(datetime.now())
            params.append(patient_id)
            
            query = f"UPDATE patients SET {', '.join(update_fields)} WHERE id = ?"
            await conn.execute(query, params)
                        
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
            existing = await fetch_one(conn, "SELECT * FROM patients WHERE id = ? AND status = 'active'", (patient_id,))
            if not existing:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            # Update patient status to pending discharge
            await execute_query(conn, 
                "UPDATE patients SET status = ?, updatedat = ? WHERE id = ?",
                ('pending_discharge', datetime.now(), patient_id)
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
            existing = await fetch_one(conn, "SELECT * FROM patients WHERE id = ? AND status = 'pending_discharge'", (patient_id,))
            if not existing:
                raise HTTPException(status_code=404, detail="Patient not pending discharge")
            
            # Update to approved status
            await execute_query(conn,
                "UPDATE patients SET status = ?, updatedat = ? WHERE id = ?",
                ('discharge_approved', datetime.now(), patient_id)
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
            existing = await fetch_one(conn, "SELECT * FROM patients WHERE id = ? AND status = 'discharge_approved'", (patient_id,))
            if not existing:
                raise HTTPException(status_code=404, detail="Patient not approved for discharge")
            
            now = datetime.now()
            
            # Complete discharge
            await execute_query(conn,
                "UPDATE patients SET status = ?, dischargedate = ?, updatedat = ? WHERE id = ?",
                ('discharged', now, now, patient_id)
            )
            
            # Remove watch and return to pool
            # First get the assigned device
            assigned_device = await conn.fetchrow(
                "SELECT deviceid FROM deviceassignments WHERE patientid = $1 AND status = 'active'",
                patient_id
            )

            if assigned_device:
                device_id = assigned_device['deviceid']

                # Update assignment status
                await conn.execute(
                    "UPDATE deviceassignments SET status = 'inactive', unassignedat = $1, unassignedby = $2, unassignmentreason = 'Patient discharged' WHERE patientid = $3 AND status = 'active'",
                    now, completion_data.get('nurseId', 'System'), patient_id
                )

                # Return device to available pool
                await conn.execute(
                    "UPDATE devices SET status = 'available', assignedpatientid = NULL, updatedat = $1 WHERE id = $2",
                    now, device_id
                )

                # Clear patient device assignment
                await conn.execute(
                    "UPDATE patients SET assigneddeviceid = NULL WHERE id = $1",
                    patient_id
                )

                logger.info(f"✅ Watch {device_id} returned to pool from patient {patient_id}")
            else:
                logger.info(f"ℹ️ No watch assigned to patient {patient_id} during discharge")
            
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
                "name": f"{patient_dict.get('firstname', '')} {patient_dict.get('lastname', '')}",
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
                    id, patientid, name, dosage, frequency, route, status, prescribedby
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, 
                medication_id,
                patient_id, 
                medication_data.get('name', ''),
                medication_data.get('dosage', ''),
                medication_data.get('frequency', ''),
                medication_data.get('route', ''),
                medication_data.get('status', 'active'),
                created_by
            )
            
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
            count_result = await conn.fetchval('SELECT COUNT(*) FROM patient_notes WHERE patientid = $1', patient_id)
            next_note_number = (count_result or 0) + 1
            patient_note_id = f"{patient_id}-NOTE{next_note_number}"
            
            # Insert the note with patient-specific sequential ID
            await conn.execute("""
                INSERT INTO patient_notes (
                    id, patientid, notecontent, notetype, authorid, authorname, authorrole
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, 
                patient_note_id, patient_id, content.strip(), note_data.get('category', 'General'), created_by,
                note_data.get('authorName', 'Unknown'), note_data.get('authorRole', 'Staff')
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
                        # Handle tuple/list format
                        keys = ['id', 'patientid', 'content', 'authorId', 'authorName', 'authorRole', 'timestamp', 'editedAt', 'isEdited']
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
                            "authorId": created_by,
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
                        "authorId": created_by,
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
    Get all case sheet entries for a patient
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists
            patient = await fetch_one(conn, "SELECT id FROM patients WHERE id = ? AND status = 'active'", (patient_id,))
            if not patient:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            query = """
                SELECT c.*, s.name as performedbyname
                FROM caseSheetEntries c
                LEFT JOIN staff s ON c.performedBy = s.id
                WHERE c.patientid = ? 
                ORDER BY c.timestamp DESC
            """
            
            rows = await fetch_all(conn, query, (patient_id,))
            entries = []
            for row in rows:
                entry_dict = dict(row) if hasattr(row, 'keys') else row
                entries.append(entry_dict)
            
            logger.info(f"📋 Retrieved {len(entries)} case entries for patient: {patient_id}")
            return entries
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get case entries error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve case entries")

@router.get("/{patient_id}/medications")
async def get_medications(patient_id: str):
    """
    Get all medications for a patient
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists
            patient = await fetch_one(conn, "SELECT id FROM patients WHERE id = ? AND status = 'active'", (patient_id,))
            if not patient:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            query = """
                SELECT * FROM medications 
                WHERE patientid = ? 
                ORDER BY createdAt DESC
            """
            
            rows = await fetch_all(conn, query, (patient_id,))
            medications = []
            for row in rows:
                med_dict = dict(row) if hasattr(row, 'keys') else row
                medications.append(med_dict)
            
            logger.info(f"💊 Retrieved {len(medications)} medications for patient: {patient_id}")
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
                SELECT pn.*, s.name as authorname 
                FROM patient_notes pn
                LEFT JOIN staff s ON pn.authorid = s.id
                WHERE pn.patientid = $1 
                ORDER BY pn.createdat DESC
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
            patient = await fetch_one(conn, "SELECT id FROM patients WHERE id = ? AND status = 'active'", (patient_id,))
            if not patient:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            # Verify medication exists and is active
            medication = await fetch_one(conn, 
                "SELECT * FROM medications WHERE id = ? AND patientid = ? AND status = 'active'", 
                (int(medication_id), patient_id))
            if not medication:
                raise HTTPException(status_code=404, detail="Active medication not found")
            
            # Update medication's updatedat timestamp to record administration
            now = datetime.now()
            await execute_query(conn, 
                "UPDATE medications SET updatedat = ? WHERE id = ? AND patientid = ?",
                (now, int(medication_id), patient_id))
            
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
                query_find = "SELECT id FROM patient_notes WHERE id = ? AND patientid = ?"
                try:
                    existing_note = await fetch_one(conn, query_find, (int(note_id), patient_id))
                except ValueError:
                    existing_note = None
            elif note_id.startswith(patient_id) and "-NOTE" in note_id:
                # Patient-specific ID (PAT-xxx-NOTEx)
                query_find = "SELECT id FROM patient_notes WHERE id = ? AND patientid = ?"
                existing_note = await fetch_one(conn, query_find, (note_id, patient_id))
            else:
                # Unknown ID format
                logger.warning(f"Unknown note ID format: {note_id}")
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