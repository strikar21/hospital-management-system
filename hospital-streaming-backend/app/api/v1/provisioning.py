from fastapi import APIRouter, HTTPException, Query, Depends, status
from typing import Optional
from app.services.device_provisioning_service import DeviceProvisioningService
from app.services.staff_service import StaffService
from app.schemas.devices import (
    DeviceProvisionRequest, DeviceResponse, DeviceUpdate, 
    DeviceStatusUpdate, DeviceListResponse
)

router = APIRouter(prefix="/provisioning")

async def verify_provisioner(staff_id: str = Query(..., description="Staff ID of the provisioner")):
    """Verify that the staff member has provisioner role"""
    staff = await StaffService.get_staff_by_id(staff_id)
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found"
        )
    
    if staff.role != "Provisioner" and staff.role not in ["Admin", "Administrator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Provisioners and Administrators can manage devices"
        )
    
    return staff

@router.post("/devices", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def provision_device(
    device_data: DeviceProvisionRequest,
    provisioner: dict = Depends(verify_provisioner)
):
    """Provision a new device in the hospital system"""
    try:
        device = await DeviceProvisioningService.provision_device(
            device_data, 
            provisioner.staff_id
        )
        
        if device:
            return device
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to provision device"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/devices", response_model=DeviceListResponse)
async def list_devices(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    device_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    location: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=True),
    provisioner: dict = Depends(verify_provisioner)
):
    """List all provisioned devices with filtering"""
    result = await DeviceProvisioningService.list_devices(
        page=page,
        page_size=page_size,
        device_type=device_type,
        status=status,
        location=location,
        is_active=is_active
    )
    return DeviceListResponse(**result)

@router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    provisioner: dict = Depends(verify_provisioner)
):
    """Get device details by device ID"""
    device = await DeviceProvisioningService.get_device(device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    return device

@router.put("/devices/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: str,
    update_data: DeviceUpdate,
    provisioner: dict = Depends(verify_provisioner)
):
    """Update device configuration and settings"""
    try:
        device = await DeviceProvisioningService.update_device(device_id, update_data)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )
        return device
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.patch("/devices/{device_id}/status", response_model=DeviceResponse)
async def update_device_status(
    device_id: str,
    status_data: DeviceStatusUpdate,
    provisioner: dict = Depends(verify_provisioner)
):
    """Update device operational status"""
    try:
        device = await DeviceProvisioningService.update_device_status(device_id, status_data)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )
        return device
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_device(
    device_id: str,
    provisioner: dict = Depends(verify_provisioner)
):
    """Deactivate a device (soft delete)"""
    success = await DeviceProvisioningService.deactivate_device(
        device_id, 
        provisioner.staff_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )

@router.get("/device-types")
async def get_device_types(provisioner: dict = Depends(verify_provisioner)):
    """Get list of supported device types"""
    return {
        "device_types": [
            {"type": "watch", "name": "Patient Watch", "category": "wearable"},
            {"type": "vital_monitor", "name": "Vital Signs Monitor", "category": "medical"},
            {"type": "door_scanner", "name": "Door Access Scanner", "category": "security"},
            {"type": "bed_sensor", "name": "Bed Sensor", "category": "monitoring"},
            {"type": "iv_pump", "name": "IV Infusion Pump", "category": "medical"},
            {"type": "ventilator", "name": "Ventilator", "category": "medical"},
            {"type": "ecg_monitor", "name": "ECG Monitor", "category": "medical"},
            {"type": "pulse_oximeter", "name": "Pulse Oximeter", "category": "medical"},
            {"type": "blood_pressure_monitor", "name": "Blood Pressure Monitor", "category": "medical"},
            {"type": "temperature_sensor", "name": "Temperature Sensor", "category": "monitoring"},
            {"type": "camera", "name": "Security Camera", "category": "security"},
            {"type": "access_control", "name": "Access Control System", "category": "security"},
            {"type": "emergency_button", "name": "Emergency Call Button", "category": "safety"},
            {"type": "tablet", "name": "Medical Tablet", "category": "computing"},
            {"type": "smartphone", "name": "Medical Smartphone", "category": "computing"}
        ]
    }

@router.get("/locations")
async def get_common_locations(provisioner: dict = Depends(verify_provisioner)):
    """Get list of common hospital locations for device placement"""
    return {
        "locations": [
            # ICU Locations
            "ICU-101", "ICU-102", "ICU-103", "ICU-104", "ICU-105",
            "ICU-Main", "ICU-Isolation", "ICU-Entry",
            
            # General Wards
            "Ward-A101", "Ward-A102", "Ward-B201", "Ward-B202", "Ward-C301", "Ward-C302",
            
            # Emergency Department
            "ER-Main", "ER-Trauma1", "ER-Trauma2", "ER-Triage", "ER-Resus",
            
            # Operating Theaters
            "OT-1", "OT-2", "OT-3", "OT-4", "OT-Recovery",
            
            # Specialty Units
            "Cardio-Unit", "Neuro-Unit", "Ortho-Unit", "Peds-Ward", "Maternity-Ward",
            
            # Support Areas
            "Pharmacy", "Laboratory", "Radiology", "Reception", "Administration",
            "Nursing-Station", "Storage", "Equipment-Room", "Staff-Room",
            
            # Access Points
            "Main-Entrance", "Staff-Entrance", "Emergency-Exit", "Elevator-A", "Elevator-B"
        ]
    }

@router.get("/status-types")
async def get_device_statuses(provisioner: dict = Depends(verify_provisioner)):
    """Get list of possible device statuses"""
    return {
        "statuses": [
            {"status": "online", "description": "Device is connected and operational"},
            {"status": "offline", "description": "Device is not responding"},
            {"status": "maintenance", "description": "Device is under maintenance"},
            {"status": "error", "description": "Device has reported an error"},
            {"status": "provisioning", "description": "Device is being set up"}
        ]
    }