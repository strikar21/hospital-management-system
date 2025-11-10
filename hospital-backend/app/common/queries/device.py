"""Device queries - Optimized database queries for device data."""

from typing import Optional, List, Dict, Any
import asyncpg


async def get_device_by_id(conn: asyncpg.Connection, device_id: str) -> Optional[Dict[str, Any]]:
    """
    Get device by ID.

    Args:
        conn: Database connection
        device_id: Device UUID

    Returns:
        Device record as dict or None if not found

    Example:
        >>> device = await get_device_by_id(conn, "WATCH001")
    """
    query = """
        SELECT
            id, "deviceType", status, "serialNumber",
            "firmwareVersion", "batteryLevel", "lastSeen",
            "createdAt", "updatedAt"
        FROM devices
        WHERE id = $1
    """

    row = await conn.fetchrow(query, device_id)
    return dict(row) if row else None


async def get_device_assignment(
    conn: asyncpg.Connection,
    patient_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get active device assignment for patient.

    Args:
        conn: Database connection
        patient_id: Patient UUID

    Returns:
        Device assignment record or None if no active assignment

    Example:
        >>> assignment = await get_device_assignment(conn, "123e4567-e89b-12d3-a456-426614174000")
    """
    query = """
        SELECT
            id, "patientId", "deviceId", status,
            "assignedAt", "assignedBy"
        FROM deviceassignments
        WHERE "patientId" = $1 AND status = 'active'
        LIMIT 1
    """

    row = await conn.fetchrow(query, patient_id)
    return dict(row) if row else None


async def get_available_devices(
    conn: asyncpg.Connection,
    device_type: str = 'watch',
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get available devices for assignment.

    Args:
        conn: Database connection
        device_type: Type of device ('watch', 'monitor', etc.)
        limit: Maximum number of devices to return

    Returns:
        List of available device records

    Example:
        >>> devices = await get_available_devices(conn, 'watch', limit=10)
    """
    query = """
        SELECT
            id, "deviceType", status, "serialNumber",
            "firmwareVersion", "batteryLevel"
        FROM devices
        WHERE "deviceType" = $1 AND status = 'available'
        ORDER BY "lastSeen" DESC
        LIMIT $2
    """

    rows = await conn.fetch(query, device_type, limit)
    return [dict(row) for row in rows]
