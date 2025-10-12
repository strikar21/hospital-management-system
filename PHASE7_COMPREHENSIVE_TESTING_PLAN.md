# Phase 7: Comprehensive System Testing Plan

**Date Created:** 2025-10-12
**Branch:** feat/staff-resolution-standardization
**Purpose:** Test all refactored components (Phases 1-6) for functionality and integration

---

## Executive Summary

Phase 7 will systematically test all refactored components to ensure:
- ✅ Frontend services work correctly with backend APIs
- ✅ All atomic operations function as expected
- ✅ Staff resolution and field name standardization (camelCase) is working
- ✅ No regressions from refactoring
- ✅ End-to-end workflows complete successfully

---

## Test Environment

### Backend Status
- **URL:** http://localhost:8001
- **Status:** ✅ HEALTHY
- **Database:** ✅ CONNECTED (PostgreSQL + TimescaleDB)
- **API Version:** v1 and v2 available

### Test Data Available
**Patients (5 total):**
- `7163182b-5d6e-412d-93d9-28ecfd86cc6e` - Robert Anderson (active, Room 201 Bed A)
- `9b1f89f3-577d-451e-983d-e6a97f937d76` - William Johnson (active, Room 203 Bed A)
- `6b851aa6-e564-40b6-963f-e1a5efdf024c` - Jennifer Lee (discharged, Room 204 Bed A)
- `081a5294-da91-4c74-bb8a-e5062f5851dd` - Thomas Brown (active, Room 205 Bed B)
- `TEST001` - Test Patient (active, Room 101 Bed 1)

**Staff (10 total):**
- `DOC0001` - Sarah Johnson (Doctor)
- `DOC0002` - Michael Chen (Doctor)
- `NUR0001` - Emily Rodriguez (Nurse)
- `NUR0002` - James Wilson (Nurse)
- `LAB001` - Laboratory Services
- `RAD001` - Radiology Department
- `TEC0001` - David Kumar (Technician)
- `ADM0001` - Lisa Thompson (Administrator)
- And more...

**Existing Data:**
- 49 Medications
- 19 Investigations
- 145 Case Entries
- 0 Therapies (needs testing!)

---

## Backend API Endpoints (Verified)

### V2 Repository-Based Endpoints
- `/api/v2/patients` - Patients v2
- `/api/v2/medications` - Medications v2

### Atomic Medical Operations (`/api/v2/`)
1. `POST /patients/{patient_id}/medications` - Add medication (atomic)
2. `POST /patients/{patient_id}/investigations` - Add investigation (atomic)
3. `POST /patients/{patient_id}/therapies` - Add therapy (atomic) ⚠️
4. `POST /patients/{patient_id}/notes` - Add note (atomic)
5. `POST /patients/{patient_id}/medical-action` - Execute medical action
6. `POST /patients/{patient_id}/medications/{medication_id}/administer` - Administer medication
7. `POST /patients/{patient_id}/therapies/{therapy_id}/sessions` - Record therapy session
8. `PUT /patients/{patient_id}/investigations/{investigation_id}/status` - Update investigation status
9. `PUT /patients/{patient_id}/medications/{medication_id}/status` - Update medication status
10. `PUT /patients/{patient_id}/therapies/{therapy_id}/status` - Update therapy status
11. `POST /patients/{patient_id}/alerts/{alert_id}/acknowledge` - Acknowledge alert
12. `POST /patients/{patient_id}/investigations/{investigation_id}/complete` - Complete investigation

### V1 Endpoints
- `/api/v1/auth` - Authentication
- `/api/v1/staff` - Staff management
- `/api/v1/nursing` - Nursing dashboard
- `/api/v1/admission` - Admissions
- `/api/v1/discharge` - Discharge workflow
- `/api/v1/devices` - Device management

---

## Test Categories

### Category 1: Backend Connectivity ✅
**Purpose:** Verify backend is accessible and responds correctly
**Tests:**
1. Health check endpoint
2. Working patients endpoint
3. V2 API endpoints
4. Atomic operation endpoints

### Category 2: Service Layer Testing (Frontend)
**Purpose:** Verify all refactored services work correctly
**Tests:**
1. MedicationService (Phase 2)
2. InvestigationService (Phase 2)
3. TherapyService (Phase 3) ⚠️ Known issue
4. NotesService (Phase 5)
5. CaseSheetService (Phase 6)
6. AlertService (Phase 6)

### Category 3: Hook Layer Testing
**Purpose:** Verify hooks integrate correctly with services
**Tests:**
1. usePatientMedications
2. usePatientInvestigations
3. usePatientTherapies ⚠️ Known issue
4. usePatientNotes
5. usePatientCaseSheet

### Category 4: Component Layer Testing
**Purpose:** Verify UI components render and function
**Tests:**
1. PatientMedicationsContainer
2. PatientInvestigationsContainer
3. PatientTherapiesContainer ⚠️ Known issue
4. PatientNotesContainer
5. CaseSheetBook

### Category 5: Integration Testing
**Purpose:** Verify cross-component workflows
**Tests:**
1. Add medication → Case entry created → Timeline updated
2. Add investigation → Case entry created → Timeline updated
3. Add therapy → Case entry created → Timeline updated
4. Add note → Case entry created → Timeline updated
5. Acknowledge alert → Case entry created → Timeline updated
6. Complete medication → Status updated → Timeline updated
7. Staff name resolution across all operations

### Category 6: Field Name Standardization
**Purpose:** Verify camelCase consistency
**Tests:**
1. Backend returns camelCase (patientId, createdBy, performedBy)
2. Frontend sends camelCase (patientId, userId, status)
3. No snake_case anywhere
4. Staff fields standardized (prescribedBy, performedBy, acknowledgedBy)

---

## Test Execution Plan

### Phase 7.1: Backend Endpoint Verification
**Goal:** Confirm all backend endpoints are working

**Test 1: Health Check**
```bash
curl http://localhost:8001/health
Expected: {"status":"healthy","timestamp":"...","database":"connected","version":"1.0.0"}
```

**Test 2: Get Patients**
```bash
curl http://localhost:8001/working-patients
Expected: {"patients":[...], "count":5, "status":"success"}
```

**Test 3: Get Medications for Patient**
```bash
curl "http://localhost:8001/medications/patient/7163182b-5d6e-412d-93d9-28ecfd86cc6e"
Expected: {"medications":[...]} with camelCase fields
```

**Test 4: Get Investigations for Patient**
```bash
curl "http://localhost:8001/investigations/patient/7163182b-5d6e-412d-93d9-28ecfd86cc6e"
Expected: {"investigations":[...]} with camelCase fields
```

**Test 5: Get Therapies for Patient** ⚠️
```bash
curl "http://localhost:8001/therapy/patient/7163182b-5d6e-412d-93d9-28ecfd86cc6e"
Expected: {"therapy":[...]} - Need to verify endpoint exists
```

**Test 6: Get Case Entries**
```bash
curl "http://localhost:8001/patients/7163182b-5d6e-412d-93d9-28ecfd86cc6e/case-entries?includeStaff=true"
Expected: {"caseEntries":[...], "staff":[...]} with staff resolution
```

---

### Phase 7.2: Atomic Operations Testing
**Goal:** Verify atomic operations work and create case entries

**Test 1: Add Medication (Atomic)**
```bash
POST /api/v2/patients/7163182b-5d6e-412d-93d9-28ecfd86cc6e/medications?performedBy=DOC0001
Body: {
  "medicationName": "Test Medication",
  "dosage": "500mg",
  "frequency": "twice daily",
  "route": "oral",
  "duration": "7 days",
  "instructions": "Take with food"
}
Expected: {"success":true, "medicalRecord":{...}, "caseEntry":{...}}
```

**Test 2: Add Investigation (Atomic)**
```bash
POST /api/v2/patients/7163182b-5d6e-412d-93d9-28ecfd86cc6e/investigations?performedBy=DOC0001
Body: {
  "testName": "Blood Test",
  "testType": "Laboratory",
  "reason": "Routine checkup",
  "urgency": "normal"
}
Expected: {"success":true, "medicalRecord":{...}, "caseEntry":{...}}
```

**Test 3: Add Therapy (Atomic)** ⚠️
```bash
POST /api/v2/patients/7163182b-5d6e-412d-93d9-28ecfd86cc6e/therapies?performedBy=DOC0001
Body: {
  "therapyName": "Physical Therapy",
  "therapyType": "physical",
  "frequency": "daily",
  "duration": "2 weeks",
  "instructions": "Leg exercises"
}
Expected: {"success":true, "medicalRecord":{...}, "caseEntry":{...}}
```

**Test 4: Add Note (Atomic)**
```bash
POST /api/v2/patients/7163182b-5d6e-412d-93d9-28ecfd86cc6e/notes?performedBy=DOC0001
Body: {
  "content": "Test note content",
  "noteType": "doctorNote"
}
Expected: {"success":true, "medicalRecord":{...}, "caseEntry":{...}}
```

**Test 5: Acknowledge Alert (Atomic)**
```bash
POST /api/v2/patients/{patient_id}/alerts/{alert_id}/acknowledge
Body: {
  "acknowledgedBy": "DOC0001",
  "alertId": "{alert_id}"
}
Expected: {"success":true, "caseEntry":{...}}
```

---

### Phase 7.3: Frontend Service Testing
**Goal:** Verify frontend services call correct backend endpoints

**Test Using Browser Console:**

**1. Test MedicationService**
```javascript
import { MedicationService } from './services';

// Get medications
const meds = await MedicationService.getPatientMedications('7163182b-5d6e-412d-93d9-28ecfd86cc6e');
console.log('Medications:', meds);

// Add medication (atomic)
const result = await MedicationService.addMedicationAtomic(
  '7163182b-5d6e-412d-93d9-28ecfd86cc6e',
  {
    medicationName: 'Test Med',
    dosage: '100mg',
    frequency: 'once daily',
    route: 'oral',
    duration: '5 days',
    instructions: 'Test'
  },
  'DOC0001'
);
console.log('Add Result:', result);
```

**2. Test InvestigationService**
```javascript
import { InvestigationService } from './services';

const investigations = await InvestigationService.getPatientInvestigations('7163182b-5d6e-412d-93d9-28ecfd86cc6e');
console.log('Investigations:', investigations);
```

**3. Test TherapyService** ⚠️
```javascript
import { TherapyService } from './services';

const therapies = await TherapyService.getPatientTherapies('7163182b-5d6e-412d-93d9-28ecfd86cc6e');
console.log('Therapies:', therapies);
```

**4. Test NotesService**
```javascript
import { NotesService } from './services';

const notes = await NotesService.getPatientRecords('7163182b-5d6e-412d-93d9-28ecfd86cc6e');
console.log('Notes:', notes);
```

**5. Test CaseSheetService**
```javascript
import { CaseSheetService } from './services';

const caseEntries = await CaseSheetService.getCaseEntries('7163182b-5d6e-412d-93d9-28ecfd86cc6e');
console.log('Case Entries:', caseEntries);
```

**6. Test AlertService**
```javascript
import { AlertService } from './services';

const alerts = await AlertService.getPatientAlerts('7163182b-5d6e-412d-93d9-28ecfd86cc6e');
console.log('Alerts:', alerts);
```

---

### Phase 7.4: Integration Workflow Testing
**Goal:** Verify end-to-end workflows

**Workflow 1: Add Medication → Verify Case Entry**
1. Add medication using MedicationService
2. Refresh case sheet
3. Verify case entry created with:
   - type: 'medication'
   - performedBy: 'DOC0001'
   - performedByName: 'Sarah Johnson' (staff resolved)
   - description includes medication name

**Workflow 2: Add Investigation → Verify Case Entry**
1. Add investigation using InvestigationService
2. Refresh case sheet
3. Verify case entry created

**Workflow 3: Add Therapy → Verify Case Entry** ⚠️
1. Add therapy using TherapyService
2. Refresh case sheet
3. Verify case entry created

**Workflow 4: Add Note → Verify Case Entry**
1. Add note using NotesService
2. Refresh case sheet
3. Verify case entry created

**Workflow 5: Acknowledge Alert → Verify Case Entry**
1. Trigger alert (manually create one)
2. Acknowledge using AlertService
3. Verify case entry created with 'alertAcknowledged' type

---

### Phase 7.5: Field Name Standardization Verification
**Goal:** Ensure camelCase everywhere

**Backend Response Checks:**
```javascript
// Check medication response
const med = meds[0];
console.assert(med.patientId !== undefined, 'patientId should exist');
console.assert(med.patient_id === undefined, 'patient_id should NOT exist');
console.assert(med.prescribedBy !== undefined, 'prescribedBy should exist');
console.assert(med.prescribed_by === undefined, 'prescribed_by should NOT exist');

// Check case entry response
const entry = caseEntries[0];
console.assert(entry.performedBy !== undefined, 'performedBy should exist');
console.assert(entry.performed_by === undefined, 'performed_by should NOT exist');
console.assert(entry.performedByName !== undefined, 'performedByName should exist');
console.assert(entry.performed_by_name === undefined, 'performed_by_name should NOT exist');
```

---

## Known Issues to Investigate

### Issue 1: Therapies Not Working ⚠️
**Status:** Reported by user ("notes work, therapies dont")
**Potential Causes:**
1. Backend endpoint mismatch (`/therapy` vs `/therapies`)
2. Field mapping issues (therapyType vs type)
3. Status enum mismatch (scheduled vs active)
4. Missing patientId prop in component

**Testing Steps:**
1. Check if backend endpoint exists
2. Verify field names in request/response
3. Check status values
4. Test with browser console first

### Issue 2: Alert Acknowledgment
**Status:** AlertService created but not tested
**Testing Steps:**
1. Create test alert
2. Acknowledge using AlertService
3. Verify case entry created
4. Check staff name resolution

---

## Test Execution Order

1. ✅ Backend connectivity (curl tests)
2. ⏸️ Backend atomic operations (curl/Postman tests)
3. ⏸️ Frontend services (browser console tests)
4. ⏸️ Frontend hooks (browser console tests)
5. ⏸️ Frontend components (manual UI testing)
6. ⏸️ Integration workflows (end-to-end tests)
7. ⏸️ Field name standardization (validation tests)

---

## Success Criteria

### Must Pass:
- ✅ All backend endpoints respond with 200 OK
- ✅ All services return data in camelCase format
- ✅ Atomic operations create both medical record and case entry
- ✅ Staff names resolved correctly in all responses
- ✅ No snake_case fields anywhere
- ✅ All components render without errors
- ✅ End-to-end workflows complete successfully

### Nice to Have:
- Performance benchmarks
- Load testing results
- Error handling verification

---

## Test Results Documentation

Results will be documented in: `PHASE7_TEST_RESULTS.md`

Format:
```
## Test: [Name]
- **Status:** ✅ PASS / ❌ FAIL / ⚠️ PARTIAL
- **Date:** 2025-10-12
- **Tested By:** Claude
- **Request:** [curl command or code]
- **Expected:** [expected result]
- **Actual:** [actual result]
- **Notes:** [any observations]
```

---

## Next Steps

1. Execute Phase 7.1: Backend endpoint verification
2. Execute Phase 7.2: Atomic operations testing
3. Execute Phase 7.3: Frontend service testing
4. Execute Phase 7.4: Integration workflow testing
5. Execute Phase 7.5: Field name standardization verification
6. Document all results in PHASE7_TEST_RESULTS.md
7. Fix any issues found
8. Create Phase 7 completion report

---

*Generated with Research-First Medical Developer approach*
*Test data verified, no assumptions made*
*All test IDs from actual database*
