# Staff Field Naming - Implementation Guide
**Approved Plan: Option 3 - Workflow Tables**
**Date:** 2025-10-04
**Status:** ✅ APPROVED - Ready for Implementation

---

## 🎯 Final Decision: Simple 3-Field Pattern

### Core Medical Tables
```
prescribedBy  - Doctor who ordered/prescribed (medical context)
performedBy   - Staff who executed action (medical action)
createdBy     - Who created database record (audit trail)
```

### Workflow Tables
```
Keep domain-specific fields in dedicated workflow tables:
- discharge_requests: requestedBy, approvedBy, performedBy
- deviceassignments: assignedBy (already separate)
- admissionrecommendations: recommendedBy, processedBy (already separate)
```

---

## 📊 Complete Field Mapping

### What's Changing:

| Table | Old Field | New Field | Action |
|-------|-----------|-----------|--------|
| medicationadministrations | `administeredBy` | `performedBy` | RENAME |
| patient_alerts | `acknowledgedBy` | `performedBy` | RENAME |
| investigations | - | `performedBy` | ADD (who conducted test) |
| patientnotes | - | `editedBy` | ADD |
| ALL medical tables | - | `createdBy` | ADD (audit) |

### What's Being Removed:

| Code Location | Bad Field Check | Action |
|---------------|-----------------|--------|
| patient_service.py:159-164 | `conductedBy`, `authorId`, `createdBy` on therapies | DELETE (fields don't exist) |

### What's Being Created:

| New Table | Purpose |
|-----------|---------|
| discharge_requests | Multi-step discharge workflow (request → approve → execute) |

---

## 🗄️ Database Schema Changes

### 1. Create Discharge Workflow Table

```sql
CREATE TABLE IF NOT EXISTS discharge_requests (
    id SERIAL PRIMARY KEY,
    "patientId" TEXT NOT NULL,
    status TEXT DEFAULT 'requested',
    reason TEXT,
    notes TEXT,

    -- Request stage (doctor)
    "requestedBy" TEXT NOT NULL,
    "requestedAt" TIMESTAMPTZ DEFAULT NOW(),

    -- Approval stage (admin)
    "approvedBy" TEXT,
    "approvedAt" TIMESTAMPTZ,
    "approvalNotes" TEXT,

    -- Execution stage (nurse)
    "performedBy" TEXT,
    "performedAt" TIMESTAMPTZ,
    "dischargeNotes" TEXT,

    -- Audit
    "createdAt" TIMESTAMPTZ DEFAULT NOW(),
    "updatedAt" TIMESTAMPTZ DEFAULT NOW(),

    FOREIGN KEY ("patientId") REFERENCES patients(id)
);

CREATE INDEX idx_discharge_requests_patient ON discharge_requests("patientId");
CREATE INDEX idx_discharge_requests_status ON discharge_requests(status);

-- Add comments for documentation
COMMENT ON TABLE discharge_requests IS 'Multi-step discharge approval workflow';
COMMENT ON COLUMN discharge_requests."requestedBy" IS 'Doctor who requested discharge';
COMMENT ON COLUMN discharge_requests."approvedBy" IS 'Admin who approved discharge';
COMMENT ON COLUMN discharge_requests."performedBy" IS 'Nurse who executed discharge';
```

### 2. Rename Existing Fields

```sql
-- Rename administeredBy → performedBy
ALTER TABLE medicationadministrations
RENAME COLUMN "administeredBy" TO "performedBy";

-- Rename acknowledgedBy → performedBy
ALTER TABLE patient_alerts
RENAME COLUMN "acknowledgedBy" TO "performedBy";
```

### 3. Add New Fields

```sql
-- Add performedBy to investigations (who conducted the test)
ALTER TABLE investigations
ADD COLUMN "performedBy" TEXT;

-- Add editedBy to patientnotes
ALTER TABLE patientnotes
ADD COLUMN "editedBy" TEXT;

-- Add createdBy to all medical tables (audit trail)
ALTER TABLE medications ADD COLUMN "createdBy" TEXT;
ALTER TABLE medicationadministrations ADD COLUMN "createdBy" TEXT;
ALTER TABLE investigations ADD COLUMN "createdBy" TEXT;
ALTER TABLE therapy ADD COLUMN "createdBy" TEXT;
ALTER TABLE therapysessions ADD COLUMN "createdBy" TEXT;
ALTER TABLE casesheetentries ADD COLUMN "createdBy" TEXT;
ALTER TABLE patient_alerts ADD COLUMN "createdBy" TEXT;
-- Note: patientnotes uses authorId as primary creator field
```

### 4. Add Documentation Comments

```sql
-- Medications
COMMENT ON COLUMN medications."prescribedBy" IS 'Doctor who prescribed medication';
COMMENT ON COLUMN medications."createdBy" IS 'Staff who entered record in system (audit)';

-- Medication Administrations
COMMENT ON COLUMN medicationadministrations."performedBy" IS 'Nurse who administered medication';
COMMENT ON COLUMN medicationadministrations."createdBy" IS 'Staff who created administration record';

-- Investigations
COMMENT ON COLUMN investigations."prescribedBy" IS 'Doctor who ordered test';
COMMENT ON COLUMN investigations."performedBy" IS 'Technician who conducted test';
COMMENT ON COLUMN investigations."createdBy" IS 'Staff who created test order';

-- Therapy
COMMENT ON COLUMN therapy."prescribedBy" IS 'Doctor who prescribed therapy';
COMMENT ON COLUMN therapy."createdBy" IS 'Staff who created therapy order';

-- Therapy Sessions
COMMENT ON COLUMN therapysessions."performedBy" IS 'Therapist who conducted session';
COMMENT ON COLUMN therapysessions."createdBy" IS 'Staff who created session record';

-- Alerts
COMMENT ON COLUMN patient_alerts."performedBy" IS 'Staff who acknowledged/resolved alert';
COMMENT ON COLUMN patient_alerts."createdBy" IS 'System/Watch that generated alert';

-- Notes
COMMENT ON COLUMN patientnotes."authorId" IS 'Doctor/Nurse who authored note (medical ownership)';
COMMENT ON COLUMN patientnotes."editedBy" IS 'Staff who last edited note';
```

---

## 🔧 Backend Code Changes

### Files to Modify:

**1. app/core/database.py**
- Add discharge_requests table creation
- Rename administeredBy → performedBy in medicationadministrations
- Rename acknowledgedBy → performedBy in patient_alerts
- Add performedBy to investigations
- Add editedBy to patientnotes
- Add createdBy to all medical tables

**2. app/services/patient_service.py (lines 159-164)**
```python
# DELETE THESE LINES:
if therapy.get('conductedBy'):
    staff_ids.add(therapy['conductedBy'])
if therapy.get('authorId'):
    staff_ids.add(therapy['authorId'])
if therapy.get('createdBy'):
    staff_ids.add(therapy['createdBy'])

# KEEP ONLY:
if therapy.get('prescribedBy'):
    staff_ids.add(therapy['prescribedBy'])
```

**3. Update administeredBy → performedBy:**
- app/api/v1/nursing.py
- app/api/v2/medications.py
- app/services/medical_action_service.py

**4. Update acknowledgedBy → performedBy:**
- app/services/medical_action_service.py
- app/repositories/patient_repository.py
- app/api/v2/atomic_medical.py

**5. Create new DischargeService:**
- app/services/discharge_service.py (new file)
- app/api/v2/discharge.py (new file or update existing)

---

## 🎨 Frontend Code Changes

### Files to Modify:

**1. types/MedicalTypes.ts**
```typescript
interface MedicalRecordAudit {
  createdBy?: string;
  createdByName?: string;
  createdAt: string;
  updatedAt?: string;
}

export interface medication extends MedicalRecordAudit {
  prescribedBy: string;
  prescribedByName?: string;
}

export interface medicationAdministration extends MedicalRecordAudit {
  performedBy: string;      // Was: administeredBy
  performedByName?: string;
  performedAt: string;
}

export interface investigation extends MedicalRecordAudit {
  prescribedBy: string;
  prescribedByName?: string;
  performedBy?: string;      // NEW
  performedByName?: string;  // NEW
}

export interface alert extends MedicalRecordAudit {
  performedBy?: string;      // Was: acknowledgedBy
  performedByName?: string;
  performedAt?: string;
}
```

**2. Create new workflow type:**
```typescript
export interface dischargeRequest {
  id: number;
  patientId: string;
  status: 'requested' | 'approved' | 'completed' | 'cancelled';
  reason: string;

  requestedBy: string;
  requestedByName?: string;
  requestedAt: string;

  approvedBy?: string;
  approvedByName?: string;
  approvedAt?: string;

  performedBy?: string;
  performedByName?: string;
  performedAt?: string;
}
```

**3. Update services:**
- services/MedicationService.ts (administeredBy → performedBy)
- services/patient/PatientCaseService.ts (acknowledgedBy → performedBy)
- services/DischargeService.ts (new file)

**4. Update transformers:**
- utils/transformers/MedicationTransformer.ts

---

## ✅ Implementation Checklist

### Phase 1: Database (Priority 1)
- [ ] Add discharge_requests table to database.py
- [ ] Rename medicationadministrations.administeredBy → performedBy
- [ ] Rename patient_alerts.acknowledgedBy → performedBy
- [ ] Add investigations.performedBy column
- [ ] Add patientnotes.editedBy column
- [ ] Add createdBy to all medical tables
- [ ] Add database comments
- [ ] Test database migration on dev

### Phase 2: Backend Code (Priority 2)
- [ ] Remove bad field checks from patient_service.py
- [ ] Update nursing.py: administeredBy → performedBy
- [ ] Update medications.py: administeredBy → performedBy
- [ ] Update medical_action_service.py: administeredBy → performedBy
- [ ] Update medical_action_service.py: acknowledgedBy → performedBy
- [ ] Update patient_repository.py: acknowledgedBy → performedBy
- [ ] Update atomic_medical.py: acknowledgedBy → performedBy
- [ ] Create DischargeService
- [ ] Create discharge API endpoints
- [ ] Add createdBy to all create operations
- [ ] Test backend APIs

### Phase 3: Frontend (Priority 3)
- [ ] Update MedicalTypes.ts
- [ ] Create dischargeRequest type
- [ ] Update MedicationService.ts
- [ ] Update PatientCaseService.ts
- [ ] Update MedicationTransformer.ts
- [ ] Create DischargeService.ts
- [ ] Update components using these fields
- [ ] Run TypeScript build
- [ ] Test frontend

### Phase 4: Testing (Priority 4)
- [ ] Test discharge workflow (request → approve → complete)
- [ ] Test medication administration
- [ ] Test alert acknowledgment
- [ ] Test investigation with performedBy
- [ ] Test note editing with editedBy
- [ ] Integration tests
- [ ] E2E tests

---

## 🎯 Final Schema Reference

### All Medical Tables After Changes:

```
medications:
  - prescribedBy (doctor who prescribed)
  - createdBy (who entered in system)

medicationadministrations:
  - performedBy (nurse who gave medicine) [renamed from administeredBy]
  - createdBy (who created record)

investigations:
  - prescribedBy (doctor who ordered)
  - performedBy (tech who conducted) [NEW]
  - createdBy (who created order)

therapy:
  - prescribedBy (doctor who prescribed)
  - createdBy (who created order)

therapysessions:
  - performedBy (therapist who conducted)
  - createdBy (who created record)

patient_alerts:
  - performedBy (who acknowledged) [renamed from acknowledgedBy]
  - createdBy (system/watch that generated)

casesheetentries:
  - performedBy (who performed action)
  - createdBy (who created entry)

patientnotes:
  - authorId (who authored note) [special - medical ownership]
  - editedBy (who edited) [NEW]

discharge_requests: [NEW TABLE]
  - requestedBy (doctor)
  - approvedBy (admin)
  - performedBy (nurse)
  - createdBy (audit)
```

---

## ⏱️ Time Estimate

| Phase | Estimated Time |
|-------|---------------|
| Database changes | 3 hours |
| Backend updates | 4 hours |
| Frontend updates | 2 hours |
| Testing | 1 hour |
| **Total** | **10 hours** |

---

## 🚨 Migration Notes

**Before running migration:**
1. Backup production database
2. Test on dev environment first
3. Check for any custom queries that use old field names
4. Update any reports/analytics that reference old fields

**After migration:**
1. Verify all field renames successful
2. Check data integrity
3. Test all CRUD operations
4. Verify frontend builds without errors
5. Run full test suite

---

## 📝 Quick Reference Card

**When creating a new medical record:**
```python
{
  "prescribedBy": "STAFF_ID_WHO_PRESCRIBED",  # Doctor
  "createdBy": "STAFF_ID_WHO_ENTERED_DATA"     # Data entry staff
}
```

**When executing an action:**
```python
{
  "performedBy": "STAFF_ID_WHO_DID_IT",  # Nurse/tech/therapist
  "performedAt": "2025-01-15T10:30:00Z"
}
```

**For workflows (discharge):**
```python
{
  "requestedBy": "DOCTOR_ID",     # Step 1: Request
  "approvedBy": "ADMIN_ID",       # Step 2: Approve
  "performedBy": "NURSE_ID"       # Step 3: Execute
}
```

---

**Status:** Ready for implementation
**Next Step:** Start with Phase 1 - Database changes
