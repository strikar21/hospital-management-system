# Baseline Fix Implementation Plan
**Date:** 2025-10-05
**Project:** Hospital Management System
**Purpose:** Establish solid foundation addressing all critical security, validation, and data integrity issues
**Based on:** COMPREHENSIVE_DEEP_AUDIT_REPORT.md + COMPREHENSIVE_ERROR_DETECTION_AUDIT.md + FINAL_COMPREHENSIVE_AUDIT_REPORT.md

---

## Executive Summary

### Total Baseline Fixes Required: 147
- **Critical Issues (P0):** 42 - Must fix immediately (patient safety, security, data loss)
- **High Priority (P1):** 51 - Fix within 1-2 weeks (data integrity, compliance)
- **Medium Priority (P2):** 38 - Fix within 1 month (reliability, UX)
- **Low Priority (P3):** 16 - Fix within 3 months (optimization, cleanup)

### Fix Distribution by Layer
- **Database Foundation:** 32 fixes (constraints, migrations, soft delete)
- **Backend Security:** 28 fixes (auth, validation, secrets)
- **Backend Error Handling:** 35 fixes (try-catch, null checks, race conditions)
- **Frontend Error Handling:** 24 fixes (null safety, API errors, loading states)
- **API Validation:** 18 fixes (Pydantic models, input sanitization)
- **Configuration:** 10 fixes (environment variables, CORS, logging)

### Current State Assessment
✅ **Architecture:** 98% compliant - medical logic backend-only, frontend display-only
✅ **camelCase:** 98% compliant - database, backend, frontend standardized
❌ **Database Constraints:** 20% complete - missing foreign keys, checks, soft delete
❌ **Security:** 45% complete - hardcoded secrets, no JWT validation, SQL injection risks
❌ **Validation:** 30% complete - minimal Pydantic validation, no medical data validation
❌ **Error Handling:** 40% complete - many try-catch blocks missing, null pointer risks

### Target State (After Baseline)
- ✅ 100% database referential integrity with foreign keys and constraints
- ✅ 100% authentication required, no default "SYSTEM" bypasses
- ✅ 100% input validation on all endpoints with medical data validation
- ✅ 95% error handling coverage with specific exception catching
- ✅ 100% soft delete implementation, no data loss
- ✅ 0 hardcoded secrets, all environment variables validated

---

## Part 1: Database Foundation (Week 1-2, Priority P0-P1)

### Phase 1.1: Add Foreign Key Constraints (Days 1-3)

**Execution Order:** patients → staff → devices → medical records

#### Fix #1: Add Foreign Keys to medications table
**Severity:** HIGH
**File:** New migration file: `hospital-backend/migrations/001_add_foreign_keys_medications.sql`
**Current State:**
```sql
CREATE TABLE medications (
    "patientId" TEXT NOT NULL,  -- ❌ No FK constraint
    "prescribedBy" TEXT NOT NULL,  -- ❌ No FK constraint
    ...
);
```

**New Migration Code:**
```sql
-- 001_add_foreign_keys_medications.sql

-- Add foreign key to patients table
ALTER TABLE medications
ADD CONSTRAINT fk_medications_patient
FOREIGN KEY ("patientId") REFERENCES patients(id)
ON DELETE CASCADE;  -- If patient deleted, cascade delete medications

-- Add foreign key to staff table (prescriber)
ALTER TABLE medications
ADD CONSTRAINT fk_medications_prescriber
FOREIGN KEY ("prescribedBy") REFERENCES staff(id)
ON DELETE RESTRICT;  -- Cannot delete staff who prescribed medications

-- Add foreign key to staff table (creator)
ALTER TABLE medications
ADD CONSTRAINT fk_medications_creator
FOREIGN KEY ("createdBy") REFERENCES staff(id)
ON DELETE SET NULL;  -- Set to NULL if creator deleted
```

**Backend Changes Required:**
- **File:** `hospital-backend/app/services/medication_service.py:40-70`
- **Change:** Add exception handling for FK violations
```python
# BEFORE:
async def add_medication(self, patient_id: str, medication_data: Dict[str, Any], user_id: str):
    return await self.medication_repository.create_medication(patient_id, medication_data)

# AFTER:
async def add_medication(self, patient_id: str, medication_data: Dict[str, Any], user_id: str):
    try:
        return await self.medication_repository.create_medication(patient_id, medication_data)
    except asyncpg.ForeignKeyViolationError as e:
        if 'fk_medications_patient' in str(e):
            raise ValueError(f"Patient {patient_id} not found")
        elif 'fk_medications_prescriber' in str(e):
            raise ValueError(f"Prescriber {medication_data.get('prescribedBy')} not found in staff directory")
        else:
            raise ValueError(f"Invalid reference: {str(e)}")
    except asyncpg.UniqueViolationError as e:
        raise ValueError(f"Duplicate medication record")
```

**Frontend Changes Required:**
- **File:** `hospital-display-app/src/services/MedicationService.ts:47-68`
- **Change:** Handle new error messages
```typescript
// Add error handling in catch block
catch (error: any) {
  if (error.message?.includes('Patient') && error.message?.includes('not found')) {
    throw new Error('This patient no longer exists. Please refresh the page.');
  }
  if (error.message?.includes('Prescriber') && error.message?.includes('not found')) {
    throw new Error('The selected prescriber is not in the staff directory. Please select a valid staff member.');
  }
  throw error;
}
```

**Testing Checklist:**
- [ ] Unit test: Try to create medication for non-existent patient → should fail with clear error
- [ ] Unit test: Try to create medication with invalid prescriber → should fail with clear error
- [ ] Unit test: Delete patient with medications → should cascade delete medications
- [ ] Unit test: Try to delete staff who prescribed medications → should fail with RESTRICT error
- [ ] Integration test: Full medication creation flow with valid references → should succeed
- [ ] Manual test: Frontend displays proper error messages

**Impact:** Prevents orphaned medication records, ensures data integrity

---

#### Fix #2: Add Foreign Keys to investigations table
**Severity:** HIGH
**File:** `hospital-backend/migrations/002_add_foreign_keys_investigations.sql`

**Migration Code:**
```sql
-- Add foreign keys for investigations
ALTER TABLE investigations
ADD CONSTRAINT fk_investigations_patient
FOREIGN KEY ("patientId") REFERENCES patients(id)
ON DELETE CASCADE;

ALTER TABLE investigations
ADD CONSTRAINT fk_investigations_prescriber
FOREIGN KEY ("prescribedBy") REFERENCES staff(id)
ON DELETE RESTRICT;

ALTER TABLE investigations
ADD CONSTRAINT fk_investigations_performer
FOREIGN KEY ("performedBy") REFERENCES staff(id)
ON DELETE SET NULL;

ALTER TABLE investigations
ADD CONSTRAINT fk_investigations_creator
FOREIGN KEY ("createdBy") REFERENCES staff(id)
ON DELETE SET NULL;
```

**Backend Changes:**
- **File:** `hospital-backend/app/services/investigation_service.py`
- **Pattern:** Same FK violation handling as medications (see Fix #1)

**Testing:** Same pattern as Fix #1

---

#### Fix #3: Add Foreign Keys to therapy table
**Severity:** HIGH
**File:** `hospital-backend/migrations/003_add_foreign_keys_therapy.sql`

**Migration Code:**
```sql
ALTER TABLE therapy
ADD CONSTRAINT fk_therapy_patient
FOREIGN KEY ("patientId") REFERENCES patients(id)
ON DELETE CASCADE;

ALTER TABLE therapy
ADD CONSTRAINT fk_therapy_prescriber
FOREIGN KEY ("prescribedBy") REFERENCES staff(id)
ON DELETE RESTRICT;

ALTER TABLE therapy
ADD CONSTRAINT fk_therapy_creator
FOREIGN KEY ("createdBy") REFERENCES staff(id)
ON DELETE SET NULL;
```

---

#### Fix #4: Add Foreign Keys to therapysessions table
**Severity:** HIGH
**File:** `hospital-backend/migrations/004_add_foreign_keys_therapysessions.sql`

**Migration Code:**
```sql
ALTER TABLE therapysessions
ADD CONSTRAINT fk_therapysessions_therapy
FOREIGN KEY ("therapyId") REFERENCES therapy(id)
ON DELETE CASCADE;

ALTER TABLE therapysessions
ADD CONSTRAINT fk_therapysessions_patient
FOREIGN KEY ("patientId") REFERENCES patients(id)
ON DELETE CASCADE;

ALTER TABLE therapysessions
ADD CONSTRAINT fk_therapysessions_performer
FOREIGN KEY ("performedBy") REFERENCES staff(id)
ON DELETE SET NULL;

ALTER TABLE therapysessions
ADD CONSTRAINT fk_therapysessions_creator
FOREIGN KEY ("createdBy") REFERENCES staff(id)
ON DELETE SET NULL;
```

---

#### Fix #5: Add Foreign Keys to patientnotes table
**Severity:** HIGH
**File:** `hospital-backend/migrations/005_add_foreign_keys_patientnotes.sql`

**Migration Code:**
```sql
ALTER TABLE patientnotes
ADD CONSTRAINT fk_patientnotes_patient
FOREIGN KEY ("patientId") REFERENCES patients(id)
ON DELETE CASCADE;

ALTER TABLE patientnotes
ADD CONSTRAINT fk_patientnotes_creator
FOREIGN KEY ("createdBy") REFERENCES staff(id)
ON DELETE SET NULL;

ALTER TABLE patientnotes
ADD CONSTRAINT fk_patientnotes_editor
FOREIGN KEY ("editedBy") REFERENCES staff(id)
ON DELETE SET NULL;
```

---

#### Fix #6: Add Foreign Keys to caseEntries table
**Severity:** HIGH
**File:** `hospital-backend/migrations/006_add_foreign_keys_caseentries.sql`

**Migration Code:**
```sql
ALTER TABLE "caseEntries"
ADD CONSTRAINT fk_caseentries_patient
FOREIGN KEY ("patientId") REFERENCES patients(id)
ON DELETE CASCADE;

ALTER TABLE "caseEntries"
ADD CONSTRAINT fk_caseentries_performer
FOREIGN KEY ("performedBy") REFERENCES staff(id)
ON DELETE SET NULL;

ALTER TABLE "caseEntries"
ADD CONSTRAINT fk_caseentries_creator
FOREIGN KEY ("createdBy") REFERENCES staff(id)
ON DELETE SET NULL;
```

---

#### Fix #7: Add Foreign Keys to patient_alerts table
**Severity:** HIGH
**File:** `hospital-backend/migrations/007_add_foreign_keys_alerts.sql`

**Migration Code:**
```sql
ALTER TABLE patient_alerts
ADD CONSTRAINT fk_alerts_patient
FOREIGN KEY ("patientId") REFERENCES patients(id)
ON DELETE CASCADE;

ALTER TABLE patient_alerts
ADD CONSTRAINT fk_alerts_performer
FOREIGN KEY ("performedBy") REFERENCES staff(id)
ON DELETE SET NULL;

ALTER TABLE patient_alerts
ADD CONSTRAINT fk_alerts_resolver
FOREIGN KEY ("resolvedBy") REFERENCES staff(id)
ON DELETE SET NULL;
```

---

#### Fix #8: Add Foreign Keys to deviceassignments table
**Severity:** HIGH
**File:** `hospital-backend/migrations/008_add_foreign_keys_deviceassignments.sql`

**Migration Code:**
```sql
ALTER TABLE deviceassignments
ADD CONSTRAINT fk_deviceassignments_patient
FOREIGN KEY ("patientId") REFERENCES patients(id)
ON DELETE CASCADE;

ALTER TABLE deviceassignments
ADD CONSTRAINT fk_deviceassignments_device
FOREIGN KEY ("deviceId") REFERENCES devices(id)
ON DELETE CASCADE;

ALTER TABLE deviceassignments
ADD CONSTRAINT fk_deviceassignments_assigner
FOREIGN KEY ("assignedBy") REFERENCES staff(id)
ON DELETE SET NULL;
```

---

#### Fix #9: Add Foreign Keys to medicationadministrations table
**Severity:** CRITICAL - PATIENT SAFETY
**File:** `hospital-backend/migrations/009_add_foreign_keys_medadmin.sql`

**Migration Code:**
```sql
ALTER TABLE medicationadministrations
ADD CONSTRAINT fk_medadmin_medication
FOREIGN KEY ("medicationId") REFERENCES medications(id)
ON DELETE CASCADE;

ALTER TABLE medicationadministrations
ADD CONSTRAINT fk_medadmin_patient
FOREIGN KEY ("patientId") REFERENCES patients(id)
ON DELETE CASCADE;

ALTER TABLE medicationadministrations
ADD CONSTRAINT fk_medadmin_performer
FOREIGN KEY ("performedBy") REFERENCES staff(id)
ON DELETE SET NULL;

ALTER TABLE medicationadministrations
ADD CONSTRAINT fk_medadmin_creator
FOREIGN KEY ("createdBy") REFERENCES staff(id)
ON DELETE SET NULL;
```

---

### Phase 1.2: Add CHECK Constraints (Days 4-5)

#### Fix #10: Add Status CHECK Constraints
**Severity:** MEDIUM
**File:** `hospital-backend/migrations/010_add_check_constraints_status.sql`

**Migration Code:**
```sql
-- Medications status
ALTER TABLE medications
ADD CONSTRAINT check_medications_status
CHECK (status IN ('active', 'completed', 'discontinued', 'on_hold'));

-- Investigations status
ALTER TABLE investigations
ADD CONSTRAINT check_investigations_status
CHECK (status IN ('ordered', 'scheduled', 'in_progress', 'completed', 'cancelled'));

-- Therapy status
ALTER TABLE therapy
ADD CONSTRAINT check_therapy_status
CHECK (status IN ('active', 'completed', 'discontinued', 'on_hold'));

-- Patient status
ALTER TABLE patients
ADD CONSTRAINT check_patients_status
CHECK (status IN ('active', 'discharged', 'deceased', 'transferred'));

-- Devices status
ALTER TABLE devices
ADD CONSTRAINT check_devices_status
CHECK (status IN ('available', 'assigned', 'maintenance', 'retired'));

-- Alert severity
ALTER TABLE patient_alerts
ADD CONSTRAINT check_alerts_severity
CHECK (severity IN ('low', 'medium', 'high', 'critical', 'emergency'));
```

**Impact:** Prevents typos creating invalid statuses ('actuve', 'Active', 'ACTIVE')

---

#### Fix #11: Add Date Validation Constraints
**Severity:** MEDIUM
**File:** `hospital-backend/migrations/011_add_check_constraints_dates.sql`

**Migration Code:**
```sql
-- Birth date cannot be in future
ALTER TABLE patients
ADD CONSTRAINT check_patients_birthdate
CHECK ("dateOfBirth" IS NULL OR "dateOfBirth" <= CURRENT_DATE);

-- Discharge date must be after admission date
ALTER TABLE patients
ADD CONSTRAINT check_patients_discharge_after_admission
CHECK ("dischargeDate" IS NULL OR "admissionDate" IS NULL OR "dischargeDate" >= "admissionDate");

-- Medication end date must be after start date
ALTER TABLE medications
ADD CONSTRAINT check_medications_dates
CHECK ("endDate" IS NULL OR "startDate" IS NULL OR "endDate" >= "startDate");

-- Therapy end date must be after start date
ALTER TABLE therapy
ADD CONSTRAINT check_therapy_dates
CHECK ("endDate" IS NULL OR "startDate" IS NULL OR "endDate" >= "startDate");

-- Investigation completed must be after scheduled
ALTER TABLE investigations
ADD CONSTRAINT check_investigations_dates
CHECK ("completedAt" IS NULL OR "scheduledAt" IS NULL OR "completedAt" >= "scheduledAt");
```

---

#### Fix #12: Add Numeric Range Constraints
**Severity:** LOW
**File:** `hospital-backend/migrations/012_add_check_constraints_ranges.sql`

**Migration Code:**
```sql
-- Age must be reasonable (0-150 years)
ALTER TABLE admissionrecommendations
ADD CONSTRAINT check_admission_age
CHECK (age IS NULL OR (age >= 0 AND age <= 150));

-- Battery level 0-100%
ALTER TABLE devices
ADD CONSTRAINT check_devices_battery
CHECK ("batteryLevel" IS NULL OR ("batteryLevel" >= 0 AND "batteryLevel" <= 100));

-- Session number must be positive
ALTER TABLE therapysessions
ADD CONSTRAINT check_session_number
CHECK ("sessionNumber" > 0);
```

---

### Phase 1.3: Add UNIQUE Constraints (Day 6)

#### Fix #13: Add Unique Constraints
**Severity:** MEDIUM
**File:** `hospital-backend/migrations/013_add_unique_constraints.sql`

**Migration Code:**
```sql
-- Patient MRN must be unique (if provided)
ALTER TABLE patients
ADD CONSTRAINT unique_patients_mrn
UNIQUE (mrn);

-- Device serial numbers must be unique
-- (Already exists in schema, verify)

-- Device MAC addresses must be unique
-- (Already exists in schema, verify)

-- Staff email must be unique
-- (Already exists in schema, verify)

-- Staff NFC card ID must be unique
-- (Already exists in schema, verify)

-- Only one active device assignment per device
CREATE UNIQUE INDEX unique_active_device_assignment
ON deviceassignments ("deviceId")
WHERE status = 'active';
```

**Backend Changes Required:**
- **File:** `hospital-backend/app/services/patient_service.py`
- **Change:** Handle MRN uniqueness violation
```python
try:
    patient = await self.patient_repository.create_patient(patient_data)
except asyncpg.UniqueViolationError as e:
    if 'unique_patients_mrn' in str(e):
        raise ValueError(f"Patient with MRN {patient_data.get('mrn')} already exists")
    raise
```

---

### Phase 1.4: Implement Soft Delete (Days 7-8)

#### Fix #14: Add deletedAt Column to All Tables
**Severity:** CRITICAL - COMPLIANCE
**File:** `hospital-backend/migrations/014_add_soft_delete.sql`

**Migration Code:**
```sql
-- Add deletedAt column to all tables that don't have it
ALTER TABLE patients ADD COLUMN IF NOT EXISTS "deletedAt" TIMESTAMPTZ;
ALTER TABLE medications ADD COLUMN IF NOT EXISTS "deletedAt" TIMESTAMPTZ;
ALTER TABLE investigations ADD COLUMN IF NOT EXISTS "deletedAt" TIMESTAMPTZ;
ALTER TABLE therapy ADD COLUMN IF NOT EXISTS "deletedAt" TIMESTAMPTZ;
ALTER TABLE therapysessions ADD COLUMN IF NOT EXISTS "deletedAt" TIMESTAMPTZ;
ALTER TABLE patientnotes ADD COLUMN IF NOT EXISTS "deletedAt" TIMESTAMPTZ;
ALTER TABLE medicationadministrations ADD COLUMN IF NOT EXISTS "deletedAt" TIMESTAMPTZ;

-- Create index for soft delete queries
CREATE INDEX idx_patients_not_deleted ON patients ("deletedAt") WHERE "deletedAt" IS NULL;
CREATE INDEX idx_medications_not_deleted ON medications ("deletedAt") WHERE "deletedAt" IS NULL;
CREATE INDEX idx_investigations_not_deleted ON investigations ("deletedAt") WHERE "deletedAt" IS NULL;
CREATE INDEX idx_therapy_not_deleted ON therapy ("deletedAt") WHERE "deletedAt" IS NULL;
```

**Backend Changes Required:**
- **File:** `hospital-backend/app/repositories/base_repository.py:50-80`
- **Change:** Modify all SELECT queries to filter out soft-deleted records

**BEFORE:**
```python
async def get_all(self) -> List[Dict[str, Any]]:
    query = f'SELECT * FROM {self.table_name}'
    return await self.execute_custom_query(query)
```

**AFTER:**
```python
async def get_all(self, include_deleted: bool = False) -> List[Dict[str, Any]]:
    if include_deleted:
        query = f'SELECT * FROM {self.table_name}'
    else:
        query = f'SELECT * FROM {self.table_name} WHERE "deletedAt" IS NULL'
    return await self.execute_custom_query(query)

async def soft_delete(self, record_id: str, deleted_by: str) -> bool:
    """Soft delete a record by setting deletedAt timestamp"""
    query = f'''
        UPDATE {self.table_name}
        SET "deletedAt" = NOW(), "updatedAt" = NOW()
        WHERE id = $1 AND "deletedAt" IS NULL
        RETURNING id
    '''
    result = await self.execute_custom_query(query, [record_id])
    return len(result) > 0
```

- **File:** `hospital-backend/app/services/patient_service.py`
- **Change:** Replace hard delete with soft delete

**BEFORE:**
```python
async def delete_patient(self, patient_id: str):
    return await self.patient_repository.delete(patient_id)
```

**AFTER:**
```python
async def delete_patient(self, patient_id: str, deleted_by: str):
    """Soft delete patient - preserves all medical history"""
    # Validate patient can be deleted
    patient = await self.patient_repository.get_by_id(patient_id)
    if not patient:
        raise ValueError(f"Patient {patient_id} not found")

    if patient.get('status') == 'active':
        raise ValueError("Cannot delete active patient. Discharge patient first.")

    # Soft delete patient (cascades to related records via database triggers)
    success = await self.patient_repository.soft_delete(patient_id, deleted_by)

    if success:
        # Log to audit trail
        await self.audit_log(
            user_id=deleted_by,
            action="PATIENT_SOFT_DELETE",
            resource_type="patient",
            resource_id=patient_id,
            details=f"Patient {patient.get('firstName')} {patient.get('lastName')} soft deleted"
        )

    return success
```

**Testing:**
- [ ] Soft delete patient → verify patient.deletedAt is set
- [ ] Verify get_all() excludes soft-deleted patients
- [ ] Verify get_by_id() can still retrieve deleted patient with include_deleted=True
- [ ] Verify medical history preserved after patient soft delete
- [ ] Verify audit log entry created

---

## Part 2: Security Baseline (Week 2, Priority P0)

### Phase 2.1: Remove Hardcoded Secrets (Days 1-2)

#### Fix #15: Remove Hardcoded Database Passwords
**Severity:** CRITICAL
**Files to Change:**
- `hospital-backend/app/core/config.py:18, 26, 31`
- `hospital-backend/docker-compose.yml:10, 29, 63`

**Current Code (config.py):**
```python
databasePassword: str = os.environ.get("DATABASE_PASSWORD", "hospital123")  # ❌
timescaledbPassword: str = os.environ.get("TIMESCALEDB_PASSWORD", "hospital123")  # ❌
secretKey: str = os.environ.get("SECRET_KEY", "HSM-2024-SecureKey-ChangeInProd-V1.0")  # ❌
```

**New Code:**
```python
# Require environment variables, no defaults
databasePassword: str = os.environ.get("DATABASE_PASSWORD")
if not databasePassword:
    raise ValueError("DATABASE_PASSWORD environment variable is required")

timescaledbPassword: str = os.environ.get("TIMESCALEDB_PASSWORD")
if not timescaledbPassword:
    raise ValueError("TIMESCALEDB_PASSWORD environment variable is required")

secretKey: str = os.environ.get("SECRET_KEY")
if not secretKey or len(secretKey) < 32:
    raise ValueError("SECRET_KEY environment variable is required (minimum 32 characters)")
```

**Related Changes:**

1. **Create .env.example (if doesn't exist):**
```bash
# Database Configuration
DATABASE_URL=postgresql://hospital_user:YOUR_SECURE_PASSWORD@localhost:5432/hospitaldb
DATABASE_PASSWORD=YOUR_SECURE_PASSWORD

# TimescaleDB Configuration
TIMESCALEDB_URL=postgresql://hospital_user:YOUR_SECURE_PASSWORD@localhost:5433/hospitaltimescale
TIMESCALEDB_PASSWORD=YOUR_SECURE_PASSWORD

# Security
SECRET_KEY=GENERATE_MINIMUM_32_CHARACTER_RANDOM_STRING_HERE

# SMTP (for alerts)
SMTP_PASSWORD=YOUR_APP_PASSWORD

# MQTT (for ESP32)
MQTT_PASSWORD=YOUR_MQTT_PASSWORD
```

2. **Add startup validation script:**
- **File:** `hospital-backend/app/core/startup_validation.py` (NEW FILE)
```python
"""
Startup validation to ensure all required environment variables are set
"""
import os
import sys
import logging

logger = logging.getLogger(__name__)

REQUIRED_ENV_VARS = [
    "DATABASE_PASSWORD",
    "TIMESCALEDB_PASSWORD",
    "SECRET_KEY",
]

def validate_environment():
    """Validate all required environment variables are set"""
    missing = []
    for var in REQUIRED_ENV_VARS:
        if not os.environ.get(var):
            missing.append(var)

    if missing:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing)}")
        logger.error("Please set these variables in your .env file or environment")
        sys.exit(1)

    # Validate SECRET_KEY length
    secret_key = os.environ.get("SECRET_KEY")
    if len(secret_key) < 32:
        logger.error("❌ SECRET_KEY must be at least 32 characters long")
        sys.exit(1)

    logger.info("✅ Environment validation passed")
```

3. **Update main.py to call validation:**
- **File:** `hospital-backend/main.py:1-20`
```python
# Add at top of file
from app.core.startup_validation import validate_environment

# Call before creating FastAPI app
validate_environment()

app = FastAPI(title="Hospital Management System")
```

4. **Update docker-compose.yml:**
```yaml
# REMOVE hardcoded passwords, use .env file
postgres:
  environment:
    POSTGRES_PASSWORD: ${DATABASE_PASSWORD}  # From .env

timescaledb:
  environment:
    POSTGRES_PASSWORD: ${TIMESCALEDB_PASSWORD}  # From .env

pgadmin:
  environment:
    PGADMIN_DEFAULT_PASSWORD: ${PGADMIN_PASSWORD}  # From .env
```

**Testing:**
- [ ] Start app without .env file → should fail with clear error message
- [ ] Start app with SECRET_KEY < 32 chars → should fail with error
- [ ] Start app with valid .env → should start successfully

**Impact:** Prevents production deployment with default credentials

---

#### Fix #16: Remove Hardcoded Seed Credentials
**Severity:** CRITICAL
**File:** `hospital-backend/app/core/database.py:543-605`

**Current Code:**
```python
staffCredentials = [
    {"id": "DOC0001", "pin": hash_pin("1234"), "password": hash_password("doctor123")},
    {"id": "ADM0001", "pin": hash_pin("9999"), "password": hash_password("admin123")},
]
```

**Change:** Add environment check to prevent seed in production

**New Code:**
```python
async def seedDatabase():
    """Seed database with initial data - DEVELOPMENT ONLY"""

    # CRITICAL: Never run in production
    if os.environ.get("ENVIRONMENT") == "production":
        logger.error("❌ CRITICAL: Attempted to run seed function in production")
        logger.error("❌ Seed data contains weak default passwords")
        raise RuntimeError("Seed function cannot run in production environment")

    logger.warning("⚠️  Running database seed - DEVELOPMENT MODE ONLY")
    logger.warning("⚠️  Default passwords are WEAK and must be changed immediately")

    # ... existing seed code ...
```

**Related Changes:**

1. **Add environment detection:**
- **File:** `hospital-backend/app/core/config.py`
```python
class Settings(BaseSettings):
    # Add environment setting
    environment: str = os.environ.get("ENVIRONMENT", "development")

    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    def is_development(self) -> bool:
        return self.environment.lower() in ["development", "dev", "local"]
```

2. **Update deployment docs to set ENVIRONMENT=production**

**Testing:**
- [ ] Set ENVIRONMENT=production, try to seed → should fail
- [ ] Set ENVIRONMENT=development, try to seed → should work with warning

---

### Phase 2.2: Implement JWT Authentication (Days 3-5)

#### Fix #17: Add JWT Token Validation Middleware
**Severity:** CRITICAL
**File:** `hospital-backend/app/middleware/auth.py` (NEW FILE)

**New Code:**
```python
"""
JWT Authentication Middleware
"""
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()

async def verify_jwt_token(credentials: HTTPAuthorizationCredentials) -> dict:
    """Verify JWT token and return payload"""
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.secretKey,
            algorithms=[settings.algorithm]
        )

        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )

        # Verify required fields
        if not payload.get("user_id") or not payload.get("role"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing required fields"
            )

        return payload

    except JWTError as e:
        logger.error(f"JWT validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

def create_access_token(user_id: str, role: str, email: str) -> str:
    """Create JWT access token"""
    expires = datetime.utcnow() + timedelta(minutes=settings.accessTokenExpireMinutes)

    payload = {
        "user_id": user_id,
        "role": role,
        "email": email,
        "exp": expires,
        "iat": datetime.utcnow()
    }

    token = jwt.encode(payload, settings.secretKey, algorithm=settings.algorithm)
    return token

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dependency to extract current user from JWT token"""
    return await verify_jwt_token(credentials)
```

**Related Changes:**

1. **Update atomic medical endpoints to require auth:**
- **File:** `hospital-backend/app/api/v2/atomic_medical.py:108-150`

**BEFORE:**
```python
@router.post("/patients/{patient_id}/medications")
async def add_medication_atomic_endpoint(
    patient_id: str,
    medication: MedicationRequest,
    performed_by: str = "SYSTEM"  # ❌ Default bypass
):
```

**AFTER:**
```python
from ...middleware.auth import get_current_user

@router.post("/patients/{patient_id}/medications")
async def add_medication_atomic_endpoint(
    patient_id: str,
    medication: MedicationRequest,
    current_user: dict = Depends(get_current_user)  # ✅ Required auth
):
    # Extract user_id from token
    performed_by = current_user["user_id"]
    user_role = current_user["role"]

    # Verify user has permission to prescribe
    if medication.prescribedBy and medication.prescribedBy != performed_by:
        # Ensure only doctors can prescribe
        if user_role not in ["doctor", "physician", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only doctors can prescribe medications"
            )
```

2. **Apply to ALL endpoints that modify data:**
- `add_investigation_atomic_endpoint`
- `add_therapy_atomic_endpoint`
- `add_note_atomic_endpoint`
- `administer_medication_atomic_endpoint`
- All v1 endpoints

**Testing:**
- [ ] Call endpoint without token → should return 401 Unauthorized
- [ ] Call endpoint with expired token → should return 401 Unauthorized
- [ ] Call endpoint with invalid token → should return 401 Unauthorized
- [ ] Call endpoint with valid token → should succeed
- [ ] Nurse tries to prescribe medication → should return 403 Forbidden

---

#### Fix #18: Implement Role-Based Access Control (RBAC)
**Severity:** HIGH
**File:** `hospital-backend/app/middleware/rbac.py` (NEW FILE)

**New Code:**
```python
"""
Role-Based Access Control (RBAC) Middleware
"""
from fastapi import HTTPException, status
from typing import List
from enum import Enum

class Role(str, Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    NURSE = "nurse"
    PHARMACIST = "pharmacist"
    LAB_TECH = "lab_tech"
    RADIOLOGIST = "radiologist"

class Permission(str, Enum):
    PRESCRIBE_MEDICATION = "prescribe_medication"
    ADMINISTER_MEDICATION = "administer_medication"
    ORDER_INVESTIGATION = "order_investigation"
    PERFORM_INVESTIGATION = "perform_investigation"
    CREATE_THERAPY = "create_therapy"
    PERFORM_THERAPY = "perform_therapy"
    ADMIT_PATIENT = "admit_patient"
    DISCHARGE_PATIENT = "discharge_patient"
    VIEW_PATIENT = "view_patient"
    EDIT_PATIENT = "edit_patient"

ROLE_PERMISSIONS = {
    Role.ADMIN: [p for p in Permission],  # All permissions
    Role.DOCTOR: [
        Permission.PRESCRIBE_MEDICATION,
        Permission.ORDER_INVESTIGATION,
        Permission.CREATE_THERAPY,
        Permission.ADMIT_PATIENT,
        Permission.DISCHARGE_PATIENT,
        Permission.VIEW_PATIENT,
        Permission.EDIT_PATIENT,
    ],
    Role.NURSE: [
        Permission.ADMINISTER_MEDICATION,
        Permission.PERFORM_THERAPY,
        Permission.VIEW_PATIENT,
        Permission.EDIT_PATIENT,
    ],
    Role.PHARMACIST: [
        Permission.ADMINISTER_MEDICATION,
        Permission.VIEW_PATIENT,
    ],
    Role.LAB_TECH: [
        Permission.PERFORM_INVESTIGATION,
        Permission.VIEW_PATIENT,
    ],
}

def require_permission(required_permission: Permission):
    """Decorator to require specific permission"""
    def decorator(func):
        async def wrapper(*args, current_user: dict, **kwargs):
            user_role = Role(current_user.get("role"))
            user_permissions = ROLE_PERMISSIONS.get(user_role, [])

            if required_permission not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{user_role}' does not have permission '{required_permission}'"
                )

            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator
```

**Usage Example:**
```python
from ...middleware.rbac import require_permission, Permission

@router.post("/patients/{patient_id}/medications")
async def add_medication_atomic_endpoint(
    patient_id: str,
    medication: MedicationRequest,
    current_user: dict = Depends(get_current_user)
):
    # Check permission
    user_role = Role(current_user.get("role"))
    user_permissions = ROLE_PERMISSIONS.get(user_role, [])

    if Permission.PRESCRIBE_MEDICATION not in user_permissions:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to prescribe medications"
        )

    # Continue with medication creation...
```

**Testing:**
- [ ] Doctor prescribes medication → should succeed
- [ ] Nurse tries to prescribe medication → should fail with 403
- [ ] Nurse administers medication → should succeed
- [ ] Lab tech performs investigation → should succeed
- [ ] Lab tech tries to prescribe medication → should fail with 403

---

### Phase 2.3: Fix SQL Injection Vulnerabilities (Day 6)

#### Fix #19: Whitelist Column Names in Dynamic Queries
**Severity:** CRITICAL
**File:** `hospital-backend/app/services/medical_action_service.py:206-228`

**Current Code (VULNERABLE):**
```python
columns = list(med_data.keys())  # ❌ Keys come from API request
quoted_columns = [f'"{col}"' if any(c.isupper() for c in col) else col for col in columns]
query = f"""
    INSERT INTO medications ({', '.join(quoted_columns)})
    VALUES ({', '.join(placeholders)})
    RETURNING *
"""
```

**New Code (SECURE):**
```python
# Define allowed column whitelist
ALLOWED_MEDICATION_COLUMNS = {
    'patientId', 'name', 'dosage', 'frequency', 'route',
    'startDate', 'endDate', 'duration', 'status',
    'prescribedBy', 'createdBy', 'createdAt', 'updatedAt'
}

def sanitize_columns(data: Dict[str, Any], allowed_columns: set) -> Dict[str, Any]:
    """Filter data to only allowed columns"""
    sanitized = {}
    for key, value in data.items():
        if key in allowed_columns:
            sanitized[key] = value
        else:
            logger.warning(f"Attempted to insert disallowed column: {key}")
    return sanitized

# In the insert function:
med_data = sanitize_columns(med_data, ALLOWED_MEDICATION_COLUMNS)
columns = list(med_data.keys())
quoted_columns = [f'"{col}"' for col in columns]  # All are safe now
```

**Related Changes:**

Create whitelists for all tables:
```python
ALLOWED_INVESTIGATION_COLUMNS = {
    'patientId', 'type', 'name', 'scheduledAt', 'completedAt',
    'priority', 'status', 'prescribedBy', 'performedBy', 'results',
    'notes', 'urgency', 'createdBy', 'createdAt', 'updatedAt'
}

ALLOWED_THERAPY_COLUMNS = {
    'patientId', 'type', 'description', 'startDate', 'endDate',
    'frequency', 'duration', 'status', 'prescribedBy', 'notes',
    'createdBy', 'createdAt', 'updatedAt'
}
```

**Testing:**
- [ ] Try to insert with malicious column name like `'); DROP TABLE medications; --` → should be filtered out
- [ ] Try to insert valid data → should succeed
- [ ] Try to insert data with extra unexpected columns → should be filtered and logged

---

## Part 3: API Validation Baseline (Week 3, Priority P0-P1)

### Phase 3.1: Add Pydantic Validators (Days 1-3)

#### Fix #20: Add Medication Dosage Validation
**Severity:** CRITICAL - PATIENT SAFETY
**File:** `hospital-backend/app/api/v2/atomic_medical.py:28-43`

**Current Code:**
```python
class MedicationRequest(BaseModel):
    name: str
    dosage: str  # ❌ Any string accepted
    frequency: str  # ❌ Any string accepted
    route: str  # ❌ Any string accepted
```

**New Code:**
```python
from pydantic import BaseModel, validator, Field
from typing import Optional, Literal
from enum import Enum
import re

class RouteEnum(str, Enum):
    """Standard medication routes"""
    PO = "PO"  # Oral
    IV = "IV"  # Intravenous
    IM = "IM"  # Intramuscular
    SC = "SC"  # Subcutaneous
    SL = "SL"  # Sublingual
    PR = "PR"  # Rectal
    TOP = "TOP"  # Topical
    INH = "INH"  # Inhalation
    EYE = "EYE"  # Ophthalmic
    EAR = "EAR"  # Otic
    NASAL = "NASAL"  # Nasal

class FrequencyEnum(str, Enum):
    """Standard medication frequencies"""
    QD = "QD"  # Once daily
    BID = "BID"  # Twice daily
    TID = "TID"  # Three times daily
    QID = "QID"  # Four times daily
    Q4H = "Q4H"  # Every 4 hours
    Q6H = "Q6H"  # Every 6 hours
    Q8H = "Q8H"  # Every 8 hours
    Q12H = "Q12H"  # Every 12 hours
    PRN = "PRN"  # As needed
    STAT = "STAT"  # Immediately
    ONCE = "ONCE"  # One time only

class MedicationRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    dosage: str = Field(..., min_length=1, max_length=50)
    frequency: FrequencyEnum
    route: RouteEnum
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    duration: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = 'active'
    prescribedBy: Optional[str] = None

    @validator('dosage')
    def validate_dosage_format(cls, v):
        """
        Validate dosage format: number + unit
        Examples: 500mg, 10ml, 2tablets, 1.5g
        """
        dosage_pattern = r'^\d+(\.\d+)?\s*(mg|g|ml|mcg|μg|units?|tablets?|capsules?|drops?|puffs?|patches?|iu)$'
        if not re.match(dosage_pattern, v, re.IGNORECASE):
            raise ValueError(
                'Invalid dosage format. Examples: 500mg, 10ml, 2tablets, 1.5g'
            )
        return v

    @validator('name')
    def validate_medication_name(cls, v):
        """Validate medication name"""
        # Remove extra whitespace
        v = ' '.join(v.split())

        # Check for suspicious patterns (XSS prevention)
        if re.search(r'[<>{}]', v):
            raise ValueError('Medication name contains invalid characters')

        return v

    @validator('endDate')
    def validate_end_after_start(cls, v, values):
        """Ensure end date is after start date"""
        if v and 'startDate' in values and values['startDate']:
            from datetime import datetime
            try:
                start = datetime.fromisoformat(values['startDate'].replace('Z', '+00:00'))
                end = datetime.fromisoformat(v.replace('Z', '+00:00'))
                if end < start:
                    raise ValueError('End date must be after start date')
            except ValueError as e:
                raise ValueError(f'Invalid date format: {str(e)}')
        return v

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

**Frontend Changes Required:**
- **File:** `hospital-display-app/src/components/modals/MedicationForm.tsx`
- **Change:** Add dropdowns for route and frequency

```typescript
// Add to medication form
<FormGroup>
  <Label>Route *</Label>
  <Select
    value={medication.route}
    onChange={(e) => setMedication({...medication, route: e.target.value})}
  >
    <option value="">Select route...</option>
    <option value="PO">PO - Oral</option>
    <option value="IV">IV - Intravenous</option>
    <option value="IM">IM - Intramuscular</option>
    <option value="SC">SC - Subcutaneous</option>
    <option value="SL">SL - Sublingual</option>
    <option value="PR">PR - Rectal</option>
    <option value="TOP">TOP - Topical</option>
    <option value="INH">INH - Inhalation</option>
  </Select>
</FormGroup>

<FormGroup>
  <Label>Frequency *</Label>
  <Select
    value={medication.frequency}
    onChange={(e) => setMedication({...medication, frequency: e.target.value})}
  >
    <option value="">Select frequency...</option>
    <option value="QD">QD - Once daily</option>
    <option value="BID">BID - Twice daily</option>
    <option value="TID">TID - Three times daily</option>
    <option value="QID">QID - Four times daily</option>
    <option value="Q4H">Q4H - Every 4 hours</option>
    <option value="Q6H">Q6H - Every 6 hours</option>
    <option value="Q8H">Q8H - Every 8 hours</option>
    <option value="PRN">PRN - As needed</option>
  </Select>
</FormGroup>

<FormGroup>
  <Label>Dosage *</Label>
  <Input
    type="text"
    value={medication.dosage}
    onChange={(e) => setMedication({...medication, dosage: e.target.value})}
    placeholder="e.g., 500mg, 10ml, 2tablets"
  />
  <FormText color="muted">
    Format: number + unit (e.g., 500mg, 10ml, 2tablets)
  </FormText>
</FormGroup>
```

**Error Handling:**
- **File:** `hospital-display-app/src/services/MedicationService.ts`
- **Change:** Parse validation errors and show user-friendly messages

```typescript
catch (error: any) {
  if (error.detail && Array.isArray(error.detail)) {
    // Pydantic validation error
    const messages = error.detail.map((err: any) => {
      if (err.loc && err.msg) {
        const field = err.loc[err.loc.length - 1];
        return `${field}: ${err.msg}`;
      }
      return err.msg;
    }).join('\n');
    throw new Error(`Validation failed:\n${messages}`);
  }
  throw error;
}
```

**Testing:**
- [ ] Submit medication with dosage "abc" → should fail with validation error
- [ ] Submit medication with dosage "500mg" → should succeed
- [ ] Submit medication with route "injection" → should fail
- [ ] Submit medication with route "IV" → should succeed
- [ ] Submit medication with end date before start date → should fail

---

#### Fix #21: Add Investigation Validation
**Severity:** HIGH
**File:** `hospital-backend/app/api/v2/atomic_medical.py:45-52`

**New Code:**
```python
class InvestigationType(str, Enum):
    LAB = "lab"
    IMAGING = "imaging"
    CARDIAC = "cardiac"
    RESPIRATORY = "respiratory"
    OTHER = "other"

class PriorityEnum(str, Enum):
    ROUTINE = "routine"
    URGENT = "urgent"
    STAT = "stat"

class InvestigationRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    type: InvestigationType = InvestigationType.LAB
    priority: PriorityEnum = PriorityEnum.ROUTINE
    urgency: PriorityEnum = PriorityEnum.ROUTINE  # Alias for priority
    notes: Optional[str] = Field(None, max_length=1000)
    prescribedBy: Optional[str] = None

    @validator('name')
    def validate_investigation_name(cls, v):
        """Validate investigation name"""
        v = ' '.join(v.split())
        if re.search(r'[<>{}]', v):
            raise ValueError('Investigation name contains invalid characters')
        return v
```

---

#### Fix #22: Add Therapy Validation
**Severity:** HIGH
**File:** `hospital-backend/app/api/v2/atomic_medical.py:54-61`

**New Code:**
```python
class TherapyType(str, Enum):
    PHYSICAL = "physical"
    OCCUPATIONAL = "occupational"
    SPEECH = "speech"
    RESPIRATORY = "respiratory"
    DIALYSIS = "dialysis"
    WOUND_CARE = "wound_care"
    OTHER = "other"

class TherapyRequest(BaseModel):
    type: TherapyType
    description: Optional[str] = Field(None, max_length=1000)
    frequency: Optional[str] = Field(None, max_length=50)
    duration: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=1000)
    prescribedBy: Optional[str] = None

    @validator('description')
    def validate_description(cls, v):
        """Ensure description exists for therapies"""
        if not v or len(v.strip()) < 10:
            raise ValueError('Therapy description must be at least 10 characters')
        return v.strip()
```

---

### Phase 3.2: Add Medical Business Validation (Days 4-5)

#### Fix #23: Validate Medication Before Administration
**Severity:** CRITICAL - PATIENT SAFETY
**File:** `hospital-backend/app/services/medical_action_service.py:333-391`

**Current Code:**
```python
async def _record_medication_administration(self, conn, patient_id, administration_data, performed_by):
    # ❌ No validation before administering
    medication_details = await conn.fetchrow(...)
```

**New Code:**
```python
async def _validate_medication_administration(
    self,
    conn,
    patient_id: str,
    medication_id: int,
    performed_by: str
) -> Dict[str, Any]:
    """
    Validate medication can be administered
    Returns medication details if valid, raises ValueError if not
    """

    # 1. Verify medication exists and is active
    medication = await conn.fetchrow(
        '''
        SELECT m.*, p.status as patient_status
        FROM medications m
        JOIN patients p ON m."patientId" = p.id
        WHERE m.id = $1 AND m."patientId" = $2
        ''',
        medication_id, patient_id
    )

    if not medication:
        raise ValueError(f"Medication {medication_id} not found for patient {patient_id}")

    # 2. Check medication status
    if medication['status'] not in ['active', 'on_hold']:
        raise ValueError(
            f"Cannot administer {medication['status']} medication. "
            f"Status must be 'active' or 'on_hold'"
        )

    # 3. Check patient status
    if medication['patient_status'] == 'discharged':
        raise ValueError("Cannot administer medication to discharged patient")

    if medication['patient_status'] == 'deceased':
        raise ValueError("Cannot administer medication to deceased patient")

    # 4. Check timing (prevent double administration)
    last_admin = await conn.fetchrow(
        '''
        SELECT "performedAt"
        FROM medicationadministrations
        WHERE "medicationId" = $1 AND "patientId" = $2
        AND status = 'completed'
        ORDER BY "performedAt" DESC
        LIMIT 1
        ''',
        medication_id, patient_id
    )

    if last_admin:
        from datetime import datetime, timedelta
        last_time = last_admin['performedAt']
        min_interval = timedelta(hours=4)  # Minimum 4 hours between doses

        if datetime.now() - last_time < min_interval:
            raise ValueError(
                f"Medication was administered {last_time.strftime('%H:%M')}. "
                f"Minimum 4-hour interval required. Try again after "
                f"{(last_time + min_interval).strftime('%H:%M')}"
            )

    # 5. Verify performer has permission
    staff = await conn.fetchrow(
        'SELECT role FROM staff WHERE id = $1',
        performed_by
    )

    if not staff:
        raise ValueError(f"Staff member {performed_by} not found")

    if staff['role'] not in ['nurse', 'doctor', 'pharmacist', 'admin']:
        raise ValueError(
            f"Role '{staff['role']}' does not have permission to administer medications"
        )

    return medication

async def _record_medication_administration(self, conn, patient_id, administration_data, performed_by):
    """Record medication administration after validation"""

    medication_id = int(administration_data.get('medication_id'))

    # VALIDATE BEFORE ADMINISTERING
    medication = await self._validate_medication_administration(
        conn, patient_id, medication_id, performed_by
    )

    # Now safe to administer...
    # (existing administration code)
```

**Frontend Changes:**
- **File:** `hospital-display-app/src/hooks/usePatientMedications.ts:146-185`

**Change:** Handle validation errors gracefully

```typescript
try {
  const response = await fetch(...);
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to administer medication');
  }
  const result = await response.json();

  // ✅ Check result.success explicitly
  if (result.success) {
    alert(`✅ ${med.name} administered successfully!`);
    await refreshMedications();
  } else {
    throw new Error(result.message || 'Administration failed');
  }

} catch (error: any) {
  // ✅ Show specific error message
  alert(`❌ Administration Failed: ${error.message}`);
  console.error('Medication administration error:', error);
}
```

**Testing:**
- [ ] Try to administer discontinued medication → should fail with clear error
- [ ] Try to administer to discharged patient → should fail
- [ ] Try to administer same medication twice within 4 hours → should fail with time remaining
- [ ] Try to administer with lab tech role → should fail with permission error
- [ ] Administer valid medication as nurse → should succeed

---

## Part 4: Backend Error Handling (Week 4, Priority P1)

### Phase 4.1: Add Try-Catch Blocks (Days 1-3)

#### Fix #24: Add Error Handling to Patient Service
**Severity:** HIGH
**File:** `hospital-backend/app/services/patient_service.py:30-150`

**Pattern to Apply Throughout File:**

```python
# BEFORE:
async def get_patient_with_details(self, patient_id: str):
    result = await self.patient_repository.get_patient_full_data(patient_id)
    return result  # ❌ No error handling

# AFTER:
async def get_patient_with_details(self, patient_id: str):
    try:
        result = await self.patient_repository.get_patient_full_data(patient_id)

        if not result:
            self.logger.warning(f"Patient {patient_id} not found")
            return None

        return result

    except asyncpg.PostgresError as e:
        self.logger.error(f"Database error fetching patient {patient_id}: {e}", exc_info=True)
        raise RuntimeError(f"Failed to fetch patient data: {str(e)}")
    except Exception as e:
        self.logger.error(f"Unexpected error fetching patient {patient_id}: {e}", exc_info=True)
        raise
```

**Functions to Update (29 functions):**
1. `get_patient_with_details` (line 30)
2. `_resolve_staff_names` (line 89)
3. `_process_medical_records` (line 131)
4. `add_patient_note` (line 296)
5. `update_note` (line 321)
6. `update_patient` (line 339)
7. ... (continue for all methods)

**Create Custom Exception Classes:**
- **File:** `hospital-backend/app/core/exceptions.py` (NEW FILE)

```python
"""
Custom exception classes for hospital management system
"""

class HospitalBaseException(Exception):
    """Base exception for hospital system"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class PatientNotFoundException(HospitalBaseException):
    """Patient not found in database"""
    pass

class InvalidOperationException(HospitalBaseException):
    """Operation not allowed in current state"""
    pass

class ValidationException(HospitalBaseException):
    """Data validation failed"""
    pass

class PermissionDeniedException(HospitalBaseException):
    """User lacks permission for operation"""
    pass

class DatabaseConstraintException(HospitalBaseException):
    """Database constraint violation"""
    pass
```

**Usage:**
```python
from ..core.exceptions import PatientNotFoundException, DatabaseConstraintException

async def get_patient_with_details(self, patient_id: str):
    try:
        result = await self.patient_repository.get_patient_full_data(patient_id)
        if not result:
            raise PatientNotFoundException(
                f"Patient {patient_id} not found",
                details={"patient_id": patient_id}
            )
        return result

    except asyncpg.ForeignKeyViolationError as e:
        raise DatabaseConstraintException(
            "Referenced record not found",
            details={"constraint": e.constraint_name}
        )
```

---

#### Fix #25: Add Null Checks Throughout Backend
**Severity:** HIGH
**Files:** Multiple service files

**Pattern to Apply:**

```python
# BEFORE:
camel_result['age'] = self.patient_repository.calculate_age(
    camel_result['dateOfBirth']  # ❌ Could be None or empty string
)

# AFTER:
date_of_birth = camel_result.get('dateOfBirth')
if date_of_birth:
    try:
        camel_result['age'] = self.patient_repository.calculate_age(date_of_birth)
    except Exception as e:
        self.logger.warning(f"Failed to calculate age for patient: {e}")
        camel_result['age'] = None  # ✅ Explicit None instead of crashing
else:
    camel_result['age'] = None
```

**Locations to Fix (35+ instances):**
1. `patient_service.py:70` - dateOfBirth check
2. `patient_service.py:137` - prescribedBy check
3. `medical_action_service.py:344` - medication_details null check
4. ... (continue with full list from audit)

---

#### Fix #26: Handle JSON Parsing Errors Properly
**Severity:** HIGH
**File:** `hospital-backend/app/services/patient_service.py:43-52`

**BEFORE:**
```python
if isinstance(field_data, str):
    try:
        field_data = json.loads(field_data)
    except (json.JSONDecodeError, TypeError):
        field_data = []  # ❌ Silently converts error to empty array
```

**AFTER:**
```python
if isinstance(field_data, str):
    try:
        field_data = json.loads(field_data)
    except json.JSONDecodeError as e:
        self.logger.error(
            f"Malformed JSON in {field_name} for patient {patient_id}: {e}",
            extra={
                "patient_id": patient_id,
                "field": field_name,
                "raw_data": field_data[:200]  # Log first 200 chars
            }
        )
        # Alert admin about data corruption
        await self.alert_admin_data_corruption(patient_id, field_name, field_data)
        # Preserve original data, don't convert to empty array
        field_data = field_data  # Keep as string
    except TypeError as e:
        self.logger.error(f"Type error parsing {field_name}: {e}")
        field_data = []
```

**Add Admin Alert Function:**
```python
async def alert_admin_data_corruption(self, patient_id: str, field_name: str, raw_data: str):
    """Alert system administrators about data corruption"""
    from ..core.alerts import alert_system_error

    await alert_system_error(
        title="Data Corruption Detected",
        message=f"Malformed JSON in patient {patient_id} field '{field_name}'",
        source="patient_service",
        metadata={
            "patient_id": patient_id,
            "field": field_name,
            "preview": raw_data[:100]
        }
    )
```

---

### Phase 4.2: Add Connection Pool Monitoring (Days 4-5)

#### Fix #27: Implement Connection Pool Health Checks
**Severity:** HIGH
**File:** `hospital-backend/app/core/database.py:29-75`

**Add Pool Metrics:**
```python
import prometheus_client as prom

# Define metrics
pool_size_gauge = prom.Gauge('db_pool_size', 'Current database pool size')
pool_available_gauge = prom.Gauge('db_pool_available', 'Available connections')
pool_timeout_counter = prom.Counter('db_pool_timeouts', 'Connection pool timeout count')

async def getConnectionPool():
    """Get or create PostgreSQL database connection pool with monitoring"""
    global _connectionPool

    if _connectionPool is None:
        try:
            logger.info(f"Creating connection pool...")
            _connectionPool = await asyncpg.create_pool(
                settings.databaseUrl,
                min_size=2,
                max_size=20,
                command_timeout=30,
                server_settings={
                    'jit': 'off',
                    'application_name': 'hospital_management'
                }
            )
            logger.info("✅ PostgreSQL connection pool created")

            # Start pool monitoring
            asyncio.create_task(monitor_pool_health())

        except Exception as e:
            logger.error(f"❌ Failed to create PostgreSQL pool: {e}")
            # Implement retry logic
            await retry_pool_creation()
            raise

    return _connectionPool

async def monitor_pool_health():
    """Monitor connection pool health and alert if issues"""
    while True:
        try:
            pool = _connectionPool
            if pool:
                size = pool.get_size()
                available = pool.get_idle_size()
                in_use = size - available

                # Update metrics
                pool_size_gauge.set(size)
                pool_available_gauge.set(available)

                # Alert if pool is nearly exhausted
                utilization = in_use / size if size > 0 else 0
                if utilization > 0.9:  # 90% utilized
                    logger.warning(
                        f"⚠️  Connection pool {utilization*100:.1f}% utilized "
                        f"({in_use}/{size} connections in use)"
                    )
                    await alert_admin_pool_exhaustion(utilization, in_use, size)

                # Alert if no connections available
                if available == 0:
                    logger.error("❌ Connection pool exhausted!")
                    await alert_admin_pool_exhausted()

        except Exception as e:
            logger.error(f"Error monitoring pool health: {e}")

        # Check every 30 seconds
        await asyncio.sleep(30)

async def retry_pool_creation():
    """Retry pool creation with exponential backoff"""
    max_retries = 5
    retry_delay = 1  # seconds

    for attempt in range(max_retries):
        try:
            logger.info(f"Retry attempt {attempt + 1}/{max_retries}")
            await asyncio.sleep(retry_delay)

            pool = await asyncpg.create_pool(settings.databaseUrl, ...)
            logger.info(f"✅ Pool created on retry {attempt + 1}")
            return pool

        except Exception as e:
            logger.error(f"Retry {attempt + 1} failed: {e}")
            retry_delay *= 2  # Exponential backoff

    raise RuntimeError("Failed to create database pool after all retries")
```

---

#### Fix #28: Add Deadlock Detection and Retry
**Severity:** CRITICAL
**File:** `hospital-backend/app/services/medical_action_service.py:31-58`

**Add Deadlock Handling:**
```python
import asyncio
from random import random

async def atomic_transaction_with_retry(self, patient_id: str, max_retries: int = 3):
    """Atomic transaction with automatic deadlock retry"""

    for attempt in range(max_retries):
        try:
            async with getDbConnection() as conn:
                async with conn.transaction():
                    # Set statement timeout to prevent infinite locks
                    await conn.execute("SET LOCAL statement_timeout = '10s'")

                    # Lock patient row
                    locked_patient = await conn.fetchrow(
                        'SELECT lock_patient_for_atomic_operation($1)',
                        patient_id
                    )

                    if not locked_patient:
                        raise ValueError(f"Patient {patient_id} not found")

                    yield conn  # Yield connection for use in operation
                    return  # Success, exit retry loop

        except asyncpg.DeadlockDetectedError as e:
            if attempt < max_retries - 1:
                # Exponential backoff with jitter
                delay = (2 ** attempt) + random()
                self.logger.warning(
                    f"Deadlock detected (attempt {attempt + 1}/{max_retries}). "
                    f"Retrying in {delay:.2f}s..."
                )
                await asyncio.sleep(delay)
            else:
                self.logger.error(f"Deadlock persists after {max_retries} attempts")
                raise ValueError("Operation failed due to database contention. Please try again.")

        except asyncpg.QueryCanceledError as e:
            self.logger.error(f"Query timeout: {e}")
            raise ValueError("Operation timed out. Database may be overloaded.")
```

---

## Part 5: Frontend Error Handling (Week 5, Priority P1-P2)

### Phase 5.1: Add Null Safety (Days 1-3)

#### Fix #29: Add Optional Chaining Throughout Frontend
**Severity:** HIGH
**Files:** All hooks and services (14 files)

**Pattern to Apply:**

```typescript
// BEFORE:
setMedications(prev => prev.map(med =>
  med.id === medicationId ? result.medical_record : med
  // ❌ What if result.medical_record is undefined?
));

// AFTER:
setMedications(prev => prev.map(med =>
  med.id === medicationId
    ? (result?.medical_record ?? med)  // ✅ Use nullish coalescing
    : med
));
```

**Locations to Fix:**

1. **File:** `hospital-display-app/src/hooks/usePatientMedications.ts`
   - Line 68-69: `result.medical_record` → `result?.medical_record ?? med`
   - Line 201-204: Add null checks before `time.split(':').map(Number)`

```typescript
// BEFORE:
const nextTime = nextTimes.find(time => {
  const [hours, minutes] = time.split(':').map(Number);
  return (hours * 60 + minutes) > currentTime;
});

// AFTER:
const nextTime = nextTimes.find(time => {
  if (!time || typeof time !== 'string') return false;

  const parts = time.split(':');
  if (parts.length !== 2) return false;

  const hours = parseInt(parts[0], 10);
  const minutes = parseInt(parts[1], 10);

  if (isNaN(hours) || isNaN(minutes)) return false;

  return (hours * 60 + minutes) > currentTime;
});
```

2. **File:** `hospital-display-app/src/services/PatientCaseService.ts:46`

```typescript
// BEFORE:
const staffId = staff.staffId || staff.id || staff.userId || staff.staff_id;

// AFTER:
const staffId = staff?.staffId ?? staff?.id ?? staff?.userId ?? staff?.staff_id ?? 'unknown';
```

3. **Apply throughout all service files:**
   - MedicationService.ts
   - InvestigationService.ts
   - TherapyService.ts
   - PatientNotesService.ts
   - VitalService.ts

---

#### Fix #30: Initialize useState with Default Values
**Severity:** MEDIUM
**Files:** All hooks

```typescript
// BEFORE:
const [medications, setMedications] = useState<medication[]>();  // ❌ undefined initially

// AFTER:
const [medications, setMedications] = useState<medication[]>([]);  // ✅ Empty array default

// BEFORE:
const [patient, setPatient] = useState<patient>();  // ❌ undefined initially

// AFTER:
const [patient, setPatient] = useState<patient | null>(null);  // ✅ Explicit null
```

**Apply to all hooks:**
- usePatientMedications.ts
- usePatientInvestigations.ts
- usePatientTherapies.ts
- usePatientNotes.ts
- usePatientAlerts.ts

---

### Phase 5.2: Add Error States and Loading States (Days 4-5)

#### Fix #31: Implement Proper Error Handling in Services
**Severity:** HIGH
**File:** `hospital-display-app/src/services/MedicationService.ts:22-44`

**BEFORE:**
```typescript
static async getPatientMedications(patientId: string): Promise<medication[]> {
  try {
    const response = await this.fetchFromBackend(`/medications/patient/${patientId}`);
    return this.handleV2Response<medication>(response);
  } catch (error) {
    // Error fetching patient medications - handle silently
    return [];  // ❌ User sees no medications, thinks patient has none
  }
}
```

**AFTER:**
```typescript
static async getPatientMedications(patientId: string): Promise<medication[]> {
  try {
    const response = await this.fetchFromBackend(`/medications/patient/${patientId}`);
    return this.handleV2Response<medication>(response);
  } catch (error: any) {
    console.error(`Failed to fetch medications for patient ${patientId}:`, error);

    // Re-throw with user-friendly message
    throw new Error(
      `Failed to load medications: ${error.message || 'Unknown error'}. ` +
      `Please refresh the page or contact support if the issue persists.`
    );
  }
}
```

**Update Hook to Handle Errors:**
- **File:** `hospital-display-app/src/hooks/usePatientMedications.ts`

```typescript
const [medications, setMedications] = useState<medication[]>([]);
const [loading, setLoading] = useState<boolean>(true);
const [error, setError] = useState<string | null>(null);

useEffect(() => {
  async function loadMedications() {
    if (!patientId) return;

    setLoading(true);
    setError(null);

    try {
      const meds = await MedicationService.getPatientMedications(patientId);
      setMedications(meds ?? []);
    } catch (err: any) {
      setError(err.message);
      console.error('Error loading medications:', err);
    } finally {
      setLoading(false);
    }
  }

  loadMedications();
}, [patientId]);

return { medications, loading, error, refreshMedications };
```

**Update Component to Display Error:**
- **File:** `hospital-display-app/src/components/PatientMedications.tsx`

```typescript
const { medications, loading, error, refreshMedications } = usePatientMedications(patient.id);

if (loading) {
  return <Spinner>Loading medications...</Spinner>;
}

if (error) {
  return (
    <Alert color="danger">
      <AlertHeading>Error Loading Medications</AlertHeading>
      <p>{error}</p>
      <Button onClick={refreshMedications}>Try Again</Button>
    </Alert>
  );
}

if (medications.length === 0) {
  return <p>No medications prescribed</p>;
}

return (
  <MedicationList medications={medications} />
);
```

---

#### Fix #32: Add Network Timeout to Fetch Calls
**Severity:** MEDIUM
**File:** `hospital-display-app/src/services/BaseService.ts:93-123`

**Add Timeout Wrapper:**
```typescript
protected static async fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeout: number = 30000
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error: any) {
    clearTimeout(timeoutId);

    if (error.name === 'AbortError') {
      throw new Error('Request timed out. Please check your network connection.');
    }
    throw error;
  }
}

protected static async fetchFromBackend(
  endpoint: string,
  options: RequestInit = {}
): Promise<any> {
  const url = getApiUrl(endpoint);
  const signedOptions = this.signRequest(options);

  // Use timeout wrapper
  const response = await this.fetchWithTimeout(url, signedOptions);

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  return await response.json();
}
```

---

### Phase 5.3: Implement Error Boundaries (Day 6)

#### Fix #33: Add React Error Boundaries
**Severity:** MEDIUM
**File:** `hospital-display-app/src/components/ErrorBoundary.tsx` (NEW FILE)

**Create Error Boundary Component:**
```typescript
import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Alert, Button, Container } from 'reactstrap';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null
    };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught error:', error, errorInfo);

    this.setState({
      error,
      errorInfo
    });

    // Log to error tracking service (e.g., Sentry)
    // logErrorToService(error, errorInfo);
  }

  private handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <Container className="my-5">
          <Alert color="danger">
            <h4 className="alert-heading">Something went wrong</h4>
            <p>An error occurred while rendering this component.</p>

            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="mt-3">
                <summary>Error Details (Development Only)</summary>
                <pre className="mt-2">
                  {this.state.error.toString()}
                  {this.state.errorInfo?.componentStack}
                </pre>
              </details>
            )}

            <hr />
            <div className="d-flex gap-2">
              <Button color="primary" onClick={this.handleReset}>
                Try Again
              </Button>
              <Button color="secondary" onClick={() => window.location.reload()}>
                Reload Page
              </Button>
            </div>
          </Alert>
        </Container>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
```

**Use Error Boundary:**
- **File:** `hospital-display-app/src/App.tsx` or `hospital-display-app/src/CaseSheetBook.tsx`

```typescript
import ErrorBoundary from './components/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary>
      <CaseSheetBook />
    </ErrorBoundary>
  );
}

// Or wrap individual components:
<ErrorBoundary fallback={<div>Failed to load medications</div>}>
  <PatientMedications patient={patient} />
</ErrorBoundary>
```

---

## Part 6: Configuration Baseline (Week 6, Priority P2)

### Phase 6.1: Environment Variables (Days 1-2)

#### Fix #34: Create Complete .env.example
**Severity:** MEDIUM
**File:** `hospital-backend/.env.example`

**Complete Example File:**
```bash
# Environment
ENVIRONMENT=development  # Options: development, staging, production

# Database Configuration
DATABASE_URL=postgresql://hospital_user:YOUR_SECURE_PASSWORD@localhost:5432/hospitaldb
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=hospitaldb
DATABASE_USER=hospital_user
DATABASE_PASSWORD=YOUR_SECURE_PASSWORD_MIN_16_CHARS

# TimescaleDB Configuration
TIMESCALEDB_URL=postgresql://hospital_user:YOUR_SECURE_PASSWORD@localhost:5433/hospitaltimescale
TIMESCALEDB_HOST=localhost
TIMESCALEDB_PORT=5433
TIMESCALEDB_NAME=hospitaltimescale
TIMESCALEDB_USER=hospital_user
TIMESCALEDB_PASSWORD=YOUR_SECURE_PASSWORD_MIN_16_CHARS

# Security
SECRET_KEY=GENERATE_RANDOM_STRING_MINIMUM_32_CHARACTERS_LONG
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS (comma-separated list)
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Logging
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# MQTT (ESP32 Communication)
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_USERNAME=hospital_mqtt
MQTT_PASSWORD=YOUR_MQTT_PASSWORD

# SMTP (Email Alerts)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
SMTP_FROM_EMAIL=noreply@hospital.com

# Alert Configuration
ENABLE_EMAIL_ALERTS=true
ENABLE_SMS_ALERTS=false
ALERT_WEBHOOK_URL=

# Monitoring
ENABLE_PROMETHEUS_METRICS=true
PROMETHEUS_PORT=9090
```

---

#### Fix #35: Add Environment Variable Validation
**Severity:** HIGH
**File:** `hospital-backend/app/core/config.py`

**Enhanced Config with Validation:**
```python
from pydantic_settings import BaseSettings
from pydantic import validator, Field
from typing import List
import os

class Settings(BaseSettings):
    """Application settings with validation"""

    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")

    @validator('environment')
    def validate_environment(cls, v):
        allowed = ['development', 'dev', 'local', 'staging', 'production', 'prod']
        if v.lower() not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of: {', '.join(allowed)}")
        return v.lower()

    # Database
    databaseUrl: str = Field(..., env="DATABASE_URL")
    databasePassword: str = Field(..., env="DATABASE_PASSWORD")

    @validator('databasePassword')
    def validate_db_password(cls, v, values):
        if values.get('environment') in ['production', 'prod']:
            if len(v) < 16:
                raise ValueError("DATABASE_PASSWORD must be at least 16 characters in production")
            if v in ['password', '12345678', 'admin123', 'hospital123']:
                raise ValueError("DATABASE_PASSWORD is too weak for production")
        return v

    # Security
    secretKey: str = Field(..., env="SECRET_KEY")

    @validator('secretKey')
    def validate_secret_key(cls, v, values):
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")

        if values.get('environment') in ['production', 'prod']:
            # In production, require high entropy
            if v.count('a') > len(v) * 0.3:  # Too many repeated characters
                raise ValueError("SECRET_KEY has low entropy (too many repeated characters)")

        return v

    # CORS
    backendCorsOrigins: List[str] = Field(
        default=["http://localhost:3000"],
        env="BACKEND_CORS_ORIGINS"
    )

    @validator('backendCorsOrigins', pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v

    @validator('backendCorsOrigins')
    def validate_cors_origins(cls, v, values):
        if values.get('environment') in ['production', 'prod']:
            # Warn if localhost in production CORS
            for origin in v:
                if 'localhost' in origin or '127.0.0.1' in origin:
                    raise ValueError(
                        f"CORS origin '{origin}' contains localhost. "
                        "This is likely a misconfiguration in production."
                    )
        return v

    # Logging
    logLevel: str = Field(default="INFO", env="LOG_LEVEL")

    @validator('logLevel')
    def validate_log_level(cls, v):
        allowed = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        v = v.upper()
        if v not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(allowed)}")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False

# Validate on import
settings = Settings()
```

---

### Phase 6.2: CORS Configuration (Day 3)

#### Fix #36: Configure CORS Properly
**Severity:** MEDIUM
**File:** `hospital-backend/main.py`

**Add CORS Middleware:**
```python
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(title="Hospital Management System")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backendCorsOrigins,  # From environment
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],  # For file downloads
    max_age=600,  # Cache preflight requests for 10 minutes
)
```

---

### Phase 6.3: Logging Configuration (Day 4)

#### Fix #37: Remove DEBUG Logs with PII
**Severity:** MEDIUM
**File:** Multiple backend files

**Create Secure Logger:**
- **File:** `hospital-backend/app/core/secure_logger.py` (NEW FILE)

```python
"""
Secure logging utility that prevents PII leakage
"""
import logging
import re
from typing import Any, Dict

class SecureLogger:
    """Logger wrapper that sanitizes sensitive data"""

    # Patterns to redact
    PII_PATTERNS = [
        (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]'),  # SSN
        (r'\b\d{10,}\b', '[PHONE]'),  # Phone numbers
        (r'\b[\w\.-]+@[\w\.-]+\.\w+\b', '[EMAIL]'),  # Emails
        (r'\b\d{16}\b', '[CARD]'),  # Credit cards
    ]

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def sanitize(self, message: str) -> str:
        """Remove PII from log message"""
        for pattern, replacement in self.PII_PATTERNS:
            message = re.sub(pattern, replacement, message)
        return message

    def info(self, message: str, **kwargs):
        self.logger.info(self.sanitize(message), **kwargs)

    def warning(self, message: str, **kwargs):
        self.logger.warning(self.sanitize(message), **kwargs)

    def error(self, message: str, **kwargs):
        self.logger.error(self.sanitize(message), **kwargs)

    def debug(self, message: str, **kwargs):
        # Only log debug in development
        if settings.environment != 'production':
            self.logger.debug(self.sanitize(message), **kwargs)
```

**Usage:**
```python
# BEFORE:
import logging
logger = logging.getLogger(__name__)
logger.debug(f"Creating patient: {patient_data}")  # ❌ Logs full patient data

# AFTER:
from app.core.secure_logger import SecureLogger
logger = SecureLogger(__name__)
logger.debug(f"Creating patient with ID: {patient_data.get('id')}")  # ✅ Only logs ID
```

---

## Cross-Reference Matrix

| Fix # | Primary File | Related Changes | Priority | Week |
|-------|-------------|-----------------|----------|------|
| #1 (FK: medications→patients) | migrations/001_add_fk_medications.sql | medication_service.py, MedicationService.ts | P1 | 1 |
| #2-9 (All FKs) | migrations/*.sql | All services, All frontend services | P1 | 1 |
| #10-13 (CHECK/UNIQUE) | migrations/*.sql | Service error handling | P2 | 1-2 |
| #14 (Soft delete) | migrations/014_soft_delete.sql | base_repository.py, all services | P0 | 2 |
| #15 (Remove secrets) | config.py, docker-compose.yml | .env, startup_validation.py | P0 | 2 |
| #17-18 (JWT/RBAC) | middleware/auth.py, middleware/rbac.py | All API endpoints | P0 | 2 |
| #19 (SQL injection) | medical_action_service.py | All dynamic queries | P0 | 2 |
| #20-22 (Validation) | atomic_medical.py | MedicationForm.tsx, frontend services | P0 | 3 |
| #23 (Med validation) | medical_action_service.py | usePatientMedications.ts | P0 | 3 |
| #24-26 (Error handling) | patient_service.py, exceptions.py | All services | P1 | 4 |
| #27-28 (Pool monitoring) | database.py | prometheus setup | P1 | 4 |
| #29-30 (Null safety) | All hooks | All services | P1 | 5 |
| #31-32 (Frontend errors) | BaseService.ts, all services | All components | P1 | 5 |
| #33 (Error boundary) | ErrorBoundary.tsx | App.tsx, CaseSheetBook.tsx | P2 | 5 |
| #34-37 (Config) | .env.example, config.py, main.py | secure_logger.py | P2 | 6 |

---

## Testing Strategy

### Unit Tests Required (147 minimum)

**Backend Unit Tests (85 tests):**
1. Foreign key violation handling (9 tests - one per FK)
2. CHECK constraint validation (15 tests)
3. Soft delete operations (10 tests)
4. Pydantic validation (15 tests)
5. Medical business validation (12 tests)
6. Error handling edge cases (24 tests)

**Frontend Unit Tests (45 tests):**
1. Null safety with optional chaining (20 tests)
2. API error handling (15 tests)
3. Loading states (10 tests)

**Integration Tests (30 tests):**
1. Full medication lifecycle (5 tests)
2. Authentication flow (5 tests)
3. Atomic operations with rollback (10 tests)
4. Database constraints end-to-end (10 tests)

### Manual Test Scenarios (20 scenarios)

1. Try to create medication without valid token → 401
2. Try to prescribe as nurse → 403
3. Try to administer discontinued medication → validation error
4. Delete patient with medications → cascade delete
5. Submit invalid dosage format → validation error
6. Network timeout → error message displayed
7. ... (continue with full list)

---

## Success Criteria

After baseline implementation complete:

### Database Layer ✅
- [ ] All foreign key constraints in place (9 constraints)
- [ ] All CHECK constraints in place (15 constraints)
- [ ] All UNIQUE constraints in place (5 constraints)
- [ ] Soft delete implemented on all tables
- [ ] Connection pool monitoring active
- [ ] Deadlock retry logic working

### Security Layer ✅
- [ ] No hardcoded secrets in code
- [ ] Environment validation on startup
- [ ] JWT authentication required on all endpoints
- [ ] RBAC enforced for all operations
- [ ] SQL injection vulnerabilities eliminated
- [ ] CORS properly configured

### Validation Layer ✅
- [ ] All API endpoints have Pydantic models
- [ ] Medication dosage validation working
- [ ] Route and frequency enums enforced
- [ ] Medical business rules validated before operations
- [ ] All user input sanitized

### Error Handling ✅
- [ ] All backend services have try-catch blocks
- [ ] Specific exception types caught
- [ ] Null checks throughout backend
- [ ] Frontend has error states
- [ ] Frontend has loading states
- [ ] Error boundary catches React errors
- [ ] Network timeouts handled

### Configuration ✅
- [ ] Complete .env.example provided
- [ ] Environment variable validation working
- [ ] Production deployment blocks weak passwords
- [ ] Logging sanitizes PII
- [ ] CORS restricted to allowed origins

### Compliance ✅
- [ ] Audit trail preserved (soft delete)
- [ ] Staff accountability enforced (no "SYSTEM" default)
- [ ] Medical record integrity guaranteed (foreign keys)
- [ ] Patient safety validated (medication checks)

---

## Timeline Summary

**Week 1-2:** Database Foundation (P0-P1)
- Days 1-3: Foreign key constraints
- Days 4-5: CHECK constraints
- Day 6: UNIQUE constraints
- Days 7-8: Soft delete implementation

**Week 2:** Security Baseline (P0)
- Days 1-2: Remove hardcoded secrets
- Days 3-5: JWT authentication + RBAC
- Day 6: SQL injection fixes

**Week 3:** API Validation (P0-P1)
- Days 1-3: Pydantic validators
- Days 4-5: Medical business validation

**Week 4:** Backend Error Handling (P1)
- Days 1-3: Try-catch blocks + custom exceptions
- Days 4-5: Connection pool monitoring + deadlock handling

**Week 5:** Frontend Error Handling (P1-P2)
- Days 1-3: Null safety (optional chaining)
- Days 4-5: Error states + loading states
- Day 6: Error boundaries

**Week 6:** Configuration (P2)
- Days 1-2: Environment variables
- Day 3: CORS configuration
- Day 4: Secure logging

**Total Duration:** 6 weeks for full baseline establishment

---

## Risk Mitigation

### High-Risk Changes
1. **Foreign key constraints** - Could break existing data
   - **Mitigation:** Run data validation queries first, fix orphaned records before adding constraints

2. **Soft delete migration** - Changes delete behavior
   - **Mitigation:** Test thoroughly in staging, add rollback SQL scripts

3. **JWT authentication** - Could lock out users
   - **Mitigation:** Implement gradually, add bypass for admin, test token generation

### Rollback Plan
Each migration includes rollback SQL:
```sql
-- Migration: 001_add_foreign_keys_medications.sql

-- ROLLBACK:
ALTER TABLE medications DROP CONSTRAINT IF EXISTS fk_medications_patient;
ALTER TABLE medications DROP CONSTRAINT IF EXISTS fk_medications_prescriber;
```

---

## Documentation Requirements

Create/update these documents:
1. **DEPLOYMENT_GUIDE.md** - Environment setup, .env configuration
2. **SECURITY_GUIDE.md** - Authentication, RBAC, password policies
3. **API_VALIDATION_GUIDE.md** - Pydantic models, validation rules
4. **ERROR_HANDLING_GUIDE.md** - Exception types, error codes, user messages
5. **DATABASE_CONSTRAINTS_GUIDE.md** - All constraints, cascade rules, soft delete

---

**Plan Created:** 2025-10-05
**Estimated Completion:** 6 weeks from start
**Status:** Ready for implementation after user approval
**Dependencies:** None - can start immediately
