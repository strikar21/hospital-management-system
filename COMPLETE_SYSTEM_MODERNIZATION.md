# Complete Hospital System CamelCase Modernization

## Current State Analysis
- **Backend**: 30+ files, ~1000+ snake_case instances
- **Frontend**: 17 files, 522 snake_case instances  
- **Database**: Complete snake_case schema
- **Total**: ~1500+ snake_case instances to convert

## Strategy: Parallel Modernization with Staged Rollout

### Phase 1: Foundation - New Database Schema (Week 1)

#### 1.1 Create Clean CamelCase Database
```sql
-- NEW: hospital_streaming_v2 database
CREATE DATABASE hospital_streaming_v2;

-- All tables with camelCase
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
    activeProblems JSONB,
    lastMedicationTime TIMESTAMP WITH TIME ZONE,
    nextMedicationDue TIMESTAMP WITH TIME ZONE,
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
    deviceToken VARCHAR(255) UNIQUE,
    apiKey VARCHAR(255) UNIQUE,
    lastSeen TIMESTAMP WITH TIME ZONE,
    lastHeartbeat TIMESTAMP WITH TIME ZONE,
    batteryLevel FLOAT,
    signalStrength INTEGER,
    assignmentStatus VARCHAR(20) DEFAULT 'free',
    assignedTo VARCHAR(255),
    assignedAt TIMESTAMP WITH TIME ZONE,
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

-- TimescaleDB tables
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

CREATE TABLE deviceAlertsTs (
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deviceId TEXT NOT NULL,
    patientId TEXT,
    alertType TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT,
    resolvedAt TIMESTAMPTZ,
    acknowledged BOOLEAN DEFAULT FALSE,
    metadata JSONB,
    PRIMARY KEY (timestamp, deviceId, alertType)
);
```

### Phase 2: Backend Modernization (Week 2-3)

#### 2.1 Models with CamelCase
```python
# app/models/patient.py - COMPLETE MODERNIZATION
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON
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
    activeProblems = Column(JSON)
    lastMedicationTime = Column(DateTime(timezone=True))
    nextMedicationDue = Column(DateTime(timezone=True))
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())
    isActive = Column(Boolean, default=True)
    
    # All relationships camelCase
    medications = relationship("PatientMedication", back_populates="patient")
    vitalReadings = relationship("VitalReading", back_populates="patient")
    caseEntries = relationship("PatientCaseEntry", back_populates="patient")
    allergies = relationship("PatientAllergy", back_populates="patient")
    handoffNotes = relationship("HandoffNote", back_populates="patient")

class PatientMedication(Base):
    __tablename__ = "patientMedications"
    
    id = Column(String, primary_key=True)
    patientId = Column(String, ForeignKey("patients.id"))
    name = Column(String, nullable=False)
    dosage = Column(String, nullable=False)
    frequency = Column(String, nullable=False)
    route = Column(String, nullable=False)
    status = Column(String, default="active")
    startDate = Column(DateTime(timezone=True))
    endDate = Column(DateTime(timezone=True))
    prescribedBy = Column(String, nullable=False)
    prescribedAt = Column(DateTime(timezone=True))
    canEdit = Column(Boolean, default=True)
    
    patient = relationship("Patient", back_populates="medications")
```

#### 2.2 Services with CamelCase Queries
```python
# app/services/patient_service.py - MODERNIZED
class PatientService:
    @staticmethod
    async def get_all_patients(limit: int = 100):
        query = """
            SELECT id, name, bedNumber, ward, assignedDoctor, age, gender,
                   diagnosis, admissionDate, currentStatus, codeStatus,
                   activeProblems, lastMedicationTime, nextMedicationDue,
                   createdAt, updatedAt, isActive
            FROM patients 
            WHERE isActive = true 
            ORDER BY createdAt DESC 
            LIMIT $1
        """
        results = await database.fetch_all(query, limit)
        
        # Convert to frontend format
        patients = []
        for row in results:
            patient = {
                "id": row["id"],
                "name": row["name"],
                "bedNumber": row["bedNumber"],
                "ward": row["ward"],
                "assignedDoctor": row["assignedDoctor"],
                "age": row["age"],
                "gender": row["gender"],
                "diagnosis": row["diagnosis"],
                "admissionDate": row["admissionDate"],
                "currentStatus": row["currentStatus"],
                "codeStatus": row["codeStatus"],
                "activeProblems": row["activeProblems"] or [],
                "lastMedicationTime": row["lastMedicationTime"],
                "nextMedicationDue": row["nextMedicationDue"],
                "createdAt": row["createdAt"],
                "updatedAt": row["updatedAt"],
                "isActive": row["isActive"]
            }
            patients.append(patient)
            
        return patients
```

#### 2.3 API Endpoints with CamelCase
```python
# app/api/v1/patients.py - COMPLETE MODERNIZATION
@router.get("/", response_model=List[PatientResponse])
async def get_patients(
    limit: int = 100,
    ward: Optional[str] = None,
    status: Optional[str] = None
):
    """Get patients with camelCase response"""
    patients = await PatientService.get_all_patients(limit)
    
    if ward:
        patients = [p for p in patients if p["ward"] == ward]
    if status:
        patients = [p for p in patients if p["currentStatus"] == status]
    
    return patients

@router.post("/", response_model=PatientResponse) 
async def create_patient(patient: PatientCreate):
    """Create patient with camelCase data"""
    created = await PatientService.create_patient(patient.dict())
    return PatientResponse(**created)

@router.get("/{patientId}/vitals/history")
async def get_patient_vitals_history(
    patientId: str,
    timeRange: str = "24h",
    vitalType: Optional[str] = None
):
    """Get patient vital history with camelCase"""
    query = """
        SELECT timestamp, deviceId, patientId, vitalType, value, unit,
               qualityIndicator, metadata
        FROM vitalReadings
        WHERE patientId = $1
        AND timestamp >= NOW() - INTERVAL $2
    """
    
    if vitalType:
        query += " AND vitalType = $3"
        results = await database.fetch_all(query, patientId, timeRange, vitalType)
    else:
        results = await database.fetch_all(query, patientId, timeRange)
    
    return [{
        "timestamp": r["timestamp"],
        "deviceId": r["deviceId"], 
        "patientId": r["patientId"],
        "vitalType": r["vitalType"],
        "value": r["value"],
        "unit": r["unit"],
        "qualityIndicator": r["qualityIndicator"],
        "metadata": r["metadata"]
    } for r in results]
```

### Phase 3: Frontend Modernization (Week 4-5)

#### 3.1 Types with CamelCase
```typescript
// src/types.ts - COMPLETE MODERNIZATION
export interface Patient {
    id: string;
    name: string;
    bedNumber: string;
    ward: string;
    assignedDoctor: string;
    age?: number;
    gender?: string;
    diagnosis?: string;
    admissionDate?: string;
    currentStatus: 'stable' | 'critical' | 'emergency';
    codeStatus: 'fullCode' | 'dnr' | 'dnrCca' | 'comfortCare';
    activeProblems?: string[];
    lastMedicationTime?: string;
    nextMedicationDue?: string;
    vitals?: PatientVitals;
    allergies?: Allergy[];
    medications?: Medication[];
    caseSheet?: CaseSheetEntry[];
    handoffNotes?: HandoffNote[];
    createdAt: string;
    updatedAt?: string;
    isActive: boolean;
}

export interface PatientVitals {
    heartRate?: number;
    bloodPressure?: string;
    bloodPressureValue?: number;
    temperature?: number;
    respiratoryRate?: number;
    oxygenSat?: number;
    ecg?: number;
    eeg?: number;
    isEcgMode?: boolean;
    bioimpedance?: number;
    tremor?: number;
    fallRisk?: 'low' | 'medium' | 'high';
    lastUpdated?: string;
    lastSync?: string;
}

export interface VitalHistory {
    timestamp: string;
    deviceId: string;
    patientId: string;
    vitalType: string;
    value: number;
    unit: string;
    qualityIndicator?: string;
    metadata?: any;
}

export interface Device {
    id: number;
    deviceId: string;
    name: string;
    deviceType: string;
    status: 'online' | 'offline' | 'maintenance';
    location?: string;
    macAddress?: string;
    ipAddress?: string;
    firmwareVersion?: string;
    batteryLevel?: number;
    signalStrength?: number;
    assignmentStatus: 'free' | 'assigned' | 'maintenance';
    assignedTo?: string;
    assignedAt?: string;
    lastSeen?: string;
    lastHeartbeat?: string;
    createdAt: string;
    updatedAt?: string;
    isActive: boolean;
}
```

#### 3.2 API Service with CamelCase
```typescript
// src/api.ts - MODERNIZED SECTIONS
export class HospitalAPI {
    
    static async getPatients(limit: number = 100): Promise<Patient[]> {
        const response = await this.fetchFromBackend(`/patients?limit=${limit}`);
        
        return response.map((p: any) => ({
            id: p.id,
            name: p.name,
            bedNumber: p.bedNumber,
            ward: p.ward,
            assignedDoctor: p.assignedDoctor,
            age: p.age,
            gender: p.gender,
            diagnosis: p.diagnosis,
            admissionDate: p.admissionDate,
            currentStatus: p.currentStatus,
            codeStatus: p.codeStatus,
            activeProblems: p.activeProblems || [],
            lastMedicationTime: p.lastMedicationTime,
            nextMedicationDue: p.nextMedicationDue,
            // Convert vitals to camelCase if present
            vitals: p.vitals ? {
                heartRate: p.vitals.heartRate || 75,
                bloodPressure: p.vitals.bloodPressure || '120/80',
                bloodPressureValue: p.vitals.bloodPressureValue || 120,
                temperature: p.vitals.temperature || 98.6,
                respiratoryRate: p.vitals.respiratoryRate || 16,
                oxygenSat: p.vitals.oxygenSat || 98,
                ecg: p.vitals.ecg || 120,
                eeg: p.vitals.eeg || 45,
                isEcgMode: p.vitals.isEcgMode !== undefined ? p.vitals.isEcgMode : true,
                bioimpedance: p.vitals.bioimpedance || 500,
                tremor: p.vitals.tremor || 0.0,
                fallRisk: p.vitals.fallRisk || 'low',
                lastUpdated: p.vitals.lastUpdated || new Date().toLocaleTimeString(),
                lastSync: p.vitals.lastSync || new Date().toISOString()
            } : undefined,
            allergies: (p.allergies || []).map((allergy: any) => ({
                id: allergy.id,
                allergen: allergy.allergen,
                allergenType: allergy.allergenType,
                reaction: allergy.reaction,
                severity: allergy.severity,
                verificationStatus: allergy.verificationStatus,
                recordedDate: allergy.recordedDate,
                recordedBy: allergy.recordedBy
            })),
            createdAt: p.createdAt,
            updatedAt: p.updatedAt,
            isActive: p.isActive
        }));
    }

    static async getPatientVitalHistory(
        patientId: string, 
        timeRange: TimeRange = '24h',
        vitalType?: string
    ): Promise<VitalHistory[]> {
        let url = `/patients/${patientId}/vitals/history?timeRange=${timeRange}`;
        if (vitalType) {
            url += `&vitalType=${vitalType}`;
        }
        
        const response = await this.fetchFromBackend(url);
        
        return response.map((record: any) => ({
            timestamp: record.timestamp,
            deviceId: record.deviceId,
            patientId: record.patientId,
            vitalType: record.vitalType,
            value: record.value,
            unit: record.unit,
            qualityIndicator: record.qualityIndicator,
            metadata: record.metadata
        }));
    }
}
```

### Phase 4: Data Migration & Testing (Week 6)

#### 4.1 Comprehensive Data Migration
```python
# scripts/complete_migration.py
async def migrate_complete_system():
    print("🚀 Starting complete system migration...")
    
    # Migrate all entities
    await migrate_patients()
    await migrate_devices() 
    await migrate_staff()
    await migrate_vitals()
    await migrate_medications()
    await migrate_case_entries()
    await migrate_handoff_notes()
    
    print("✅ Complete system migration finished!")

async def migrate_patients():
    print("👥 Migrating patients...")
    old_patients = await old_db.fetch_all("""
        SELECT * FROM patients WHERE is_active = true
    """)
    
    for p in old_patients:
        await new_db.execute("""
            INSERT INTO patients (id, name, bedNumber, ward, assignedDoctor,
                                age, gender, diagnosis, admissionDate, currentStatus,
                                codeStatus, activeProblems, lastMedicationTime,
                                nextMedicationDue, createdAt, updatedAt, isActive)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
        """, p['id'], p['name'], p['bed_number'], p['ward'], p['assigned_doctor'],
             p['age'], p['gender'], p['diagnosis'], p['admission_date'], p['status'],
             p['code_status'], p['active_problems'], p['last_medication_time'],
             p['next_medication_due'], p['created_at'], p['updated_at'], p['is_active'])
    
    print(f"✅ Migrated {len(old_patients)} patients")
```

#### 4.2 End-to-End Testing
```typescript
// tests/integration/complete-system.test.ts
describe('Complete CamelCase System', () => {
    test('Patient CRUD operations', async () => {
        // Create patient with camelCase
        const patientData = {
            id: 'P001',
            name: 'John Doe',
            bedNumber: 'A101',
            ward: 'ICU',
            assignedDoctor: 'Dr. Smith',
            currentStatus: 'stable',
            codeStatus: 'fullCode'
        };
        
        const response = await api.post('/api/v1/patients', patientData);
        expect(response.data.bedNumber).toBe('A101');
        expect(response.data.isActive).toBe(true);
    });
    
    test('Vitals data flow', async () => {
        const vitalData = {
            deviceId: 'DEV001',
            patientId: 'P001', 
            vitalType: 'heartRate',
            value: 75,
            qualityIndicator: 'good'
        };
        
        await api.post('/api/v1/vitals', vitalData);
        
        const history = await api.get('/api/v1/patients/P001/vitals/history');
        expect(history.data[0].vitalType).toBe('heartRate');
        expect(history.data[0].deviceId).toBe('DEV001');
    });
});
```

### Timeline Summary
- **Week 1**: Database schema + migration scripts
- **Week 2-3**: Complete backend modernization (models, services, APIs)
- **Week 4-5**: Complete frontend modernization (types, components, API calls)
- **Week 6**: Testing + deployment

## Benefits
✅ **Unified system** - Complete camelCase across all layers
✅ **Modern codebase** - Clean, maintainable code
✅ **Better performance** - Optimized queries and data flow
✅ **Easier development** - Consistent naming conventions
✅ **Zero technical debt** - Fresh start with best practices

This comprehensive approach ensures your entire hospital system uses consistent camelCase naming throughout.