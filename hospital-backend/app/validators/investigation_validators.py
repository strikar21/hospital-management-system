"""
Investigation data validators
Provides comprehensive validation for investigations/tests
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime
from .sanitizers import sanitize_string, sanitize_id, clean_whitespace


class InvestigationRequest(BaseModel):
    """
    Validated investigation request model
    Ensures all investigation data meets requirements
    """

    testName: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Name of the test"
    )

    testType: Optional[Literal[
        'Lab',
        'Radiology',
        'ECG',
        'Echo',
        'CT',
        'MRI',
        'X-Ray',
        'Ultrasound',
        'Endoscopy',
        'Biopsy',
        'Other'
    ]] = Field(
        default='Lab',
        description="Type of test"
    )

    urgency: Optional[Literal['Routine', 'Urgent', 'STAT']] = Field(
        default='Routine',
        description="Urgency level"
    )

    priority: Optional[Literal['Routine', 'High', 'Critical']] = Field(
        default='Routine',
        description="Priority level"
    )

    prescribedBy: str = Field(
        ...,
        description="Staff ID of prescriber"
    )

    performedBy: Optional[str] = Field(
        None,
        description="Staff ID of performer"
    )

    scheduledDate: Optional[datetime] = Field(
        None,
        description="Scheduled date/time"
    )

    notes: Optional[str] = Field(
        None,
        max_length=2000,
        description="Additional notes"
    )

    result: Optional[str] = Field(
        None,
        max_length=5000,
        description="Test result"
    )

    status: Optional[Literal['pending', 'scheduled', 'in-progress', 'completed', 'cancelled']] = Field(
        default='pending',
        description="Investigation status"
    )

    @field_validator('testName')
    @classmethod
    def validate_test_name(cls, v):
        """Validate and clean test name"""
        v = clean_whitespace(v)
        if not v:
            raise ValueError('Test name cannot be empty')
        return v

    @field_validator('prescribedBy', 'performedBy')
    @classmethod
    def validate_staff_id(cls, v):
        """Validate staff ID format"""
        if v:
            try:
                pattern = r'^[A-Z]{3}[0-9]{4}$'
                return sanitize_id(v, pattern)
            except ValueError as e:
                raise ValueError(f'Invalid staff ID: {e}')
        return v

    @field_validator('notes', mode='before')
    @classmethod
    def validate_notes(cls, v):
        """Sanitize notes field"""
        if v:
            return sanitize_string(v, max_length=2000)
        return v

    @field_validator('result', mode='before')
    @classmethod
    def validate_result(cls, v):
        """Sanitize result field"""
        if v:
            return sanitize_string(v, max_length=5000)
        return v

    class Config:
        extra = 'ignore'


class InvestigationUpdate(BaseModel):
    """
    Validated investigation update model
    All fields optional for partial updates
    """

    testName: Optional[str] = Field(None, min_length=1, max_length=200)

    testType: Optional[Literal[
        'Lab',
        'Radiology',
        'ECG',
        'Echo',
        'CT',
        'MRI',
        'X-Ray',
        'Ultrasound',
        'Endoscopy',
        'Biopsy',
        'Other'
    ]] = None

    urgency: Optional[Literal['Routine', 'Urgent', 'STAT']] = None
    priority: Optional[Literal['Routine', 'High', 'Critical']] = None
    performedBy: Optional[str] = None
    scheduledDate: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=2000)
    result: Optional[str] = Field(None, max_length=5000)
    status: Optional[Literal['pending', 'scheduled', 'in-progress', 'completed', 'cancelled']] = None

    # In Pydantic v2, validators are automatically inherited
    # No need to manually reference parent class validators

    class Config:
        extra = 'ignore'
