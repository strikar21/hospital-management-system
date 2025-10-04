# Backend Implementation Guide - prescribedBy Standardization

## Overview
Frontend has been updated to use `prescribedBy` pattern. Backend needs to be updated to match.

## Database Migration

### Run Migration Script:
```bash
cd hospital-backend
python migrate_prescribedby_standardization.py
```

### What It Does:
1. Renames `investigations.performedBy` → `investigations.prescribedBy`
2. Renames `therapy.performedBy` → `therapy.prescribedBy`
3. Drops `patientnotes.authorName` column (redundant - will lookup from staff table)
4. Drops `patientnotes.authorRole` column (redundant - will lookup from staff table)

---

## Backend API Changes Needed

### 1. Investigations API

**Files to modify:**
- `app/api/v2/investigations.py`
- `app/services/investigation_service.py`
- `app/repositories/patient_repository.py` (if investigation queries are here)

**Changes:**
- Accept `prescribedBy` field in POST `/atomic/patients/{id}/investigations`
- Store `prescribedBy` in database (column already renamed by migration)
- When returning investigations, JOIN with staff table to get prescriber name
- Return both `prescribedBy` (staffId) and `prescribedByName` (from staff.firstName + staff.lastName)

**Example Response:**
```json
{
  "id": "123",
  "name": "Complete Blood Count",
  "type": "lab",
  "prescribedBy": "STAFF001",
  "prescribedByName": "Dr. John Smith",
  "status": "pending",
  ...
}
```

---

### 2. Therapy API

**Files to modify:**
- `app/api/v2/therapy.py`
- `app/services/therapy_service.py`
- `app/repositories/therapy_repository.py`

**Changes:**
- Accept `prescribedBy` field in POST `/atomic/patients/{id}/therapies`
- Store `prescribedBy` in database (column already renamed by migration)
- When returning therapies, JOIN with staff table to get prescriber name
- Return both `prescribedBy` (staffId) and `prescribedByName` (from staff.firstName + staff.lastName)

**Example Response:**
```json
{
  "id": "456",
  "description": "Physical Therapy for Lower Back",
  "type": "physiotherapy",
  "prescribedBy": "STAFF002",
  "prescribedByName": "Dr. Jane Doe",
  "status": "active",
  ...
}
```

---

### 3. Patient Notes API

**Files to modify:**
- `app/api/v1/patients.py` or `app/api/v2/patients.py` (notes endpoints)
- Any service handling patient notes

**Changes:**
- Accept ONLY `authorId` field in POST `/patients/{id}/notes` (frontend already updated)
- Do NOT expect `authorName` or `authorRole` (columns dropped by migration)
- When returning notes, JOIN with staff table to get author details
- Return `authorId`, `authorName` (from staff.firstName + staff.lastName), and `authorRole` (from staff.role)

**Example Request (from frontend):**
```json
{
  "content": "Patient improving well",
  "authorId": "STAFF003"
}
```

**Example Response:**
```json
{
  "id": "789",
  "content": "Patient improving well",
  "authorId": "STAFF003",
  "authorName": "Nurse Sarah Johnson",
  "authorRole": "Nurse",
  "timestamp": "2025-10-03T10:30:00Z",
  ...
}
```

---

## SQL Query Examples

### Investigations with Staff Lookup:
```sql
SELECT
    i.*,
    CONCAT(s."firstName", ' ', s."lastName") as "prescribedByName"
FROM investigations i
LEFT JOIN staff s ON i."prescribedBy" = s.id
WHERE i."patientId" = $1
ORDER BY i."createdAt" DESC;
```

### Therapies with Staff Lookup:
```sql
SELECT
    t.*,
    CONCAT(s."firstName", ' ', s."lastName") as "prescribedByName"
FROM therapy t
LEFT JOIN staff s ON t."prescribedBy" = s.id
WHERE t."patientId" = $1
ORDER BY t."createdAt" DESC;
```

### Notes with Staff Lookup:
```sql
SELECT
    n.*,
    CONCAT(s."firstName", ' ', s."lastName") as "authorName",
    s.role as "authorRole"
FROM patientnotes n
LEFT JOIN staff s ON n."authorId" = s.id
WHERE n."patientId" = $1
ORDER BY n.timestamp DESC;
```

---

## Validation

### Before Storing:
- Verify that `prescribedBy` / `authorId` exists in staff table
- Return error if staff ID not found
- Ensure staff is active (`isActive = true`)

### When Returning:
- Always include name fields from staff lookup
- Handle case where staff might be deleted (show ID as fallback)

---

## Testing Checklist

### After Implementation:
- [ ] Run migration script successfully
- [ ] Investigations POST accepts `prescribedBy`
- [ ] Investigations GET returns `prescribedByName`
- [ ] Therapies POST accepts `prescribedBy`
- [ ] Therapies GET returns `prescribedByName`
- [ ] Notes POST accepts only `authorId` (rejects `authorName`/`authorRole`)
- [ ] Notes GET returns `authorName` and `authorRole` via staff lookup
- [ ] All endpoints validate staff IDs exist
- [ ] Test with real patient data
- [ ] Verify frontend displays prescriber names correctly

---

## Rollback Plan

If issues occur, rollback migration:

```sql
-- Rollback investigations
ALTER TABLE investigations
RENAME COLUMN "prescribedBy" TO "performedBy";

-- Rollback therapy
ALTER TABLE therapy
RENAME COLUMN "prescribedBy" TO "performedBy";

-- Restore patientnotes columns (data will be lost!)
ALTER TABLE patientnotes
ADD COLUMN "authorName" TEXT,
ADD COLUMN "authorRole" TEXT;
```

**Note**: Restoring patientnotes columns won't restore data - only structure.

---

## Files Modified (Frontend - Already Done):
✅ `hospital-display-app/src/types/MedicalTypes.ts`
✅ `hospital-display-app/src/components/PatientInvestigations.tsx`
✅ `hospital-display-app/src/components/PatientTherapies.tsx`
✅ `hospital-display-app/src/hooks/usePatientInvestigations.ts`
✅ `hospital-display-app/src/hooks/usePatientTherapies.ts`
✅ `hospital-display-app/src/services/patient/PatientNotesService.ts`
✅ `hospital-display-app/src/components/PatientNotes/NotesEditor.tsx`

## Files to Modify (Backend - TODO):
❌ Database migration (script ready: `migrate_prescribedby_standardization.py`)
❌ `app/services/patient_service.py` - **CRITICAL: Update staff name resolution**

### Specific Changes in patient_service.py:

**Lines 201-202** - Change investigations staff lookup:
```python
# OLD:
if inv.get('performedBy') and inv['performedBy'] in staff_names:
    inv['performedByName'] = staff_names[inv['performedBy']]

# NEW:
if inv.get('prescribedBy') and inv['prescribedBy'] in staff_names:
    inv['prescribedByName'] = staff_names[inv['prescribedBy']]
```

**Lines 212-213** - Change therapies staff lookup:
```python
# OLD:
if therapy.get('conductedBy') and therapy['conductedBy'] in staff_names:
    therapy['conductedByName'] = staff_names[therapy['conductedBy']]

# NEW:
if therapy.get('prescribedBy') and therapy['prescribedBy'] in staff_names:
    therapy['prescribedByName'] = staff_names[therapy['prescribedBy']]
```

**Notes (lines 223-224)** - Already correct! ✅
```python
if note.get('authorId') and note['authorId'] in staff_names:
    note['authorName'] = staff_names[note['authorId']]
```

The backend already has staff lookup infrastructure via `get_staff_names()` - just needs field name updates!

---

*Created: 2025-10-03*
*Frontend Status: ✅ Complete*
*Backend Status: ⏳ Pending Implementation*
