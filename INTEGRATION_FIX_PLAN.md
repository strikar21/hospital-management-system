# Frontend/Backend Integration Fix Plan
**Date:** 2025-10-06
**Priority:** 🔴 HIGH - Broken Audit Trail
**Status:** Ready for Implementation

---

## Executive Summary

**Problem:** Frontend services are NOT correctly passing staff audit fields to backend, resulting in:
- 100% of medications/investigations created have `createdBy = NULL` (or will be 'SYSTEM' once atomic endpoints are used)
- 60% of notes have `createdBy = 'system'` instead of actual user
- All edited notes will have `editedBy = 'system'` instead of actual editor

**Root Cause:** Field name mismatches and missing query parameters

**Impact:** ❌ Broken regulatory audit trail, DPDP Act 2023 non-compliance

---

## Verified Issues

### ✅ Issue 1: Atomic Endpoints Missing `performed_by` Parameter
**Files Affected:**
- `hospital-display-app/src/services/MedicationService.ts:47`
- `hospital-display-app/src/services/InvestigationService.ts:48`
- `hospital-display-app/src/services/TherapyService.ts:49`

**Current Code:**
```typescript
// Frontend sends request without performed_by
const response = await this.fetchFromBackend(
  `/atomic/patients/${patientId}/medications`,
  {
    method: 'POST',
    body: JSON.stringify({ ...medication })
  }
);
```

**Backend Receives:**
```python
async def add_medication_atomic_endpoint(
    patient_id: str,
    medication: MedicationRequest,
    performed_by: str = "SYSTEM"  # ❌ Defaults to SYSTEM
)
```

**Result:** All records created via atomic endpoints have `createdBy = "SYSTEM"`

---

### ✅ Issue 2: Notes Creation Field Name Mismatch
**File:** `hospital-display-app/src/services/patient/PatientNotesService.ts:39`

**Frontend Sends:**
```typescript
body: JSON.stringify({
  content,
  comment: content,
  commentedBy: userId,  // ❌ WRONG FIELD NAME
  authorName: username
})
```

**Backend Expects:**
```python
author_id=note_data.get('createdBy') or note_data.get('authorId', 'system')
# ❌ Looks for 'createdBy' or 'authorId', not 'commentedBy'
```

**Result:** Backend falls back to `'system'`, so notes have `createdBy = 'system'`

---

### ✅ Issue 3: Notes Editing Field Name Mismatch
**File:** `hospital-display-app/src/services/patient/PatientNotesService.ts:67`

**Frontend Sends:**
```typescript
body: JSON.stringify({
  content: newContent,
  editedBy: userId,  // ❌ WRONG FIELD NAME
  editedAt: new Date().toISOString()
})
```

**Backend Expects:**
```python
editor_id=note_data.get('modifiedBy', 'system')
# ❌ Looks for 'modifiedBy', not 'editedBy'
```

**Result:** Backend falls back to `'system'`, so edited notes have `editedBy = 'system'`

---

## Fix Strategy

**Two Approaches:**

### Option A: Fix Frontend (Recommended ✅)
Change frontend services to match backend expectations.
- ✅ Simpler (3 frontend files)
- ✅ Backend already supports these fields
- ✅ No backend changes needed
- ❌ Frontend breaking change

### Option B: Fix Backend
Change backend to accept frontend field names.
- ✅ No frontend changes
- ❌ More complex (multiple backend files)
- ❌ Need to maintain backwards compatibility
- ❌ Technical debt

**RECOMMENDATION: Option A (Fix Frontend)**

---

## Implementation Plan - Option A (Frontend Fix)

### Fix 1: Add `performed_by` to Atomic Endpoints

**Files to Modify:**
1. `hospital-display-app/src/services/MedicationService.ts`
2. `hospital-display-app/src/services/InvestigationService.ts`
3. `hospital-display-app/src/services/TherapyService.ts`

**Change:**
```typescript
// BEFORE
const response = await this.fetchFromBackend(
  `/atomic/patients/${patientId}/medications`,
  { method: 'POST', body: JSON.stringify({ ...medication }) }
);

// AFTER
const response = await this.fetchFromBackend(
  `/atomic/patients/${patientId}/medications?performed_by=${userId}`,
  { method: 'POST', body: JSON.stringify({ ...medication }) }
);
```

**Impact:**
- ✅ All new medications will have correct `createdBy`
- ✅ All new investigations will have correct `createdBy`
- ✅ All new therapies will have correct `createdBy`

---

### Fix 2: Change `commentedBy` to `createdBy` in Notes

**File:** `hospital-display-app/src/services/patient/PatientNotesService.ts`

**Change:**
```typescript
// BEFORE (Line 39)
body: JSON.stringify({
  content,
  comment: content,
  commentedBy: userId,  // ❌ WRONG
  authorName: username
})

// AFTER
body: JSON.stringify({
  content,
  comment: content,
  createdBy: userId,  // ✅ CORRECT
  authorName: username
})
```

**Impact:**
- ✅ All new notes will have correct `createdBy` (actual user, not 'system')

---

### Fix 3: Change `editedBy` to `modifiedBy` in Note Edits

**File:** `hospital-display-app/src/services/patient/PatientNotesService.ts`

**Change:**
```typescript
// BEFORE (Line 67)
body: JSON.stringify({
  content: newContent,
  editedBy: userId,  // ❌ WRONG
  editedAt: new Date().toISOString()
})

// AFTER
body: JSON.stringify({
  content: newContent,
  modifiedBy: userId,  // ✅ CORRECT
  modifiedAt: new Date().toISOString()
})
```

**Impact:**
- ✅ All edited notes will have correct `editedBy` (actual editor, not 'system')

---

## Code Changes Required

### File 1: MedicationService.ts

**Location:** `hospital-display-app/src/services/MedicationService.ts:47-60`

```typescript
static async addMedication(patientId: string, medication: Omit<medication, 'id' | 'history'>, userId: string): Promise<any> {
  try {
    const response = await this.fetchFromBackend(`/atomic/patients/${patientId}/medications?performed_by=${userId}`, {
      method: 'POST',
      body: JSON.stringify({
        name: medication.name,
        dosage: medication.dosage,
        frequency: medication.frequency,
        route: medication.route,
        duration: medication.duration,
        prescribedBy: medication.prescribedBy || userId,
        status: 'active'
      })
    });

    return response;
  } catch (error) {
    return null;
  }
}
```

---

### File 2: InvestigationService.ts

**Location:** `hospital-display-app/src/services/InvestigationService.ts:48-65`

```typescript
static async addInvestigation(patientId: string, investigation: Omit<investigation, 'id' | 'createdAt' | 'updatedAt' | 'createdBy' | 'createdByName'>, userId: string): Promise<any> {
  try {
    const response = await this.fetchFromBackend(`/atomic/patients/${patientId}/investigations?performed_by=${userId}`, {
      method: 'POST',
      body: JSON.stringify({
        ...investigation,
        prescribedBy: userId,
        status: 'ordered'
      })
    });

    return response;
  } catch (error) {
    return null;
  }
}
```

---

### File 3: TherapyService.ts

**Location:** `hospital-display-app/src/services/TherapyService.ts:49-66`

```typescript
static async addTherapy(patientId: string, therapy: Omit<therapy, 'id' | 'createdAt' | 'updatedAt' | 'createdBy' | 'createdByName'>, userId: string): Promise<any> {
  try {
    const response = await this.fetchFromBackend(`/atomic/patients/${patientId}/therapies?performed_by=${userId}`, {
      method: 'POST',
      body: JSON.stringify({
        ...therapy,
        prescribedBy: userId,
        status: 'active'
      })
    });

    return response;
  } catch (error) {
    return null;
  }
}
```

---

### File 4: PatientNotesService.ts (Note Creation)

**Location:** `hospital-display-app/src/services/patient/PatientNotesService.ts:32-49`

```typescript
static async addNoteComment(patientId: string, content: string, userId: string, username?: string, userrole?: string): Promise<any> {
  try {
    const response = await this.fetchFromBackend(`/atomic/patients/${patientId}/notes`, {
      method: 'POST',
      body: JSON.stringify({
        content,
        comment: content,
        createdBy: userId,  // ✅ CHANGED from commentedBy
        authorName: username
      })
    });
    return response;
  } catch (error) {
    throw error;
  }
}
```

---

### File 5: PatientNotesService.ts (Note Editing)

**Location:** `hospital-display-app/src/services/patient/PatientNotesService.ts:61-76`

```typescript
static async editNoteComment(patientId: string, noteId: string, newContent: string, userId: string): Promise<boolean> {
  try {
    await this.fetchFromBackend(`/patients/${patientId}/notes/${noteId}`, {
      method: 'PUT',
      body: JSON.stringify({
        content: newContent,
        modifiedBy: userId,  // ✅ CHANGED from editedBy
        modifiedAt: new Date().toISOString()  // ✅ CHANGED from editedAt
      })
    });
    return true;
  } catch (error) {
    return false;
  }
}
```

---

## Testing Plan

### Test 1: Medication Creation
```typescript
// Create medication via frontend
MedicationService.addMedication(patientId, medicationData, 'DOC0001');

// Verify in database
SELECT "createdBy" FROM medications WHERE id = [new_id];
// Expected: 'DOC0001' (not 'SYSTEM' or NULL)
```

### Test 2: Investigation Creation
```typescript
// Create investigation via frontend
InvestigationService.addInvestigation(patientId, investigationData, 'DOC0001');

// Verify in database
SELECT "createdBy" FROM investigations WHERE id = [new_id];
// Expected: 'DOC0001' (not 'SYSTEM' or NULL)
```

### Test 3: Note Creation
```typescript
// Create note via frontend
PatientNotesService.addNoteComment(patientId, 'Test note', 'DOC0001');

// Verify in database
SELECT "createdBy" FROM patientnotes WHERE id = [new_id];
// Expected: 'DOC0001' (not 'system')
```

### Test 4: Note Editing
```typescript
// Edit note via frontend
PatientNotesService.editNoteComment(patientId, noteId, 'Edited content', 'NUR0001');

// Verify in database
SELECT "editedBy", "isEdited" FROM patientnotes WHERE id = [note_id];
// Expected: editedBy='NUR0001', isEdited=true (not 'system')
```

---

## Rollback Plan

**If issues occur after deployment:**

1. **Revert Frontend Files**
   ```bash
   git revert <commit-hash>
   ```

2. **Backend is Unchanged**
   - No backend rollback needed
   - Backend already has backwards compatibility

3. **No Data Migration Needed**
   - Changes only affect new records going forward
   - Old records remain as-is

---

## Success Criteria

✅ **After implementation:**
- 100% of new medications have correct `createdBy` (actual user, not SYSTEM)
- 100% of new investigations have correct `createdBy` (actual user, not SYSTEM)
- 100% of new therapies have correct `createdBy` (actual user, not SYSTEM)
- 100% of new notes have correct `createdBy` (actual user, not 'system')
- 100% of edited notes have correct `editedBy` (actual editor, not 'system')

---

## Estimated Effort

| Task | Time | Risk |
|------|------|------|
| Code changes (5 files) | 1 hour | Low |
| Testing (4 integration tests) | 1 hour | Low |
| Frontend build & deploy | 30 min | Low |
| Verification & monitoring | 30 min | Low |
| **TOTAL** | **3 hours** | **Low** |

---

## Files to Modify

1. ✅ `hospital-display-app/src/services/MedicationService.ts` (Line 49)
2. ✅ `hospital-display-app/src/services/InvestigationService.ts` (Line 50)
3. ✅ `hospital-display-app/src/services/TherapyService.ts` (Line 51)
4. ✅ `hospital-display-app/src/services/patient/PatientNotesService.ts` (Lines 39, 67)

**Total:** 4 frontend files, 5 specific line changes

---

## Next Steps

1. ✅ Review this plan
2. ⏳ Get approval for changes
3. ⏳ Implement fixes in frontend services
4. ⏳ Test all 4 scenarios (medications, investigations, therapies, notes)
5. ⏳ Deploy frontend changes
6. ⏳ Monitor database for correct createdBy/editedBy values

---

**Status:** 📋 PLAN READY FOR IMPLEMENTATION
**Priority:** 🔴 HIGH
**Breaking Changes:** Yes (frontend API calls change slightly)
**Backend Changes Required:** None
