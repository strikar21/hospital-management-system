"""
Repository-Based Medication API Endpoints
Clean implementation using MedicationService
"""

from fastapi import APIRouter, HTTPException, Depends
import logging

from ...services.service_factory import get_medication_service
from ...validators.medical_validators import MedicationRequest, MedicationUpdate
from ...core.auth_dependencies import require_medical_staff
from ...core.errors import MedicationNotFoundError, ValidationError, DatabaseError
from ...models.api_response import create_list_response, create_success_response, create_operation_response

router = APIRouter(dependencies=[Depends(require_medical_staff)])
logger = logging.getLogger(__name__)


@router.get("/list")
async def list_medications():
    """List all medications"""
    try:
        medication_service = get_medication_service()
        medications = await medication_service.get_all()

        logger.info(f"✅ Retrieved {len(medications)} total medications")
        return create_list_response(
            data=medications,
            total=len(medications),
            message="Medications retrieved successfully"
        )

    except Exception as e:
        logger.error(f"❌ Error listing medications: {e}")
        raise DatabaseError(message="Failed to list medications", operation="list_medications")


@router.get("/patient/{patient_id}")
async def get_patient_medications(patient_id: str):
    """Get all medications for a patient"""
    try:
        medication_service = get_medication_service()
        medications = await medication_service.get_by_patient_id(patient_id)

        # Resolve staff names for modifiedBy and prescribedBy using utility
        from ...utils.staff_resolution import resolve_staff_names
        from ...core.database import getDbConnection

        async with getDbConnection() as conn:
            medications = await resolve_staff_names(
                conn=conn,
                records=medications,
                staff_fields=['prescribedBy', 'modifiedBy']
            )

        logger.info(f"✅ Retrieved {len(medications)} medications for patient {patient_id}")
        return create_list_response(
            data=medications,
            total=len(medications),
            message=f"Medications for patient {patient_id} retrieved successfully"
        )

    except Exception as e:
        logger.error(f"❌ Error getting medications for patient {patient_id}: {e}")
        raise DatabaseError(message="Failed to get patient medications", operation="get_patient_medications")


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
            raise ValidationError("Failed to add medication - invalid data or patient not found")

        logger.info(f"✅ Added medication '{medication.name}' to patient {patient_id}")
        return create_success_response(
            data=result,
            message=f"Medication '{medication.name}' added successfully"
        )

    except ValidationError:
        raise
    except ValueError as e:
        raise ValidationError(str(e))
    except Exception as e:
        logger.error(f"❌ Error adding medication to patient {patient_id}: {e}")
        raise DatabaseError(message="Failed to add medication", operation="add_medication")


@router.get("/patient/{patient_id}/active")
async def get_active_medications(patient_id: str):
    """Get active medications for a patient"""
    try:
        medication_service = get_medication_service()
        medications = await medication_service.get_by_patient_id(patient_id)

        # Filter for active medications
        active_medications = [med for med in medications if med.get('status') == 'active']

        logger.info(f"✅ Retrieved {len(active_medications)} active medications for patient {patient_id}")
        return create_list_response(
            data=active_medications,
            total=len(active_medications),
            message=f"Active medications for patient {patient_id} retrieved successfully"
        )

    except Exception as e:
        logger.error(f"❌ Error getting active medications for patient {patient_id}: {e}")
        raise DatabaseError(message="Failed to get active medications", operation="get_active_medications")


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
        return create_list_response(
            data=types,
            total=len(types),
            message="Medication types retrieved successfully"
        )

    except Exception as e:
        logger.error(f"❌ Error getting medication types: {e}")
        raise DatabaseError(message="Failed to get medication types", operation="get_medication_types")


@router.put("/{medication_id}/status")
async def update_medication_status_simplified(medication_id: str, status_data: dict):
    """Update medication status (simplified path for frontend)"""
    try:
        medication_service = get_medication_service()

        # Validate status field
        if not status_data.get('status'):
            raise ValidationError("Status is required", field="status")

        # Try to find the medication first to get patient_id
        # This is a simplified approach - in production, you might want to store patient context
        success = await medication_service.update_medication(
            patient_id=None,  # Service should handle this internally
            medication_id=medication_id,
            status=status_data.get('status'),
            updated_by=status_data.get('modifiedBy', 'system')
        )

        if not success:
            raise MedicationNotFoundError(medication_id=medication_id)

        logger.info(f"✅ Updated medication {medication_id} status")
        return create_operation_response("Medication status updated successfully")

    except (ValidationError, MedicationNotFoundError):
        raise
    except ValueError as e:
        raise ValidationError(str(e))
    except Exception as e:
        logger.error(f"❌ Error updating medication {medication_id}: {e}")
        raise DatabaseError(message="Failed to update medication status", operation="update_medication_status_simplified")


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
            raise MedicationNotFoundError(medication_id=medication_id)

        logger.info(f"✅ Completed medication administration {medication_id}")
        return create_operation_response("Medication administration recorded successfully")

    except (ValidationError, MedicationNotFoundError):
        raise
    except ValueError as e:
        raise ValidationError(str(e))
    except Exception as e:
        logger.error(f"❌ Error completing medication {medication_id}: {e}")
        raise DatabaseError(message="Failed to complete medication", operation="complete_medication")


@router.put("/patient/{patient_id}/{medication_id}/status")
async def update_medication_status(
    patient_id: str,
    medication_id: str,
    status_data: dict
):
    """Update medication status"""
    try:
        medication_service = get_medication_service()

        # Validate status field
        if not status_data.get('status'):
            raise ValidationError("Status is required", field="status")

        success = await medication_service.update_medication(
            patient_id=patient_id,
            medication_id=medication_id,
            status=status_data.get('status'),
            updated_by='system'
        )

        if not success:
            raise MedicationNotFoundError(medication_id=medication_id)

        logger.info(f"✅ Updated medication {medication_id} status for patient {patient_id}")
        return create_operation_response("Medication status updated successfully")

    except (ValidationError, MedicationNotFoundError):
        raise
    except ValueError as e:
        raise ValidationError(str(e))
    except Exception as e:
        logger.error(f"❌ Error updating medication {medication_id}: {e}")
        raise DatabaseError(message="Failed to update medication status", operation="update_medication_status")
