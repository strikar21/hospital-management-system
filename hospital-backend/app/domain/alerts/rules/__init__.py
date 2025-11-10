"""
Alert rules - Single source of truth for alert thresholds and checking.

Usage:
    from app.domain.alerts.rules import VITAL_THRESHOLDS, check_vital_threshold

    # Check if heart rate breaches threshold
    result = check_vital_threshold('heartrate', 125)
    if result:
        severity, threshold_value, message_prefix = result
        print(f"Alert! HR {125} exceeds threshold {threshold_value} (severity: {severity})")
"""

from .thresholds import VITAL_THRESHOLDS, get_threshold
from .checker import check_vital_threshold, check_all_vitals
from .constants import AlertSeverity, AlertType, SEVERITY_ORDER

__all__ = [
    'VITAL_THRESHOLDS',
    'get_threshold',
    'check_vital_threshold',
    'check_all_vitals',
    'AlertSeverity',
    'AlertType',
    'SEVERITY_ORDER'
]
