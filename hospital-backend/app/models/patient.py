"""
Patient data models
"""

from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime, date

class PatientBase(BaseModel):
    """Base patient model - matches database schema"""
    firstName: str
    lastName: str
    mrn: Optional[str] = None
    dateOfBirth: Optional[date] = None
    gender: Optional[str] = None
    phoneNumber: Optional[str] = None
    emergencyContactName: Optional[str] = None
    emergencyContactPhone: Optional[str] = None
    bloodType: Optional[str] = None
    allergies: Optional[str] = None
    medicalHistory: Optional[str] = None
    currentMedications: Optional[str] = None
    roomNumber: Optional[str] = None
    bedNumber: Optional[str] = None
    attendingPhysician: Optional[str] = None
    nurseInCharge: Optional[str] = None

class PatientCreate(PatientBase):
    """Patient creation model"""
    pass

class PatientUpdate(BaseModel):
    """Patient update model - matches database schema"""
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    mrn: Optional[str] = None
    dateOfBirth: Optional[date] = None
    gender: Optional[str] = None
    phoneNumber: Optional[str] = None
    emergencyContactName: Optional[str] = None
    emergencyContactPhone: Optional[str] = None
    bloodType: Optional[str] = None
    allergies: Optional[str] = None
    medicalHistory: Optional[str] = None
    currentMedications: Optional[str] = None
    roomNumber: Optional[str] = None
    bedNumber: Optional[str] = None
    attendingPhysician: Optional[str] = None
    nurseInCharge: Optional[str] = None
    status: Optional[str] = None

class Patient(PatientBase):
    """Complete patient model - matches database schema"""
    id: str
    admissionDate: Optional[datetime] = None
    dischargeDate: Optional[datetime] = None
    # Note: Device assignments are tracked in deviceassignments table, not here
    status: str = "active"
    createdAt: datetime
    updatedAt: datetime

    # Internal attribute for vitals data
    _current_vitals: Optional['VitalSigns'] = None
    _current_alerts: List[Any] = []

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True

    @property
    def name(self) -> str:
        """Computed property for frontend compatibility - combines firstName and lastName"""
        return f"{self.firstName} {self.lastName}".strip()

    @property
    def ward(self) -> str:
        """Extract ward from room number for frontend compatibility"""
        if self.roomNumber:
            # Assuming room format like "ICU-101", "GEN-205", etc.
            return self.roomNumber.split("-")[0] if "-" in self.roomNumber else ""
        return ""

    @property
    def room(self) -> str:
        """Return room number for frontend compatibility"""
        return self.roomNumber or ""

    @property
    def assignedDoctor(self) -> str:
        """Return attending physician for frontend compatibility"""
        return self.attendingPhysician or ""

    @property
    def vitals(self) -> dict:
        """Computed vitals property for frontend compatibility"""
        if hasattr(self, '_current_vitals') and self._current_vitals:
            vitals_data = {
                "heartRate": self._current_vitals.heartRate or 0,
                "temperature": self._current_vitals.temperature or 0.0,
                "oxygenSat": self._current_vitals.oxygenSaturation or 0,
                "respiratoryRate": self._current_vitals.respiratoryRate or 0,
                "bloodPressureValue": self._current_vitals.bloodPressureSystolic or 0,
                "lastUpdated": self._current_vitals.timestamp.isoformat() if self._current_vitals.timestamp else "",
                "lastSync": self._current_vitals.timestamp.isoformat() if self._current_vitals.timestamp else "",
                "ecg": 0,  # Default values for extended monitoring
                "eeg": 0,
                "isEcgMode": False,
                "bioImpedance": 0,
                "tremor": 0,
                "fallRisk": "low"
            }

            # Format blood pressure as string "120/80"
            if (self._current_vitals.bloodPressureSystolic and
                self._current_vitals.bloodPressureDiastolic):
                vitals_data["bloodPressure"] = f"{self._current_vitals.bloodPressureSystolic}/{self._current_vitals.bloodPressureDiastolic}"
            else:
                vitals_data["bloodPressure"] = "0/0"

            return vitals_data

        # Return default vitals structure
        return {
            "heartRate": 0,
            "bloodPressure": "0/0",
            "bloodPressureValue": 0,
            "temperature": 0.0,
            "oxygenSat": 0,
            "respiratoryRate": 0,
            "ecg": 0,
            "eeg": 0,
            "isEcgMode": False,
            "bioImpedance": 0,
            "tremor": 0,
            "fallRisk": "low",
            "lastUpdated": "",
            "lastSync": ""
        }

    @property
    def alerts(self) -> List[dict]:
        """Return alerts in frontend format"""
        return getattr(self, '_current_alerts', [])

    @property
    def deviceStatus(self) -> str:
        """Device status for frontend compatibility

        Note: Device assignments are tracked in deviceassignments table.
        This property returns a default value. For actual device status,
        query the deviceassignments table and check device.lastSeen timestamp.
        Use API endpoints like /api/v1/watchmanagement/assigned for accurate status.
        """
        # Device status should be queried separately via deviceassignments table
        # This is a placeholder for backward compatibility
        return "unknown"

    @property
    def age(self) -> int:
        """Calculate age from date of birth"""
        if self.dateOfBirth:
            from datetime import date
            today = date.today()
            return today.year - self.dateOfBirth.year - ((today.month, today.day) < (self.dateOfBirth.month, self.dateOfBirth.day))
        return 0

    @property
    def medicationsList(self) -> List[dict]:
        """Return medications list for frontend"""
        return getattr(self, '_medications', [])

    @property
    def investigationsList(self) -> List[dict]:
        """Return investigations list for frontend"""
        return getattr(self, '_investigations', [])

    @property
    def therapiesList(self) -> List[dict]:
        """Return therapies list for frontend"""
        return getattr(self, '_therapies', [])

    @property
    def notesList(self) -> List[dict]:
        """Return notes list for frontend"""
        return getattr(self, '_notes', [])

    @property
    def caseSheet(self) -> List[dict]:
        """Return case sheet entries for frontend"""
        return getattr(self, '_case_sheet', [])

    def set_current_vitals(self, vitals: 'VitalSigns'):
        """Set current vitals for computed property"""
        self._current_vitals = vitals

    def set_alerts(self, alerts: List[dict]):
        """Set alerts for the patient"""
        self._current_alerts = alerts

    def set_medical_data(self, medications: List[dict] = None, investigations: List[dict] = None,
                        therapies: List[dict] = None, notes: List[dict] = None, case_sheet: List[dict] = None):
        """Set medical data for computed properties"""
        if medications is not None:
            self._medications = medications
        if investigations is not None:
            self._investigations = investigations
        if therapies is not None:
            self._therapies = therapies
        if notes is not None:
            self._notes = notes
        if case_sheet is not None:
            self._case_sheet = case_sheet

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
    currentvitals: Optional[VitalSigns] = None
    recentvitals: List[VitalSigns] = []
    medications: List[Any] = []
    investigations: List[Any] = []
    therapies: List[Any] = []
    notes: List[Any] = []