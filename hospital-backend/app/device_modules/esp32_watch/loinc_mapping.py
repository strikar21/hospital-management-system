"""
LOINC Code Mapping for Vital Signs

Maps ESP32 sensor readings to standardized LOINC codes
Source: https://loinc.org/
"""

from typing import Dict, Any


# Standard LOINC codes for vital signs
LOINC_CODES = {
    "heartRate": {
        "code": "8867-4",
        "display": "Heart rate",
        "unit": "beats/minute",
        "system": "http://loinc.org",
        "category": "vital-signs",
        "ucum": "/min"
    },
    "spo2": {
        "code": "59408-5",
        "display": "Oxygen saturation in Arterial blood by Pulse oximetry",
        "unit": "%",
        "system": "http://loinc.org",
        "category": "vital-signs",
        "ucum": "%"
    },
    "temperature": {
        "code": "8310-5",
        "display": "Body temperature",
        "unit": "Cel",
        "system": "http://loinc.org",
        "category": "vital-signs",
        "ucum": "Cel"
    },
    "systolicBP": {
        "code": "8480-6",
        "display": "Systolic blood pressure",
        "unit": "mm[Hg]",
        "system": "http://loinc.org",
        "category": "vital-signs",
        "ucum": "mm[Hg]"
    },
    "diastolicBP": {
        "code": "8462-4",
        "display": "Diastolic blood pressure",
        "unit": "mm[Hg]",
        "system": "http://loinc.org",
        "category": "vital-signs",
        "ucum": "mm[Hg]"
    },
    "respiratoryRate": {
        "code": "9279-1",
        "display": "Respiratory rate",
        "unit": "breaths/minute",
        "system": "http://loinc.org",
        "category": "vital-signs",
        "ucum": "/min"
    },
    "steps": {
        "code": "41950-7",
        "display": "Number of steps in 24 hour Measured",
        "unit": "steps",
        "system": "http://loinc.org",
        "category": "activity",
        "ucum": "{steps}"
    }
}


# Normal ranges for adults (for alert detection)
NORMAL_RANGES = {
    "heartRate": {"min": 60, "max": 100, "critical_low": 40, "critical_high": 150},
    "spo2": {"min": 95, "max": 100, "critical_low": 90, "critical_high": 100},
    "temperature": {"min": 36.1, "max": 37.2, "critical_low": 35.0, "critical_high": 39.0},
    "systolicBP": {"min": 90, "max": 120, "critical_low": 70, "critical_high": 180},
    "diastolicBP": {"min": 60, "max": 80, "critical_low": 40, "critical_high": 110},
    "respiratoryRate": {"min": 12, "max": 20, "critical_low": 8, "critical_high": 30}
}


def get_loinc_for_vital(vital_type: str) -> Dict[str, Any]:
    """
    Get LOINC coding information for a vital sign type

    Args:
        vital_type: Type of vital (heartRate, spo2, etc.)

    Returns:
        LOINC coding dictionary or None if not found
    """
    return LOINC_CODES.get(vital_type)


def get_normal_range(vital_type: str) -> Dict[str, float]:
    """
    Get normal range for a vital sign

    Args:
        vital_type: Type of vital

    Returns:
        Dictionary with min, max, critical_low, critical_high
    """
    return NORMAL_RANGES.get(vital_type, {})


def is_within_normal_range(vital_type: str, value: float) -> bool:
    """
    Check if a vital sign value is within normal range

    Args:
        vital_type: Type of vital
        value: Measured value

    Returns:
        True if within normal range, False otherwise
    """
    ranges = get_normal_range(vital_type)
    if not ranges:
        return True  # Unknown vital, assume normal

    return ranges["min"] <= value <= ranges["max"]


def is_critical(vital_type: str, value: float) -> bool:
    """
    Check if a vital sign value is in critical range

    Args:
        vital_type: Type of vital
        value: Measured value

    Returns:
        True if critical, False otherwise
    """
    ranges = get_normal_range(vital_type)
    if not ranges:
        return False

    return value < ranges["critical_low"] or value > ranges["critical_high"]
