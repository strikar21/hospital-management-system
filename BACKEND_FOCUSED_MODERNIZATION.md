# Backend-Focused camelCase Modernization Strategy

## Situation Analysis
- ✅ **Frontend**: Mostly camelCase, working well (~10-15 snake_case instances to clean up)
- ❌ **Backend**: Extensive snake_case (~30+ files, 1000+ instances)
- ❌ **Database**: Completely snake_case schema

## Strategy: Backend-First with Minimal Frontend Touchups

### Phase 1: Database Schema Modernization (1 week)

#### 1.1 Create New camelCase Database Schema
```sql
-- NEW: init_camelcase.sql
CREATE TABLE devices (
    id SERIAL PRIMARY KEY,
    deviceId VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    deviceType VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'offline',
    location VARCHAR(255),
    macAddress VARCHAR(17) UNIQUE,
    ipAddress VARCHAR(45),
    firmwareVersion VARCHAR(50),
    batteryLevel FLOAT,
    signalStrength INTEGER,
    assignmentStatus VARCHAR(20) DEFAULT 'free',
    assignedTo VARCHAR(255),
    assignedAt TIMESTAMP WITH TIME ZONE,
    createdAt TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updatedAt TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    isActive BOOLEAN DEFAULT TRUE
);

CREATE TABLE patients (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    bedNumber VARCHAR(50) NOT NULL,
    ward VARCHAR(100) NOT NULL,
    assignedDoctor VARCHAR(255) NOT NULL,
    age INTEGER,
    gender VARCHAR(20),
    diagnosis TEXT,
    admissionDate TIMESTAMP WITH TIME ZONE,
    currentStatus VARCHAR(50) DEFAULT 'stable',
    codeStatus VARCHAR(50) DEFAULT 'fullCode',
    createdAt TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updatedAt TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    isActive BOOLEAN DEFAULT TRUE
);

CREATE TABLE staff (
    id SERIAL PRIMARY KEY,
    staffId VARCHAR(255) UNIQUE NOT NULL,
    firstName VARCHAR(255) NOT NULL,
    lastName VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    role VARCHAR(100) NOT NULL,
    department VARCHAR(100),
    nfcId VARCHAR(255) UNIQUE,
    passwordHash VARCHAR(255),
    pinHash VARCHAR(255),
    isActive BOOLEAN DEFAULT TRUE,
    createdAt TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updatedAt TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- TimescaleDB for vitals (already converted in our previous work)
CREATE TABLE vitalReadings (
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deviceId TEXT NOT NULL,
    patientId TEXT NOT NULL,
    vitalType TEXT NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit TEXT,
    qualityIndicator TEXT,
    metadata JSONB,
    PRIMARY KEY (timestamp, deviceId, vitalType)
);
```

#### 1.2 Data Migration Scripts
```python
# scripts/migrate_database.py
import asyncio
import asyncpg

async def migrate_all_data():
    # Connect to old and new databases
    old_db = await asyncpg.connect("postgresql://user:pass@localhost:5432/hospital_streaming")
    new_db = await asyncpg.connect("postgresql://user:pass@localhost:5432/hospital_streaming_v2")
    
    # Migrate patients
    await migrate_patients(old_db, new_db)
    # Migrate devices  
    await migrate_devices(old_db, new_db)
    # Migrate staff
    await migrate_staff(old_db, new_db)
    # Migrate vitals
    await migrate_vitals(old_db, new_db)

async def migrate_patients(old_db, new_db):
    patients = await old_db.fetch("""
        SELECT id, name, bed_number, ward, assigned_doctor, age, gender,
               diagnosis, admission_date, status, created_at, updated_at, is_active
        FROM patients WHERE is_active = true
    """)
    
    for p in patients:
        await new_db.execute("""
            INSERT INTO patients (id, name, bedNumber, ward, assignedDoctor, age, 
                                gender, diagnosis, admissionDate, currentStatus,
                                createdAt, updatedAt, isActive)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        """, p['id'], p['name'], p['bed_number'], p['ward'], p['assigned_doctor'],
             p['age'], p['gender'], p['diagnosis'], p['admission_date'], p['status'],
             p['created_at'], p['updated_at'], p['is_active'])
```

### Phase 2: Backend Model Modernization (1 week)

#### 2.1 Convert All Model Files
```python
# app/models/patient.py - MODERNIZED
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    bedNumber = Column(String, nullable=False)
    ward = Column(String, nullable=False)
    assignedDoctor = Column(String, nullable=False)
    age = Column(Integer)
    gender = Column(String)
    diagnosis = Column(Text)
    admissionDate = Column(DateTime(timezone=True))
    currentStatus = Column(String, default="stable")
    codeStatus = Column(String, default="fullCode")
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())
    isActive = Column(Boolean, default=True)
    
    # Relationships with camelCase
    medications = relationship("PatientMedication", back_populates="patient")
    vitalReadings = relationship("VitalReading", back_populates="patient")
    caseEntries = relationship("PatientCaseEntry", back_populates="patient")
```

#### 2.2 Convert All Service Files
```python
# app/services/patient_service.py - MODERNIZED
class PatientService:
    @staticmethod
    async def get_patients(limit: int = 100):
        query = """
            SELECT id, name, bedNumber, ward, assignedDoctor, age, gender,
                   diagnosis, admissionDate, currentStatus, codeStatus,
                   createdAt, updatedAt, isActive
            FROM patients 
            WHERE isActive = true 
            ORDER BY createdAt DESC 
            LIMIT $1
        """
        return await database.fetch_all(query, limit)
    
    @staticmethod 
    async def create_patient(patient_data: dict):
        query = """
            INSERT INTO patients (id, name, bedNumber, ward, assignedDoctor,
                                age, gender, diagnosis, admissionDate, currentStatus)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING *
        """
        return await database.fetch_one(query, 
            patient_data['id'], patient_data['name'], patient_data['bedNumber'],
            patient_data['ward'], patient_data['assignedDoctor'], patient_data['age'],
            patient_data['gender'], patient_data['diagnosis'], patient_data['admissionDate'],
            patient_data['currentStatus'])
```

### Phase 3: Backend API Modernization (1 week)

#### 3.1 Convert All API Endpoints
```python
# app/api/v1/patients.py - MODERNIZED
from fastapi import APIRouter, Depends, HTTPException
from app.services.patient_service import PatientService
from app.schemas.patient import PatientResponse, PatientCreate

router = APIRouter(prefix="/patients")

@router.get("/", response_model=List[PatientResponse])
async def get_patients(limit: int = 100):
    """Get all patients with camelCase response"""
    patients = await PatientService.get_patients(limit)
    return [PatientResponse(**patient) for patient in patients]

@router.post("/", response_model=PatientResponse)
async def create_patient(patient: PatientCreate):
    """Create new patient with camelCase data"""
    patient_data = patient.dict()
    created_patient = await PatientService.create_patient(patient_data)
    return PatientResponse(**created_patient)
```

#### 3.2 Update Schema Definitions
```python
# app/schemas/patient.py - MODERNIZED
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PatientBase(BaseModel):
    name: str
    bedNumber: str
    ward: str
    assignedDoctor: str
    age: Optional[int] = None
    gender: Optional[str] = None
    diagnosis: Optional[str] = None
    currentStatus: str = "stable"

class PatientCreate(PatientBase):
    id: str
    admissionDate: datetime

class PatientResponse(PatientBase):
    id: str
    admissionDate: Optional[datetime] = None
    codeStatus: str = "fullCode"
    createdAt: datetime
    updatedAt: Optional[datetime] = None
    isActive: bool = True
    
    class Config:
        orm_mode = True
```

### Phase 4: Minimal Frontend Touchups (2-3 days)

#### 4.1 Fix Remaining snake_case in Frontend
```typescript
// Fix these specific instances found:
// src/PasswordChange.tsx
const changePassword = async () => {
    await fetch('/api/v1/staff/change-password', {
        method: 'POST',
        body: JSON.stringify({
            currentPassword: currentPassword,  // ✅ Fixed
            newPassword: newPassword,          // ✅ Fixed
        })
    });
};

// src/EnhancedVitalChart.tsx  
interface VitalMetadata {
    maxValue?: number;        // ✅ Fixed from max_value
    minValue?: number;        // ✅ Fixed from min_value
    qualityScore?: number;    // ✅ Fixed from quality_score
    dataPoints?: number;      // ✅ Fixed from data_points
}

interface MedicationEvent {
    medicationName: string;   // ✅ Fixed from medication_name
    eventType: string;        // ✅ Fixed from event_type
    displayLabel: string;     // ✅ Fixed from display_label
}
```

### Phase 5: Testing & Validation (3-5 days)

#### 5.1 Backend API Testing
```python
# tests/test_patients_api.py
async def test_create_patient():
    patient_data = {
        "id": "P001",
        "name": "John Doe", 
        "bedNumber": "A101",
        "ward": "ICU",
        "assignedDoctor": "Dr. Smith",
        "age": 45,
        "gender": "Male",
        "diagnosis": "Post-surgical monitoring",
        "currentStatus": "stable",
        "admissionDate": "2024-01-01T10:00:00Z"
    }
    
    response = await client.post("/api/v1/patients/", json=patient_data)
    assert response.status_code == 200
    
    result = response.json()
    assert result["name"] == "John Doe"
    assert result["bedNumber"] == "A101"
    assert result["isActive"] == True
```

#### 5.2 Frontend Integration Testing
- Test all forms still submit correctly
- Verify API calls return expected camelCase data
- Check that patient listings, vital charts, device management all work

### Phase 6: Deployment (1-2 days)

#### 6.1 Blue-Green Deployment
- Deploy new backend alongside old one
- Route 10% traffic to new backend initially
- Monitor for errors, gradually increase traffic
- Complete cutover once validated

#### 6.2 Database Cutover
- Final data sync from old to new database
- Update connection strings to point to new database
- Keep old database as backup for 1-2 weeks

## Timeline Summary
- **Phase 1**: Database Schema (1 week)
- **Phase 2**: Backend Models (1 week)  
- **Phase 3**: Backend APIs (1 week)
- **Phase 4**: Frontend Touchups (2-3 days)
- **Phase 5**: Testing (3-5 days)
- **Phase 6**: Deployment (1-2 days)

**Total**: ~4 weeks for complete modernization

## Benefits of This Approach
✅ **Preserve working frontend** - minimal changes needed
✅ **Focus on root cause** - backend has most snake_case
✅ **Faster completion** - 4 weeks vs months of conversion
✅ **Lower risk** - frontend continues working throughout
✅ **Clean result** - unified camelCase system
✅ **Easier maintenance** - consistent naming conventions

This approach leverages your existing working frontend while modernizing the backend where most of the snake_case technical debt exists.