"""
Patient data validators
Provides comprehensive validation for patient information
"""

from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Optional, Literal
from datetime import date, datetime
from .sanitizers import sanitize_string, sanitize_phone, clean_whitespace


class PatientCreateValidated(BaseModel):
    """
    Validated patient creation model
    Ensures all patient data meets safety and format requirements
    """

    firstName: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Patient first name"
    )

    lastName: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Patient last name"
    )

    dateOfBirth: Optional[date] = Field(
        None,
        description="Date of birth"
    )

    gender: Optional[Literal['Male', 'Female', 'Other', 'Prefer not to say']] = Field(
        None,
        description="Patient gender"
    )

    phoneNumber: Optional[str] = Field(
        None,
        description="Phone number (10-15 digits)"
    )

    email: Optional[EmailStr] = Field(
        None,
        description="Email address"
    )

    emergencyContactName: Optional[str] = Field(
        None,
        max_length=200,
        description="Emergency contact name"
    )

    emergencyContactPhone: Optional[str] = Field(
        None,
        description="Emergency contact phone"
    )

    bloodType: Optional[Literal['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']] = Field(
        None,
        description="Blood type"
    )

    allergies: Optional[str] = Field(
        None,
        max_length=2000,
        description="Known allergies"
    )

    medicalHistory: Optional[str] = Field(
        None,
        max_length=5000,
        description="Medical history"
    )

    currentMedications: Optional[str] = Field(
        None,
        max_length=2000,
        description="Current medications"
    )

    roomNumber: Optional[str] = Field(
        None,
        max_length=50,
        description="Room number"
    )

    bedNumber: Optional[str] = Field(
        None,
        max_length=50,
        description="Bed number"
    )

    attendingPhysician: Optional[str] = Field(
        None,
        max_length=100,
        description="Attending physician ID"
    )

    nurseInCharge: Optional[str] = Field(
        None,
        max_length=100,
        description="Nurse in charge ID"
    )

    mrn: Optional[str] = Field(
        None,
        max_length=50,
        description="Medical record number"
    )

    @field_validator('firstName', 'lastName')
    @classmethod
    def validate_names(cls, v):
        """Validate and clean names"""
        if v:
            v = clean_whitespace(v)
            if not v:
                raise ValueError('Name cannot be empty or only whitespace')
            # Remove numbers from names
            if any(c.isdigit() for c in v):
                raise ValueError('Name cannot contain numbers')
        return v

    @field_validator('dateOfBirth')
    @classmethod
    def validate_dob(cls, v):
        """Validate date of birth"""
        if v:
            today = date.today()

            # Cannot be in the future
            if v > today:
                raise ValueError('Date of birth cannot be in the future')

            # Cannot be too far in the past (before 1900)
            if v < date(1900, 1, 1):
                raise ValueError('Date of birth too far in the past (before 1900)')

            # Check age is reasonable (not over 150 years old)
            age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
            if age > 150:
                raise ValueError('Age calculated from date of birth is unrealistic (>150 years)')

        return v

    @field_validator('phoneNumber', 'emergencyContactPhone')
    @classmethod
    def validate_phone(cls, v):
        """Validate and sanitize phone number"""
        if v:
            try:
                return sanitize_phone(v)
            except ValueError as e:
                raise ValueError(f'Invalid phone number: {e}')
        return v

    @field_validator('emergencyContactName')
    @classmethod
    def validate_emergency_contact(cls, v):
        """Validate emergency contact name"""
        if v:
            v = clean_whitespace(v)
            return sanitize_string(v, max_length=200)
        return v

    @field_validator('allergies', 'medicalHistory', 'currentMedications')
    @classmethod
    def validate_medical_fields(cls, v, info):
        """Sanitize medical text fields"""
        if v:
            max_lengths = {
                'allergies': 2000,
                'medicalHistory': 5000,
                'currentMedications': 2000
            }
            max_length = max_lengths.get(info.field_name, 2000)
            return sanitize_string(v, max_length=max_length)
        return v

    @field_validator('roomNumber', 'bedNumber')
    @classmethod
    def validate_room_bed(cls, v):
        """Validate room and bed numbers"""
        if v:
            v = clean_whitespace(v)
            return sanitize_string(v, max_length=50)
        return v

    class Config:
        extra = 'ignore'


class PatientUpdateValidated(BaseModel):
    """
    Validated patient update model
    All fields optional for partial updates
    """

    firstName: Optional[str] = Field(None, min_length=1, max_length=100)
    lastName: Optional[str] = Field(None, min_length=1, max_length=100)
    dateOfBirth: Optional[date] = None
    gender: Optional[Literal['Male', 'Female', 'Other', 'Prefer not to say']] = None
    phoneNumber: Optional[str] = None
    email: Optional[EmailStr] = None
    emergencyContactName: Optional[str] = Field(None, max_length=200)
    emergencyContactPhone: Optional[str] = None
    bloodType: Optional[Literal['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']] = None
    allergies: Optional[str] = Field(None, max_length=2000)
    medicalHistory: Optional[str] = Field(None, max_length=5000)
    currentMedications: Optional[str] = Field(None, max_length=2000)
    roomNumber: Optional[str] = Field(None, max_length=50)
    bedNumber: Optional[str] = Field(None, max_length=50)
    attendingPhysician: Optional[str] = Field(None, max_length=100)
    nurseInCharge: Optional[str] = Field(None, max_length=100)
    mrn: Optional[str] = Field(None, max_length=50)
    status: Optional[Literal['active', 'discharged', 'deceased', 'transferred']] = None

    # In Pydantic v2, validators are automatically inherited
    # No need to manually reference parent class validators

    class Config:
        extra = 'ignore'
