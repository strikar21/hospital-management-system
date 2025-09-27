"""
Watch Management API endpoints for ESP32 watch assignment and monitoring
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import asyncpg
import logging
from datetime import datetime, timedelta
import uuid

from ...core.database import getDbConnection
# Utils for date serialization
from ...services.websocket_manager import connectionManager

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/available")
async def getAvailableWatches():
    """Get all available ESP32 watches for assignment"""
    try:
        async with getDbConnection() as conn:
            query = """
            SELECT d.*,
                   CASE WHEN d.lastseen > NOW() - INTERVAL '5 minutes' THEN 'connected'
                        WHEN d.lastseen > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
                        ELSE 'offline' END as connectionStatus
            FROM devices d
            WHERE d."deviceType" = 'watch' AND d.status = 'available'
            ORDER BY d.lastseen DESC, d.serialnumber
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
                watchDict['displayName'] = f"Watch {watchDict.get('serialnumber', '')}"
                watchDict['batteryStatus'] = getBatteryStatus(watchDict.get('batterylevel', 0))

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
                   CASE WHEN d.lastseen > NOW() - INTERVAL '5 minutes' THEN 'connected'
                        WHEN d.lastseen > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
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
                assignmentDict['watchDisplay'] = f"Watch {assignmentDict['serialnumber']}"
                assignmentDict['batteryStatus'] = getBatteryStatus(assignmentDict.get('batterylevel', 0))

                assignments.append(assignmentDict)

            logger.info(f"✅ Retrieved {len(assignments)} assigned watches")

            return JSONResponse(content={
                "success": True,
                "assignedWatches": assignments,
                "count": len(assignments)
            })

    except Exception as e:
        logger.error(f"❌ Error getting assigned watches: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get assigned watches: {str(e)}")

@router.post("/assign")
async def assignWatchToPatient(assignmentData: dict):
    """Assign an ESP32 watch to a patient"""
    try:
        patientId = assignmentData.get('patientId')
        deviceId = assignmentData.get('deviceId')
        assignedBy = assignmentData.get('assignedBy', 'System')

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
                if existingAssignment:
                    raise HTTPException(status_code=400, detail="Patient already has a watch assigned")

                assignmentId = str(uuid.uuid4())
                now = datetime.now()

                # Create device assignment
                await conn.execute("""
                    INSERT INTO deviceassignments (id, \"patientId\", \"deviceId\", \"assignedAt\", \"assignedBy\", status)
                    VALUES ($1, $2, $3, $4, $5, 'active')
                """, assignmentId, patientId, deviceId, now, assignedBy)

                # Update device status
                await conn.execute(
                    "UPDATE devices SET status = 'assigned', \"assignedPatientId\" = $1, \"updatedAt\" = $2 WHERE id = $3",
                    patientId, now, deviceId
                )

                # Update patient record
                await conn.execute(
                    "UPDATE patients SET \"assignedDeviceId\" = $1, \"updatedAt\" = $2 WHERE id = $3",
                    deviceId, now, patientId
                )

                logger.info(f"✅ Assigned watch {device['serialnumber']} to patient {patientId}")

                return JSONResponse(content={
                    "success": True,
                    "assignmentId": assignmentId,
                    "message": f"Watch {device['serialnumber']} assigned to {patient['firstName']} {patient['lastName']}"
                })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error assigning watch: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to assign watch: {str(e)}")

@router.post("/unassign")
async def unassignWatchFromPatient(unassignmentData: dict):
    """Unassign an ESP32 watch from a patient"""
    try:
        patientId = unassignmentData.get('patientId')
        deviceId = unassignmentData.get('deviceId')
        unassignedBy = unassignmentData.get('unassignedBy', 'System')
        reason = unassignmentData.get('reason', 'Manual unassignment')

        if not patientId or not deviceId:
            raise HTTPException(status_code=400, detail="Patient ID and Device ID are required")

        async with getDbConnection() as conn:
            async with conn.transaction():
                # Verify assignment exists
                assignment = await conn.fetchrow(
                    "SELECT * FROM deviceassignments WHERE \"patientId\" = $1 AND \"deviceId\" = $2 AND status = 'active'",
                    patientId, deviceId
                )
                if not assignment:
                    raise HTTPException(status_code=404, detail="Active assignment not found")

                now = datetime.now()

                # Update assignment status
                await conn.execute("""
                    UPDATE deviceassignments
                    SET status = 'inactive', unassignedat = $1, unassignedby = $2, unassignmentreason = $3
                    WHERE \"patientId\" = $4 AND \"deviceId\" = $5 AND status = 'active'
                """, now, unassignedBy, reason, patientId, deviceId)

                # Update device status
                await conn.execute(
                    "UPDATE devices SET status = 'available', \"assignedPatientId\" = NULL, \"updatedAt\" = $1 WHERE id = $2",
                    now, deviceId
                )

                # Update patient record
                await conn.execute(
                    "UPDATE patients SET \"assignedDeviceId\" = NULL, \"updatedAt\" = $1 WHERE id = $2",
                    now, patientId
                )

                logger.info(f"✅ Unassigned watch from patient {patientId}, reason: {reason}")

                return JSONResponse(content={
                    "success": True,
                    "message": f"Watch unassigned successfully. Reason: {reason}"
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
                   CASE WHEN d.lastseen > NOW() - INTERVAL '5 minutes' THEN 'connected'
                        WHEN d.lastseen > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
                        ELSE 'offline' END as connectionStatus,
                   EXTRACT(EPOCH FROM (NOW() - d.lastseen))/60 as minutesSinceLastSeen
            FROM devices d
            LEFT JOIN deviceassignments da ON d.id = da."deviceId" AND da.status = 'active'
            LEFT JOIN patients p ON da."patientId" = p.id
            WHERE d."deviceType" = 'watch'
            ORDER BY d.status, d.lastseen DESC
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
                statusDict['watchDisplay'] = f"Watch {statusDict['serialnumber']}"
                statusDict['patientName'] = f"{statusDict['firstName'] or ''} {statusDict['lastName'] or ''}".strip() or 'Unassigned'
                statusDict['batteryStatus'] = getBatteryStatus(statusDict.get('batterylevel', 0))

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
                   CASE WHEN d.lastseen > NOW() - INTERVAL '5 minutes' THEN 'connected'
                        WHEN d.lastseen > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
                        ELSE 'offline' END as connectionStatus,
                   EXTRACT(EPOCH FROM (NOW() - d.lastseen))/60 as minutesSinceLastSeen
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
                        "patientId": deviceDict['"patientId"'],
                        "patientName": f"{deviceDict['firstName']} {deviceDict['lastName']}",
                        "location": f"Room {deviceDict['roomNumber']}, Bed {deviceDict['bedNumber']}",
                        "deviceId": deviceDict['id'],
                        "deviceSerial": deviceDict['serialnumber'],
                        "message": f"Watch {deviceDict['serialnumber']} disconnected",
                        "minutesSinceLastSeen": round(deviceDict['minutesSinceLastSeen']),
                        "timestamp": datetime.now().isoformat()
                    })

                # Check for low battery alert
                batteryLevel = deviceDict.get('batterylevel', 100)
                if batteryLevel <= 20:
                    severity = "critical" if batteryLevel <= 10 else "medium"
                    alerts.append({
                        "id": f"battery{deviceDict['id']}",
                        "type": "lowBattery",
                        "severity": severity,
                        "patientId": deviceDict['"patientId"'],
                        "patientName": f"{deviceDict['firstName']} {deviceDict['lastName']}",
                        "location": f"Room {deviceDict['roomNumber']}, Bed {deviceDict['bedNumber']}",
                        "deviceId": deviceDict['id'],
                        "deviceSerial": deviceDict['serialnumber'],
                        "message": f"Watch {deviceDict['serialnumber']} battery low ({batteryLevel}%)",
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