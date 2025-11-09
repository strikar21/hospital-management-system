"""
Domain schemas - Single source of truth for all data structures.

These schemas are mirrored in frontend TypeScript interfaces.
Any changes here MUST be reflected in:
- hospital-display-app/src/data/schemas/

Schemas:
- VitalsRecord: Complete vitals data structure
- AlertRecord: Alert data structure
- PatientRecord: Patient demographic and medical data
- MedicationRecord: Medication order data
- InvestigationRecord: Investigation/lab order data
- TherapyRecord: Therapy prescription data
- StaffRecord: Staff member data
"""

from .vitals_schema import (
    VitalsRecord,
    VitalsThresholds,
    VITAL_THRESHOLDS
)
from .alert_schema import (
    AlertRecord,
    AlertType,
    AlertSeverity,
    AlertStatus,
    AlertDeduplicationWindow,
    AlertAcknowledgment,
    AlertResolution
)
from .patient_schema import (
    PatientRecord,
    PatientStatus,
    DischargeStatus,
    Gender,
    PatientSearchCriteria,
    PatientListItem
)
from .medication_schema import (
    MedicationRecord,
    MedicationStatus,
    MedicationRoute,
    MedicationAdministration
)
from .staff_schema import (
    StaffRecord,
    StaffRole,
    StaffResolution,
    StaffCredentials
)

__all__ = [
    # Vitals
    'VitalsRecord',
    'VitalsThresholds',
    'VITAL_THRESHOLDS',

    # Alerts
    'AlertRecord',
    'AlertType',
    'AlertSeverity',
    'AlertStatus',
    'AlertDeduplicationWindow',
    'AlertAcknowledgment',
    'AlertResolution',

    # Patients
    'PatientRecord',
    'PatientStatus',
    'DischargeStatus',
    'Gender',
    'PatientSearchCriteria',
    'PatientListItem',

    # Medications
    'MedicationRecord',
    'MedicationStatus',
    'MedicationRoute',
    'MedicationAdministration',

    # Staff
    'StaffRecord',
    'StaffRole',
    'StaffResolution',
    'StaffCredentials'
]
