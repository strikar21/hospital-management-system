"""
FHIR R5 Device API
Endpoints for managing IoT devices and device assignments
"""

from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from ...services.fhir.fhir_device_service import FhirDeviceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fhir/r5/devices", tags=["FHIR R5 - Devices"])

# Initialize service
device_service = FhirDeviceService()


# ================================
# DEVICE CRUD
# ================================

@router.post("/")
async def createDevice(device_data: Dict[str, Any]):
    """
    Create FHIR R5 Device

    Request body:
    {
        "deviceId": "fit-00001",
        "deviceType": "watch",
        "displayName": "Fit Watch 00001",
        "manufacturer": "Custom ESP32",
        "modelNumber": "ESP32-WATCH-V2",
        "serialNumber": "ESP32-SN-00001",
        "macAddress": "AA:BB:CC:DD:EE:FF",
        "firmwareVersion": "v2.1.3",
        "batteryLevel": 85,
        "status": "active"
    }
    """
    try:
        # Validate required fields
        if not device_data.get('deviceId'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="deviceId is required"
            )

        if not device_data.get('deviceType'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="deviceType is required (watch, tablet, doorScanner, sensor)"
            )

        # Check if device already exists
        existing = await device_service.get_device_by_device_id(device_data['deviceId'])
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Device {device_data['deviceId']} already exists"
            )

        result = await device_service.create_device(device_data)

        logger.info(f"✅ Created device: {device_data['deviceId']}")

        return JSONResponse({
            "success": True,
            "deviceId": str(result['id']),
            "deviceCode": result['deviceId'],
            "deviceType": result['deviceType'],
            "status": result['status']
        }, status_code=status.HTTP_201_CREATED)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating device: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create device: {str(e)}"
        )


@router.get("/{deviceId}")
async def getDevice(deviceId: str):
    """Get device by UUID"""
    try:
        result = await device_service.get_by_id(deviceId)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device not found: {deviceId}"
            )

        return JSONResponse({
            "success": True,
            "device": {
                "id": str(result['id']),
                "deviceId": result['deviceId'],
                "deviceType": result['deviceType'],
                "displayName": result.get('displayName'),
                "manufacturer": result.get('manufacturer'),
                "modelNumber": result.get('modelNumber'),
                "macAddress": result.get('macAddress'),
                "firmwareVersion": result.get('firmwareVersion'),
                "batteryLevel": result.get('batteryLevel'),
                "status": result['status'],
                "lastSeen": result.get('lastSeen').isoformat() if result.get('lastSeen') else None,
                "resource": result.get('resource')
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting device: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get device: {str(e)}"
        )


@router.get("/code/{deviceCode}")
async def getDeviceByCode(deviceCode: str):
    """Get device by deviceId code (fit-00001, ESP32_WATCH_002, etc.)"""
    try:
        result = await device_service.get_device_by_device_id(deviceCode)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device not found: {deviceCode}"
            )

        return JSONResponse({
            "success": True,
            "device": {
                "id": str(result['id']),
                "deviceId": result['deviceId'],
                "deviceType": result['deviceType'],
                "displayName": result.get('displayName'),
                "batteryLevel": result.get('batteryLevel'),
                "status": result['status'],
                "lastSeen": result.get('lastSeen').isoformat() if result.get('lastSeen') else None
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting device by code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get device: {str(e)}"
        )


@router.get("/mac/{macAddress}")
async def getDeviceByMac(macAddress: str):
    """Get device by MAC address"""
    try:
        result = await device_service.get_device_by_mac(macAddress)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device not found with MAC: {macAddress}"
            )

        return JSONResponse({
            "success": True,
            "device": {
                "id": str(result['id']),
                "deviceId": result['deviceId'],
                "deviceType": result['deviceType'],
                "macAddress": result.get('macAddress'),
                "status": result['status']
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting device by MAC: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get device: {str(e)}"
        )


@router.get("/")
async def getDevices(
    deviceType: Optional[str] = Query(None, description="Filter by type: watch, tablet, doorScanner"),
    status_filter: Optional[str] = Query('active', alias='status', description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get devices with filters"""
    try:
        if deviceType:
            results = await device_service.get_devices_by_type(
                deviceType,
                status=status_filter,
                limit=limit,
                offset=offset
            )
        else:
            results = await device_service.search(
                filters={'status': status_filter} if status_filter else None,
                limit=limit,
                offset=offset
            )

        devices = []
        for r in results:
            devices.append({
                "id": str(r['id']),
                "deviceId": r['deviceId'],
                "deviceType": r['deviceType'],
                "displayName": r.get('displayName'),
                "batteryLevel": r.get('batteryLevel'),
                "status": r['status'],
                "lastSeen": r.get('lastSeen').isoformat() if r.get('lastSeen') else None
            })

        return JSONResponse({
            "success": True,
            "count": len(devices),
            "devices": devices
        })

    except Exception as e:
        logger.error(f"❌ Error getting devices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get devices: {str(e)}"
        )


@router.get("/available/list")
async def getAvailableDevices(
    deviceType: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get available devices (not currently assigned)"""
    try:
        results = await device_service.get_available_devices(
            device_type=deviceType,
            limit=limit,
            offset=offset
        )

        devices = []
        for r in results:
            devices.append({
                "id": str(r['id']),
                "deviceId": r['deviceid'],
                "deviceType": r['devicetype'],
                "displayName": r.get('displayname'),
                "batteryLevel": r.get('batterylevel'),
                "lastSeen": r.get('lastseen').isoformat() if r.get('lastseen') else None,
                "assignmentStatus": r.get('assignmentstatus')
            })

        return JSONResponse({
            "success": True,
            "count": len(devices),
            "availableDevices": devices
        })

    except Exception as e:
        logger.error(f"❌ Error getting available devices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get available devices: {str(e)}"
        )


@router.patch("/{deviceId}")
async def updateDevice(deviceId: str, updates: Dict[str, Any]):
    """
    Update device

    Can update: batteryLevel, firmwareVersion, status, maintenanceStatus, etc.
    """
    try:
        result = await device_service.update_device(deviceId, updates)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device not found: {deviceId}"
            )

        logger.info(f"✅ Updated device: {deviceId}")

        return JSONResponse({
            "success": True,
            "deviceId": str(result['id']),
            "updatedAt": result['updatedAt'].isoformat()
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating device: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update device: {str(e)}"
        )


@router.post("/{deviceId}/health")
async def updateDeviceHealth(
    deviceId: str,
    health_data: Dict[str, Any]
):
    """
    Update device health metrics (from ESP32 heartbeat)

    Request body:
    {
        "batteryLevel": 80,
        "lastSeen": "2025-11-18T10:30:00Z"  // optional, defaults to now
    }
    """
    try:
        if 'batteryLevel' not in health_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="batteryLevel is required"
            )

        last_seen = None
        if health_data.get('lastSeen'):
            last_seen = datetime.fromisoformat(health_data['lastSeen'].replace('Z', '+00:00'))

        result = await device_service.update_device_health(
            deviceId,
            health_data['batteryLevel'],
            last_seen
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device not found: {deviceId}"
            )

        return JSONResponse({
            "success": True,
            "deviceId": str(result['id']),
            "batteryLevel": result.get('batteryLevel'),
            "lastSeen": result.get('lastSeen').isoformat() if result.get('lastSeen') else None
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating device health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update device health: {str(e)}"
        )


# ================================
# DEVICE ASSIGNMENT
# ================================

@router.post("/{deviceId}/assign")
async def assignDeviceToPatient(
    deviceId: str,
    assignment_data: Dict[str, Any]
):
    """
    Assign device to patient

    Request body:
    {
        "patientContextId": "uuid",
        "operatorReference": "https://hms.hospital.com/fhir/Practitioner/TEC001",  // optional
        "assignmentReason": "vitals monitoring"  // optional
    }
    """
    try:
        if not assignment_data.get('patientContextId'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="patientContextId is required"
            )

        # Check if device is already assigned
        existing_assignment = await device_service.get_device_assignment(deviceId)
        if existing_assignment:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Device {deviceId} is already assigned to patient {existing_assignment['patientContextId']}"
            )

        result = await device_service.assign_device_to_patient(
            deviceId,
            assignment_data['patientContextId'],
            assignment_data.get('operatorReference'),
            assignment_data.get('assignmentReason')
        )

        logger.info(f"✅ Assigned device {deviceId} to patient {assignment_data['patientContextId']}")

        return JSONResponse({
            "success": True,
            "assignmentId": str(result['id']),
            "deviceId": str(result['deviceId']),
            "patientContextId": str(result['patientContextId']),
            "status": result['status'],
            "assignedAt": result['periodStart'].isoformat() if result.get('periodStart') else None
        }, status_code=status.HTTP_201_CREATED)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error assigning device: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign device: {str(e)}"
        )


@router.delete("/assignments/{assignmentId}")
async def unassignDevice(assignmentId: str):
    """Unassign device from patient"""
    try:
        result = await device_service.unassign_device(assignmentId)

        logger.info(f"✅ Unassigned device association: {assignmentId}")

        return JSONResponse({
            "success": True,
            "assignmentId": str(result['id']),
            "status": result['status'],
            "unassignedAt": result.get('periodEnd').isoformat() if result.get('periodEnd') else None
        })

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"❌ Error unassigning device: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unassign device: {str(e)}"
        )


@router.get("/{deviceId}/assignment")
async def getDeviceAssignment(deviceId: str):
    """Get current assignment for a device"""
    try:
        result = await device_service.get_device_assignment(deviceId)

        if not result:
            return JSONResponse({
                "success": True,
                "deviceId": deviceId,
                "assignment": None,
                "message": "Device is not currently assigned"
            })

        return JSONResponse({
            "success": True,
            "deviceId": deviceId,
            "assignment": {
                "id": str(result['id']),
                "patientContextId": str(result['patientContextId']),
                "status": result['status'],
                "assignedAt": result['periodStart'].isoformat() if result.get('periodStart') else None,
                "operatorReference": result.get('operatorReference')
            }
        })

    except Exception as e:
        logger.error(f"❌ Error getting device assignment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get device assignment: {str(e)}"
        )


@router.get("/patient/{patientContextId}/devices")
async def getPatientDevices(patientContextId: str):
    """Get all devices currently assigned to a patient"""
    try:
        results = await device_service.get_patient_devices(patientContextId)

        devices = []
        for r in results:
            devices.append({
                "assignmentId": str(r['id']),
                "deviceId": str(r['deviceId']),
                "deviceCode": r.get('deviceId'),
                "deviceType": r.get('deviceType'),
                "displayName": r.get('displayName'),
                "batteryLevel": r.get('batteryLevel'),
                "assignedAt": r['periodStart'].isoformat() if r.get('periodStart') else None
            })

        return JSONResponse({
            "success": True,
            "patientContextId": patientContextId,
            "count": len(devices),
            "devices": devices
        })

    except Exception as e:
        logger.error(f"❌ Error getting patient devices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get patient devices: {str(e)}"
        )
