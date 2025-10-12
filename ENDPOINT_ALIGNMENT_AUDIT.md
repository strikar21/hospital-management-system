# Frontend-Backend Endpoint Alignment Audit

**Date:** 2025-10-12
**Purpose:** Verify frontend service endpoints match backend API
**Status:** ⚠️ MISMATCHES FOUND

---

## Executive Summary

Critical endpoint mismatches found between frontend services and backend API. The frontend uses `/medications/patient/{patientId}` but backend uses `/medications/patient/{patient_id}` with **snake_case** parameter.

**Key Issues:**
1. ❌ **Parameter naming mismatch** - Frontend: `patientId` (camelCase) vs Backend: `patient_id` (snake_case)
2. ✅ **Atomic endpoints aligned** - Both use `/atomic/patients/{patientId}/...`
3. ⚠️ **Status update endpoints need verification**

---

## Endpoint Comparison

### 1. MEDICATIONS

#### Frontend (MedicationService via BaseMedicalRecordService)
```typescript
// Get all medications
GET /${config.recordType}/patient/${patientId}
→ GET /medications/patient/${patientId}

// Get active medications
GET /${config.recordType}/patient/${patientId}/${statusFilter}
→ GET /medications/patient/${patientId}/active

// Add medication (atomic)
POST /atomic/patients/${patientId}/${config.recordType}?performedBy=${userId}
→ POST /atomic/patients/${patientId}/medications?performedBy=${userId}

// Update medication status
PUT /${config.recordType}/${recordId}/status
→ PUT /medications/${recordId}/status
```

#### Backend (medications.py)
```python
@router.get("/patient/{patient_id}")         # ❌ MISMATCH: patient_id (snake_case)
@router.get("/patient/{patient_id}/active")  # ❌ MISMATCH: patient_id (snake_case)
@router.post("/patient/{patient_id}")        # Legacy
@router.put("/{medication_id}/status")       # ❌ MISMATCH: medication_id (snake_case)
```

#### Backend (atomic_medical.py)
```python
@router.post("/patients/{patient_id}/medications")  # ✅ MATCH (frontend sends patientId, backend receives patient_id)
@router.put("/patients/{patient_id}/medications/{medication_id}/status")
```

**Status:** ⚠️ **PARAMETER MISMATCH** - snake_case vs camelCase

---

### 2. INVESTIGATIONS

#### Frontend (InvestigationService via BaseMedicalRecordService)
```typescript
// Get all investigations
GET /investigations/patient/${patientId}

// Get pending investigations
GET /investigations/patient/${patientId}/pending

// Add investigation (atomic)
POST /atomic/patients/${patientId}/investigations?performedBy=${userId}

// Update investigation status
PUT /investigations/${recordId}/status
```

#### Backend
```python
# No explicit /investigations/patient/{patient_id} endpoint found in backend
# Atomic endpoint exists:
@router.post("/patients/{patient_id}/investigations")  # ✅ MATCH
@router.put("/patients/{patient_id}/investigations/{investigation_id}/status")
@router.post("/patients/{patient_id}/investigations/{investigation_id}/complete")
```

**Status:** ⚠️ **MISSING GET ENDPOINT** - Backend missing `/investigations/patient/{patient_id}`

---

### 3. THERAPIES

#### Frontend (TherapyService via BaseMedicalRecordService)
```typescript
// Get all therapies
GET /therapies/patient/${patientId}

// Get active therapies
GET /therapies/patient/${patientId}/active

// Add therapy (atomic)
POST /atomic/patients/${patientId}/therapies?performedBy=${userId}

// Update therapy status
PUT /therapies/${recordId}/status
```

#### Backend
```python
# No explicit /therapies/patient/{patient_id} endpoint found in backend
# Atomic endpoint exists:
@router.post("/patients/{patient_id}/therapies")  # ✅ MATCH
@router.put("/patients/{patient_id}/therapies/{therapy_id}/status")
@router.post("/patients/{patient_id}/therapies/{therapy_id}/sessions")
```

**Status:** ⚠️ **MISSING GET ENDPOINT** - Backend missing `/therapies/patient/{patient_id}`

---

### 4. NOTES

#### Frontend (NotesService via BaseMedicalRecordService)
```typescript
// Get all notes
GET /notes/patient/${patientId}

// Add note (atomic)
POST /atomic/patients/${patientId}/notes?performedBy=${userId}
```

#### Backend (patients.py)
```python
@router.post("/{patient_id}/notes")          # For patients router
@router.put("/{patient_id}/notes/{note_id}")
@router.delete("/{patient_id}/notes/{note_id}")
```

#### Backend (atomic_medical.py)
```python
@router.post("/patients/{patient_id}/notes")  # ✅ MATCH
```

**Status:** ⚠️ **MISSING GET ENDPOINT** - Backend missing `/notes/patient/{patient_id}`

---

### 5. CASE SHEET / ALERTS

#### Frontend (CaseSheetService)
```typescript
// Get case entries with staff data
GET /patients/${patientId}/case-entries?includeStaff=true

// Add case entry
POST /patients/${patientId}/case-entries
```

#### Backend (patients.py)
```python
@router.get("/{patient_id}/case-entries")    # ❌ MISMATCH: patient_id (snake_case)
@router.post("/{patient_id}/case-entries")   # ❌ MISMATCH: patient_id (snake_case)
```

**Status:** ⚠️ **PARAMETER MISMATCH** - snake_case vs camelCase

---

#### Frontend (AlertService)
```typescript
// Get patient alerts
GET /patients/${patientId}/alerts

// Acknowledge alert (atomic)
POST /atomic/patients/${patientId}/alerts/${alertId}/acknowledge

// Resolve alert (atomic)
POST /atomic/patients/${patientId}/alerts/${alertId}/resolve
```

#### Backend (patients.py)
```python
@router.get("/{patient_id}/alerts")  # ❌ MISMATCH: patient_id (snake_case)
@router.post("/{patient_id}/alerts/{alert_id}/acknowledge")  # ❌ MISMATCH
```

#### Backend (atomic_medical.py)
```python
@router.post("/patients/{patient_id}/alerts/{alert_id}/acknowledge")  # ✅ MATCH
```

**Status:** ⚠️ **PARAMETER MISMATCH** - snake_case vs camelCase

---

## Critical Issues Found

### Issue 1: Parameter Naming Convention Mismatch ❌

**Problem:** Frontend uses camelCase (`patientId`, `medicationId`) but backend uses snake_case (`patient_id`, `medication_id`)

**Impact:**
- FastAPI/Pydantic may auto-convert between naming conventions
- This works **accidentally** but is not explicit
- Creates confusion and maintenance issues

**Frontend:**
```typescript
GET /medications/patient/${patientId}
```

**Backend:**
```python
@router.get("/patient/{patient_id}")
```

**Solution Options:**
1. **Option A (RECOMMENDED):** Update backend to use camelCase in path parameters
   - Change `{patient_id}` → `{patientId}`
   - Aligns with project's strict camelCase policy

2. **Option B:** Update frontend to use snake_case
   - Violates CLAUDE.md guidelines
   - NOT RECOMMENDED

3. **Option C:** Keep as-is and document the auto-conversion
   - Implicit behavior
   - May break unexpectedly

---

### Issue 2: Missing GET Endpoints ❌

**Problem:** Frontend expects GET endpoints that don't exist in backend

**Missing Endpoints:**
- ❌ `GET /investigations/patient/{patient_id}`
- ❌ `GET /therapies/patient/{patient_id}`
- ❌ `GET /notes/patient/{patient_id}`

**Current Workaround:** Frontend may be getting 404 errors or empty responses

**Solution:** Add missing GET endpoints to backend or update frontend to use existing endpoints

---

### Issue 3: Status Update Endpoint Mismatch ⚠️

**Frontend expects:**
```typescript
PUT /medications/${medicationId}/status
PUT /investigations/${investigationId}/status
PUT /therapies/${therapyId}/status
```

**Backend has:**
```python
PUT /medications/{medication_id}/status  # medications.py:137
PUT /patients/{patient_id}/medications/{medication_id}/status  # atomic_medical.py:563
```

**Problem:** Frontend uses short path, backend may require full path with patient_id

---

## Working Endpoints ✅

### Atomic Operations (ALL WORKING)
- ✅ POST `/atomic/patients/{patient_id}/medications`
- ✅ POST `/atomic/patients/{patient_id}/investigations`
- ✅ POST `/atomic/patients/{patient_id}/therapies`
- ✅ POST `/atomic/patients/{patient_id}/notes`
- ✅ POST `/atomic/patients/{patient_id}/alerts/{alert_id}/acknowledge`
- ✅ POST `/atomic/patients/{patient_id}/medications/{medication_id}/administer`
- ✅ POST `/atomic/patients/{patient_id}/therapies/{therapy_id}/sessions`

**Note:** These work because path parameters are auto-converted by FastAPI

---

## Recommendations

### Priority: CRITICAL

1. **Verify Parameter Auto-Conversion**
   - Test if FastAPI auto-converts `patientId` → `patient_id`
   - Check if this is explicit in backend configuration

2. **Standardize to camelCase (RECOMMENDED)**
   - Update all backend path parameters to camelCase
   - Aligns with CLAUDE.md strict camelCase policy
   - Example: `{patient_id}` → `{patientId}`

### Priority: HIGH

3. **Add Missing GET Endpoints**
   - Add `GET /investigations/patient/{patientId}`
   - Add `GET /therapies/patient/{patientId}`
   - Add `GET /notes/patient/{patientId}`
   - OR update frontend to use correct endpoints

4. **Verify Status Update Endpoints**
   - Test if short paths work: `PUT /medications/{medicationId}/status`
   - OR update frontend to use full paths

---

## Testing Required

### Backend Endpoint Verification
```bash
# Test if endpoints exist
curl http://localhost:8001/medications/patient/PAT001
curl http://localhost:8001/investigations/patient/PAT001
curl http://localhost:8001/therapies/patient/PAT001
```

### Parameter Conversion Test
```bash
# Test camelCase parameter
curl http://localhost:8001/patients/PAT001/case-entries

# Check if FastAPI logs show conversion
```

---

## Next Steps

1. **Immediate:** Test actual backend to verify endpoints exist
2. **Immediate:** Check FastAPI parameter conversion behavior
3. **High Priority:** Add missing GET endpoints OR fix frontend
4. **High Priority:** Standardize to camelCase across all endpoints
5. **Medium Priority:** Create endpoint documentation with correct paths

---

## Conclusion

**Status:** ⚠️ **ALIGNMENT ISSUES FOUND**

The frontend and backend have endpoint mismatches primarily due to:
1. Parameter naming convention differences (camelCase vs snake_case)
2. Missing GET endpoints for investigations, therapies, notes
3. Potential status update endpoint path mismatches

**Critical Action:** Verify if backend is running and test actual endpoints to determine if auto-conversion is working or if endpoints are failing.

---

*Generated with Research-First Medical Developer approach*
*Following endpoint audit protocol*
