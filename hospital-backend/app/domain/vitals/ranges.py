"""Vital sign valid ranges for validation."""

from typing import Dict, Tuple, Optional

# Valid ranges for each vital sign
# Format: (min, max) - values outside this range are invalid (likely sensor error)
VITAL_RANGES: Dict[str, Tuple[float, float]] = {
    'heartrate': (20, 300),          # bpm - physiologically possible range
    'oxygen': (0, 100),               # % - SpO2 saturation percentage
    'temperature': (25.0, 45.0),      # °C - Body temperature range
    'respiratory': (0, 60),           # breaths/min
    'systolic': (40, 300),            # mmHg - Systolic blood pressure
    'diastolic': (20, 200),           # mmHg - Diastolic blood pressure
    'batteryLevel': (0, 100),         # % - Device battery
    'signalQuality': (0, 100)         # % - Signal quality
}


def is_valid_vital(vital_type: str, value: float) -> bool:
    """
    Check if vital value is within valid physiological range.

    Args:
        vital_type: Type of vital
        value: Vital value

    Returns:
        True if valid, False if outside physiological range

    Example:
        >>> is_valid_vital('heartrate', 75)
        True
        >>> is_valid_vital('heartrate', 500)  # Impossible value
        False
    """
    if vital_type not in VITAL_RANGES:
        return True  # Unknown vital type, assume valid

    min_val, max_val = VITAL_RANGES[vital_type]
    return min_val <= value <= max_val


def get_valid_range(vital_type: str) -> Optional[Tuple[float, float]]:
    """
    Get valid range for vital type.

    Args:
        vital_type: Type of vital

    Returns:
        Tuple of (min, max) or None if unknown vital type

    Example:
        >>> get_valid_range('heartrate')
        (20, 300)
    """
    return VITAL_RANGES.get(vital_type)
