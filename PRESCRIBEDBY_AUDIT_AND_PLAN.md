# prescribedBy Field Audit and Implementation Plan

## COMPLETE AUDIT FINDINGS

### 1. **MEDICATIONS TAB** ✅ FULLY IMPLEMENTED

**Database Schema:**
```sql
CREATE TABLE medications (
    "prescribedBy" TEXT NOT NULL
)
```

**TypeScript Type:**
```typescript
interface medication {
    prescribedBy: string;
    prescribedByName?: string;
}
```

**Frontend Display:**
```typescript
// Line 273 in PatientMedications.tsx
{(med as any).prescribedByName || med.prescribedBy}
```

**Data Flow:**
- ✅ Frontend **sends**: `prescribedBy: currentUser.staffId`
- ✅ Backend **stores**: In `medications` table
- ✅ Backend **returns**: Both `prescribedBy` (ID) and `prescribedByName` (looked up from staff table)
- ✅ Frontend **displays**: Name with fallback to ID

**STATUS**: ✅ COMPLETE - Gold standard pattern

---

### 2. **INVESTIGATIONS TAB** ❌ MISSING prescribedBy

**Database Schema:**
```sql
CREATE TABLE investigations (
    "performedBy" TEXT,  -- Who executed the investigation
    -- MISSING: prescribedBy field
)
```

**TypeScript Type:**
```typescript
interface investigation {
    performedBy: string;
    performedByName?: string;
    // MISSING: prescribedBy and prescribedByName
}
```

**Frontend Display:**
```typescript
// Line 159 in PatientInvestigations.tsx
{inv.performedBy}  // Shows ID, not name
```

**Data Flow:**
- ✅ Frontend **sends**: `prescribedBy: currentUser.staffId` (just added)
- ❌ Backend **database**: NO `prescribedBy` column
- ❌ Backend **returns**: Only `performedBy`
- ❌ Frontend **displays**: Shows `performedBy` ID (not name)

**ISSUES**:
1. Database missing `prescribedBy` column
2. Frontend sends `prescribedBy` but backend can't store it
3. Frontend displays `performedBy` ID instead of name
4. Type definition missing `prescribedBy` fields
5. `performedBy` vs `prescribedBy` semantic confusion

**SEMANTIC CLARIFICATION**:
- `prescribedBy` = Who **ordered** the investigation (Doctor)
- `performedBy` = Who **executed** the investigation (Lab Tech/Radiologist)

---

### 3. **THERAPIES TAB** ❌ MISSING prescribedBy

**Database Schema:**
```sql
CREATE TABLE therapy (
    "performedBy" TEXT,  -- Who executed therapy sessions
    -- MISSING: prescribedBy field
)
```

**TypeScript Type:**
```typescript
interface therapy {
    performedBy: string;
    performedByName?: string;
    // MISSING: prescribedBy and prescribedByName
}
```

**Frontend Display:**
```typescript
// Line 144 in PatientTherapies.tsx
{therapy.performedBy}  // Shows ID, not name
```

**Data Flow:**
- ✅ Frontend **sends**: `prescribedBy: currentUser.staffId` (just added)
- ❌ Backend **database**: NO `prescribedBy` column
- ❌ Backend **returns**: Only `performedBy`
- ❌ Frontend **displays**: Shows `performedBy` ID (not name)

**ISSUES**:
1. Database missing `prescribedBy` column
2. Frontend sends `prescribedBy` but backend can't store it
3. Frontend displays `performedBy` ID instead of name
4. Type definition missing `prescribedBy` fields
5. `performedBy` vs `prescribedBy` semantic confusion

**SEMANTIC CLARIFICATION**:
- `prescribedBy` = Who **ordered** the therapy (Doctor)
- `performedBy` = Who **administered** therapy sessions (Physiotherapist)

---

### 4. **NOTES TAB** ✅ CORRECT PATTERN

**Backend:**
- Notes use `authorId` and backend looks up `authorName` from staff table

**TypeScript Type:**
```typescript
interface noteComment {
    authorId: string;
    authorName: string;  // Backend provides via staff lookup
    authorRole: string;
}
```

**Frontend Display:**
```typescript
// NotesViewer.tsx lines 73-75
<span>{note.authorName}</span>
<span>{note.authorRole}</span>
```

**Data Flow:**
- ✅ Frontend **sends**: `authorId` only (we just changed this)
- ✅ Backend **returns**: `authorName` (from staff table lookup)
- ✅ Frontend **displays**: Name correctly

**STATUS**: ✅ CORRECT - Backend performs staff lookup

---

## COMPARISON SUMMARY

| Feature | Medications | Investigations | Therapies | Notes |
|---------|-------------|----------------|-----------|-------|
| **DB has prescribedBy/authorId** | ✅ YES | ❌ NO | ❌ NO | ✅ YES (authorId) |
| **Type has prescribedBy/authorId** | ✅ YES | ❌ NO | ❌ NO | ✅ YES |
| **Frontend sends prescribedBy** | ✅ YES | ✅ YES (new) | ✅ YES (new) | ✅ YES (authorId) |
| **Backend returns name** | ✅ YES | ❌ NO | ❌ NO | ✅ YES |
| **Frontend displays name** | ✅ YES | ❌ NO (shows ID) | ❌ NO (shows ID) | ✅ YES |
| **Has performedBy field** | N/A | ✅ YES | ✅ YES | N/A |

---

## ROOT CAUSE ANALYSIS

### The Issue:
Frontend was recently modified to **send** `prescribedBy`, but:
1. **Database** doesn't have `prescribedBy` columns for investigations/therapies
2. **Backend API** likely ignores the `prescribedBy` field (column doesn't exist)
3. **Frontend types** don't have `prescribedBy` fields
4. **Frontend display** shows `performedBy` (ID) instead of names

### The Fix Needed:
Three-layer fix required:
1. **Database Migration**: Add `prescribedBy` columns
2. **Backend API**: Handle `prescribedBy` field and return `prescribedByName`
3. **Frontend**: Add types and update display logic

---

## IMPLEMENTATION PLAN

### Phase 1: Database Migration (Backend)

**File**: `hospital-backend/app/core/database.py` or new migration script

```sql
-- Add prescribedBy column to investigations table
ALTER TABLE investigations
ADD COLUMN "prescribedBy" TEXT;

-- Add prescribedBy column to therapy table
ALTER TABLE therapy
ADD COLUMN "prescribedBy" TEXT;

-- Optional: Backfill existing records with performedBy value
UPDATE investigations
SET "prescribedBy" = "performedBy"
WHERE "prescribedBy" IS NULL;

UPDATE therapy
SET "prescribedBy" = "performedBy"
WHERE "prescribedBy" IS NULL;
```

---

### Phase 2: Backend API Updates (Backend)

**Files to modify:**
1. `hospital-backend/app/api/v2/investigations.py`
2. `hospital-backend/app/api/v2/therapy.py`
3. `hospital-backend/app/services/investigation_service.py`
4. `hospital-backend/app/services/therapy_service.py`
5. `hospital-backend/app/repositories/investigation_repository.py` (if exists)
6. `hospital-backend/app/repositories/therapy_repository.py`

**Changes needed:**
- Accept `prescribedBy` in POST endpoints
- Store `prescribedBy` in database
- Perform staff table lookup for `prescribedByName`
- Return both `prescribedBy` (ID) and `prescribedByName` (name) in responses
- Keep `performedBy` and `performedByName` for execution tracking

---

### Phase 3: Frontend Type Updates (Frontend)

**File**: `hospital-display-app/src/types/MedicalTypes.ts`

```typescript
export interface investigation {
    id: string;
    type: 'lab' | 'imaging' | 'biopsy' | 'culture';
    name: string;
    // ... existing fields ...
    prescribedBy: string;           // ADD: Who ordered the investigation
    prescribedByName?: string;      // ADD: Prescriber name from staff lookup
    performedBy: string;             // KEEP: Who executed the investigation
    performedByName?: string;        // KEEP: Performer name from staff lookup
    // ... rest of fields ...
}

export interface therapy {
    id: string;
    type: 'physiotherapy' | 'occupational' | 'speech' | 'respiratory';
    // ... existing fields ...
    prescribedBy: string;           // ADD: Who ordered the therapy
    prescribedByName?: string;      // ADD: Prescriber name from staff lookup
    performedBy: string;             // KEEP: Who administered therapy
    performedByName?: string;        // KEEP: Performer name from staff lookup
    // ... rest of fields ...
}
```

---

### Phase 4: Frontend Display Updates (Frontend)

**File 1**: `hospital-display-app/src/components/PatientInvestigations.tsx`

```typescript
// Line 159 - Change from:
<p><span className="font-medium">Ordered by:</span> {inv.performedBy}</p>

// To:
<p><span className="font-medium">Ordered by:</span> {inv.prescribedByName || inv.prescribedBy || 'Unknown'}</p>

// Optionally add performed by info if needed:
{inv.performedByName && (
    <p><span className="font-medium">Performed by:</span> {inv.performedByName || inv.performedBy}</p>
)}
```

**File 2**: `hospital-display-app/src/components/PatientTherapies.tsx`

```typescript
// Line 144 - Change from:
<p><span className="font-medium">Prescribed by:</span> {therapy.performedBy}</p>

// To:
<p><span className="font-medium">Prescribed by:</span> {therapy.prescribedByName || therapy.prescribedBy || 'Unknown'}</p>

// Optionally add therapist info if needed (already exists at line 145):
{therapy.therapist && <p><span className="font-medium">Therapist:</span> {therapy.therapist}</p>}
```

---

### Phase 5: Documentation Updates (Frontend)

**File**: `PATIENT_DETAIL_TABS_DATA_FIELDS_ANALYSIS.md`

Update to reflect:
- `prescribedBy` stored in database
- `prescribedByName` returned by backend after staff lookup
- Separation of `prescribedBy` (who ordered) vs `performedBy` (who executed)

---

## ROLLOUT SEQUENCE

### Step 1: Backend Changes (CRITICAL - Do First)
1. Create database migration script
2. Run migration on database
3. Update backend API to accept and store `prescribedBy`
4. Update backend to return `prescribedByName` via staff lookup
5. Test backend endpoints

### Step 2: Frontend Changes (After Backend Complete)
1. Update TypeScript types
2. Update display components
3. Test frontend display
4. Update documentation

---

## RISK ASSESSMENT

### Low Risk:
- ✅ Database migration (adding nullable column is safe)
- ✅ TypeScript type updates (compile-time only)

### Medium Risk:
- ⚠️ Backend API changes (need careful testing)
- ⚠️ Frontend display changes (UI changes visible to users)

### Mitigation:
- Test backend API with Postman/curl before frontend integration
- Verify staff lookup works correctly
- Check existing records display correctly after migration

---

## SUCCESS CRITERIA

### After Implementation:
1. ✅ Investigations show "Ordered by: Dr. Smith" (not "Ordered by: STAFF001")
2. ✅ Therapies show "Prescribed by: Dr. Jones" (not "Prescribed by: STAFF002")
3. ✅ Database has `prescribedBy` columns with proper foreign key relationships
4. ✅ Backend performs staff table lookup and returns names
5. ✅ Frontend displays names with proper fallbacks
6. ✅ Consistent pattern across Medications, Investigations, Therapies, Notes

---

## ESTIMATED EFFORT

- **Backend**: 2-3 hours (migration + API updates + testing)
- **Frontend**: 1 hour (types + display updates + testing)
- **Testing**: 1 hour (end-to-end verification)
- **Total**: 4-5 hours

---

*Audit Date: 2025-10-03*
*Status: Ready for implementation*
