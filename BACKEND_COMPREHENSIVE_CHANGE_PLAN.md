# Backend Comprehensive Change Plan - prescribedBy Standardization

## Complete Backend Audit Results

### Files That Need Changes:

1. **`app/repositories/therapy_repository.py`** - Line 45
   - Currently: `'performedBy': therapy_data.get('therapist') or therapy_data.get('performed_by')`
   - Change to: `'prescribedBy': therapy_data.get('therapist') or therapy_data.get('prescribed_by') or therapy_data.get('prescribedBy')`

2. **`app/services/patient_service.py`** - Lines 201-202, 212-213
   - Investigations: Change `performedBy` → `prescribedBy`
   - Therapies: Change `conductedBy` → `prescribedBy`

3. **Database Schema** (via migration script)
   - Rename columns in investigations and therapy tables
   - Drop redundant columns in patientnotes table

### Files That DON'T Need Changes:

✅ **`app/api/v2/investigations.py`** - Generic, passes data through
✅ **`app/api/v2/therapy.py`** - Generic, passes data through
✅ **`app/api/v2/atomic_medical.py`** - Uses `performed_by` parameter name (correct)
✅ **`app/services/investigation_service.py`** - Generic, no hardcoded field names
✅ **`app/services/medical_action_service.py`** - Uses repositories

---

## Detailed Change Plan

### CHANGE 1: Database Migration

**File**: Run `hospital-backend/migrate_prescribedby_standardization.py`

**What it does**:
```sql
-- Investigations table
ALTER TABLE investigations
RENAME COLUMN "performedBy" TO "prescribedBy";

-- Therapy table
ALTER TABLE therapy
RENAME COLUMN "performedBy" TO "prescribedBy";

-- PatientNotes table
ALTER TABLE patientnotes
DROP COLUMN "authorName",
DROP COLUMN "authorRole";
```

**When**: Run FIRST before code changes

---

### CHANGE 2: Therapy Repository

**File**: `hospital-backend/app/repositories/therapy_repository.py`

**Line 45** - Update field name in add_therapy():
```python
# BEFORE:
therapy_record = {
    'patientId': patient_id,
    'type': therapy_data.get('therapy_type') or therapy_data.get('type'),
    'description': therapy_data.get('description'),
    'frequency': therapy_data.get('frequency'),
    'duration': therapy_data.get('duration'),
    'performedBy': therapy_data.get('therapist') or therapy_data.get('performed_by'),  # ← OLD
    'notes': therapy_data.get('notes'),
    'status': 'active'
}

# AFTER:
therapy_record = {
    'patientId': patient_id,
    'type': therapy_data.get('therapy_type') or therapy_data.get('type'),
    'description': therapy_data.get('description'),
    'frequency': therapy_data.get('frequency'),
    'duration': therapy_data.get('duration'),
    'prescribedBy': therapy_data.get('prescribed_by') or therapy_data.get('prescribedBy'),  # ← NEW
    'notes': therapy_data.get('notes'),
    'status': 'active'
}
```

**Explanation**: Frontend now sends `prescribedBy`, database column renamed to `prescribedBy`

---

### CHANGE 3: Patient Service - Staff Name Resolution

**File**: `hospital-backend/app/services/patient_service.py`

**Lines 201-202** - Update investigations staff lookup:
```python
# BEFORE:
if inv.get('performedBy') and inv['performedBy'] in staff_names:
    inv['performedByName'] = staff_names[inv['performedBy']]

# AFTER:
if inv.get('prescribedBy') and inv['prescribedBy'] in staff_names:
    inv['prescribedByName'] = staff_names[inv['prescribedBy']]
```

**Lines 212-213** - Update therapies staff lookup:
```python
# BEFORE:
if therapy.get('conductedBy') and therapy['conductedBy'] in staff_names:
    therapy['conductedByName'] = staff_names[therapy['conductedBy']]

# AFTER:
if therapy.get('prescribedBy') and therapy['prescribedBy'] in staff_names:
    therapy['prescribedByName'] = staff_names[therapy['prescribedBy']]
```

**Explanation**: After database migration, field names change. Staff lookup must use new names.

---

### CHANGE 4: Update Therapy Sessions (Optional - for future)

**File**: `hospital-backend/app/repositories/therapy_repository.py`

**Line 96** - Therapy sessions still use `performedBy` (correct for who executed session):
```python
# NO CHANGE NEEDED - This is correct
# Therapy sessions track who performed the session, not who prescribed the therapy
query = """
    INSERT INTO therapysessions (..., "performedBy", ...)
    VALUES (...)
"""
```

**Explanation**: Therapy sessions' `performedBy` is different from therapy's `prescribedBy`
- Therapy `prescribedBy` = who ordered the therapy (doctor)
- Session `performedBy` = who conducted the session (therapist)

---

## Execution Order

### Step 1: Backup Database ⚠️
```bash
pg_dump hospital_management > backup_before_prescribedby_migration.sql
```

### Step 2: Run Migration
```bash
cd hospital-backend
python migrate_prescribedby_standardization.py
```

**Expected output**:
```
🔄 Starting prescribedBy standardization migration...

1️⃣ Migrating investigations table...
   ✅ investigations.performedBy → prescribedBy

2️⃣ Migrating therapy table...
   ✅ therapy.performedBy → prescribedBy

3️⃣ Migrating patientnotes table...
   ✅ Dropped patientnotes.authorName (will use staff lookup)
   ✅ Dropped patientnotes.authorRole (will use staff lookup)

✅ Migration completed successfully!
```

### Step 3: Update Code Files
1. Edit `app/repositories/therapy_repository.py` line 45
2. Edit `app/services/patient_service.py` lines 201-202, 212-213

### Step 4: Restart Backend
```bash
# Stop current backend
# Start backend server
```

### Step 5: Test Endpoints

**Test Investigation Creation**:
```bash
curl -X POST http://localhost:8001/api/atomic/patients/{patient_id}/investigations \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Complete Blood Count",
    "type": "lab",
    "priority": "routine",
    "prescribedBy": "STAFF001"
  }'
```

**Expected Response**:
```json
{
  "success": true,
  "medical_record": {
    "id": "123",
    "name": "Complete Blood Count",
    "prescribedBy": "STAFF001",
    "prescribedByName": "Dr. John Smith",  // ← Staff lookup worked
    ...
  },
  ...
}
```

**Test Therapy Creation**:
```bash
curl -X POST http://localhost:8001/api/atomic/patients/{patient_id}/therapies \
  -H "Content-Type: application/json" \
  -d '{
    "type": "physiotherapy",
    "description": "Lower back therapy",
    "frequency": "3x per week",
    "duration": "4 weeks",
    "prescribedBy": "STAFF002"
  }'
```

**Expected Response**:
```json
{
  "success": true,
  "medical_record": {
    "id": "456",
    "type": "physiotherapy",
    "prescribedBy": "STAFF002",
    "prescribedByName": "Dr. Jane Doe",  // ← Staff lookup worked
    ...
  },
  ...
}
```

---

## Rollback Plan

If issues occur:

**Step 1: Restore Database**
```bash
psql hospital_management < backup_before_prescribedby_migration.sql
```

**Step 2: Revert Code Changes**
- Git revert the 2 file changes

**Step 3: Restart Backend**

---

## Testing Checklist

After implementation:
- [ ] Migration script runs without errors
- [ ] Database columns renamed correctly
- [ ] PatientNotes columns dropped
- [ ] Backend starts without errors
- [ ] POST investigations with `prescribedBy` works
- [ ] GET investigations returns `prescribedByName`
- [ ] POST therapies with `prescribedBy` works
- [ ] GET therapies returns `prescribedByName`
- [ ] POST notes with only `authorId` works
- [ ] GET notes returns `authorName` and `authorRole`
- [ ] Frontend displays prescriber names (not IDs)
- [ ] No existing data is corrupted

---

## Summary

**Total Files to Change**: 3
1. Database (migration script)
2. `therapy_repository.py` (1 line)
3. `patient_service.py` (4 lines)

**Total Lines of Code**: 5 lines changed

**Risk Level**: Low (simple field renames + migration)

**Estimated Time**: 30 minutes

---

*Created: 2025-10-03*
*Status: Ready for implementation*
