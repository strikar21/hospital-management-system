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

from .vitals_schema import VitalsRecord, VitalsThresholds
from .alert_schema import AlertRecord
from .patient_schema import PatientRecord
from .medication_schema import MedicationRecord
from .staff_schema import StaffRecord

__all__ = [
    'VitalsRecord',
    'VitalsThresholds',
    'AlertRecord',
    'PatientRecord',
    'MedicationRecord',
    'StaffRecord'
]
