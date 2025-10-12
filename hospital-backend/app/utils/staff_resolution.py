"""
Staff Resolution Utility

Centralized utility for resolving staff IDs to staff details (name, role).
Eliminates code duplication across medications.py, medical_action_service.py, and case sheet queries.

Usage:
    from app.utils.staff_resolution import resolve_staff_names

    # Resolve staff names for multiple records
    medications = await resolve_staff_names(
        conn=conn,
        records=medications_list,
        staff_fields=['prescribedBy', 'modifiedBy']
    )

    # Each record will have new fields added:
    # - prescribedByName, prescribedByRole
    # - modifiedByName, modifiedByRole
"""

from typing import List, Dict, Any, Optional
import asyncpg


async def resolve_staff_names(
    conn: asyncpg.Connection,
    records: List[Dict[str, Any]],
    staff_fields: List[str]
) -> List[Dict[str, Any]]:
    """
    Resolve staff IDs to names and roles for multiple records.

    Args:
        conn: Database connection
        records: List of records with staff ID fields
        staff_fields: List of field names to resolve (e.g., ['prescribedBy', 'performedBy'])

    Returns:
        List of records with added {field}Name and {field}Role fields

    Example:
        Input record:
            {'id': 1, 'prescribedBy': 'DOC0001', 'performedBy': 'NURSE0001'}

        Output record (after resolution with staff_fields=['prescribedBy', 'performedBy']):
            {
                'id': 1,
                'prescribedBy': 'DOC0001',
                'prescribedByName': 'Dr. Smith',
                'prescribedByRole': 'doctor',
                'performedBy': 'NURSE0001',
                'performedByName': 'Nurse Johnson',
                'performedByRole': 'nurse'
            }
    """

    if not records:
        return records

    # Step 1: Collect all unique staff IDs across all fields
    staff_ids = set()
    for record in records:
        for field in staff_fields:
            staff_id = record.get(field)
            if staff_id and staff_id != "SYSTEM":  # Skip SYSTEM user
                staff_ids.add(staff_id)

    if not staff_ids:
        return records

    # Step 2: Fetch staff details in single query
    staff_records = await conn.fetch(
        """
        SELECT id, "firstName", "lastName", role
        FROM staff
        WHERE id = ANY($1::text[])
        """,
        list(staff_ids)
    )

    # Step 3: Build lookup dictionary
    staff_lookup = {}
    for record in staff_records:
        staff_id = record['id']
        first_name = record['firstName'] or ''
        last_name = record['lastName'] or ''
        role = record['role'] or 'Staff'

        # Format name based on role prefix (matching patient_repository pattern)
        if staff_id.startswith('DOC'):
            name = f"Dr. {first_name} {last_name}".strip()
        else:
            name = f"{first_name} {last_name}".strip()

        staff_lookup[staff_id] = {
            'name': name,
            'role': role
        }

    # Step 4: Enrich records with staff details
    for record in records:
        for field in staff_fields:
            staff_id = record.get(field)

            if not staff_id:
                continue

            # Handle SYSTEM user
            if staff_id == "SYSTEM":
                record[f"{field}Name"] = "System"
                record[f"{field}Role"] = "system"
                continue

            # Lookup staff details
            staff_info = staff_lookup.get(staff_id)
            if staff_info:
                record[f"{field}Name"] = staff_info['name']
                record[f"{field}Role"] = staff_info['role']
            else:
                # Staff ID not found (shouldn't happen with FK constraints)
                record[f"{field}Name"] = f"Unknown ({staff_id})"
                record[f"{field}Role"] = "unknown"

    return records


async def get_staff_names(
    conn: asyncpg.Connection,
    staff_ids: List[str]
) -> Dict[str, Dict[str, str]]:
    """
    Get staff details for a list of staff IDs.

    Args:
        conn: Database connection
        staff_ids: List of staff IDs to look up

    Returns:
        Dictionary mapping staff ID to {name, role}

    Example:
        result = await get_staff_names(conn, ['DOC0001', 'NURSE0001'])
        # Returns:
        # {
        #     'DOC0001': {'name': 'Dr. Smith', 'role': 'doctor'},
        #     'NURSE0001': {'name': 'Nurse Johnson', 'role': 'nurse'}
        # }
    """

    if not staff_ids:
        return {}

    # Filter out SYSTEM and None values
    valid_ids = [sid for sid in staff_ids if sid and sid != "SYSTEM"]

    if not valid_ids:
        # Only SYSTEM or empty IDs
        return {
            sid: {'name': 'System', 'role': 'system'}
            for sid in staff_ids if sid == "SYSTEM"
        }

    staff_records = await conn.fetch(
        """
        SELECT id, "firstName", "lastName", role
        FROM staff
        WHERE id = ANY($1::text[])
        """,
        valid_ids
    )

    result = {}
    for record in staff_records:
        staff_id = record['id']
        first_name = record['firstName'] or ''
        last_name = record['lastName'] or ''
        role = record['role'] or 'Staff'

        # Format name based on role prefix (matching patient_repository pattern)
        if staff_id.startswith('DOC'):
            name = f"Dr. {first_name} {last_name}".strip()
        else:
            name = f"{first_name} {last_name}".strip()

        result[staff_id] = {
            'name': name,
            'role': role
        }

    # Add SYSTEM if it was in the input
    if "SYSTEM" in staff_ids:
        result["SYSTEM"] = {'name': 'System', 'role': 'system'}

    return result
