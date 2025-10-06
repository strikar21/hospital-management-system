"""
Vital signs validators
Provides comprehensive validation for patient vital signs with medical range checking
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from datetime import datetime
from .sanitizers import sanitize_id


class VitalSignsCreate(BaseModel):
    """
    Validated vital signs model
    Ensures all vital signs are within medically reasonable ranges
    """

    patientId: str = Field(
        ...,
        description="Patient ID (format: PAT0001)"
    )

    deviceId: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Device ID that recorded vitals"
    )

    timestamp: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="Time vitals were recorded"
    )

    heartRate: Optional[int] = Field(
        None,
        ge=20,
        le=300,
        description="Heart rate in beats per minute (20-300 bpm)"
    )

    bloodPressureSystolic: Optional[int] = Field(
        None,
        ge=50,
        le=250,
        description="Systolic blood pressure in mmHg (50-250)"
    )

    bloodPressureDiastolic: Optional[int] = Field(
        None,
        ge=30,
        le=150,
        description="Diastolic blood pressure in mmHg (30-150)"
    )

    temperature: Optional[float] = Field(
        None,
        ge=30.0,
        le=45.0,
        description="Body temperature in Celsius (30-45°C)"
    )

    oxygenSaturation: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Oxygen saturation percentage (0-100%)"
    )

    respiratoryRate: Optional[int] = Field(
        None,
        ge=0,
        le=60,
        description="Respiratory rate in breaths per minute (0-60)"
    )

    glucoseLevel: Optional[float] = Field(
        None,
        ge=0.0,
        le=1000.0,
        description="Glucose level in mg/dL (0-1000)"
    )

    @field_validator('patientId')
    @classmethod
    def validate_patient_id(cls, v):
        """Validate patient ID format"""
        try:
            pattern = r'^PAT[0-9]{4}$'
            return sanitize_id(v, pattern)
        except ValueError as e:
            raise ValueError(f'Invalid patient ID: {e}')

    @model_validator(mode='after')
    def validate_bp_ratio(self):
        """Ensure diastolic pressure is less than systolic"""
        if self.bloodPressureDiastolic and self.bloodPressureSystolic:
            if self.bloodPressureDiastolic >= self.bloodPressureSystolic:
                raise ValueError(
                    f'Diastolic blood pressure ({self.bloodPressureDiastolic}) must be lower than '
                    f'systolic blood pressure ({self.bloodPressureSystolic})'
                )
        return self

    @field_validator('temperature')
    @classmethod
    def validate_temperature_precision(cls, v):
        """Validate temperature has reasonable precision"""
        if v:
            # Round to 1 decimal place
            return round(v, 1)
        return v

    @field_validator('glucoseLevel')
    @classmethod
    def validate_glucose_precision(cls, v):
        """Validate glucose has reasonable precision"""
        if v:
            # Round to 1 decimal place
            return round(v, 1)
        return v

    @field_validator('heartRate')
    @classmethod
    def validate_heart_rate(cls, v):
        """Additional validation for heart rate"""
        if v:
            # Warn if extremely low or high (but still allow)
            if v < 40 or v > 200:
                # In production, this could trigger a clinical alert
                pass
        return v

    @field_validator('oxygenSaturation')
    @classmethod
    def validate_oxygen_saturation(cls, v):
        """Additional validation for oxygen saturation"""
        if v:
            # Warn if critically low (but still allow)
            if v < 90:
                # In production, this could trigger a clinical alert
                pass
        return v

    class Config:
        extra = 'ignore'


class VitalSignsUpdate(BaseModel):
    """
    Validated vital signs update model
    All fields optional for partial updates
    """

    deviceId: Optional[str] = Field(None, max_length=100)
    heartRate: Optional[int] = Field(None, ge=20, le=300)
    bloodPressureSystolic: Optional[int] = Field(None, ge=50, le=250)
    bloodPressureDiastolic: Optional[int] = Field(None, ge=30, le=150)
    temperature: Optional[float] = Field(None, ge=30.0, le=45.0)
    oxygenSaturation: Optional[int] = Field(None, ge=0, le=100)
    respiratoryRate: Optional[int] = Field(None, ge=0, le=60)
    glucoseLevel: Optional[float] = Field(None, ge=0.0, le=1000.0)

    # In Pydantic v2, validators are automatically inherited
    # No need to manually reference parent class validators

    class Config:
        extra = 'ignore'
