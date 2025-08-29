from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

# Patient Models
class PatientBase(BaseModel):
    name: str
    bed_number: str
    ward: str
    room: str
    department: str
    assigned_doctor: str
    age: int
    gender: str
    weight: Optional[float] = None
    diagnosis: str
    admission_date: str
    status: str = "stable"
    # Enhanced clinical safety fields
    code_status: Optional[str] = "full_code"  # full_code, dnr, dnr_cca, comfort_care
    active_problems: Optional[List[str]] = []
    last_medication_time: Optional[str] = None
    next_medication_due: Optional[str] = None

class PatientCreate(PatientBase):
    id: str

class PatientUpdate(BaseModel):
    name: Optional[str] = None
    bed_number: Optional[str] = None
    ward: Optional[str] = None
    room: Optional[str] = None
    department: Optional[str] = None
    assigned_doctor: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    weight: Optional[float] = None
    diagnosis: Optional[str] = None
    status: Optional[str] = None

class PatientVitals(BaseModel):
    heart_rate: int
    blood_pressure: str
    blood_pressure_value: int
    respiratory_rate: int
    oxygen_sat: int
    temperature: float
    ecg: int
    eeg: int
    is_ecg_mode: bool
    bioimpedance: int
    tremor: float
    fall_risk: str
    last_updated: str
    last_sync: str

# Medication Models
class MedicationHistoryEntry(BaseModel):
    id: str
    action: str
    timestamp: datetime
    performed_by: str

    class Config:
        from_attributes = True

class PatientMedicationResponse(BaseModel):
    id: str
    name: str
    dosage: str
    frequency: str
    route: str
    status: str
    start_date: str = Field(alias="startDate")
    end_date: Optional[str] = Field(alias="endDate")
    prescribed_by: str = Field(alias="prescribedBy")
    prescribed_at: datetime = Field(alias="prescribedAt")
    modified_by: Optional[str] = Field(alias="modifiedBy")
    modified_at: Optional[datetime] = Field(alias="modifiedAt")
    can_edit: bool = Field(alias="canEdit")
    history: List[MedicationHistoryEntry] = []

    class Config:
        from_attributes = True
        populate_by_name = True
        
    def model_dump(self, **kwargs):
        # Force by_alias=True to use camelCase field names
        kwargs.setdefault('by_alias', True)
        return super().model_dump(**kwargs)

class MedicationCreate(BaseModel):
    name: str
    dosage: str
    frequency: str
    route: str
    start_date: str
    prescribed_by: str

# Note Models  
class PatientNoteResponse(BaseModel):
    id: str
    content: str
    author_id: str = Field(alias="authorId")
    author_name: str = Field(alias="authorName")
    author_role: str = Field(alias="authorRole")
    timestamp: datetime
    edited_at: Optional[datetime] = Field(alias="editedAt")
    can_edit: bool = Field(alias="canEdit")
    is_edited: bool = Field(alias="isEdited")

    class Config:
        from_attributes = True
        populate_by_name = True
        
    def model_dump(self, **kwargs):
        # Force by_alias=True to use camelCase field names
        kwargs.setdefault('by_alias', True)
        return super().model_dump(**kwargs)

class NoteCreate(BaseModel):
    content: str
    author_id: str
    author_name: str
    author_role: str

# Alert Models
class PatientAlertResponse(BaseModel):
    id: str
    message: str
    severity: str
    timestamp: str
    isAcknowledged: bool
    acknowledgedBy: Optional[str] = None
    acknowledgedByName: Optional[str] = None
    acknowledgedByRole: Optional[str] = None
    acknowledgedAt: Optional[str] = None

    class Config:
        from_attributes = True

# Case Entry Models
class CaseEntryCreate(BaseModel):
    entry_type: str  # examination, treatment, observation, medication_change, discharge
    description: str
    performed_by: str

class CaseEntryResponse(BaseModel):
    id: str
    timestamp: datetime
    entry_type: str = Field(alias="entryType")
    description: str
    performed_by: str = Field(alias="performedBy")
    can_edit: bool = Field(alias="canEdit")

    class Config:
        from_attributes = True
        populate_by_name = True
        
    def model_dump(self, **kwargs):
        # Force by_alias=True to use camelCase field names
        kwargs.setdefault('by_alias', True)
        return super().model_dump(**kwargs)

# Complete Patient Response
class PatientResponse(BaseModel):
    id: str
    name: str
    bed_number: str
    ward: str
    room: str
    department: str
    assigned_doctor: str
    age: int
    gender: str
    weight: Optional[float]
    diagnosis: str
    admission_date: str
    status: str
    # Enhanced clinical safety fields
    code_status: Optional[str] = "full_code"
    active_problems: Optional[List[str]] = []
    last_medication_time: Optional[str] = None
    next_medication_due: Optional[str] = None
    allergies: Optional[List[dict]] = []  # Will contain allergy information
    vitals: Optional[PatientVitals] = None
    alerts: List[PatientAlertResponse] = []
    medications: List[PatientMedicationResponse] = []
    notes: List[PatientNoteResponse] = []
    case_sheet: List[CaseEntryResponse] = []
    investigations: List[dict] = []
    therapies: List[dict] = []
    handoff_notes: Optional[List[dict]] = []  # For shift handoff notes

    class Config:
        from_attributes = True

class PatientListResponse(BaseModel):
    patients: List[PatientResponse]
    total_count: int
    page: int = 1
    page_size: int = 50

# Staff Models
class StaffResponse(BaseModel):
    id: str
    staff_id: str
    name: str
    role: str
    department: str
    nfc_id: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True

class StaffLogin(BaseModel):
    staff_id: str
    password: str

class StaffLoginResponse(BaseModel):
    user_id: str
    name: str
    role: str
    department: str
    access_token: str

# Device Assignment
class DeviceAssignment(BaseModel):
    patient_id: str
    device_id: str
    assigned_by: str

# Allergy Models
class AllergyResponse(BaseModel):
    id: str
    allergen: str
    allergen_type: str = Field(alias="allergenType")  # medication, food, environmental, other
    reaction: str
    severity: str  # mild, moderate, severe, life_threatening
    onset: Optional[str] = None
    verification_status: str = Field(alias="verificationStatus", default="confirmed")  # confirmed, unconfirmed, entered_in_error
    recorded_date: str = Field(alias="recordedDate")
    recorded_by: str = Field(alias="recordedBy")

    class Config:
        from_attributes = True
        populate_by_name = True
        
    def model_dump(self, **kwargs):
        # Force by_alias=True to use camelCase field names
        kwargs.setdefault('by_alias', True)
        return super().model_dump(**kwargs)

class AllergyCreate(BaseModel):
    allergen: str
    allergen_type: str
    reaction: str
    severity: str
    onset: Optional[str] = None
    recorded_by: str

# Handoff Notes Models
class HandoffNoteResponse(BaseModel):
    id: str
    patient_id: str
    shift: str  # day, evening, night
    from_nurse: str
    to_nurse: Optional[str] = None
    priority: str  # low, medium, high, critical
    category: str  # medication, assessment, procedure, safety, family, other
    note: str
    timestamp: str
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None

    class Config:
        from_attributes = True

class HandoffNoteCreate(BaseModel):
    patient_id: str
    shift: str
    from_nurse: str
    to_nurse: Optional[str] = None
    priority: str = "medium"
    category: str
    note: str