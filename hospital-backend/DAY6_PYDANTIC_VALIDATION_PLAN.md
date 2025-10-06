# Day 6: Pydantic Validation Implementation Plan

**Date:** 2025-10-05
**Status:** 🚧 IN PROGRESS
**Focus:** Add comprehensive Pydantic validation for all API inputs

---

## Executive Summary

Day 6 addresses critical validation gaps identified in audit reports. Current state: API endpoints accept unvalidated `dict` objects, allowing invalid medical data (wrong dosages, invalid routes, malformed IDs) to enter the system.

### Current State (INSECURE):
- ❌ Medication endpoints accept `medication_data: dict` with no validation
- ❌ No validation of dosage values (could be negative, zero, or absurd)
- ❌ No validation of routes (could be typos like "oarl" instead of "oral")
- ❌ No validation of frequencies (could be malformed)
- ❌ Phone numbers, emails accepted without format checking
- ❌ Foreign key IDs not validated before database insertion
- ❌ String fields have no length limits (SQL injection risk)
- ❌ Date ranges not validated (end before start, future dates)

### Target State (SECURE):
- ✅ All API endpoints use typed Pydantic models
- ✅ Medical data validated with custom validators
- ✅ Enums for routes, frequencies, statuses
- ✅ Range validators for vital signs, dosages
- ✅ Format validators for phone, email, IDs
- ✅ Foreign key existence checks
- ✅ String length limits
- ✅ Date logic validation

---

## Audit Issues to Resolve

### From COMPREHENSIVE_ERROR_DETECTION_AUDIT.md:

**Issue #31: No Input Validation on Atomic Endpoints**
- **Location:** `app/api/v2/atomic_medical.py`
- **Severity:** CRITICAL
- **Problem:** Endpoints accept `dict` without validation

**Issue #32: Medication Dosage Not Validated**
- **Location:** `app/api/v2/atomic_medical.py:28-43`
- **Severity:** CRITICAL - PATIENT SAFETY
- **Problem:** No validation of dosage values (could prescribe negative doses)

**Issue #30: Data Type Inefficiency**
- **Location:** Multiple tables
- **Severity:** MEDIUM
- **Problem:** TEXT fields with no length limits

---

## Implementation Steps

### Step 1: Create Medical Data Validators (Core)

**File:** `app/validators/medical_validators.py`

**Content:**
- Medication validators (dosage, route, frequency)
- Investigation validators (test types, urgency)
- Therapy validators (types, duration)
- Vital signs validators (ranges for HR, BP, temp, O2)
- Patient data validators (phone, email, blood type)

**Example Validators:**
```python
from pydantic import validator, Field
from typing import Literal

class MedicationRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    dosage: str = Field(..., min_length=1, max_length=100)
    route: Literal['Oral', 'IV', 'IM', 'SC', 'Topical', 'Inhalation']
    frequency: str = Field(..., pattern=r'^(Once daily|Twice daily|TDS|QDS|PRN|STAT|.*times daily)$')
    prescribedBy: str = Field(..., pattern=r'^[A-Z]{3}[0-9]{4}$')  # e.g., DOC0001

    @validator('dosage')
    def validate_dosage(cls, v):
        # Extract numeric value and unit
        # Ensure positive, reasonable range
        # E.g., "500mg", "10ml", "2 tablets"
        return v

    @validator('prescribedBy')
    def validate_staff_id_format(cls, v):
        # Verify format matches staff ID pattern
        return v
```

### Step 2: Create Patient Validators

**File:** `app/validators/patient_validators.py`

**Content:**
```python
from pydantic import BaseModel, validator, EmailStr, Field
from datetime import date, datetime

class PatientCreate(BaseModel):
    firstName: str = Field(..., min_length=1, max_length=100, strip_whitespace=True)
    lastName: str = Field(..., min_length=1, max_length=100, strip_whitespace=True)
    dateOfBirth: date
    gender: Literal['Male', 'Female', 'Other', 'Prefer not to say']
    phoneNumber: Optional[str] = Field(None, pattern=r'^\+?[0-9]{10,15}$')
    email: Optional[EmailStr] = None
    bloodType: Optional[Literal['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']] = None

    @validator('dateOfBirth')
    def validate_dob(cls, v):
        if v > date.today():
            raise ValueError('Date of birth cannot be in the future')
        if v < date(1900, 1, 1):
            raise ValueError('Date of birth too far in the past')
        return v

    @validator('phoneNumber')
    def validate_phone(cls, v):
        if v:
            # Remove spaces, dashes, etc.
            cleaned = ''.join(c for c in v if c.isdigit() or c == '+')
            if len(cleaned) < 10:
                raise ValueError('Phone number too short')
            return cleaned
        return v
```

### Step 3: Create Investigation Validators

**File:** `app/validators/investigation_validators.py`

```python
class InvestigationRequest(BaseModel):
    testName: str = Field(..., min_length=1, max_length=200)
    testType: Literal['Lab', 'Radiology', 'ECG', 'Echo', 'CT', 'MRI', 'X-Ray', 'Ultrasound']
    urgency: Literal['Routine', 'Urgent', 'STAT']
    priority: Literal['Routine', 'High', 'Critical']
    prescribedBy: str = Field(..., pattern=r'^[A-Z]{3}[0-9]{4}$')
    performedBy: Optional[str] = Field(None, pattern=r'^[A-Z]{3}[0-9]{4}$')
    notes: Optional[str] = Field(None, max_length=2000)

    @validator('testName')
    def validate_test_name(cls, v):
        # Remove extra whitespace
        return ' '.join(v.split())
```

### Step 4: Create Therapy Validators

**File:** `app/validators/therapy_validators.py`

```python
class TherapyRequest(BaseModel):
    therapyType: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    startDate: datetime
    endDate: Optional[datetime] = None
    frequency: Optional[str] = Field(None, max_length=100)
    prescribedBy: str = Field(..., pattern=r'^[A-Z]{3}[0-9]{4}$')

    @validator('endDate')
    def validate_date_range(cls, v, values):
        if v and 'startDate' in values and v < values['startDate']:
            raise ValueError('End date cannot be before start date')
        return v
```

### Step 5: Create Vital Signs Validators

**File:** `app/validators/vitals_validators.py`

```python
class VitalSignsCreate(BaseModel):
    patientId: str = Field(..., pattern=r'^PAT[0-9]{4}$')
    heartRate: Optional[int] = Field(None, ge=20, le=300)  # 20-300 bpm
    bloodPressureSystolic: Optional[int] = Field(None, ge=50, le=250)  # 50-250 mmHg
    bloodPressureDiastolic: Optional[int] = Field(None, ge=30, le=150)  # 30-150 mmHg
    temperature: Optional[float] = Field(None, ge=30.0, le=45.0)  # 30-45°C
    oxygenSaturation: Optional[int] = Field(None, ge=0, le=100)  # 0-100%
    respiratoryRate: Optional[int] = Field(None, ge=0, le=60)  # 0-60 breaths/min
    glucoseLevel: Optional[float] = Field(None, ge=0.0, le=1000.0)  # 0-1000 mg/dL

    @validator('bloodPressureDiastolic')
    def validate_bp_ratio(cls, v, values):
        if v and 'bloodPressureSystolic' in values:
            systolic = values['bloodPressureSystolic']
            if v >= systolic:
                raise ValueError('Diastolic pressure must be lower than systolic')
        return v
```

### Step 6: Update API Endpoints to Use Validators

**Files to Modify:**
- `app/api/v2/medications.py` - Replace `dict` with `MedicationRequest`
- `app/api/v2/investigations.py` - Replace `dict` with `InvestigationRequest`
- `app/api/v2/therapy.py` - Replace `dict` with `TherapyRequest`
- `app/api/v2/patients.py` - Use `PatientCreate` with validators
- `app/api/v1/patients.py` - Use `PatientCreate` with validators

**Example Before:**
```python
@router.post("/patient/{patient_id}")
async def add_medication(
    patient_id: str,
    medication_data: dict  # ❌ No validation
):
```

**Example After:**
```python
from ...validators.medical_validators import MedicationRequest

@router.post("/patient/{patient_id}")
async def add_medication(
    patient_id: str,
    medication: MedicationRequest  # ✅ Validated
):
    medication_data = medication.dict()
```

### Step 7: Create Sanitization Utilities

**File:** `app/validators/sanitizers.py`

```python
import re
from typing import Optional

def sanitize_string(value: Optional[str], max_length: int = 1000) -> Optional[str]:
    """Remove potentially dangerous characters, trim whitespace"""
    if not value:
        return value

    # Remove control characters
    value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\r\t')

    # Trim whitespace
    value = value.strip()

    # Limit length
    if len(value) > max_length:
        value = value[:max_length]

    return value if value else None

def sanitize_id(value: str, pattern: str = r'^[A-Z]{3}[0-9]{4}$') -> str:
    """Validate ID format"""
    if not re.match(pattern, value):
        raise ValueError(f'Invalid ID format: {value}')
    return value

def sanitize_phone(value: Optional[str]) -> Optional[str]:
    """Clean phone number format"""
    if not value:
        return value

    # Keep only digits and +
    cleaned = ''.join(c for c in value if c.isdigit() or c == '+')

    return cleaned if len(cleaned) >= 10 else None
```

### Step 8: Create Validation Tests

**File:** `tests/test_day6_validators.py`

**Tests:**
1. Test medication validators accept valid data
2. Test medication validators reject invalid dosage
3. Test medication validators reject invalid route
4. Test patient validators reject future DOB
5. Test patient validators reject invalid phone
6. Test patient validators reject invalid email
7. Test vital signs validators reject out-of-range values
8. Test BP validator rejects diastolic > systolic
9. Test date range validators reject end before start
10. Test string sanitizers remove control characters
11. Test ID validators reject malformed IDs
12. Test comprehensive validation on API endpoints

---

## Validation Rules Summary

### Medication Validation:
- **name:** Required, 1-200 chars
- **dosage:** Required, 1-100 chars, positive values
- **route:** Enum: Oral, IV, IM, SC, Topical, Inhalation
- **frequency:** Pattern: "Once daily", "Twice daily", "TDS", etc.
- **prescribedBy:** Pattern: `^[A-Z]{3}[0-9]{4}$` (e.g., DOC0001)
- **startDate:** Cannot be in far future
- **endDate:** Must be after startDate if provided

### Investigation Validation:
- **testName:** Required, 1-200 chars
- **testType:** Enum: Lab, Radiology, ECG, Echo, CT, MRI, X-Ray, Ultrasound
- **urgency:** Enum: Routine, Urgent, STAT
- **priority:** Enum: Routine, High, Critical
- **prescribedBy:** Valid staff ID format
- **notes:** Max 2000 chars

### Therapy Validation:
- **therapyType:** Required, 1-200 chars
- **description:** Max 2000 chars
- **startDate:** Valid datetime
- **endDate:** After startDate if provided
- **frequency:** Max 100 chars
- **prescribedBy:** Valid staff ID format

### Patient Validation:
- **firstName/lastName:** Required, 1-100 chars
- **dateOfBirth:** Not in future, not before 1900
- **gender:** Enum: Male, Female, Other, Prefer not to say
- **phoneNumber:** Pattern: 10-15 digits, optional +
- **email:** Valid email format or null
- **bloodType:** Enum: A+, A-, B+, B-, AB+, AB-, O+, O-

### Vital Signs Validation:
- **heartRate:** 20-300 bpm
- **bloodPressureSystolic:** 50-250 mmHg
- **bloodPressureDiastolic:** 30-150 mmHg, must be < systolic
- **temperature:** 30.0-45.0°C
- **oxygenSaturation:** 0-100%
- **respiratoryRate:** 0-60 breaths/min
- **glucoseLevel:** 0-1000 mg/dL

---

## Security Benefits

### 1. Input Validation Prevents:
- ✅ SQL Injection (limited string lengths, sanitized input)
- ✅ Invalid medical data entering database
- ✅ Negative or zero dosages
- ✅ Malformed IDs causing FK errors
- ✅ Invalid date ranges causing logic errors

### 2. Patient Safety Improvements:
- ✅ Cannot prescribe invalid medication routes
- ✅ Cannot enter impossible vital signs
- ✅ Cannot create invalid date ranges for therapies
- ✅ Dosage validation prevents prescription errors

### 3. Data Quality Improvements:
- ✅ Consistent formats for phone, email
- ✅ Clean, trimmed strings
- ✅ Valid enums (no typos)
- ✅ Proper ID formats

---

## Files to Create

### New Validator Modules:
1. `app/validators/__init__.py`
2. `app/validators/medical_validators.py` - Medications
3. `app/validators/patient_validators.py` - Patients
4. `app/validators/investigation_validators.py` - Investigations
5. `app/validators/therapy_validators.py` - Therapies
6. `app/validators/vitals_validators.py` - Vital signs
7. `app/validators/sanitizers.py` - Input sanitization utilities

### Test Files:
8. `tests/test_day6_validators.py` - Validation tests

### Documentation:
9. `DAY6_COMPLETION_SUMMARY.md` - Summary when done

---

## Files to Modify

### API Endpoints (Replace `dict` with Pydantic models):
1. `app/api/v2/medications.py`
2. `app/api/v2/investigations.py`
3. `app/api/v2/therapy.py`
4. `app/api/v2/patients.py`
5. `app/api/v1/patients.py`
6. `app/api/v2/atomic_medical.py`

### Models (Add validators to existing models):
7. `app/models/patient.py` - Add validators
8. `app/models/staff.py` - Add validators

---

## Testing Strategy

### Unit Tests:
- Test each validator independently
- Test accept valid data
- Test reject invalid data
- Test edge cases (boundaries)
- Test sanitization functions

### Integration Tests:
- Test API endpoints reject invalid requests
- Test API endpoints accept valid requests
- Test error messages are clear
- Test validation happens before database operations

---

## Expected Outcome

### Before Day 6:
```python
# Any data accepted - DANGEROUS!
await add_medication(
    patient_id="INVALID_ID",
    medication_data={
        "name": "",
        "dosage": "-500mg",
        "route": "oarl",  # typo
        "frequency": "whenever"
    }
)
# ❌ Invalid data enters database
```

### After Day 6:
```python
# Validation prevents invalid data
await add_medication(
    patient_id="INVALID_ID",
    medication=MedicationRequest(
        name="",  # ❌ Rejected: too short
        dosage="-500mg",  # ❌ Rejected: negative
        route="oarl",  # ❌ Rejected: not in enum
        frequency="whenever"  # ❌ Rejected: invalid pattern
    }
)
# Returns 422 Validation Error with clear message
```

---

## Success Criteria

- ✅ All medical endpoints use Pydantic models (no `dict`)
- ✅ All validators implemented and tested
- ✅ All validation tests passing
- ✅ API returns clear validation errors (422)
- ✅ Invalid medical data rejected before database
- ✅ Audit issues #31, #32 resolved

---

## Next Steps

1. Create validator modules
2. Implement medication validators
3. Implement patient validators
4. Implement investigation validators
5. Implement therapy validators
6. Implement vital signs validators
7. Update API endpoints
8. Create comprehensive tests
9. Run tests and verify
10. Update documentation

---

**Status:** Ready to implement
**Estimated Time:** 2-3 hours
**Priority:** CRITICAL (Patient Safety)
