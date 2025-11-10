"""Parse timestamp strings to datetime objects."""

from datetime import datetime, timezone
from typing import Union


def parse_iso8601(timestamp_str: str) -> datetime:
    """
    Parse ISO8601 string to UTC datetime (timezone-aware).

    Handles both 'Z' suffix and explicit timezone offsets.

    Args:
        timestamp_str: ISO8601 formatted string (e.g., "2025-11-10T14:30:00Z")

    Returns:
        Timezone-aware datetime in UTC

    Example:
        >>> parse_iso8601("2025-11-10T14:30:00Z")
        datetime(2025, 11, 10, 14, 30, 0, tzinfo=timezone.utc)
    """
    # Handle 'Z' suffix (Zulu time = UTC)
    if timestamp_str.endswith('Z'):
        timestamp_str = timestamp_str.replace('Z', '+00:00')

    dt = datetime.fromisoformat(timestamp_str)

    # Ensure timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


def parse_timestamp(value: Union[str, datetime, int, float]) -> datetime:
    """
    Parse various timestamp formats to datetime.

    Args:
        value: ISO8601 string, datetime object, or Unix epoch (int/float)

    Returns:
        Timezone-aware datetime in UTC

    Example:
        >>> parse_timestamp("2025-11-10T14:30:00Z")
        >>> parse_timestamp(1699627800)
        >>> parse_timestamp(datetime.now())
    """
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    if isinstance(value, str):
        return parse_iso8601(value)

    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)

    raise ValueError(f"Cannot parse timestamp from type {type(value)}")
