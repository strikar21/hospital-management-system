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

from ...core.database import get_db_connection
from ...utils.transformers import transform_dict_to_camel, serialize_dates_in_dict
from ...services.websocket_manager import connection_manager

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/available")
async def get_available_watches():
    """Get all available ESP32 watches for assignment"""
    try:
        async with get_db_connection() as conn:
            query = """
            SELECT d.*,
                   CASE WHEN d.lastseen > NOW() - INTERVAL '5 minutes' THEN 'connected'
                        WHEN d.lastseen > NOW() - INTERVAL '1 hour' THEN 'recently_seen'
                        ELSE 'offline' END as connection_status
            FROM devices d
            WHERE d.devicetype = 'watch' AND d.status = 'available'
            ORDER BY d.lastseen DESC, d.serialnumber
            """

            rows = await conn.fetch(query)

            watches = []
            for row in rows:
                watch_dict = dict(row)
                serialized_watch = serialize_dates_in_dict(watch_dict)
                transformed_watch = transform_dict_to_camel(serialized_watch)

                # Add display information
                transformed_watch['displayName'] = f"Watch {watch_dict['serialnumber']}"
                transformed_watch['batteryStatus'] = get_battery_status(watch_dict.get('batterylevel', 0))

                watches.append(transformed_watch)

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
async def get_assigned_watches():
    """Get all currently assigned watches with patient information"""
    try:
        async with get_db_connection() as conn:
            query = """
            SELECT d.*, da.*, p.firstname, p.lastname, p.roomnumber, p.bednumber,
                   CASE WHEN d.lastseen > NOW() - INTERVAL '5 minutes' THEN 'connected'
                        WHEN d.lastseen > NOW() - INTERVAL '1 hour' THEN 'recently_seen'
                        ELSE 'offline' END as connection_status
            FROM devices d
            JOIN deviceassignments da ON d.id = da.deviceid
            JOIN patients p ON da.patientid = p.id
            WHERE d.devicetype = 'watch' AND da.status = 'active'
            ORDER BY p.lastname, p.firstname
            """

            rows = await conn.fetch(query)

            assignments = []
            for row in rows:
                assignment_dict = dict(row)
                serialized_assignment = serialize_dates_in_dict(assignment_dict)
                transformed_assignment = transform_dict_to_camel(serialized_assignment)

                # Add display information
                transformed_assignment['patientName'] = f"{assignment_dict['firstname']} {assignment_dict['lastname']}"
                transformed_assignment['location'] = f"Room {assignment_dict['roomnumber']}, Bed {assignment_dict['bednumber']}"
                transformed_assignment['watchDisplay'] = f"Watch {assignment_dict['serialnumber']}"
                transformed_assignment['batteryStatus'] = get_battery_status(assignment_dict.get('batterylevel', 0))

                assignments.append(transformed_assignment)

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
async def assign_watch_to_patient(assignment_data: dict):
    """Assign an ESP32 watch to a patient"""
    try:
        patient_id = assignment_data.get('patientId')
        device_id = assignment_data.get('deviceId')
        assigned_by = assignment_data.get('assignedBy', 'System')

        if not patient_id or not device_id:
            raise HTTPException(status_code=400, detail="Patient ID and Device ID are required")

        async with get_db_connection() as conn:
            async with conn.transaction():
                # Verify patient exists and is active
                patient = await conn.fetchrow("SELECT * FROM patients WHERE id = $1 AND status = 'active'", patient_id)
                if not patient:
                    raise HTTPException(status_code=404, detail="Active patient not found")

                # Verify device exists and is available
                device = await conn.fetchrow("SELECT * FROM devices WHERE id = $1 AND devicetype = 'watch' AND status = 'available'", device_id)
                if not device:
                    raise HTTPException(status_code=404, detail="Available watch not found")

                # Check if patient already has a watch assigned
                existing_assignment = await conn.fetchrow(
                    "SELECT * FROM deviceassignments WHERE patientid = $1 AND status = 'active'",
                    patient_id
                )
                if existing_assignment:
                    raise HTTPException(status_code=400, detail="Patient already has a watch assigned")

                assignment_id = str(uuid.uuid4())
                now = datetime.now()

                # Create device assignment
                await conn.execute("""
                    INSERT INTO deviceassignments (id, patientid, deviceid, assignedat, assignedby, status)
                    VALUES ($1, $2, $3, $4, $5, 'active')
                """, assignment_id, patient_id, device_id, now, assigned_by)

                # Update device status
                await conn.execute(
                    "UPDATE devices SET status = 'assigned', assignedpatientid = $1, updatedat = $2 WHERE id = $3",
                    patient_id, now, device_id
                )

                # Update patient record
                await conn.execute(
                    "UPDATE patients SET assigneddeviceid = $1, updatedat = $2 WHERE id = $3",
                    device_id, now, patient_id
                )

                logger.info(f"✅ Assigned watch {device['serialnumber']} to patient {patient_id}")

                return JSONResponse(content={
                    "success": True,
                    "assignmentId": assignment_id,
                    "message": f"Watch {device['serialnumber']} assigned to {patient['firstname']} {patient['lastname']}"
                })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error assigning watch: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to assign watch: {str(e)}")

@router.post("/unassign")
async def unassign_watch_from_patient(unassignment_data: dict):
    """Unassign an ESP32 watch from a patient"""
    try:
        patient_id = unassignment_data.get('patientId')
        device_id = unassignment_data.get('deviceId')
        unassigned_by = unassignment_data.get('unassignedBy', 'System')
        reason = unassignment_data.get('reason', 'Manual unassignment')

        if not patient_id or not device_id:
            raise HTTPException(status_code=400, detail="Patient ID and Device ID are required")

        async with get_db_connection() as conn:
            async with conn.transaction():
                # Verify assignment exists
                assignment = await conn.fetchrow(
                    "SELECT * FROM deviceassignments WHERE patientid = $1 AND deviceid = $2 AND status = 'active'",
                    patient_id, device_id
                )
                if not assignment:
                    raise HTTPException(status_code=404, detail="Active assignment not found")

                now = datetime.now()

                # Update assignment status
                await conn.execute("""
                    UPDATE deviceassignments
                    SET status = 'inactive', unassignedat = $1, unassignedby = $2, unassignmentreason = $3
                    WHERE patientid = $4 AND deviceid = $5 AND status = 'active'
                """, now, unassigned_by, reason, patient_id, device_id)

                # Update device status
                await conn.execute(
                    "UPDATE devices SET status = 'available', assignedpatientid = NULL, updatedat = $1 WHERE id = $2",
                    now, device_id
                )

                # Update patient record
                await conn.execute(
                    "UPDATE patients SET assigneddeviceid = NULL, updatedat = $1 WHERE id = $2",
                    now, patient_id
                )

                logger.info(f"✅ Unassigned watch from patient {patient_id}, reason: {reason}")

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
async def get_watch_connection_status():
    """Get connection status of all watches"""
    try:
        async with get_db_connection() as conn:
            query = """
            SELECT d.*, da.patientid, p.firstname, p.lastname,
                   CASE WHEN d.lastseen > NOW() - INTERVAL '5 minutes' THEN 'connected'
                        WHEN d.lastseen > NOW() - INTERVAL '1 hour' THEN 'recently_seen'
                        ELSE 'offline' END as connection_status,
                   EXTRACT(EPOCH FROM (NOW() - d.lastseen))/60 as minutes_since_last_seen
            FROM devices d
            LEFT JOIN deviceassignments da ON d.id = da.deviceid AND da.status = 'active'
            LEFT JOIN patients p ON da.patientid = p.id
            WHERE d.devicetype = 'watch'
            ORDER BY d.status, d.lastseen DESC
            """

            rows = await conn.fetch(query)

            watch_status = []
            for row in rows:
                status_dict = dict(row)
                serialized_status = serialize_dates_in_dict(status_dict)
                transformed_status = transform_dict_to_camel(serialized_status)

                # Add display information
                transformed_status['watchDisplay'] = f"Watch {status_dict['serialnumber']}"
                transformed_status['patientName'] = f"{status_dict['firstname'] or ''} {status_dict['lastname'] or ''}".strip() or 'Unassigned'
                transformed_status['batteryStatus'] = get_battery_status(status_dict.get('batterylevel', 0))

                watch_status.append(transformed_status)

            # Count by status
            connected = sum(1 for w in watch_status if w['connectionStatus'] == 'connected')
            recently_seen = sum(1 for w in watch_status if w['connectionStatus'] == 'recently_seen')
            offline = sum(1 for w in watch_status if w['connectionStatus'] == 'offline')

            logger.info(f"✅ Watch status: {connected} connected, {recently_seen} recent, {offline} offline")

            return JSONResponse(content={
                "success": True,
                "watchStatus": watch_status,
                "summary": {
                    "total": len(watch_status),
                    "connected": connected,
                    "recentlySeen": recently_seen,
                    "offline": offline
                }
            })

    except Exception as e:
        logger.error(f"❌ Error getting watch connection status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get watch connection status: {str(e)}")

@router.get("/alerts")
async def get_watch_alerts():
    """Get current watch-related alerts (disconnect, low battery, etc.)"""
    try:
        async with get_db_connection() as conn:
            query = """
            SELECT d.*, da.patientid, p.firstname, p.lastname, p.roomnumber, p.bednumber,
                   CASE WHEN d.lastseen > NOW() - INTERVAL '5 minutes' THEN 'connected'
                        WHEN d.lastseen > NOW() - INTERVAL '1 hour' THEN 'recently_seen'
                        ELSE 'offline' END as connection_status,
                   EXTRACT(EPOCH FROM (NOW() - d.lastseen))/60 as minutes_since_last_seen
            FROM devices d
            JOIN deviceassignments da ON d.id = da.deviceid AND da.status = 'active'
            JOIN patients p ON da.patientid = p.id
            WHERE d.devicetype = 'watch' AND p.status = 'active'
            """

            rows = await conn.fetch(query)

            alerts = []
            for row in rows:
                device_dict = dict(row)

                # Check for disconnect alert
                if device_dict['connection_status'] == 'offline':
                    alerts.append({
                        "id": f"disconnect_{device_dict['id']}",
                        "type": "watch_disconnect",
                        "severity": "high",
                        "patientId": device_dict['patientid'],
                        "patientName": f"{device_dict['firstname']} {device_dict['lastname']}",
                        "location": f"Room {device_dict['roomnumber']}, Bed {device_dict['bednumber']}",
                        "deviceId": device_dict['id'],
                        "deviceSerial": device_dict['serialnumber'],
                        "message": f"Watch {device_dict['serialnumber']} disconnected",
                        "minutesSinceLastSeen": round(device_dict['minutes_since_last_seen']),
                        "timestamp": datetime.now().isoformat()
                    })

                # Check for low battery alert
                battery_level = device_dict.get('batterylevel', 100)
                if battery_level <= 20:
                    severity = "critical" if battery_level <= 10 else "medium"
                    alerts.append({
                        "id": f"battery_{device_dict['id']}",
                        "type": "low_battery",
                        "severity": severity,
                        "patientId": device_dict['patientid'],
                        "patientName": f"{device_dict['firstname']} {device_dict['lastname']}",
                        "location": f"Room {device_dict['roomnumber']}, Bed {device_dict['bednumber']}",
                        "deviceId": device_dict['id'],
                        "deviceSerial": device_dict['serialnumber'],
                        "message": f"Watch {device_dict['serialnumber']} battery low ({battery_level}%)",
                        "batteryLevel": battery_level,
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

def get_battery_status(battery_level: int) -> str:
    """Get battery status description"""
    if battery_level >= 80:
        return "excellent"
    elif battery_level >= 60:
        return "good"
    elif battery_level >= 40:
        return "fair"
    elif battery_level >= 20:
        return "low"
    else:
        return "critical"