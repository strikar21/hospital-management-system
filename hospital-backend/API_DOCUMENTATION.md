# Hospital Management System API Documentation

**Version:** 1.0.0
**Generated:** 2025-09-24 06:23:58

## Overview

The Hospital Management System provides a comprehensive REST API for managing hospital operations, including:
- Patient management and medical records
- Staff authentication and management
- Device assignment and monitoring
- Medication administration tracking
- Audit logging and compliance

## Architecture

### Repository Pattern (v2 Endpoints)
The new v2 endpoints use an optimized repository pattern with:
- **BaseRepository**: Common CRUD operations with automatic camelCase handling
- **Service Layer**: Business logic and data transformation
- **Performance Optimized**: Sub-millisecond query performance with strategic indexing
- **Data Integrity**: Foreign key constraints and referential integrity

### Database Optimizations
- 23 performance indexes for optimal query speed
- 10 foreign key constraints for data integrity
- PostgreSQL quoted identifiers for camelCase support
- Repository query optimization with prepared statements

## Authentication

All endpoints require appropriate authentication:
- **Staff Login**: POST `/api/v1/auth/login`
- **NFC Authentication**: POST `/api/v1/auth/nfc-login`
- **PIN Authentication**: POST `/api/v1/auth/pin-login`

## Base URLs

- **Development**: `http://localhost:8001`
- **API v1**: `http://localhost:8001/api/v1`
- **API v2 (Repository)**: `http://localhost:8001/api/v2`

---

## API Endpoints


### Authentication

#### `POST /api/v1/auth/simple-test`

**Summary:** Simpletest

**Description:** Ultra simple test endpoint to verify POST requests work

**Request Body:**
```json
{
  "type": "object",
  "title": "Data"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v1/auth/debug-auth`

**Summary:** Debugauth

**Description:** Debug auth endpoint - always succeeds

**Responses:**
- `200`: Successful Response

---

#### `GET /api/v1/auth/test`

**Summary:** Authtest

**Description:** Test endpoint to verify auth router is working

**Responses:**
- `200`: Successful Response

---

#### `POST /api/v1/auth/login`

**Summary:** Stafflogin

**Description:** Staff login endpoint - supports staff ID + PIN and NFC card authentication - Uses middleware transformation

**Request Body:**
```json
{
  "$ref": "#/components/schemas/StaffLogin"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v1/auth/logout`

**Summary:** Stafflogout

**Description:** Staff logout endpoint

**Parameters:**
- `staffId` (string) - **Required** - No description

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v1/auth/me/{staffId}`

**Summary:** Getcurrentstaff

**Description:** Get current staff information

**Parameters:**
- `staffId` (string) - **Required** - No description

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v1/auth/nfc-tap`

**Summary:** Nfctaplogin

**Description:** NFC card tap authentication

**Parameters:**
- `nfcCardId` (string) - **Required** - No description

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---


### Patients (v2 - Repository)

#### `GET /api/v2/patients/list`

**Summary:** Get All Patients

**Description:** Get all patients with optional filtering - Repository Pattern Implementation

**Parameters:**
- `status` (string) - Optional - Filter by patient status
- `room_number` (string) - Optional - Filter by room number
- `ward` (string) - Optional - Filter by ward
- `limit` (integer) - Optional - Maximum number of patients to return
- `offset` (integer) - Optional - Number of patients to skip

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v2/patients/{patient_id}`

**Summary:** Get Patient

**Description:** Get complete patient data with medical records

**Parameters:**
- `patient_id` (string) - **Required** - No description

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `PUT /api/v2/patients/{patient_id}`

**Summary:** Update Patient

**Description:** Update patient record

**Parameters:**
- `patient_id` (string) - **Required** - No description

**Request Body:**
```json
{
  "$ref": "#/components/schemas/PatientUpdate"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v2/patients/search/{query}`

**Summary:** Search Patients

**Description:** Search patients by name, ID, or room number

**Parameters:**
- `query` (string) - **Required** - No description
- `limit` (integer) - Optional - Maximum number of results to return

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v2/patients/status/{status}`

**Summary:** Get Patients By Status

**Description:** Get patients filtered by status (stable, critical, emergency, discharged)

**Parameters:**
- `status` (string) - **Required** - No description

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v2/patients/{patient_id}/notes`

**Summary:** Add Patient Note

**Description:** Add note to patient record

**Parameters:**
- `patient_id` (string) - **Required** - No description

**Request Body:**
```json
{
  "type": "object",
  "title": "Note Data"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `PUT /api/v2/patients/{patient_id}/notes/{note_id}`

**Summary:** Edit Patient Note

**Description:** Edit patient note

**Parameters:**
- `patient_id` (string) - **Required** - No description
- `note_id` (string) - **Required** - No description

**Request Body:**
```json
{
  "type": "object",
  "title": "Note Data"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `DELETE /api/v2/patients/{patient_id}/notes/{note_id}`

**Summary:** Delete Patient Note

**Description:** Delete patient note

**Parameters:**
- `patient_id` (string) - **Required** - No description
- `note_id` (string) - **Required** - No description

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v2/patients/{patient_id}/discharge`

**Summary:** Discharge Patient

**Description:** Discharge patient with workflow automation

**Parameters:**
- `patient_id` (string) - **Required** - No description

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v2/patients/{patient_id}/alerts/{alert_id}/acknowledge`

**Summary:** Acknowledge Alert

**Description:** Acknowledge patient alert

**Parameters:**
- `patient_id` (string) - **Required** - No description
- `alert_id` (string) - **Required** - No description

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v2/patients/{patient_id}/case-entries`

**Summary:** Get Case Entries

**Description:** Get all case entries for patient

**Parameters:**
- `patient_id` (string) - **Required** - No description

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v2/patients/{patient_id}/case-entries`

**Summary:** Add Case Entry

**Description:** Add case entry to patient record

**Parameters:**
- `patient_id` (string) - **Required** - No description

**Request Body:**
```json
{
  "type": "object",
  "title": "Entry Data"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v2/patients/create`

**Summary:** Create Patient V2

**Description:** Create new patient record - V2 API endpoint

**Request Body:**
```json
{
  "$ref": "#/components/schemas/PatientCreate"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v2/patients/`

**Summary:** Create Patient

**Description:** Create new patient record

**Request Body:**
```json
{
  "$ref": "#/components/schemas/PatientCreate"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---


### Staff Management

#### `GET /api/v1/staff/test-simple`

**Summary:** Testsimple

**Description:** Simple test endpoint

**Responses:**
- `200`: Successful Response

---

#### `GET /api/v1/staff/`

**Summary:** Getallstaff

**Description:** Get all staff members with optional filtering

**Parameters:**
- `role` (string) - Optional - Filter by staff role
- `department` (string) - Optional - Filter by department
- `activeOnly` (boolean) - Optional - Show only active staff

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v1/staff/`

**Summary:** Createstaffmember

**Description:** Create a new staff member

**Parameters:**
- `createdBy` (string) - **Required** - No description

**Request Body:**
```json
{
  "$ref": "#/components/schemas/StaffCreate"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v1/staff/{staffId}`

**Summary:** Getstaffmember

**Description:** Get a specific staff member

**Parameters:**
- `staffId` (string) - **Required** - No description

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `PUT /api/v1/staff/update/{staffId}`

**Summary:** Updatestaffmember

**Description:** Update an existing staff member

**Parameters:**
- `staffId` (string) - **Required** - No description
- `updatedBy` (string) - **Required** - ID of user making the update

**Request Body:**
```json
{
  "$ref": "#/components/schemas/StaffUpdate"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `PUT /api/v1/staff/deactivate/{staffId}`

**Summary:** Deactivatestaffmember

**Description:** Deactivate a staff member (soft delete)

**Parameters:**
- `staffId` (string) - **Required** - No description
- `deactivatedBy` (string) - **Required** - ID of user performing deactivation

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `PUT /api/v1/staff/change-pin/{staffId}`

**Summary:** Changestaffpin

**Description:** Allow staff to change their PIN (self-service or admin)

**Parameters:**
- `staffId` (string) - **Required** - No description
- `newPin` (string) - **Required** - New 4-digit PIN
- `changedBy` (string) - **Required** - ID of user making the change

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `PUT /api/v1/staff/change-password/{staffId}`

**Summary:** Changestaffpassword

**Description:** Allow staff to change their password (self-service or admin)

**Parameters:**
- `staffId` (string) - **Required** - No description
- `newPassword` (string) - **Required** - New password
- `changedBy` (string) - **Required** - ID of user making the change

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `PUT /api/v1/staff/toggle-card/{staffId}`

**Summary:** Togglestaffcard

**Description:** Enable or disable staff NFC card access (security management)

**Parameters:**
- `staffId` (string) - **Required** - No description
- `enable` (boolean) - **Required** - True to enable card, False to disable
- `changedBy` (string) - **Required** - ID of user making the change

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `PUT /api/v1/staff/reassign-department/{staffId}`

**Summary:** Reassignstaffdepartment

**Description:** Reassign staff to different department/ward

**Parameters:**
- `staffId` (string) - **Required** - No description
- `newDepartment` (string) - **Required** - New department/ward name
- `changedBy` (string) - **Required** - ID of user making the change

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `PUT /api/v1/staff/soft-delete/{staffId}`

**Summary:** Softdeletestaff

**Description:** Soft delete staff (disable login, clear card, keep data)

**Parameters:**
- `staffId` (string) - **Required** - No description
- `deletedBy` (string) - **Required** - ID of user performing soft delete

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `PUT /api/v1/staff/issue-new-card/{staffId}`

**Summary:** Issuenewnfccard

**Description:** Issue a new NFC card to staff (replacement for lost/damaged cards)

**Parameters:**
- `staffId` (string) - **Required** - No description
- `cardId` (string) - Optional - Optional custom card ID, auto-generated if not provided
- `issuedBy` (string) - **Required** - ID of user issuing the card

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `PUT /api/v1/staff/replace-lost-card/{staffId}`

**Summary:** Replacelostnfccard

**Description:** Replace lost/damaged/stolen NFC card with security logging

**Parameters:**
- `staffId` (string) - **Required** - No description
- `reason` (string) - Optional - Reason for replacement: lost, damaged, stolen, expired
- `replacedBy` (string) - **Required** - ID of user processing replacement

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `PUT /api/v1/staff/update-card-id/{staffId}`

**Summary:** Updatenfccardid

**Description:** Update/change NFC card ID for administrative purposes

**Parameters:**
- `staffId` (string) - **Required** - No description
- `newCardId` (string) - **Required** - New card ID to assign
- `updatedBy` (string) - **Required** - ID of user making the update

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v1/staff/card-status/{staffId}`

**Summary:** Getnfccardstatus

**Description:** Get current NFC card status for a staff member

**Parameters:**
- `staffId` (string) - **Required** - No description

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v1/staff/cards/list`

**Summary:** Listallnfccards

**Description:** List all NFC cards in the system (for admin management)

**Parameters:**
- `activeOnly` (boolean) - Optional - Show only active cards
- `department` (string) - Optional - Filter by department

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v1/staff/roles/list`

**Summary:** Getroleslist

**Description:** Get list of available staff roles for frontend dropdown

**Responses:**
- `200`: Successful Response

---

#### `GET /api/v1/staff/departments/list`

**Summary:** Getdepartmentslist

**Description:** Get list of available departments for frontend dropdown

**Responses:**
- `200`: Successful Response

---

#### `GET /api/v1/staff/generate-id/{role}`

**Summary:** Generatestaffid

**Description:** Generate next available staff ID for given role

**Parameters:**
- `role` (string) - **Required** - No description

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---


### Medical Records (v2)

#### `GET /api/v2/medications/patient/{patient_id}`

**Summary:** Get Patient Medications

**Description:** Get all medications for a patient

**Parameters:**
- `patient_id` (string) - **Required** - No description

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v2/medications/patient/{patient_id}`

**Summary:** Add Medication

**Description:** Add medication to patient

**Parameters:**
- `patient_id` (string) - **Required** - No description

**Request Body:**
```json
{
  "type": "object",
  "title": "Medication Data"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `PUT /api/v2/medications/patient/{patient_id}/{medication_id}/status`

**Summary:** Update Medication Status

**Description:** Update medication status

**Parameters:**
- `patient_id` (string) - **Required** - No description
- `medication_id` (string) - **Required** - No description

**Request Body:**
```json
{
  "type": "object",
  "title": "Status Data"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v2/investigations/patient/{patient_id}`

**Summary:** Get Patient Investigations

**Description:** Get all investigations for a patient

**Parameters:**
- `patient_id` (string) - **Required** - No description

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v2/investigations/patient/{patient_id}`

**Summary:** Add Investigation

**Description:** Add investigation to patient

**Parameters:**
- `patient_id` (string) - **Required** - No description

**Request Body:**
```json
{
  "type": "object",
  "title": "Investigation Data"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `PUT /api/v2/investigations/patient/{patient_id}/{investigation_id}/status`

**Summary:** Update Investigation Status

**Description:** Update investigation status

**Parameters:**
- `patient_id` (string) - **Required** - No description
- `investigation_id` (string) - **Required** - No description

**Request Body:**
```json
{
  "type": "object",
  "title": "Status Data"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v2/investigations/patient/{patient_id}/{investigation_id}/complete`

**Summary:** Complete Investigation

**Description:** Complete investigation with results

**Parameters:**
- `patient_id` (string) - **Required** - No description
- `investigation_id` (string) - **Required** - No description

**Request Body:**
```json
{
  "type": "object",
  "title": "Completion Data"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v2/therapy/patient/{patient_id}`

**Summary:** Get Patient Therapy Sessions

**Description:** Get all therapy sessions for a patient

**Parameters:**
- `patient_id` (string) - **Required** - No description

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v2/therapy/patient/{patient_id}`

**Summary:** Add Therapy Session

**Description:** Add therapy session to patient

**Parameters:**
- `patient_id` (string) - **Required** - No description

**Request Body:**
```json
{
  "type": "object",
  "title": "Session Data"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `PUT /api/v2/therapy/patient/{patient_id}/{session_id}/status`

**Summary:** Update Therapy Session Status

**Description:** Update therapy session status

**Parameters:**
- `patient_id` (string) - **Required** - No description
- `session_id` (string) - **Required** - No description

**Request Body:**
```json
{
  "type": "object",
  "title": "Status Data"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v2/therapy/patient/{patient_id}/{session_id}/complete`

**Summary:** Complete Therapy Session

**Description:** Complete therapy session with notes

**Parameters:**
- `patient_id` (string) - **Required** - No description
- `session_id` (string) - **Required** - No description

**Request Body:**
```json
{
  "type": "object",
  "title": "Completion Data"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v2/therapy/types`

**Summary:** Get Therapy Types

**Description:** Get available therapy types

**Responses:**
- `200`: Successful Response

---


### Device Management

#### `POST /api/v1/esp32/provision`

**Summary:** Provisionesp32Device

**Description:** Provision new ESP32 device with automatic serial assignment
Validates provisioner credentials and assigns device ID/serial

**Request Body:**
```json
{
  "type": "object",
  "title": "Provisiondata"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v1/esp32/online`

**Summary:** Deviceonline

**Description:** Mark device as online after successful provisioning

**Request Body:**
```json
{
  "type": "object",
  "title": "Statusdata"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v1/esp32/register`

**Summary:** Registeresp32Device

**Description:** Register ESP32 device in the system
Called by ESP32 on startup

**Request Body:**
```json
{
  "type": "object",
  "title": "Devicedata"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v1/esp32/{deviceId}/heartbeat`

**Summary:** Deviceheartbeat

**Description:** Receive heartbeat from ESP32 device
Updates device status and battery level

**Parameters:**
- `deviceId` (string) - **Required** - No description

**Request Body:**
```json
{
  "type": "object",
  "title": "Heartbeatdata"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v1/esp32/{deviceId}/vitals/{patientId}`

**Summary:** Receivevitalsdata

**Description:** Receive vitals data from ESP32 device
Stores in TimescaleDB and broadcasts to WebSocket subscribers

**Parameters:**
- `deviceId` (string) - **Required** - No description
- `patientId` (string) - **Required** - No description

**Request Body:**
```json
{
  "type": "object",
  "title": "Vitalsdata"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v1/esp32/{deviceId}/alert`

**Summary:** Receiveemergencyalert

**Description:** Receive emergency alert from ESP32 device

**Parameters:**
- `deviceId` (string) - **Required** - No description

**Request Body:**
```json
{
  "type": "object",
  "title": "Alertdata"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v1/esp32/door-scanner/{scannerId}/scan`

**Summary:** Doorscannerdetection

**Description:** Receive BLE device detection from door scanner ESP32
Tracks which devices (watches/tablets) are in which rooms

**Parameters:**
- `scannerId` (string) - **Required** - No description

**Request Body:**
```json
{
  "type": "object",
  "title": "Scandata"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v1/devices/types`

**Summary:** Getdevicetypes

**Description:** Get all supported device types

**Responses:**
- `200`: Successful Response

---

#### `POST /api/v1/devices/`

**Summary:** Createdevice

**Description:** Add a new device to the hospital inventory

**Parameters:**
- `createdBy` (string) - **Required** - Staff ID creating the device

**Request Body:**
```json
{
  "type": "object",
  "title": "Devicedata"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v1/devices/`

**Summary:** Listdevices

**Description:** List all devices in the hospital inventory with optional filtering

**Parameters:**
- `deviceType` (string) - Optional - Filter by device type
- `status` (string) - Optional - Filter by status
- `location` (string) - Optional - Filter by location
- `limit` (integer) - Optional - Maximum number of devices to return

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v1/devices/{deviceId}`

**Summary:** Getdevice

**Description:** Get detailed information about a specific device

**Parameters:**
- `deviceId` (string) - **Required** - No description

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `PUT /api/v1/devices/{deviceId}`

**Summary:** Updatedevice

**Description:** Update device properties

**Parameters:**
- `deviceId` (string) - **Required** - No description
- `updatedBy` (string) - **Required** - Staff ID updating the device

**Request Body:**
```json
{
  "type": "object",
  "title": "Updatedata"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `DELETE /api/v1/devices/{deviceId}`

**Summary:** Removedevice

**Description:** Remove a device from the hospital inventory (soft delete unless force=True)

**Parameters:**
- `deviceId` (string) - **Required** - No description
- `deletedBy` (string) - **Required** - Staff ID removing the device
- `force` (boolean) - Optional - No description

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v1/devices/location/{location}`

**Summary:** Getdevicesbylocation

**Description:** Get all devices in a specific location (room, department, etc.)

**Parameters:**
- `location` (string) - **Required** - No description

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v1/devices/status/health`

**Summary:** Getdevicehealthstatus

**Description:** Get overall device health status across the hospital

**Responses:**
- `200`: Successful Response

---


### System Administration

#### `POST /api/v1/admission/recommendations`

**Summary:** Createadmissionrecommendation

**Description:** Create a new admission recommendation from doctor assessment

**Request Body:**
```json
{
  "type": "object",
  "title": "Admissiondata"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v1/admission/recommendations`

**Summary:** Getadmissionrecommendations

**Description:** Get admission recommendations with optional status filter

**Parameters:**
- `status` (string) - Optional - No description

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v1/dischargeworkflow/test`

**Summary:** Testendpoint

**Description:** Test endpoint to verify router is working

**Responses:**
- `200`: Successful Response

---

#### `POST /api/v1/dischargeworkflow/doctor-request`

**Summary:** Doctorrequestdischarge

**Description:** Doctor requests discharge for a patient

**Request Body:**
```json
{
  "$ref": "#/components/schemas/DischargeRequest"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v1/dischargeworkflow/admin-approval`

**Summary:** Adminapprovedischarge

**Description:** Hospital Administrator approves discharge request

**Request Body:**
```json
{
  "$ref": "#/components/schemas/AdminApprovalRequest"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v1/dischargeworkflow/nurse-discharge`

**Summary:** Nursecompletedischarge

**Description:** Nurse completes the discharge process

**Parameters:**
- `patientId` (string) - **Required** - No description
- `nurseId` (string) - **Required** - Nurse ID completing discharge
- `dischargeNotes` (string) - Optional - Final discharge notes

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v1/dischargeworkflow/nurse-approve`

**Summary:** Nurseapprovedischarge

**Description:** Nurse approves discharge for a patient

**Parameters:**
- `patientId` (string) - **Required** - No description
- `nurseId` (string) - **Required** - Nurse ID approving discharge
- `dischargeNotes` (string) - Optional - Discharge notes

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v1/dischargeworkflow/pending`

**Summary:** Getpendingdischarges

**Description:** Get list of pending discharge requests (simplified - returns empty list for now)

**Parameters:**
- `staffId` (string) - **Required** - Staff ID requesting pending discharges

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v1/admin/reset-connections`

**Summary:** Resetconnections

**Description:** Reset database connection pools to force fresh connections

**Responses:**
- `200`: Successful Response

---

#### `GET /api/v1/admin/health`

**Summary:** Healthcheck

**Description:** System health check

**Responses:**
- `200`: Successful Response

---

#### `POST /api/v1/admin/audit/log`

**Summary:** Createauditlog

**Description:** Create an audit log entry (frontend logging endpoint) - handles lowercase fields

**Responses:**
- `200`: Successful Response

---

#### `GET /api/v1/admin/audit/logs`

**Summary:** Getauditlogs

**Description:** Get audit logs with optional filtering

**Parameters:**
- `userId` (string) - Optional - No description
- `action` (string) - Optional - No description
- `limit` (integer) - Optional - No description

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v1/admin/log`

**Summary:** Createauditlogalias

**Description:** Backward compatibility alias for /audit/log

**Responses:**
- `200`: Successful Response

---

#### `GET /api/v1/admin/logs`

**Summary:** Getauditlogsalias

**Description:** Backward compatibility alias for /audit/logs

**Parameters:**
- `userId` (string) - Optional - No description
- `action` (string) - Optional - No description
- `limit` (integer) - Optional - No description

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v1/nursing/ward/{wardName}/dashboard`

**Summary:** Getwarddashboard

**Description:** Get comprehensive ward dashboard with all patients and their clinical status

**Parameters:**
- `wardName` (string) - **Required** - No description
- `shift` (string) - Optional - nursing shift filter

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v1/nursing/medication-alerts`

**Summary:** Getmedicationalerts

**Description:** Get medication administration alerts for nursing staff

**Parameters:**
- `ward` (string) - Optional - Ward filter
- `hoursAhead` (integer) - Optional - Hours to look ahead for due medications

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v1/nursing/therapy-schedule`

**Summary:** Gettherapyschedule

**Description:** Get therapy session schedule for nursing coordination

**Parameters:**
- `ward` (string) - Optional - Ward filter
- `date` (string) - Optional - Date filter (YYYY-MM-DD)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v1/nursing/medication-administration/{administrationId}/administer`

**Summary:** Administermedication

**Description:** Mark medication as administered

**Parameters:**
- `administrationId` (string) - **Required** - No description
- `administeredBy` (string) - **Required** - No description
- `notes` (string) - Optional - No description

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v1/nursing/therapy-session/{sessionId}/complete`

**Summary:** Completetherapysession

**Description:** Mark therapy session as completed

**Parameters:**
- `sessionId` (string) - **Required** - No description
- `performedBy` (string) - **Required** - No description
- `sessionNotes` (string) - Optional - No description
- `duration` (string) - Optional - No description

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v1/watchmanagement/available`

**Summary:** Getavailablewatches

**Description:** Get all available ESP32 watches for assignment

**Responses:**
- `200`: Successful Response

---

#### `GET /api/v1/watchmanagement/assigned`

**Summary:** Getassignedwatches

**Description:** Get all currently assigned watches with patient information

**Responses:**
- `200`: Successful Response

---

#### `POST /api/v1/watchmanagement/assign`

**Summary:** Assignwatchtopatient

**Description:** Assign an ESP32 watch to a patient

**Request Body:**
```json
{
  "type": "object",
  "title": "Assignmentdata"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v1/watchmanagement/unassign`

**Summary:** Unassignwatchfrompatient

**Description:** Unassign an ESP32 watch from a patient

**Request Body:**
```json
{
  "type": "object",
  "title": "Unassignmentdata"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `GET /api/v1/watchmanagement/connection-status`

**Summary:** Getwatchconnectionstatus

**Description:** Get connection status of all watches

**Responses:**
- `200`: Successful Response

---

#### `GET /api/v1/watchmanagement/alerts`

**Summary:** Getwatchalerts

**Description:** Get current watch-related alerts (disconnect, low battery, etc.)

**Responses:**
- `200`: Successful Response

---

#### `GET /working-patients`

**Summary:** Getpatientsworking

**Description:** Working patients list endpoint - bypasses problematic router

**Responses:**
- `200`: Successful Response

---

#### `GET /`

**Summary:** Root

**Description:** Root endpoint

**Responses:**
- `200`: Successful Response

---


### WebSocket

#### `GET /api/v1/ws/connections/status`

**Summary:** Getwebsocketstatus

**Description:** Get current WebSocket connection status

**Responses:**
- `200`: Successful Response

---

#### `POST /api/v1/ws/broadcast/vitals/{patientId}`

**Summary:** Broadcastvitalsupdate

**Description:** Manually broadcast vitals update to subscribers
Used for testing or external integrations - requires deviceId validation

**Parameters:**
- `patientId` (string) - **Required** - No description
- `deviceId` (string) - **Required** - Device ID sending vitals

**Request Body:**
```json
{
  "type": "object",
  "title": "Vitalsdata"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v1/ws/broadcast/medication/{patientId}`

**Summary:** Broadcastmedicationupdate

**Description:** Manually broadcast medication update to subscribers
Used for testing or external integrations

**Parameters:**
- `patientId` (string) - **Required** - No description

**Request Body:**
```json
{
  "type": "object",
  "title": "Medicationdata"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

#### `POST /api/v1/ws/broadcast/alert`

**Summary:** Broadcastalert

**Description:** Broadcast alert to all or patient-specific subscribers

**Request Body:**
```json
{
  "type": "object",
  "title": "Alertdata"
}
```

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---


### Health & Monitoring

#### `GET /health`

**Summary:** Healthcheck

**Description:** Health check endpoint

**Responses:**
- `200`: Successful Response

---


## Repository Pattern Examples (v2 Endpoints)

### Patient Management

#### List Patients
```bash
GET /api/v2/patients/list?limit=20&offset=0&status=active
```

**Response:**
```json
{
  "patients": [
    {
      "id": "patient-123",
      "firstName": "John",
      "lastName": "Doe",
      "status": "active",
      "roomNumber": "101",
      "assignedDeviceId": "device-456",
      "createdAt": "2023-01-15T10:30:00Z",
      "canEdit": true,
      "age": 45
    }
  ],
  "total": 1,
  "success": true
}
```

#### Get Patient Details
```bash
GET /api/v2/patients/patient-123
```

#### Create Patient
```bash
POST /api/v2/patients/create
Content-Type: application/json

{
  "firstName": "Jane",
  "lastName": "Smith",
  "dateOfBirth": "1980-05-15",
  "gender": "female",
  "phoneNumber": "+1234567890",
  "emergencyContactName": "John Smith",
  "emergencyContactPhone": "+1234567891"
}
```

### Medical Records

#### Patient Medications
```bash
GET /api/v2/medications/patient/patient-123
```

#### Patient Investigations
```bash
GET /api/v2/investigations/patient/patient-123
```

#### Patient Therapy
```bash
GET /api/v2/therapy/patient/patient-123
```

## Performance Characteristics

### Query Performance (Post-Optimization)
- **Patient list queries**: < 1.5ms average
- **Medical record lookups**: < 1ms average
- **Device management**: < 1ms average
- **Staff authentication**: < 1ms average
- **Audit queries**: < 0.5ms average

### Database Optimizations
- **23 strategic indexes** for optimal query performance
- **10 foreign key constraints** for referential integrity
- **PostgreSQL quoted identifiers** for camelCase support
- **Repository pattern** with prepared statements

## Error Handling

All endpoints return consistent error responses:

```json
{
  "detail": "Error description",
  "status": "error",
  "timestamp": "2023-01-15T10:30:00Z"
}
```

Common HTTP status codes:
- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `422`: Validation Error
- `500`: Internal Server Error

## Rate Limiting

API endpoints are subject to rate limiting:
- **Authentication endpoints**: 10 requests/minute per IP
- **Data modification**: 100 requests/minute per user
- **Read operations**: 1000 requests/minute per user

## Data Formats

### Timestamps
All timestamps are in ISO 8601 format with UTC timezone:
```
2023-01-15T10:30:00Z
```

### Dates
Date fields use ISO 8601 date format:
```
2023-01-15
```

### Patient Status
- `active`: Currently admitted
- `discharged`: Discharged from hospital
- `transferred`: Transferred to another facility

### Device Status
- `active`: Device in use
- `inactive`: Device available
- `maintenance`: Device under maintenance
- `decommissioned`: Device retired

## WebSocket Events

Real-time updates are available via WebSocket connection:

### Connection
```javascript
const ws = new WebSocket('ws://localhost:8001/api/v1/ws');
```

### Event Types
- `patient_vitals`: Real-time vital signs
- `device_status`: Device connection status
- `medication_alert`: Medication reminders
- `system_alert`: System notifications

## Security

### Data Encryption
- All API communications over HTTPS in production
- Sensitive data encrypted at rest
- JWT tokens for session management

### Compliance
- HIPAA compliant data handling
- Audit logging for all data access
- Role-based access control

## Support

For API support and documentation updates:
- **GitHub Issues**: Report bugs and feature requests
- **API Changes**: Monitor for breaking changes
- **Performance Issues**: Check database optimization status

---

*This documentation is auto-generated from the OpenAPI schema and updated with each deployment.*
