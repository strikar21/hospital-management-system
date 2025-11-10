"""Vitals queries - Optimized database queries for vitals data."""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import asyncpg


async def get_latest_vitals(
    conn: asyncpg.Connection,
    patient_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get latest vitals for patient from TimescaleDB.

    Args:
        conn: Database connection (TimescaleDB)
        patient_id: Patient UUID

    Returns:
        Latest vitals record or None

    Example:
        >>> vitals = await get_latest_vitals(conn, "123e4567-e89b-12d3-a456-426614174000")
    """
    query = """
        SELECT
            time, "patientId", "heartRate", "respiratoryRate",
            "oxygenSaturation", "skinTemperature",
            "systolicPressure", "diastolicPressure",
            "batteryLevel", "signalQuality"
        FROM vitals_realtime
        WHERE "patientId" = $1
        ORDER BY time DESC
        LIMIT 1
    """

    row = await conn.fetchrow(query, patient_id)
    return dict(row) if row else None


async def get_vitals_history(
    conn: asyncpg.Connection,
    patient_id: str,
    hours: int = 24,
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """
    Get vitals history for patient.

    Args:
        conn: Database connection (TimescaleDB)
        patient_id: Patient UUID
        hours: Number of hours of history to fetch
        limit: Maximum number of records to return

    Returns:
        List of vitals records ordered by time DESC

    Example:
        >>> vitals = await get_vitals_history(conn, patient_id, hours=12, limit=500)
    """
    query = """
        SELECT
            time, "patientId", "heartRate", "respiratoryRate",
            "oxygenSaturation", "skinTemperature",
            "systolicPressure", "diastolicPressure",
            "batteryLevel", "signalQuality"
        FROM vitals_realtime
        WHERE "patientId" = $1
          AND time > NOW() - INTERVAL '{hours} hours'
        ORDER BY time DESC
        LIMIT $2
    """.format(hours=hours)

    rows = await conn.fetch(query, patient_id, limit)
    return [dict(row) for row in rows]
