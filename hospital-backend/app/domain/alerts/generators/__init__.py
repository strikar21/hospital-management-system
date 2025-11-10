"""
Alert generators - Generate different types of alerts.

Usage:
    from app.domain.alerts.generators import generate_vital_alert, generate_arrhythmia_alert

    alert = generate_vital_alert(patient_id, 'heartrate', 125, device_id)
    alert = generate_arrhythmia_alert(patient_id, 'atrial_fibrillation', 0.95)
"""

from .vital import generate_vital_alert
from .arrhythmia import generate_arrhythmia_alert
from .device import generate_device_alert

__all__ = [
    'generate_vital_alert',
    'generate_arrhythmia_alert',
    'generate_device_alert'
]
