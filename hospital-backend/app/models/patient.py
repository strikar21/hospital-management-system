"""
Patient data models
"""

from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime, date

class PatientBase(BaseModel):
    """Base patient model - matches database schema"""
    firstname: str
    lastname: str
    dateofbirth: Optional[date] = None
    gender: Optional[str] = None
    phonenumber: Optional[str] = None
    emergencycontactname: Optional[str] = None
    emergencycontactphone: Optional[str] = None
    bloodtype: Optional[str] = None
    allergies: Optional[str] = None
    medicalhistory: Optional[str] = None
    roomnumber: Optional[str] = None
    bednumber: Optional[str] = None
    attendingphysician: Optional[str] = None
    nurseincharge: Optional[str] = None

class PatientCreate(PatientBase):
    """Patient creation model"""
    pass

class PatientUpdate(BaseModel):
    """Patient update model - matches database schema"""
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    dateofbirth: Optional[date] = None
    gender: Optional[str] = None
    phonenumber: Optional[str] = None
    emergencycontactname: Optional[str] = None
    emergencycontactphone: Optional[str] = None
    bloodtype: Optional[str] = None
    allergies: Optional[str] = None
    medicalhistory: Optional[str] = None
    roomnumber: Optional[str] = None
    bednumber: Optional[str] = None
    attendingphysician: Optional[str] = None
    nurseincharge: Optional[str] = None
    status: Optional[str] = None

class Patient(PatientBase):
    """Complete patient model - matches database schema"""
    id: str
    admissiondate: Optional[datetime] = None
    dischargedate: Optional[datetime] = None
    assigneddeviceid: Optional[str] = None
    status: str = "active"
    createdat: datetime
    updatedat: datetime
    
    class Config:
        from_attributes = True

class VitalSigns(BaseModel):
    """Vital signs data model - uses camelCase as per project standards"""
    id: Optional[int] = None
    patientId: str
    deviceId: Optional[str] = ""  # Make optional with default
    timestamp: datetime
    heartRate: Optional[int] = None
    bloodPressureSystolic: Optional[int] = None
    bloodPressureDiastolic: Optional[int] = None
    temperature: Optional[float] = None
    oxygenSaturation: Optional[int] = None
    respiratoryRate: Optional[int] = None
    glucoseLevel: Optional[float] = None
    
    class Config:
        from_attributes = True

class PatientWithVitals(Patient):
    """Patient model with current vital signs and related data"""
    currentVitals: Optional[VitalSigns] = None
    recentVitals: List[VitalSigns] = []
    medications: List[Any] = []
    investigations: List[Any] = []
    therapies: List[Any] = []
    notes: List[Any] = []