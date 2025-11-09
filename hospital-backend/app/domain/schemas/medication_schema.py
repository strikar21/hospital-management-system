"""
Medication schema - Single source of truth for medication data structure.

This schema is mirrored in frontend:
    hospital-display-app/src/data/schemas/Medication.schema.ts

Any changes here MUST be reflected in frontend schema.

Usage:
    from app.domain.schemas import MedicationRecord

    medication: MedicationRecord = {
        'id': 1,
        'patientId': 'P001',
        'name': 'Aspirin',
        'dosage': '100mg',
        'frequency': 'Once daily',
        'route': 'Oral',
        'prescribedBy': 'DOC001'
    }
"""

from typing import TypedDict, Optional, Literal
from datetime import datetime


# Type aliases
MedicationStatus = Literal['active', 'completed', 'discontinued', 'held']
MedicationRoute = Literal['Oral', 'IV', 'IM', 'SC', 'Topical', 'Inhalation', 'Rectal']


class MedicationRecord(TypedDict, total=False):
    """
    Complete medication order data structure.

    Frontend Mirror: hospital-display-app/src/data/schemas/Medication.schema.ts
    """

    # ========================================
    # MEDICATION IDENTIFICATION
    # ========================================
    id: int                               # Medication order ID (REQUIRED)
    patientId: str                        # Patient UUID (REQUIRED)

    # ========================================
    # MEDICATION DETAILS (Required)
    # ========================================
    name: str                             # Medication name (REQUIRED)
    dosage: str                           # Dosage (e.g., "100mg", "5ml")
    frequency: str                        # Frequency (e.g., "Once daily", "TID")
    route: MedicationRoute                # Route of administration

    # ========================================
    # MEDICATION TIMING
    # ========================================
    startDate: Optional[datetime]         # When medication starts
    endDate: Optional[datetime]           # When medication ends
    duration: Optional[str]               # Duration (e.g., "7 days", "2 weeks")

    # ========================================
    # STATUS AND TRACKING
    # ========================================
    status: Optional[MedicationStatus]    # Medication status
    canEdit: Optional[bool]               # Can be edited (24-hour window)

    # ========================================
    # PRESCRIBER INFORMATION
    # ========================================
    prescribedBy: str                     # Prescriber staff ID (REQUIRED)
    prescribedByName: Optional[str]       # Prescriber name (resolved by backend)
    prescribedByRole: Optional[str]       # Prescriber role (resolved by backend)

    # ========================================
    # AUDIT TRAIL
    # ========================================
    createdBy: Optional[str]              # Who created record
    createdByName: Optional[str]          # Creator name (resolved by backend)
    createdAt: Optional[datetime]         # Creation timestamp
    updatedAt: Optional[datetime]         # Last update timestamp
    modifiedBy: Optional[str]             # Who last modified
    modifiedByName: Optional[str]         # Modifier name (resolved by backend)


class MedicationAdministration(TypedDict):
    """
    Medication administration record.

    Tracks when medication was actually given to patient.
    """
    id: str                               # Administration record ID
    medicationId: int                     # Medication order ID
    patientId: str                        # Patient UUID
    scheduledTime: datetime               # When medication was scheduled
    performedAt: Optional[datetime]       # When actually administered
    performedBy: Optional[str]            # Staff ID who administered
    performedByName: Optional[str]        # Staff name (resolved by backend)
    dosageGiven: Optional[str]            # Actual dosage given
    route: Optional[str]                  # Route used
    status: str                           # scheduled, completed, skipped, refused
    notes: Optional[str]                  # Administration notes
