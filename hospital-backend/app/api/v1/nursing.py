"""
Nursing dashboard API endpoints for ward-level clinical workflow
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from ...core.database import getDbConnection
from ...core.db_utils import fetchOne, fetchAll
from ...services.audit import logAuditEvent

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/ward/{wardName}/dashboard")
async def getWardDashboard(
    wardName: str,
    shift: Optional[str] = Query(None, description="nursing shift filter")
):
    """
    Get comprehensive ward dashboard with all patients and their clinical status
    """
    try:
        async with getDbConnection() as conn:
            # Get all active patients in the ward
            patientsQuery = """
                SELECT 
                    p.id, p.firstName, p.lastName, p.roomNumber, p.bedNumber,
                    p.attendingPhysician, p.nurseInCharge, p.admissionDate,
                    d.id as "deviceId", d.deviceType, d.status as devicestatus
                FROM patients p
                LEFT JOIN devices d ON p.assignedDeviceId = d.id
                WHERE p.status = 'active' 
                AND (p.roomNumber LIKE $1 OR $1 IS NULL)
                ORDER BY p.roomNumber, p.bedNumber
            """
            
            wardFilter = f"{wardName}%" if wardName != "all" else None
            patients = await conn.fetch(patientsQuery, wardFilter)
            
            wardData = []
            for patient in patients:
                patientDict = dict(patient)
                patientId = patientDict['id']
                
                # Get pending medication administrations
                medQuery = """
                    SELECT ma.id, ma.scheduledTime, ma.status, m.name, ma.dosageGiven
                    FROM medicationadministrations ma
                    JOIN medications m ON ma.medicationId::text = m.id::text
                    WHERE ma.patientId = $1 AND ma.status IN ('scheduled', 'due')
                    AND ma.scheduledTime >= NOW() - INTERVAL '24 hours'
                    AND ma.scheduledTime <= NOW() + INTERVAL '4 hours'
                    ORDER BY ma.scheduledTime
                """
                pendingMeds = await conn.fetch(medQuery, patientId)
                
                # Get pending therapy sessions
                therapyQuery = """
                    SELECT ts.id, ts.scheduleddate, ts.status, t.type, t.description
                    FROM therapysessions ts
                    JOIN therapy t ON ts.therapyid::text = t.id::text
                    WHERE ts.patientId = $1 AND ts.status IN ('scheduled', 'inProgress')
                    AND ts.scheduleddate >= NOW() - INTERVAL '24 hours'
                    AND ts.scheduleddate <= NOW() + INTERVAL '4 hours'
                    ORDER BY ts.scheduleddate
                """
                pendingTherapies = await conn.fetch(therapyQuery, patientId)
                
                # Get pending investigations
                investigationsQuery = """
                    SELECT id, name, type, "scheduledTime", priority, status
                    FROM investigations
                    WHERE "patientId" = $1 AND status IN ('ordered', 'scheduled')
                    AND "scheduledTime" >= NOW() - INTERVAL '24 hours'
                    AND "scheduledTime" <= NOW() + INTERVAL '8 hours'
                    ORDER BY priority DESC, "scheduledTime"
                """
                pendingInvestigations = await conn.fetch(investigationsQuery, patientId)
                
                # Get latest vitals (last 30 minutes)
                vitalsQuery = """
                    SELECT vitaltype, value, unit, time
                    FROM vitals_timeseries 
                    WHERE "patientId" = $1 
                    AND time >= NOW() - INTERVAL '30 minutes'
                    ORDER BY time DESC
                    LIMIT 10
                """
                recentVitals = await conn.fetch(vitalsQuery, patientId)
                
                patientData = {
                    patient: dict(patient),
                    pendingmedications: [dict(med) for med in pendingMeds],
                    pendingtherapies: [dict(therapy) for therapy in pendingTherapies],
                    pendinginvestigations: [dict(inv) for inv in pendingInvestigations],
                    recentvitals: [dict(vital) for vital in recentVitals],
                    alertcount: len(pendingMeds) + len(pendingTherapies) + len(pendingInvestigations)
                }
                
                wardData.append(patientData)
            
            return {
                ward: wardName,
                totalpatients: len(wardData),
                shift: shift,
                timestamp: datetime.now(),
                patients: wardData
            }
            
    except Exception as e:
        logger.error(f"❌ Ward dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get ward dashboard")

@router.get("/medication-alerts")
async def getMedicationAlerts(
    ward: Optional[str] = Query(None, description="Ward filter"),
    hoursAhead: int = Query(4, description="Hours to look ahead for due medications")
):
    """
    Get medication administration alerts for nursing staff
    """
    try:
        async with getDbConnection() as conn:
            query = """
                SELECT 
                    ma.id, ma.patientId, ma.scheduledTime, ma.status,
                    m.name as medicationname, ma.dosageGiven, m.route,
                    p.firstName, p.lastName, p.roomNumber, p.bedNumber
                FROM medicationadministrations ma
                JOIN medications m ON ma.medicationId::text = m.id::text
                JOIN patients p ON ma.patientId = p.id
                WHERE ma.status IN ('scheduled', 'due', 'overdue')
                AND ma.scheduledTime <= NOW() + INTERVAL '%s hours'
                AND p.status = 'active'
                AND ($1 IS NULL OR p.roomNumber LIKE $1)
                ORDER BY 
                    CASE 
                        WHEN ma.scheduledTime < NOW() THEN 0 -- overdue first
                        ELSE 1 
                    END,
                    ma.scheduledTime
            """
            
            wardFilter = f"{ward}%" if ward else None
            alerts = await conn.fetch(query % hoursAhead, wardFilter)
            
            return {
                totalalerts: len(alerts),
                ward: ward,
                hoursahead: hoursAhead,
                timestamp: datetime.now(),
                alerts: [dict(alert) for alert in alerts]
            }
            
    except Exception as e:
        logger.error(f"❌ Medication alerts error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get medication alerts")

@router.get("/therapy-schedule")
async def getTherapySchedule(
    ward: Optional[str] = Query(None, description="Ward filter"),
    date: Optional[str] = Query(None, description="Date filter (YYYY-MM-DD)")
):
    """
    Get therapy session schedule for nursing coordination
    """
    try:
        targetDate = datetime.strptime(date, "%Y-%m-%d").date() if date else datetime.now().date()
        
        async with getDbConnection() as conn:
            query = """
                SELECT 
                    ts.id, ts.patientId, ts.scheduleddate, ts.status, ts.sessionnumber,
                    t.type as therapytype, t.description, ts.performedBy,
                    p.firstName, p.lastName, p.roomNumber, p.bedNumber
                FROM therapysessions ts
                JOIN therapy t ON ts.therapyid::text = t.id::text
                JOIN patients p ON ts.patientId = p.id
                WHERE DATE(ts.scheduleddate) = $1
                AND p.status = 'active'
                AND ($2 IS NULL OR p.roomNumber LIKE $2)
                ORDER BY ts.scheduleddate, p.roomNumber, p.bedNumber
            """
            
            wardFilter = f"{ward}%" if ward else None
            sessions = await conn.fetch(query, targetDate, wardFilter)
            
            return {
                date: targetDate.isoformat(),
                ward: ward,
                totalsessions: len(sessions),
                timestamp: datetime.now(),
                sessions: [dict(session) for session in sessions]
            }
            
    except Exception as e:
        logger.error(f"❌ Therapy schedule error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get therapy schedule")

@router.post("/medication-administration/{administrationId}/administer")
async def administerMedication(
    administrationId: str,
    administeredBy: str,
    notes: Optional[str] = None
):
    """
    Mark medication as administered
    """
    try:
        async with getDbConnection() as conn:
            # Check if administration exists
            checkQuery = """
                SELECT ma.*, p.firstName, p.lastName, m.name as medicationname
                FROM medicationadministrations ma
                JOIN patients p ON ma.patientId = p.id
                JOIN medications m ON ma.medicationId::text = m.id::text
                WHERE ma.id = $1
            """
            administration = await conn.fetchrow(checkQuery, administrationId)
            
            if not administration:
                raise HTTPException(status_code=404, detail="Medication administration not found")
            
            # Update administration status
            updateQuery = """
                UPDATE medicationadministrations 
                SET status = 'administered', 
                    "administeredAt" = NOW(),
                    "administeredBy" = $1,
                    notes = $2,
                    "updatedAt" = NOW()
                WHERE id = $3
            """
            await conn.execute(updateQuery, administeredBy, notes, administrationId)
            
            # Log audit event
            await logAuditEvent(
                userId=administeredBy,
                action="MEDICATION_ADMINISTERED",
                resourceType="MEDICATION_ADMINISTRATION",
                resourceId=administrationId,
                details=f"Administered {administration['medicationname']} to {administration.get('firstName', '')} {administration.get('lastName', '')}"
            )
            
            logger.info(f"✅ Medication administered: {administrationId} by {administeredBy}")
            
            return {
                "message": "Medication administered successfully",
                "administrationid": administrationId,
                "administeredBy": administeredBy,
                "administeredAt": datetime.now().isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Administer medication error: {e}")
        raise HTTPException(status_code=500, detail="Failed to administer medication")

@router.post("/therapy-session/{sessionId}/complete")
async def completeTherapySession(
    sessionId: str,
    performedBy: str,
    sessionNotes: Optional[str] = None,
    duration: Optional[str] = None
):
    """
    Mark therapy session as completed
    """
    try:
        async with getDbConnection() as conn:
            # Check if session exists
            checkQuery = """
                SELECT ts.*, p.firstName, p.lastName, t.type, t.description
                FROM therapysessions ts
                JOIN patients p ON ts.patientId = p.id
                JOIN therapy t ON ts.therapyid::text = t.id::text
                WHERE ts.id = $1
            """
            session = await conn.fetchrow(checkQuery, sessionId)
            
            if not session:
                raise HTTPException(status_code=404, detail="Therapy session not found")
            
            # Update session status
            updateQuery = """
                UPDATE therapysessions 
                SET status = 'completed',
                    "completedAt" = NOW(),
                    "performedBy" = $1,
                    sessionnotes = $2,
                    duration = $3,
                    "updatedAt" = NOW()
                WHERE id = $4
            """
            await conn.execute(updateQuery, performedBy, sessionNotes, duration, sessionId)
            
            # Log audit event
            await logAuditEvent(
                userId=performedBy,
                action="THERAPY_SESSION_COMPLETED",
                resourceType="THERAPY_SESSION",
                resourceId=sessionId,
                details=f"Completed {session['type']} session for {session['firstName']} {session['lastName']}"
            )
            
            logger.info(f"✅ Therapy session completed: {sessionId} by {performedBy}")
            
            return {
                "message": "Therapy session completed successfully",
                sessionid: sessionId,
                "performedBy": performedBy,
                "completedAt": datetime.now()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Complete therapy session error: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete therapy session")