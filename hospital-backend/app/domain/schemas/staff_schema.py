"""
Staff schema - Single source of truth for staff data structure.

This schema is mirrored in frontend:
    hospital-display-app/src/data/schemas/Staff.schema.ts

Any changes here MUST be reflected in frontend schema.

Usage:
    from app.domain.schemas import StaffRecord

    staff: StaffRecord = {
        'id': 'DOC001',
        'firstName': 'Dr. Jane',
        'lastName': 'Smith',
        'role': 'Doctor',
        'department': 'Cardiology',
        'isActive': True
    }
"""

from typing import TypedDict, Optional, Literal
from datetime import datetime


# Type aliases
StaffRole = Literal['Doctor', 'Nurse', 'Administrator', 'Technician', 'Provisioner']


class StaffRecord(TypedDict, total=False):
    """
    Complete staff member data structure.

    Frontend Mirror: hospital-display-app/src/data/schemas/Staff.schema.ts
    """

    # ========================================
    # STAFF IDENTIFICATION (Required)
    # ========================================
    id: str                               # Staff ID (REQUIRED)
    role: StaffRole                       # Staff role (REQUIRED)

    # ========================================
    # PERSONAL INFORMATION
    # ========================================
    firstName: Optional[str]              # First name
    lastName: Optional[str]               # Last name
    email: Optional[str]                  # Email address
    phoneNumber: Optional[str]            # Contact phone

    # ========================================
    # DEPARTMENT AND ROLE
    # ========================================
    department: Optional[str]             # Department (Cardiology, ICU, etc.)

    # ========================================
    # AUTHENTICATION
    # ========================================
    pin: Optional[str]                    # Hashed PIN for quick login
    password: Optional[str]               # Hashed password for full login
    nfcCardId: Optional[str]              # NFC card ID for tap login

    # ========================================
    # STATUS AND ACTIVITY
    # ========================================
    isActive: Optional[bool]              # Is staff member active
    lastSeen: Optional[datetime]          # Last activity timestamp

    # ========================================
    # AUDIT TRAIL
    # ========================================
    createdAt: Optional[datetime]         # Record creation timestamp
    updatedAt: Optional[datetime]         # Last update timestamp


class StaffResolution(TypedDict):
    """
    Resolved staff information (ID → Name + Role).

    Used when displaying staff names in UI instead of IDs.
    """
    id: str                               # Staff ID
    name: str                             # Full name (firstName + lastName)
    role: StaffRole                       # Staff role
    department: Optional[str]             # Department


class StaffCredentials(TypedDict):
    """
    Staff authentication credentials.

    Used during login/authentication flow.
    """
    staffId: str                          # Staff ID
    pin: Optional[str]                    # PIN for quick login
    password: Optional[str]               # Password for full login
    nfcCardId: Optional[str]              # NFC card for tap login
