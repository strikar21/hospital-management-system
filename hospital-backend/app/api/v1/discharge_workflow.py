"""
Discharge workflow API endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
import logging
from pydantic import BaseModel

from ...core.database import getDbConnection
from ...services.audit import logAuditEvent

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/test")
async def testEndpoint():
    """Test endpoint to verify router is working"""
    return {"message": "Discharge workflow router is working!"}

class DischargeRequest(BaseModel):
    patientId: str
    dischargeReason: str
    dischargeNotes: str = ""
    requestedBy: str

@router.post("/doctor-request")
async def doctorRequestDischarge(dischargeRequest: DischargeRequest):
    """
    Doctor requests discharge for a patient
    """
    try:
        async with getDbConnection() as conn:
            # Start explicit transaction
            async with conn.transaction():
                # Verify patient exists and is active
                patient = await conn.fetchrow(
                    "SELECT * FROM patients WHERE id = $1 AND status = 'active'",
                    dischargeRequest.patientId
                )
                if not patient:
                    raise HTTPException(status_code=404, detail="Active patient not found")

                now = datetime.now()

                # Update patient discharge status to 'requested'
                logger.info(f"🔄 Updating discharge status for patient {dischargeRequest.patientId} to 'requested'")
                result = await conn.execute(
                    "UPDATE patients SET dischargeStatus = 'requested', updatedAt = $1 WHERE id = $2",
                    now, dischargeRequest.patientId
                )
                logger.info(f"✅ Database update result: {result}")

                # Verify the update worked within the same transaction
                checkResult = await conn.fetchrow(
                    'SELECT dischargeStatus FROM patients WHERE id = $1',
                    dischargeRequest.patientId
                )
                logger.info(f"🔍 Verification - discharge status is now: {checkResult['dischargeStatus'] if checkResult else 'NOT FOUND'}")

                if not checkResult or checkResult['dischargeStatus'] != 'requested':
                    raise Exception("Database update failed - status not changed")

            # Transaction is committed automatically here

            # Log audit event
            await logAuditEvent(
                userId=dischargeRequest.requestedBy,
                action="DISCHARGE_REQUESTED",
                resourceType="PATIENT",
                resourceId=dischargeRequest.patientId,
                details=f"Doctor requested discharge for patient {dischargeRequest.patientId}: {dischargeRequest.dischargeReason}. Notes: {dischargeRequest.dischargeNotes}"
            )

            logger.info(f"🏥 Doctor {dischargeRequest.requestedBy} requested discharge for patient {dischargeRequest.patientId}")
            return {
                "success": True,
                "message": "Discharge request submitted successfully",
                "patientId": dischargeRequest.patientId,
                "requestedBy": dischargeRequest.requestedBy,
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
async def adminApproveDischarge(approvalRequest: AdminApprovalRequest):
    """
    Hospital Administrator approves discharge request
    """
    try:
        async with getDbConnection() as conn:
            # Verify patient exists and has requested discharge
            patient = await conn.fetchrow(
                'SELECT * FROM patients WHERE id = $1 AND dischargeStatus = \'requested\'',
                approvalRequest.patientId
            )
            if not patient:
                raise HTTPException(status_code=404, detail="Patient with discharge request not found")

            now = datetime.now()

            # Update patient discharge status to 'adminApproved'
            await conn.execute(
                "UPDATE patients SET dischargeStatus = 'adminapproved', updatedAt = $1 WHERE id = $2",
                now, approvalRequest.patientId
            )

            # Log audit event
            await logAuditEvent(
                userId=approvalRequest.approvedBy,
                action="DISCHARGE_ADMIN_APPROVED",
                resourceType="PATIENT",
                resourceId=approvalRequest.patientId,
                details=f"Admin approved discharge for patient {approvalRequest.patientId}. Notes: {approvalRequest.approvalNotes}"
            )

            logger.info(f"✅ Admin {approvalRequest.approvedBy} approved discharge for patient {approvalRequest.patientId}")
            return {
                "success": True,
                "message": "Discharge approved by administrator",
                "patientId": approvalRequest.patientId,
                "approvedBy": approvalRequest.approvedBy,
                "status": "adminapproved"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Admin discharge approval error: {e}")
        raise HTTPException(status_code=500, detail="Failed to approve discharge request")

@router.post("/nurse-discharge")
async def nurseCompleteDischarge(
    patientId: str,
    nurseId: str = Query(..., description="Nurse ID completing discharge"),
    dischargeNotes: str = Query("", description="Final discharge notes")
):
    """
    Nurse completes the discharge process
    """
    try:
        async with getDbConnection() as conn:
            # Verify patient exists and has admin-approved discharge
            patient = await conn.fetchrow(
                'SELECT * FROM patients WHERE id = $1 AND dischargeStatus = \'adminapproved\'',
                patientId
            )
            if not patient:
                raise HTTPException(status_code=404, detail="Patient with admin-approved discharge not found")

            now = datetime.now()

            # Complete discharge: update status to 'discharged' and dischargerstatus to 'completed'
            await conn.execute(
                "UPDATE patients SET status = 'discharged', dischargeStatus = 'completed', dischargeDate = $1, updatedAt = $2 WHERE id = $3",
                now, now, patientId
            )

            # Unassign any devices
            await conn.execute(
                "UPDATE deviceassignments SET status = 'inactive', unassignedAt = $1 WHERE patientId = $2 AND status = 'active'",
                now, patientId
            )
            await conn.execute(
                'UPDATE devices SET assignedPatientId = NULL, status = \'available\' WHERE assignedPatientId = $1',
                patientId
            )

            # Log audit event
            await logAuditEvent(
                userId=nurseId,
                action="DISCHARGE_COMPLETED",
                resourceType="PATIENT",
                resourceId=patientId,
                details=f"Nurse completed discharge for patient {patientId}. Notes: {dischargeNotes}"
            )

            logger.info(f"✅ Patient {patientId} discharged by nurse {nurseId}")
            return {
                "success": True,
                "message": "Patient discharge completed",
                "patientId": patientId,
                "dischargedBy": nurseId,
                "dischargeDate": now.isoformat()
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Nurse discharge completion error: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete patient discharge")

@router.post("/nurse-approve")
async def nurseApproveDischarge(
    patientId: str,
    nurseId: str = Query(..., description="Nurse ID approving discharge"),
    dischargeNotes: str = Query("", description="Discharge notes")
):
    """
    Nurse approves discharge for a patient
    """
    try:
        async with getDbConnection() as conn:
            # Verify patient exists and is active
            patient = await conn.fetchrow(
                "SELECT * FROM patients WHERE id = $1 AND status = 'active'",
                patientId
            )
            if not patient:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            now = datetime.now()
            
            # Update patient status to discharged
            await conn.execute(
                "UPDATE patients SET status = 'discharged', dischargeDate = $1, updatedAt = $2 WHERE id = $3",
                now, now, patientId
            )
            
            # Unassign any devices
            await conn.execute(
                "UPDATE deviceassignments SET status = 'inactive', unassignedAt = $1 WHERE patientId = $2 AND status = 'active'",
                now, patientId
            )
            await conn.execute(
                'UPDATE devices SET assignedPatientId = NULL, status = \'available\' WHERE assignedPatientId = $1',
                patientId
            )
            
            # Log audit event
            await logAuditEvent(
                userId=nurseId,
                action="DISCHARGE_APPROVED",
                resourceType="PATIENT",
                resourceId=patientId,
                details=f"Nurse approved discharge for patient {patientId}. Notes: {dischargeNotes}"
            )

            logger.info(f"✅ Patient {patientId} discharged by nurse {nurseId}")
            return {
                "success": True,
                "message": "Patient discharge approved and completed",
                "patientId": patientId,
                "dischargedBy": nurseId,
                "dischargeDate": now.isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Nurse discharge approval error: {e}")
        raise HTTPException(status_code=500, detail="Failed to approve patient discharge")

@router.get("/pending")
async def getPendingDischarges(
    staffId: str = Query(..., description="Staff ID requesting pending discharges")
):
    """
    Get list of pending discharge requests (simplified - returns empty list for now)
    """
    try:
        # For now, return empty list since we're not maintaining a dischargeRequests table
        # In the future, this could query a proper dischargeRequests table
        logger.info(f"📋 Pending discharge requests requested by {staffId}")
        return []
            
    except Exception as e:
        logger.error(f"❌ Get pending discharges error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve pending discharge requests")