"""Datetime utility functions."""

from datetime import datetime, timezone


def now_utc() -> datetime:
    """
    Get current UTC time (timezone-aware).

    Returns:
        Current datetime in UTC with timezone info

    Example:
        >>> now_utc()
        datetime(2025, 11, 10, 14, 30, 0, tzinfo=timezone.utc)
    """
    return datetime.now(timezone.utc)


def seconds_since(dt: datetime) -> float:
    """
    Get seconds elapsed since given datetime.

    Args:
        dt: Past datetime

    Returns:
        Seconds elapsed (float)

    Example:
        >>> dt = now_utc() - timedelta(minutes=5)
        >>> seconds_since(dt)
        300.0
    """
    return (now_utc() - dt).total_seconds()


def is_recent(dt: datetime, max_age_seconds: float) -> bool:
    """
    Check if datetime is within max age.

    Args:
        dt: Datetime to check
        max_age_seconds: Maximum age in seconds

    Returns:
        True if dt is within max_age_seconds of now

    Example:
        >>> dt = now_utc() - timedelta(minutes=2)
        >>> is_recent(dt, max_age_seconds=300)  # 5 minutes
        True
    """
    return seconds_since(dt) < max_age_seconds
