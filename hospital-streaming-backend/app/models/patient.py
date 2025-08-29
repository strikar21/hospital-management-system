from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Float, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    bedNumber = Column(String, nullable=False)
    ward = Column(String, nullable=False)
    room = Column(String, nullable=False)
    department = Column(String, nullable=False)
    assignedDoctor = Column(String, nullable=False)
    
    # Patient demographics
    age = Column(Integer, nullable=False)
    gender = Column(String, nullable=False)
    weight = Column(Float)
    diagnosis = Column(String, nullable=False)
    admissionDate = Column(String, nullable=False)
    
    # Current status
    status = Column(String, default="stable")  # stable, critical, emergency
    
    # Enhanced clinical safety fields
    codeStatus = Column(String, default="full_code")  # full_code, dnr, dnr_cca, comfort_care
    activeProblems = Column(JSON)  # Array of active medical problems
    lastMedicationTime = Column(String)  # ISO timestamp of last medication
    nextMedicationDue = Column(String)  # ISO timestamp of next medication
    
    # Current vitals (latest from devices)
    currentVitals = Column(JSON)
    
    # Timestamps
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())
    isActive = Column(Boolean, default=True)
    
    # Relationships
    medications = relationship("PatientMedication", back_populates="patient")
    notes = relationship("PatientNote", back_populates="patient")
    caseEntries = relationship("PatientCaseEntry", back_populates="patient")
    alerts = relationship("PatientAlert", back_populates="patient")
    allergies = relationship("PatientAllergy", back_populates="patient")
    handoffNotes = relationship("HandoffNote", back_populates="patient")

class PatientMedication(Base):
    __tablename__ = "patientMedications"
    
    id = Column(String, primary_key=True, index=True)
    patientId = Column(String, ForeignKey("patients.id"), nullable=False)
    
    name = Column(String, nullable=False)
    dosage = Column(String, nullable=False)
    frequency = Column(String, nullable=False)
    route = Column(String, nullable=False)
    status = Column(String, default="active")  # active, stopped, held
    
    startDate = Column(String, nullable=False)
    endDate = Column(String)
    
    prescribedBy = Column(String, nullable=False)
    prescribedAt = Column(DateTime(timezone=True), server_default=func.now())
    modifiedBy = Column(String)
    modifiedAt = Column(DateTime(timezone=True))
    
    canEdit = Column(Boolean, default=True)
    
    # Relationships
    patient = relationship("Patient", back_populates="medications")
    history = relationship("MedicationHistory", back_populates="medication")

class MedicationHistory(Base):
    __tablename__ = "medicationHistory"
    
    id = Column(String, primary_key=True, index=True)
    medicationId = Column(String, ForeignKey("patient_medications.id"), nullable=False)
    
    action = Column(String, nullable=False)  # prescribed, modified, stopped, etc.
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    performedBy = Column(String, nullable=False)
    changes = Column(JSON)
    
    # Relationships
    medication = relationship("PatientMedication", back_populates="history")

class PatientNote(Base):
    __tablename__ = "patient_notes"
    
    id = Column(String, primary_key=True, index=True)
    patientId = Column(String, ForeignKey("patients.id"), nullable=False)
    
    content = Column(Text, nullable=False)
    authorId = Column(String, nullable=False)
    authorName = Column(String, nullable=False)
    authorRole = Column(String, nullable=False)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    editedAt = Column(DateTime(timezone=True))
    canEdit = Column(Boolean, default=True)
    isEdited = Column(Boolean, default=False)
    
    # Relationships
    patient = relationship("Patient", back_populates="notes")

class PatientCaseEntry(Base):
    __tablename__ = "patient_case_entries"
    
    id = Column(String, primary_key=True, index=True)
    patientId = Column(String, ForeignKey("patients.id"), nullable=False)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    entryType = Column(String, nullable=False)  # admission, medication, note, etc.
    description = Column(Text, nullable=False)
    performedBy = Column(String, nullable=False)
    can_edit = Column(Boolean, default=False)
    
    # Relationships
    patient = relationship("Patient", back_populates="case_entries")

class PatientAlert(Base):
    __tablename__ = "patient_alerts"
    
    id = Column(String, primary_key=True, index=True)
    patientId = Column(String, ForeignKey("patients.id"), nullable=False)
    
    message = Column(String, nullable=False)
    severity = Column(String, nullable=False)  # low, medium, high, critical
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    isAcknowledged = Column(Boolean, default=False)
    acknowledgedBy = Column(String)
    acknowledgedByName = Column(String)
    acknowledgedByRole = Column(String)
    acknowledgedAt = Column(DateTime(timezone=True))
    
    # Relationships
    patient = relationship("Patient", back_populates="alerts")

class Staff(Base):
    __tablename__ = "staff"
    
    id = Column(String, primary_key=True, index=True)
    staffId = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # Doctor, Nurse, Admin, Technician
    department = Column(String, nullable=False)
    nfcId = Column(String, unique=True)
    
    # Authentication
    passwordHash = Column(String)  # For staff login
    
    # Status
    isActive = Column(Boolean, default=True)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

class PatientDeviceMapping(Base):
    __tablename__ = "patient_device_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    patientId = Column(String, ForeignKey("patients.id"), nullable=False)
    deviceId = Column(String, nullable=False)  # References devices.device_id
    
    assignedAt = Column(DateTime(timezone=True), server_default=func.now())
    assignedBy = Column(String, nullable=False)
    isActive = Column(Boolean, default=True)

class PatientAllergy(Base):
    __tablename__ = "patient_allergies"
    
    id = Column(String, primary_key=True, index=True)
    patientId = Column(String, ForeignKey("patients.id"), nullable=False)
    
    allergen = Column(String, nullable=False)
    allergenType = Column(String, nullable=False)  # medication, food, environmental, other
    reaction = Column(String, nullable=False)
    severity = Column(String, nullable=False)  # mild, moderate, severe, life_threatening
    onset = Column(String)
    verificationStatus = Column(String, default="confirmed")  # confirmed, unconfirmed, entered_in_error
    
    recordedDate = Column(String, nullable=False)
    recordedBy = Column(String, nullable=False)
    
    # Timestamps
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    patient = relationship("Patient", back_populates="allergies")

class HandoffNote(Base):
    __tablename__ = "handoff_notes"
    
    id = Column(String, primary_key=True, index=True)
    patientId = Column(String, ForeignKey("patients.id"), nullable=False)
    
    shift = Column(String, nullable=False)  # day, evening, night
    fromNurse = Column(String, nullable=False)
    toNurse = Column(String)
    priority = Column(String, default="medium")  # low, medium, high, critical
    category = Column(String, nullable=False)  # medication, assessment, procedure, safety, family, other
    note = Column(Text, nullable=False)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    acknowledged = Column(Boolean, default=False)
    acknowledgedBy = Column(String)
    acknowledgedAt = Column(DateTime(timezone=True))
    
    # Relationships
    patient = relationship("Patient", back_populates="handoff_notes")