"""
Repository-Based Medication API Endpoints
Clean implementation using MedicationService
"""

from fastapi import APIRouter, HTTPException
import logging

from ...services.service_factory import get_medication_service
from ...validators.medical_validators import MedicationRequest, MedicationUpdate

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/list")
async def list_medications():
    """List all medications"""
    try:
        medication_service = get_medication_service()
        medications = await medication_service.get_all()

        logger.info(f"✅ Retrieved {len(medications)} total medications")
        return {"medications": medications, "count": len(medications)}

    except Exception as e:
        logger.error(f"❌ Error listing medications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patient/{patient_id}")
async def get_patient_medications(patient_id: str):
    """Get all medications for a patient"""
    try:
        medication_service = get_medication_service()
        medications = await medication_service.get_by_patient_id(patient_id)

        logger.info(f"✅ Retrieved {len(medications)} medications for patient {patient_id}")
        return {"medications": medications, "count": len(medications)}

    except Exception as e:
        logger.error(f"❌ Error getting medications for patient {patient_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/patient/{patient_id}")
async def add_medication(
    patient_id: str,
    medication: MedicationRequest
):
    """Add medication to patient with comprehensive validation"""
    try:
        medication_service = get_medication_service()

        # Convert validated Pydantic model to dict
        medication_data = medication.dict(exclude_none=False)

        result = await medication_service.add_medication(
            patient_id=patient_id,
            medication_data=medication_data,
            created_by=medication.prescribedBy
        )

        if not result:
            raise HTTPException(status_code=400, detail="Failed to add medication")

        logger.info(f"✅ Added medication '{medication.name}' to patient {patient_id}")
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error adding medication to patient {patient_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patient/{patient_id}/active")
async def get_active_medications(patient_id: str):
    """Get active medications for a patient"""
    try:
        medication_service = get_medication_service()
        medications = await medication_service.get_by_patient_id(patient_id)

        # Filter for active medications
        active_medications = [med for med in medications if med.get('status') == 'active']

        logger.info(f"✅ Retrieved {len(active_medications)} active medications for patient {patient_id}")
        return {"medications": active_medications, "count": len(active_medications)}

    except Exception as e:
        logger.error(f"❌ Error getting active medications for patient {patient_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/patient/{patient_id}/add")
async def add_medication_simplified(patient_id: str, medication: MedicationRequest):
    """Add medication to patient (simplified path for frontend with validation)"""
    return await add_medication(patient_id, medication)


@router.get("/types")
async def get_medication_types():
    """Get available medication types"""
    try:
        # Common medication types for hospital management
        types = [
            {"id": "analgesic", "name": "Analgesic", "category": "Pain Management"},
            {"id": "antibiotic", "name": "Antibiotic", "category": "Anti-Infection"},
            {"id": "anticoagulant", "name": "Anticoagulant", "category": "Blood Thinner"},
            {"id": "antihypertensive", "name": "Antihypertensive", "category": "Blood Pressure"},
            {"id": "diuretic", "name": "Diuretic", "category": "Fluid Management"},
            {"id": "insulin", "name": "Insulin", "category": "Diabetes Management"},
            {"id": "sedative", "name": "Sedative", "category": "Anxiety/Sleep"},
            {"id": "steroid", "name": "Steroid", "category": "Anti-Inflammatory"},
        ]

        logger.info(f"✅ Retrieved {len(types)} medication types")
        return {"types": types, "count": len(types)}

    except Exception as e:
        logger.error(f"❌ Error getting medication types: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{medication_id}/status")
async def update_medication_status_simplified(medication_id: str, status_data: dict):
    """Update medication status (simplified path for frontend)"""
    try:
        medication_service = get_medication_service()

        # Try to find the medication first to get patient_id
        # This is a simplified approach - in production, you might want to store patient context
        success = await medication_service.update_medication(
            patient_id=None,  # Service should handle this internally
            medication_id=medication_id,
            status=status_data.get('status'),
            updated_by=status_data.get('modifiedBy', 'system')
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to update medication")

        logger.info(f"✅ Updated medication {medication_id} status")
        return {"success": True, "message": "Medication status updated successfully"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error updating medication {medication_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{medication_id}/complete")
async def complete_medication(medication_id: str, completion_data: dict):
    """Mark medication administration as complete"""
    try:
        medication_service = get_medication_service()

        success = await medication_service.update_medication(
            patient_id=None,
            medication_id=medication_id,
            status='administered',
            updated_by=completion_data.get('performedBy', 'system')
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to complete medication")

        logger.info(f"✅ Completed medication administration {medication_id}")
        return {"success": True, "message": "Medication administration recorded"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error completing medication {medication_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/patient/{patient_id}/{medication_id}/status")
async def update_medication_status(
    patient_id: str,
    medication_id: str,
    status_data: dict
):
    """Update medication status"""
    try:
        medication_service = get_medication_service()

        success = await medication_service.update_medication(
            patient_id=patient_id,
            medication_id=medication_id,
            status=status_data.get('status'),
            updated_by='system'
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to update medication")

        logger.info(f"✅ Updated medication {medication_id} status for patient {patient_id}")
        return {"success": True, "message": "Medication status updated successfully"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error updating medication {medication_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))# Trigger reload
