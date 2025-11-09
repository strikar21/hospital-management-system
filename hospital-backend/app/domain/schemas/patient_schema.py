"""
Patient schema - Single source of truth for patient data structure.

This schema is mirrored in frontend:
    hospital-display-app/src/data/schemas/Patient.schema.ts

Any changes here MUST be reflected in frontend schema.

Usage:
    from app.domain.schemas import PatientRecord

    patient: PatientRecord = {
        'id': 'P001',
        'firstName': 'John',
        'lastName': 'Doe',
        'dateOfBirth': date(1980, 1, 15),
        'admissionDate': datetime.now(timezone.utc)
    }
"""

from typing import TypedDict, Optional, List, Literal
from datetime import datetime, date


# Type aliases
PatientStatus = Literal['active', 'critical', 'emergency', 'pendingDischarge', 'discharged']
DischargeStatus = Literal['active', 'requested', 'adminapproved', 'discharged']
Gender = Literal['Male', 'Female', 'Other']


class PatientRecord(TypedDict, total=False):
    """
    Complete patient demographic and medical data structure.

    Frontend Mirror: hospital-display-app/src/data/schemas/Patient.schema.ts
    """

    # ========================================
    # PATIENT IDENTIFICATION (Required)
    # ========================================
    id: str                               # Patient UUID (REQUIRED)
    firstName: str                        # First name (REQUIRED)
    lastName: str                         # Last name (REQUIRED)

    # ========================================
    # DEMOGRAPHICS
    # ========================================
    dateOfBirth: Optional[date]           # Date of birth
    age: Optional[int]                    # Age in years (calculated by backend)
    gender: Optional[Gender]              # Gender
    phoneNumber: Optional[str]            # Contact phone
    emergencyContactName: Optional[str]   # Emergency contact name
    emergencyContactPhone: Optional[str]  # Emergency contact phone

    # ========================================
    # MEDICAL INFORMATION
    # ========================================
    bloodType: Optional[str]              # Blood type (A+, B-, etc.)
    allergies: Optional[str]              # Known allergies (text field)
    medicalHistory: Optional[str]         # Medical history summary
    currentMedications: Optional[str]     # Current medications at admission
    diagnosis: Optional[str]              # Primary diagnosis
    codeStatus: Optional[str]             # Code status (fullcode, dnr, etc.)

    # ========================================
    # ADMISSION/DISCHARGE
    # ========================================
    admissionDate: Optional[datetime]     # Admission timestamp
    dischargeDate: Optional[datetime]     # Discharge timestamp
    status: Optional[PatientStatus]       # Current patient status
    dischargeStatus: Optional[DischargeStatus] # Discharge workflow status
    recommendedFrom: Optional[str]        # Recommendation source

    # ========================================
    # BED ASSIGNMENT (Manual Entry)
    # ========================================
    roomNumber: Optional[str]             # Room number (entered by nurse)
    bedNumber: Optional[str]              # Bed number (entered by nurse)

    # ========================================
    # DEVICE ASSIGNMENT
    # ========================================
    assignedDeviceId: Optional[str]       # ESP32 watch device ID
    deviceStatus: Optional[str]           # connected, disconnected, offline, lowBattery
    deviceBatteryLevel: Optional[int]     # Device battery 0-100
    deviceLastSeen: Optional[str]         # Device last seen timestamp
    deviceSerialNumber: Optional[str]     # Device serial number
    deviceName: Optional[str]             # Device display name
    deviceAssignedAt: Optional[str]       # When device was assigned
    deviceAssignedBy: Optional[str]       # Who assigned the device

    # ========================================
    # STAFF ASSIGNMENTS
    # ========================================
    attendingPhysician: Optional[str]     # Attending physician staff ID
    attendingPhysicianName: Optional[str] # Physician name (resolved by backend)
    nurseInCharge: Optional[str]          # Nurse staff ID
    nurseInChargeName: Optional[str]      # Nurse name (resolved by backend)

    # ========================================
    # AUDIT TRAIL
    # ========================================
    createdAt: Optional[datetime]         # Record creation timestamp
    updatedAt: Optional[datetime]         # Last update timestamp


class PatientSearchCriteria(TypedDict, total=False):
    """
    Patient search/filter criteria.

    Used for patient list queries with filtering.
    """
    status: Optional[PatientStatus]       # Filter by status
    department: Optional[str]             # Filter by department
    ward: Optional[str]                   # Filter by ward
    attendingPhysician: Optional[str]     # Filter by physician
    roomNumber: Optional[str]             # Filter by room
    searchTerm: Optional[str]             # Search by name/ID


class PatientListItem(TypedDict):
    """
    Minimal patient data for list views.

    Lighter weight than full PatientRecord for dashboard display.
    """
    id: str
    firstName: str
    lastName: str
    age: int
    roomNumber: str
    bedNumber: str
    status: PatientStatus
    attendingPhysicianName: str
    assignedDeviceId: Optional[str]
    deviceStatus: Optional[str]
