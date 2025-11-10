"""Format datetime objects to strings."""

from datetime import datetime, timezone


def to_iso8601(dt: datetime) -> str:
    """
    Format datetime to ISO8601 string with 'Z' suffix.

    Args:
        dt: Datetime object (timezone-aware or naive)

    Returns:
        ISO8601 string with 'Z' suffix (e.g., "2025-11-10T14:30:00Z")

    Example:
        >>> to_iso8601(datetime(2025, 11, 10, 14, 30, 0, tzinfo=timezone.utc))
        "2025-11-10T14:30:00Z"
    """
    # Ensure timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # Convert to UTC and format
    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.isoformat().replace('+00:00', 'Z')


def format_relative(dt: datetime) -> str:
    """
    Format datetime as relative time string ("2m ago", "5h ago").

    Args:
        dt: Datetime object

    Returns:
        Human-readable relative time string

    Example:
        >>> format_relative(datetime.now() - timedelta(minutes=5))
        "5m ago"
    """
    from .utils import seconds_since

    elapsed = seconds_since(dt)

    if elapsed < 60:
        return "Just now"
    elif elapsed < 3600:
        mins = int(elapsed / 60)
        return f"{mins}m ago"
    elif elapsed < 86400:
        hours = int(elapsed / 3600)
        return f"{hours}h ago"
    else:
        days = int(elapsed / 86400)
        return f"{days}d ago"


def format_medical(dt: datetime) -> str:
    """
    Format datetime for medical records (24-hour format, ISO date).

    Args:
        dt: Datetime object

    Returns:
        Medical record format: "2025-11-10 14:30:00 UTC"

    Example:
        >>> format_medical(datetime(2025, 11, 10, 14, 30, 0, tzinfo=timezone.utc))
        "2025-11-10 14:30:00 UTC"
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
