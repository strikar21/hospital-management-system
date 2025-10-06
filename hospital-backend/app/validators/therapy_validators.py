"""
Therapy data validators
Provides comprehensive validation for therapy prescriptions
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal
from datetime import datetime
from .sanitizers import sanitize_string, sanitize_id, clean_whitespace


class TherapyRequest(BaseModel):
    """
    Validated therapy request model
    Ensures all therapy data meets requirements
    """

    therapyType: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Type of therapy"
    )

    description: Optional[str] = Field(
        None,
        max_length=2000,
        description="Therapy description"
    )

    startDate: datetime = Field(
        ...,
        description="Start date/time"
    )

    endDate: Optional[datetime] = Field(
        None,
        description="End date/time"
    )

    frequency: Optional[str] = Field(
        None,
        max_length=100,
        description="Frequency of therapy"
    )

    prescribedBy: str = Field(
        ...,
        description="Staff ID of prescriber"
    )

    performedBy: Optional[str] = Field(
        None,
        description="Staff ID of performer"
    )

    notes: Optional[str] = Field(
        None,
        max_length=2000,
        description="Additional notes"
    )

    status: Optional[Literal['scheduled', 'in-progress', 'completed', 'discontinued', 'on-hold']] = Field(
        default='scheduled',
        description="Therapy status"
    )

    @field_validator('therapyType')
    @classmethod
    def validate_therapy_type(cls, v):
        """Validate and clean therapy type"""
        v = clean_whitespace(v)
        if not v:
            raise ValueError('Therapy type cannot be empty')
        return v

    @model_validator(mode='after')
    def validate_date_range(self):
        """Ensure end date is after start date"""
        if self.endDate and self.startDate:
            if self.endDate < self.startDate:
                raise ValueError('End date cannot be before start date')
        return self

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

    @field_validator('description', mode='before')
    @classmethod
    def validate_description(cls, v):
        """Sanitize description field"""
        if v:
            v = clean_whitespace(v)
            return sanitize_string(v, max_length=2000)
        return v

    @field_validator('frequency', mode='before')
    @classmethod
    def validate_frequency(cls, v):
        """Sanitize frequency field"""
        if v:
            v = clean_whitespace(v)
            return sanitize_string(v, max_length=100)
        return v

    @field_validator('notes', mode='before')
    @classmethod
    def validate_notes(cls, v):
        """Sanitize notes field"""
        if v:
            v = clean_whitespace(v)
            return sanitize_string(v, max_length=2000)
        return v

    class Config:
        extra = 'ignore'


class TherapyUpdate(BaseModel):
    """
    Validated therapy update model
    All fields optional for partial updates
    """

    therapyType: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None
    frequency: Optional[str] = Field(None, max_length=100)
    performedBy: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=2000)
    status: Optional[Literal['scheduled', 'in-progress', 'completed', 'discontinued', 'on-hold']] = None

    # In Pydantic v2, validators are automatically inherited
    # No need to manually reference parent class validators

    class Config:
        extra = 'ignore'
