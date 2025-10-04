# Patient Detail Tabs - Data Fields Analysis

## Overview
This document shows all data fields sent to backend when prescribing/ordering and fields retrieved when opening each tab.

---

## 1. MEDICATIONS TAB

### **When Prescribing New Medication** (POST to `/atomic/patients/{patientId}/medications`)
**Fields Sent:**
```json
{
  "name": "string",              // Medication name
  "dosage": "string",            // e.g., "10mg"
  "frequency": "string",         // e.g., "Twice daily"
  "route": "string",             // PO, IV, IM, SC, Inhaled, Topical
  "duration": "string",          // e.g., "7 days"
  "status": "active",            // Fixed value
  "prescribedBy": "string"       // currentUser.staffId
  // Backend generates: id, startDate, createdAt, canEdit
}
```

### **When Changing Medication Status** (POST to `/atomic/patients/{patientId}/medications/{medicationId}/status`)
**Fields Sent:**
```json
{
  "medication_id": "string",     // Medication ID
  "status": "string",            // active, stopped, held
  "changed_by": "string"         // currentUser.staffId
}
```

### **When Administering Medication** (POST to `/atomic/patients/{patientId}/medications/{medicationId}/administer`)
**Fields Sent:**
```json
{
  "administered_by": "string",   // currentUser.staffId
  "notes": "string"              // Auto-generated description
}
```

### **Fields Retrieved** (GET from `/patients/{patientId}/medications`)
**Backend Returns:**
```json
{
  "id": "string",
  "name": "string",
  "dosage": "string",
  "frequency": "string",
  "route": "string",
  "status": "active | stopped | held | administered",
  "startDate": "string",
  "endDate": "string (optional)",
  "duration": "string (optional)",
  "prescribedBy": "string",
  "prescribedByName": "string (optional)",
  "createdAt": "string",
  "modifiedBy": "string (optional)",
  "updatedAt": "string (optional)",
  "canEdit": "boolean",
  "history": [
    {
      "id": "string",
      "action": "prescribed | held | resumed | stopped | modified | administered",
      "timestamp": "string",
      "performedBy": "string",
      "reason": "string (optional)",
      "previousState": "any (optional)",
      "newState": "any (optional)"
    }
  ]
}
```

---

## 2. INVESTIGATIONS TAB

### **When Ordering New Investigation** (POST to `/atomic/patients/{patientId}/investigations`)
**Fields Sent:**
```json
{
  "name": "string",              // Investigation name
  "type": "string",              // lab, imaging, biopsy, culture
  "priority": "string",          // routine, urgent, stat
  "urgency": "string",           // Fixed: "Routine"
  "notes": "string",             // Special instructions
  "prescribedBy": "string"       // currentUser.staffId
  // Backend generates: id, status, performedBy, createdAt, canEdit
  // Note: Investigation status flow is: pending → ordered → scheduled → inProgress → completed/cancelled
}
```

### **When Starting Investigation** (POST to `/patients/{patientId}/case-entries`)
**Fields Sent:**
```json
{
  "entryType": "investigation",
  "description": "string",       // Auto-generated description
  "performedBy": "string"        // currentUser.staffId
}
```

### **Fields Retrieved** (GET from `/patients/{patientId}/investigations`)
**Backend Returns:**
```json
{
  "id": "string",
  "type": "lab | imaging | biopsy | culture",
  "name": "string",
  "createdAt": "string",
  "orderedAt": "string (optional)",
  "scheduledAt": "string (optional)",
  "completedAt": "string (optional)",
  "status": "pending | ordered | scheduled | inProgress | completed | cancelled",
  "results": "string (optional)",
  "labResults": [
    {
      "id": "string",
      "patientId": "string",
      "testName": "string",
      "testCode": "string",
      "result": "string",
      "normalRange": "string",
      "units": "string",
      "status": "pending | preliminary | final | corrected | cancelled",
      "abnormalFlag": "normal | high | low | criticalHigh | criticalLow",
      "createdAt": "string",
      "completedat": "string",
      "performingLab": "string",
      "performedBy": "string",
      "performedByName": "string (optional)"
    }
  ],
  "performedBy": "string",
  "performedByName": "string (optional)",
  "priority": "routine | urgent | stat",
  "urgency": "STAT | Emergency | Urgent | Routine",
  "notes": "string (optional)",
  "canEdit": "boolean"
}
```

### **Imaging Studies Retrieved** (from backend imaging integration)
```json
{
  "id": "string",
  "patientId": "string",
  "studyType": "xray | ct | mri | ultrasound | mammography | pet | nuclear",
  "bodyPart": "string",
  "createdAt": "string",
  "status": "scheduled | inProgress | completed | cancelled",
  "images": [
    {
      "id": "string",
      "url": "string",
      "thumbnail": "string",
      "series": "string",
      "instanceNumber": "number",
      "viewPosition": "string (optional)"
    }
  ],
  "report": {
    "id": "string",
    "findings": "string",
    "impression": "string",
    "recommendations": "string",
    "performedBy": "string",
    "createdAt": "string",
    "status": "preliminary | final | addendum"
  },
  "performedBy": "string",
  "performedByName": "string (optional)",
  "technologist": "string (optional)",
  "radiologist": "string (optional)",
  "urgency": "routine | urgent | stat"
}
```

---

## 3. THERAPY TAB

### **When Prescribing New Therapy** (POST to `/atomic/patients/{patientId}/therapies`)
**Fields Sent:**
```json
{
  "type": "string",              // physiotherapy, occupational, speech, respiratory
  "description": "string",       // Therapy description
  "frequency": "string",         // e.g., "3x per week"
  "duration": "string"           // e.g., "4 weeks"
  // Backend generates: id, status, performedBy, startDate, canEdit
}
```

### **When Adding Therapy Session** (POST to `/atomic/patients/{patientId}/therapies/{therapyId}/sessions`)
**Fields Sent:**
```json
{
  "therapy_id": "string",        // Therapy ID
  "duration": "number",          // Minutes (integer)
  "notes": "string",             // Session notes
  "performed_by": "string"       // currentUser.staffId
}
```

### **When Completing Therapy** (POST to `/atomic/patients/{patientId}/therapies/{therapyId}/complete`)
**Fields Sent:**
```json
{
  "therapy_id": "string",        // Therapy ID
  "completed_by": "string"       // currentUser.staffId
}
```

### **Fields Retrieved** (GET from `/patients/{patientId}/therapies`)
**Backend Returns:**
```json
{
  "id": "string",
  "type": "physiotherapy | occupational | speech | respiratory",
  "name": "string",
  "description": "string",
  "frequency": "string",
  "duration": "string",
  "startDate": "string",
  "endDate": "string (optional)",
  "status": "active | completed | cancelled",
  "performedBy": "string",
  "performedByName": "string (optional)",
  "therapist": "string (optional)",
  "notes": "string (optional)",
  "sessions": [
    {
      "id": "string",
      "date": "string",
      "duration": "number",       // minutes
      "notes": "string",
      "therapist": "string",
      "patientResponse": "string"
    }
  ],
  "canEdit": "boolean"
}
```

---

## 4. NOTES TAB

### **When Adding New Note** (POST to backend - endpoint in NotesEditor)
**Fields Sent:**
```json
{
  "content": "string",           // Note content
  "authorId": "string"           // currentUser.staffId
  // Backend generates: id, timestamp, authorName (from staff table lookup)
}
```

### **When Editing Note** (PUT to backend - endpoint in NotesEditor)
**Fields Sent:**
```json
{
  "noteId": "string",
  "content": "string",           // Updated content
  "editedBy": "string",          // currentUser.staffId
  // Backend generates: editedAt timestamp
}
```

### **Fields Retrieved** (GET from `/patients/{patientId}/notes`)
**Backend Returns:**
```json
{
  "id": "string",
  "content": "string",
  "timestamp": "string",
  "author": "string",
  "authorId": "string",
  "category": "string",
  "canEdit": "boolean",
  "editedAt": "string (optional)",
  "editedBy": "string (optional)"
}
```

---

## 5. OVERVIEW TAB

### **Fields Retrieved** (GET from `/patients/{patientId}?includeStaff=true`)
**Backend Returns Complete Patient Object:**
```json
{
  "id": "string",
  "firstName": "string",
  "lastName": "string",
  "age": "number",
  "gender": "string",
  "admissionDate": "string",
  "bedNumber": "string",
  "roomNumber": "string",
  "diagnosis": "string",
  "chiefComplaint": "string",
  "status": "string",
  "watchId": "string",
  "lastMedicationTime": "string (optional)",
  "vitals": {
    "heartRate": "number",
    "bloodPressure": "string",
    "temperature": "number",
    "oxygenSaturation": "number",
    "respiratoryRate": "number",
    "timestamp": "string"
  },
  "medications": [ /* medication array */ ],
  "investigations": [ /* investigation array */ ],
  "therapies": [ /* therapy array */ ],
  "notes": [ /* notes array */ ],
  "alerts": [ /* alerts array */ ],
  "caseSheet": [ /* case sheet entries array */ ],
  "staff": {
    /* Staff data for name resolution */
  }
}
```

---

## 6. CASE SHEET TAB

### **Fields Retrieved** (GET from `/patients/{patientId}/case-entries`)
**Backend Returns:**
```json
{
  "id": "string",                // Backend-generated UUID
  "timestamp": "string",         // Backend-generated ISO timestamp
  "type": "string",              // doctorNote, nurseNote, technicianNote, adminNote, etc.
  "description": "string",       // Entry description
  "performedBy": "string",       // Staff ID
  "performedByName": "string (optional)",
  "canEdit": "boolean",
  "details": {
    /* Additional entry-specific details */
  }
}
```

---

## Key Architectural Patterns

### 1. **Single Source of Truth**
- All IDs and timestamps are **backend-generated**
- Frontend **never** creates IDs or timestamps
- After every operation, frontend **refetches** data from backend

### 2. **Atomic Operations**
- Use `/atomic/*` endpoints for operations that need both medical record + case entry
- Backend creates both records in single database transaction
- Guarantees data consistency

### 3. **Field Naming Convention**
- **Strict camelCase** across all layers (database, backend, frontend)
- No snake_case, no PascalCase, no kebab-case
- Consistent field names: `patientId`, `firstName`, `createdAt`, etc.

### 4. **Permission Control**
- `canEdit` field controls UI edit permissions
- Backend validates all operations against user role
- Frontend uses `PermissionUtils` for role-based UI rendering

### 5. **Staff Data Lookup - Single Source of Truth**
- All `prescribedBy` fields send only `staffId` (not staff name)
- All `authorId` fields send only `staffId` (not author name/role)
- Backend performs staff table lookup to populate name fields (`prescribedByName`, `authorName`, `authorRole`)
- Ensures data consistency and avoids redundant data storage
- Database does NOT store staff names redundantly - only IDs with foreign key constraints

---

## Summary Table

| Tab | Action | Endpoint | Fields Sent | Fields Retrieved |
|-----|--------|----------|-------------|------------------|
| Medications | Prescribe | POST `/atomic/patients/{id}/medications` | 6 fields (incl. prescribedBy) | 13+ fields |
| Medications | Change Status | POST `/atomic/patients/{id}/medications/{medId}/status` | 3 fields | - |
| Medications | Administer | POST `/atomic/patients/{id}/medications/{medId}/administer` | 2 fields | - |
| Investigations | Order | POST `/atomic/patients/{id}/investigations` | 6 fields (incl. prescribedBy) | 15+ fields + lab results |
| Investigations | View Imaging | GET from backend | - | Complete imaging studies with DICOM |
| Therapy | Prescribe | POST `/atomic/patients/{id}/therapies` | 5 fields (incl. prescribedBy) | 12+ fields + sessions |
| Therapy | Add Session | POST `/atomic/patients/{id}/therapies/{therapyId}/sessions` | 4 fields | - |
| Notes | Add | POST to backend | 2 fields (content, authorId) | 8+ fields |
| Notes | Edit | PUT to backend | 3 fields | - |
| Overview | View | GET `/patients/{id}?includeStaff=true` | - | Complete patient object |
| Case Sheet | View | GET `/patients/{id}/case-entries` | - | All case entries |

---

*Document Generated: 2025-10-03*
*All data fields follow strict camelCase convention*
*Backend is single source of truth for all medical data*
