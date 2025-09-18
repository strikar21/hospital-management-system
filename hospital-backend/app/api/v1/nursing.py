"""
Nursing dashboard API endpoints for ward-level clinical workflow
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from ...core.database import get_db_connection
from ...core.db_utils import fetch_one, fetch_all
from ...services.audit import log_audit_event

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/ward/{ward_name}/dashboard")
async def get_ward_dashboard(
    ward_name: str,
    shift: Optional[str] = Query(None, description="nursing shift filter")
):
    """
    Get comprehensive ward dashboard with all patients and their clinical status
    """
    try:
        async with get_db_connection() as conn:
            # Get all active patients in the ward
            patients_query = """
                SELECT 
                    p.id, p.firstname, p.lastname, p.roomnumber, p.bednumber,
                    p.attendingphysician, p.nurseincharge, p.admissiondate,
                    d.id as deviceid, d.devicetype, d.status as devicestatus
                FROM patients p
                LEFT JOIN devices d ON p.assigneddeviceid = d.id
                WHERE p.status = 'active' 
                AND (p.roomnumber LIKE $1 OR $1 IS NULL)
                ORDER BY p.roomnumber, p.bednumber
            """
            
            ward_filter = f"{ward_name}%" if ward_name != "all" else None
            patients = await conn.fetch(patients_query, ward_filter)
            
            ward_data = []
            for patient in patients:
                patient_dict = dict(patient)
                patient_id = patient_dict['id']
                
                # Get pending medication administrations
                med_query = """
                    SELECT ma.id, ma.scheduledtime, ma.status, m.name, ma.dosagegiven
                    FROM medicationadministrations ma
                    JOIN medications m ON ma.medicationid::text = m.id::text
                    WHERE ma.patientid = $1 AND ma.status IN ('scheduled', 'due')
                    AND ma.scheduledtime >= NOW() - INTERVAL '24 hours'
                    AND ma.scheduledtime <= NOW() + INTERVAL '4 hours'
                    ORDER BY ma.scheduledtime
                """
                pending_meds = await conn.fetch(med_query, patient_id)
                
                # Get pending therapy sessions
                therapy_query = """
                    SELECT ts.id, ts.scheduleddate, ts.status, t.type, t.description
                    FROM therapysessions ts
                    JOIN therapy t ON ts.therapyid::text = t.id::text
                    WHERE ts.patientid = $1 AND ts.status IN ('scheduled', 'in_progress')
                    AND ts.scheduleddate >= NOW() - INTERVAL '24 hours'
                    AND ts.scheduleddate <= NOW() + INTERVAL '4 hours'
                    ORDER BY ts.scheduleddate
                """
                pending_therapies = await conn.fetch(therapy_query, patient_id)
                
                # Get pending investigations
                investigations_query = """
                    SELECT id, name, type, scheduledtime, priority, status
                    FROM investigations
                    WHERE patientid = $1 AND status IN ('ordered', 'scheduled')
                    AND scheduledtime >= NOW() - INTERVAL '24 hours'
                    AND scheduledtime <= NOW() + INTERVAL '8 hours'
                    ORDER BY priority DESC, scheduledtime
                """
                pending_investigations = await conn.fetch(investigations_query, patient_id)
                
                # Get latest vitals (last 30 minutes)
                vitals_query = """
                    SELECT vitaltype, value, unit, time
                    FROM vitals_timeseries 
                    WHERE patientid = $1 
                    AND time >= NOW() - INTERVAL '30 minutes'
                    ORDER BY time DESC
                    LIMIT 10
                """
                recent_vitals = await conn.fetch(vitals_query, patient_id)
                
                patient_data = {
                    "patient": dict(patient),
                    "pendingMedications": [dict(med) for med in pending_meds],
                    "pendingTherapies": [dict(therapy) for therapy in pending_therapies],
                    "pendingInvestigations": [dict(inv) for inv in pending_investigations],
                    "recentVitals": [dict(vital) for vital in recent_vitals],
                    "alertCount": len(pending_meds) + len(pending_therapies) + len(pending_investigations)
                }
                
                ward_data.append(patient_data)
            
            return {
                "ward": ward_name,
                "totalPatients": len(ward_data),
                "shift": shift,
                "timestamp": datetime.now(),
                "patients": ward_data
            }
            
    except Exception as e:
        logger.error(f"❌ Ward dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get ward dashboard")

@router.get("/medication-alerts")
async def get_medication_alerts(
    ward: Optional[str] = Query(None, description="Ward filter"),
    hours_ahead: int = Query(4, description="Hours to look ahead for due medications")
):
    """
    Get medication administration alerts for nursing staff
    """
    try:
        async with get_db_connection() as conn:
            query = """
                SELECT 
                    ma.id, ma.patientid, ma.scheduledtime, ma.status,
                    m.name as medicationname, ma.dosagegiven, m.route,
                    p.firstname, p.lastname, p.roomnumber, p.bednumber
                FROM medicationadministrations ma
                JOIN medications m ON ma.medicationid::text = m.id::text
                JOIN patients p ON ma.patientid = p.id
                WHERE ma.status IN ('scheduled', 'due', 'overdue')
                AND ma.scheduledtime <= NOW() + INTERVAL '%s hours'
                AND p.status = 'active'
                AND ($1 IS NULL OR p.roomnumber LIKE $1)
                ORDER BY 
                    CASE 
                        WHEN ma.scheduledtime < NOW() THEN 0 -- overdue first
                        ELSE 1 
                    END,
                    ma.scheduledtime
            """
            
            ward_filter = f"{ward}%" if ward else None
            alerts = await conn.fetch(query % hours_ahead, ward_filter)
            
            return {
                "totalAlerts": len(alerts),
                "ward": ward,
                "hoursAhead": hours_ahead,
                "timestamp": datetime.now(),
                "alerts": [dict(alert) for alert in alerts]
            }
            
    except Exception as e:
        logger.error(f"❌ Medication alerts error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get medication alerts")

@router.get("/therapy-schedule")
async def get_therapy_schedule(
    ward: Optional[str] = Query(None, description="Ward filter"),
    date: Optional[str] = Query(None, description="Date filter (YYYY-MM-DD)")
):
    """
    Get therapy session schedule for nursing coordination
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date() if date else datetime.now().date()
        
        async with get_db_connection() as conn:
            query = """
                SELECT 
                    ts.id, ts.patientid, ts.scheduleddate, ts.status, ts.sessionnumber,
                    t.type as therapytype, t.description, ts.performedby,
                    p.firstname, p.lastname, p.roomnumber, p.bednumber
                FROM therapysessions ts
                JOIN therapy t ON ts.therapyid::text = t.id::text
                JOIN patients p ON ts.patientid = p.id
                WHERE DATE(ts.scheduleddate) = $1
                AND p.status = 'active'
                AND ($2 IS NULL OR p.roomnumber LIKE $2)
                ORDER BY ts.scheduleddate, p.roomnumber, p.bednumber
            """
            
            ward_filter = f"{ward}%" if ward else None
            sessions = await conn.fetch(query, target_date, ward_filter)
            
            return {
                "date": target_date.isoformat(),
                "ward": ward,
                "totalSessions": len(sessions),
                "timestamp": datetime.now(),
                "sessions": [dict(session) for session in sessions]
            }
            
    except Exception as e:
        logger.error(f"❌ Therapy schedule error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get therapy schedule")

@router.post("/medication-administration/{administration_id}/administer")
async def administer_medication(
    administration_id: str,
    administered_by: str,
    notes: Optional[str] = None
):
    """
    Mark medication as administered
    """
    try:
        async with get_db_connection() as conn:
            # Check if administration exists
            check_query = """
                SELECT ma.*, p.firstname, p.lastname, m.name as medicationname
                FROM medicationadministrations ma
                JOIN patients p ON ma.patientid = p.id
                JOIN medications m ON ma.medicationid::text = m.id::text
                WHERE ma.id = $1
            """
            administration = await conn.fetchrow(check_query, administration_id)
            
            if not administration:
                raise HTTPException(status_code=404, detail="Medication administration not found")
            
            # Update administration status
            update_query = """
                UPDATE medicationadministrations 
                SET status = 'administered', 
                    administeredat = NOW(),
                    administeredby = $1,
                    notes = $2,
                    updatedat = NOW()
                WHERE id = $3
            """
            await conn.execute(update_query, administered_by, notes, administration_id)
            
            # Log audit event
            await log_audit_event(
                user_id=administered_by,
                action="MEDICATION_ADMINISTERED",
                resource_type="MEDICATION_ADMINISTRATION",
                resource_id=administration_id,
                details=f"Administered {administration['medicationname']} to {administration['firstname']} {administration['lastname']}"
            )
            
            logger.info(f"✅ Medication administered: {administration_id} by {administered_by}")
            
            return {
                "message": "Medication administered successfully",
                "administrationId": administration_id,
                "administeredBy": administered_by,
                "administeredAt": datetime.now()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Administer medication error: {e}")
        raise HTTPException(status_code=500, detail="Failed to administer medication")

@router.post("/therapy-session/{session_id}/complete")
async def complete_therapy_session(
    session_id: str,
    performed_by: str,
    session_notes: Optional[str] = None,
    duration: Optional[str] = None
):
    """
    Mark therapy session as completed
    """
    try:
        async with get_db_connection() as conn:
            # Check if session exists
            check_query = """
                SELECT ts.*, p.firstname, p.lastname, t.type, t.description
                FROM therapysessions ts
                JOIN patients p ON ts.patientid = p.id
                JOIN therapy t ON ts.therapyid::text = t.id::text
                WHERE ts.id = $1
            """
            session = await conn.fetchrow(check_query, session_id)
            
            if not session:
                raise HTTPException(status_code=404, detail="Therapy session not found")
            
            # Update session status
            update_query = """
                UPDATE therapysessions 
                SET status = 'completed',
                    completedat = NOW(),
                    performedby = $1,
                    sessionnotes = $2,
                    duration = $3,
                    updatedat = NOW()
                WHERE id = $4
            """
            await conn.execute(update_query, performed_by, session_notes, duration, session_id)
            
            # Log audit event
            await log_audit_event(
                user_id=performed_by,
                action="THERAPY_SESSION_COMPLETED",
                resource_type="THERAPY_SESSION",
                resource_id=session_id,
                details=f"Completed {session['type']} session for {session['firstname']} {session['lastname']}"
            )
            
            logger.info(f"✅ Therapy session completed: {session_id} by {performed_by}")
            
            return {
                "message": "Therapy session completed successfully",
                "sessionId": session_id,
                "performedBy": performed_by,
                "completedAt": datetime.now()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Complete therapy session error: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete therapy session")