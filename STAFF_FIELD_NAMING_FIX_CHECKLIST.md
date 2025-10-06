# Staff Field Naming - Implementation Checklist

**Approved Strategy:** 3-field pattern + workflow tables
**Date:** 2025-10-04
**Estimated Time:** 10 hours

---

## 🎯 Final Schema Pattern

### Core Medical Tables (3 fields):
```
prescribedBy  - Doctor who ordered/prescribed
performedBy   - Staff who executed action
createdBy     - Who created database record (audit)
```

### Notes Table (Special case):
```
authorId  - Who authored note
editedBy  - Who edited note
```

### Workflow Tables (Keep domain-specific):
```
discharge_requests:       requestedBy, approvedBy, performedBy
deviceassignments:        assignedBy (keep)
admissionrecommendations: recommendedBy, processedBy (keep)
```

---

## ✅ Phase 1: Database Schema Changes

### 1.1 Create New Table

**File:** `hospital-backend/app/core/database.py`
**Location:** After line 387 (after patient_alerts table)

**Add:**
```sql
-- Discharge Workflow table
CREATE TABLE IF NOT EXISTS discharge_requests (
    id SERIAL PRIMARY KEY,
    "patientId" TEXT NOT NULL,
    status TEXT DEFAULT 'requested',
    reason TEXT,
    notes TEXT,

    "requestedBy" TEXT NOT NULL,
    "requestedAt" TIMESTAMPTZ DEFAULT NOW(),

    "approvedBy" TEXT,
    "approvedAt" TIMESTAMPTZ,
    "approvalNotes" TEXT,

    "performedBy" TEXT,
    "performedAt" TIMESTAMPTZ,
    "dischargeNotes" TEXT,

    "createdAt" TIMESTAMPTZ DEFAULT NOW(),
    "updatedAt" TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_discharge_requests_patient ON discharge_requests("patientId");
CREATE INDEX idx_discharge_requests_status ON discharge_requests(status);
```

### 1.2 Rename Fields

**File:** `hospital-backend/app/core/database.py`

**Line 290:** Change `"administeredBy"` → `"performedBy"`
```sql
-- BEFORE:
"administeredBy" TEXT,

-- AFTER:
"performedBy" TEXT,
```

**Line 383:** Change `"acknowledgedBy"` → `"performedBy"`
```sql
-- BEFORE:
"acknowledgedBy" TEXT,

-- AFTER:
"performedBy" TEXT,
```

### 1.3 Add Missing Fields

**Add to investigations table (after line 309):**
```sql
"performedBy" TEXT,  -- Who conducted the test
```

**Add to patientnotes table (after line 358):**
```sql
"editedBy" TEXT,  -- Who last edited the note
```

**Add to medications table (after line 278):**
```sql
"createdBy" TEXT,  -- Who created the record
```

**Add to medicationadministrations table (after line 290):**
```sql
"createdBy" TEXT,
```

**Add to investigations table (after performedBy):**
```sql
"createdBy" TEXT,
```

**Add to therapy table (after line 329):**
```sql
"createdBy" TEXT,
```

**Add to therapysessions table (after line 343):**
```sql
"createdBy" TEXT,
```

**Add to casesheetentries table (after line 368):**
```sql
"createdBy" TEXT,
```

**Add to patient_alerts table (after performedBy):**
```sql
"createdBy" TEXT,
```

---

## ✅ Phase 2: Backend Code Updates

### 2.1 Remove Bad Field Checks

**File:** `hospital-backend/app/services/patient_service.py`
**Lines 159-164**

**DELETE:**
```python
if therapy.get('conductedBy'):
    staff_ids.add(therapy['conductedBy'])
if therapy.get('authorId'):
    staff_ids.add(therapy['authorId'])
if therapy.get('createdBy'):
    staff_ids.add(therapy['createdBy'])
```

**KEEP ONLY:**
```python
if therapy.get('prescribedBy'):
    staff_ids.add(therapy['prescribedBy'])
```

### 2.2 Update: administeredBy → performedBy

**Files to update:**

1. **`app/api/v1/nursing.py`** - Line 206, 232, 237, 241, 248, 253
   - Change parameter: `administeredBy: str` → `performedBy: str`
   - Change SQL: `"administeredBy" = $1` → `"performedBy" = $1`
   - Change variable references

2. **`app/api/v2/medications.py`** - Line 159
   ```python
   # BEFORE:
   updated_by=completion_data.get('administeredBy', 'system')

   # AFTER:
   updated_by=completion_data.get('performedBy', 'system')
   ```

3. **`app/services/medical_action_service.py`** - Line 357
   ```python
   # BEFORE:
   'administeredBy': performed_by,

   # AFTER:
   'performedBy': performed_by,
   ```

### 2.3 Update: acknowledgedBy → performedBy

**Files to update:**

1. **`app/services/medical_action_service.py`** - Lines 487, 497, 690
   ```python
   # BEFORE:
   "acknowledgedBy" = $1
   'acknowledgedBy': performed_by
   acknowledged_by = medical_record.get('acknowledgedBy', 'Unknown staff')

   # AFTER:
   "performedBy" = $1
   'performedBy': performed_by
   performed_by_staff = medical_record.get('performedBy', 'Unknown staff')
   ```

2. **`app/repositories/patient_repository.py`** - Lines 244, 438, 463
   ```python
   # BEFORE:
   acknowledgedBy = $1
   "acknowledgedBy", "acknowledgedAt"
   'performedBy': alert['acknowledgedBy']

   # AFTER:
   performedBy = $1
   "performedBy", "performedAt"  # Also rename acknowledgedAt → performedAt
   'performedBy': alert['performedBy']
   ```

3. **`app/api/v2/atomic_medical.py`** - Line 597 (comment only)
   ```python
   # Update comment: acknowledgedBy → performedBy
   ```

### 2.4 Create Discharge Service

**New File:** `hospital-backend/app/services/discharge_service.py`

```python
"""
Discharge Workflow Service - Multi-step discharge approval process
"""
from typing import Dict, Optional
from datetime import datetime
import logging

from .base_service import BaseService

logger = logging.getLogger(__name__)


class DischargeService(BaseService):
    """
    Handles multi-step discharge workflow:
    1. Doctor requests discharge (requestedBy)
    2. Admin approves discharge (approvedBy)
    3. Nurse completes discharge (performedBy)
    """

    async def request_discharge(
        self,
        patient_id: str,
        requested_by: str,
        reason: str,
        notes: Optional[str] = None
    ) -> Dict:
        """Doctor requests patient discharge"""
        query = """
            INSERT INTO discharge_requests
            ("patientId", "requestedBy", reason, notes, status)
            VALUES ($1, $2, $3, $4, 'requested')
            RETURNING *
        """

        result = await self.execute_custom_query(
            query,
            [patient_id, requested_by, reason, notes]
        )

        logger.info(f"Discharge requested for patient {patient_id} by {requested_by}")
        return result[0] if result else None

    async def approve_discharge(
        self,
        request_id: int,
        approved_by: str,
        approval_notes: Optional[str] = None
    ) -> Dict:
        """Admin approves discharge request"""
        query = """
            UPDATE discharge_requests
            SET status = 'approved',
                "approvedBy" = $1,
                "approvedAt" = NOW(),
                "approvalNotes" = $2,
                "updatedAt" = NOW()
            WHERE id = $3 AND status = 'requested'
            RETURNING *
        """

        result = await self.execute_custom_query(
            query,
            [approved_by, approval_notes, request_id]
        )

        if result:
            logger.info(f"Discharge request {request_id} approved by {approved_by}")
        return result[0] if result else None

    async def complete_discharge(
        self,
        request_id: int,
        performed_by: str,
        discharge_notes: Optional[str] = None
    ) -> Dict:
        """Nurse completes patient discharge"""
        query = """
            UPDATE discharge_requests
            SET status = 'completed',
                "performedBy" = $1,
                "performedAt" = NOW(),
                "dischargeNotes" = $2,
                "updatedAt" = NOW()
            WHERE id = $3 AND status = 'approved'
            RETURNING *
        """

        result = await self.execute_custom_query(
            query,
            [performed_by, discharge_notes, request_id]
        )

        if result:
            # Update patient status
            patient_query = """
                UPDATE patients
                SET status = 'discharged',
                    "updatedAt" = NOW()
                WHERE id = (
                    SELECT "patientId" FROM discharge_requests WHERE id = $1
                )
            """
            await self.execute_custom_query(patient_query, [request_id])

            logger.info(f"Discharge completed for request {request_id} by {performed_by}")

        return result[0] if result else None

    async def get_pending_requests(self) -> list[Dict]:
        """Get all pending discharge requests"""
        query = """
            SELECT dr.*, p.name as "patientName"
            FROM discharge_requests dr
            JOIN patients p ON dr."patientId" = p.id
            WHERE dr.status = 'requested'
            ORDER BY dr."requestedAt" DESC
        """
        return await self.execute_custom_query(query)

    async def get_approved_requests(self) -> list[Dict]:
        """Get approved but not completed discharge requests"""
        query = """
            SELECT dr.*, p.name as "patientName"
            FROM discharge_requests dr
            JOIN patients p ON dr."patientId" = p.id
            WHERE dr.status = 'approved'
            ORDER BY dr."approvedAt" DESC
        """
        return await self.execute_custom_query(query)
```

**Update:** `hospital-backend/app/services/__init__.py`
```python
from .discharge_service import DischargeService
```

**Update:** `hospital-backend/app/services/service_factory.py`
```python
def get_discharge_service():
    from .discharge_service import DischargeService
    return DischargeService()
```

### 2.5 Update Discharge API

**File:** `hospital-backend/app/api/v1/discharge_workflow.py`

**Replace entire file content** with calls to new DischargeService

---

## ✅ Phase 3: Frontend Updates

### 3.1 Update Types

**File:** `hospital-display-app/src/types/MedicalTypes.ts`

**Add interface:**
```typescript
interface MedicalRecordAudit {
  createdBy?: string;
  createdByName?: string;
  createdAt: string;
  updatedAt?: string;
}
```

**Update existing interfaces:**
```typescript
export interface medication extends MedicalRecordAudit {
  // existing fields...
  prescribedBy: string;
  prescribedByName?: string;
}

export interface medicationAdministration extends MedicalRecordAudit {
  performedBy: string;        // Was: administeredBy
  performedByName?: string;
  performedAt: string;         // Was: administeredAt
}

export interface investigation extends MedicalRecordAudit {
  prescribedBy: string;
  prescribedByName?: string;
  performedBy?: string;        // NEW - who conducted test
  performedByName?: string;
}
```

**File:** `hospital-display-app/src/types/PatientTypes.ts`

**Update alert interface:**
```typescript
export interface alert {
  id: string;
  message: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  timestamp: string;
  performedBy?: string;      // Was: acknowledgedBy
  performedByName?: string;
  performedByRole?: string;
  completedAt?: string;      // Was: acknowledgedAt
  isAcknowledged: boolean;
}
```

**Add new interface:**
```typescript
export interface dischargeRequest {
  id: number;
  patientId: string;
  status: 'requested' | 'approved' | 'completed' | 'cancelled';
  reason: string;
  notes?: string;

  requestedBy: string;
  requestedByName?: string;
  requestedAt: string;

  approvedBy?: string;
  approvedByName?: string;
  approvedAt?: string;
  approvalNotes?: string;

  performedBy?: string;
  performedByName?: string;
  performedAt?: string;
  dischargeNotes?: string;
}
```

### 3.2 Update Services

**File:** `hospital-display-app/src/services/MedicationService.ts`

**Line 125:** Change `administeredBy` → `performedBy`
```typescript
// BEFORE:
administeredBy: userId,

// AFTER:
performedBy: userId,
```

**File:** `hospital-display-app/src/services/patient/PatientCaseService.ts`

**Line 119:** Change `acknowledgedBy` → `performedBy`
```typescript
// BEFORE:
acknowledgedBy: userId

// AFTER:
performedBy: userId
```

**File:** `hospital-display-app/src/utils/transformers/MedicationTransformer.ts`

**Lines 187-188:** Change field names
```typescript
// BEFORE:
administeredBy: administrationData.administeredBy,
administeredByName: administrationData.administeredByName,

// AFTER:
performedBy: administrationData.performedBy,
performedByName: administrationData.performedByName,
```

### 3.3 Create Discharge Service

**New File:** `hospital-display-app/src/services/DischargeService.ts`

```typescript
import { BaseService } from './BaseService';
import { dischargeRequest } from '../types/PatientTypes';

export class DischargeService extends BaseService {

  static async requestDischarge(
    patientId: string,
    requestedBy: string,
    reason: string,
    notes?: string
  ): Promise<dischargeRequest> {
    const response = await this.fetchFromBackend('/discharge/request', {
      method: 'POST',
      body: JSON.stringify({ patientId, requestedBy, reason, notes })
    });
    return response;
  }

  static async approveDischarge(
    requestId: number,
    approvedBy: string,
    approvalNotes?: string
  ): Promise<dischargeRequest> {
    const response = await this.fetchFromBackend('/discharge/approve', {
      method: 'POST',
      body: JSON.stringify({ requestId, approvedBy, approvalNotes })
    });
    return response;
  }

  static async completeDischarge(
    requestId: number,
    performedBy: string,
    dischargeNotes?: string
  ): Promise<dischargeRequest> {
    const response = await this.fetchFromBackend('/discharge/complete', {
      method: 'POST',
      body: JSON.stringify({ requestId, performedBy, dischargeNotes })
    });
    return response;
  }

  static async getPendingRequests(): Promise<dischargeRequest[]> {
    const response = await this.fetchFromBackend('/discharge/pending');
    return Array.isArray(response) ? response : [];
  }

  static async getApprovedRequests(): Promise<dischargeRequest[]> {
    const response = await this.fetchFromBackend('/discharge/approved');
    return Array.isArray(response) ? response : [];
  }
}
```

---

## ✅ Phase 4: Testing

### Database Migration Test
```sql
-- Test discharge_requests table
INSERT INTO discharge_requests ("patientId", "requestedBy", reason)
VALUES ('TEST001', 'DOC001', 'Patient recovered');

-- Test field renames
SELECT "performedBy" FROM medicationadministrations LIMIT 1;
SELECT "performedBy" FROM patient_alerts LIMIT 1;

-- Test new columns
SELECT "performedBy", "createdBy" FROM investigations LIMIT 1;
SELECT "editedBy" FROM patientnotes LIMIT 1;
```

### Backend API Test
```bash
# Test discharge workflow
curl -X POST http://localhost:8001/discharge/request \
  -H "Content-Type: application/json" \
  -d '{"patientId": "PAT001", "requestedBy": "DOC001", "reason": "Recovered"}'
```

### Frontend Build Test
```bash
cd hospital-display-app
npm run build
```

---

## 📋 Quick Reference: Field Mapping

| Old Field | New Field | Context |
|-----------|-----------|---------|
| `administeredBy` | `performedBy` | Medication administration |
| `acknowledgedBy` | `performedBy` | Alert acknowledgment |
| `conductedBy` | ❌ DELETE | Doesn't exist, remove checks |
| `requestedBy` | ✅ KEEP | Discharge workflow only |
| `approvedBy` | ✅ KEEP | Discharge workflow only |
| `assignedBy` | ✅ KEEP | Device assignments |
| `recommendedBy` | ✅ KEEP | Admission recommendations |
| `processedBy` | ✅ KEEP | Admission processing |

---

## 🎯 Success Criteria

- [ ] discharge_requests table exists
- [ ] All field renames completed
- [ ] All new columns added
- [ ] Backend compiles without errors
- [ ] Frontend compiles without errors
- [ ] Discharge workflow functional
- [ ] All medical operations use correct field names

---

**Total Estimated Time:** 10 hours
**Priority:** HIGH - Fixes architectural inconsistency
