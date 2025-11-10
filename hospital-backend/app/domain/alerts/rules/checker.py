"""Check vital values against thresholds."""

from typing import Optional, Tuple, Dict, List
from .thresholds import VITAL_THRESHOLDS
from .constants import AlertSeverity


def check_vital_threshold(
    vital_type: str,
    value: float
) -> Optional[Tuple[AlertSeverity, float, str]]:
    """
    Check if vital value breaches threshold.

    Args:
        vital_type: Type of vital (heartrate, oxygen, temperature, etc.)
        value: Current vital value

    Returns:
        Tuple of (severity, threshold_value, message_prefix) if breach detected
        None if value is within normal range

    Example:
        >>> check_vital_threshold('heartrate', 125)
        ('high', 120, 'High')

        >>> check_vital_threshold('heartrate', 75)
        None  # Normal range
    """
    # Check if vital type has thresholds
    if vital_type not in VITAL_THRESHOLDS:
        return None

    threshold = VITAL_THRESHOLDS[vital_type]

    # Check critical low
    if threshold.get('criticalLow') is not None and value <= threshold['criticalLow']:
        return ('critical', threshold['criticalLow'], 'Critical Low')

    # Check critical high
    if threshold.get('criticalHigh') is not None and value >= threshold['criticalHigh']:
        return ('critical', threshold['criticalHigh'], 'Critical High')

    # Check warning low
    if threshold.get('warningLow') is not None and value <= threshold['warningLow']:
        return ('high', threshold['warningLow'], 'Low')

    # Check warning high
    if threshold.get('warningHigh') is not None and value >= threshold['warningHigh']:
        return ('high', threshold['warningHigh'], 'High')

    # Value is within normal range
    return None


def check_all_vitals(vitals: Dict[str, float]) -> List[Tuple[str, AlertSeverity, float, str]]:
    """
    Check all vitals and return list of alerts.

    Args:
        vitals: Dict of vital_type -> value

    Returns:
        List of tuples: (vital_type, severity, threshold_value, message_prefix)

    Example:
        >>> check_all_vitals({'heartrate': 125, 'oxygen': 88})
        [('heartrate', 'high', 120, 'High'), ('oxygen', 'critical', 85, 'Critical Low')]
    """
    alerts = []

    for vital_type, value in vitals.items():
        result = check_vital_threshold(vital_type, value)
        if result:
            severity, threshold_value, message_prefix = result
            alerts.append((vital_type, severity, threshold_value, message_prefix))

    return alerts
