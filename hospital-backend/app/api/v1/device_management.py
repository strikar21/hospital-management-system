"""
General Device Management API endpoints for all hospital devices
(tablets, displays, sensors, medical equipment, etc.)
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import asyncpg
import logging
from datetime import datetime, timedelta
import uuid

from ...core.database import getDbConnection
from ...services.audit import logAuditEvent
from ...core.auth_dependencies import require_admin, require_medical_staff, get_current_user
from ...middleware.staff_resolution_middleware import resolve_staff_in_response

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(require_admin)])

# Device types supported by the system
DEVICE_TYPES = {
    'tablet': 'Tablet/Display Device',
    'watch': 'ESP32 Patient Watch',
    'sensor': 'IoT Sensor',
    'medicalEquipment': 'Medical Equipment Interface',
    'doorScanner': 'BLE Door Scanner',
    'vitalMonitor': 'Vital Signs Monitor',
    'infusionPump': 'Smart Infusion Pump',
    'other': 'Other Device'
}

DEVICE_STATUSES = ['available', 'assigned', 'maintenance', 'retired', 'offline']

@router.get("/types")
async def getDeviceTypes():
    """Get all supported device types"""
    return JSONResponse(content={
        "success": True,
        "deviceTypes": DEVICE_TYPES,
        "statuses": DEVICE_STATUSES
    })

@router.post("/")
async def createDevice(
    deviceData: dict,
    createdBy: str = Query(..., description="Staff ID creating the device"),
    current_user: dict = Depends(require_admin)  # Only admin can add devices
):
    """
    Add a new device to the hospital inventory

    RBAC: Requires administrator role.
    """
    try:
        # Required fields
        requiredFields = ['deviceType', 'name', 'location']
        for field in requiredFields:
            if field not in deviceData:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

        # Validate device type
        if deviceData['deviceType'] not in DEVICE_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid device type. Must be one of: {list(DEVICE_TYPES.keys())}")

        deviceId = f"{deviceData.get('deviceType', '').upper()}_{str(uuid.uuid4())[:8].upper()}"

        async with getDbConnection() as conn:
            query = """
                INSERT INTO devices (
                    id, "deviceType", name, model, manufacturer, "serialNumber", "macAddress",
                    "firmwareVersion", status, location, description, "createdAt", "updatedAt"
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                RETURNING *
            """

            now = datetime.now()
            values = (
                deviceId,
                deviceData['deviceType'],
                deviceData['name'],
                deviceData.get('model'),
                deviceData.get('manufacturer'),
                deviceData.get('serialNumber'),
                deviceData.get('macAddress'),
                deviceData.get('firmwareVersion'),
                deviceData.get('status', 'available'),
                deviceData['location'],
                deviceData.get('description', ''),
                now, now
            )

            row = await conn.fetchrow(query, *values)
            deviceDict = dict(row)

            # Convert datetime objects for JSON serialization
            for key, value in deviceDict.items():
                if isinstance(value, datetime):
                    deviceDict[key] = value.isoformat()

            # Log audit event
            await logAuditEvent(
                userId=createdBy,
                action="DEVICE_CREATED",
                resourceType="DEVICE",
                resourceId=deviceId,
                details=f"Created {deviceData['deviceType']} device: {deviceData['name']}"
            )

            logger.info(f"✅ Created device: {deviceId}")
            return JSONResponse(content={
                "success": True,
                "device": deviceDict,
                "message": f"Device {deviceData['name']} added to inventory"
            })

    except Exception as e:
        logger.error(f"❌ Error creating device: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create device: {str(e)}")

@router.get("/available")
async def getAvailableDevices(
    deviceType: Optional[str] = Query(None, description="Filter by device type"),
    location: Optional[str] = Query(None, description="Filter by location"),
    limit: int = Query(50, description="Maximum number of devices to return")
):
    """Get available devices for assignment - Frontend Compatible Endpoint"""
    try:
        async with getDbConnection() as conn:
            whereClauses = ["status = 'available'"]  # Only available devices
            params = []
            paramCount = 1

            if deviceType:
                paramCount += 1
                whereClauses.append(f"\"deviceType\" = ${paramCount}")
                params.append(deviceType)

            if location:
                paramCount += 1
                whereClauses.append(f"location ILIKE ${paramCount}")
                params.append(f"%{location}%")

            whereClause = " WHERE " + " AND ".join(whereClauses)

            query = f"""
                SELECT d.*,
                       CASE WHEN d."lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
                            WHEN d."lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
                            ELSE 'offline' END as connectionStatus,
                       'N/A' as currentAssignment
                FROM devices d
                {whereClause}
                ORDER BY d."deviceType", d.name
                LIMIT {limit}
            """

            rows = await conn.fetch(query, *params)

            devices = []
            for row in rows:
                deviceDict = dict(row)
                # Convert datetime fields to ISO strings
                if deviceDict.get('createdAt'):
                    deviceDict['createdAt'] = deviceDict['createdAt'].isoformat()
                if deviceDict.get('lastSeen'):
                    deviceDict['lastSeen'] = deviceDict['lastSeen'].isoformat()

                devices.append(deviceDict)

            logger.info(f"✅ Retrieved {len(devices)} available devices")

            return JSONResponse(content={
                "success": True,
                "devices": devices,
                "count": len(devices),
                "filters": {
                    "deviceType": deviceType,
                    "location": location,
                    "status": "available"
                }
            })

    except Exception as e:
        logger.error(f"❌ Failed to get available devices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get available devices: {str(e)}")

@router.get("/")
async def listDevices(
    deviceType: Optional[str] = Query(None, description="Filter by device type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    location: Optional[str] = Query(None, description="Filter by location"),
    limit: int = Query(100, description="Maximum number of devices to return")
):
    """List all devices in the hospital inventory with optional filtering"""
    try:
        async with getDbConnection() as conn:
            whereClauses = []
            params = []
            paramCount = 0

            if deviceType:
                paramCount += 1
                whereClauses.append(f"\"deviceType\" = ${paramCount}")
                params.append(deviceType)

            if status:
                paramCount += 1
                whereClauses.append(f"status = ${paramCount}")
                params.append(status)

            if location:
                paramCount += 1
                whereClauses.append(f"location ILIKE ${paramCount}")
                params.append(f"%{location}%")

            whereClause = " WHERE " + " AND ".join(whereClauses) if whereClauses else ""

            query = f"""
                SELECT d.*,
                       CASE WHEN d."lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
                            WHEN d."lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
                            ELSE 'offline' END as connectionStatus
                FROM devices d
                {whereClause}
                ORDER BY d."deviceType", d.name
                LIMIT {limit}
            """

            rows = await conn.fetch(query, *params)

            devices = []
            for row in rows:
                deviceDict = dict(row)

                # Convert datetime objects for JSON serialization
                for key, value in deviceDict.items():
                    if isinstance(value, datetime):
                        deviceDict[key] = value.isoformat()

                # Add computed fields
                deviceDict['deviceTypeName'] = DEVICE_TYPES.get(deviceDict['deviceType'], 'Unknown')
                devices.append(deviceDict)

            # Get summary statistics
            summaryQuery = """
                SELECT "deviceType", status, COUNT(*) as count
                FROM devices
                GROUP BY "deviceType", status
                ORDER BY "deviceType", status
            """
            summaryRows = await conn.fetch(summaryQuery)

            summary = {}
            for row in summaryRows:
                deviceType = row['deviceType']
                if deviceType not in summary:
                    summary[deviceType] = {}
                summary[deviceType][row['status']] = row['count']

            logger.info(f"✅ Retrieved {len(devices)} devices")
            return JSONResponse(content={
                "success": True,
                "devices": devices,
                "count": len(devices),
                "summary": summary,
                "filters": {
                    "deviceType": deviceType,
                    "status": status,
                    "location": location
                }
            })

    except Exception as e:
        logger.error(f"❌ Error listing devices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list devices: {str(e)}")

@router.get("/{deviceId}")
async def getDevice(deviceId: str):
    """Get detailed information about a specific device"""
    try:
        async with getDbConnection() as conn:
            query = """
                SELECT d.*,
                       CASE WHEN d."lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
                            WHEN d."lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
                            ELSE 'offline' END as connectionStatus,
                       CAST(EXTRACT(EPOCH FROM (NOW() - d."lastSeen"))/60 AS DOUBLE PRECISION) as minutesSinceLastSeen
                FROM devices d
                WHERE d.id = $1
            """

            row = await conn.fetchrow(query, deviceId)
            if not row:
                raise HTTPException(status_code=404, detail="Device not found")

            deviceDict = dict(row)

            # Convert datetime objects for JSON serialization
            for key, value in deviceDict.items():
                if isinstance(value, datetime):
                    deviceDict[key] = value.isoformat()

            # Add computed fields
            deviceDict['deviceTypeName'] = DEVICE_TYPES.get(deviceDict['deviceType'], 'Unknown')

            # Get assignment history if applicable
            if deviceDict['deviceType'] in ['watch', 'tablet']:
                assignmentQuery = """
                    SELECT da.*, p."firstName", p."lastName", p."roomNumber", p."bedNumber"
                    FROM deviceassignments da
                    LEFT JOIN patients p ON da."patientId" = p.id
                    WHERE da."deviceId" = $1
                    ORDER BY da."assignedAt" DESC
                    LIMIT 10
                """
                assignmentRows = await conn.fetch(assignmentQuery, deviceId)
                assignments = []
                for assignmentRow in assignmentRows:
                    assignmentDict = dict(assignmentRow)
                    for key, value in assignmentDict.items():
                        if isinstance(value, datetime):
                            assignmentDict[key] = value.isoformat()
                    assignments.append(assignmentDict)
                deviceDict['assignmentHistory'] = assignments

            logger.info(f"✅ Retrieved device: {deviceId}")

            # Apply staff resolution middleware (resolves assignedBy in assignmentHistory)
            response = {
                "success": True,
                "device": deviceDict
            }
            response = await resolve_staff_in_response(response, conn)

            return JSONResponse(content=response)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting device: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get device: {str(e)}")

@router.put("/{deviceId}")
async def updateDevice(
    deviceId: str,
    updateData: dict,
    updatedBy: str = Query(..., description="Staff ID updating the device"),
    current_user: dict = Depends(require_admin)  # Only admin can update devices
):
    """
    Update device properties

    RBAC: Requires administrator role.
    """
    try:
        # Allowed fields for update - match actual database schema
        # Note: Device assignments are tracked in deviceassignments table, not here
        allowedFields = ['name', 'model', 'manufacturer', 'location', 'serialNumber', 'macAddress',
                         'firmwareVersion', 'batteryLevel', 'status', 'description', 'lastSeen',
                         'calibrationDate', 'nextMaintenanceDate']
        updateFields = []
        updateValues = []
        paramCount = 0

        for field, value in updateData.items():
            if field in allowedFields:
                paramCount += 1
                updateFields.append(f"{field} = ${paramCount}")
                updateValues.append(value)

        if not updateFields:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        async with getDbConnection() as conn:
            # Add updatedAt field
            paramCount += 1
            updateFields.append(f'"updatedAt" = ${paramCount}')
            updateValues.append(datetime.now())

            # Add deviceId as final parameter
            paramCount += 1
            updateValues.append(deviceId)

            query = f"""
                UPDATE devices
                SET {', '.join(updateFields)}
                WHERE id = ${paramCount}
                RETURNING *
            """

            row = await conn.fetchrow(query, *updateValues)
            if not row:
                raise HTTPException(status_code=404, detail="Device not found")

            deviceDict = dict(row)

            # Convert datetime objects for JSON serialization
            for key, value in deviceDict.items():
                if isinstance(value, datetime):
                    deviceDict[key] = value.isoformat()

            # Log audit event
            await logAuditEvent(
                userId=updatedBy,
                action="DEVICE_UPDATED",
                resourceType="DEVICE",
                resourceId=deviceId,
                details=f"Updated device: {deviceDict['name']}"
            )

            logger.info(f"✅ Updated device: {deviceId}")
            return JSONResponse(content={
                "success": True,
                "device": deviceDict,
                "message": f"Device {deviceDict['name']} updated successfully"
            })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating device: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update device: {str(e)}")

@router.delete("/{deviceId}")
async def removeDevice(
    deviceId: str,
    deletedBy: str = Query(..., description="Staff ID removing the device"),
    force: bool = False,
    current_user: dict = Depends(require_admin)  # Only admin can remove devices
):
    """
    Remove a device from the hospital inventory (soft delete unless force=True)

    RBAC: Requires administrator role.
    """
    try:
        async with getDbConnection() as conn:
            # Check if device has active assignments
            assignmentCheck = """
                SELECT da."patientId", p."firstName", p."lastName"
                FROM deviceassignments da
                JOIN patients p ON da."patientId" = p.id
                WHERE da."deviceId" = $1 AND da.status = 'active'
            """
            assignment = await conn.fetchrow(assignmentCheck, deviceId)

            if assignment and not force:
                patientName = f"{assignment['firstName']} {assignment['lastName']}"
                raise HTTPException(
                    status_code=400,
                    detail=f"Device is currently assigned to {patientName}. Unassign first or use force=True"
                )

            if force and assignment:
                # Force unassign first
                await conn.execute(
                    'UPDATE deviceassignments SET status = \'forceRemoved\', "unassignedAt" = $1 WHERE "deviceId" = $2 AND status = \'active\'',
                    datetime.now(), deviceId
                )

            # Get device info before deletion
            deviceInfo = await conn.fetchrow('SELECT name, "deviceType" FROM devices WHERE id = $1', deviceId)
            if not deviceInfo:
                raise HTTPException(status_code=404, detail="Device not found")

            # Soft delete by setting status to 'retired'
            query = """
                UPDATE devices
                SET status = 'retired', "updatedAt" = $1
                WHERE id = $2
                RETURNING name
            """

            row = await conn.fetchrow(query, datetime.now(), deviceId)
            if not row:
                raise HTTPException(status_code=404, detail="Device not found")

            # Log audit event
            await logAuditEvent(
                userId=deletedBy,
                action="DEVICE_REMOVED",
                resourceType="DEVICE",
                resourceId=deviceId,
                details=f"Removed {deviceInfo['deviceType']} device: {deviceInfo['name']}"
            )

            logger.info(f"✅ Removed device: {deviceId}")
            return JSONResponse(content={
                "success": True,
                "message": f"Device {row['name']} removed from inventory",
                "forceRemoved": force
            })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error removing device: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove device: {str(e)}")

@router.get("/location/{location}")
async def getDevicesByLocation(location: str):
    """Get all devices in a specific location (room, department, etc.)"""
    try:
        async with getDbConnection() as conn:
            query = """
                SELECT d.*,
                       CASE WHEN d."lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
                            WHEN d."lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
                            ELSE 'offline' END as connectionStatus
                FROM devices d
                WHERE d.location ILIKE $1 AND d.status != 'retired'
                ORDER BY d."deviceType", d.name
            """

            rows = await conn.fetch(query, f"%{location}%")

            devices = []
            for row in rows:
                deviceDict = dict(row)

                # Convert datetime objects for JSON serialization
                for key, value in deviceDict.items():
                    if isinstance(value, datetime):
                        deviceDict[key] = value.isoformat()

                deviceDict['deviceTypeName'] = DEVICE_TYPES.get(deviceDict['deviceType'], 'Unknown')
                devices.append(deviceDict)

            logger.info(f"✅ Retrieved {len(devices)} devices for location: {location}")
            return JSONResponse(content={
                "success": True,
                "location": location,
                "devices": devices,
                "count": len(devices)
            })

    except Exception as e:
        logger.error(f"❌ Error getting devices by location: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get devices by location: {str(e)}")

@router.get("/status/health")
async def getDeviceHealthStatus():
    """Get overall device health status across the hospital"""
    try:
        async with getDbConnection() as conn:
            query = """
                SELECT
                    "deviceType",
                    status,
                    COUNT(*) as count,
                    CASE WHEN "lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
                         WHEN "lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
                         ELSE 'offline' END as "connectionStatus"
                FROM devices
                WHERE status != 'retired'
                GROUP BY "deviceType", status,
                    CASE WHEN "lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
                         WHEN "lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
                         ELSE 'offline' END
                ORDER BY "deviceType", status
            """

            rows = await conn.fetch(query)

            healthSummary = {}
            totalDevices = 0
            onlineDevices = 0

            for row in rows:
                deviceType = row['deviceType']
                if deviceType not in healthSummary:
                    healthSummary[deviceType] = {
                        'total': 0,
                        'online': 0,
                        'offline': 0,
                        'maintenance': 0,
                        'available': 0,
                        'assigned': 0
                    }

                count = row['count']
                totalDevices += count
                healthSummary[deviceType]['total'] += count

                # Connection status
                if row['connectionStatus'] in ['connected', 'recentlySeen']:
                    healthSummary[deviceType]['online'] += count
                    onlineDevices += count
                else:
                    healthSummary[deviceType]['offline'] += count

                # Device status
                status = row['status']
                if status in healthSummary[deviceType]:
                    healthSummary[deviceType][status] += count

            overallHealth = {
                'totalDevices': totalDevices,
                'onlineDevices': onlineDevices,
                'offlineDevices': totalDevices - onlineDevices,
                'healthPercentage': round((onlineDevices / totalDevices * 100) if totalDevices > 0 else 0, 2)
            }

            logger.info(f"✅ Retrieved device health status")
            return JSONResponse(content={
                "success": True,
                "overallHealth": overallHealth,
                "byDeviceType": healthSummary,
                "timestamp": datetime.now().isoformat()
            })

    except Exception as e:
        logger.error(f"❌ Error getting device health status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get device health status: {str(e)}")