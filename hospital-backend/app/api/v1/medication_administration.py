"""
Medication administration tracking API endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
import logging

from ...core.database import get_db_connection
from ...core.db_utils import fetch_one, fetch_all
from ...services.audit import log_audit_event

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/schedule")
async def schedule_medication_administration(administration_data: dict):
    """
    Schedule a medication administration
    """
    try:
        async with get_db_connection() as conn:
            # Verify medication exists
            medication_query = "SELECT * FROM medications WHERE id = $1::text AND patientid = $2"
            medication = await conn.fetchrow(medication_query, 
                                           str(administration_data['medicationId']), 
                                           administration_data['patientId'])
            
            if not medication:
                raise HTTPException(status_code=404, detail="Medication not found")
            
            # Generate administration ID
            admin_id = str(uuid.uuid4())
            
            query = """
                INSERT INTO medicationadministrations (
                    id, medicationid, patientid, scheduledtime, dosagegiven, 
                    route, status, notes, createdat, updatedat
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id
            """
            
            scheduled_time = datetime.fromisoformat(administration_data['scheduledTime'].replace('Z', '+00:00'))
            
            result = await conn.fetchrow(query,
                admin_id,
                str(administration_data['medicationId']),
                administration_data['patientId'],
                scheduled_time,
                administration_data.get('dosageGiven', medication['dosage']),
                administration_data.get('route', medication['route']),
                'scheduled',
                administration_data.get('notes', ''),
                datetime.now(),
                datetime.now()
            )
            
            # Log audit event
            await log_audit_event(
                user_id=administration_data.get('scheduledBy', 'system'),
                action="MEDICATION_ADMINISTRATION_SCHEDULED",
                resource_type="MEDICATION_ADMINISTRATION",
                resource_id=admin_id,
                details=f"Scheduled {medication['name']} administration for patient {administration_data['patientId']}"
            )
            
            logger.info(f"✅ Scheduled medication administration: {admin_id}")
            
            return {
                "message": "Medication administration scheduled successfully",
                "administrationId": admin_id,
                "scheduledTime": scheduled_time
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Schedule medication administration error: {e}")
        raise HTTPException(status_code=500, detail="Failed to schedule medication administration")

@router.get("/patient/{patient_id}")
async def get_patient_medication_administrations(
    patient_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)")
):
    """
    Get medication administrations for a patient
    """
    try:
        async with get_db_connection() as conn:
            query = """
                SELECT 
                    ma.id, ma.medicationid, ma.patientid, ma.scheduledtime, 
                    ma.administeredat, ma.administeredby, ma.dosagegiven, 
                    ma.route, ma.status, ma.notes,
                    m.name as medicationname, m.frequency, m.duration
                FROM medicationadministrations ma
                JOIN medications m ON ma.medicationid::text = m.id::text
                WHERE ma.patientid = $1
            """
            
            params = [patient_id]
            param_count = 1
            
            if status:
                param_count += 1
                query += f" AND ma.status = ${param_count}"
                params.append(status)
            
            if date_from:
                param_count += 1
                query += f" AND DATE(ma.scheduledtime) >= ${param_count}"
                params.append(date_from)
                
            if date_to:
                param_count += 1
                query += f" AND DATE(ma.scheduledtime) <= ${param_count}"
                params.append(date_to)
            
            query += " ORDER BY ma.scheduledtime DESC"
            
            rows = await conn.fetch(query, *params)
            
            administrations = []
            for row in rows:
                admin_dict = dict(row)
                # Convert to camelCase for consistency
                admin_formatted = {
                    "id": admin_dict["id"],
                    "medicationId": admin_dict["medicationid"],
                    "patientId": admin_dict["patientid"],
                    "scheduledTime": admin_dict["scheduledtime"],
                    "administeredAt": admin_dict["administeredat"],
                    "administeredBy": admin_dict["administeredby"],
                    "dosageGiven": admin_dict["dosagegiven"],
                    "route": admin_dict["route"],
                    "status": admin_dict["status"],
                    "notes": admin_dict["notes"],
                    "medicationName": admin_dict["medicationname"],
                    "frequency": admin_dict["frequency"],
                    "duration": admin_dict["duration"]
                }
                administrations.append(admin_formatted)
            
            logger.info(f"💊 Retrieved {len(administrations)} medication administrations for patient {patient_id}")
            return administrations
            
    except Exception as e:
        logger.error(f"❌ Get patient medication administrations error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve medication administrations")

@router.put("/{administration_id}/administer")
async def administer_medication(
    administration_id: str,
    administration_data: dict
):
    """
    Mark medication as administered
    """
    try:
        async with get_db_connection() as conn:
            # Check if administration exists
            check_query = """
                SELECT ma.*, m.name as medicationname, p.firstname, p.lastname
                FROM medicationadministrations ma
                JOIN medications m ON ma.medicationid::text = m.id::text
                JOIN patients p ON ma.patientid = p.id
                WHERE ma.id = $1
            """
            administration = await conn.fetchrow(check_query, administration_id)
            
            if not administration:
                raise HTTPException(status_code=404, detail="Medication administration not found")
            
            if administration['status'] == 'administered':
                raise HTTPException(status_code=400, detail="Medication already administered")
            
            # Update administration
            update_query = """
                UPDATE medicationadministrations 
                SET status = 'administered',
                    administeredat = $1,
                    administeredby = $2,
                    notes = COALESCE($3, notes),
                    dosagegiven = COALESCE($4, dosagegiven),
                    updatedat = $1
                WHERE id = $5
            """
            
            now = datetime.now()
            await conn.execute(update_query,
                now,
                administration_data['administeredBy'],
                administration_data.get('notes'),
                administration_data.get('dosageGiven'),
                administration_id
            )
            
            # Log audit event
            await log_audit_event(
                user_id=administration_data['administeredBy'],
                action="MEDICATION_ADMINISTERED",
                resource_type="MEDICATION_ADMINISTRATION", 
                resource_id=administration_id,
                details=f"Administered {administration['medicationname']} to {administration['firstname']} {administration['lastname']}"
            )
            
            logger.info(f"💊 Medication administered: {administration_id}")
            
            return {
                "message": "Medication administered successfully",
                "administrationId": administration_id,
                "administeredAt": now,
                "administeredBy": administration_data['administeredBy']
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Administer medication error: {e}")
        raise HTTPException(status_code=500, detail="Failed to administer medication")

@router.put("/{administration_id}/skip")
async def skip_medication_administration(
    administration_id: str,
    skip_data: dict
):
    """
    Mark medication administration as skipped
    """
    try:
        async with get_db_connection() as conn:
            # Check if administration exists
            check_query = "SELECT * FROM medicationadministrations WHERE id = $1"
            administration = await conn.fetchrow(check_query, administration_id)
            
            if not administration:
                raise HTTPException(status_code=404, detail="Medication administration not found")
            
            if administration['status'] != 'scheduled':
                raise HTTPException(status_code=400, detail="Only scheduled administrations can be skipped")
            
            # Update administration
            update_query = """
                UPDATE medicationadministrations 
                SET status = 'skipped',
                    notes = COALESCE($1, notes) || '\nSkipped: ' || $2,
                    updatedat = $3
                WHERE id = $4
            """
            
            now = datetime.now()
            await conn.execute(update_query,
                administration['notes'],
                skip_data.get('reason', 'No reason provided'),
                now,
                administration_id
            )
            
            # Log audit event
            await log_audit_event(
                user_id=skip_data['skippedBy'],
                action="MEDICATION_ADMINISTRATION_SKIPPED",
                resource_type="MEDICATION_ADMINISTRATION",
                resource_id=administration_id,
                details=f"Skipped medication administration: {skip_data.get('reason', 'No reason provided')}"
            )
            
            logger.info(f"💊 Medication administration skipped: {administration_id}")
            
            return {
                "message": "Medication administration skipped",
                "administrationId": administration_id,
                "reason": skip_data.get('reason', 'No reason provided'),
                "skippedBy": skip_data['skippedBy']
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Skip medication administration error: {e}")
        raise HTTPException(status_code=500, detail="Failed to skip medication administration")

@router.get("/due")
async def get_due_administrations(
    hours_ahead: int = Query(4, description="Hours to look ahead for due medications"),
    ward: Optional[str] = Query(None, description="Filter by ward/room prefix")
):
    """
    Get medication administrations that are due or overdue
    """
    try:
        async with get_db_connection() as conn:
            query = """
                SELECT
                    ma.id, ma.patientid, ma.scheduledtime, ma.status, ma.dosagegiven,
                    m.name as medicationname, m.route,
                    p.firstname, p.lastname, p.roomnumber, p.bednumber
                FROM medicationadministrations ma
                JOIN medications m ON ma.medicationid::text = m.id::text
                JOIN patients p ON ma.patientid = p.id
                WHERE ma.status IN ('scheduled', 'due')
                AND ma.scheduledtime <= NOW() + INTERVAL '%s hours'
                AND p.status = 'active'
            """ % hours_ahead
            
            params = []
            if ward:
                query += " AND p.roomnumber LIKE $1"
                params.append(f"{ward}%")
            
            query += """
                ORDER BY
                    CASE
                        WHEN ma.scheduledtime AT TIME ZONE 'UTC' < NOW() AT TIME ZONE 'UTC' THEN 0 -- overdue first
                        ELSE 1
                    END,
                    ma.scheduledtime
            """
            
            rows = await conn.fetch(query, *params) if params else await conn.fetch(query)
            
            due_administrations = []
            for row in rows:
                admin_dict = dict(row)
                # Determine if overdue - handle timezone aware comparison
                scheduled_time = admin_dict['scheduledtime']
                if scheduled_time.tzinfo:
                    # Timezone aware datetime
                    current_time = datetime.now(scheduled_time.tzinfo)
                else:
                    # Timezone naive datetime
                    current_time = datetime.now()
                is_overdue = scheduled_time < current_time
                
                admin_formatted = {
                    "id": admin_dict["id"],
                    "patientId": admin_dict["patientid"],
                    "scheduledTime": admin_dict["scheduledtime"],
                    "status": admin_dict["status"],
                    "dosageGiven": admin_dict["dosagegiven"],
                    "medicationName": admin_dict["medicationname"],
                    "route": admin_dict["route"],
                    "patientName": f"{admin_dict['firstname']} {admin_dict['lastname']}",
                    "roomNumber": admin_dict["roomnumber"],
                    "bedNumber": admin_dict["bednumber"],
                    "isOverdue": is_overdue
                }
                due_administrations.append(admin_formatted)
            
            overdue_count = sum(1 for admin in due_administrations if admin['isOverdue'])
            
            logger.info(f"💊 Retrieved {len(due_administrations)} due administrations ({overdue_count} overdue)")
            
            return {
                "totalDue": len(due_administrations),
                "overdueCount": overdue_count,
                "hoursAhead": hours_ahead,
                "administrations": due_administrations
            }
            
    except Exception as e:
        logger.error(f"❌ Get due administrations error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve due administrations")