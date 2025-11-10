"""
Vital sign thresholds - Single source of truth.

IMPORTANT: These thresholds are for ALERTING purposes.
Clinical normal ranges may differ. Consult medical staff before changing.

Indian Medical Guidelines Compliance:
- Heart Rate: Based on Indian Council of Medical Research (ICMR) guidelines
- SpO2: COVID-19 management guidelines (AIIMS/ICMR)
- Temperature: Standard Celsius ranges per Indian medical practice
"""

from typing import Dict, Any, Optional, Tuple

# SINGLE SOURCE OF TRUTH for all vital thresholds
VITAL_THRESHOLDS: Dict[str, Dict[str, Any]] = {
    'heartrate': {
        'unit': 'bpm',
        'criticalLow': 40,      # Severe bradycardia
        'warningLow': 50,       # Bradycardia
        'warningHigh': 120,     # Tachycardia
        'criticalHigh': 150,    # Severe tachycardia
        'normalRange': (60, 100)
    },

    'oxygen': {
        'unit': '%',
        'criticalLow': 85,      # Severe hypoxia (per ICMR COVID guidelines)
        'warningLow': 90,       # Hypoxia
        'warningHigh': None,    # No upper limit for SpO2
        'criticalHigh': None,
        'normalRange': (95, 100)
    },

    'temperature': {
        'unit': '°C',
        'criticalLow': 35.0,    # Hypothermia
        'warningLow': 36.0,     # Low-grade hypothermia
        'warningHigh': 38.0,    # Fever
        'criticalHigh': 39.5,   # High fever
        'normalRange': (36.5, 37.5)
    },

    'respiratory': {
        'unit': '/min',
        'criticalLow': 8,       # Respiratory depression
        'warningLow': 10,       # Bradypnea
        'warningHigh': 24,      # Tachypnea
        'criticalHigh': 30,     # Severe tachypnea
        'normalRange': (12, 20)
    },

    'systolic': {
        'unit': 'mmHg',
        'criticalLow': 90,      # Hypotension
        'warningLow': 100,      # Low BP
        'warningHigh': 140,     # Hypertension
        'criticalHigh': 180,    # Severe hypertension
        'normalRange': (110, 130)
    },

    'diastolic': {
        'unit': 'mmHg',
        'criticalLow': 60,      # Hypotension
        'warningLow': 65,       # Low BP
        'warningHigh': 90,      # Hypertension
        'criticalHigh': 110,    # Severe hypertension
        'normalRange': (70, 85)
    }
}


def get_threshold(vital_type: str) -> Optional[Dict[str, Any]]:
    """
    Get threshold configuration for vital type.

    Args:
        vital_type: Type of vital (heartrate, oxygen, etc.)

    Returns:
        Threshold dict or None if vital type not found

    Example:
        >>> get_threshold('heartrate')
        {'unit': 'bpm', 'criticalLow': 40, ...}
    """
    return VITAL_THRESHOLDS.get(vital_type)
