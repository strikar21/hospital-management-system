"""
Universal 2-hour edit window utility for all medical records
"""

from datetime import datetime, timezone
from typing import Union, Dict, Any

def isWithinEditWindow(createdAt: Union[str, datetime], hoursLimit: int = 2) -> bool:
    """
    Universal function to check if ANY medical record is within the edit window
    Works for medications, investigations, therapy, notes - all the same 2-hour rule

    Args:
        createdAt: Creation timestamp (string or datetime)
        hoursLimit: Hours allowed for editing (default 2)

    Returns:
        bool: True if within edit window, False otherwise
    """
    if not createdAt:
        return False

    # Handle both datetime objects and strings
    if isinstance(createdAt, str):
        try:
            creationTime = datetime.fromisoformat(createdAt.replace('Z', '+00:00'))
        except:
            return False
    else:
        creationTime = createdAt

    currentTime = datetime.now()

    # Make both timezone-aware if one is
    if creationTime.tzinfo and not currentTime.tzinfo:
        currentTime = currentTime.replace(tzinfo=timezone.utc)
    elif not creationTime.tzinfo and currentTime.tzinfo:
        creationTime = creationTime.replace(tzinfo=timezone.utc)

    hoursElapsed = (currentTime - creationTime).total_seconds() / 3600
    return hoursElapsed <= hoursLimit

def getRemainingEditTime(createdAt: Union[str, datetime], hoursLimit: int = 2) -> int:
    """
    Get remaining edit time in minutes for any medical record

    Args:
        createdAt: Creation timestamp
        hoursLimit: Hours allowed for editing (default 2)

    Returns:
        int: Remaining minutes (0 if expired)
    """
    if not createdAt:
        return 0

    if isinstance(createdAt, str):
        try:
            creationTime = datetime.fromisoformat(createdAt.replace('Z', '+00:00'))
        except:
            return 0
    else:
        creationTime = createdAt

    currentTime = datetime.now()

    # Make both timezone-aware if one is
    if creationTime.tzinfo and not currentTime.tzinfo:
        currentTime = currentTime.replace(tzinfo=timezone.utc)
    elif not creationTime.tzinfo and currentTime.tzinfo:
        creationTime = creationTime.replace(tzinfo=timezone.utc)

    minutesElapsed = (currentTime - creationTime).total_seconds() / 60
    remainingMinutes = (hoursLimit * 60) - minutesElapsed

    return max(0, int(remainingMinutes))

def checkEditPermission(record: Dict[Any, Any], hoursLimit: int = 2) -> Dict[str, Union[bool, int, str]]:
    """
    Check edit permission for any medical record and return detailed info

    Args:
        record: Database record with createdAt field
        hoursLimit: Hours allowed for editing (default 2)

    Returns:
        dict: {
            'canEdit': bool,
            'remainingMinutes': int,
            'message': str
        }
    """
    # Handle different field names for creation timestamp (prefer camelCase)
    createdAt = record.get('createdAt') or record.get('createdat') or record.get('timestamp')

    if not createdAt:
        return {
            'canEdit': False,
            'remainingMinutes': 0,
            'message': 'Creation timestamp not found'
        }

    canEdit = isWithinEditWindow(createdAt, hoursLimit)
    remainingMinutes = getRemainingEditTime(createdAt, hoursLimit)

    if canEdit:
        if remainingMinutes > 60:
            hours = remainingMinutes // 60
            mins = remainingMinutes % 60
            message = f"{hours}h {mins}m remaining"
        else:
            message = f"{remainingMinutes}m remaining"
    else:
        message = "Edit window expired"

    return {
        'canEdit': canEdit,
        'remainingMinutes': remainingMinutes,
        'message': message
    }