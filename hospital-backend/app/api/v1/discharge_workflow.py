"""
Discharge workflow API endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
import logging
from pydantic import BaseModel

from ...core.database import get_db_connection
from ...services.audit import log_audit_event

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify router is working"""
    return {"message": "Discharge workflow router is working!"}

class DischargeRequest(BaseModel):
    patientId: str
    dischargeReason: str
    dischargeNotes: str = ""
    requestedBy: str

@router.post("/doctor-request")
async def doctor_request_discharge(discharge_request: DischargeRequest):
    """
    Doctor requests discharge for a patient
    """
    try:
        async with get_db_connection() as conn:
            # Start explicit transaction
            async with conn.transaction():
                # Verify patient exists and is active
                patient = await conn.fetchrow(
                    "SELECT * FROM patients WHERE id = $1 AND status = 'active'",
                    discharge_request.patientId
                )
                if not patient:
                    raise HTTPException(status_code=404, detail="Active patient not found")

                now = datetime.now()

                # Update patient discharge status to 'requested'
                logger.info(f"🔄 Updating discharge status for patient {discharge_request.patientId} to 'requested'")
                result = await conn.execute(
                    "UPDATE patients SET dischargerstatus = 'requested', updatedat = $1 WHERE id = $2",
                    now, discharge_request.patientId
                )
                logger.info(f"✅ Database update result: {result}")

                # Verify the update worked within the same transaction
                check_result = await conn.fetchrow(
                    "SELECT dischargerstatus FROM patients WHERE id = $1",
                    discharge_request.patientId
                )
                logger.info(f"🔍 Verification - discharge status is now: {check_result['dischargerstatus'] if check_result else 'NOT FOUND'}")

                if not check_result or check_result['dischargerstatus'] != 'requested':
                    raise Exception("Database update failed - status not changed")

            # Transaction is committed automatically here

            # Log audit event
            await log_audit_event(
                user_id=discharge_request.requestedBy,
                action="DISCHARGE_REQUESTED",
                resource_type="PATIENT",
                resource_id=discharge_request.patientId,
                details=f"Doctor requested discharge for patient {discharge_request.patientId}: {discharge_request.dischargeReason}. Notes: {discharge_request.dischargeNotes}"
            )

            logger.info(f"🏥 Doctor {discharge_request.requestedBy} requested discharge for patient {discharge_request.patientId}")
            return {
                "success": True,
                "message": "Discharge request submitted successfully",
                "patientId": discharge_request.patientId,
                "requestedBy": discharge_request.requestedBy,
                "status": "requested"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Doctor discharge request error: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit discharge request")

class AdminApprovalRequest(BaseModel):
    patientId: str
    approvalNotes: str = ""
    approvedBy: str

@router.post("/admin-approval")
async def admin_approve_discharge(approval_request: AdminApprovalRequest):
    """
    Hospital Administrator approves discharge request
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists and has requested discharge
            patient = await conn.fetchrow(
                "SELECT * FROM patients WHERE id = $1 AND dischargerstatus = 'requested'",
                approval_request.patientId
            )
            if not patient:
                raise HTTPException(status_code=404, detail="Patient with discharge request not found")

            now = datetime.now()

            # Update patient discharge status to 'adminApproved'
            await conn.execute(
                "UPDATE patients SET dischargerstatus = 'adminapproved', updatedat = $1 WHERE id = $2",
                now, approval_request.patientId
            )

            # Log audit event
            await log_audit_event(
                user_id=approval_request.approvedBy,
                action="DISCHARGE_ADMIN_APPROVED",
                resource_type="PATIENT",
                resource_id=approval_request.patientId,
                details=f"Admin approved discharge for patient {approval_request.patientId}. Notes: {approval_request.approvalNotes}"
            )

            logger.info(f"✅ Admin {approval_request.approvedBy} approved discharge for patient {approval_request.patientId}")
            return {
                "success": True,
                "message": "Discharge approved by administrator",
                "patientId": approval_request.patientId,
                "approvedBy": approval_request.approvedBy,
                "status": "adminapproved"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Admin discharge approval error: {e}")
        raise HTTPException(status_code=500, detail="Failed to approve discharge request")

@router.post("/nurse-discharge")
async def nurse_complete_discharge(
    patient_id: str,
    nurse_id: str = Query(..., description="Nurse ID completing discharge"),
    discharge_notes: str = Query("", description="Final discharge notes")
):
    """
    Nurse completes the discharge process
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists and has admin-approved discharge
            patient = await conn.fetchrow(
                "SELECT * FROM patients WHERE id = $1 AND dischargerstatus = 'adminapproved'",
                patient_id
            )
            if not patient:
                raise HTTPException(status_code=404, detail="Patient with admin-approved discharge not found")

            now = datetime.now()

            # Complete discharge: update status to 'discharged' and dischargerstatus to 'completed'
            await conn.execute(
                "UPDATE patients SET status = 'discharged', dischargerstatus = 'completed', dischargedate = $1, updatedat = $2 WHERE id = $3",
                now, now, patient_id
            )

            # Unassign any devices
            await conn.execute(
                "UPDATE deviceassignments SET status = 'inactive', unassignedat = $1 WHERE patientid = $2 AND status = 'active'",
                now, patient_id
            )
            await conn.execute(
                "UPDATE devices SET assignedpatientid = NULL, status = 'available' WHERE assignedpatientid = $1",
                patient_id
            )

            # Log audit event
            await log_audit_event(
                user_id=nurse_id,
                action="DISCHARGE_COMPLETED",
                resource_type="PATIENT",
                resource_id=patient_id,
                details=f"Nurse completed discharge for patient {patient_id}. Notes: {discharge_notes}"
            )

            logger.info(f"✅ Patient {patient_id} discharged by nurse {nurse_id}")
            return {
                "success": True,
                "message": "Patient discharge completed",
                "patientId": patient_id,
                "dischargedBy": nurse_id,
                "dischargeDate": now.isoformat()
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Nurse discharge completion error: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete patient discharge")

@router.post("/nurse-approve")
async def nurse_approve_discharge(
    patient_id: str,
    nurse_id: str = Query(..., description="Nurse ID approving discharge"),
    discharge_notes: str = Query("", description="Discharge notes")
):
    """
    Nurse approves discharge for a patient
    """
    try:
        async with get_db_connection() as conn:
            # Verify patient exists and is active
            patient = await conn.fetchrow(
                "SELECT * FROM patients WHERE id = $1 AND status = 'active'",
                patient_id
            )
            if not patient:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            now = datetime.now()
            
            # Update patient status to discharged
            await conn.execute(
                "UPDATE patients SET status = 'discharged', dischargedate = $1, updatedat = $2 WHERE id = $3",
                now, now, patient_id
            )
            
            # Unassign any devices
            await conn.execute(
                "UPDATE deviceassignments SET status = 'inactive', unassignedat = $1 WHERE patientid = $2 AND status = 'active'",
                now, patient_id
            )
            await conn.execute(
                "UPDATE devices SET assignedpatientid = NULL, status = 'available' WHERE assignedpatientid = $1",
                patient_id
            )
            
            # Log audit event
            await log_audit_event(
                user_id=nurse_id,
                action="DISCHARGE_APPROVED",
                resource_type="PATIENT", 
                resource_id=patient_id,
                details=f"Nurse approved discharge for patient {patient_id}. Notes: {discharge_notes}"
            )
            
            logger.info(f"✅ Patient {patient_id} discharged by nurse {nurse_id}")
            return {
                "success": True,
                "message": "Patient discharge approved and completed",
                "patientId": patient_id,
                "dischargedBy": nurse_id,
                "dischargeDate": now.isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Nurse discharge approval error: {e}")
        raise HTTPException(status_code=500, detail="Failed to approve patient discharge")

@router.get("/pending")
async def get_pending_discharges(
    staff_id: str = Query(..., description="Staff ID requesting pending discharges")
):
    """
    Get list of pending discharge requests (simplified - returns empty list for now)
    """
    try:
        # For now, return empty list since we're not maintaining a discharge_requests table
        # In the future, this could query a proper discharge_requests table
        logger.info(f"📋 Pending discharge requests requested by {staff_id}")
        return []
            
    except Exception as e:
        logger.error(f"❌ Get pending discharges error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve pending discharge requests")