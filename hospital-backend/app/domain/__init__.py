"""
Domain layer - Business logic and schemas.

Contains:
- schemas/: TypedDict definitions for all data structures
- vitals/: Vitals domain logic (normalization, thresholds, validation)
- alerts/: Alert domain logic (pipeline, deduplication, severity calculation)
- staff/: Staff domain logic (name resolution, permissions)
- patient/: Patient domain logic (data assembly, edit windows)
"""

# Import all schemas
from .schemas import (
    # Vitals
    VitalsRecord, VitalsThresholds, VITAL_THRESHOLDS,
    # Alerts
    AlertRecord, AlertType, AlertSeverity, AlertStatus,
    AlertDeduplicationWindow, AlertAcknowledgment, AlertResolution,
    # Patients
    PatientRecord, PatientStatus, DischargeStatus, Gender,
    PatientSearchCriteria, PatientListItem,
    # Medications
    MedicationRecord, MedicationStatus, MedicationRoute,
    MedicationAdministration,
    # Staff
    StaffRecord, StaffRole, StaffResolution, StaffCredentials
)

# Import domain business logic
from .vitals import VitalsNormalizer
from .alerts import AlertPipeline, AlertDeduplicator
from .staff import StaffResolver

__all__ = [
    # Schemas - Vitals
    'VitalsRecord',
    'VitalsThresholds',
    'VITAL_THRESHOLDS',

    # Schemas - Alerts
    'AlertRecord',
    'AlertType',
    'AlertSeverity',
    'AlertStatus',
    'AlertDeduplicationWindow',
    'AlertAcknowledgment',
    'AlertResolution',

    # Schemas - Patients
    'PatientRecord',
    'PatientStatus',
    'DischargeStatus',
    'Gender',
    'PatientSearchCriteria',
    'PatientListItem',

    # Schemas - Medications
    'MedicationRecord',
    'MedicationStatus',
    'MedicationRoute',
    'MedicationAdministration',

    # Schemas - Staff
    'StaffRecord',
    'StaffRole',
    'StaffResolution',
    'StaffCredentials',

    # Domain Logic
    'VitalsNormalizer',
    'AlertPipeline',
    'AlertDeduplicator',
    'StaffResolver'
]
