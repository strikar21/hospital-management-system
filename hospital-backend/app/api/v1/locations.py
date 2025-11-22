"""
Location Tracking and Door Scanner Management API

Endpoints for:
- Door scanner configuration and management
- Real-time device location tracking
- Room occupancy queries
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from ...core.database import getDbConnection
from ...services.door_scanner_service import DoorScannerService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/locations", tags=["locations"])


# ================================
# DOOR SCANNER CONFIGURATION
# ================================

@router.put("/door-scanner/{scannerId}/config")
async def updateDoorScannerConfig(
    scannerId: str,
    config: Dict[str, Any]
):
    """Update door scanner configuration (room assignment, location, ward)"""
    try:
        async with getDbConnection() as conn:
            # Validate scanner exists
            scanner = await conn.fetchrow(
                'SELECT id FROM "doorScanners" WHERE id = $1',
                scannerId
            )

            if not scanner:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Door scanner {scannerId} not found"
                )

            # Build update query dynamically
            update_fields = []
            update_values = []
            param_count = 1

            if "roomId" in config:
                update_fields.append(f'"roomId" = ${param_count}')
                update_values.append(config["roomId"])
                param_count += 1

            if "locationDescription" in config:
                update_fields.append(f'"locationDescription" = ${param_count}')
                update_values.append(config["locationDescription"])
                param_count += 1

            if "ward" in config:
                update_fields.append(f'ward = ${param_count}')
                update_values.append(config["ward"])
                param_count += 1

            if "isActive" in config:
                update_fields.append(f'"isActive" = ${param_count}')
                update_values.append(config["isActive"])
                param_count += 1

            if not update_fields:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No valid configuration fields provided"
                )

            # Add updatedAt
            update_fields.append(f'"updatedAt" = ${param_count}')
            update_values.append(datetime.now())
            param_count += 1

            # Add scannerId for WHERE clause
            update_values.append(scannerId)

            query = f'''
                UPDATE "doorScanners"
                SET {", ".join(update_fields)}
                WHERE id = ${param_count}
                RETURNING *
            '''

            updated = await conn.fetchrow(query, *update_values)

            logger.info(f"🔧 Door scanner {scannerId} configuration updated")

            return JSONResponse({
                "success": True,
                "scannerId": scannerId,
                "configuration": {
                    "roomId": updated["roomId"],
                    "locationDescription": updated["locationDescription"],
                    "ward": updated["ward"],
                    "isActive": updated["isActive"],
                    "updatedAt": updated["updatedAt"].isoformat()
                }
            })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating door scanner config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update door scanner configuration: {str(e)}"
        )


@router.get("/door-scanner/{scannerId}")
async def getDoorScannerInfo(scannerId: str):
    """Get door scanner configuration and status"""
    try:
        async with getDbConnection() as conn:
            scanner = await conn.fetchrow(
                '''SELECT ds.*, d.name, d."deviceType", d.status, d."lastSeen"
                   FROM "doorScanners" ds
                   JOIN devices d ON ds.id = d.id
                   WHERE ds.id = $1''',
                scannerId
            )

            if not scanner:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Door scanner {scannerId} not found"
                )

            return JSONResponse({
                "success": True,
                "scanner": {
                    "id": scanner["id"],
                    "name": scanner["name"],
                    "deviceType": scanner["deviceType"],
                    "roomId": scanner["roomId"],
                    "locationDescription": scanner["locationDescription"],
                    "ward": scanner["ward"],
                    "isActive": scanner["isActive"],
                    "status": scanner["status"],
                    "lastSeen": scanner["lastSeen"].isoformat() if scanner["lastSeen"] else None,
                    "lastScanTimestamp": scanner["lastScanTimestamp"].isoformat() if scanner["lastScanTimestamp"] else None
                }
            })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching door scanner info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch door scanner info: {str(e)}"
        )


@router.get("/door-scanners")
async def getAllDoorScanners(
    ward: Optional[str] = None,
    isActive: Optional[bool] = None
):
    """Get all door scanners with optional filtering"""
    try:
        async with getDbConnection() as conn:
            query = '''
                SELECT ds.*, d.name, d."deviceType", d.status, d."lastSeen"
                FROM "doorScanners" ds
                JOIN devices d ON ds.id = d.id
                WHERE 1=1
            '''

            params = []
            param_count = 1

            if ward:
                query += f' AND ds.ward = ${param_count}'
                params.append(ward)
                param_count += 1

            if isActive is not None:
                query += f' AND ds."isActive" = ${param_count}'
                params.append(isActive)
                param_count += 1

            query += ' ORDER BY ds."createdAt" DESC'

            scanners = await conn.fetch(query, *params)

            return JSONResponse({
                "success": True,
                "count": len(scanners),
                "scanners": [
                    {
                        "id": s["id"],
                        "name": s["name"],
                        "roomId": s["roomId"],
                        "locationDescription": s["locationDescription"],
                        "ward": s["ward"],
                        "isActive": s["isActive"],
                        "status": s["status"],
                        "lastScanTimestamp": s["lastScanTimestamp"].isoformat() if s["lastScanTimestamp"] else None
                    }
                    for s in scanners
                ]
            })

    except Exception as e:
        logger.error(f"❌ Error fetching door scanners: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch door scanners: {str(e)}"
        )


# ================================
# LOCATION QUERIES
# ================================

@router.get("/room/{roomId}/occupancy")
async def getRoomOccupancy(roomId: str):
    """Get current devices/patients in a specific room"""
    try:
        async with getDbConnection() as conn:
            occupancy = await DoorScannerService.get_room_occupancy(conn, room_id=roomId)

            return JSONResponse({
                "success": True,
                "roomId": roomId,
                "currentOccupancy": occupancy,
                "deviceCount": len(occupancy),
                "timestamp": datetime.now().isoformat()
            })

    except Exception as e:
        logger.error(f"❌ Error fetching room occupancy: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch room occupancy: {str(e)}"
        )


@router.get("/device/{deviceId}")
async def getDeviceLocation(deviceId: str):
    """Get current location of a specific device"""
    try:
        async with getDbConnection() as conn:
            location = await DoorScannerService.get_device_location(conn, device_id=deviceId)

            if not location:
                return JSONResponse({
                    "success": True,
                    "deviceId": deviceId,
                    "location": None,
                    "message": "Device location not tracked or never detected"
                })

            return JSONResponse({
                "success": True,
                "deviceId": deviceId,
                "location": location,
                "timestamp": datetime.now().isoformat()
            })

    except Exception as e:
        logger.error(f"❌ Error fetching device location: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch device location: {str(e)}"
        )


@router.get("/all-rooms")
async def getAllRoomOccupancy(ward: Optional[str] = None):
    """Get occupancy for all rooms"""
    try:
        async with getDbConnection() as conn:
            all_occupancy = await DoorScannerService.get_all_room_occupancy(conn)

            # Filter by ward if specified
            if ward:
                scanners = await conn.fetch(
                    'SELECT "roomId" FROM "doorScanners" WHERE ward = $1',
                    ward
                )
                ward_rooms = {s["roomId"] for s in scanners}
                all_occupancy = {
                    room: devices
                    for room, devices in all_occupancy.items()
                    if room in ward_rooms
                }

            # Calculate summary stats
            total_devices = sum(len(devices) for devices in all_occupancy.values())
            occupied_rooms = sum(1 for devices in all_occupancy.values() if len(devices) > 0)

            return JSONResponse({
                "success": True,
                "summary": {
                    "totalRooms": len(all_occupancy),
                    "occupiedRooms": occupied_rooms,
                    "totalDevices": total_devices,
                    "ward": ward
                },
                "rooms": all_occupancy,
                "timestamp": datetime.now().isoformat()
            })

    except Exception as e:
        logger.error(f"❌ Error fetching all room occupancy: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch all room occupancy: {str(e)}"
        )
