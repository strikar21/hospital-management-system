from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List, Optional
from sqlalchemy import select, update, delete
from datetime import datetime, timedelta

from app.schemas.device import (
    DeviceCreate, DeviceUpdate, DeviceResponse, DeviceListResponse,
    DeviceHealth, DeviceAlertResponse, VitalReadingResponse
)
from app.models.device import Device, DeviceAlert, VitalReading
from app.db.database import database
from app.services.device_service import DeviceService

router = APIRouter(prefix="/devices")

@router.post("/", response_model=DeviceResponse, status_code=201)
async def register_device(
    device_data: DeviceCreate,
    request: Request
):
    """Register a new device in the system"""
    device_service = DeviceService(request.app.state.websocket_manager)
    
    try:
        device = await device_service.register_device(device_data)
        return device
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to register device")

@router.get("/", response_model=DeviceListResponse)
async def get_devices(
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    status: Optional[str] = Query(None, description="Filter by device status"),
    location: Optional[str] = Query(None, description="Filter by location"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page")
):
    """Get list of registered devices with filtering"""
    
    # Build query
    query = select(Device).where(Device.isActive == True)
    
    if device_type:
        query = query.where(Device.deviceType == device_type)
    if status:
        query = query.where(Device.status == status)
    if location:
        query = query.where(Device.location.ilike(f"%{location}%"))
    
    # Get total count
    count_query = select(Device.id).where(Device.isActive == True)
    if device_type:
        count_query = count_query.where(Device.deviceType == device_type)
    if status:
        count_query = count_query.where(Device.status == status)
    if location:
        count_query = count_query.where(Device.location.ilike(f"%{location}%"))
    
    total_count = len(await database.fetch_all(count_query))
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    devices = await database.fetch_all(query)
    
    # Convert database rows to DeviceResponse objects manually
    device_responses = []
    for device in devices:
        device_dict = dict(device)
        print(f"Device dict keys: {list(device_dict.keys())}")
        print(f"AssignmentStatus value: {repr(device_dict.get('assignmentStatus'))}")
        # Ensure assignmentStatus has a default value if None
        if device_dict.get('assignmentStatus') is None:
            device_dict['assignmentStatus'] = 'free'
        device_responses.append(DeviceResponse(**device_dict))
    
    return DeviceListResponse(
        devices=device_responses,
        total_count=total_count,
        page=page,
        page_size=page_size
    )

@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: str):
    """Get specific device by ID"""
    query = select(Device).where(
        Device.deviceId == device_id,
        Device.isActive == True
    )
    device = await database.fetch_one(query)
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return DeviceResponse.from_orm(device)

@router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(device_id: str, device_update: DeviceUpdate, request: Request):
    """Update device information"""
    device_service = DeviceService(request.app.state.websocket_manager)
    
    try:
        device = await device_service.update_device(device_id, device_update)
        return device
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update device")

@router.delete("/{device_id}", status_code=204)
async def delete_device(device_id: str):
    """Soft delete a device"""
    query = update(Device).where(
        Device.deviceId == device_id
    ).values(
        isActive=False,
        updatedAt=datetime.utcnow()
    )
    
    result = await database.execute(query)
    if result == 0:
        raise HTTPException(status_code=404, detail="Device not found")

@router.post("/{device_id}/heartbeat", status_code=200)
async def device_heartbeat(device_id: str, health_data: DeviceHealth, request: Request):
    """Receive heartbeat from device and update status"""
    device_service = DeviceService(request.app.state.websocket_manager)
    
    try:
        await device_service.update_device_heartbeat(device_id, health_data)
        return {"status": "heartbeat_received"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{device_id}/alerts", response_model=List[DeviceAlertResponse])
async def get_device_alerts(
    device_id: str,
    active_only: bool = Query(True, description="Show only active alerts"),
    limit: int = Query(50, ge=1, le=100)
):
    """Get alerts for specific device"""
    query = select(DeviceAlert).where(DeviceAlert.deviceId == device_id)
    
    if active_only:
        query = query.where(DeviceAlert.isActive == True)
    
    query = query.order_by(DeviceAlert.createdAt.desc()).limit(limit)
    alerts = await database.fetch_all(query)
    
    return [DeviceAlertResponse.from_orm(alert) for alert in alerts]

@router.post("/{device_id}/alerts/{alert_id}/acknowledge", status_code=200)
async def acknowledge_alert(
    device_id: str, 
    alert_id: int, 
    acknowledged_by: str = Query(..., description="Staff member ID")
):
    """Acknowledge a device alert"""
    query = update(DeviceAlert).where(
        DeviceAlert.id == alert_id,
        DeviceAlert.deviceId == device_id,
        DeviceAlert.isActive == True
    ).values(
        isAcknowledged=True,
        acknowledgedBy=acknowledged_by,
        acknowledgedAt=datetime.utcnow()
    )
    
    result = await database.execute(query)
    if result == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"status": "alert_acknowledged"}

@router.get("/{device_id}/vitals", response_model=List[VitalReadingResponse])
async def get_device_vitals(
    device_id: str,
    patient_id: Optional[str] = Query(None, description="Filter by patient"),
    hours: int = Query(24, ge=1, le=168, description="Hours of data to retrieve"),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get vital signs data from device"""
    query = select(VitalReading).where(VitalReading.deviceId == device_id)
    
    if patient_id:
        query = query.where(VitalReading.patientId == patient_id)
    
    # Filter by time range
    since = datetime.utcnow() - timedelta(hours=hours)
    query = query.where(VitalReading.readingTimestamp >= since)
    
    query = query.order_by(VitalReading.readingTimestamp.desc()).limit(limit)
    vitals = await database.fetch_all(query)
    
    return [VitalReadingResponse.from_orm(vital) for vital in vitals]

@router.get("/type/{device_type}", response_model=List[DeviceResponse])
async def get_devices_by_type(device_type: str):
    """Get all devices of specific type"""
    query = select(Device).where(
        Device.deviceType == device_type,
        Device.isActive == True
    )
    devices = await database.fetch_all(query)
    
    return [DeviceResponse.from_orm(device) for device in devices]

@router.get("/location/{location}", response_model=List[DeviceResponse])
async def get_devices_by_location(location: str):
    """Get all devices in specific location"""
    query = select(Device).where(
        Device.location.ilike(f"%{location}%"),
        Device.isActive == True
    )
    devices = await database.fetch_all(query)
    
    return [DeviceResponse.from_orm(device) for device in devices]

@router.get("/status/summary")
async def get_device_status_summary():
    """Get summary of device statuses"""
    query = """
        SELECT 
            "deviceType",
            status,
            COUNT(*) as count
        FROM devices 
        WHERE "isActive" = true
        GROUP BY "deviceType", status
    """
    
    result = await database.fetch_all(query)
    
    # Organize data by device type
    summary = {}
    for row in result:
        device_type = row['deviceType']
        if device_type not in summary:
            summary[device_type] = {}
        summary[device_type][row['status']] = row['count']
    
    return {"device_status_summary": summary}

@router.post("/discharge-patient/{patient_id}")
async def discharge_patient_via_devices(patient_id: str):
    """Temporary discharge endpoint in devices router"""
    try:
        # Simple discharge - set patient inactive
        discharge_query = """
            UPDATE patients 
            SET "isActive" = false, 
                "dischargeDate" = :discharge_date,
                status = 'discharged'
            WHERE id = :patient_id AND "isActive" = true
        """
        result = await database.execute(discharge_query, {
            "patient_id": patient_id,
            "discharge_date": datetime.utcnow().isoformat()
        })
        
        if result == 0:
            return {"success": False, "message": "Patient not found or already discharged"}
        
        return {
            "success": True,
            "message": f"Patient {patient_id} successfully discharged",
            "patient_id": patient_id,
            "discharge_date": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}