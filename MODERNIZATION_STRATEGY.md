# Hospital System Modernization Strategy

## Overview
Hybrid approach: Create new camelCase backend while preserving working frontend, then gradually modernize frontend components.

## Phase 1: Backend Modernization (2-3 weeks)

### 1.1 New Database Schema Design
```sql
-- NEW: hospital_streaming_v2 database
CREATE DATABASE hospital_streaming_v2;

-- Core entities with camelCase
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

CREATE TABLE vitalReadings (
    id SERIAL PRIMARY KEY,
    deviceId VARCHAR(255) REFERENCES devices(deviceId),
    patientId VARCHAR(255) REFERENCES patients(id),
    heartRate INTEGER,
    bloodPressureSystolic INTEGER,
    bloodPressureDiastolic INTEGER,
    temperature FLOAT,
    oxygenSaturation FLOAT,
    respiratoryRate INTEGER,
    ecgData JSONB,
    signalQuality FLOAT,
    isValid BOOLEAN DEFAULT TRUE,
    readingTimestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    createdAt TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Staff with unified naming
CREATE TABLE staff (
    id SERIAL PRIMARY KEY,
    staffId VARCHAR(255) UNIQUE NOT NULL,
    firstName VARCHAR(255) NOT NULL,
    lastName VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL, -- computed: firstName + lastName
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
```

### 1.2 Backend API Translation Layer
```python
# NEW: app/middleware/legacy_translation.py
from fastapi import Request
import json

class LegacyTranslationMiddleware:
    """
    Translates between frontend's snake_case and backend's camelCase
    """
    
    SNAKE_TO_CAMEL_MAP = {
        'patient_id': 'patientId',
        'device_id': 'deviceId', 
        'staff_id': 'staffId',
        'heart_rate': 'heartRate',
        'blood_pressure_systolic': 'bloodPressureSystolic',
        'oxygen_saturation': 'oxygenSaturation',
        'access_token': 'accessToken',
        'nfc_id': 'nfcId',
        'created_at': 'createdAt',
        'updated_at': 'updatedAt',
        'is_active': 'isActive'
    }
    
    async def __call__(self, request: Request, call_next):
        # Convert incoming snake_case to camelCase
        if request.method in ['POST', 'PUT', 'PATCH']:
            body = await request.body()
            if body:
                data = json.loads(body)
                converted_data = self.convert_to_camel(data)
                # Inject converted data back into request
        
        response = await call_next(request)
        
        # Convert outgoing camelCase to snake_case for frontend compatibility
        if response.headers.get('content-type') == 'application/json':
            response_data = await response.json()
            converted_response = self.convert_to_snake(response_data)
            return JSONResponse(converted_response)
        
        return response
```

### 1.3 Clean Model Definitions
```python
# NEW: app/models/patient.py
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
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
```

## Phase 2: Data Migration Strategy (3-5 days)

### 2.1 Migration Scripts
```python
# scripts/migrate_to_camelcase.py
async def migrate_patients():
    """Migrate patients from old snake_case to new camelCase schema"""
    
    # Read from old database
    old_patients = await old_db.fetch_all("""
        SELECT id, name, bed_number, ward, assigned_doctor, age, gender,
               diagnosis, admission_date, status, created_at, updated_at, is_active
        FROM patients WHERE is_active = true
    """)
    
    # Insert into new database with camelCase
    for patient in old_patients:
        await new_db.execute("""
            INSERT INTO patients (id, name, bedNumber, ward, assignedDoctor, age, 
                                gender, diagnosis, admissionDate, currentStatus,
                                createdAt, updatedAt, isActive)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        """, patient['id'], patient['name'], patient['bed_number'], 
             patient['ward'], patient['assigned_doctor'], patient['age'],
             patient['gender'], patient['diagnosis'], patient['admission_date'],
             patient['status'], patient['created_at'], patient['updated_at'],
             patient['is_active'])
```

### 2.2 Parallel Deployment
- Run both old and new backends simultaneously
- Route traffic gradually from old to new
- Validate data consistency between systems

## Phase 3: Gradual Frontend Modernization (Optional - 4-6 weeks)

### 3.1 Component-by-Component Migration
```typescript
// NEW: Modern components with camelCase
interface Patient {
    id: string;
    name: string;
    bedNumber: string;
    ward: string;
    assignedDoctor: string;
    currentStatus: 'stable' | 'critical' | 'emergency';
    createdAt: string;
    isActive: boolean;
}

// Update API calls gradually
const fetchPatients = async (): Promise<Patient[]> => {
    const response = await fetch('/api/v2/patients'); // New camelCase API
    return response.json();
};
```

### 3.2 Backward Compatibility
- Keep old API endpoints active during transition
- Feature flags to switch between old/new components
- A/B testing for critical workflows

## Phase 4: Cleanup (1-2 weeks)
- Remove old snake_case database
- Remove translation middleware
- Remove old API endpoints
- Update documentation

## Timeline Summary
- **Phase 1**: New Backend (2-3 weeks)
- **Phase 2**: Migration (3-5 days)  
- **Phase 3**: Frontend Updates (Optional, 4-6 weeks)
- **Phase 4**: Cleanup (1-2 weeks)

**Total**: 4-5 weeks for full backend modernization with working system throughout
**Total with frontend**: 10-12 weeks for complete system modernization

## Benefits
✅ **Zero downtime** - System works throughout migration
✅ **Risk-free** - Can rollback at any point
✅ **Gradual** - Update components as needed
✅ **Clean result** - Modern camelCase system
✅ **Preserve investment** - Keep working frontend initially