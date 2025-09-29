# Database Tables and Case Sheet Analysis

## Current Database Structure (Confirmed Tables)

Based on analysis of the backend repository files, the following tables exist in the database:

### 1. `patients` (Main patient table)
**Columns (all camelCase):**
- `id` (primary key)
- `firstName`
- `lastName`
- `mrn` (Medical Record Number)
- `dateOfBirth`
- `gender`
- `phoneNumber`
- `emergencyContactName`
- `emergencyContactPhone`
- `bloodType`
- `allergies`
- `medicalHistory`
- `currentMedications`
- `roomNumber`
- `bedNumber`
- `attendingPhysician`
- `nurseInCharge`
- `admissionDate`
- `dischargeDate`
- `assignedDeviceId`
- `status`
- `createdAt`
- `updatedAt`

### 2. `patientnotes` (Patient notes table)
**Columns (camelCase):**
- `id` (primary key)
- `patientId` (foreign key)
- `content`
- `authorId`
- `authorName`
- `authorRole`
- `timestamp`
- `editedAt`
- `isEdited`

### 3. `medications` (Medications table)
**Columns (camelCase):**
- `id` (primary key)
- `patientId` (foreign key)
- `medicationName`
- `dosage`
- `frequency`
- `route`
- `status`
- `prescribedBy`
- `authorId`
- `createdBy`
- `createdAt`
- `updatedAt`

### 4. `investigations` (Investigations table)
**Columns (camelCase):**
- `id` (primary key)
- `patientId` (foreign key)
- `type`
- `name`
- `priority`
- `status`
- `results`
- `orderedBy`
- `authorId`
- `createdBy`
- `createdAt`
- `completedAt`

### 5. `therapy` (Therapy table)
**Columns (camelCase):**
- `id` (primary key)
- `patientId` (foreign key)
- `type`
- `description`
- `frequency`
- `duration`
- `status`
- `conductedBy`
- `authorId`
- `createdBy`
- `startDate`
- `endDate`
- `sessions` (JSON array)

### 6. `staff` (Staff table)
**Columns (camelCase):**
- `id` (primary key)
- `firstName`
- `lastName`
- `role`

### 7. `patient_alerts` (Patient alerts table)
**Columns (camelCase):**
- `id` (primary key)
- `patientId` (foreign key)
- `alertType`
- `severity`
- `message`
- `status`
- `acknowledgedBy`
- `acknowledgedAt`
- `createdAt`
- `updatedAt`

## Missing Table: `case_entries`

### Problem Discovered
The backend code expects a `case_entries` table for case sheet functionality, but this table **DOES NOT EXIST** in the database.

### Expected `case_entries` Table Structure
Based on the repository code analysis, the table should have:

**Columns (camelCase):**
- `id` (primary key, UUID)
- `patientId` (foreign key)
- `entryType` (medication, investigation, therapy, note, etc.)
- `description`
- `findings`
- `recommendations`
- `followUpDate`
- `severity`
- `category`
- `createdBy`
- `timestamp`
- `createdAt`
- `updatedAt`
- `deletedAt`

### Backend API Endpoints (V2)
The backend has working endpoints expecting this table:
- `GET /api/v2/patients/{patient_id}/case-entries`
- `POST /api/v2/patients/{patient_id}/case-entries`

## Case Sheet Functionality Design

### How Case Sheets Should Work

Based on the user's question: *"i thought we just show all details in a time wise manner from all entries in other tabs in casesheet?"*

**Answer: YES, that's exactly how it should work.**

### Case Sheet Concept
The case sheet should be a **chronological timeline** that aggregates ALL medical activities from other tabs:

1. **Medications**: All prescriptions, status changes, administrations
2. **Investigations**: All orders, starts, completions with results
3. **Therapies**: All therapy sessions, status changes
4. **Notes**: All clinical notes from doctors, nurses, technicians
5. **Other Events**: Admissions, discharges, alert acknowledgments

### Current Implementation Status

**Frontend**: ✅ READY
- PatientCaseService implemented with proper camelCase
- PatientDetailContainer loads case entries properly
- API integration fixed and working
- Error handling in place

**Backend**: ✅ READY
- PatientService.add_case_entry() method exists
- PatientService.get_case_entries() method exists
- API v2 endpoints exist and working
- Repository methods implemented

**Database**: ❌ MISSING TABLE
- `case_entries` table does not exist
- This is why all case sheet calls fail with "relation does not exist"

## Two Implementation Approaches

### Approach 1: Create Missing `case_entries` Table
Create the missing table and use the existing backend infrastructure.

**Pros:**
- Backend code already exists
- Clean separation of case entries
- Proper audit trail

**Cons:**
- Requires database schema change
- Need to populate existing data

### Approach 2: Virtual Case Sheet (Aggregate from Existing Tables)
Modify backend to dynamically create case sheet from existing tables.

**Pros:**
- No new table needed
- All data already exists
- Automatically includes all historical data

**Cons:**
- More complex queries
- Performance considerations
- Backend changes needed

## Recommendation

**Use Approach 1**: Create the missing `case_entries` table.

**Rationale:**
- Backend infrastructure already exists
- Frontend already implemented
- Proper medical record audit trail
- Clean data architecture
- All other medical workflows already create case entries

## Next Steps

1. **Create case_entries table** with proper camelCase schema
2. **Populate historical data** from existing medications, investigations, therapies, notes
3. **Test case sheet functionality** end-to-end
4. **Verify chronological ordering** of all entries

## Database Schema SQL (Needed)

```sql
CREATE TABLE case_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "patientId" TEXT NOT NULL REFERENCES patients(id),
    "entryType" TEXT NOT NULL,
    description TEXT NOT NULL,
    findings TEXT,
    recommendations TEXT,
    "followUpDate" DATE,
    severity TEXT,
    category TEXT,
    "createdBy" TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    "deletedAt" TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_case_entries_patient_id ON case_entries("patientId");
CREATE INDEX idx_case_entries_timestamp ON case_entries(timestamp);
CREATE INDEX idx_case_entries_entry_type ON case_entries("entryType");
```

## Compliance Note
All column names follow **strict camelCase** as required by project standards. No snake_case used.