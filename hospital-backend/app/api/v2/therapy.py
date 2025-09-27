"""
Repository-Based Therapy API Endpoints
Clean implementation using TherapyService
"""

from fastapi import APIRouter, HTTPException
import logging

from ...services.service_factory import get_therapy_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/list")
async def list_therapy_sessions():
    """List all therapy sessions"""
    try:
        therapy_service = get_therapy_service()
        sessions = await therapy_service.get_all()

        logger.info(f"✅ Retrieved {len(sessions)} total therapy sessions")
        return {"therapySessions": sessions, "count": len(sessions)}

    except Exception as e:
        logger.error(f"❌ Error listing therapy sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patient/{patient_id}")
async def get_patient_therapy_sessions(patient_id: str):
    """Get all therapy sessions for a patient"""
    try:
        therapy_service = get_therapy_service()
        sessions = await therapy_service.get_by_patient_id(patient_id)

        logger.info(f"✅ Retrieved {len(sessions)} therapy sessions for patient {patient_id}")
        return {"therapySessions": sessions, "count": len(sessions)}

    except Exception as e:
        logger.error(f"❌ Error getting therapy sessions for patient {patient_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/patient/{patient_id}")
async def add_therapy_session(
    patient_id: str,
    session_data: dict
):
    """Add therapy session to patient"""
    try:
        therapy_service = get_therapy_service()

        session = await therapy_service.add_therapy_session(
            patient_id=patient_id,
            session_data=session_data,
            created_by='system'
        )

        if not session:
            raise HTTPException(status_code=400, detail="Failed to add therapy session")

        logger.info(f"✅ Added therapy session to patient {patient_id}")
        return session

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error adding therapy session to patient {patient_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/patient/{patient_id}/{session_id}/status")
async def update_therapy_session_status(
    patient_id: str,
    session_id: str,
    status_data: dict
):
    """Update therapy session status"""
    try:
        therapy_service = get_therapy_service()

        success = await therapy_service.update_therapy_session(
            patient_id=patient_id,
            session_id=session_id,
            status=status_data.get('status'),
            updated_by='system'
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to update therapy session")

        logger.info(f"✅ Updated therapy session {session_id} for patient {patient_id}")
        return {"success": True, "message": "Therapy session status updated successfully"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error updating therapy session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/patient/{patient_id}/{session_id}/complete")
async def complete_therapy_session(
    patient_id: str,
    session_id: str,
    completion_data: dict
):
    """Complete therapy session with notes"""
    try:
        therapy_service = get_therapy_service()

        success = await therapy_service.complete_therapy_session(
            patient_id=patient_id,
            session_id=session_id,
            notes=completion_data.get('notes'),
            completed_by='system'
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to complete therapy session")

        logger.info(f"✅ Completed therapy session {session_id} for patient {patient_id}")
        return {"success": True, "message": "Therapy session completed successfully"}

    except Exception as e:
        logger.error(f"❌ Error completing therapy session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patient/{patient_id}/active")
async def get_active_therapy_sessions(patient_id: str):
    """Get active therapy sessions for a patient"""
    try:
        therapy_service = get_therapy_service()
        sessions = await therapy_service.get_by_patient_id(patient_id)

        # Filter for active therapy sessions
        active_sessions = [session for session in sessions if session.get('status') in ['active', 'scheduled', 'inProgress']]

        logger.info(f"✅ Retrieved {len(active_sessions)} active therapy sessions for patient {patient_id}")
        return {"therapy": active_sessions, "count": len(active_sessions)}

    except Exception as e:
        logger.error(f"❌ Error getting active therapy sessions for patient {patient_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/patient/{patient_id}/add")
async def add_therapy_session_simplified(patient_id: str, session_data: dict):
    """Add therapy session to patient (simplified path for frontend)"""
    return await add_therapy_session(patient_id, session_data)


@router.put("/{session_id}/status")
async def update_therapy_status_simplified(session_id: str, status_data: dict):
    """Update therapy session status (simplified path for frontend)"""
    try:
        therapy_service = get_therapy_service()

        success = await therapy_service.update_therapy_session(
            patient_id=None,
            session_id=session_id,
            status=status_data.get('status'),
            updated_by=status_data.get('modifiedBy', 'system')
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to update therapy session")

        logger.info(f"✅ Updated therapy session {session_id} status")
        return {"success": True, "message": "Therapy session status updated successfully"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error updating therapy session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/complete")
async def complete_therapy_session_simplified(session_id: str, completion_data: dict):
    """Complete therapy session with notes (simplified path for frontend)"""
    try:
        therapy_service = get_therapy_service()

        success = await therapy_service.complete_therapy_session(
            patient_id=None,
            session_id=session_id,
            notes=completion_data.get('notes'),
            completed_by=completion_data.get('completedBy', 'system')
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to complete therapy session")

        logger.info(f"✅ Completed therapy session {session_id}")
        return {"success": True, "message": "Therapy session completed successfully"}

    except Exception as e:
        logger.error(f"❌ Error completing therapy session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types")
async def get_therapy_types():
    """Get available therapy types"""
    try:
        # Provide fallback therapy types since service method might not exist
        try:
            therapy_service = get_therapy_service()
            therapy_types = await therapy_service.get_therapy_types()

            logger.info(f"✅ Retrieved {len(therapy_types)} therapy types from service")
            return {"types": therapy_types, "count": len(therapy_types)}
        except (AttributeError, NotImplementedError):
            # Fallback to static therapy types
            therapy_types = [
                {"id": "physiotherapy", "name": "Physiotherapy", "category": "Physical Rehabilitation"},
                {"id": "occupational_therapy", "name": "Occupational Therapy", "category": "Functional Rehabilitation"},
                {"id": "speech_therapy", "name": "Speech Therapy", "category": "Communication"},
                {"id": "respiratory_therapy", "name": "Respiratory Therapy", "category": "Breathing"},
                {"id": "cardiac_rehab", "name": "Cardiac Rehabilitation", "category": "Heart Health"},
                {"id": "wound_care", "name": "Wound Care", "category": "Wound Management"},
                {"id": "pain_management", "name": "Pain Management", "category": "Pain Relief"},
                {"id": "mobility_therapy", "name": "Mobility Therapy", "category": "Movement"},
            ]

            logger.info(f"✅ Retrieved {len(therapy_types)} therapy types (fallback)")
            return {"types": therapy_types, "count": len(therapy_types)}

    except Exception as e:
        logger.error(f"❌ Error getting therapy types: {e}")
        raise HTTPException(status_code=500, detail=str(e))