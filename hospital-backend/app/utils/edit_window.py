"""
Universal 2-hour edit window utility for all medical records
"""

from datetime import datetime, timezone
from typing import Union, Dict, Any

def is_within_edit_window(created_at: Union[str, datetime], hours_limit: int = 2) -> bool:
    """
    Universal function to check if ANY medical record is within the edit window
    Works for medications, investigations, therapy, notes - all the same 2-hour rule
    
    Args:
        created_at: Creation timestamp (string or datetime)
        hours_limit: Hours allowed for editing (default 2)
    
    Returns:
        bool: True if within edit window, False otherwise
    """
    if not created_at:
        return False
    
    # Handle both datetime objects and strings
    if isinstance(created_at, str):
        try:
            creation_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except:
            return False
    else:
        creation_time = created_at
    
    current_time = datetime.now()
    
    # Make both timezone-aware if one is
    if creation_time.tzinfo and not current_time.tzinfo:
        current_time = current_time.replace(tzinfo=timezone.utc)
    elif not creation_time.tzinfo and current_time.tzinfo:
        creation_time = creation_time.replace(tzinfo=timezone.utc)
    
    hours_elapsed = (current_time - creation_time).total_seconds() / 3600
    return hours_elapsed <= hours_limit

def get_remaining_edit_time(created_at: Union[str, datetime], hours_limit: int = 2) -> int:
    """
    Get remaining edit time in minutes for any medical record
    
    Args:
        created_at: Creation timestamp
        hours_limit: Hours allowed for editing (default 2)
    
    Returns:
        int: Remaining minutes (0 if expired)
    """
    if not created_at:
        return 0
    
    if isinstance(created_at, str):
        try:
            creation_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except:
            return 0
    else:
        creation_time = created_at
    
    current_time = datetime.now()
    
    # Make both timezone-aware if one is
    if creation_time.tzinfo and not current_time.tzinfo:
        current_time = current_time.replace(tzinfo=timezone.utc)
    elif not creation_time.tzinfo and current_time.tzinfo:
        creation_time = creation_time.replace(tzinfo=timezone.utc)
    
    minutes_elapsed = (current_time - creation_time).total_seconds() / 60
    remaining_minutes = (hours_limit * 60) - minutes_elapsed
    
    return max(0, int(remaining_minutes))

def check_edit_permission(record: Dict[Any, Any], hours_limit: int = 2) -> Dict[str, Union[bool, int, str]]:
    """
    Check edit permission for any medical record and return detailed info
    
    Args:
        record: Database record with created_at field
        hours_limit: Hours allowed for editing (default 2)
    
    Returns:
        dict: {
            'can_edit': bool,
            'remaining_minutes': int,
            'message': str
        }
    """
    # Handle different field names for creation timestamp
    created_at = record.get('createdat') or record.get('created_at') or record.get('timestamp')
    
    if not created_at:
        return {
            'can_edit': False,
            'remaining_minutes': 0,
            'message': 'Creation timestamp not found'
        }
    
    can_edit = is_within_edit_window(created_at, hours_limit)
    remaining_minutes = get_remaining_edit_time(created_at, hours_limit)
    
    if can_edit:
        if remaining_minutes > 60:
            hours = remaining_minutes // 60
            mins = remaining_minutes % 60
            message = f"{hours}h {mins}m remaining"
        else:
            message = f"{remaining_minutes}m remaining"
    else:
        message = "Edit window expired"
    
    return {
        'can_edit': can_edit,
        'remaining_minutes': remaining_minutes,
        'message': message
    }