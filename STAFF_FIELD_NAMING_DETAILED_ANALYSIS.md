d# Staff Field Naming - Detailed Analysis & Inconsistencies

**Date:** 2025-10-04
**Issue:** Inconsistent staff ID field naming across database, backend, and frontend
**Impact:** HIGH - Confusing for developers, harder queries, inconsistent data model

---

## 📊 Current Situation: CHAOS

You have **7 DIFFERENT field names** for staff IDs across your system:

| Field Name | Usage | Meaning |
|------------|-------|---------|
| `prescribedBy` | Medications, Investigations, Therapies | Who prescribed/ordered |
| `performedBy` | Therapy Sessions, Case Sheet Entries, Alerts | Who performed action |
| `conductedBy` | Therapies (alternative) | Who conducted therapy |
| `authorId` | Patient Notes | Who authored note |
| `createdBy` | Generic | Who created record |
| `modifiedBy` | Generic updates | Who last modified |
| `editedBy` | Notes | Who edited note |

**Additional complexity:**
- `administeredBy` - Who administered medication
- `acknowledgedBy` - Who acknowledged alert
- `approvedBy` - Who approved discharge

---

## 🗄️ Database Schema Analysis

### Current Database Fields:

**Medications Table:**
```sql
CREATE TABLE medications (
    "prescribedBy" TEXT NOT NULL,  -- ⚠️ Domain-specific
    "createdAt" TIMESTAMPTZ,
    "updatedAt" TIMESTAMPTZ
);
```

**Medication Administrations:**
```sql
CREATE TABLE medicationadministrations (
    "administeredBy" TEXT,  -- ⚠️ Different from prescribedBy
    "createdAt" TIMESTAMPTZ,
    "updatedAt" TIMESTAMPTZ
);
```

**Investigations Table:**
```sql
CREATE TABLE investigations (
    "prescribedBy" TEXT,  -- ⚠️ Same as medications
    "createdAt" TIMESTAMPTZ,
    "updatedAt" TIMESTAMPTZ
);
```

**Therapies Table:**
```sql
CREATE TABLE therapy (
    "prescribedBy" TEXT,  -- ⚠️ Same as medications/investigations
    "createdAt" TIMESTAMPTZ,
    "updatedAt" TIMESTAMPTZ
);
```

**Therapy Sessions:**
```sql
CREATE TABLE therapysessions (
    "performedBy" TEXT,  -- ⚠️ DIFFERENT from therapy.prescribedBy!
    "createdAt" TIMESTAMPTZ,
    "updatedAt" TIMESTAMPTZ
);
```

**Patient Notes:**
```sql
CREATE TABLE patientnotes (
    "authorId" TEXT NOT NULL,  -- ⚠️ DIFFERENT naming pattern!
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    "editedAt" TIMESTAMPTZ,  -- ⚠️ No editedBy field!
    "isEdited" BOOLEAN
);
```

**Case Sheet Entries:**
```sql
CREATE TABLE casesheetentries (
    "performedBy" TEXT NOT NULL,  -- ⚠️ Same as therapy sessions
    timestamp TIMESTAMPTZ DEFAULT NOW()
);
```

**Alerts Table:**
```sql
CREATE TABLE alerts (
    "modifiedBy" TEXT,  -- ⚠️ Generic field
    -- No createdBy!
);
```

---

## 🔍 Specific Problem Areas

### Problem 1: Therapy Confusion

**Database has TWO different fields:**
- `therapy.prescribedBy` - Who ordered the therapy
- `therapysessions.performedBy` - Who performed the session

**Backend code confusion:**
```python
# patient_service.py lines 159-164
if therapy.get('conductedBy'):  # ⚠️ conductedBy doesn't exist in DB!
    staff_ids.add(therapy['conductedBy'])
if therapy.get('authorId'):  # ⚠️ authorId doesn't exist in therapy table!
    staff_ids.add(therapy['authorId'])
if therapy.get('createdBy'):  # ⚠️ createdBy doesn't exist in therapy table!
    staff_ids.add(therapy['createdBy'])
```

**Reality:** Only `prescribedBy` exists in the database!

---

### Problem 2: Medications Transformation Mess

**Database field:** `prescribedBy`
**Backend transforms to:** `performedBy` for case sheet

```python
# patient_repository.py lines 338-339
'performedBy': med['prescribedBy'],  # ⚠️ Renaming prescribedBy to performedBy!
'performedByName': med.get('prescribedByName', 'Unknown'),
```

**Why?** To match case sheet `performedBy` pattern
**Result:** Confusing - same person, different field names

---

### Problem 3: Investigations Same Issue

**Database field:** `prescribedBy`
**Backend transforms to:** `performedBy` for case sheet

```python
# patient_repository.py lines 361-362
'performedBy': inv['prescribedBy'],  # ⚠️ Same renaming!
'performedByName': inv.get('prescribedByName', 'Unknown'),
```

---

### Problem 4: Patient Notes Unique Pattern

**Database field:** `authorId`
**Backend transforms to:** `performedBy` for case sheet

```python
# patient_repository.py line 392
SELECT pn.id, pn.content, pn."authorId" as "performedBy",  -- ⚠️ Aliasing!
```

**Also adds:**
- `authorName`
- `performedByName` (same as authorName)

**Why `authorId` not `prescribedBy`?** No clear reason!

---

### Problem 5: Frontend Expects Multiple Fields

**Frontend types:**
```typescript
// MedicalTypes.ts
export interface medication {
  prescribedBy: string;
  prescribedByName?: string;
  // ...
}

export interface investigation {
  performedBy?: string;  // ⚠️ Different from medication!
  performedByName?: string;
  prescribedBy?: string;  // ⚠️ Also has prescribedBy!
  // ...
}

export interface therapy {
  conductedBy?: string;  // ⚠️ Different again!
  conductedByName?: string;
  // ...
}
```

**Result:** Frontend has to handle multiple field names for the same concept!

---

### Problem 6: Case Sheet Standardization Attempt

**Case Sheet tries to standardize on `performedBy`:**
```typescript
export interface caseSheetEntry {
  performedBy: string;
  performedByName?: string;
  performedByRole?: string;
}
```

**But source data uses:**
- Medications: `prescribedBy` → transformed to `performedBy`
- Investigations: `prescribedBy` → transformed to `performedBy`
- Therapies: `prescribedBy` → transformed to `performedBy`
- Notes: `authorId` → transformed to `performedBy`
- Alerts: `acknowledgedBy` → transformed to `performedBy`

**Transformation happens in:** `patient_repository.py` lines 315-481

---

## 📈 Inconsistency Count

**Total occurrences found:**
- Backend: ~150+ references
- Frontend: 121 references across 32 files

**Field name variations:**
1. `prescribedBy` - 48 occurrences
2. `performedBy` - 42 occurrences
3. `authorId` - 18 occurrences
4. `createdBy` - 15 occurrences
5. `modifiedBy` - 12 occurrences
6. `conductedBy` - 8 occurrences
7. `editedBy` - 6 occurrences
8. `administeredBy` - 5 occurrences
9. `acknowledgedBy` - 4 occurrences

---

## 🎯 Proposed Solutions

### Option 1: **Dual-Pattern Approach** (Recommended)

Keep domain-specific fields + add audit fields:

**Database Schema:**
```sql
-- Domain-specific (medical context)
CREATE TABLE medications (
    "prescribedBy" TEXT NOT NULL,     -- Medical: who prescribed
    "administeredBy" TEXT,            -- Medical: who gave dose
    "createdBy" TEXT,                 -- Audit: who created record
    "modifiedBy" TEXT,                -- Audit: who last modified
    "createdAt" TIMESTAMPTZ,
    "updatedAt" TIMESTAMPTZ
);

CREATE TABLE investigations (
    "orderedBy" TEXT NOT NULL,        -- Medical: who ordered (clearer than prescribedBy)
    "performedBy" TEXT,               -- Medical: who performed test
    "createdBy" TEXT,                 -- Audit: who created record
    "modifiedBy" TEXT,                -- Audit: who last modified
    "createdAt" TIMESTAMPTZ,
    "updatedAt" TIMESTAMPTZ
);

CREATE TABLE therapies (
    "orderedBy" TEXT NOT NULL,        -- Medical: who ordered
    "createdBy" TEXT,                 -- Audit: who created record
    "modifiedBy" TEXT,                -- Audit: who last modified
    "createdAt" TIMESTAMPTZ,
    "updatedAt" TIMESTAMPTZ
);

CREATE TABLE therapysessions (
    "performedBy" TEXT NOT NULL,      -- Medical: who performed session
    "createdBy" TEXT,                 -- Audit: who created record
    "modifiedBy" TEXT,                -- Audit: who last modified
    "createdAt" TIMESTAMPTZ,
    "updatedAt" TIMESTAMPTZ
);

CREATE TABLE patientnotes (
    "authorId" TEXT NOT NULL,         -- Medical: who authored (keep for notes)
    "editedBy" TEXT,                  -- Medical: who last edited
    "createdAt" TIMESTAMPTZ,
    "updatedAt" TIMESTAMPTZ
);
```

**Benefits:**
- Medical context preserved (prescribedBy, orderedBy, performedBy)
- Audit trail consistent (createdBy, modifiedBy)
- Clearer semantics

**Changes needed:**
- Add `createdBy`, `modifiedBy` to all tables
- Change investigations `prescribedBy` → `orderedBy`
- Add `editedBy` to patient notes
- Frontend keeps domain-specific fields

---

### Option 2: **Full Standardization** (Simpler but loses context)

Use only generic audit fields:

**Database Schema:**
```sql
-- All tables use same pattern
CREATE TABLE medications (
    "createdBy" TEXT NOT NULL,
    "modifiedBy" TEXT,
    "createdAt" TIMESTAMPTZ,
    "updatedAt" TIMESTAMPTZ
);

CREATE TABLE investigations (
    "createdBy" TEXT NOT NULL,
    "modifiedBy" TEXT,
    "createdAt" TIMESTAMPTZ,
    "updatedAt" TIMESTAMPTZ
);

-- etc.
```

**Benefits:**
- Simple, consistent
- Easy to query
- Clear audit trail

**Drawbacks:**
- Lose medical context (who prescribed vs who administered)
- Less clear in medical workflows
- "Who prescribed this?" requires looking at created_by

---

### Option 3: **Hybrid with JSON** (Most flexible)

Keep simple audit fields + store details in JSON:

**Database Schema:**
```sql
CREATE TABLE medications (
    "createdBy" TEXT NOT NULL,
    "modifiedBy" TEXT,
    "staffDetails" JSONB,  -- {"prescribedBy": "STAFF001", "administeredBy": "STAFF002"}
    "createdAt" TIMESTAMPTZ,
    "updatedAt" TIMESTAMPTZ
);
```

**Benefits:**
- Flexible - can add any staff role
- Simple primary fields
- Rich details when needed

**Drawbacks:**
- Can't easily index JSON fields
- More complex queries for specific staff

---

## ✅ **Recommended Approach: Option 1 (Dual-Pattern)**

**Why:**
1. **Medical clarity:** Doctors want to know "who prescribed this?"
2. **Audit compliance:** System needs to know "who created/modified?"
3. **Best of both worlds:** Domain language + audit trail
4. **Regulatory:** DPDP Act, Clinical Establishments Act need audit trails

---

## 🔧 Implementation Plan

### Phase 1: Database Migration (2 hours)

**Step 1:** Add audit fields to all tables
```sql
ALTER TABLE medications ADD COLUMN "createdBy" TEXT;
ALTER TABLE medications ADD COLUMN "modifiedBy" TEXT;

ALTER TABLE investigations ADD COLUMN "createdBy" TEXT;
ALTER TABLE investigations ADD COLUMN "modifiedBy" TEXT;
ALTER TABLE investigations RENAME COLUMN "prescribedBy" TO "orderedBy";

ALTER TABLE therapy ADD COLUMN "createdBy" TEXT;
ALTER TABLE therapy ADD COLUMN "modifiedBy" TEXT;

ALTER TABLE therapysessions ADD COLUMN "createdBy" TEXT;
ALTER TABLE therapysessions ADD COLUMN "modifiedBy" TEXT;

ALTER TABLE patientnotes ADD COLUMN "editedBy" TEXT;
ALTER TABLE patientnotes ADD COLUMN "createdBy" TEXT;
ALTER TABLE patientnotes RENAME COLUMN "authorId" TO "createdBy";  -- Or keep authorId
```

**Step 2:** Backfill data
```sql
-- Copy existing data to new fields
UPDATE medications SET "createdBy" = "prescribedBy" WHERE "createdBy" IS NULL;
UPDATE investigations SET "createdBy" = "orderedBy" WHERE "createdBy" IS NULL;
-- etc.
```

---

### Phase 2: Backend Updates (3 hours)

**Update repositories to use new fields:**

```python
# medication_repository.py
async def create_medication(self, medication_data: Dict, created_by: str) -> Dict:
    """Create medication with proper audit fields"""
    query = """
        INSERT INTO medications (
            "patientId", name, dosage, frequency, route,
            "prescribedBy",  -- Medical context
            "createdBy",      -- Audit trail
            "createdAt"
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
        RETURNING *
    """

async def update_medication(self, medication_id: str, updates: Dict, modified_by: str):
    """Update with audit trail"""
    query = """
        UPDATE medications
        SET
            status = $1,
            "modifiedBy" = $2,  -- Audit trail
            "updatedAt" = NOW()
        WHERE id = $3
    """
```

**Remove incorrect field checks:**
```python
# patient_service.py - REMOVE these lines (159-164):
if therapy.get('conductedBy'):  # ❌ DELETE - doesn't exist in DB
    staff_ids.add(therapy['conductedBy'])
if therapy.get('authorId'):  # ❌ DELETE - doesn't exist in therapy
    staff_ids.add(therapy['authorId'])
```

**Fix transformations:**
```python
# patient_repository.py - Keep domain fields, add audit fields
'prescribedBy': med['prescribedBy'],  # ✅ Keep medical context
'prescribedByName': med.get('prescribedByName'),
'createdBy': med['createdBy'],  # ✅ Add audit
'createdByName': med.get('createdByName'),
'modifiedBy': med.get('modifiedBy'),  # ✅ Add audit
'modifiedByName': med.get('modifiedByName'),
```

---

### Phase 3: Frontend Updates (2 hours)

**Update TypeScript types:**

```typescript
// MedicalTypes.ts

// Base interface for all medical records
interface MedicalRecordAudit {
  createdBy: string;
  createdByName?: string;
  modifiedBy?: string;
  modifiedByName?: string;
  createdAt: string;
  updatedAt?: string;
}

export interface medication extends MedicalRecordAudit {
  id: string;
  name: string;
  dosage: string;

  // Medical context fields
  prescribedBy: string;
  prescribedByName?: string;
  administeredBy?: string;
  administeredByName?: string;

  // Inherited audit fields from MedicalRecordAudit
}

export interface investigation extends MedicalRecordAudit {
  id: string;
  name: string;
  type: string;

  // Medical context fields
  orderedBy: string;  // Changed from prescribedBy
  orderedByName?: string;
  performedBy?: string;
  performedByName?: string;

  // Inherited audit fields
}

export interface therapy extends MedicalRecordAudit {
  id: string;
  type: string;
  description: string;

  // Medical context fields
  orderedBy: string;  // Changed from prescribedBy
  orderedByName?: string;

  // Inherited audit fields
}

export interface noteComment extends MedicalRecordAudit {
  id: string;
  content: string;

  // Medical context fields (keep authorId for notes)
  authorId: string;
  authorName?: string;
  authorRole?: string;
  editedBy?: string;
  editedByName?: string;

  // Inherited audit fields
}
```

**Update components:**
```typescript
// PatientMedications.tsx
<div>
  <span>Prescribed by: {medication.prescribedByName}</span>
  <span className="text-xs text-gray-500">
    Created by: {medication.createdByName}
  </span>
  {medication.modifiedBy && (
    <span className="text-xs text-gray-500">
      Last modified by: {medication.modifiedByName}
    </span>
  )}
</div>
```

---

### Phase 4: Testing (1 hour)

**Test cases:**
1. Create medication → verify `prescribedBy` and `createdBy` set
2. Update medication → verify `modifiedBy` set
3. Create investigation → verify `orderedBy` and `createdBy` set
4. Create note → verify `authorId` and `createdBy` set
5. Edit note → verify `editedBy` set
6. Case sheet entry → verify all staff names resolved

---

## 📋 Migration Checklist

- [ ] Create database migration script
- [ ] Backup production database
- [ ] Run migration on development database
- [ ] Test all medical record creation/updates
- [ ] Update backend repositories
- [ ] Update backend services
- [ ] Remove incorrect field checks
- [ ] Update frontend types
- [ ] Update frontend components
- [ ] Update API documentation
- [ ] Run full test suite
- [ ] Deploy to staging
- [ ] Test in staging
- [ ] Deploy to production

---

## 🎯 Quick Wins (Can Do Now)

**Before full migration, you can clean up code:**

### 1. Remove Non-Existent Field Checks

**File:** `patient_service.py` lines 159-164
```python
# ❌ DELETE THESE - Fields don't exist in therapy table
if therapy.get('conductedBy'):
    staff_ids.add(therapy['conductedBy'])
if therapy.get('authorId'):
    staff_ids.add(therapy['authorId'])
if therapy.get('createdBy'):
    staff_ids.add(therapy['createdBy'])
```

**Replace with:**
```python
# ✅ Only check fields that actually exist
if therapy.get('prescribedBy'):
    staff_ids.add(therapy['prescribedBy'])
```

---

### 2. Document Current Fields

**Create:** `STAFF_FIELD_REFERENCE.md`
```markdown
# Staff Field Reference

## Medications
- Database: `prescribedBy` (who prescribed)
- Frontend: `prescribedBy` + `prescribedByName`

## Investigations
- Database: `prescribedBy` (who ordered)
- Frontend: `prescribedBy` + `prescribedByName`

## Therapies
- Database: `prescribedBy` (who ordered)
- Frontend: `prescribedBy` + `prescribedByName`

## Therapy Sessions
- Database: `performedBy` (who performed session)
- Frontend: `performedBy` + `performedByName`

## Patient Notes
- Database: `authorId` (who wrote note)
- Frontend: `authorId` + `authorName`

## Case Sheet Entries
- Database: `performedBy` (who performed action)
- Frontend: `performedBy` + `performedByName`
```

---

## 💰 Effort Estimate

| Task | Time | Difficulty |
|------|------|------------|
| Database migration script | 1 hour | Medium |
| Backend repository updates | 2 hours | Medium |
| Backend service cleanup | 1 hour | Easy |
| Frontend type updates | 1 hour | Easy |
| Frontend component updates | 1 hour | Easy |
| Testing | 1 hour | Easy |
| Documentation | 30 min | Easy |
| **Total** | **7.5 hours** | **Medium** |

---

## 🚨 Risks

**Low Risk:**
- Well-defined scope
- Can be done incrementally
- Backward compatible (keep old fields during migration)

**Mitigation:**
- Test on dev database first
- Deploy to staging before production
- Keep old field names as aliases during transition
- Add database triggers to sync old/new fields temporarily

---

## 🏁 Summary

**Current State:** 🔴 Chaotic - 7+ different field names for same concept

**Proposed State:** 🟢 Organized - Clear separation:
- Medical fields: `prescribedBy`, `orderedBy`, `performedBy`, `authorId`
- Audit fields: `createdBy`, `modifiedBy`, `editedBy`

**Next Steps:**
1. Review this proposal
2. Choose Option 1, 2, or 3
3. Create database migration script
4. Implement in dev environment
5. Test thoroughly
6. Deploy

**Question:** Which option do you prefer? Or should I create a different approach?
