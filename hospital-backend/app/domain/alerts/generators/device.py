"""Generate alerts for device issues."""

from app.domain.schemas import AlertRecord, AlertSeverity
from app.common.datetime import now_utc


def generate_device_alert(
    patient_id: str,
    device_id: str,
    issue: str,
    severity: AlertSeverity = 'medium'
) -> AlertRecord:
    """
    Generate alert for device malfunction or connectivity issue.

    Args:
        patient_id: Patient UUID
        device_id: Device ID with issue
        issue: Description of the issue
        severity: Alert severity ('low', 'medium', 'high', 'critical')

    Returns:
        AlertRecord

    Example:
        >>> alert = generate_device_alert(
        ...     'patient-123',
        ...     'WATCH001',
        ...     'Low battery (15%)',
        ...     severity='medium'
        ... )
    """
    message = f"Device {device_id}: {issue}"

    # Create alert record
    alert: AlertRecord = {
        'id': None,
        'patientId': patient_id,
        'type': 'device',
        'severity': severity,
        'status': 'active',
        'message': message,
        'createdBy': 'system',
        'createdAt': now_utc()
    }

    return alert
