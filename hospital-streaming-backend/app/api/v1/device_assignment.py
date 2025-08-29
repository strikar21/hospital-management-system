from fastapi import APIRouter, HTTPException, Query, status, Depends
from typing import List, Optional
import logging

from app.services.device_assignment_service import DeviceAssignmentService
from app.services.staff_service import StaffService
from app.schemas.device_assignment import (
    DeviceAssignmentCreate,
    DeviceAssignmentUpdate,
    DeviceReassignmentCreate,
    DeviceAssignmentResponse,
    FreeDeviceResponse,
    PatientDeviceResponse,
    AssignmentHistoryResponse,
    DevicePoolStatusResponse
)

router = APIRouter(prefix="/device-assignment")
logger = logging.getLogger(__name__)

async def verify_staff_access(staff_id: str = Query(..., description="Staff ID performing the action")):
    """Verify staff member exists and is active"""
    staff = await StaffService.get_staff_by_id(staff_id)
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found"
        )
    return staff

@router.get("/free-devices", response_model=List[FreeDeviceResponse])
async def get_free_devices(
    device_type: Optional[str] = Query(None, description="Filter by device type (watch, vital_monitor, etc.)"),
    location: Optional[str] = Query(None, description="Filter by location"),
    staff: dict = Depends(verify_staff_access)
):
    """Get list of available devices from the free pool"""
    try:
        devices = await DeviceAssignmentService.get_free_devices(device_type, location)
        return devices
    except Exception as e:
        logger.error(f"Error getting free devices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve free devices"
        )

@router.get("/assigned-devices")
async def get_assigned_devices(
    staff_id: str = Query(..., description="Staff ID to get assignments for"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    location: Optional[str] = Query(None, description="Filter by location")
):
    """Get list of currently assigned devices"""
    try:
        from app.db.database import database
        
        # Build query for assigned devices with patient details
        query = """
        SELECT 
            d."deviceId",
            d.name as "deviceName",
            d."deviceType",
            d.location as "deviceLocation",
            d."assignedTo" as "patientId",
            d."assignmentStatus",
            d."batteryLevel",
            d."lastHeartbeat",
            da."assignedAt",
            da."assignedBy",
            da."assignmentReason",
            da.status as "assignmentStatusAlias",
            p.name as "patientName",
            p.age as "patientAge",
            p.gender as "patientGender",
            p.ward,
            p.room,
            p."bedNumber",
            p.diagnosis
        FROM devices d
        LEFT JOIN device_assignments da ON d."deviceId" = da."deviceId" AND da.status = 'active'
        LEFT JOIN patients p ON d."assignedTo" = p.id
        WHERE d."assignmentStatus" = 'assigned'
        AND d."isActive" = true
        """
        
        params = {}
        
        if device_type:
            query += " AND d.\"deviceType\" = :device_type"
            params["device_type"] = device_type
            
        if location:
            query += " AND d.location = :location"
            params["location"] = location
        
        query += " ORDER BY da.\"assignedAt\" DESC"
        
        assignments = await database.fetch_all(query, params)
        
        # Format response
        assigned_devices = []
        for assignment in assignments:
            assigned_devices.append({
                "deviceId": assignment["deviceId"],
                "deviceName": assignment["deviceName"],
                "deviceType": assignment["deviceType"],
                "deviceLocation": assignment["deviceLocation"],
                "batteryLevel": assignment["batteryLevel"],
                "lastHeartbeat": assignment["lastHeartbeat"].isoformat() if assignment["lastHeartbeat"] else None,
                "assignmentStatus": assignment["assignmentStatus"],
                "assignedAt": assignment["assignedAt"].isoformat() if assignment["assignedAt"] else None,
                "assignedBy": assignment["assignedBy"],
                "assignmentReason": assignment["assignmentReason"],
                "patient": {
                    "id": assignment["patientId"],
                    "name": assignment["patientName"],
                    "age": assignment["patientAge"],
                    "gender": assignment["patientGender"],
                    "ward": assignment["ward"],
                    "room": assignment["room"],
                    "bedNumber": assignment["bedNumber"],
                    "diagnosis": assignment["diagnosis"]
                } if assignment["patientId"] else None
            })
        
        return {
            "assigned_devices": assigned_devices,
            "total_assigned": len(assigned_devices)
        }
        
    except Exception as e:
        logger.error(f"Error getting assigned devices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve assigned devices"
        )

@router.post("/assign", response_model=DeviceAssignmentResponse)
async def assign_device(
    assignment: DeviceAssignmentCreate,
    staff: dict = Depends(verify_staff_access)
):
    """Assign a device to a patient"""
    try:
        result = await DeviceAssignmentService.assign_device_to_patient(
            assignment.deviceId,
            assignment.patientId,
            assignment.assignedBy,
            assignment.assignmentReason
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to assign device"
            )
        
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error assigning device: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign device"
        )

@router.post("/unassign/{device_id}")
async def unassign_device(
    device_id: str,
    unassignment: DeviceAssignmentUpdate,
    staff: dict = Depends(verify_staff_access)
):
    """Unassign device from patient and return to free pool"""
    try:
        success = await DeviceAssignmentService.unassign_device(
            device_id,
            unassignment.unassignedBy,
            unassignment.unassignmentReason,
            unassignment.newDeviceId
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to unassign device"
            )
        
        return {"success": True, "message": f"Device {device_id} unassigned successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error unassigning device: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unassign device"
        )

@router.post("/reassign", response_model=DeviceAssignmentResponse)
async def reassign_device(
    reassignment: DeviceReassignmentCreate,
    staff: dict = Depends(verify_staff_access)
):
    """Reassign patient from one device to another"""
    try:
        result = await DeviceAssignmentService.reassign_device(
            reassignment.oldDeviceId,
            reassignment.newDeviceId,
            reassignment.reassignedBy,
            reassignment.reassignmentReason
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to reassign device"
            )
        
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error reassigning device: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reassign device"
        )

@router.get("/patient/{patient_id}/device")
async def get_patient_device(
    patient_id: str,
    staff: dict = Depends(verify_staff_access)
):
    """Get currently assigned device for a patient"""
    try:
        device = await DeviceAssignmentService.get_patient_device(patient_id)
        
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No device currently assigned to this patient"
            )
        
        return device
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting patient device: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve patient device"
        )

@router.get("/history")
async def get_assignment_history(
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    device_id: Optional[str] = Query(None, description="Filter by device ID"), 
    limit: int = Query(default=50, description="Number of records to return"),
    staff: dict = Depends(verify_staff_access)
):
    """Get assignment history for patient, device, or all assignments"""
    try:
        history = await DeviceAssignmentService.get_assignment_history(
            patient_id, device_id, limit
        )
        
        return {"history": history, "total_records": len(history)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting assignment history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve assignment history"
        )

@router.get("/pool-status")
async def get_device_pool_status(staff: dict = Depends(verify_staff_access)):
    """Get overview of device pool status"""
    try:
        status_info = await DeviceAssignmentService.get_device_pool_status()
        return status_info
    except Exception as e:
        logger.error(f"Error getting device pool status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve device pool status"
        )

@router.get("/bulk-operations/unassign-patient/{patient_id}")
async def bulk_unassign_patient_devices(
    patient_id: str,
    unassigned_by: str = Query(..., description="Staff ID performing bulk unassignment"),
    unassignment_reason: str = Query(default="patient_discharge", description="Reason for unassignment"),
    staff: dict = Depends(verify_staff_access)
):
    """Unassign all devices from a patient (useful for discharge)"""
    try:
        # Get all devices assigned to patient
        history = await DeviceAssignmentService.get_assignment_history(
            patient_id=patient_id, limit=100
        )
        
        # Find active assignments
        active_devices = [
            record for record in history 
            if record["status"] == "active"
        ]
        
        if not active_devices:
            return {
                "success": True,
                "message": "No devices currently assigned to patient",
                "unassigned_count": 0
            }
        
        # Unassign each device
        unassigned_count = 0
        errors = []
        
        for record in active_devices:
            try:
                await DeviceAssignmentService.unassign_device(
                    record["deviceId"],
                    unassigned_by,
                    unassignment_reason
                )
                unassigned_count += 1
            except Exception as e:
                errors.append(f"Device {record['device_id']}: {str(e)}")
        
        response = {
            "success": True,
            "message": f"Successfully unassigned {unassigned_count} devices",
            "unassigned_count": unassigned_count,
            "total_found": len(active_devices)
        }
        
        if errors:
            response["errors"] = errors
            response["success"] = unassigned_count > 0
        
        return response
        
    except Exception as e:
        logger.error(f"Error in bulk unassignment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform bulk unassignment"
        )