# Day 1 Testing Guide - Foreign Key Constraints

## What Was Implemented

### ✅ Backend Changes
1. **Migration File Created:** `hospital-backend/migrations/001_add_foreign_keys_medications.sql`
   - Adds FK constraint: medications.patientId → patients.id (CASCADE)
   - Adds FK constraint: medications.prescribedBy → staff.id (RESTRICT)
   - Adds FK constraint: medications.createdBy → staff.id (SET NULL)

2. **Rollback Script Created:** `hospital-backend/migrations/001_rollback.sql`
   - Removes all FK constraints if needed

3. **Backend Service Updated:** `hospital-backend/app/services/medication_service.py`
   - Added comprehensive FK violation error handling
   - Specific error messages for each FK constraint
   - Proper logging of all violations

### ✅ Frontend Changes
1. **Hook Updated:** `hospital-display-app/src/hooks/usePatientMedications.ts`
   - Enhanced error handling in `handleAddMedication`
   - User-friendly error messages for FK violations
   - Specific alerts for patient not found, prescriber not found, etc.

---

## How to Test

### Step 1: Apply the Migration

```bash
# Navigate to backend directory
cd hospital-backend

# Connect to your PostgreSQL database
psql -U postgres -d hospital_management

# Apply the migration
\i migrations/001_add_foreign_keys_medications.sql

# Verify constraints were added
\d medications

# Expected output should show:
# Foreign-key constraints:
#     "fk_medications_patient" FOREIGN KEY ("patientId") REFERENCES patients(id) ON DELETE CASCADE
#     "fk_medications_prescriber" FOREIGN KEY ("prescribedBy") REFERENCES staff(id) ON DELETE RESTRICT
#     "fk_medications_creator" FOREIGN KEY ("createdBy") REFERENCES staff(id) ON DELETE SET NULL
```

### Step 2: Test FK Constraints Work

#### Test 2.1: Try to Create Medication for Non-Existent Patient

```sql
-- This should FAIL with FK violation
INSERT INTO medications ("patientId", name, dosage, frequency, route, status, "prescribedBy", "createdBy", "createdAt", "updatedAt")
VALUES ('INVALID_PATIENT_ID', 'Aspirin', '500mg', 'BID', 'PO', 'active', 'DOC001', 'DOC001', NOW(), NOW());

-- Expected error:
-- ERROR: insert or update on table "medications" violates foreign key constraint "fk_medications_patient"
-- DETAIL: Key (patientId)=(INVALID_PATIENT_ID) is not present in table "patients".
```

#### Test 2.2: Try to Create Medication with Invalid Prescriber

```sql
-- First, get a valid patient ID
SELECT id FROM patients LIMIT 1;
-- Example: PAT001

-- Now try with invalid prescriber - should FAIL
INSERT INTO medications ("patientId", name, dosage, frequency, route, status, "prescribedBy", "createdBy", "createdAt", "updatedAt")
VALUES ('PAT001', 'Aspirin', '500mg', 'BID', 'PO', 'active', 'INVALID_STAFF', 'DOC001', NOW(), NOW());

-- Expected error:
-- ERROR: insert or update on table "medications" violates foreign key constraint "fk_medications_prescriber"
```

#### Test 2.3: Test CASCADE Delete

```sql
-- Create a test patient and medication
INSERT INTO patients (id, "firstName", "lastName", "dateOfBirth", gender, status, "createdAt", "updatedAt")
VALUES ('TEST_PATIENT_123', 'Test', 'Patient', '1990-01-01', 'M', 'active', NOW(), NOW());

-- Get a valid staff ID
SELECT id FROM staff LIMIT 1;
-- Example: STAFF001

-- Create medication for test patient
INSERT INTO medications ("patientId", name, dosage, frequency, route, status, "prescribedBy", "createdBy", "createdAt", "updatedAt")
VALUES ('TEST_PATIENT_123', 'Test Med', '100mg', 'QD', 'PO', 'active', 'STAFF001', 'STAFF001', NOW(), NOW());

-- Verify medication exists
SELECT * FROM medications WHERE "patientId" = 'TEST_PATIENT_123';

-- Delete the patient - medication should CASCADE delete
DELETE FROM patients WHERE id = 'TEST_PATIENT_123';

-- Verify medication was deleted
SELECT * FROM medications WHERE "patientId" = 'TEST_PATIENT_123';
-- Should return 0 rows
```

#### Test 2.4: Test RESTRICT Delete

```sql
-- Try to delete a staff member who prescribed medications
SELECT "prescribedBy", COUNT(*)
FROM medications
WHERE "prescribedBy" IS NOT NULL
GROUP BY "prescribedBy"
LIMIT 1;
-- Example: DOC001 has 5 medications

-- Try to delete this staff - should FAIL
DELETE FROM staff WHERE id = 'DOC001';

-- Expected error:
-- ERROR: update or delete on table "staff" violates foreign key constraint "fk_medications_prescriber" on table "medications"
-- DETAIL: Key (id)=(DOC001) is still referenced from table "medications".
```

### Step 3: Test Backend Service Error Handling

```bash
# Start the backend server
cd hospital-backend
source venv/Scripts/activate  # Windows
# or: source venv/bin/activate  # Mac/Linux
python main.py

# In another terminal, test with curl:

# Test 1: Invalid patient ID
curl -X POST http://localhost:8001/api/v2/patients/INVALID_ID/medications \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Aspirin",
    "dosage": "500mg",
    "frequency": "BID",
    "route": "PO",
    "prescribedBy": "DOC001"
  }'

# Expected response:
# {
#   "detail": "Patient INVALID_ID not found. Cannot create medication for non-existent patient."
# }

# Test 2: Invalid prescriber
curl -X POST http://localhost:8001/api/v2/patients/PAT001/medications \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Aspirin",
    "dosage": "500mg",
    "frequency": "BID",
    "route": "PO",
    "prescribedBy": "INVALID_STAFF"
  }'

# Expected response:
# {
#   "detail": "Prescriber INVALID_STAFF not found in staff directory. Please verify the staff ID."
# }
```

### Step 4: Test Frontend Error Messages

1. **Start both backend and frontend:**
```bash
# Terminal 1 - Backend
cd hospital-backend
source venv/Scripts/activate
python main.py

# Terminal 2 - Frontend
cd hospital-display-app
npm start
```

2. **Test in browser:**
   - Open http://localhost:3000
   - Navigate to a patient detail page
   - Click "Add Medication"
   - Fill in medication details but use invalid data:
     - Either delete the patient in another tab while adding medication
     - Or modify the prescribedBy field to an invalid staff ID (via dev tools)
   - Submit the form

3. **Expected Results:**
   - ❌ Error alert appears with specific message
   - If patient not found: "❌ Error: Patient not found. The patient may have been discharged..."
   - If prescriber not found: "❌ Error: Prescriber not found in staff directory..."
   - Error is logged to console
   - Form does not clear (user can retry)

### Step 5: Verify All Changes

```bash
# Check database constraints
psql -U postgres -d hospital_management
\d medications

# Should show 3 foreign key constraints

# Check backend service has error handling
grep -n "ForeignKeyViolationError" hospital-backend/app/services/medication_service.py
# Should show line numbers with FK handling

# Check frontend has error handling
grep -n "Prescriber.*not found" hospital-display-app/src/hooks/usePatientMedications.ts
# Should show line numbers with error messages
```

---

## Rollback Procedure (If Needed)

If you encounter issues and need to rollback:

```bash
# Connect to database
psql -U postgres -d hospital_management

# Run rollback script
\i migrations/001_rollback.sql

# Verify constraints removed
\d medications
# Should NOT show the FK constraints
```

---

## Success Criteria

After testing, verify:
- [ ] Migration runs successfully without errors
- [ ] `\d medications` shows 3 FK constraints
- [ ] Cannot insert medication with invalid patientId (FK violation error)
- [ ] Cannot insert medication with invalid prescribedBy (FK violation error)
- [ ] Deleting patient CASCADE deletes their medications
- [ ] Cannot delete staff who prescribed medications (RESTRICT error)
- [ ] Backend service catches FK violations and returns meaningful errors
- [ ] Frontend displays user-friendly error messages
- [ ] Console logs show detailed error information
- [ ] Rollback script successfully removes constraints

---

## Next Steps

Once Day 1 testing is complete and all criteria pass:
1. Mark Day 1 as complete ✅
2. Proceed to Day 2: Add FK constraints to investigations, therapy, and casesheetentries tables
3. Document any issues found during testing

---

## Troubleshooting

### Issue: Migration fails with "constraint already exists"
**Solution:** Constraints may already exist. Drop them first:
```sql
ALTER TABLE medications DROP CONSTRAINT IF EXISTS fk_medications_patient;
ALTER TABLE medications DROP CONSTRAINT IF EXISTS fk_medications_prescriber;
ALTER TABLE medications DROP CONSTRAINT IF EXISTS fk_medications_creator;
```

### Issue: Migration fails with "referenced table not found"
**Solution:** Ensure patients and staff tables exist:
```sql
SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename IN ('patients', 'staff', 'medications');
```

### Issue: Backend not catching FK violations
**Solution:** Verify asyncpg is imported:
```python
import asyncpg
# Make sure asyncpg.exceptions.ForeignKeyViolationError is used
```

### Issue: Frontend error messages not showing
**Solution:** Check that error.response.data structure matches:
```javascript
console.log('Full error object:', error);
console.log('Error response:', error?.response?.data);
```

---

**Testing Date:** 2025-10-05
**Status:** Ready for Testing ✅
**Next Review:** After all tests pass
