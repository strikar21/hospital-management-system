"""
Therapy sessions tracking API endpoints
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
async def schedule_therapy_session(session_data: dict):
    """
    Schedule a therapy session
    """
    try:
        async with get_db_connection() as conn:
            # Verify therapy exists
            therapy_query = "SELECT * FROM therapy WHERE id = $1::text AND patientid = $2"
            therapy = await conn.fetchrow(therapy_query, 
                                        str(session_data['therapyId']), 
                                        session_data['patientId'])
            
            if not therapy:
                raise HTTPException(status_code=404, detail="Therapy not found")
            
            # Generate session ID
            session_id = str(uuid.uuid4())
            
            # Get next session number for this therapy
            session_count_query = """
                SELECT COUNT(*) FROM therapysessions 
                WHERE therapyid = $1::text AND patientid = $2
            """
            session_count = await conn.fetchval(session_count_query, 
                                              str(session_data['therapyId']), 
                                              session_data['patientId'])
            session_number = (session_count or 0) + 1
            
            query = """
                INSERT INTO therapysessions (
                    id, therapyid, patientid, sessionnumber, scheduleddate,
                    performedby, status, duration, createdat, updatedat
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id
            """
            
            scheduled_date = datetime.fromisoformat(session_data['scheduledDate'].replace('Z', '+00:00'))
            
            result = await conn.fetchrow(query,
                session_id,
                str(session_data['therapyId']),
                session_data['patientId'],
                session_number,
                scheduled_date,
                session_data.get('performedBy', ''),
                'scheduled',
                session_data.get('duration', therapy['duration']),
                datetime.now(),
                datetime.now()
            )
            
            # Log audit event
            await log_audit_event(
                user_id=session_data.get('scheduledBy', 'system'),
                action="THERAPY_SESSION_SCHEDULED",
                resource_type="THERAPY_SESSION",
                resource_id=session_id,
                details=f"Scheduled {therapy['type']} session #{session_number} for patient {session_data['patientId']}"
            )
            
            logger.info(f"✅ Scheduled therapy session: {session_id}")
            
            return {
                "message": "Therapy session scheduled successfully",
                "sessionId": session_id,
                "sessionNumber": session_number,
                "scheduledDate": scheduled_date
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Schedule therapy session error: {e}")
        raise HTTPException(status_code=500, detail="Failed to schedule therapy session")

@router.get("/patient/{patient_id}")
async def get_patient_therapy_sessions(
    patient_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    therapy_id: Optional[str] = Query(None, description="Filter by therapy ID"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)")
):
    """
    Get therapy sessions for a patient
    """
    try:
        async with get_db_connection() as conn:
            query = """
                SELECT 
                    ts.id, ts.therapyid, ts.patientid, ts.sessionnumber, 
                    ts.scheduleddate, ts.completedat, ts.performedby, 
                    ts.status, ts.duration, ts.sessionnotes,
                    t.type as therapytype, t.description, t.frequency
                FROM therapysessions ts
                JOIN therapy t ON ts.therapyid::text = t.id::text
                WHERE ts.patientid = $1
            """
            
            params = [patient_id]
            param_count = 1
            
            if status:
                param_count += 1
                query += f" AND ts.status = ${param_count}"
                params.append(status)
            
            if therapy_id:
                param_count += 1
                query += f" AND ts.therapyid = ${param_count}::text"
                params.append(therapy_id)
            
            if date_from:
                param_count += 1
                query += f" AND DATE(ts.scheduleddate) >= ${param_count}"
                params.append(date_from)
                
            if date_to:
                param_count += 1
                query += f" AND DATE(ts.scheduleddate) <= ${param_count}"
                params.append(date_to)
            
            query += " ORDER BY ts.scheduleddate DESC"
            
            rows = await conn.fetch(query, *params)
            
            sessions = []
            for row in rows:
                session_dict = dict(row)
                # Convert to camelCase for consistency
                session_formatted = {
                    "id": session_dict["id"],
                    "therapyId": session_dict["therapyid"],
                    "patientId": session_dict["patientid"],
                    "sessionNumber": session_dict["sessionnumber"],
                    "scheduledDate": session_dict["scheduleddate"],
                    "completedAt": session_dict["completedat"],
                    "performedBy": session_dict["performedby"],
                    "status": session_dict["status"],
                    "duration": session_dict["duration"],
                    "sessionNotes": session_dict["sessionnotes"],
                    "therapyType": session_dict["therapytype"],
                    "description": session_dict["description"],
                    "frequency": session_dict["frequency"]
                }
                sessions.append(session_formatted)
            
            logger.info(f"🏃 Retrieved {len(sessions)} therapy sessions for patient {patient_id}")
            return sessions
            
    except Exception as e:
        logger.error(f"❌ Get patient therapy sessions error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve therapy sessions")

@router.put("/{session_id}/complete")
async def complete_therapy_session(
    session_id: str,
    completion_data: dict
):
    """
    Mark therapy session as completed
    """
    try:
        async with get_db_connection() as conn:
            # Check if session exists
            check_query = """
                SELECT ts.*, t.type as therapytype, p.firstname, p.lastname
                FROM therapysessions ts
                JOIN therapy t ON ts.therapyid::text = t.id::text
                JOIN patients p ON ts.patientid = p.id
                WHERE ts.id = $1
            """
            session = await conn.fetchrow(check_query, session_id)
            
            if not session:
                raise HTTPException(status_code=404, detail="Therapy session not found")
            
            if session['status'] == 'completed':
                raise HTTPException(status_code=400, detail="Session already completed")
            
            # Update session
            update_query = """
                UPDATE therapysessions 
                SET status = 'completed',
                    completedat = $1,
                    performedby = $2,
                    sessionnotes = COALESCE($3, sessionnotes),
                    duration = COALESCE($4, duration),
                    updatedat = $1
                WHERE id = $5
            """
            
            now = datetime.now()
            await conn.execute(update_query,
                now,
                completion_data['performedBy'],
                completion_data.get('sessionNotes'),
                completion_data.get('duration'),
                session_id
            )
            
            # Log audit event
            await log_audit_event(
                user_id=completion_data['performedBy'],
                action="THERAPY_SESSION_COMPLETED",
                resource_type="THERAPY_SESSION",
                resource_id=session_id,
                details=f"Completed {session['therapytype']} session #{session['sessionnumber']} for {session['firstname']} {session['lastname']}"
            )
            
            logger.info(f"🏃 Therapy session completed: {session_id}")
            
            return {
                "message": "Therapy session completed successfully",
                "sessionId": session_id,
                "completedAt": now,
                "performedBy": completion_data['performedBy']
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Complete therapy session error: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete therapy session")

@router.put("/{session_id}/cancel")
async def cancel_therapy_session(
    session_id: str,
    cancellation_data: dict
):
    """
    Cancel a therapy session
    """
    try:
        async with get_db_connection() as conn:
            # Check if session exists
            check_query = "SELECT * FROM therapysessions WHERE id = $1"
            session = await conn.fetchrow(check_query, session_id)
            
            if not session:
                raise HTTPException(status_code=404, detail="Therapy session not found")
            
            if session['status'] not in ['scheduled', 'in_progress']:
                raise HTTPException(status_code=400, detail="Only scheduled or in-progress sessions can be cancelled")
            
            # Update session
            update_query = """
                UPDATE therapysessions 
                SET status = 'cancelled',
                    sessionnotes = COALESCE($1, sessionnotes) || '\nCancelled: ' || $2,
                    updatedat = $3
                WHERE id = $4
            """
            
            now = datetime.now()
            await conn.execute(update_query,
                session['sessionnotes'],
                cancellation_data.get('reason', 'No reason provided'),
                now,
                session_id
            )
            
            # Log audit event
            await log_audit_event(
                user_id=cancellation_data['cancelledBy'],
                action="THERAPY_SESSION_CANCELLED",
                resource_type="THERAPY_SESSION",
                resource_id=session_id,
                details=f"Cancelled therapy session: {cancellation_data.get('reason', 'No reason provided')}"
            )
            
            logger.info(f"🏃 Therapy session cancelled: {session_id}")
            
            return {
                "message": "Therapy session cancelled",
                "sessionId": session_id,
                "reason": cancellation_data.get('reason', 'No reason provided'),
                "cancelledBy": cancellation_data['cancelledBy']
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Cancel therapy session error: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel therapy session")

@router.get("/scheduled")
async def get_scheduled_sessions(
    date: Optional[str] = Query(None, description="Date filter (YYYY-MM-DD)"),
    ward: Optional[str] = Query(None, description="Filter by ward/room prefix"),
    therapy_type: Optional[str] = Query(None, description="Filter by therapy type")
):
    """
    Get scheduled therapy sessions
    """
    try:
        target_date = date if date else datetime.now().date()
        
        async with get_db_connection() as conn:
            query = """
                SELECT 
                    ts.id, ts.patientid, ts.scheduleddate, ts.status, ts.sessionnumber,
                    ts.performedby, ts.duration,
                    t.type as therapytype, t.description,
                    p.firstname, p.lastname, p.roomnumber, p.bednumber
                FROM therapysessions ts
                JOIN therapy t ON ts.therapyid::text = t.id::text
                JOIN patients p ON ts.patientid = p.id
                WHERE DATE(ts.scheduleddate) = $1
                AND p.status = 'active'
            """
            
            params = [target_date]
            param_count = 1
            
            if ward:
                param_count += 1
                query += f" AND p.roomnumber LIKE ${param_count}"
                params.append(f"{ward}%")
            
            if therapy_type:
                param_count += 1
                query += f" AND t.type = ${param_count}"
                params.append(therapy_type)
            
            query += " ORDER BY ts.scheduleddate, p.roomnumber, p.bednumber"
            
            rows = await conn.fetch(query, *params)
            
            sessions = []
            for row in rows:
                session_dict = dict(row)
                session_formatted = {
                    "id": session_dict["id"],
                    "patientId": session_dict["patientid"],
                    "scheduledDate": session_dict["scheduleddate"],
                    "status": session_dict["status"],
                    "sessionNumber": session_dict["sessionnumber"],
                    "performedBy": session_dict["performedby"],
                    "duration": session_dict["duration"],
                    "therapyType": session_dict["therapytype"],
                    "description": session_dict["description"],
                    "patientName": f"{session_dict['firstname']} {session_dict['lastname']}",
                    "roomNumber": session_dict["roomnumber"],
                    "bedNumber": session_dict["bednumber"]
                }
                sessions.append(session_formatted)
            
            logger.info(f"🏃 Retrieved {len(sessions)} scheduled therapy sessions for {target_date}")
            
            return {
                "date": str(target_date),
                "totalSessions": len(sessions),
                "sessions": sessions
            }
            
    except Exception as e:
        logger.error(f"❌ Get scheduled sessions error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve scheduled sessions")

@router.put("/{session_id}/start")
async def start_therapy_session(
    session_id: str,
    start_data: dict
):
    """
    Mark therapy session as started/in progress
    """
    try:
        async with get_db_connection() as conn:
            # Check if session exists
            check_query = "SELECT * FROM therapysessions WHERE id = $1"
            session = await conn.fetchrow(check_query, session_id)
            
            if not session:
                raise HTTPException(status_code=404, detail="Therapy session not found")
            
            if session['status'] != 'scheduled':
                raise HTTPException(status_code=400, detail="Only scheduled sessions can be started")
            
            # Update session
            update_query = """
                UPDATE therapysessions 
                SET status = 'in_progress',
                    performedby = $1,
                    updatedat = $2
                WHERE id = $3
            """
            
            now = datetime.now()
            await conn.execute(update_query,
                start_data['performedBy'],
                now,
                session_id
            )
            
            # Log audit event
            await log_audit_event(
                user_id=start_data['performedBy'],
                action="THERAPY_SESSION_STARTED",
                resource_type="THERAPY_SESSION",
                resource_id=session_id,
                details=f"Started therapy session {session_id}"
            )
            
            logger.info(f"🏃 Therapy session started: {session_id}")
            
            return {
                "message": "Therapy session started",
                "sessionId": session_id,
                "status": "in_progress",
                "performedBy": start_data['performedBy']
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Start therapy session error: {e}")
        raise HTTPException(status_code=500, detail="Failed to start therapy session")