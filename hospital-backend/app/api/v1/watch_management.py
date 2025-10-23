"""
Watch Management API endpoints for ESP32 watch assignment and monitoring
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
from decimal import Decimal
import asyncpg
import logging
from datetime import datetime, timedelta

from ...core.database import getDbConnection
# Utils for date serialization
from ...services.websocket_manager import connectionManager
from ...services.mqtt_service import mqttService
from ...core.auth_dependencies import require_medical_staff, require_admin, get_current_user, require_admin_or_medical
from ...middleware.staff_resolution_middleware import resolve_staff_in_response

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(require_admin_or_medical)])

@router.get("/available")
async def getAvailableWatches():
    """Get all available ESP32 watches for assignment"""
    try:
        async with getDbConnection() as conn:
            query = """
            SELECT d.*,
                   CASE WHEN d."lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
                        WHEN d."lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
                        ELSE 'offline' END as connectionStatus
            FROM devices d
            WHERE d."deviceType" = 'watch' AND d.status = 'available'
            ORDER BY d."lastSeen" DESC, d."serialNumber"
            """

            rows = await conn.fetch(query)

            watches = []
            for row in rows:
                watchDict = dict(row)

                # Convert datetime objects for JSON serialization
                for key, value in watchDict.items():
                    if isinstance(value, datetime):
                        watchDict[key] = value.isoformat()

                # Add display information
                watchDict['displayName'] = f"Watch {watchDict.get('serialNumber', '')}"
                watchDict['batteryStatus'] = getBatteryStatus(watchDict.get('batteryLevel', 0))

                watches.append(watchDict)

            logger.info(f"✅ Retrieved {len(watches)} available watches")

            return JSONResponse(content={
                "success": True,
                "availableWatches": watches,
                "count": len(watches)
            })

    except Exception as e:
        logger.error(f"❌ Error getting available watches: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get available watches: {str(e)}")

@router.get("/assigned")
async def getAssignedWatches():
    """Get all currently assigned watches with patient information"""
    try:
        async with getDbConnection() as conn:
            query = """
            SELECT d.*, da.*, p."firstName", p."lastName", p."roomNumber", p."bedNumber",
                   CASE WHEN d."lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
                        WHEN d."lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
                        ELSE 'offline' END as connectionStatus
            FROM devices d
            JOIN deviceassignments da ON d.id = da."deviceId"
            JOIN patients p ON da."patientId" = p.id
            WHERE d."deviceType" = 'watch' AND da.status = 'active'
            ORDER BY p."lastName", p."firstName"
            """

            rows = await conn.fetch(query)

            assignments = []
            for row in rows:
                assignmentDict = dict(row)

                # Convert datetime objects for JSON serialization
                for key, value in assignmentDict.items():
                    if isinstance(value, datetime):
                        assignmentDict[key] = value.isoformat()

                # Add display information
                assignmentDict['patientName'] = f"{assignmentDict['firstName']} {assignmentDict['lastName']}"
                assignmentDict['location'] = f"Room {assignmentDict['roomNumber']}, Bed {assignmentDict['bedNumber']}"
                assignmentDict['watchDisplay'] = f"Watch {assignmentDict.get('serialNumber', '')}"
                assignmentDict['batteryStatus'] = getBatteryStatus(assignmentDict.get('batteryLevel', 0))

                assignments.append(assignmentDict)

            logger.info(f"✅ Retrieved {len(assignments)} assigned watches")

            # Apply staff resolution middleware (resolves assignedBy → assignedByName, assignedByRole)
            response = {
                "success": True,
                "assignedWatches": assignments,
                "count": len(assignments)
            }
            response = await resolve_staff_in_response(response, conn)

            return JSONResponse(content=response)

    except Exception as e:
        logger.error(f"❌ Error getting assigned watches: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get assigned watches: {str(e)}")

@router.post("/assign")
async def assignWatchToPatient(
    assignmentData: dict,
    current_user: dict = Depends(require_medical_staff)  # Doctor or Nurse can assign
):
    """
    Assign an ESP32 watch to a patient

    RBAC: Requires medical staff (doctor or nurse).
    """
    try:
        patientId = assignmentData.get('patientId')
        deviceId = assignmentData.get('deviceId')
        assignedBy = current_user['id']  # Always use authenticated user's ID from JWT token

        if not patientId or not deviceId:
            raise HTTPException(status_code=400, detail="Patient ID and Device ID are required")

        async with getDbConnection() as conn:
            async with conn.transaction():
                # Verify patient exists and is active
                patient = await conn.fetchrow("SELECT * FROM patients WHERE id = $1 AND status = 'active'", patientId)
                if not patient:
                    raise HTTPException(status_code=404, detail="Active patient not found")

                # Verify device exists and is available
                device = await conn.fetchrow("SELECT * FROM devices WHERE id = $1 AND \"deviceType\" = 'watch' AND status = 'available'", deviceId)
                if not device:
                    raise HTTPException(status_code=404, detail="Available watch not found")

                # Check if patient already has a watch assigned
                existingAssignment = await conn.fetchrow(
                    "SELECT * FROM deviceassignments WHERE \"patientId\" = $1 AND status = 'active'",
                    patientId
                )

                now = datetime.now()

                if existingAssignment:
                    # AUTO-UNASSIGN: Mark old watch as inactive and update device status
                    oldDeviceId = existingAssignment['deviceId']

                    await conn.execute("""
                        UPDATE deviceassignments
                        SET status = 'inactive',
                            "unassignedAt" = $1,
                            "unassignedBy" = $2,
                            "unassignmentReason" = 'Auto-unassigned for reassignment'
                        WHERE \"patientId\" = $3 AND status = 'active'
                    """, now, assignedBy, patientId)

                    # Update old device status to available
                    await conn.execute(
                        "UPDATE devices SET status = 'available', \"updatedAt\" = $1 WHERE id = $2",
                        now, oldDeviceId
                    )

                    logger.info(f"🔄 Auto-unassigned existing watch {oldDeviceId} for reassignment by {assignedBy}")

                # Create device assignment (id auto-generated by database sequence)
                assignmentId = await conn.fetchval("""
                    INSERT INTO deviceassignments (\"patientId\", \"deviceId\", \"assignedAt\", \"assignedBy\", status)
                    VALUES ($1, $2, $3, $4, 'active')
                    RETURNING id
                """, patientId, deviceId, now, assignedBy)

                # Update device status (assignment tracked in deviceassignments table)
                await conn.execute(
                    "UPDATE devices SET status = 'assigned', \"updatedAt\" = $1 WHERE id = $2",
                    now, deviceId
                )

                logger.info(f"✅ Assigned watch {device['serialNumber']} to patient {patientId}")

                # Send MQTT notification to ESP32 device
                mqttSuccess = await mqttService.publishAssignment(deviceId, patientId)
                if not mqttSuccess:
                    logger.warning(f"⚠️ MQTT assignment notification failed for {deviceId} - device may not receive assignment until reconnect")

                return JSONResponse(content={
                    "success": True,
                    "assignmentId": assignmentId,
                    "message": f"Watch {device['serialNumber']} assigned to {patient['firstName']} {patient['lastName']}",
                    "mqttNotificationSent": mqttSuccess
                })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error assigning watch: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to assign watch: {str(e)}")

@router.post("/unassign")
async def unassignWatchFromPatient(
    unassignmentData: dict,
    current_user: dict = Depends(require_medical_staff)  # Doctor or Nurse can unassign
):
    """
    Unassign an ESP32 watch from a patient

    RBAC: Requires medical staff (doctor or nurse).
    """
    try:
        deviceId = unassignmentData.get('deviceId')
        patientId = unassignmentData.get('patientId')  # Optional - will be looked up if not provided
        unassignedBy = current_user['id']  # Always use authenticated user's ID from JWT token
        reason = unassignmentData.get('reason', 'Manual unassignment')

        if not deviceId:
            raise HTTPException(status_code=400, detail="Device ID is required")

        async with getDbConnection() as conn:
            async with conn.transaction():
                # If patientId not provided, look it up from device assignment
                if not patientId:
                    assignment = await conn.fetchrow(
                        "SELECT * FROM deviceassignments WHERE \"deviceId\" = $1 AND status = 'active'",
                        deviceId
                    )
                    if not assignment:
                        raise HTTPException(status_code=404, detail="No active assignment found for this device")

                    patientId = assignment['patientId']
                    logger.info(f"🔍 Looked up patientId={patientId} for deviceId={deviceId}")
                else:
                    # Verify assignment exists when patientId is explicitly provided
                    assignment = await conn.fetchrow(
                        "SELECT * FROM deviceassignments WHERE \"patientId\" = $1 AND \"deviceId\" = $2 AND status = 'active'",
                        patientId, deviceId
                    )
                    if not assignment:
                        raise HTTPException(status_code=404, detail="Active assignment not found for patient and device")

                now = datetime.now()

                # Update assignment status
                await conn.execute("""
                    UPDATE deviceassignments
                    SET status = 'inactive', "unassignedAt" = $1, "unassignedBy" = $2, "unassignmentReason" = $3
                    WHERE \"patientId\" = $4 AND \"deviceId\" = $5 AND status = 'active'
                """, now, unassignedBy, reason, patientId, deviceId)

                # Update device status to available (assignment tracked in deviceassignments table)
                await conn.execute(
                    "UPDATE devices SET status = 'available', \"updatedAt\" = $1 WHERE id = $2",
                    now, deviceId
                )

                logger.info(f"✅ Unassigned watch from patient {patientId}, reason: {reason}")

                # Send MQTT deassignment notification to ESP32 device
                mqttSuccess = await mqttService.publishDeassignment(deviceId)
                if not mqttSuccess:
                    logger.warning(f"⚠️ MQTT deassignment notification failed for {deviceId} - device may continue sending vitals until reconnect")

                return JSONResponse(content={
                    "success": True,
                    "message": f"Watch unassigned successfully. Reason: {reason}",
                    "mqttNotificationSent": mqttSuccess
                })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error unassigning watch: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to unassign watch: {str(e)}")

@router.get("/connection-status")
async def getWatchConnectionStatus():
    """Get connection status of all watches"""
    try:
        async with getDbConnection() as conn:
            query = """
            SELECT d.*, da."patientId", p."firstName", p."lastName",
                   CASE WHEN d."lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
                        WHEN d."lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
                        ELSE 'offline' END as "connectionStatus",
                   CAST(EXTRACT(EPOCH FROM (NOW() - d."lastSeen"))/60 AS DOUBLE PRECISION) as "minutesSinceLastSeen"
            FROM devices d
            LEFT JOIN deviceassignments da ON d.id = da."deviceId" AND da.status = 'active'
            LEFT JOIN patients p ON da."patientId" = p.id
            WHERE d."deviceType" = 'watch'
            ORDER BY d.status, d."lastSeen" DESC
            """

            rows = await conn.fetch(query)

            watchStatus = []
            for row in rows:
                statusDict = dict(row)

                # Convert datetime objects for JSON serialization
                for key, value in statusDict.items():
                    if isinstance(value, datetime):
                        statusDict[key] = value.isoformat()

                # Add display information
                statusDict['watchDisplay'] = f"Watch {statusDict.get('serialNumber', '')}"
                statusDict['patientName'] = f"{statusDict['firstName'] or ''} {statusDict['lastName'] or ''}".strip() or 'Unassigned'
                statusDict['batteryStatus'] = getBatteryStatus(statusDict.get('batteryLevel', 0))

                watchStatus.append(statusDict)

            # Count by status
            connected = sum(1 for w in watchStatus if w['connectionStatus'] == 'connected')
            recentlySeen = sum(1 for w in watchStatus if w['connectionStatus'] == 'recentlySeen')
            offline = sum(1 for w in watchStatus if w['connectionStatus'] == 'offline')

            logger.info(f"✅ Watch status: {connected} connected, {recentlySeen} recent, {offline} offline")

            return JSONResponse(content={
                "success": True,
                "watchStatus": watchStatus,
                "summary": {
                    "total": len(watchStatus),
                    "connected": connected,
                    "recentlySeen": recentlySeen,
                    "offline": offline
                }
            })

    except Exception as e:
        logger.error(f"❌ Error getting watch connection status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get watch connection status: {str(e)}")

@router.get("/alerts")
async def getWatchAlerts():
    """Get current watch-related alerts (disconnect, low battery, etc.)"""
    try:
        async with getDbConnection() as conn:
            query = """
            SELECT d.*, da."patientId", p."firstName", p."lastName", p."roomNumber", p."bedNumber",
                   CASE WHEN d."lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
                        WHEN d."lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
                        ELSE 'offline' END as connectionStatus,
                   CAST(EXTRACT(EPOCH FROM (NOW() - d."lastSeen"))/60 AS DOUBLE PRECISION) as minutesSinceLastSeen
            FROM devices d
            JOIN deviceassignments da ON d.id = da."deviceId" AND da.status = 'active'
            JOIN patients p ON da."patientId" = p.id
            WHERE d."deviceType" = 'watch' AND p.status = 'active'
            """

            rows = await conn.fetch(query)

            alerts = []
            for row in rows:
                deviceDict = dict(row)

                # Check for disconnect alert
                if deviceDict['connectionStatus'] == 'offline':
                    alerts.append({
                        "id": f"disconnect{deviceDict['id']}",
                        "type": "watchDisconnect",
                        "severity": "high",
                        "patientId": deviceDict['patientId'],
                        "patientName": f"{deviceDict['firstName']} {deviceDict['lastName']}",
                        "location": f"Room {deviceDict['roomNumber']}, Bed {deviceDict['bedNumber']}",
                        "deviceId": deviceDict['id'],
                        "deviceSerial": deviceDict.get('serialNumber', ''),
                        "message": f"Watch {deviceDict.get('serialNumber', '')} disconnected",
                        "minutesSinceLastSeen": round(deviceDict['minutesSinceLastSeen']),
                        "timestamp": datetime.now().isoformat()
                    })

                # Check for low battery alert
                batteryLevel = deviceDict.get('batteryLevel', 100)
                if batteryLevel <= 20:
                    severity = "critical" if batteryLevel <= 10 else "medium"
                    alerts.append({
                        "id": f"battery{deviceDict['id']}",
                        "type": "lowBattery",
                        "severity": severity,
                        "patientId": deviceDict['patientId'],
                        "patientName": f"{deviceDict['firstName']} {deviceDict['lastName']}",
                        "location": f"Room {deviceDict['roomNumber']}, Bed {deviceDict['bedNumber']}",
                        "deviceId": deviceDict['id'],
                        "deviceSerial": deviceDict.get('serialNumber', ''),
                        "message": f"Watch {deviceDict.get('serialNumber', '')} battery low ({batteryLevel}%)",
                        "batteryLevel": batteryLevel,
                        "timestamp": datetime.now().isoformat()
                    })

            logger.info(f"✅ Found {len(alerts)} watch alerts")

            return JSONResponse(content={
                "success": True,
                "alerts": alerts,
                "count": len(alerts)
            })

    except Exception as e:
        logger.error(f"❌ Error getting watch alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get watch alerts: {str(e)}")

def getBatteryStatus(batteryLevel: int) -> str:
    """Get battery status description"""
    if batteryLevel >= 80:
        return "excellent"
    elif batteryLevel >= 60:
        return "good"
    elif batteryLevel >= 40:
        return "fair"
    elif batteryLevel >= 20:
        return "low"
    else:
        return "critical"