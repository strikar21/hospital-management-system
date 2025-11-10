"""
Datetime utilities - Single source of truth for all timestamp operations.

Usage:
    from app.common.datetime import now_utc, parse_iso8601, to_iso8601

    # Get current UTC time (timezone-aware)
    current = now_utc()

    # Parse ISO8601 string
    dt = parse_iso8601("2025-11-10T14:30:00Z")

    # Format to ISO8601
    iso_str = to_iso8601(dt)
"""

from .parser import parse_iso8601, parse_timestamp
from .formatter import to_iso8601, format_relative, format_medical
from .utils import now_utc, seconds_since, is_recent

__all__ = [
    'parse_iso8601',
    'parse_timestamp',
    'to_iso8601',
    'format_relative',
    'format_medical',
    'now_utc',
    'seconds_since',
    'is_recent'
]
