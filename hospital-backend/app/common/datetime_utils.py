"""
Datetime utilities - DEPRECATED - Use app.common.datetime instead.

MIGRATION NOTICE:
This module is being phased out. New code should use:
    from app.common.datetime import now_utc, parse_iso8601, to_iso8601

Backward compatibility wrappers provided for existing code.

Provides:
- ISO8601 parsing with timezone support
- UTC timestamp generation
- Age calculation
- Time window validation
- Date parsing (without time)

Legacy Usage:
    from app.common.datetime_utils import parse_iso8601, to_utc_now

    timestamp = parse_iso8601(data['timestamp'])
    current_time = to_utc_now()
"""

from datetime import datetime, timezone, timedelta, date
from typing import Optional
import logging

# Import from new modular datetime package
from app.common.datetime import now_utc as _now_utc
from app.common.datetime import parse_iso8601 as _parse_iso8601
from app.common.datetime import to_iso8601 as _to_iso8601

logger = logging.getLogger(__name__)


def parse_iso8601(timestamp_str: str) -> datetime:
    """
    Parse ISO8601 timestamp string with timezone support.

    DEPRECATED: Use app.common.datetime.parse_iso8601() instead.
    This is a backward compatibility wrapper.

    Args:
        timestamp_str: ISO8601 formatted timestamp string

    Returns:
        datetime object with timezone info
    """
    return _parse_iso8601(timestamp_str)


def to_utc_now() -> datetime:
    """
    Get current UTC time with timezone info.

    DEPRECATED: Use app.common.datetime.now_utc() instead.
    This is a backward compatibility wrapper.

    Returns:
        Current datetime in UTC with timezone

    Example:
        >>> to_utc_now()
        datetime(2025, 11, 9, 10, 30, 0, tzinfo=timezone.utc)
    """
    return _now_utc()


def format_iso8601(dt: datetime) -> str:
    """
    Format datetime to ISO8601 string.

    DEPRECATED: Use app.common.datetime.to_iso8601() instead.
    This is a backward compatibility wrapper.

    Args:
        dt: datetime object (with or without timezone)

    Returns:
        ISO8601 formatted string

    Example:
        >>> format_iso8601(datetime(2025, 11, 9, 10, 30, 0, tzinfo=timezone.utc))
        '2025-11-09T10:30:00+00:00'
    """
    return _to_iso8601(dt)


def parse_date_only(date_str: str) -> date:
    """
    Parse date string (without time component).

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        date object

    Example:
        >>> parse_date_only("2000-01-15")
        date(2000, 1, 15)
    """
    if not date_str:
        raise ValueError("Date string cannot be empty")

    try:
        return datetime.fromisoformat(date_str).date()
    except ValueError as e:
        logger.error(f"Failed to parse date '{date_str}': {e}")
        raise ValueError(f"Invalid date format: {date_str}")


def calculate_age(date_of_birth: str) -> int:
    """
    Calculate age from date of birth.

    Args:
        date_of_birth: Date of birth in YYYY-MM-DD format or ISO8601

    Returns:
        Age in years

    Example:
        >>> calculate_age("2000-01-15")
        25  # (as of 2025)
    """
    if not date_of_birth:
        raise ValueError("Date of birth cannot be empty")

    # Check if it's a full timestamp or just a date
    if 'T' in date_of_birth:
        dob = parse_iso8601(date_of_birth).date()
    else:
        dob = parse_date_only(date_of_birth)

    today = to_utc_now().date()

    # Calculate age (accounting for birthday not yet occurred this year)
    age = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1

    return age


def is_within_window(
    timestamp: datetime,
    window_minutes: int,
    reference_time: Optional[datetime] = None
) -> bool:
    """
    Check if timestamp is within a time window from reference time.

    Args:
        timestamp: Timestamp to check
        window_minutes: Window size in minutes
        reference_time: Reference time (defaults to now)

    Returns:
        True if timestamp is within window, False otherwise

    Example:
        >>> ts = to_utc_now() - timedelta(minutes=3)
        >>> is_within_window(ts, window_minutes=5)
        True
    """
    if reference_time is None:
        reference_time = to_utc_now()

    # Ensure both are timezone-aware
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)

    time_diff = abs((reference_time - timestamp).total_seconds())
    window_seconds = window_minutes * 60

    return time_diff <= window_seconds


def get_hours_difference(start: datetime, end: datetime) -> float:
    """
    Get difference between two timestamps in hours.

    Args:
        start: Start timestamp
        end: End timestamp

    Returns:
        Difference in hours (float)

    Example:
        >>> start = to_utc_now()
        >>> end = start + timedelta(hours=2)
        >>> get_hours_difference(start, end)
        2.0
    """
    diff = abs((end - start).total_seconds())
    return diff / 3600
