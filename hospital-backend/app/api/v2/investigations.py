"""
Repository-Based Investigation API Endpoints
Clean implementation using InvestigationService
"""

from fastapi import APIRouter, HTTPException
import logging

from ...services.service_factory import get_investigation_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/list")
async def list_investigations():
    """List all investigations"""
    try:
        investigation_service = get_investigation_service()
        investigations = await investigation_service.get_all()

        logger.info(f"✅ Retrieved {len(investigations)} total investigations")
        return {"investigations": investigations, "count": len(investigations)}

    except Exception as e:
        logger.error(f"❌ Error listing investigations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patient/{patient_id}")
async def get_patient_investigations(patient_id: str):
    """Get all investigations for a patient"""
    try:
        investigation_service = get_investigation_service()
        investigations = await investigation_service.get_by_patient_id(patient_id)

        logger.info(f"✅ Retrieved {len(investigations)} investigations for patient {patient_id}")
        return {"investigations": investigations, "count": len(investigations)}

    except Exception as e:
        logger.error(f"❌ Error getting investigations for patient {patient_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/patient/{patient_id}")
async def add_investigation(
    patient_id: str,
    investigation_data: dict
):
    """Add investigation to patient"""
    try:
        investigation_service = get_investigation_service()

        investigation = await investigation_service.add_investigation(
            patient_id=patient_id,
            investigation_data=investigation_data,
            created_by='system'
        )

        if not investigation:
            raise HTTPException(status_code=400, detail="Failed to add investigation")

        logger.info(f"✅ Added investigation to patient {patient_id}")
        return investigation

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error adding investigation to patient {patient_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/patient/{patient_id}/{investigation_id}/status")
async def update_investigation_status(
    patient_id: str,
    investigation_id: str,
    status_data: dict
):
    """Update investigation status"""
    try:
        investigation_service = get_investigation_service()

        success = await investigation_service.update_investigation(
            patient_id=patient_id,
            investigation_id=investigation_id,
            status=status_data.get('status'),
            updated_by='system'
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to update investigation")

        logger.info(f"✅ Updated investigation {investigation_id} for patient {patient_id}")
        return {"success": True, "message": "Investigation status updated successfully"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error updating investigation {investigation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patient/{patient_id}/pending")
async def get_pending_investigations(patient_id: str):
    """Get pending investigations for a patient"""
    try:
        investigation_service = get_investigation_service()
        investigations = await investigation_service.get_by_patient_id(patient_id)

        # Filter for pending investigations
        pending_investigations = [inv for inv in investigations if inv.get('status') in ['pending', 'ordered', 'inProgress']]

        logger.info(f"✅ Retrieved {len(pending_investigations)} pending investigations for patient {patient_id}")
        return {"investigations": pending_investigations, "count": len(pending_investigations)}

    except Exception as e:
        logger.error(f"❌ Error getting pending investigations for patient {patient_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/patient/{patient_id}/add")
async def add_investigation_simplified(patient_id: str, investigation_data: dict):
    """Add investigation to patient (simplified path for frontend)"""
    return await add_investigation(patient_id, investigation_data)


@router.get("/types")
async def get_investigation_types():
    """Get available investigation types"""
    try:
        # Common investigation types for hospital management
        types = [
            {"id": "blood_test", "name": "Blood Test", "category": "Laboratory"},
            {"id": "urine_test", "name": "Urine Test", "category": "Laboratory"},
            {"id": "x_ray", "name": "X-Ray", "category": "Imaging"},
            {"id": "ct_scan", "name": "CT Scan", "category": "Imaging"},
            {"id": "mri", "name": "MRI", "category": "Imaging"},
            {"id": "ultrasound", "name": "Ultrasound", "category": "Imaging"},
            {"id": "ecg", "name": "ECG/EKG", "category": "Cardiac"},
            {"id": "echo", "name": "Echocardiogram", "category": "Cardiac"},
            {"id": "biopsy", "name": "Biopsy", "category": "Pathology"},
        ]

        logger.info(f"✅ Retrieved {len(types)} investigation types")
        return {"types": types, "count": len(types)}

    except Exception as e:
        logger.error(f"❌ Error getting investigation types: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{investigation_id}/status")
async def update_investigation_status_simplified(investigation_id: str, status_data: dict):
    """Update investigation status (simplified path for frontend)"""
    try:
        investigation_service = get_investigation_service()

        success = await investigation_service.update_investigation(
            patient_id=None,
            investigation_id=investigation_id,
            status=status_data.get('status'),
            updated_by=status_data.get('modifiedBy', 'system')
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to update investigation")

        logger.info(f"✅ Updated investigation {investigation_id} status")
        return {"success": True, "message": "Investigation status updated successfully"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error updating investigation {investigation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{investigation_id}/complete")
async def complete_investigation_simplified(investigation_id: str, completion_data: dict):
    """Complete investigation with results (simplified path for frontend)"""
    try:
        investigation_service = get_investigation_service()

        success = await investigation_service.complete_investigation(
            patient_id=None,
            investigation_id=investigation_id,
            results=completion_data.get('results'),
            completed_by=completion_data.get('completedBy', 'system')
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to complete investigation")

        logger.info(f"✅ Completed investigation {investigation_id}")
        return {"success": True, "message": "Investigation completed successfully"}

    except Exception as e:
        logger.error(f"❌ Error completing investigation {investigation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{investigation_id}/results")
async def update_investigation_results(investigation_id: str, results_data: dict):
    """Update investigation results"""
    try:
        investigation_service = get_investigation_service()

        success = await investigation_service.update_investigation_results(
            investigation_id=investigation_id,
            results=results_data.get('results'),
            updated_by=results_data.get('modifiedBy', 'system')
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to update investigation results")

        logger.info(f"✅ Updated investigation {investigation_id} results")
        return {"success": True, "message": "Investigation results updated successfully"}

    except Exception as e:
        logger.error(f"❌ Error updating investigation {investigation_id} results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/patient/{patient_id}/{investigation_id}/complete")
async def complete_investigation(
    patient_id: str,
    investigation_id: str,
    completion_data: dict
):
    """Complete investigation with results"""
    try:
        investigation_service = get_investigation_service()

        success = await investigation_service.complete_investigation(
            patient_id=patient_id,
            investigation_id=investigation_id,
            results=completion_data.get('results'),
            completed_by='system'
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to complete investigation")

        logger.info(f"✅ Completed investigation {investigation_id} for patient {patient_id}")
        return {"success": True, "message": "Investigation completed successfully"}

    except Exception as e:
        logger.error(f"❌ Error completing investigation {investigation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))