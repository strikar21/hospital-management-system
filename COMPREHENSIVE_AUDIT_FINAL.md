# Comprehensive Field Audit - All Layers
**Date:** 2025-10-05
**Scope:** Database schema, Backend code, Frontend types

---

## Executive Summary

**CRITICAL FINDINGS:**
1. ❌ **2 tables with snake_case columns** (atomic_transactions, medical_operations)
2. ⚠️ **Backend code has 25+ references to old column names** (authorId, administeredAt)
3. ⚠️ **Database state uncertain** - schema file is outdated, doesn't reflect recent migrations

**Database Compliance:**
- ✅ 8 medical tables: 100% compliant (if migrations were applied)
- ❌ 2 operational tables: 0% compliant (snake_case columns)

**Backend Code Compliance:**
- ❌ ~75% compliant (25+ outdated references)

**Frontend Compliance:**
- ✅ 100% compliant

---

## Part 1: Database Schema Issues

### ❌ CRITICAL: Tables with snake_case Columns

#### 1. atomic_transactions (ALL columns snake_case)
```sql
Current Schema:
- id: uuid
- transaction_id: uuid          ❌ Should be: transactionId
- patient_id: text              ❌ Should be: patientId
- operation_type: varchar       ❌ Should be: operationType
- operation_data: jsonb         ❌ Should be: operationData
- status: varchar               ✅ OK
- started_at: timestamptz       ❌ Should be: startedAt
- completed_at: timestamptz     ❌ Should be: completedAt
- error_message: text           ❌ Should be: errorMessage
- retry_count: integer          ❌ Should be: retryCount
```

**Impact:** Used in atomic medical operations
**Files using this table:**
- app/services/medical_action_service.py:749-752 (INSERT)
- app/api/v2/atomic_medical.py:554-558 (SELECT)

#### 2. medical_operations (ALL columns snake_case)
```sql
Current Schema:
- id: uuid
- idempotency_key: varchar      ❌ Should be: idempotencyKey
- operation_type: varchar       ❌ Should be: operationType
- patient_id: text              ❌ Should be: patientId
- result: jsonb                 ✅ OK
- status: varchar               ✅ OK
- created_at: timestamptz       ❌ Should be: createdAt
- completed_at: timestamptz     ❌ Should be: completedAt
```

**Impact:** Used for idempotency tracking
**Files using this table:**
- app/services/medical_action_service.py:717 (SELECT)
- app/services/medical_action_service.py:733-737 (INSERT)

---

### ⚠️ Database State Uncertainty

**Issue:** The file `database_schema_complete.txt` is OUTDATED and doesn't reflect recent migrations.

**Discrepancies found:**

1. **medicationadministrations**
   - Schema file shows: `administeredBy`, `administeredAt`
   - STANDARDIZATION_FIXES_APPLIED.md claims: Changed to `performedBy`, `performedAt`
   - **Status:** UNKNOWN - need to verify actual database

2. **patient_alerts**
   - Schema file shows: `acknowledgedBy`, `acknowledgedAt`
   - REVERTED_CHANGES_AND_FIXES.md claims: Changed to `performedBy`, `performedAt`
   - **Status:** UNKNOWN - need to verify actual database

3. **patientnotes**
   - Schema file shows: `authorId`, `authorName`, `authorRole`
   - STANDARDIZATION_FIXES_APPLIED.md claims: `authorId` → `createdBy`
   - Backend code STILL uses: `authorId` (25 instances)
   - **Status:** INCONSISTENT

4. **casesheetentries**
   - Schema file shows: Table exists
   - STANDARDIZATION_FIXES_APPLIED.md claims: Table DROPPED
   - **Status:** UNKNOWN

5. **therapies**
   - Schema file shows: Table named `therapies`
   - STANDARDIZATION_FIXES_APPLIED.md claims: Renamed to `therapies_legacy`
   - **Status:** UNKNOWN

---

## Part 2: Backend Code Issues

### ❌ authorId References (Should be createdBy)

**Total instances:** 24 in active code + utilities

#### CRITICAL Files (Must Fix):

**1. app/core/database.py:362**
```python
"authorId" TEXT NOT NULL,  ❌ Should be: "createdBy"
```
**Impact:** Schema creation uses wrong column name

**2. app/repositories/patient_repository.py**
- Line 124: `INSERT INTO patientnotes ("patientId", content, "authorId")`
- Line 126: `RETURNING id, "patientId", content, "authorId", timestamp...`

**3. app/api/v2/patients.py:164**
```python
author_id=note_data.get('authorId', 'system')  ❌ Should be: 'createdBy'
```

**4. app/api/v1/patients.py**
- Line 314: `LEFT JOIN staff s ON pn.authorId = s.id`
- Line 1119: `keys = ['id', 'patientid', 'content', 'authorId', ...]`
- Line 1140: `"authorId": created_by,`
- Line 1154: `"authorId": created_by,`

**5. app/services/medical_action_service.py:314**
```python
'authorId': performed_by  ❌ Should be: 'createdBy': performed_by
```

**6. app/services/patient_service.py (14 instances)**
- Lines 139-140: Check and add `med['authorId']` to staff_ids
- Lines 150-151: Check and add `inv['authorId']` to staff_ids
- Lines 166-167: Check and add `note['authorId']` to staff_ids
- Lines 188-189: Resolve `med['authorId']` to `med['authorName']`
- Lines 199-200: Resolve `inv['authorId']` to `inv['authorName']`
- Lines 210-211: Resolve `therapy['authorId']` to `therapy['authorName']`
- Lines 219-220: Resolve `note['authorId']` to `note['authorName']`
- Line 351: Check `note.get('authorId') == user_id`

#### Utility Files (Can ignore - one-time scripts):
- populate_database.py (3 instances)
- update_medical_records.py (11 instances)
- migrate_prescribedby_standardization.py (1 instance)

---

### ❌ administeredAt Reference (Should be performedAt)

**1. app/services/medical_action_service.py:676**
```python
timestamp = medical_record.get('administeredAt', '')  ❌ Should be: 'performedAt'
```

**2. database_schema_complete.txt:187** (file is outdated)
```
- administeredAt: timestamp with time zone NULL  ❌ Should be: performedAt
```

---

### ⚠️ acknowledgedBy/acknowledgedAt References

**Found in utility/test files only:**
- add_sample_alerts.py
- create_patient_alerts_table.py
- test_alert_query.py
- init-scripts/02-init-timescale-database.sql

**Status:** These are old setup scripts, can be ignored or updated

---

## Part 3: SQL Query Analysis

### Snake_case in Actual SQL Queries:

**1. atomic_transactions table queries:**

**app/services/medical_action_service.py:749-752**
```sql
INSERT INTO atomic_transactions (
    transaction_id,    ❌ snake_case
    patient_id,        ❌ snake_case
    operation_type,    ❌ snake_case
    operation_data,    ❌ snake_case
    status
) VALUES ($1, $2, $3, $4, 'in_progress')
```

**app/api/v2/atomic_medical.py:554-557**
```sql
SELECT transaction_id, patient_id, operation_type, status,
       started_at, completed_at, error_message
FROM atomic_transactions
WHERE transaction_id = $1 AND patient_id = $2
```

**2. medical_operations table queries:**

**app/services/medical_action_service.py:717**
```sql
SELECT result FROM medical_operations
WHERE idempotency_key = $1 AND status = 'completed'
```

**app/services/medical_action_service.py:733-735**
```sql
INSERT INTO medical_operations (
    idempotency_key,   ❌ snake_case
    operation_type,    ❌ snake_case
    patient_id,        ❌ snake_case
    result, status, completed_at
) VALUES ($1, $2, $3, $4, 'completed', NOW())
```

---

## Part 4: Compliance Summary

### Database Layer:

| Table | Compliance | Issues |
|-------|-----------|--------|
| atomic_transactions | ❌ 0% | All columns snake_case (8 fields) |
| medical_operations | ❌ 0% | All columns snake_case (5 fields) |
| medicationadministrations | ⚠️ Unknown | May have administeredBy/At or performedBy/At |
| patient_alerts | ⚠️ Unknown | May have acknowledgedBy/At or performedBy/At |
| patientnotes | ⚠️ Unknown | May have authorId or createdBy |
| medications | ✅ 100% | All camelCase |
| investigations | ✅ 100% | All camelCase |
| therapy | ✅ 100% | All camelCase |
| therapysessions | ✅ 100% | All camelCase |
| caseEntries | ✅ 100% | All camelCase |

### Backend Code Layer:

| Issue | Count | Severity |
|-------|-------|----------|
| authorId references (should be createdBy) | 24 | 🔴 HIGH |
| administeredAt references (should be performedAt) | 1 | 🟡 MEDIUM |
| snake_case SQL columns | 13 | 🔴 CRITICAL |

### Frontend Layer:
- ✅ **100% Compliant** - All types use camelCase

---

## Part 5: Recommended Fix Plan

### Phase 1: Verify Current Database State ⚠️ CRITICAL FIRST STEP

**Action:** Connect to database and get actual schema for:
1. medicationadministrations
2. patient_alerts
3. patientnotes
4. Check if casesheetentries exists
5. Check if therapies or therapies_legacy exists

**Why:** Previous migrations may or may not have been applied. We need ground truth.

---

### Phase 2: Fix Database Schema (snake_case tables)

#### Option A: Rename Columns (Recommended)
```sql
-- Fix atomic_transactions
ALTER TABLE atomic_transactions
  RENAME COLUMN transaction_id TO "transactionId";
ALTER TABLE atomic_transactions
  RENAME COLUMN patient_id TO "patientId";
ALTER TABLE atomic_transactions
  RENAME COLUMN operation_type TO "operationType";
ALTER TABLE atomic_transactions
  RENAME COLUMN operation_data TO "operationData";
ALTER TABLE atomic_transactions
  RENAME COLUMN started_at TO "startedAt";
ALTER TABLE atomic_transactions
  RENAME COLUMN completed_at TO "completedAt";
ALTER TABLE atomic_transactions
  RENAME COLUMN error_message TO "errorMessage";
ALTER TABLE atomic_transactions
  RENAME COLUMN retry_count TO "retryCount";

-- Fix medical_operations
ALTER TABLE medical_operations
  RENAME COLUMN idempotency_key TO "idempotencyKey";
ALTER TABLE medical_operations
  RENAME COLUMN operation_type TO "operationType";
ALTER TABLE medical_operations
  RENAME COLUMN patient_id TO "patientId";
ALTER TABLE medical_operations
  RENAME COLUMN created_at TO "createdAt";
ALTER TABLE medical_operations
  RENAME COLUMN completed_at TO "completedAt";
```

#### Option B: Leave As-Is (NOT Recommended)
- Keep snake_case for operational tables
- Violates camelCase standard
- Creates inconsistency

---

### Phase 3: Fix Backend Code

#### 3A: Fix authorId → createdBy (24 instances)

**Files to update:**
1. ✅ app/core/database.py:362
2. ✅ app/repositories/patient_repository.py:124, 126
3. ✅ app/api/v2/patients.py:164
4. ✅ app/api/v1/patients.py:314, 1119, 1140, 1154
5. ✅ app/services/medical_action_service.py:314
6. ✅ app/services/patient_service.py (14 instances)

#### 3B: Fix administeredAt → performedAt (1 instance)

**File to update:**
- ✅ app/services/medical_action_service.py:676

#### 3C: Fix SQL Queries (13 snake_case column references)

**Files to update:**
1. ✅ app/services/medical_action_service.py:749-752 (atomic_transactions INSERT)
2. ✅ app/services/medical_action_service.py:717 (medical_operations SELECT)
3. ✅ app/services/medical_action_service.py:733-737 (medical_operations INSERT)
4. ✅ app/api/v2/atomic_medical.py:554-558 (atomic_transactions SELECT)

---

### Phase 4: Verification

After all fixes:
1. ✅ Update database_schema_complete.txt with actual current schema
2. ✅ Run backend tests
3. ✅ Test all CRUD operations for medical records
4. ✅ Verify frontend works correctly
5. ✅ Run comprehensive audit again

---

## Part 6: Risk Assessment

### High Risk:
1. ❌ **atomic_transactions and medical_operations schema changes** - Used in critical atomic operations
2. ❌ **authorId → createdBy changes** - 24 instances, high chance of missing one

### Medium Risk:
1. ⚠️ **Unknown database state** - Migrations may be partially applied
2. ⚠️ **administeredAt reference** - Only 1 instance but in timestamp logic

### Low Risk:
1. ✅ **Utility script references** - Not used in production

---

## Conclusion

**Current State:** ~75% compliant across all layers

**To achieve 100% compliance:**
1. Verify current database state (CRITICAL)
2. Fix 2 tables with snake_case columns (13 columns total)
3. Fix 25 backend code references
4. Update schema documentation

**Estimated effort:** 2-3 hours for all fixes + testing

**Recommended approach:** Fix in order (Phase 1 → Phase 4) with verification at each step
