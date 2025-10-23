"""
V2 Unified Device API - Single Source of Truth
Uses devices_enriched view for all device queries
Replaces multiple v1 endpoints with one flexible endpoint
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
import logging

from ...core.database import getDbConnection
from ...core.db_utils import fetchAll, fetchOne
from ...core.auth_dependencies import require_admin, require_medical_staff

router = APIRouter()
logger = logging.getLogger(__name__)

# ================================
# UNIFIED DEVICE QUERY ENDPOINT
# ================================

@router.get("/", dependencies=[Depends(require_medical_staff)])
async def get_devices(
    deviceType: Optional[str] = Query(None, description="Filter by device type (watch, tablet, sensor, etc.)"),
    status: Optional[str] = Query(None, description="Filter by device status (available, assigned, maintenance, etc.)"),
    location: Optional[str] = Query(None, description="Filter by location (ward, room, etc.)"),
    patientId: Optional[str] = Query(None, description="Filter by assigned patient ID"),
    connectionStatus: Optional[str] = Query(None, description="Filter by connection status (connected, recentlySeen, offline)"),
    batteryMin: Optional[int] = Query(None, description="Minimum battery level (0-100)"),
    batteryMax: Optional[int] = Query(None, description="Maximum battery level (0-100)"),
    includeUnassigned: Optional[bool] = Query(True, description="Include unassigned devices"),
    includeAssigned: Optional[bool] = Query(True, description="Include assigned devices"),
    limit: int = Query(100, description="Maximum number of devices to return"),
    offset: int = Query(0, description="Number of devices to skip for pagination")
):
    """
    Unified device query endpoint using devices_enriched view

    This single endpoint replaces multiple v1 endpoints:
    - /devices/available → status=available
    - /devices/assigned → assignmentStatus=active
    - /watch-management/available → deviceType=watch&status=available
    - /watch-management/assigned → deviceType=watch&assignmentStatus=active

    Returns complete device data including:
    - All device fields
    - Current assignment info (if assigned)
    - Patient info (if assigned)
    - Computed fields (connectionStatus, batteryStatus)
    """
    try:
        # Build WHERE clause dynamically based on filters
        where_clauses = []
        params = []
        param_counter = 1

        # Device type filter
        if deviceType and deviceType.lower() != 'all':
            where_clauses.append(f'"deviceType" = ${param_counter}')
            params.append(deviceType)
            param_counter += 1

        # Status filter
        if status and status.lower() != 'all':
            where_clauses.append(f'status = ${param_counter}')
            params.append(status)
            param_counter += 1

        # Location filter
        if location and location.lower() != 'all':
            where_clauses.append(f'location ILIKE ${param_counter}')
            params.append(f'%{location}%')
            param_counter += 1

        # Patient filter
        if patientId:
            where_clauses.append(f'"assignedPatientId" = ${param_counter}')
            params.append(patientId)
            param_counter += 1

        # Connection status filter
        if connectionStatus:
            where_clauses.append(f'"connectionStatus" = ${param_counter}')
            params.append(connectionStatus)
            param_counter += 1

        # Battery level filters
        if batteryMin is not None:
            where_clauses.append(f'"batteryLevel" >= ${param_counter}')
            params.append(batteryMin)
            param_counter += 1

        if batteryMax is not None:
            where_clauses.append(f'"batteryLevel" <= ${param_counter}')
            params.append(batteryMax)
            param_counter += 1

        # Assignment status filter (unassigned/assigned)
        if not includeUnassigned and includeAssigned:
            where_clauses.append('"assignmentStatus" = \'active\'')
        elif includeUnassigned and not includeAssigned:
            where_clauses.append('("assignmentStatus" IS NULL OR "assignmentStatus" != \'active\')')
        # If both true, no filter needed (show all)

        # Build final query
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        query = f"""
            SELECT
                id AS "deviceId",
                id,
                "deviceType",
                name,
                "serialNumber",
                "macAddress",
                "firmwareVersion",
                status,
                location,
                description,
                "batteryLevel",
                "lastSeen",
                "calibrationDate",
                "nextMaintenanceDate",
                "createdAt",
                "updatedAt",
                model,
                manufacturer,
                "assignmentId",
                "assignedPatientId",
                "assignedBy",
                "assignedAt",
                "unassignedBy",
                "unassignedAt",
                "unassignmentReason",
                "assignmentStatus",
                "patientFirstName",
                "patientLastName",
                "roomNumber",
                "bedNumber",
                "patientName",
                "patientLocation",
                "connectionStatus",
                "batteryStatus",
                "minutesSinceLastSeen"
            FROM devices_enriched
            WHERE {where_sql}
            ORDER BY "createdAt" DESC
            LIMIT ${param_counter}
            OFFSET ${param_counter + 1}
        """

        params.extend([limit, offset])

        # Execute query
        async with getDbConnection() as conn:
            # Query already uses $1, $2 style placeholders, call conn.fetch() directly
            devices = await conn.fetch(query, *params)

            # Get total count for pagination
            count_query = f"""
                SELECT COUNT(*) as total
                FROM devices_enriched
                WHERE {where_sql}
            """
            # Count query also uses $N placeholders, call conn.fetchrow() directly
            count_result = await conn.fetchrow(count_query, *params[:-2])  # Exclude limit/offset params
            total = count_result['total'] if count_result else 0

        logger.info(f"✅ Retrieved {len(devices)} devices (total: {total}, filters: {len(where_clauses)})")

        return {
            "devices": devices,
            "count": len(devices),
            "total": total,
            "offset": offset,
            "limit": limit,
            "success": True
        }

    except Exception as e:
        logger.error(f"❌ Error getting devices: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{device_id}", dependencies=[Depends(require_medical_staff)])
async def get_device(device_id: str):
    """
    Get single device by ID with complete data
    Uses devices_enriched view for consistent data
    """
    try:
        query = """
            SELECT
                id AS "deviceId",
                id,
                "deviceType",
                name,
                "serialNumber",
                "macAddress",
                "firmwareVersion",
                status,
                location,
                description,
                "batteryLevel",
                "lastSeen",
                "calibrationDate",
                "nextMaintenanceDate",
                "createdAt",
                "updatedAt",
                model,
                manufacturer,
                "assignmentId",
                "assignedPatientId",
                "assignedBy",
                "assignedAt",
                "unassignedBy",
                "unassignedAt",
                "unassignmentReason",
                "assignmentStatus",
                "patientFirstName",
                "patientLastName",
                "roomNumber",
                "bedNumber",
                "patientName",
                "patientLocation",
                "connectionStatus",
                "batteryStatus",
                "minutesSinceLastSeen"
            FROM devices_enriched
            WHERE id = $1
        """

        async with getDbConnection() as conn:
            device = await fetchOne(conn, query, (device_id,))

        if not device:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

        logger.info(f"✅ Retrieved device: {device_id}")
        return device

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# DEVICE STATISTICS ENDPOINT
# ================================

@router.get("/stats/summary", dependencies=[Depends(require_medical_staff)])
async def get_device_stats():
    """
    Get device pool statistics and summary
    Uses devices_enriched view for accurate counts
    """
    try:
        query = """
            SELECT
                COUNT(*) as "totalDevices",
                COUNT(*) FILTER (WHERE status = 'available') as "availableDevices",
                COUNT(*) FILTER (WHERE "assignmentStatus" = 'active') as "assignedDevices",
                COUNT(*) FILTER (WHERE status = 'maintenance') as "maintenanceDevices",
                COUNT(*) FILTER (WHERE status = 'retired') as "retiredDevices",
                COUNT(*) FILTER (WHERE "connectionStatus" = 'offline') as "offlineDevices",
                COUNT(*) FILTER (WHERE "connectionStatus" = 'connected') as "connectedDevices",
                COUNT(*) FILTER (WHERE "batteryLevel" < 20) as "lowBatteryDevices",
                COUNT(*) FILTER (WHERE "batteryLevel" < 40) as "mediumBatteryDevices",
                COUNT(*) FILTER (WHERE "deviceType" = 'watch') as "totalWatches",
                COUNT(*) FILTER (WHERE "deviceType" = 'tablet') as "totalTablets",
                COUNT(*) FILTER (WHERE "deviceType" = 'sensor') as "totalSensors"
            FROM devices_enriched
        """

        async with getDbConnection() as conn:
            stats = await fetchOne(conn, query)

        logger.info(f"✅ Retrieved device statistics")
        return {
            "summary": stats,
            "success": True
        }

    except Exception as e:
        logger.error(f"❌ Error getting device stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# CONVENIENCE ENDPOINTS (SHORTCUTS)
# ================================

@router.get("/available/watches", dependencies=[Depends(require_medical_staff)])
async def get_available_watches():
    """
    Convenience endpoint: Get available watches
    Shortcut for: GET /devices?deviceType=watch&status=available
    """
    try:
        query = """
            SELECT id AS "deviceId", *
            FROM devices_enriched
            WHERE "deviceType" = 'watch' AND status = 'available'
            ORDER BY name
        """

        async with getDbConnection() as conn:
            watches = await fetchAll(conn, query)

        logger.info(f"✅ Retrieved {len(watches)} available watches")
        return {
            "devices": watches,
            "count": len(watches),
            "success": True
        }

    except Exception as e:
        logger.error(f"❌ Error getting available watches: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/assigned/all", dependencies=[Depends(require_medical_staff)])
async def get_assigned_devices():
    """
    Convenience endpoint: Get all assigned devices
    Shortcut for: GET /devices?includeUnassigned=false
    """
    try:
        query = """
            SELECT id AS "deviceId", *
            FROM devices_enriched
            WHERE "assignmentStatus" = 'active'
            ORDER BY "assignedAt" DESC
        """

        async with getDbConnection() as conn:
            devices = await fetchAll(conn, query)

        logger.info(f"✅ Retrieved {len(devices)} assigned devices")
        return {
            "devices": devices,
            "count": len(devices),
            "success": True
        }

    except Exception as e:
        logger.error(f"❌ Error getting assigned devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/low-battery/all", dependencies=[Depends(require_medical_staff)])
async def get_low_battery_devices():
    """
    Convenience endpoint: Get devices with low battery (< 20%)
    Shortcut for: GET /devices?batteryMax=19
    """
    try:
        query = """
            SELECT id AS "deviceId", *
            FROM devices_enriched
            WHERE "batteryLevel" < 20
            ORDER BY "batteryLevel" ASC
        """

        async with getDbConnection() as conn:
            devices = await fetchAll(conn, query)

        logger.info(f"✅ Retrieved {len(devices)} low battery devices")
        return {
            "devices": devices,
            "count": len(devices),
            "success": True
        }

    except Exception as e:
        logger.error(f"❌ Error getting low battery devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))
