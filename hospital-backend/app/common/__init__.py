"""
Common utilities shared across all services.
Provides centralized implementations for cross-cutting concerns.
"""

from .datetime_utils import (
    parse_iso8601,
    to_utc_now,
    format_iso8601,
    calculate_age,
    parse_date_only,
    is_within_window,
    get_hours_difference
)

from .serialization import (
    to_camel_case,
    dict_to_camel_case,
    to_snake_case,
    dict_to_snake_case,
    clean_none_values
)

from .constants import (
    EDIT_WINDOW_HOURS,
    ALERT_DEDUPLICATION_MINUTES,
    MAX_PAGE_SIZE,
    DEFAULT_PAGE_SIZE,
    ALERT_SEVERITY_LOW,
    ALERT_SEVERITY_MEDIUM,
    ALERT_SEVERITY_HIGH,
    ALERT_SEVERITY_CRITICAL,
    ALERT_STATUS_ACTIVE,
    ALERT_STATUS_ACKNOWLEDGED,
    ALERT_STATUS_RESOLVED
)

__all__ = [
    # datetime_utils
    'parse_iso8601',
    'to_utc_now',
    'format_iso8601',
    'calculate_age',
    'parse_date_only',
    'is_within_window',
    'get_hours_difference',

    # serialization
    'to_camel_case',
    'dict_to_camel_case',
    'to_snake_case',
    'dict_to_snake_case',
    'clean_none_values',

    # constants
    'EDIT_WINDOW_HOURS',
    'ALERT_DEDUPLICATION_MINUTES',
    'MAX_PAGE_SIZE',
    'DEFAULT_PAGE_SIZE',
    'ALERT_SEVERITY_LOW',
    'ALERT_SEVERITY_MEDIUM',
    'ALERT_SEVERITY_HIGH',
    'ALERT_SEVERITY_CRITICAL',
    'ALERT_STATUS_ACTIVE',
    'ALERT_STATUS_ACKNOWLEDGED',
    'ALERT_STATUS_RESOLVED'
]
