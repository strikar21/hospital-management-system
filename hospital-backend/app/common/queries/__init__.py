"""
Query utilities - Prepared statements for common database queries.

Usage:
    from app.common.queries import get_patient_by_id, get_device_assignment

    async with pool.acquire() as conn:
        patient = await get_patient_by_id(conn, patient_id)
        device = await get_device_assignment(conn, patient_id)
"""

from .patient import get_patient_by_id, get_patients_by_status
from .device import get_device_assignment, get_device_by_id, get_available_devices
from .vitals import get_latest_vitals, get_vitals_history

__all__ = [
    'get_patient_by_id',
    'get_patients_by_status',
    'get_device_assignment',
    'get_device_by_id',
    'get_available_devices',
    'get_latest_vitals',
    'get_vitals_history'
]
