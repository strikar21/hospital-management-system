"""
Atomic Medical API Endpoints
Provides failproof atomic operations for all medical actions
Replaces individual service calls with single atomic operations
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uuid
import logging
from datetime import datetime

from ...services.medical_action_service import (
    MedicalActionService,
    medical_action_service,
    add_medication_atomic,
    add_investigation_atomic,
    add_therapy_atomic,
    add_note_atomic
)
from ...validators.medical_validators import MedicationRequest
from ...validators.investigation_validators import InvestigationRequest as InvestigationRequestValidated
from ...validators.therapy_validators import TherapyRequest as TherapyRequestValidated
from ...core.auth_dependencies import require_doctor, require_medical_staff, get_current_user

# Rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/atomic", tags=["Atomic Medical Operations"], dependencies=[Depends(require_medical_staff)])
logger = logging.getLogger(__name__)


def validate_performed_by(performedBy: str, current_user: dict) -> None:
    """
    Validate that performedBy matches authenticated user.
    Prevents audit trail forgery where Doctor A could act as Doctor B.

    FIXED: Added security validation for HIPAA/DPDP Act 2023 compliance

    Args:
        performedBy: User ID claiming to perform the action
        current_user: Authenticated user from JWT token

    Raises:
        HTTPException: 403 if performedBy doesn't match authenticated user
    """
    if performedBy == "SYSTEM":
        return  # System actions allowed (e.g., automated processes)

    if performedBy != current_user.get("id"):
        raise HTTPException(
            status_code=403,
            detail=f"Cannot perform action as {performedBy}. Authenticated as {current_user.get('id')}. "
                   f"Audit trail forgery is not permitted."
        )


# Use validated request models from validators module
# MedicationRequest imported from validators
# InvestigationRequest and TherapyRequest below are for backward compatibility

class InvestigationRequest(InvestigationRequestValidated):
    """Investigation request with validation - extends validated base"""
    # Map 'name' to 'testName' for backward compatibility
    name: Optional[str] = None

    def dict(self, **kwargs):
        d = super().dict(**kwargs)
        # Handle name -> testName mapping
        if 'name' in d and d['name']:
            d['testName'] = d.pop('name')
        return d


class TherapyRequest(TherapyRequestValidated):
    """Therapy request with validation - extends validated base"""
    # Map 'type' to 'therapyType' for backward compatibility
    type: Optional[str] = None

    def dict(self, **kwargs):
        d = super().dict(**kwargs)
        # Handle type -> therapyType mapping
        if 'type' in d and d['type']:
            d['therapyType'] = d.pop('type')
        return d


class NoteRequest(BaseModel):
    content: Optional[str] = None
    comment: Optional[str] = None  # Support both field names
    authorName: Optional[str] = None
    commentedBy: Optional[str] = None  # Support both field names


class MedicationAdministrationRequest(BaseModel):
    administeredBy: str
    notes: Optional[str] = None


class TherapySessionRequest(BaseModel):
    therapyId: str
    duration: int  # minutes
    notes: str
    performedBy: str


class AlertAcknowledgmentRequest(BaseModel):
    alertId: str
    acknowledgedBy: str


class InvestigationCompletionRequest(BaseModel):
    investigationId: str
    results: str
    completedBy: str


class MedicationStatusChangeRequest(BaseModel):
    medicationId: Optional[str] = None  # Optional - already in URL path
    status: str
    changedBy: str


class AtomicResponse(BaseModel):
    success: bool
    medicalRecord: Dict[str, Any]
    caseEntry: Dict[str, Any]
    actionType: str
    transactionId: str
    message: str


@router.post("/patients/{patient_id}/medications", response_model=AtomicResponse)
@limiter.limit("30/minute")
async def add_medication_atomic_endpoint(
    request: Request,
    patient_id: str,
    medication: MedicationRequest,
    performedBy: str = "SYSTEM",  # Keep for backward compatibility
    current_user: dict = Depends(require_doctor)  # Only doctors can prescribe
) -> AtomicResponse:
    """
    Add medication atomically with automatic case entry creation

    This single endpoint replaces:
    1. POST /medications (medical action)
    2. POST /case-entries (case sheet update)
    3. Frontend state updates

    Everything happens in one atomic transaction or fails completely.

    RBAC: Requires doctor role. Must prescribe as themselves.
    """
    try:
        logger.info(f"Atomic medication request for patient {patient_id} by user {current_user.get('id')}")
        logger.debug(f"Raw medication object: {medication}")
        logger.debug(f"performedBy parameter: {performedBy}")

        # FIXED: Validate performedBy to prevent audit trail forgery
        validate_performed_by(performedBy, current_user)

        # Convert to dict for service
        medication_data = medication.dict(exclude_none=True)
        logger.debug(f"medication_data after dict conversion: {medication_data}")

        # RBAC validation: Doctor must prescribe as themselves
        prescriber_id = medication_data.get("prescribedBy")
        if prescriber_id and prescriber_id != current_user.get("id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot prescribe medication as another doctor. Prescribing as {prescriber_id} but authenticated as {current_user.get('id')}"
            )

        # Execute atomic operation
        result = await add_medication_atomic(patient_id, medication_data, performedBy)

        return AtomicResponse(
            success=True,
            medicalRecord=result['medical_record'],
            caseEntry=result['case_entry'],
            actionType=result['action_type'],
            transactionId=result['transaction_id'],
            message=f"Medication '{medication.name}' added successfully with case entry"
        )

    except HTTPException:
        # Re-raise HTTP exceptions (like 403 from validation) without modification
        raise
    except Exception as e:
        logger.error(f"Atomic medication failed for patient {patient_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add medication atomically: {str(e)}"
        )


@router.post("/patients/{patient_id}/investigations", response_model=AtomicResponse)
async def add_investigation_atomic_endpoint(
    patient_id: str,
    investigation: InvestigationRequest,
    performedBy: str = "SYSTEM",  # Keep for backward compatibility
    current_user: dict = Depends(require_doctor)  # Only doctors can order investigations
) -> AtomicResponse:
    """
    Add investigation atomically with automatic case entry creation

    This single endpoint replaces:
    1. POST /investigations (medical action)
    2. POST /case-entries (case sheet update)
    3. Frontend state updates

    Everything happens in one atomic transaction or fails completely.

    RBAC: Requires doctor role. Must order as themselves.
    """
    try:
        logger.info(f"Atomic investigation request for patient {patient_id} by user {current_user.get('id')}")

        # FIXED: Validate performedBy to prevent audit trail forgery
        validate_performed_by(performedBy, current_user)

        investigation_data = investigation.dict(exclude_none=True)

        # RBAC validation: Doctor must order investigation as themselves
        prescriber_id = investigation_data.get("prescribedBy")
        if prescriber_id and prescriber_id != current_user.get("id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot order investigation as another doctor. Ordering as {prescriber_id} but authenticated as {current_user.get('id')}"
            )

        result = await add_investigation_atomic(patient_id, investigation_data, performedBy)

        return AtomicResponse(
            success=True,
            medicalRecord=result['medical_record'],
            caseEntry=result['case_entry'],
            actionType=result['action_type'],
            transactionId=result['transaction_id'],
            message=f"Investigation '{investigation.testName}' ordered successfully with case entry"
        )

    except HTTPException:
        # Re-raise HTTP exceptions (like 403 from validation) without modification
        raise
    except Exception as e:
        logger.error(f"Atomic investigation failed for patient {patient_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add investigation atomically: {str(e)}"
        )


@router.post("/patients/{patient_id}/therapies", response_model=AtomicResponse)
async def add_therapy_atomic_endpoint(
    patient_id: str,
    therapy: TherapyRequest,
    performedBy: str = "SYSTEM",
    current_user: dict = Depends(require_medical_staff)  # FIXED: Added authentication
) -> AtomicResponse:
    """
    Add therapy atomically with automatic case entry creation

    This single endpoint replaces:
    1. POST /therapies (medical action)
    2. POST /case-entries (case sheet update)
    3. Frontend state updates

    Everything happens in one atomic transaction or fails completely.

    FIXED: Now requires authentication and validates performedBy
    """
    try:
        logger.info(f"Atomic therapy request for patient {patient_id} by user {current_user.get('id')}")

        # FIXED: Validate performedBy to prevent audit trail forgery
        validate_performed_by(performedBy, current_user)

        therapy_data = therapy.dict(exclude_none=True)

        result = await add_therapy_atomic(patient_id, therapy_data, performedBy)

        return AtomicResponse(
            success=True,
            medicalRecord=result['medical_record'],
            caseEntry=result['case_entry'],
            actionType=result['action_type'],
            transactionId=result['transaction_id'],
            message=f"Therapy '{therapy.type}' prescribed successfully with case entry"
        )

    except HTTPException:
        # Re-raise HTTP exceptions (like 403 from validation) without modification
        raise
    except Exception as e:
        logger.error(f"Atomic therapy failed for patient {patient_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add therapy atomically: {str(e)}"
        )


@router.post("/patients/{patient_id}/notes", response_model=AtomicResponse)
async def add_note_atomic_endpoint(
    patient_id: str,
    note: NoteRequest,
    performedBy: str = "SYSTEM",
    current_user: dict = Depends(require_medical_staff)  # FIXED: Added authentication
) -> AtomicResponse:
    """
    Add patient note atomically with automatic case entry creation

    This single endpoint replaces:
    1. POST /notes (medical action)
    2. POST /case-entries (case sheet update)
    3. Frontend state updates

    Everything happens in one atomic transaction or fails completely.

    FIXED: Now requires authentication and validates performedBy
    """
    try:
        logger.info(f"Atomic note request for patient {patient_id} by user {current_user.get('id')}")

        # FIXED: Validate performedBy to prevent audit trail forgery
        validate_performed_by(performedBy, current_user)

        note_data = note.dict(exclude_none=True)

        result = await add_note_atomic(patient_id, note_data, performedBy)

        return AtomicResponse(
            success=True,
            medicalRecord=result['medical_record'],
            caseEntry=result['case_entry'],
            actionType=result['action_type'],
            transactionId=result['transaction_id'],
            message="Patient note added successfully with case entry"
        )

    except HTTPException:
        # Re-raise HTTP exceptions (like 403 from validation) without modification
        raise
    except Exception as e:
        logger.error(f"Atomic note failed for patient {patient_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add note atomically: {str(e)}"
        )


@router.post("/patients/{patient_id}/medical-action")
async def execute_medical_action_endpoint(
    patient_id: str,
    action_type: str,
    action_data: Dict[str, Any],
    performedBy: str = "SYSTEM",
    idempotency_key: Optional[str] = None
) -> AtomicResponse:
    """
    Universal atomic medical action endpoint

    Supports any medical action type in a single endpoint.
    Useful for dynamic frontend operations.
    """
    try:
        logger.info(f"Universal atomic action '{action_type}' for patient {patient_id}")

        result = await medical_action_service.execute_medical_action(
            action_type, patient_id, action_data, performedBy, idempotency_key
        )

        return AtomicResponse(
            success=True,
            medicalRecord=result['medical_record'],
            caseEntry=result['case_entry'],
            actionType=result['action_type'],
            transactionId=result['transaction_id'],
            message=f"Medical action '{action_type}' completed successfully"
        )

    except Exception as e:
        logger.error(f"Universal atomic action failed for patient {patient_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute medical action atomically: {str(e)}"
        )


# Medication Administration - Atomic administration with tracking

@router.post("/patients/{patient_id}/medications/{medication_id}/administer")
@limiter.limit("50/minute")
async def administer_medication_atomic_endpoint(
    request: Request,
    patient_id: str,
    medication_id: str,
    admin_request: MedicationAdministrationRequest,
    current_user: dict = Depends(require_medical_staff)  # Doctor or Nurse can administer
) -> AtomicResponse:
    """
    Record medication administration atomically with automatic case entry creation

    This endpoint handles the critical medical action of medication administration:
    1. Creates medication administration record in database
    2. Updates medication status to 'administered'
    3. Creates case entry with administration details
    4. Everything happens in one atomic transaction

    RBAC: Requires medical staff (doctor or nurse). Must administer as themselves.
    """
    try:
        logger.info(f"Atomic medication administration for medication {medication_id}, patient {patient_id} by user {current_user.get('id')}")

        # RBAC validation: Must administer as themselves
        if admin_request.administeredBy != current_user.get("id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot administer medication as another staff member. Administering as {admin_request.administeredBy} but authenticated as {current_user.get('id')}"
            )

        administration_data = {
            'medication_id': medication_id,
            # Note: performedBy passed separately as 4th argument below (line 437)
            'notes': admin_request.notes
        }

        result = await medical_action_service.execute_medical_action(
            'medication_administration',
            patient_id,
            administration_data,
            admin_request.administeredBy  # Fixed: use camelCase from model
        )

        return AtomicResponse(
            success=True,
            medicalRecord=result['medical_record'],
            caseEntry=result['case_entry'],
            actionType=result['action_type'],
            transactionId=result['transaction_id'],
            message="Medication administered successfully with case entry"
        )

    except Exception as e:
        logger.error(f"Atomic medication administration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record medication administration: {str(e)}"
        )


@router.post("/patients/{patient_id}/therapies/{therapy_id}/sessions")
async def record_therapy_session_atomic_endpoint(
    patient_id: str,
    therapy_id: str,
    request: TherapySessionRequest,
    current_user: dict = Depends(require_medical_staff)  # Doctor or Nurse can record sessions
) -> AtomicResponse:
    """
    Record therapy session completion atomically with automatic case entry creation

    This endpoint handles the critical medical action of therapy session completion:
    1. Creates therapy session record in database
    2. Updates therapy status to show it has sessions
    3. Creates case entry with session details
    4. Everything happens in one atomic transaction

    RBAC: Requires medical staff (doctor or nurse). Must record as themselves.
    """
    try:
        logger.info(f"Atomic therapy session for therapy {therapy_id}, patient {patient_id} by user {current_user.get('id')}")

        # RBAC validation: Must record session as themselves
        if request.performedBy != current_user.get("id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot record therapy session as another staff member. Recording as {request.performedBy} but authenticated as {current_user.get('id')}"
            )

        session_data = {
            'therapy_id': therapy_id,
            'duration': request.duration,
            'notes': request.notes
        }

        result = await medical_action_service.execute_medical_action(
            'therapy_session',
            patient_id,
            session_data,
            request.performedBy
        )

        return AtomicResponse(
            success=True,
            medicalRecord=result['medical_record'],
            caseEntry=result['case_entry'],
            actionType=result['action_type'],
            transactionId=result['transaction_id'],
            message="Therapy session recorded successfully with case entry"
        )

    except Exception as e:
        logger.error(f"Atomic therapy session failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record therapy session: {str(e)}"
        )


# Status Update Endpoints - Atomic status changes with case entries

@router.put("/patients/{patient_id}/investigations/{investigation_id}/status")
async def update_investigation_status_atomic(
    patient_id: str,
    investigation_id: str,
    new_status: str,
    performedBy: str = "SYSTEM"
) -> AtomicResponse:
    """
    Update investigation status atomically with automatic case entry creation

    Eliminates the "change in 2-3 places" problem for status updates:
    1. Update investigation status
    2. Create case entry
    3. Frontend state updates

    Now everything happens in one atomic transaction.
    """
    try:
        logger.info(f"Atomic status update for investigation {investigation_id} to {new_status}")

        result = await medical_action_service.execute_medical_action(
            'investigation_status_update',
            patient_id,
            {
                'investigation_id': investigation_id,
                'new_status': new_status,
                'action': f'Investigation status changed to {new_status}'
            },
            performedBy
        )

        return AtomicResponse(
            success=True,
            medicalRecord=result['medical_record'],
            caseEntry=result['case_entry'],
            actionType=result['action_type'],
            transactionId=result['transaction_id'],
            message=f"Investigation status updated to {new_status} with case entry"
        )

    except Exception as e:
        logger.error(f"Atomic investigation status update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update investigation status atomically: {str(e)}"
        )


@router.put("/patients/{patient_id}/medications/{medication_id}/status")
async def update_medication_status_atomic(
    patient_id: str,
    medication_id: str,
    new_status: str,
    performedBy: str = "SYSTEM"
) -> AtomicResponse:
    """
    Update medication status atomically with automatic case entry creation
    """
    try:
        logger.info(f"Atomic status update for medication {medication_id} to {new_status}")

        result = await medical_action_service.execute_medical_action(
            'medication_status_update',
            patient_id,
            {
                'medication_id': medication_id,
                'new_status': new_status,
                'action': f'Medication status changed to {new_status}'
            },
            performedBy
        )

        return AtomicResponse(
            success=True,
            medicalRecord=result['medical_record'],
            caseEntry=result['case_entry'],
            actionType=result['action_type'],
            transactionId=result['transaction_id'],
            message=f"Medication status updated to {new_status} with case entry"
        )

    except Exception as e:
        logger.error(f"Atomic medication status update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update medication status atomically: {str(e)}"
        )


@router.put("/patients/{patient_id}/therapies/{therapy_id}/status")
async def update_therapy_status_atomic(
    patient_id: str,
    therapy_id: str,
    new_status: str,
    performedBy: str = "SYSTEM"
) -> AtomicResponse:
    """
    Update therapy status atomically with automatic case entry creation
    """
    try:
        logger.info(f"Atomic status update for therapy {therapy_id} to {new_status}")

        result = await medical_action_service.execute_medical_action(
            'therapy_status_update',
            patient_id,
            {
                'therapy_id': therapy_id,
                'new_status': new_status,
                'action': f'Therapy status changed to {new_status}'
            },
            performedBy
        )

        return AtomicResponse(
            success=True,
            medicalRecord=result['medical_record'],
            caseEntry=result['case_entry'],
            actionType=result['action_type'],
            transactionId=result['transaction_id'],
            message=f"Therapy status updated to {new_status} with case entry"
        )

    except Exception as e:
        logger.error(f"Atomic therapy status update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update therapy status atomically: {str(e)}"
        )


@router.get("/patients/{patient_id}/transaction-status/{transaction_id}")
async def get_transaction_status(patient_id: str, transaction_id: str):
    """
    Get status of atomic transaction
    Useful for monitoring and debugging
    """
    try:
        from ...core.database import getDbConnection

        async with getDbConnection() as conn:
            transaction = await conn.fetchrow("""
                SELECT "transactionId", "patientId", "operationType", status,
                       "startedAt", "completedAt", "errorMessage"
                FROM atomic_transactions
                WHERE "transactionId" = $1 AND "patientId" = $2
            """, transaction_id, patient_id)

            if not transaction:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Transaction not found"
                )

            return {
                "transaction_id": transaction['transaction_id'],
                "patient_id": transaction['patient_id'],
                "operation_type": transaction['operation_type'],
                "status": transaction['status'],
                "started_at": transaction['started_at'].isoformat() if transaction['started_at'] else None,
                "completed_at": transaction['completed_at'].isoformat() if transaction['completed_at'] else None,
                "error_message": transaction['error_message']
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get transaction status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get transaction status: {str(e)}"
        )


@router.post("/patients/{patient_id}/alerts/{alert_id}/acknowledge", response_model=AtomicResponse)
async def acknowledge_alert_atomic_endpoint(
    patient_id: str,
    alert_id: str,
    request: AlertAcknowledgmentRequest,
    current_user: dict = Depends(require_medical_staff)  # Doctor or Nurse can acknowledge
) -> AtomicResponse:
    """
    Acknowledge alert atomically with automatic case entry creation

    This endpoint handles the critical medical action of alert acknowledgment:
    1. Updates alert status to 'acknowledged' in database
    2. Sets performedBy and performedAt fields
    3. Creates case entry with acknowledgment details
    4. Everything happens in one atomic transaction

    RBAC: Requires medical staff (doctor or nurse). Must acknowledge as themselves.
    """
    try:
        logger.info(f"Atomic alert acknowledgment for alert {alert_id}, patient {patient_id} by user {current_user.get('id')}")

        # RBAC validation: Must acknowledge as themselves
        if request.acknowledgedBy != current_user.get("id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot acknowledge alert as another staff member. Acknowledging as {request.acknowledgedBy} but authenticated as {current_user.get('id')}"
            )

        acknowledgment_data = {
            'alertId': alert_id
        }

        result = await medical_action_service.execute_medical_action(
            'alert_acknowledgment',
            patient_id,
            acknowledgment_data,
            request.acknowledgedBy
        )

        return AtomicResponse(
            success=True,
            medicalRecord=result['medical_record'],
            caseEntry=result['case_entry'],
            actionType=result['action_type'],
            transactionId=result['transaction_id'],
            message=f"Alert acknowledged successfully by {request.acknowledgedBy}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to acknowledge alert: {str(e)}"
        )


@router.post("/patients/{patient_id}/investigations/{investigation_id}/complete", response_model=AtomicResponse)
async def complete_investigation_atomic_endpoint(
    patient_id: str,
    investigation_id: str,
    request: InvestigationCompletionRequest,
    current_user: dict = Depends(require_medical_staff)  # Doctor or Nurse can complete
) -> AtomicResponse:
    """
    Complete investigation atomically with automatic case entry creation

    This endpoint handles the critical medical action of investigation completion:
    1. Updates investigation status to 'completed' in database
    2. Sets results and completedAt fields
    3. Creates case entry with completion details
    4. Everything happens in one atomic transaction

    RBAC: Requires medical staff (doctor or nurse). Must complete as themselves.
    """
    try:
        logger.info(f"Atomic investigation completion for investigation {investigation_id}, patient {patient_id} by user {current_user.get('id')}")

        # RBAC validation: Must complete as themselves
        if request.completedBy != current_user.get("id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot complete investigation as another staff member. Completing as {request.completedBy} but authenticated as {current_user.get('id')}"
            )

        completion_data = {
            'investigation_id': investigation_id,
            'results': request.results
        }

        result = await medical_action_service.execute_medical_action(
            'investigation_completion',
            patient_id,
            completion_data,
            request.completedBy  # Fixed: use camelCase from model
        )

        return AtomicResponse(
            success=True,
            medicalRecord=result['medical_record'],
            caseEntry=result['case_entry'],
            actionType=result['action_type'],
            transactionId=result['transaction_id'],
            message=f"Investigation completed successfully by {request.completedBy}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete investigation {investigation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete investigation: {str(e)}"
        )


@router.post("/patients/{patient_id}/medications/{medication_id}/status", response_model=AtomicResponse)
async def update_medication_status_atomic_endpoint(
    patient_id: str,
    medication_id: str,
    request: MedicationStatusChangeRequest
):
    """
    Atomically update medication status and create case entry
    """
    logger.info(f"Atomic medication status change for medication {medication_id}, patient {patient_id}")

    try:
        medical_action_service = MedicalActionService()

        status_change_data = {
            'medication_id': medication_id,
            'status': request.status
        }

        result = await medical_action_service.execute_medical_action(
            'medication_status_change',
            patient_id,
            status_change_data,
            request.changedBy
        )

        return AtomicResponse(
            success=True,
            medicalRecord=result['medical_record'],
            caseEntry=result['case_entry'],
            actionType=result['action_type'],
            transactionId=result['transaction_id'],
            message=f"Medication status changed to {request.status} by {request.changedBy}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update medication status {medication_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update medication status: {str(e)}"
        )


@router.get("/health/atomic")
async def atomic_health_check():
    """
    Health check for atomic operations system
    """
    try:
        from ...core.database import getDbConnection

        async with getDbConnection() as conn:
            # Test basic connectivity
            await conn.fetchval("SELECT 1")

            # Check atomic operation tables exist
            tables_exist = await conn.fetchval("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_name IN ('medical_operations', 'atomic_transactions')
            """)

            # Check helper functions exist
            functions_exist = await conn.fetchval("""
                SELECT COUNT(*) FROM information_schema.routines
                WHERE routine_name IN ('lock_patient_for_atomic_operation', 'create_atomic_case_entry')
            """)

            return {
                "status": "healthy",
                "atomic_tables_available": tables_exist == 2,
                "helper_functions_available": functions_exist == 2,
                "database_connection": "ok",
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"Atomic health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }