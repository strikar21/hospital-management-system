"""Patient queries - Optimized database queries for patient data."""

from typing import Optional, List, Dict, Any
import asyncpg


async def get_patient_by_id(conn: asyncpg.Connection, patient_id: str) -> Optional[Dict[str, Any]]:
    """
    Get patient by ID.

    Args:
        conn: Database connection
        patient_id: Patient UUID

    Returns:
        Patient record as dict or None if not found

    Example:
        >>> patient = await get_patient_by_id(conn, "123e4567-e89b-12d3-a456-426614174000")
    """
    query = """
        SELECT
            id, "firstName", "lastName", "dateOfBirth", gender,
            "contactNumber", "emergencyContact", "bloodGroup",
            "admissionDate", "roomNumber", "bedNumber",
            diagnosis, status, "createdAt", "updatedAt"
        FROM patients
        WHERE id = $1
    """

    row = await conn.fetchrow(query, patient_id)
    return dict(row) if row else None


async def get_patients_by_status(
    conn: asyncpg.Connection,
    status: str = 'active',
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get patients by status.

    Args:
        conn: Database connection
        status: Patient status ('active', 'discharged', etc.)
        limit: Maximum number of patients to return

    Returns:
        List of patient records

    Example:
        >>> patients = await get_patients_by_status(conn, 'active', limit=50)
    """
    query = """
        SELECT
            id, "firstName", "lastName", "dateOfBirth", gender,
            "contactNumber", "roomNumber", "bedNumber",
            diagnosis, status, "admissionDate"
        FROM patients
        WHERE status = $1
        ORDER BY "admissionDate" DESC
        LIMIT $2
    """

    rows = await conn.fetch(query, status, limit)
    return [dict(row) for row in rows]
