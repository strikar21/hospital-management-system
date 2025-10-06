# Deep Standardization Audit Report
**Date:** 2025-10-05
**Scope:** Database schema, Backend queries, Frontend types

## Executive Summary

**CRITICAL ISSUES FOUND:** 5 major naming mismatches between database schema and backend/frontend code.

**Status:** ❌ NOT STREAMLINED - Multiple tables have non-standard column names that don't match backend code

---

## Standardization Target

All medical action tables should use the **3-field staff tracking system:**

1. **prescribedBy** - Who ordered/prescribed the action
2. **performedBy** - Who performed/acknowledged the action
3. **createdBy** - Who created the database record

All timestamp fields should use camelCase: `createdAt`, `updatedAt`, `performedAt`, etc.

---

## Database Schema Audit

### ✅ COMPLIANT TABLES

#### 1. patient_alerts
- ✅ `performedBy` (VARCHAR) - was `acknowledgedBy`, migrated
- ✅ `performedAt` (TIMESTAMPTZ) - was `acknowledgedAt`, migrated
- ✅ `resolvedBy` (VARCHAR)
- ✅ `resolvedAt` (TIMESTAMPTZ)
- ✅ `createdAt` (TIMESTAMPTZ)

#### 2. therapysessions
- ✅ `performedBy` (TEXT)
- ✅ `createdAt` (TIMESTAMPTZ)
- ✅ `updatedAt` (TIMESTAMPTZ)

#### 3. caseEntries (PascalCase quoted table)
- ✅ `createdBy` (TEXT) - backend aliases to `performedBy` in SELECT queries
- ✅ `createdAt` (TIMESTAMPTZ)
- ✅ `updatedAt` (TIMESTAMPTZ)
- ✅ `timestamp` (TIMESTAMPTZ)

#### 4. casesheetentries (lowercase table)
- ✅ `performedBy` (TEXT)
- ✅ `createdAt` (TIMESTAMPTZ)
- ⚠️ **NOTE:** This table has 0 rows - `caseEntries` has 58 rows
- ⚠️ **DUPLICATE TABLE ISSUE** - Two case entry tables exist

---

### ❌ NON-COMPLIANT TABLES

#### 1. medicationadministrations ❌ CRITICAL
**Database has:**
- ❌ `administeredBy` (VARCHAR) - should be `performedBy`
- ❌ `administeredAt` (TIMESTAMPTZ) - should be `performedAt`

**Backend code expects (medical_action_service.py:356-357):**
```python
'performedAt': administered_at,
'performedBy': performed_by,
```

**Frontend type expects (MedicalTypes.ts:39-40):**
```typescript
performedAt: string;
performedBy: string;
```

**Impact:** ❌ INSERT operations will FAIL - columns don't exist!

---

#### 2. medications ⚠️ MISSING COLUMNS
**Database has:**
- ✅ `prescribedBy` (TEXT)
- ✅ `createdAt` (TIMESTAMPTZ)
- ❌ **MISSING** `performedBy` - No way to track who administered medication
- ❌ **MISSING** `performedAt` - No way to track when administered

**Note:** Administration tracking is in separate `medicationadministrations` table

---

#### 3. therapy ⚠️ MISSING COLUMNS
**Database has:**
- ✅ `prescribedBy` (TEXT)
- ✅ `createdAt` (TIMESTAMPTZ)
- ✅ `updatedAt` (TIMESTAMPTZ)
- ❌ **MISSING** `performedBy` - Who performed therapy?

**Note:** Performance tracking is in separate `therapysessions` table

---

#### 4. therapies (duplicate table) ⚠️ WRONG COLUMN NAMES
**Database has:**
- ❌ `createdBy` (TEXT) - used for therapy prescription, should be `prescribedBy`
- ✅ `createdAt` (TIMESTAMPTZ)
- ✅ `updatedAt` (TIMESTAMPTZ)

**Issues:**
1. Duplicate of `therapy` table (12 rows vs 5 rows)
2. Using `createdBy` instead of `prescribedBy`
3. Backend uses `therapy` table, not this one

---

#### 5. investigations ⚠️ MISSING COLUMNS
**Database has:**
- ✅ `prescribedBy` (TEXT)
- ✅ `createdAt` (TIMESTAMPTZ)
- ✅ `updatedAt` (TIMESTAMPTZ)
- ❌ **MISSING** `performedBy` - Who performed the investigation?
- ❌ **MISSING** `performedAt` - When was it performed?

**Frontend type expects (MedicalTypes.ts:70-71):**
```typescript
performedBy?: string;
performedByName?: string;
```

---

#### 6. patientnotes ⚠️ NON-STANDARD COLUMN
**Database has:**
- ❌ `authorId` (TEXT) - should be `createdBy` for consistency
- ✅ `timestamp` (TIMESTAMPTZ)

**Backend aliases in query (patient_repository.py:392):**
```python
pn."authorId" as "performedBy"
```

---

## Backend Code Audit

### Critical Code-Database Mismatches

#### 1. medical_action_service.py:356-357
```python
# TRYING TO INSERT performedBy/performedAt into medicationadministrations
'performedAt': administered_at,
'performedBy': performed_by,
# But table has administeredBy/administeredAt!
```
**Status:** ❌ WILL FAIL ON INSERT

#### 2. patient_repository.py:392-417
```python
# Using aliasing to map database columns to standardized names
pn."authorId" as "performedBy"  # patientnotes
c."createdBy" as "performedBy"  # caseEntries
```
**Status:** ✅ Works for SELECT, but inconsistent schema

---

## Frontend Type Audit

### Frontend Expectations (MedicalTypes.ts)

#### medicationAdministration (lines 34-46)
```typescript
performedAt: string;     // ✅ Expected
performedBy: string;     // ✅ Expected
performedByName?: string; // ✅ Expected
```

#### investigation (lines 58-76)
```typescript
prescribedBy: string;     // ✅ Has in DB
performedBy?: string;     // ❌ Missing in DB
performedByName?: string; // ❌ Can't resolve, missing performedBy
```

#### therapy (lines 78-95)
```typescript
prescribedBy: string;     // ✅ Has in DB
prescribedByName?: string; // ✅ Can resolve via JOIN
```

#### therapySession (lines 97-110)
```typescript
performedBy?: string;     // ✅ Has in therapysessions table
performedByName?: string; // ✅ Can resolve via JOIN
```

---

## Duplicate Table Issues

### Issue 1: Case Entry Tables
**Two tables exist:**
1. `caseEntries` (PascalCase, quoted) - 58 rows ✅ USED
2. `casesheetentries` (lowercase) - 0 rows ❌ UNUSED

**Recommendation:** Drop `casesheetentries`, keep `caseEntries`

### Issue 2: Therapy Tables
**Two tables exist:**
1. `therapy` (singular) - 5 rows ✅ USED by backend
2. `therapies` (plural) - 12 rows ⚠️ PARTIALLY USED

**Data split between tables - needs consolidation!**

---

## Critical Fixes Required

### Priority 1: Fix medicationadministrations (BLOCKING)
**Impact:** INSERT operations are currently failing!

```sql
ALTER TABLE medicationadministrations
  RENAME COLUMN "administeredBy" TO "performedBy";

ALTER TABLE medicationadministrations
  RENAME COLUMN "administeredAt" TO "performedAt";
```

### Priority 2: Add missing performedBy columns
**Impact:** Cannot track who performed actions

```sql
-- investigations table
ALTER TABLE investigations
  ADD COLUMN "performedBy" TEXT,
  ADD COLUMN "performedAt" TIMESTAMPTZ;

-- medications table (if needed for direct tracking)
ALTER TABLE medications
  ADD COLUMN "performedBy" TEXT,
  ADD COLUMN "performedAt" TIMESTAMPTZ;

-- therapy table (if needed for direct tracking)
ALTER TABLE therapy
  ADD COLUMN "performedBy" TEXT,
  ADD COLUMN "performedAt" TIMESTAMPTZ;
```

### Priority 3: Standardize patientnotes
```sql
ALTER TABLE patientnotes
  RENAME COLUMN "authorId" TO "createdBy";
```

### Priority 4: Consolidate duplicate tables

**Option A: Merge therapies into therapy**
```sql
-- Migrate data from therapies to therapy
INSERT INTO therapy (id, "patientId", type, description, ...)
SELECT id, "patientId", "therapyType" as type, description, ...
FROM therapies
WHERE id NOT IN (SELECT id FROM therapy);

-- Drop duplicate table
DROP TABLE therapies;
```

**Option B: Drop unused casesheetentries**
```sql
DROP TABLE casesheetentries;
```

---

## Summary of Issues

| Table | Issue | Severity | Impact |
|-------|-------|----------|--------|
| medicationadministrations | administeredBy/At instead of performedBy/At | 🔴 CRITICAL | INSERT failures |
| investigations | Missing performedBy/At columns | 🟡 HIGH | Can't track performer |
| medications | Missing performedBy/At columns | 🟡 MEDIUM | Using separate admin table |
| therapy | Missing performedBy/At columns | 🟡 MEDIUM | Using separate sessions table |
| patientnotes | authorId instead of createdBy | 🟡 LOW | Backend uses aliasing |
| therapies | Duplicate table with wrong schema | 🟡 MEDIUM | Data split |
| casesheetentries | Duplicate unused table | 🟢 LOW | 0 rows, safe to drop |

---

## Compliance Status

**Overall Compliance:** ❌ **40% COMPLIANT**

- ✅ 4 tables fully compliant
- ⚠️ 6 tables non-compliant
- 🔴 1 critical blocker (medicationadministrations)
- ⚠️ 2 duplicate table issues

**Recommendation:** Execute Priority 1 fix IMMEDIATELY to prevent INSERT failures.
