# Detailed Execution Plan - Baseline Foundation
**Date:** 2025-10-05
**Duration:** 14 days (2 weeks)
**Goal:** Establish solid foundation with database integrity, security, validation, and error handling
**Based on:** BASELINE_FIX_IMPLEMENTATION_PLAN.md (147 fixes)

---

## Overview

This plan breaks down the 147 baseline fixes into a **14-day execution schedule** with:
- ✅ Daily task lists with exact files and line numbers
- ✅ Step-by-step instructions for each change
- ✅ Dependencies clearly marked
- ✅ Testing checkpoints after each change
- ✅ Rollback procedures if issues occur

---

## Week 1: Database & Backend Foundation

### **DAY 1: Database Foreign Keys (Part 1)**

#### Morning Session (9 AM - 12 PM)
**Goal:** Add foreign keys to core medical tables

**Step 1.1: Create migration infrastructure**
```bash
# Terminal commands
cd hospital-backend
mkdir -p migrations
touch migrations/001_add_foreign_keys_core_tables.sql
```

**Step 1.2: Write migration for medications table**
- **File:** `hospital-backend/migrations/001_add_foreign_keys_core_tables.sql`
- **Add:**
```sql
-- Migration: Add Foreign Keys to Core Tables
-- Date: 2025-10-05
-- Description: Establish referential integrity for medical records

BEGIN;

-- 1. medications table foreign keys
ALTER TABLE medications
ADD CONSTRAINT fk_medications_patient
FOREIGN KEY ("patientId") REFERENCES patients(id)
ON DELETE CASCADE;

ALTER TABLE medications
ADD CONSTRAINT fk_medications_prescriber
FOREIGN KEY ("prescribedBy") REFERENCES staff(id)
ON DELETE RESTRICT;

ALTER TABLE medications
ADD CONSTRAINT fk_medications_creator
FOREIGN KEY ("createdBy") REFERENCES staff(id)
ON DELETE SET NULL;

COMMIT;
```

**Step 1.3: Test migration locally**
```bash
# Connect to local database
psql -U postgres -d hospital_management

# Run migration
\i migrations/001_add_foreign_keys_core_tables.sql

# Verify constraints
\d medications
# Should show 3 new foreign key constraints
```

**Step 1.4: Rollback script**
- **File:** `hospital-backend/migrations/001_rollback.sql`
```sql
BEGIN;
ALTER TABLE medications DROP CONSTRAINT IF EXISTS fk_medications_patient;
ALTER TABLE medications DROP CONSTRAINT IF EXISTS fk_medications_prescriber;
ALTER TABLE medications DROP CONSTRAINT IF EXISTS fk_medications_creator;
COMMIT;
```

#### Afternoon Session (1 PM - 5 PM)
**Goal:** Update backend to handle FK violations

**Step 1.5: Update medication service exception handling**
- **File:** `hospital-backend/app/services/medication_service.py`
- **Line:** 40-70
- **Find:**
```python
async def add_medication(self, patient_id: str, medication_data: Dict[str, Any], user_id: str):
    return await self.medication_repository.create_medication(patient_id, medication_data)
```
- **Replace with:**
```python
async def add_medication(self, patient_id: str, medication_data: Dict[str, Any], user_id: str):
    try:
        return await self.medication_repository.create_medication(patient_id, medication_data)
    except asyncpg.ForeignKeyViolationError as e:
        constraint = str(e).split('DETAIL:')[0]
        if 'fk_medications_patient' in constraint:
            raise ValueError(f"Patient {patient_id} not found. Cannot create medication for non-existent patient.")
        elif 'fk_medications_prescriber' in constraint:
            prescriber = medication_data.get('prescribedBy')
            raise ValueError(f"Prescriber {prescriber} not found in staff directory. Please verify staff ID.")
        elif 'fk_medications_creator' in constraint:
            raise ValueError(f"Creator user {user_id} not found in system.")
        raise
    except asyncpg.UniqueViolationError as e:
        raise ValueError("Duplicate medication record.")
    except Exception as e:
        self.logger.error(f"Error adding medication: {e}", exc_info=True)
        raise RuntimeError("Failed to create medication due to database error.")
```

**Step 1.6: Test backend changes**
```bash
# Start backend
cd hospital-backend
source venv/bin/activate  # or venv/Scripts/activate on Windows
python main.py

# In another terminal, test with curl
curl -X POST http://localhost:8001/api/v2/patients/INVALID_ID/medications \
  -H "Content-Type: application/json" \
  -d '{"name":"Aspirin","dosage":"500mg","frequency":"BID","route":"PO","prescribedBy":"DOC001"}'

# Expected: Error with "Patient INVALID_ID not found"
```

**Step 1.7: Update frontend error handling**
- **File:** `hospital-display-app/src/hooks/usePatientMedications.ts`
- **Line:** 60-80
- **Find:**
```typescript
const handleAddMedication = async (medData: MedicationData) => {
  try {
    await MedicationService.addMedication(patientId, medData);
    // refresh list
  } catch (error) {
    console.error(error);
    alert("Failed to add medication");
  }
};
```
- **Replace with:**
```typescript
const handleAddMedication = async (medData: MedicationData) => {
  try {
    await MedicationService.addMedication(patientId, medData);
    // refresh list
    await fetchMedications();
    return { success: true };
  } catch (error: any) {
    console.error('Add medication error:', error);

    // Parse specific errors from backend
    const message = error?.response?.data?.message || error?.message || 'Unknown error';

    if (message.includes('Patient') && message.includes('not found')) {
      alert('❌ Error: Patient not found. Please refresh the page.');
    } else if (message.includes('Prescriber') && message.includes('not found')) {
      alert('❌ Error: Prescriber not found in staff directory. Please verify the staff ID.');
    } else {
      alert(`❌ Failed to add medication: ${message}`);
    }

    return { success: false, error: message };
  }
};
```

**Day 1 Testing Checklist:**
- [ ] Migration runs successfully
- [ ] Cannot create medication for invalid patient ID
- [ ] Cannot create medication with invalid prescriber ID
- [ ] Error messages are user-friendly
- [ ] Rollback script works
- [ ] Can create medication with valid IDs

---

### **DAY 2: Database Foreign Keys (Part 2)**

#### Morning Session (9 AM - 12 PM)
**Goal:** Add foreign keys to investigations, therapy, casesheetentries tables

**Step 2.1: Create migration**
- **File:** `hospital-backend/migrations/002_add_foreign_keys_medical_records.sql`
```sql
BEGIN;

-- investigations table
ALTER TABLE investigations
ADD CONSTRAINT fk_investigations_patient
FOREIGN KEY ("patientId") REFERENCES patients(id) ON DELETE CASCADE;

ALTER TABLE investigations
ADD CONSTRAINT fk_investigations_prescriber
FOREIGN KEY ("prescribedBy") REFERENCES staff(id) ON DELETE SET NULL;

ALTER TABLE investigations
ADD CONSTRAINT fk_investigations_performer
FOREIGN KEY ("performedBy") REFERENCES staff(id) ON DELETE SET NULL;

-- therapy table
ALTER TABLE therapy
ADD CONSTRAINT fk_therapy_patient
FOREIGN KEY ("patientId") REFERENCES patients(id) ON DELETE CASCADE;

ALTER TABLE therapy
ADD CONSTRAINT fk_therapy_prescriber
FOREIGN KEY ("prescribedBy") REFERENCES staff(id) ON DELETE SET NULL;

-- casesheetentries table
ALTER TABLE casesheetentries
ADD CONSTRAINT fk_casesheetentries_patient
FOREIGN KEY ("patientId") REFERENCES patients(id) ON DELETE CASCADE;

ALTER TABLE casesheetentries
ADD CONSTRAINT fk_casesheetentries_performer
FOREIGN KEY ("performedBy") REFERENCES staff(id) ON DELETE SET NULL;

COMMIT;
```

**Step 2.2: Apply migration**
```bash
psql -U postgres -d hospital_management -f migrations/002_add_foreign_keys_medical_records.sql
```

#### Afternoon Session (1 PM - 5 PM)
**Goal:** Update investigation and therapy services

**Step 2.3: Update investigation_service.py**
- **File:** `hospital-backend/app/services/investigation_service.py`
- Add FK violation handling similar to medication_service.py

**Step 2.4: Update therapy_service.py**
- **File:** `hospital-backend/app/services/therapy_service.py`
- Add FK violation handling

**Step 2.5: Frontend updates**
- Update investigation hooks with error handling
- Update therapy hooks with error handling

**Day 2 Testing Checklist:**
- [ ] All migrations applied successfully
- [ ] Cannot create investigation for invalid patient
- [ ] Cannot create therapy for invalid patient
- [ ] Error messages clear and helpful
- [ ] All frontend forms handle errors

---

### **DAY 3: Database CHECK Constraints**

#### Morning Session (9 AM - 12 PM)
**Goal:** Add CHECK constraints for data validation

**Step 3.1: Create migration**
- **File:** `hospital-backend/migrations/003_add_check_constraints.sql`
```sql
BEGIN;

-- Patient status must be valid
ALTER TABLE patients
ADD CONSTRAINT chk_patient_status
CHECK (status IN ('active', 'discharged', 'transferred', 'deceased'));

-- Medication status must be valid
ALTER TABLE medications
ADD CONSTRAINT chk_medication_status
CHECK (status IN ('active', 'discontinued', 'completed', 'on_hold'));

-- Discharge date must be after admission date
ALTER TABLE patients
ADD CONSTRAINT chk_discharge_after_admission
CHECK ("dischargeDate" IS NULL OR "dischargeDate" >= "admissionDate");

-- Updated timestamp must be >= created timestamp
ALTER TABLE patients
ADD CONSTRAINT chk_timestamps_patients
CHECK ("updatedAt" >= "createdAt");

ALTER TABLE medications
ADD CONSTRAINT chk_timestamps_medications
CHECK ("updatedAt" >= "createdAt");

-- Medication end date must be after start date
ALTER TABLE medications
ADD CONSTRAINT chk_medication_dates
CHECK ("endDate" IS NULL OR "endDate" >= "startDate");

-- Investigation status must be valid
ALTER TABLE investigations
ADD CONSTRAINT chk_investigation_status
CHECK (status IN ('ordered', 'scheduled', 'in_progress', 'completed', 'cancelled'));

-- Therapy status must be valid
ALTER TABLE therapy
ADD CONSTRAINT chk_therapy_status
CHECK (status IN ('active', 'completed', 'discontinued'));

COMMIT;
```

**Step 3.2: Apply migration**
```bash
psql -U postgres -d hospital_management -f migrations/003_add_check_constraints.sql
```

#### Afternoon Session (1 PM - 5 PM)
**Goal:** Update backend to handle CHECK constraint violations

**Step 3.3: Update patient_service.py**
- **File:** `hospital-backend/app/services/patient_service.py`
- **Add to discharge_patient method:**
```python
async def discharge_patient(self, patient_id: str, discharge_data: Dict[str, Any], user_id: str):
    try:
        # Validate discharge date
        discharge_date = discharge_data.get('dischargeDate')
        patient = await self.patient_repository.get_by_id(patient_id)

        if discharge_date and patient.get('admissionDate'):
            if discharge_date < patient['admissionDate']:
                raise ValueError("Discharge date cannot be before admission date")

        # Proceed with discharge
        return await self.patient_repository.discharge_patient(patient_id, discharge_data, user_id)

    except asyncpg.CheckViolationError as e:
        if 'chk_discharge_after_admission' in str(e):
            raise ValueError("Discharge date must be after admission date")
        elif 'chk_patient_status' in str(e):
            raise ValueError("Invalid patient status")
        raise
```

**Day 3 Testing Checklist:**
- [ ] Cannot set invalid patient status
- [ ] Cannot discharge before admission
- [ ] Cannot set medication end date before start date
- [ ] Timestamps validated correctly
- [ ] All status fields validated

---

### **DAY 4: Security - Remove Hardcoded Secrets**

#### Morning Session (9 AM - 12 PM)
**Goal:** Remove all hardcoded secrets and use environment variables

**Step 4.1: Create .env.example**
- **File:** `hospital-backend/.env.example`
```env
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/hospital_management
TIMESCALEDB_URL=postgresql://user:password@localhost:5432/hospital_timeseries

# Security
SECRET_KEY=your-secret-key-here-minimum-32-characters
JWT_SECRET=your-jwt-secret-here-minimum-32-characters
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# SMTP Configuration (for alerts)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@hospital.com

# Application
DEBUG=false
LOG_LEVEL=INFO
ENVIRONMENT=development
```

**Step 4.2: Update config.py to require environment variables**
- **File:** `hospital-backend/app/core/config.py`
- **Find:**
```python
SECRET_KEY = os.getenv("SECRET_KEY", "HSM-2024-SecureKey-ChangeInProd-V1.0")
```
- **Replace with:**
```python
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required and not set")
if len(SECRET_KEY) < 32:
    raise ValueError("SECRET_KEY must be at least 32 characters long")
```

**Step 4.3: Remove hardcoded passwords from seed data**
- **File:** `hospital-backend/app/core/config.py` or seed scripts
- **Find:** `hospital123` and replace with strong password generation
```python
import secrets
default_password = secrets.token_urlsafe(16)  # Generate strong random password
# Log the password ONCE at startup for admin to change
logger.warning(f"DEFAULT ADMIN PASSWORD: {default_password} - CHANGE IMMEDIATELY")
```

#### Afternoon Session (1 PM - 5 PM)
**Goal:** Frontend secret management

**Step 4.4: Update frontend config**
- **File:** `hospital-display-app/.env.example`
```env
REACT_APP_API_URL=http://localhost:8001
REACT_APP_WS_URL=ws://localhost:8001
REACT_APP_ENVIRONMENT=development
```

**Step 4.5: Remove hardcoded API URLs**
- **File:** `hospital-display-app/src/config/apiConfig.ts`
- **Find:** Hardcoded `http://localhost:8001`
- **Replace with:**
```typescript
export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8001';
export const WS_BASE_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8001';
export const ENVIRONMENT = process.env.REACT_APP_ENVIRONMENT || 'development';

// Validate in production
if (ENVIRONMENT === 'production') {
  if (!process.env.REACT_APP_API_URL) {
    throw new Error('REACT_APP_API_URL must be set in production');
  }
}
```

**Day 4 Testing Checklist:**
- [ ] Backend fails to start without SECRET_KEY
- [ ] Backend fails to start with short SECRET_KEY
- [ ] No hardcoded passwords in code
- [ ] .env.example files created
- [ ] Frontend uses environment variables

---

### **DAY 5: Authentication & Authorization**

#### Morning Session (9 AM - 12 PM)
**Goal:** Implement proper JWT authentication

**Step 5.1: Create JWT utilities**
- **File:** `hospital-backend/app/core/auth.py` (new file)
```python
from datetime import datetime, timedelta
from typing import Optional
import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import settings

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

def require_role(allowed_roles: list):
    def role_checker(token_data: dict = Security(verify_token)):
        user_role = token_data.get("role")
        if user_role not in allowed_roles:
            raise HTTPException(status_code=403, detail=f"Insufficient permissions. Required: {allowed_roles}")
        return token_data
    return role_checker
```

**Step 5.2: Update medication endpoints to require auth**
- **File:** `hospital-backend/app/api/v2/medications.py`
- **Find:**
```python
@router.post("/patients/{patient_id}/medications")
async def add_medication(patient_id: str, medication: MedicationRequest, performed_by: str = "SYSTEM"):
```
- **Replace with:**
```python
from app.core.auth import verify_token, require_role

@router.post("/patients/{patient_id}/medications")
async def add_medication(
    patient_id: str,
    medication: MedicationRequest,
    token_data: dict = Security(require_role(["doctor", "physician"]))  # Only doctors can prescribe
):
    performed_by = token_data.get("sub")  # Get user ID from token
    user_role = token_data.get("role")
```

#### Afternoon Session (1 PM - 5 PM)
**Goal:** Frontend authentication integration

**Step 5.3: Create auth service**
- **File:** `hospital-display-app/src/services/AuthService.ts` (new file)
```typescript
export class AuthService {
  static async login(email: string, password: string): Promise<{token: string, user: any}> {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    if (!response.ok) {
      throw new Error('Login failed');
    }

    const data = await response.json();
    // Store token securely
    localStorage.setItem('auth_token', data.token);
    localStorage.setItem('user', JSON.stringify(data.user));
    return data;
  }

  static getToken(): string | null {
    return localStorage.getItem('auth_token');
  }

  static logout(): void {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
  }
}
```

**Step 5.4: Update BaseService to include auth token**
- **File:** `hospital-display-app/src/services/BaseService.ts`
- **Find:**
```typescript
protected static async fetchFromBackend(endpoint: string, options: RequestInit = {}) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
```
- **Replace with:**
```typescript
protected static async fetchFromBackend(endpoint: string, options: RequestInit = {}) {
  const token = AuthService.getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` }),
    ...options.headers
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers
  });

  if (response.status === 401) {
    // Token expired or invalid - redirect to login
    AuthService.logout();
    window.location.href = '/login';
    throw new Error('Authentication required');
  }
```

**Day 5 Testing Checklist:**
- [ ] Cannot add medication without token
- [ ] Nurses cannot prescribe (403 error)
- [ ] Doctors can prescribe
- [ ] Token expiration handled
- [ ] Login/logout works

---

### **DAY 6: Input Validation - Pydantic Models**

#### Full Day (9 AM - 5 PM)
**Goal:** Add comprehensive validation to all API endpoints

**Step 6.1: Create medication validation**
- **File:** `hospital-backend/app/api/v2/atomic_medical.py`
- **Find:**
```python
class MedicationRequest(BaseModel):
    name: str
    dosage: str
    frequency: str
    route: str
```
- **Replace with:**
```python
from enum import Enum
from pydantic import validator
import re

class RouteEnum(str, Enum):
    PO = "PO"  # Oral
    IV = "IV"  # Intravenous
    IM = "IM"  # Intramuscular
    SC = "SC"  # Subcutaneous
    PR = "PR"  # Rectal
    SL = "SL"  # Sublingual
    TOPICAL = "TOPICAL"
    INHALATION = "INHALATION"

class FrequencyEnum(str, Enum):
    QD = "QD"    # Once daily
    BID = "BID"  # Twice daily
    TID = "TID"  # Three times daily
    QID = "QID"  # Four times daily
    Q4H = "Q4H"  # Every 4 hours
    Q6H = "Q6H"  # Every 6 hours
    Q8H = "Q8H"  # Every 8 hours
    Q12H = "Q12H" # Every 12 hours
    PRN = "PRN"  # As needed

class MedicationRequest(BaseModel):
    name: str
    dosage: str
    frequency: FrequencyEnum
    route: RouteEnum
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    duration: Optional[str] = None

    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Medication name must be at least 2 characters')
        if len(v) > 200:
            raise ValueError('Medication name too long (max 200 characters)')
        return v.strip()

    @validator('dosage')
    def validate_dosage(cls, v):
        # Pattern: number (with optional decimal) + space + unit
        pattern = r'^\d+(\.\d+)?\s*(mg|ml|g|mcg|units?|tablets?|capsules?|drops?|puffs?)$'
        if not re.match(pattern, v, re.IGNORECASE):
            raise ValueError(
                'Invalid dosage format. Use: number + unit '
                '(e.g., "500mg", "10ml", "2tablets", "1unit")'
            )
        return v.lower()

    @validator('endDate')
    def validate_end_date(cls, v, values):
        if v and values.get('startDate'):
            from datetime import datetime
            start = datetime.fromisoformat(values['startDate'])
            end = datetime.fromisoformat(v)
            if end < start:
                raise ValueError('End date cannot be before start date')
        return v
```

**Step 6.2: Create investigation validation**
Similar pattern for investigations

**Step 6.3: Create therapy validation**
Similar pattern for therapy

**Step 6.4: Update frontend to use enums**
- **File:** `hospital-display-app/src/components/modals/MedicationModal.tsx`
```typescript
const ROUTE_OPTIONS = [
  { value: 'PO', label: 'PO (Oral)' },
  { value: 'IV', label: 'IV (Intravenous)' },
  { value: 'IM', label: 'IM (Intramuscular)' },
  { value: 'SC', label: 'SC (Subcutaneous)' },
  // ... etc
];

const FREQUENCY_OPTIONS = [
  { value: 'QD', label: 'QD (Once Daily)' },
  { value: 'BID', label: 'BID (Twice Daily)' },
  // ... etc
];

// In form:
<select name="route" required>
  {ROUTE_OPTIONS.map(opt => (
    <option key={opt.value} value={opt.value}>{opt.label}</option>
  ))}
</select>
```

**Day 6 Testing Checklist:**
- [ ] Invalid dosage format rejected
- [ ] Invalid route rejected
- [ ] Invalid frequency rejected
- [ ] End date before start date rejected
- [ ] Frontend dropdowns match backend enums

---

### **DAY 7: Error Handling - Backend Services**

#### Full Day (9 AM - 5 PM)
**Goal:** Add comprehensive error handling to all services

**Pattern to apply to ALL service files:**

```python
async def some_service_method(self, ...):
    try:
        # Existing logic
        result = await self.repository.some_operation(...)
        return result

    except asyncpg.ForeignKeyViolationError as e:
        # Handle FK violations - log and raise meaningful error
        self.logger.error(f"Foreign key violation: {e}")
        constraint_name = self._extract_constraint_name(e)
        raise ValueError(f"Referenced record not found: {constraint_name}")

    except asyncpg.UniqueViolationError as e:
        # Handle unique violations
        self.logger.error(f"Unique constraint violation: {e}")
        raise ValueError("Duplicate record - this entry already exists")

    except asyncpg.CheckViolationError as e:
        # Handle check constraint violations
        self.logger.error(f"Check constraint violation: {e}")
        constraint_name = self._extract_constraint_name(e)
        raise ValueError(f"Invalid data: {constraint_name}")

    except asyncpg.PostgresError as e:
        # Handle other database errors
        self.logger.error(f"Database error in {self.__class__.__name__}: {e}", exc_info=True)
        raise RuntimeError("Database operation failed")

    except Exception as e:
        # Catch-all for unexpected errors
        self.logger.error(f"Unexpected error in {self.__class__.__name__}: {e}", exc_info=True)
        raise

def _extract_constraint_name(self, error):
    # Extract constraint name from error message
    import re
    match = re.search(r'constraint "(.*?)"', str(error))
    return match.group(1) if match else "unknown"
```

**Files to update:**
- [ ] `patient_service.py`
- [ ] `medication_service.py`
- [ ] `investigation_service.py`
- [ ] `therapy_service.py`
- [ ] `medical_action_service.py`

**Day 7 Testing Checklist:**
- [ ] All services have try-catch blocks
- [ ] Specific exceptions caught separately
- [ ] Meaningful error messages returned
- [ ] All errors logged with context

---

## Week 2: Frontend & Integration

### **DAY 8: Frontend Error Handling**

#### Full Day (9 AM - 5 PM)
**Goal:** Add null safety and error handling to all frontend code

**Step 8.1: Add optional chaining everywhere**

**Pattern to apply:**
```typescript
// BEFORE:
const medications = patient.medications.map(med => ...)

// AFTER:
const medications = patient?.medications?.map(med => ...) ?? []
```

**Files to update with optional chaining:**
- [ ] `hooks/usePatientMedications.ts`
- [ ] `hooks/usePatientInvestigations.ts`
- [ ] `hooks/usePatientTherapies.ts`
- [ ] `services/PatientCaseService.ts`
- [ ] All component files accessing nested properties

**Step 8.2: Fix useState initialization**

```typescript
// BEFORE:
const [medications, setMedications] = useState<Medication[]>();

// AFTER:
const [medications, setMedications] = useState<Medication[]>([]);
```

**Step 8.3: Add error states to hooks**

```typescript
export function usePatientMedications(patientId: string) {
  const [medications, setMedications] = useState<Medication[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMedications = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await MedicationService.getPatientMedications(patientId);
      setMedications(data);
    } catch (err: any) {
      const message = err?.message || 'Failed to load medications';
      setError(message);
      console.error('Error fetching medications:', err);
    } finally {
      setLoading(false);
    }
  };

  return { medications, loading, error, fetchMedications };
}
```

**Step 8.4: Update components to display errors**

```typescript
function MedicationsList() {
  const { medications, loading, error } = usePatientMedications(patientId);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} onRetry={fetchMedications} />;
  if (medications.length === 0) return <EmptyState message="No medications" />;

  return <MedicationTable data={medications} />;
}
```

**Day 8 Testing Checklist:**
- [ ] No "Cannot read property of undefined" errors
- [ ] Loading states display correctly
- [ ] Error states display with retry button
- [ ] Empty states display appropriately

---

### **DAY 9: Error Boundary & Global Error Handling**

#### Morning Session (9 AM - 12 PM)
**Goal:** Implement error boundaries

**Step 9.1: Create ErrorBoundary component**
- **File:** `hospital-display-app/src/components/ErrorBoundary.tsx` (new)
```typescript
import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught error:', error, errorInfo);
    // Send to error tracking service (Sentry, etc.)
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="error-boundary">
          <h2>⚠️ Something went wrong</h2>
          <p>{this.state.error?.message}</p>
          <button onClick={() => window.location.reload()}>
            Reload Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
```

**Step 9.2: Wrap app in ErrorBoundary**
- **File:** `hospital-display-app/src/App.tsx`
```typescript
import { ErrorBoundary } from './components/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary>
      {/* existing app code */}
    </ErrorBoundary>
  );
}
```

#### Afternoon Session (1 PM - 5 PM)
**Goal:** Add global error interceptor

**Step 9.3: Create API error interceptor**
- **File:** `hospital-display-app/src/services/apiInterceptor.ts` (new)
```typescript
export function setupApiInterceptors() {
  // Intercept all fetch calls
  const originalFetch = window.fetch;

  window.fetch = async (...args) => {
    try {
      const response = await originalFetch(...args);

      // Log errors
      if (!response.ok) {
        console.error(`API Error: ${response.status} ${response.statusText}`, {
          url: args[0],
          status: response.status
        });
      }

      return response;
    } catch (error) {
      console.error('Network error:', error);
      throw error;
    }
  };
}
```

**Day 9 Testing Checklist:**
- [ ] Error boundary catches component errors
- [ ] API errors logged to console
- [ ] Can reload after error
- [ ] Error boundaries don't break working components

---

### **DAY 10: Medical Safety Validations**

#### Full Day (9 AM - 5 PM)
**Goal:** Add critical medical safety checks

**Step 10.1: Medication safety checks**
- **File:** `hospital-backend/app/services/medication_service.py`

Add method to check before administering:
```python
async def validate_medication_administration(
    self,
    medication_id: int,
    patient_id: str,
    administered_by: str
) -> Dict[str, Any]:
    """
    Validate medication can be safely administered
    Returns: {"safe": True/False, "reason": "..."}
    """
    # Get medication details
    med = await self.medication_repository.get_by_id(medication_id)
    if not med:
        return {"safe": False, "reason": "Medication not found"}

    # Check medication is still active
    if med.get('status') != 'active':
        return {
            "safe": False,
            "reason": f"Medication is {med.get('status')}, not active"
        }

    # Check patient is still admitted
    patient = await self.patient_repository.get_by_id(patient_id)
    if patient.get('status') != 'active':
        return {
            "safe": False,
            "reason": f"Patient is {patient.get('status')}, not active"
        }

    # Check timing - minimum 4 hours between doses for most meds
    last_admin = await self.get_last_administration(medication_id)
    if last_admin:
        from datetime import datetime, timedelta
        last_time = last_admin.get('performedAt')
        if last_time:
            time_since = datetime.now() - last_time
            if time_since < timedelta(hours=4):
                return {
                    "safe": False,
                    "reason": f"Too soon since last dose ({time_since.seconds // 3600}h ago). Minimum 4 hours required."
                }

    # Check for allergies
    allergies = patient.get('allergies', '')
    if allergies and med.get('name').lower() in allergies.lower():
        return {
            "safe": False,
            "reason": f"⚠️ ALLERGY ALERT: Patient allergic to {med.get('name')}"
        }

    return {"safe": True, "reason": "All checks passed"}
```

**Step 10.2: Update medication administration to use validation**
```python
async def administer_medication(self, medication_id: int, patient_id: str, admin_data: Dict, user_id: str):
    # Validate first
    validation = await self.validate_medication_administration(medication_id, patient_id, user_id)

    if not validation["safe"]:
        raise ValueError(validation["reason"])

    # Proceed with administration
    return await self.medication_repository.record_administration(...)
```

**Step 10.3: Frontend safety confirmation**
- **File:** `hospital-display-app/src/hooks/usePatientMedications.ts`

```typescript
const administerMedication = async (medicationId: number) => {
  try {
    // First validate
    const validation = await MedicationService.validateAdministration(medicationId, patientId);

    if (!validation.safe) {
      const confirmed = window.confirm(
        `⚠️ SAFETY WARNING\n\n${validation.reason}\n\nAre you sure you want to proceed?`
      );
      if (!confirmed) return;
    }

    // Proceed
    await MedicationService.administerMedication(medicationId, patientId);
    alert('✅ Medication administered successfully');
  } catch (error: any) {
    alert(`❌ Failed: ${error.message}`);
  }
};
```

**Day 10 Testing Checklist:**
- [ ] Cannot administer discontinued medication
- [ ] Cannot administer to discharged patient
- [ ] Allergy check works
- [ ] Time-between-doses check works
- [ ] Safety warnings display clearly

---

### **DAY 11: Soft Delete Implementation**

#### Full Day (9 AM - 5 PM)
**Goal:** Prevent data loss with soft delete

**Step 11.1: Add deletedAt column to all tables**
- **File:** `hospital-backend/migrations/004_add_soft_delete.sql`
```sql
BEGIN;

-- Add deletedAt column to all tables
ALTER TABLE patients ADD COLUMN "deletedAt" TIMESTAMPTZ DEFAULT NULL;
ALTER TABLE medications ADD COLUMN "deletedAt" TIMESTAMPTZ DEFAULT NULL;
ALTER TABLE investigations ADD COLUMN "deletedAt" TIMESTAMPTZ DEFAULT NULL;
ALTER TABLE therapy ADD COLUMN "deletedAt" TIMESTAMPTZ DEFAULT NULL;
ALTER TABLE casesheetentries ADD COLUMN "deletedAt" TIMESTAMPTZ DEFAULT NULL;
ALTER TABLE staff ADD COLUMN "deletedAt" TIMESTAMPTZ DEFAULT NULL;

-- Create index for faster queries
CREATE INDEX idx_patients_deleted ON patients("deletedAt") WHERE "deletedAt" IS NULL;
CREATE INDEX idx_medications_deleted ON medications("deletedAt") WHERE "deletedAt" IS NULL;

COMMIT;
```

**Step 11.2: Update base repository**
- **File:** `hospital-backend/app/repositories/base_repository.py`

```python
async def soft_delete(self, record_id: str, deleted_by: str = None) -> bool:
    """Soft delete by setting deletedAt timestamp"""
    query = f'''
        UPDATE {self.table_name}
        SET "deletedAt" = NOW()
        WHERE id = $1 AND "deletedAt" IS NULL
        RETURNING id
    '''
    result = await self.execute_custom_query(query, [record_id])

    # Log to audit trail
    if result and deleted_by:
        await self.log_audit(
            user_id=deleted_by,
            action='DELETE',
            resource_type=self.table_name,
            resource_id=record_id
        )

    return bool(result)

async def get_all_active(self) -> List[Dict[str, Any]]:
    """Get only non-deleted records"""
    query = f'SELECT * FROM {self.table_name} WHERE "deletedAt" IS NULL'
    return await self.execute_custom_query(query)
```

**Step 11.3: Update all queries to filter deleted**
Pattern:
```python
# BEFORE:
SELECT * FROM patients WHERE id = $1

# AFTER:
SELECT * FROM patients WHERE id = $1 AND "deletedAt" IS NULL
```

Apply to all repositories.

**Day 11 Testing Checklist:**
- [ ] Delete sets deletedAt instead of removing row
- [ ] Deleted records don't appear in lists
- [ ] Can query deleted records if needed (audit)
- [ ] Medical records preserved after patient "deleted"

---

### **DAY 12: Integration Testing**

#### Full Day (9 AM - 5 PM)
**Goal:** Test all baseline fixes work together

**Test Scenarios:**

1. **Patient Admission Flow**
   - Create patient
   - Assign device
   - Add medications
   - Verify all FKs work

2. **Medication Safety Flow**
   - Try to prescribe as nurse → should fail
   - Login as doctor → should succeed
   - Try invalid dosage → should fail
   - Try to administer too soon → should warn
   - Administer with allergy → should block

3. **Error Handling Flow**
   - Delete patient with medications → CASCADE works
   - Try to delete prescriber → should RESTRICT
   - Invalid data → CHECK constraints work
   - Frontend shows all errors properly

4. **Security Flow**
   - Start without SECRET_KEY → should fail
   - Login with JWT → should work
   - Expired token → should redirect to login
   - Wrong role → should get 403

**Create test script:**
- **File:** `hospital-backend/tests/test_baseline_integration.py`
```python
import pytest
import asyncpg

@pytest.mark.asyncio
async def test_medication_foreign_keys():
    """Test FK constraints on medications"""
    # Try to create medication for invalid patient
    with pytest.raises(asyncpg.ForeignKeyViolationError):
        await medication_service.add_medication("INVALID_ID", med_data, "DOC001")

@pytest.mark.asyncio
async def test_medication_safety_checks():
    """Test medication safety validations"""
    # Try to administer discontinued med
    validation = await medication_service.validate_medication_administration(
        medication_id=123,
        patient_id="PAT001",
        administered_by="NURSE001"
    )
    assert validation["safe"] == False
    assert "discontinued" in validation["reason"].lower()

# Add 50+ integration tests
```

**Day 12 Deliverables:**
- [ ] 50+ integration tests passing
- [ ] Test coverage report generated
- [ ] All critical paths tested
- [ ] Bug list created for any issues found

---

### **DAY 13: Bug Fixes & Polish**

#### Full Day (9 AM - 5 PM)
**Goal:** Fix all bugs found during integration testing

**Process:**
1. Review bug list from Day 12
2. Prioritize: P0 (must fix) → P1 (should fix) → P2 (nice to fix)
3. Fix P0 and P1 bugs
4. Retest affected areas
5. Update documentation

**Common bug patterns to watch for:**
- Null pointer errors from edge cases
- Race conditions under load
- Error messages not user-friendly
- Missing validation scenarios
- Frontend state not updating

---

### **DAY 14: Documentation & Deployment Prep**

#### Morning Session (9 AM - 12 PM)
**Goal:** Document all changes

**Step 14.1: Create CHANGELOG.md**
```markdown
# Baseline Foundation - Changelog

## Database Changes
- ✅ Added 37 foreign key constraints
- ✅ Added 15 CHECK constraints
- ✅ Added 5 UNIQUE constraints
- ✅ Implemented soft delete (deletedAt column)

## Security Changes
- ✅ Removed all hardcoded secrets
- ✅ Implemented JWT authentication
- ✅ Added role-based access control
- ✅ Fixed SQL injection vulnerabilities

## Validation Changes
- ✅ Added Pydantic validation to all endpoints
- ✅ Medication dosage/route/frequency validation
- ✅ Medical safety checks before administration
- ✅ Allergy checking

## Error Handling
- ✅ Comprehensive try-catch in all services
- ✅ Frontend null safety with optional chaining
- ✅ Error boundaries for component failures
- ✅ User-friendly error messages

## Migration Guide
[Step-by-step guide for deploying baseline changes]
```

**Step 14.2: Create deployment checklist**
```markdown
# Deployment Checklist - Baseline Foundation

## Pre-Deployment
- [ ] All tests passing (run: npm test && pytest)
- [ ] Database backup created
- [ ] Environment variables configured (.env file)
- [ ] SECRET_KEY generated (32+ characters)
- [ ] JWT_SECRET generated (32+ characters)

## Deployment Steps
1. [ ] Backup database: `pg_dump hospital_management > backup.sql`
2. [ ] Run migrations in order:
   - [ ] 001_add_foreign_keys_core_tables.sql
   - [ ] 002_add_foreign_keys_medical_records.sql
   - [ ] 003_add_check_constraints.sql
   - [ ] 004_add_soft_delete.sql
3. [ ] Deploy backend with new code
4. [ ] Deploy frontend with new code
5. [ ] Verify health check: http://api/health
6. [ ] Test critical paths

## Post-Deployment Verification
- [ ] Can create patient
- [ ] Can add medication (as doctor)
- [ ] Cannot add medication (as nurse)
- [ ] Error messages display correctly
- [ ] All FKs working (try to delete patient with meds)

## Rollback Plan
If issues occur:
1. [ ] Stop applications
2. [ ] Restore database: `psql hospital_management < backup.sql`
3. [ ] Deploy previous code version
4. [ ] Verify system operational
```

#### Afternoon Session (1 PM - 5 PM)
**Goal:** Final validation

**Step 14.3: Final smoke testing**
- Test all critical user journeys
- Verify all baseline fixes in place
- Check performance (page load times)
- Security scan (basic)

**Step 14.4: Create summary report**
```markdown
# Baseline Foundation - Summary Report

## Completed Fixes: 147/147 ✅

### Critical Fixes (42)
✅ All database foreign keys added
✅ All hardcoded secrets removed
✅ JWT authentication implemented
✅ Medical safety validations added
✅ Soft delete implemented

### High Priority Fixes (51)
✅ CHECK constraints added
✅ Error handling comprehensive
✅ Frontend null safety complete
✅ API validation complete

### Medium Priority Fixes (38)
✅ Error boundaries implemented
✅ Loading states added
✅ User-friendly error messages

### Low Priority Fixes (16)
✅ Code cleanup
✅ Documentation complete

## Success Metrics
- Database integrity: 100% (all FKs, constraints in place)
- Security: 95% (JWT auth, no secrets, SQL injection fixed)
- Validation: 100% (all endpoints validated)
- Error handling: 95% (comprehensive coverage)
- Test coverage: 80% (integration tests)

## Known Limitations
- Performance optimization needed (will be Phase 2)
- Missing features (backup, notifications) - will be Phase 3-5
- Advanced security (rate limiting, encryption at rest) - will be Phase 4

## Production Readiness
✅ Safe to deploy to staging
⚠️ Production deployment recommended after 1 week of staging validation

## Next Steps
1. Deploy to staging environment
2. Run load testing
3. Security penetration testing
4. Plan Phase 2 (Performance optimization)
```

---

## Rollback Procedures

### If Migration Fails
```bash
# Rollback specific migration
psql -U postgres -d hospital_management -f migrations/00X_rollback.sql

# Restore from backup
pg_restore -U postgres -d hospital_management backup.dump
```

### If Backend Deployment Fails
```bash
# Revert to previous version
git checkout previous-commit
python main.py
```

### If Frontend Deployment Fails
```bash
# Revert to previous version
git checkout previous-commit
npm start
```

---

## Success Criteria Checklist

After 14 days, verify:

### Database
- [ ] All foreign keys enforced
- [ ] All CHECK constraints working
- [ ] Soft delete implemented
- [ ] No orphaned records possible

### Security
- [ ] No hardcoded secrets
- [ ] JWT authentication required
- [ ] RBAC working (roles enforced)
- [ ] No SQL injection possible

### Validation
- [ ] All endpoints validated
- [ ] Medical data validated (dosage, route, frequency)
- [ ] Safety checks before administration
- [ ] Allergy checking works

### Error Handling
- [ ] All services have try-catch
- [ ] Frontend has null safety
- [ ] Error boundaries catch failures
- [ ] User sees helpful error messages

### Testing
- [ ] 80%+ test coverage
- [ ] Integration tests pass
- [ ] Manual testing complete
- [ ] Performance acceptable

---

## Contact & Support

**Issues during implementation:**
- Review audit reports for context
- Check migration rollback scripts
- Consult BASELINE_FIX_IMPLEMENTATION_PLAN.md

**After completion:**
- Document lessons learned
- Update team on changes
- Plan Phase 2 (Performance & Stability)

---

**Last Updated:** 2025-10-05
**Next Review:** After Day 14 completion
**Status:** Ready to Execute ✅
