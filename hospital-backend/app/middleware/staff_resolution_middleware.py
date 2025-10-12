"""
Staff Resolution Middleware

Automatically resolves staff ID fields to staff names and roles in API responses.
This middleware ensures EVERY API response that contains staff IDs also includes
the resolved staff names and roles, eliminating inconsistency across endpoints.

Usage:
    from app.middleware import with_staff_resolution

    @router.get("/medications")
    @with_staff_resolution
    async def get_medications(...):
        # Return data with staff IDs
        # Middleware will automatically add Name and Role fields
        return {"medications": [...]}

Key Features:
- Auto-detects 9 staff ID fields: prescribedBy, performedBy, createdBy, modifiedBy,
  assignedBy, authorId, completedBy, acknowledgedBy, editedBy
- Batch resolution (one query for all unique staff IDs)
- Recursive handling of nested objects and arrays
- Special handling for SYSTEM user
- Graceful fallback to "Unknown (ID)" if staff not found
- No changes to existing endpoint code required
"""

from functools import wraps
from typing import Any, Dict, List, Set, Callable
import asyncpg
from fastapi import Request
from app.utils.staff_resolution import get_staff_names


# All staff ID fields that should be automatically resolved
STAFF_ID_FIELDS = [
    'prescribedBy',
    'performedBy',
    'createdBy',
    'modifiedBy',
    'assignedBy',
    'authorId',
    'completedBy',
    'acknowledgedBy',
    'editedBy'
]


async def _collect_staff_ids(data: Any, staff_ids: Set[str]) -> None:
    """
    Recursively collect all staff IDs from response data.

    Args:
        data: Response data (dict, list, or primitive)
        staff_ids: Set to collect staff IDs into (modified in place)
    """
    if isinstance(data, dict):
        # Check all staff ID fields in this dict
        for field in STAFF_ID_FIELDS:
            if field in data and data[field]:
                staff_ids.add(data[field])

        # Recurse into nested values
        for value in data.values():
            await _collect_staff_ids(value, staff_ids)

    elif isinstance(data, list):
        # Recurse into array items
        for item in data:
            await _collect_staff_ids(item, staff_ids)


async def _apply_staff_resolution(
    data: Any,
    staff_lookup: Dict[str, Dict[str, str]]
) -> Any:
    """
    Recursively apply staff resolution to response data.

    Args:
        data: Response data (dict, list, or primitive)
        staff_lookup: Dictionary mapping staff ID to {name, role}

    Returns:
        Data with staff Name and Role fields added
    """
    if isinstance(data, dict):
        resolved = {**data}  # Shallow copy

        # Add Name and Role fields for each staff ID field
        for field in STAFF_ID_FIELDS:
            staff_id = resolved.get(field)

            if not staff_id:
                continue

            name_field = f"{field}Name"
            role_field = f"{field}Role"

            # ALWAYS set Name and Role - middleware is authoritative
            # This overrides any existing values (including 'Unknown' from SQL JOINs)
            staff_info = staff_lookup.get(staff_id)
            if staff_info:
                resolved[name_field] = staff_info['name']
                resolved[role_field] = staff_info['role']
            else:
                # Staff ID not found (shouldn't happen with FK constraints)
                resolved[name_field] = f"Unknown ({staff_id})"
                resolved[role_field] = "unknown"

        # Recurse into nested values
        for key, value in resolved.items():
            resolved[key] = await _apply_staff_resolution(value, staff_lookup)

        return resolved

    elif isinstance(data, list):
        # Recurse into array items
        return [await _apply_staff_resolution(item, staff_lookup) for item in data]

    else:
        # Primitive value - return as is
        return data


async def resolve_staff_in_response(
    response: Any,
    conn: asyncpg.Connection
) -> Any:
    """
    Standalone function that resolves staff IDs in responses.

    This function:
    1. Scans for all staff ID fields recursively in the response
    2. Fetches staff details in ONE batch query
    3. Adds XyzByName and XyzByRole for each XyzBy field
    4. Returns enriched response

    Usage:
        async with getDbConnection() as conn:
            # ... fetch data ...
            response = {"caseEntries": case_entries}

            # Resolve staff IDs before returning
            response = await resolve_staff_in_response(response, conn)
            return response

    Args:
        response: The response data (dict, list, or primitive)
        conn: Database connection

    Returns:
        Enriched response with staff Name and Role fields added

    Notes:
    - Works with dict responses and list responses
    - Handles nested objects and arrays
    - Only adds Name/Role fields if they don't already exist (backward compatible)
    - Gracefully handles errors (returns original response if resolution fails)
    """

    # If response is None or not a dict/list, return as is
    if response is None or not isinstance(response, (dict, list)):
        return response

    # Step 1: Collect all unique staff IDs from response
    staff_ids: Set[str] = set()
    await _collect_staff_ids(response, staff_ids)

    # If no staff IDs found, return response unmodified
    if not staff_ids:
        return response

    # Step 2: Fetch staff details in ONE batch query
    try:
        staff_lookup = await get_staff_names(conn, list(staff_ids))
    except Exception as e:
        # If staff resolution fails, log error but return response unmodified
        # (Don't break the endpoint just because staff resolution failed)
        print(f"⚠️ Staff resolution failed: {e}")
        return response

    # Step 3: Apply staff resolution recursively
    enriched_response = await _apply_staff_resolution(response, staff_lookup)

    return enriched_response
