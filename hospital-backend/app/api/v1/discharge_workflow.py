"""
Discharge workflow API endpoints
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from datetime import datetime
import logging
from pydantic import BaseModel

from ...core.database import getDbConnection
from ...services.audit import logAuditEvent
from ...core.auth_dependencies import require_doctor, require_admin, require_nurse, get_current_user, require_any_staff

router = APIRouter(dependencies=[Depends(require_any_staff)])
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
async def doctorRequestDischarge(
    dischargeRequest: DischargeRequest,
    current_user: dict = Depends(require_doctor)  # Only doctors can request discharge
):
    """
    Doctor requests discharge for a patient

    RBAC: Requires doctor role. Must request as themselves.
    """
    try:
        # RBAC validation: Doctor must request as themselves
        if dischargeRequest.requestedBy != current_user.get("id"):
            raise HTTPException(
                status_code=403,
                detail=f"Cannot request discharge as another doctor. Requesting as {dischargeRequest.requestedBy} but authenticated as {current_user.get('id')}"
            )

        async with getDbConnection() as conn:
            # Start explicit transaction
            async with conn.transaction():
                # Verify patient exists and is active
                patient = await conn.fetchrow(
                    "SELECT * FROM patients WHERE id = $1",
                    dischargeRequest.patientId
                )
                if not patient:
                    raise HTTPException(status_code=404, detail="Patient not found")

                # Check if patient already discharged
                if patient['status'] == 'discharged':
                    raise HTTPException(
                        status_code=400,
                        detail=f"Patient {dischargeRequest.patientId} is already discharged"
                    )

                # Check if not active
                if patient['status'] != 'active':
                    raise HTTPException(
                        status_code=400,
                        detail=f"Patient status is '{patient['status']}', can only discharge active patients"
                    )

                now = datetime.now()

                # Update patient discharge status to 'requested'
                logger.info(f"🔄 Updating discharge status for patient {dischargeRequest.patientId} to 'requested'")
                result = await conn.execute(
                    'UPDATE patients SET "dischargeStatus" = \'requested\', "updatedAt" = $1 WHERE id = $2',
                    now, dischargeRequest.patientId
                )
                logger.info(f"✅ Database update result: {result}")

                # Verify the update worked within the same transaction
                checkResult = await conn.fetchrow(
                    'SELECT "dischargeStatus" FROM patients WHERE id = $1',
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
async def adminApproveDischarge(
    approvalRequest: AdminApprovalRequest,
    current_user: dict = Depends(require_admin)  # Only admin can approve discharge
):
    """
    Hospital Administrator approves discharge request

    RBAC: Requires administrator role. Must approve as themselves.
    """
    # RBAC validation: Admin must approve as themselves
    if approvalRequest.approvedBy != current_user.get("id"):
        raise HTTPException(
            status_code=403,
            detail=f"Cannot approve discharge as another admin. Approving as {approvalRequest.approvedBy} but authenticated as {current_user.get('id')}"
        )
    try:
        async with getDbConnection() as conn:
            # Verify patient exists and has requested discharge
            patient = await conn.fetchrow(
                'SELECT * FROM patients WHERE id = $1 AND "dischargeStatus" = \'requested\'',
                approvalRequest.patientId
            )
            if not patient:
                raise HTTPException(status_code=404, detail="Patient with discharge request not found")

            now = datetime.now()

            # Update patient discharge status to 'adminApproved'
            await conn.execute(
                'UPDATE patients SET "dischargeStatus" = \'adminapproved\', "updatedAt" = $1 WHERE id = $2',
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
    dischargeNotes: str = Query("", description="Final discharge notes"),
    current_user: dict = Depends(require_nurse)  # Only nurse can complete discharge
):
    """
    Nurse completes the discharge process

    RBAC: Requires nurse role. Must complete as themselves.
    """
    try:
        # RBAC validation: Nurse must complete discharge as themselves
        if nurseId != current_user.get("id"):
            raise HTTPException(
                status_code=403,
                detail=f"Cannot complete discharge as another nurse. Completing as {nurseId} but authenticated as {current_user.get('id')}"
            )

        async with getDbConnection() as conn:
            # Start explicit transaction for atomic operations
            async with conn.transaction():
                # Verify patient exists
                patient = await conn.fetchrow(
                    'SELECT * FROM patients WHERE id = $1',
                    patientId
                )
                if not patient:
                    raise HTTPException(status_code=404, detail="Patient not found")

                # Check if already discharged
                if patient['status'] == 'discharged':
                    raise HTTPException(
                        status_code=400,
                        detail=f"Patient {patientId} is already discharged at {patient.get('dischargeDate', 'unknown time')}"
                    )

                # Check if discharge has been admin-approved
                if patient['dischargeStatus'] != 'adminapproved':
                    raise HTTPException(
                        status_code=400,
                        detail=f"Patient discharge not admin-approved. Current status: {patient.get('dischargeStatus', 'none')}"
                    )

                now = datetime.now()

                # Get assigned device ID before clearing it
                assignedDeviceId = patient.get('assignedDeviceId')
                deviceUnassigned = False

                # Complete discharge: update status to 'discharged' and dischargestatus to 'completed'
                await conn.execute(
                    'UPDATE patients SET status = \'discharged\', "dischargeStatus" = \'completed\', "dischargeDate" = $1, "assignedDeviceId" = NULL, "updatedAt" = $2 WHERE id = $3',
                    now, now, patientId
                )
                logger.info(f"✅ Patient {patientId} marked as discharged")

                # Unassign device if one was assigned
                if assignedDeviceId:
                    # Mark device assignment as inactive
                    await conn.execute(
                        'UPDATE deviceassignments SET status = \'inactive\', "unassignedAt" = $1 WHERE "deviceId" = $2 AND "patientId" = $3 AND status = \'active\'',
                        now, assignedDeviceId, patientId
                    )

                    # Update device status to available and clear patient assignment
                    await conn.execute(
                        'UPDATE devices SET "assignedPatientId" = NULL, status = \'available\' WHERE id = $1',
                        assignedDeviceId
                    )

                    deviceUnassigned = True
                    logger.info(f"📱 Device {assignedDeviceId} unassigned from patient {patientId} and marked as available")
                else:
                    logger.info(f"ℹ️ No device was assigned to patient {patientId}")

            # Log audit event
            await logAuditEvent(
                userId=nurseId,
                action="DISCHARGE_COMPLETED",
                resourceType="PATIENT",
                resourceId=patientId,
                details=f"Nurse completed discharge for patient {patientId}. Notes: {dischargeNotes}"
            )

            logger.info(f"✅ Patient {patientId} discharged by nurse {nurseId}")

            response = {
                "success": True,
                "message": "Patient discharge completed",
                "patientId": patientId,
                "dischargedBy": nurseId,
                "dischargeDate": now.isoformat(),
                "deviceUnassigned": deviceUnassigned
            }

            if deviceUnassigned and assignedDeviceId:
                response["deviceId"] = assignedDeviceId

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Nurse discharge completion error: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete patient discharge")

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

@router.get("/approved")
async def getApprovedDischarges(
    staffId: str = Query(..., description="Staff ID requesting approved discharges")
):
    """
    Get list of approved discharge requests waiting for nurse completion
    """
    try:
        async with getDbConnection() as conn:
            # Query patients with adminapproved discharge status
            patients = await conn.fetch(
                'SELECT id, "firstName", "lastName", "dischargeStatus" FROM patients WHERE "dischargeStatus" = \'adminapproved\' ORDER BY "updatedAt" DESC'
            )

            result = []
            for patient in patients:
                result.append({
                    "patientId": patient['id'],
                    "patientName": f"{patient['firstName']} {patient['lastName']}",
                    "status": patient['dischargeStatus']
                })

            logger.info(f"📋 Found {len(result)} approved discharge requests")
            return result

    except Exception as e:
        logger.error(f"❌ Get approved discharges error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve approved discharge requests")

# Frontend-compatible endpoints (aliases for existing functionality)

class SimpleDischargeRequest(BaseModel):
    patientId: str
    requestedBy: str
    reason: str
    notes: Optional[str] = None

@router.post("/request")
async def requestDischarge(request: SimpleDischargeRequest):
    """
    Frontend-compatible endpoint: Request patient discharge
    Maps to doctor-request endpoint
    """
    dischargeRequest = DischargeRequest(
        patientId=request.patientId,
        dischargeReason=request.reason,
        dischargeNotes=request.notes or "",
        requestedBy=request.requestedBy
    )
    return await doctorRequestDischarge(dischargeRequest)

class SimpleApprovalRequest(BaseModel):
    requestId: int
    approvedBy: str
    approvalNotes: Optional[str] = None

@router.post("/approve")
async def approveDischarge(request: SimpleApprovalRequest):
    """
    Frontend-compatible endpoint: Approve discharge request
    Maps to admin-approval endpoint
    Note: requestId is used to find the patientId
    """
    # For now, we'll need to query the patient by status since we don't have a requests table
    # This is a simplified implementation
    async with getDbConnection() as conn:
        # Find first patient with 'requested' status (temporary solution)
        patient = await conn.fetchrow(
            'SELECT id FROM patients WHERE "dischargeStatus" = \'requested\' ORDER BY "updatedAt" ASC LIMIT 1'
        )
        if not patient:
            raise HTTPException(status_code=404, detail="No pending discharge requests found")

        approvalRequest = AdminApprovalRequest(
            patientId=patient['id'],
            approvalNotes=request.approvalNotes or "",
            approvedBy=request.approvedBy
        )
        return await adminApproveDischarge(approvalRequest)

class SimpleCompleteRequest(BaseModel):
    requestId: int
    performedBy: str
    dischargeNotes: Optional[str] = None

@router.post("/complete")
async def completeDischarge(request: SimpleCompleteRequest):
    """
    Frontend-compatible endpoint: Complete patient discharge
    Maps to nurse-discharge endpoint
    Note: requestId is used to find the patientId
    """
    # For now, we'll need to query the patient by status since we don't have a requests table
    async with getDbConnection() as conn:
        # Find first patient with 'adminapproved' status (temporary solution)
        patient = await conn.fetchrow(
            'SELECT id FROM patients WHERE "dischargeStatus" = \'adminapproved\' ORDER BY "updatedAt" ASC LIMIT 1'
        )
        if not patient:
            raise HTTPException(status_code=404, detail="No approved discharge requests found")

        return await nurseCompleteDischarge(
            patientId=patient['id'],
            nurseId=request.performedBy,
            dischargeNotes=request.dischargeNotes or ""
        )