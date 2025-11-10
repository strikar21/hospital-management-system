"""Generate alerts from arrhythmia detection."""

from typing import Dict, Any
from app.domain.schemas import AlertRecord, AlertSeverity
from app.common.datetime import now_utc


def generate_arrhythmia_alert(
    patient_id: str,
    arrhythmia_type: str,
    confidence: float,
    ecg_metrics: Dict[str, Any] = None,
    device_id: str = None
) -> AlertRecord:
    """
    Generate alert from arrhythmia detection.

    Args:
        patient_id: Patient UUID
        arrhythmia_type: Type of arrhythmia detected
        confidence: Detection confidence (0.0-1.0)
        ecg_metrics: ECG metrics that triggered detection
        device_id: Device ID that detected arrhythmia

    Returns:
        AlertRecord

    Example:
        >>> alert = generate_arrhythmia_alert(
        ...     'patient-123',
        ...     'atrial_fibrillation',
        ...     0.95,
        ...     {'hr': 150, 'qrs': 'irregular'}
        ... )
    """
    # Determine severity based on arrhythmia type and confidence
    severity: AlertSeverity = 'medium'

    if arrhythmia_type in ['ventricular_fibrillation', 'ventricular_tachycardia']:
        severity = 'critical'
    elif arrhythmia_type in ['atrial_fibrillation', 'supraventricular_tachycardia']:
        severity = 'high'
    elif confidence >= 0.9:
        severity = 'high'

    # Build human-readable message
    arrhythmia_name_map = {
        'ventricular_fibrillation': 'Ventricular Fibrillation',
        'ventricular_tachycardia': 'Ventricular Tachycardia',
        'atrial_fibrillation': 'Atrial Fibrillation',
        'supraventricular_tachycardia': 'SVT',
        'bradycardia': 'Bradycardia',
        'tachycardia': 'Tachycardia'
    }
    arrhythmia_name = arrhythmia_name_map.get(
        arrhythmia_type,
        arrhythmia_type.replace('_', ' ').title()
    )

    message = f"Arrhythmia Detected: {arrhythmia_name} (confidence: {confidence:.0%})"

    # Create alert record
    alert: AlertRecord = {
        'id': None,
        'patientId': patient_id,
        'type': 'arrhythmia',
        'severity': severity,
        'status': 'active',
        'message': message,
        'createdBy': device_id or 'system',
        'createdAt': now_utc()
    }

    return alert
