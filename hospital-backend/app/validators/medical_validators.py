"""
Medical data validators for medications
Provides comprehensive validation for medication prescriptions
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal
from datetime import datetime
from .sanitizers import (
    sanitize_string,
    sanitize_id,
    validate_dosage_format,
    validate_frequency_format,
    clean_whitespace
)


class MedicationRequest(BaseModel):
    """
    Validated medication request model
    Ensures all medication data meets safety and format requirements
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Medication name"
    )

    dosage: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Dosage (e.g., '500mg', '10ml', '2 tablets')"
    )

    route: Literal[
        'Oral',
        'IV',
        'IM',
        'SC',
        'Topical',
        'Inhalation',
        'Rectal',
        'Sublingual',
        'Transdermal',
        'Intrathecal',
        'Epidural',
        'Other'
    ] = Field(
        ...,
        description="Route of administration"
    )

    frequency: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Frequency (e.g., 'Once daily', 'TDS', 'PRN')"
    )

    prescribedBy: str = Field(
        ...,
        description="Staff ID of prescriber (format: DOC0001, NUR0001)"
    )

    startDate: Optional[datetime] = Field(
        default=None,
        description="Start date/time"
    )

    endDate: Optional[datetime] = Field(
        default=None,
        description="End date/time"
    )

    notes: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Additional notes"
    )

    status: Optional[Literal['active', 'held', 'discontinued', 'completed']] = Field(
        default='active',
        description="Medication status"
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate and clean medication name"""
        v = clean_whitespace(v)
        if not v:
            raise ValueError('Medication name cannot be empty')
        return v

    @field_validator('dosage')
    @classmethod
    def validate_dosage(cls, v):
        """Validate dosage format and value"""
        return validate_dosage_format(v)

    @field_validator('frequency')
    @classmethod
    def validate_frequency(cls, v):
        """Validate frequency format"""
        return validate_frequency_format(v)

    @field_validator('prescribedBy')
    @classmethod
    def validate_prescriber_id(cls, v):
        """Validate prescriber ID format"""
        try:
            # Accept DOC, NUR, or other staff ID patterns
            pattern = r'^[A-Z]{3}[0-9]{4}$'
            return sanitize_id(v, pattern)
        except ValueError as e:
            raise ValueError(f'Invalid prescriber ID: {e}')

    @model_validator(mode='after')
    def validate_date_range(self):
        """Ensure end date is after start date"""
        if self.endDate and self.startDate:
            if self.endDate < self.startDate:
                raise ValueError('End date cannot be before start date')
        return self

    @field_validator('notes')
    @classmethod
    def validate_notes(cls, v):
        """Sanitize notes field"""
        if v:
            return sanitize_string(v, max_length=2000)
        return v

    class Config:
        # Allow extra fields for backward compatibility
        extra = 'ignore'


class MedicationUpdate(BaseModel):
    """
    Validated medication update model
    All fields optional for partial updates
    """

    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200
    )

    dosage: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100
    )

    route: Optional[Literal[
        'Oral',
        'IV',
        'IM',
        'SC',
        'Topical',
        'Inhalation',
        'Rectal',
        'Sublingual',
        'Transdermal',
        'Intrathecal',
        'Epidural',
        'Other'
    ]] = None

    frequency: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100
    )

    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=2000)

    status: Optional[Literal['active', 'held', 'discontinued', 'completed']] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate and clean medication name"""
        if v:
            v = clean_whitespace(v)
            if not v:
                raise ValueError('Medication name cannot be empty')
        return v

    @field_validator('dosage')
    @classmethod
    def validate_dosage(cls, v):
        """Validate dosage format and value"""
        if v:
            return validate_dosage_format(v)
        return v

    @field_validator('frequency')
    @classmethod
    def validate_frequency(cls, v):
        """Validate frequency format"""
        if v:
            return validate_frequency_format(v)
        return v

    @field_validator('notes')
    @classmethod
    def validate_notes(cls, v):
        """Sanitize notes field"""
        if v:
            return sanitize_string(v, max_length=2000)
        return v

    class Config:
        extra = 'ignore'
