# DEVICE MANAGEMENT END-TO-END TEST PLAN
## Complete Frontend-to-Backend Device Workflow Testing
**Created:** October 13, 2025
**Test Type:** Comprehensive End-to-End Functional Testing
**Test Engineer:** Senior QA + Senior Backend + Senior Frontend Engineers
**Test Scope:** Device Pool Management, Assignment, Modification, Monitoring

---

## EXECUTIVE SUMMARY

This document provides a **complete test plan** for testing all device management features from frontend UI through backend API to database persistence. Every feature, edge case, error scenario, and data flow will be tested.

### System Under Test:
- **Frontend**: React TypeScript device management components
- **Backend**: FastAPI device management and watch management endpoints
- **Database**: PostgreSQL `devices` and `deviceassignments` tables
- **Real-time**: MQTT/WebSocket device status updates

### Test Methodology:
1. **Unit Testing**: Individual API endpoints
2. **Integration Testing**: Frontend-to-Backend workflows
3. **E2E Testing**: Complete user journeys
4. **Stress Testing**: Concurrent operations, race conditions
5. **Security Testing**: RBAC, authentication, authorization

---

## TEST ENVIRONMENT SETUP

### Prerequisites:
```bash
✅ Backend running on port 8001
✅ Frontend running on port 3000
✅ PostgreSQL database accessible
✅ TimescaleDB database accessible
✅ Test user accounts with different roles:
   - DOC0001 (Doctor - can assign/unassign)
   - NUR0001 (Nurse - can assign/unassign)
   - ADM0001 (Administrator - full access)
   - TEC0001 (Technician - limited access)
```

### Test Data Setup:
```sql
-- Create test devices
INSERT INTO devices (id, "deviceType", name, "serialNumber", "macAddress", "firmwareVersion", status, location, "createdAt", "updatedAt")
VALUES
  ('WATCH_TEST001', 'watch', 'Test Watch 001', 'ESP32-001', 'AA:BB:CC:DD:EE:01', 'v1.2.3', 'available', 'ICU', NOW(), NOW()),
  ('WATCH_TEST002', 'watch', 'Test Watch 002', 'ESP32-002', 'AA:BB:CC:DD:EE:02', 'v1.2.3', 'available', 'Ward A', NOW(), NOW()),
  ('WATCH_TEST003', 'watch', 'Test Watch 003', 'ESP32-003', 'AA:BB:CC:DD:EE:03', 'v1.2.3', 'assigned', 'Ward B', NOW(), NOW()),
  ('TABLET_TEST001', 'tablet', 'Test Tablet 001', 'TAB-001', 'AA:BB:CC:DD:EE:11', 'v2.0.0', 'available', 'Nursing Station', NOW(), NOW());

-- Create test patients
INSERT INTO patients (id, "firstName", "lastName", "dateOfBirth", gender, "phoneNumber", "admissionDate", "roomNumber", "bedNumber", status, "createdAt", "updatedAt")
VALUES
  ('TEST_PAT_001', 'John', 'Doe', '1980-01-15', 'Male', '1234567890', NOW(), 'ICU-101', 'B1', 'active', NOW(), NOW()),
  ('TEST_PAT_002', 'Jane', 'Smith', '1975-05-20', 'Female', '0987654321', NOW(), 'WARD-A-201', 'B2', 'active', NOW(), NOW()),
  ('TEST_PAT_003', 'Bob', 'Johnson', '1990-08-10', 'Male', '1122334455', NOW(), 'WARD-B-301', 'B3', 'active', NOW(), NOW());

-- Create existing assignment for WATCH_TEST003
INSERT INTO deviceassignments ("patientId", "deviceId", "assignedBy", "assignedAt", status)
VALUES ('TEST_PAT_003', 'WATCH_TEST003', 'DOC0001', NOW(), 'active');
```

---

## TEST SUITE 1: DEVICE POOL MANAGEMENT

### Test Case 1.1: View Available Devices (GET /api/v1/devices/available)

**Objective**: Verify frontend can retrieve and display available devices

**Steps**:
1. Login as DOC0001 (Doctor)
2. Navigate to Device Management screen
3. Click "Device Pool" tab
4. Verify available devices list displays

**Expected Result**:
```json
{
  "success": true,
  "devices": [
    {
      "id": "WATCH_TEST001",
      "deviceType": "watch",
      "name": "Test Watch 001",
      "serialNumber": "ESP32-001",
      "status": "available",
      "location": "ICU",
      "connectionStatus": "offline",
      "batteryLevel": null,
      "lastSeen": null
    },
    {
      "id": "WATCH_TEST002",
      "deviceType": "watch",
      "name": "Test Watch 002",
      "serialNumber": "ESP32-002",
      "status": "available",
      "location": "Ward A",
      "connectionStatus": "offline",
      "batteryLevel": null,
      "lastSeen": null
    }
  ],
  "count": 2
}
```

**Frontend Validation**:
- ✅ Available devices card shows count: 2
- ✅ Each device displays name, serial number, location
- ✅ Battery indicator shows (if applicable)
- ✅ Connection status dot is red (offline) or green (connected)
- ✅ "Available" badge is displayed

**Database Verification**:
```sql
SELECT id, "deviceType", name, status FROM devices WHERE status = 'available';
-- Expected: 2 rows (WATCH_TEST001, WATCH_TEST002)
```

**Test Result**: [ ] PASS [ ] FAIL
**Notes**: ___________________________________________

---

### Test Case 1.2: Filter Devices by Type

**Objective**: Verify device filtering by type works correctly

**Steps**:
1. On Device Pool tab
2. Click device type filter dropdown
3. Select "watch"
4. Verify only watch devices are shown

**Expected Result**:
- Only devices with `deviceType='watch'` are displayed
- Tablets and other devices are hidden

**API Call**:
```
GET /api/v1/devices/available?deviceType=watch
```

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 1.3: Filter Devices by Location

**Objective**: Verify device filtering by location works correctly

**Steps**:
1. On Device Pool tab
2. Enter "ICU" in location filter
3. Verify only ICU devices are shown

**Expected Result**:
- Only devices with `location` containing "ICU" are displayed

**API Call**:
```
GET /api/v1/devices/available?location=ICU
```

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 1.4: View Pool Status Summary

**Objective**: Verify device pool statistics are accurate

**Steps**:
1. View Device Pool Overview section
2. Verify statistics match database

**Expected Result**:
```
Total Devices: 4
Available Devices: 3 (excluding assigned WATCH_TEST003)
Assigned Devices: 1 (WATCH_TEST003)
Offline Devices: 4 (none have recent lastSeen)
Low Battery: 0
```

**Database Verification**:
```sql
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE status = 'available') as available,
  COUNT(*) FILTER (WHERE status = 'assigned') as assigned
FROM devices;
```

**Test Result**: [ ] PASS [ ] FAIL

---

## TEST SUITE 2: DEVICE CREATION (ADD TO POOL)

### Test Case 2.1: Create New Device (Admin Only)

**Objective**: Verify only administrators can add devices to pool

**Steps**:
1. Login as ADM0001 (Administrator)
2. Navigate to Device Management
3. Click "Add Device" button
4. Fill device creation form:
   - Device Type: watch
   - Name: Test Watch 004
   - Serial Number: ESP32-004
   - MAC Address: AA:BB:CC:DD:EE:04
   - Firmware Version: v1.2.3
   - Location: Emergency
   - Description: Test device for QA
5. Click "Create Device"

**Expected API Call**:
```http
POST /api/v1/devices/ HTTP/1.1
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "deviceType": "watch",
  "name": "Test Watch 004",
  "serialNumber": "ESP32-004",
  "macAddress": "AA:BB:CC:DD:EE:04",
  "firmwareVersion": "v1.2.3",
  "location": "Emergency",
  "description": "Test device for QA"
}
```

**Expected Response**:
```json
{
  "success": true,
  "device": {
    "id": "WATCH_<UUID>",
    "deviceType": "watch",
    "name": "Test Watch 004",
    "serialNumber": "ESP32-004",
    "status": "available",
    "createdAt": "<timestamp>",
    "updatedAt": "<timestamp>"
  },
  "message": "Device Test Watch 004 added to inventory"
}
```

**Database Verification**:
```sql
SELECT * FROM devices WHERE "serialNumber" = 'ESP32-004';
-- Expected: 1 row with all fields populated
```

**Audit Log Verification**:
```sql
SELECT * FROM auditlog WHERE action = 'DEVICE_CREATED' AND "resourceId" = '<device_id>';
-- Expected: 1 row with userId = 'ADM0001'
```

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 2.2: Create Device - Validation Errors

**Objective**: Verify field validation works correctly

**Test 2.2a: Missing Required Fields**

**Steps**:
1. Attempt to create device with missing `name` field

**Expected Response**:
```json
{
  "status_code": 400,
  "detail": "Missing required field: name"
}
```

**Test 2.2b: Invalid Device Type**

**Steps**:
1. Attempt to create device with `deviceType: "invalid"`

**Expected Response**:
```json
{
  "status_code": 400,
  "detail": "Invalid device type. Must be one of: ['tablet', 'watch', 'sensor', ...]"
}
```

**Test 2.2c: Duplicate Serial Number**

**Steps**:
1. Attempt to create device with existing serial number "ESP32-001"

**Expected Response**:
```json
{
  "status_code": 500,
  "detail": "Failed to create device: duplicate key value violates unique constraint"
}
```

**Test Result 2.2a**: [ ] PASS [ ] FAIL
**Test Result 2.2b**: [ ] PASS [ ] FAIL
**Test Result 2.2c**: [ ] PASS [ ] FAIL

---

### Test Case 2.3: Create Device - RBAC Enforcement

**Objective**: Verify non-admins cannot create devices

**Steps**:
1. Login as DOC0001 (Doctor - not admin)
2. Attempt to POST to `/api/v1/devices/`

**Expected Response**:
```json
{
  "status_code": 403,
  "detail": "Insufficient permissions. Required role: Administrator"
}
```

**Test Result**: [ ] PASS [ ] FAIL

---

## TEST SUITE 3: DEVICE ASSIGNMENT WORKFLOW

### Test Case 3.1: Assign Device to Patient (Happy Path)

**Objective**: Verify successful device assignment workflow

**Steps**:
1. Login as DOC0001 (Doctor)
2. Navigate to Device Assignment screen
3. Select patient: TEST_PAT_001 (John Doe)
4. Select device: WATCH_TEST001 (Test Watch 001)
5. Select assignment reason: "Patient Admission"
6. Click "Assign Device"

**Expected API Calls**:

**Call 1: Get Available Watches**
```http
GET /api/v1/watchmanagement/available HTTP/1.1
Authorization: Bearer <token>
```

**Call 2: Get Patients**
```http
GET /api/v2/patients HTTP/1.1
Authorization: Bearer <token>
```

**Call 3: Assign Device**
```http
POST /api/v1/watchmanagement/assign HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "deviceId": "WATCH_TEST001",
  "patientId": "TEST_PAT_001"
}
```

**Expected Response**:
```json
{
  "success": true,
  "assignmentId": 12345,
  "message": "Watch ESP32-001 assigned to John Doe"
}
```

**Database Verification**:

**Check deviceassignments table**:
```sql
SELECT * FROM deviceassignments
WHERE "deviceId" = 'WATCH_TEST001' AND "patientId" = 'TEST_PAT_001' AND status = 'active';
-- Expected: 1 row with assignedBy = 'DOC0001', assignedAt = NOW()
```

**Check devices table**:
```sql
SELECT status FROM devices WHERE id = 'WATCH_TEST001';
-- Expected: status = 'assigned'
```

**Frontend Validation**:
- ✅ Success message: "Device assigned successfully"
- ✅ Device removed from available list
- ✅ Device appears in assigned devices list
- ✅ Assignment shown with patient name, location, assigned date
- ✅ Device status badge shows "Assigned"

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 3.2: Assign Device - Validation Errors

**Test 3.2a: Missing Patient ID**

**Steps**:
1. Attempt to assign device without selecting patient

**Expected Frontend Validation**:
- Form validation error: "Please select a patient"
- Assign button remains disabled

**Expected Backend Response (if bypassed)**:
```json
{
  "status_code": 400,
  "detail": "Patient ID and Device ID are required"
}
```

**Test 3.2b: Missing Device ID**

**Steps**:
1. Attempt to assign without selecting device

**Expected**: Same as 3.2a (missing device ID)

**Test 3.2c: Patient Not Found**

**Steps**:
1. Attempt to assign to non-existent patient ID: "INVALID_PATIENT"

**Expected Response**:
```json
{
  "status_code": 404,
  "detail": "Active patient not found"
}
```

**Test 3.2d: Device Not Available**

**Steps**:
1. Attempt to assign already-assigned device WATCH_TEST003

**Expected Response**:
```json
{
  "status_code": 404,
  "detail": "Available watch not found"
}
```

**Test 3.2e: Patient Already Has Device**

**Steps**:
1. Assign WATCH_TEST001 to TEST_PAT_001 (succeeds)
2. Attempt to assign WATCH_TEST002 to TEST_PAT_001 (should fail)

**Expected Response**:
```json
{
  "status_code": 400,
  "detail": "Patient already has a watch assigned"
}
```

**Database Verification**:
```sql
-- Should still only have 1 active assignment for patient
SELECT COUNT(*) FROM deviceassignments
WHERE "patientId" = 'TEST_PAT_001' AND status = 'active';
-- Expected: 1 (not 2)
```

**Test Result 3.2a**: [ ] PASS [ ] FAIL
**Test Result 3.2b**: [ ] PASS [ ] FAIL
**Test Result 3.2c**: [ ] PASS [ ] FAIL
**Test Result 3.2d**: [ ] PASS [ ] FAIL
**Test Result 3.2e**: [ ] PASS [ ] FAIL

---

### Test Case 3.3: Assign Device - RBAC Enforcement

**Objective**: Verify only medical staff can assign devices

**Test 3.3a: Doctor Can Assign**

**Steps**:
1. Login as DOC0001 (Doctor)
2. Assign device to patient

**Expected**: SUCCESS (doctors have `require_medical_staff` access)

**Test 3.3b: Nurse Can Assign**

**Steps**:
1. Login as NUR0001 (Nurse)
2. Assign device to patient

**Expected**: SUCCESS (nurses have `require_medical_staff` access)

**Test 3.3c: Technician Cannot Assign**

**Steps**:
1. Login as TEC0001 (Technician)
2. Attempt to assign device

**Expected Response**:
```json
{
  "status_code": 403,
  "detail": "Insufficient permissions. Required role: Doctor or Nurse"
}
```

**Test Result 3.3a**: [ ] PASS [ ] FAIL
**Test Result 3.3b**: [ ] PASS [ ] FAIL
**Test Result 3.3c**: [ ] PASS [ ] FAIL

---

### Test Case 3.4: Assign Device - Transaction Integrity

**Objective**: Verify database transaction rollback on partial failure

**Steps**:
1. Assign WATCH_TEST001 to TEST_PAT_001
2. **Simulate database failure** during device status update:
   - Assignment record created in deviceassignments
   - But device status update fails

**Expected Behavior**:
- ✅ Transaction is rolled back
- ✅ No assignment record in deviceassignments table
- ✅ Device status remains 'available'
- ✅ Error message returned to frontend

**Database Verification**:
```sql
SELECT COUNT(*) FROM deviceassignments WHERE "deviceId" = 'WATCH_TEST001';
-- Expected: 0 (rollback occurred)

SELECT status FROM devices WHERE id = 'WATCH_TEST001';
-- Expected: 'available' (not 'assigned')
```

**Test Result**: [ ] PASS [ ] FAIL

---

## TEST SUITE 4: DEVICE UNASSIGNMENT WORKFLOW

### Test Case 4.1: Unassign Device (Happy Path)

**Objective**: Verify successful device unassignment workflow

**Steps**:
1. Login as DOC0001 (Doctor)
2. Navigate to Assigned Devices tab
3. Locate WATCH_TEST003 assigned to TEST_PAT_003 (Bob Johnson)
4. Click "Unassign" button
5. Confirm unassignment dialog
6. Enter unassignment reason: "Patient Discharge"

**Expected API Call**:
```http
POST /api/v1/watchmanagement/unassign HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "deviceId": "WATCH_TEST003",
  "patientId": "TEST_PAT_003",
  "reason": "Patient Discharge"
}
```

**Expected Response**:
```json
{
  "success": true,
  "message": "Watch unassigned successfully. Reason: Patient Discharge"
}
```

**Database Verification**:

**Check deviceassignments table**:
```sql
SELECT status, "unassignedAt", "unassignedBy", "unassignmentReason"
FROM deviceassignments
WHERE "deviceId" = 'WATCH_TEST003' AND "patientId" = 'TEST_PAT_003';

-- Expected:
-- status = 'inactive'
-- unassignedAt = NOW()
-- unassignedBy = 'DOC0001'
-- unassignmentReason = 'Patient Discharge'
```

**Check devices table**:
```sql
SELECT status FROM devices WHERE id = 'WATCH_TEST003';
-- Expected: status = 'available'
```

**Frontend Validation**:
- ✅ Success message: "Device unassigned successfully"
- ✅ Device removed from assigned list
- ✅ Device appears in available list
- ✅ Device status badge shows "Available"

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 4.2: Unassign Device - Validation Errors

**Test 4.2a: Assignment Not Found**

**Steps**:
1. Attempt to unassign device not currently assigned

**Expected Response**:
```json
{
  "status_code": 404,
  "detail": "Active assignment not found"
}
```

**Test 4.2b: Missing Device ID**

**Steps**:
1. Call unassign API without deviceId

**Expected Response**:
```json
{
  "status_code": 400,
  "detail": "Patient ID and Device ID are required"
}
```

**Test Result 4.2a**: [ ] PASS [ ] FAIL
**Test Result 4.2b**: [ ] PASS [ ] FAIL

---

### Test Case 4.3: Unassign Device - RBAC Enforcement

**Objective**: Verify only medical staff can unassign devices

**Test 4.3a: Doctor Can Unassign**

**Expected**: SUCCESS

**Test 4.3b: Nurse Can Unassign**

**Expected**: SUCCESS

**Test 4.3c: Technician Cannot Unassign**

**Expected Response**:
```json
{
  "status_code": 403,
  "detail": "Insufficient permissions. Required role: Doctor or Nurse"
}
```

**Test Result 4.3a**: [ ] PASS [ ] FAIL
**Test Result 4.3b**: [ ] PASS [ ] FAIL
**Test Result 4.3c**: [ ] PASS [ ] FAIL

---

### Test Case 4.4: Bulk Unassignment on Patient Discharge

**Objective**: Verify all patient devices are unassigned on discharge

**Setup**:
1. Assign WATCH_TEST001 to TEST_PAT_001
2. Assign WATCH_TEST002 to TEST_PAT_001 (if system allows multiple devices)

**Steps**:
1. Call discharge API or bulk unassignment API
2. Provide patientId: TEST_PAT_001
3. Provide reason: "Patient Discharge"

**Expected API Call**:
```
POST /api/v1/discharge/perform/{discharge_request_id}
```
(Should trigger bulk unassignment internally)

**Expected Result**:
- All devices assigned to TEST_PAT_001 are unassigned
- All devices return to 'available' status
- All assignments marked as 'inactive'

**Database Verification**:
```sql
SELECT COUNT(*) FROM deviceassignments
WHERE "patientId" = 'TEST_PAT_001' AND status = 'active';
-- Expected: 0
```

**Test Result**: [ ] PASS [ ] FAIL

---

## TEST SUITE 5: DEVICE MODIFICATION

### Test Case 5.1: Update Device Properties (Admin Only)

**Objective**: Verify device details can be updated

**Steps**:
1. Login as ADM0001 (Administrator)
2. Navigate to Device Management
3. Click on WATCH_TEST001
4. Click "Edit Device"
5. Modify fields:
   - Location: "Ward C" (was "ICU")
   - Firmware Version: "v1.2.4" (was "v1.2.3")
   - Battery Level: 85% (was null)
   - Description: "Updated test device"
6. Click "Save Changes"

**Expected API Call**:
```http
PUT /api/v1/devices/WATCH_TEST001?updatedBy=ADM0001 HTTP/1.1
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "location": "Ward C",
  "firmwareVersion": "v1.2.4",
  "batteryLevel": 85,
  "description": "Updated test device"
}
```

**Expected Response**:
```json
{
  "success": true,
  "device": {
    "id": "WATCH_TEST001",
    "location": "Ward C",
    "firmwareVersion": "v1.2.4",
    "batteryLevel": 85,
    "description": "Updated test device",
    "updatedAt": "<new_timestamp>"
  },
  "message": "Device Test Watch 001 updated successfully"
}
```

**Database Verification**:
```sql
SELECT location, "firmwareVersion", "batteryLevel", description, "updatedAt"
FROM devices WHERE id = 'WATCH_TEST001';

-- Expected:
-- location = 'Ward C'
-- firmwareVersion = 'v1.2.4'
-- batteryLevel = 85
-- description = 'Updated test device'
-- updatedAt > original timestamp
```

**Audit Log Verification**:
```sql
SELECT * FROM auditlog WHERE action = 'DEVICE_UPDATED' AND "resourceId" = 'WATCH_TEST001';
-- Expected: 1 row with userId = 'ADM0001'
```

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 5.2: Update Device - RBAC Enforcement

**Objective**: Verify only admins can update device properties

**Steps**:
1. Login as DOC0001 (Doctor)
2. Attempt to PUT to `/api/v1/devices/WATCH_TEST001`

**Expected Response**:
```json
{
  "status_code": 403,
  "detail": "Insufficient permissions. Required role: Administrator"
}
```

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 5.3: Update Device Status Transitions

**Objective**: Verify valid status transitions

**Valid Transitions**:
- available → assigned (via assignment API)
- assigned → available (via unassignment API)
- available → maintenance (manual update)
- maintenance → available (manual update)
- any → retired (soft delete)

**Invalid Transitions**:
- retired → available (should not be allowed)
- assigned → maintenance (should unassign first)

**Test 5.3a: Set Device to Maintenance**

**Steps**:
1. Update WATCH_TEST001 status to 'maintenance'

**Expected**: SUCCESS
**Database Check**: status = 'maintenance', updatedAt updated

**Test 5.3b: Try to Assign Maintenance Device**

**Steps**:
1. Attempt to assign device with status='maintenance'

**Expected Response**:
```json
{
  "status_code": 404,
  "detail": "Available watch not found"
}
```

**Test 5.3c: Return Device from Maintenance**

**Steps**:
1. Update status from 'maintenance' to 'available'

**Expected**: SUCCESS

**Test Result 5.3a**: [ ] PASS [ ] FAIL
**Test Result 5.3b**: [ ] PASS [ ] FAIL
**Test Result 5.3c**: [ ] PASS [ ] FAIL

---

## TEST SUITE 6: DEVICE REMOVAL (SOFT DELETE)

### Test Case 6.1: Remove Device (Soft Delete)

**Objective**: Verify device soft delete (status → retired)

**Steps**:
1. Login as ADM0001 (Administrator)
2. Navigate to Device Management
3. Select WATCH_TEST002 (currently available)
4. Click "Remove Device"
5. Confirm removal

**Expected API Call**:
```http
DELETE /api/v1/devices/WATCH_TEST002?deletedBy=ADM0001 HTTP/1.1
Authorization: Bearer <admin_token>
```

**Expected Response**:
```json
{
  "success": true,
  "message": "Device Test Watch 002 removed from inventory",
  "forceRemoved": false
}
```

**Database Verification**:
```sql
SELECT status FROM devices WHERE id = 'WATCH_TEST002';
-- Expected: status = 'retired' (not deleted from table)
```

**Audit Log Verification**:
```sql
SELECT * FROM auditlog WHERE action = 'DEVICE_REMOVED' AND "resourceId" = 'WATCH_TEST002';
-- Expected: 1 row with userId = 'ADM0001'
```

**Frontend Validation**:
- ✅ Device no longer appears in available list
- ✅ Device no longer appears in device pool statistics
- ✅ Success message displayed

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 6.2: Remove Assigned Device (Force Required)

**Objective**: Verify cannot remove assigned device without force flag

**Setup**:
1. WATCH_TEST003 is currently assigned to TEST_PAT_003

**Steps**:
1. Attempt to DELETE WATCH_TEST003 without force flag

**Expected Response**:
```json
{
  "status_code": 400,
  "detail": "Device is currently assigned to Bob Johnson. Unassign first or use force=True"
}
```

**Database Verification**:
```sql
SELECT status FROM devices WHERE id = 'WATCH_TEST003';
-- Expected: status = 'assigned' (not changed)
```

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 6.3: Remove Assigned Device (Force Delete)

**Objective**: Verify force delete unassigns and removes device

**Steps**:
1. DELETE WATCH_TEST003 with force=True query parameter

**Expected API Call**:
```http
DELETE /api/v1/devices/WATCH_TEST003?deletedBy=ADM0001&force=true HTTP/1.1
Authorization: Bearer <admin_token>
```

**Expected Response**:
```json
{
  "success": true,
  "message": "Device Test Watch 003 removed from inventory",
  "forceRemoved": true
}
```

**Database Verification**:

**Check device status**:
```sql
SELECT status FROM devices WHERE id = 'WATCH_TEST003';
-- Expected: status = 'retired'
```

**Check assignment status**:
```sql
SELECT status FROM deviceassignments
WHERE "deviceId" = 'WATCH_TEST003' AND "patientId" = 'TEST_PAT_003';
-- Expected: status = 'forceRemoved'
```

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 6.4: Remove Device - RBAC Enforcement

**Objective**: Verify only admins can remove devices

**Steps**:
1. Login as DOC0001 (Doctor)
2. Attempt to DELETE device

**Expected Response**:
```json
{
  "status_code": 403,
  "detail": "Insufficient permissions. Required role: Administrator"
}
```

**Test Result**: [ ] PASS [ ] FAIL

---

## TEST SUITE 7: DEVICE MONITORING & STATUS

### Test Case 7.1: View Device Details

**Objective**: Verify device details page displays all information

**Steps**:
1. Login as any authenticated user
2. Navigate to Device Management
3. Click on WATCH_TEST001
4. View device details page

**Expected API Call**:
```http
GET /api/v1/devices/WATCH_TEST001 HTTP/1.1
Authorization: Bearer <token>
```

**Expected Response**:
```json
{
  "success": true,
  "device": {
    "id": "WATCH_TEST001",
    "deviceType": "watch",
    "name": "Test Watch 001",
    "serialNumber": "ESP32-001",
    "macAddress": "AA:BB:CC:DD:EE:01",
    "firmwareVersion": "v1.2.3",
    "batteryLevel": 85,
    "status": "available",
    "connectionStatus": "offline",
    "location": "Ward C",
    "description": "Updated test device",
    "lastSeen": null,
    "minutesSinceLastSeen": null,
    "calibrationDate": null,
    "nextMaintenanceDate": null,
    "createdAt": "<timestamp>",
    "updatedAt": "<timestamp>",
    "assignmentHistory": []
  }
}
```

**Frontend Validation**:
- ✅ All device properties displayed
- ✅ Connection status indicator (green=connected, yellow=recent, red=offline)
- ✅ Battery level displayed with color coding
- ✅ Assignment history section (empty if never assigned)
- ✅ Maintenance dates displayed (if applicable)

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 7.2: View Device Assignment History

**Objective**: Verify assignment history shows all past assignments

**Setup**:
1. Assign WATCH_TEST001 to TEST_PAT_001, then unassign
2. Assign WATCH_TEST001 to TEST_PAT_002, keep assigned

**Steps**:
1. View WATCH_TEST001 device details
2. Scroll to Assignment History section

**Expected Result**:
- History shows 2 entries (most recent first):
  1. Assigned to Jane Smith (TEST_PAT_002) - Status: active
  2. Assigned to John Doe (TEST_PAT_001) - Status: inactive, unassigned by DOC0001

**Database Query**:
```sql
SELECT da.*, p."firstName", p."lastName", p."roomNumber", p."bedNumber"
FROM deviceassignments da
LEFT JOIN patients p ON da."patientId" = p.id
WHERE da."deviceId" = 'WATCH_TEST001'
ORDER BY da."assignedAt" DESC
LIMIT 10;
```

**Frontend Validation**:
- ✅ Assignment history table displayed
- ✅ Each entry shows: patient name, room/bed, assigned date, assigned by, status
- ✅ Unassigned entries show unassignment reason and unassigned by
- ✅ Active assignments highlighted

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 7.3: View Devices by Location

**Objective**: Verify location-based device filtering

**Steps**:
1. Call GET `/api/v1/devices/location/ICU`

**Expected Response**:
- Returns all devices with location containing "ICU"

**Database Verification**:
```sql
SELECT * FROM devices WHERE location ILIKE '%ICU%' AND status != 'retired';
```

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 7.4: View Device Health Status

**Objective**: Verify system-wide device health monitoring

**Steps**:
1. Call GET `/api/v1/devices/status/health`

**Expected API Response**:
```json
{
  "success": true,
  "overallHealth": {
    "totalDevices": 4,
    "onlineDevices": 0,
    "offlineDevices": 4,
    "healthPercentage": 0.0
  },
  "byDeviceType": {
    "watch": {
      "total": 3,
      "online": 0,
      "offline": 3,
      "maintenance": 0,
      "available": 2,
      "assigned": 1
    },
    "tablet": {
      "total": 1,
      "online": 0,
      "offline": 1,
      "maintenance": 0,
      "available": 1,
      "assigned": 0
    }
  },
  "timestamp": "<timestamp>"
}
```

**Frontend Validation**:
- ✅ Health dashboard displays overall statistics
- ✅ Per-device-type breakdown shown
- ✅ Health percentage indicator (color-coded: green >80%, yellow 50-80%, red <50%)

**Test Result**: [ ] PASS [ ] FAIL

---

## TEST SUITE 8: WATCH-SPECIFIC FEATURES

### Test Case 8.1: Get Available Watches

**Objective**: Verify watch-specific endpoint returns only watches

**Steps**:
1. Call GET `/api/v1/watchmanagement/available`

**Expected Response**:
- Returns only devices with `deviceType='watch'` and `status='available'`
- Does not include tablets, sensors, or other device types

**Database Verification**:
```sql
SELECT * FROM devices WHERE "deviceType" = 'watch' AND status = 'available';
```

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 8.2: Get Assigned Watches with Patient Info

**Objective**: Verify assigned watches endpoint includes patient details

**Steps**:
1. Call GET `/api/v1/watchmanagement/assigned`

**Expected Response**:
```json
{
  "success": true,
  "assignedWatches": [
    {
      "id": 123,
      "deviceId": "WATCH_TEST003",
      "patientId": "TEST_PAT_003",
      "firstName": "Bob",
      "lastName": "Johnson",
      "roomNumber": "WARD-B-301",
      "bedNumber": "B3",
      "patientName": "Bob Johnson",
      "location": "Room WARD-B-301, Bed B3",
      "watchDisplay": "Watch ESP32-003",
      "serialNumber": "ESP32-003",
      "connectionStatus": "offline",
      "batteryLevel": null,
      "assignedBy": "DOC0001",
      "assignedByName": "Dr. Smith",
      "assignedByRole": "Doctor",
      "assignedAt": "<timestamp>",
      "status": "active"
    }
  ],
  "count": 1
}
```

**Staff Resolution Verification**:
- ✅ `assignedBy` (staff ID) is resolved to `assignedByName` and `assignedByRole`
- ✅ Middleware (`resolve_staff_in_response`) applied successfully

**Database Verification**:
```sql
SELECT d.*, da.*, p."firstName", p."lastName", p."roomNumber", p."bedNumber"
FROM devices d
JOIN deviceassignments da ON d.id = da."deviceId"
JOIN patients p ON da."patientId" = p.id
WHERE d."deviceType" = 'watch' AND da.status = 'active';
```

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 8.3: Watch Connection Status Monitoring

**Objective**: Verify real-time connection status tracking

**Steps**:
1. Call GET `/api/v1/watchmanagement/connection-status`

**Expected Response**:
- Returns all watches with:
  - `connectionStatus`: 'connected' (lastSeen < 5 min ago), 'recentlySeen' (<1 hour), or 'offline'
  - `minutesSinceLastSeen`: calculated value

**Database Logic**:
```sql
CASE WHEN "lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
     WHEN "lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
     ELSE 'offline' END as connectionStatus
```

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 8.4: Watch Alerts (Low Battery, Disconnect)

**Objective**: Verify watch alert generation

**Steps**:
1. Update WATCH_TEST003 batteryLevel to 15%
2. Call GET `/api/v1/watchmanagement/alerts`

**Expected Response**:
```json
{
  "success": true,
  "alerts": [
    {
      "id": "batteryWATCH_TEST003",
      "type": "lowBattery",
      "severity": "medium",
      "patientId": "TEST_PAT_003",
      "patientName": "Bob Johnson",
      "location": "Room WARD-B-301, Bed B3",
      "deviceId": "WATCH_TEST003",
      "deviceSerial": "ESP32-003",
      "message": "Watch ESP32-003 battery low (15%)",
      "batteryLevel": 15,
      "timestamp": "<timestamp>"
    },
    {
      "id": "disconnectWATCH_TEST003",
      "type": "watchDisconnect",
      "severity": "high",
      "patientId": "TEST_PAT_003",
      "patientName": "Bob Johnson",
      "location": "Room WARD-B-301, Bed B3",
      "deviceId": "WATCH_TEST003",
      "deviceSerial": "ESP32-003",
      "message": "Watch ESP32-003 disconnected",
      "minutesSinceLastSeen": 120,
      "timestamp": "<timestamp>"
    }
  ],
  "count": 2
}
```

**Alert Severity Rules**:
- Battery ≤ 10%: severity = 'critical'
- Battery 11-20%: severity = 'medium'
- Disconnected (offline): severity = 'high'

**Frontend Validation**:
- ✅ Alerts displayed in alert dashboard
- ✅ Severity color-coding (critical=red, high=orange, medium=yellow)
- ✅ Alert notifications trigger (if real-time enabled)

**Test Result**: [ ] PASS [ ] FAIL

---

## TEST SUITE 9: EDGE CASES & ERROR SCENARIOS

### Test Case 9.1: Concurrent Assignment Attempts (Race Condition)

**Objective**: Verify database prevents double-assignment

**Setup**:
- WATCH_TEST001 is available
- Two users (DOC0001 and NUR0001) attempt to assign to different patients simultaneously

**Steps**:
1. User 1 (DOC0001): POST assign WATCH_TEST001 to TEST_PAT_001
2. User 2 (NUR0001): POST assign WATCH_TEST001 to TEST_PAT_002 (within 50ms)

**Expected Behavior**:
- One request succeeds (whichever reaches database first)
- Second request fails with:
  ```json
  {
    "status_code": 404,
    "detail": "Available watch not found"
  }
  ```
- Database maintains consistency (only 1 active assignment)

**Database Verification**:
```sql
SELECT COUNT(*) FROM deviceassignments WHERE "deviceId" = 'WATCH_TEST001' AND status = 'active';
-- Expected: 1 (not 2)
```

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 9.2: Assign to Discharged Patient

**Objective**: Verify cannot assign device to inactive patient

**Setup**:
1. Set TEST_PAT_001 status to 'discharged'

**Steps**:
1. Attempt to assign WATCH_TEST001 to TEST_PAT_001

**Expected Response**:
```json
{
  "status_code": 404,
  "detail": "Active patient not found"
}
```

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 9.3: Network Failure During Assignment

**Objective**: Verify graceful handling of network errors

**Steps**:
1. Simulate network timeout during assignment API call
2. Observe frontend behavior

**Expected Frontend Behavior**:
- ✅ Loading spinner stops
- ✅ Error message: "Failed to assign device" or "Network error"
- ✅ User can retry operation
- ✅ No partial state (device not removed from available list if assignment failed)

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 9.4: Unassign Non-Existent Device

**Objective**: Verify error handling for invalid device ID

**Steps**:
1. Attempt to unassign device with ID "INVALID_DEVICE_ID"

**Expected Response**:
```json
{
  "status_code": 404,
  "detail": "Active assignment not found"
}
```

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 9.5: Update Retired Device

**Objective**: Verify cannot modify retired devices

**Setup**:
1. WATCH_TEST002 status = 'retired'

**Steps**:
1. Attempt to PUT update to WATCH_TEST002

**Expected Behavior**:
- Update succeeds (no explicit check in current code)
- **RECOMMENDATION**: Add validation to prevent updates to retired devices

**Test Result**: [ ] PASS [ ] FAIL

---

## TEST SUITE 10: PERFORMANCE & STRESS TESTING

### Test Case 10.1: Load Test - List 1000 Devices

**Objective**: Verify performance with large device pool

**Setup**:
1. Insert 1000 test devices into database

**Steps**:
1. Call GET `/api/v1/devices/?limit=1000`
2. Measure response time

**Expected Performance**:
- Response time < 2 seconds
- All 1000 devices returned
- No memory issues on frontend

**Database Optimization Check**:
- ✅ Indexes used: `idx_devices_type`, `idx_devices_status`
- ✅ Query plan efficient (no full table scan)

**Test Result**: [ ] PASS [ ] FAIL
**Response Time**: _______ ms

---

### Test Case 10.2: Load Test - Assignment History (100 Assignments)

**Objective**: Verify performance with extensive assignment history

**Setup**:
1. Create 100 assignment records for WATCH_TEST001

**Steps**:
1. Call GET `/api/v1/devices/WATCH_TEST001`
2. Measure response time for assignment history

**Expected Performance**:
- Response time < 1 second
- History limited to 10 most recent (per code: `LIMIT 10`)

**Test Result**: [ ] PASS [ ] FAIL
**Response Time**: _______ ms

---

### Test Case 10.3: Stress Test - 50 Concurrent Assignments

**Objective**: Verify system handles concurrent operations

**Setup**:
1. 50 available devices
2. 50 active patients

**Steps**:
1. Spawn 50 parallel assignment requests (1 per device-patient pair)
2. Measure success rate and response times

**Expected Result**:
- All 50 assignments succeed
- No database deadlocks
- No race conditions
- Average response time < 500ms

**Test Result**: [ ] PASS [ ] FAIL
**Success Rate**: _____%
**Average Response Time**: _______ ms

---

## TEST SUITE 11: SECURITY TESTING

### Test Case 11.1: SQL Injection - Device Name

**Objective**: Verify input sanitization prevents SQL injection

**Steps**:
1. Attempt to create device with name: `"; DROP TABLE devices; --`

**Expected Behavior**:
- Device created with literal name (not executed as SQL)
- No database tables dropped
- Parameterized queries prevent injection

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 11.2: XSS - Device Description

**Objective**: Verify frontend sanitizes device description

**Steps**:
1. Create device with description: `<script>alert('XSS')</script>`
2. View device details on frontend

**Expected Behavior**:
- Script tag is escaped or sanitized
- No JavaScript execution
- Text displayed as literal string

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 11.3: CSRF - Assignment Request

**Objective**: Verify CSRF protection on state-changing operations

**Steps**:
1. Craft assignment request from external domain
2. Attempt to submit without proper CORS headers

**Expected Response**:
- Request blocked by CORS policy
- 403 Forbidden or CORS error

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 11.4: JWT Token Expiration

**Objective**: Verify expired tokens are rejected

**Steps**:
1. Wait for JWT access token to expire (default: 15 minutes)
2. Attempt device operation with expired token

**Expected Response**:
```json
{
  "status_code": 401,
  "detail": "Token has expired"
}
```

**Frontend Behavior**:
- ✅ User redirected to login screen
- ✅ Error message: "Session expired, please login again"

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 11.5: Insufficient Permissions - Role Escalation

**Objective**: Verify role-based access cannot be bypassed

**Steps**:
1. Login as TEC0001 (Technician)
2. Manually craft POST request to assign device (bypassing frontend)
3. Submit with valid TEC0001 JWT token

**Expected Response**:
```json
{
  "status_code": 403,
  "detail": "Insufficient permissions. Required role: Doctor or Nurse"
}
```

**Test Result**: [ ] PASS [ ] FAIL

---

## TEST SUITE 12: DATA INTEGRITY & AUDIT TRAILS

### Test Case 12.1: Audit Log - All Operations

**Objective**: Verify all device operations are logged

**Operations to Test**:
1. Create device → Audit log entry with action='DEVICE_CREATED'
2. Update device → Audit log entry with action='DEVICE_UPDATED'
3. Remove device → Audit log entry with action='DEVICE_REMOVED'

**Database Verification**:
```sql
SELECT * FROM auditlog WHERE "resourceType" = 'DEVICE' AND "resourceId" = '<device_id>'
ORDER BY timestamp DESC;
```

**Expected Fields**:
- userId (staff who performed action)
- action (DEVICE_CREATED, DEVICE_UPDATED, DEVICE_REMOVED)
- resourceType ('DEVICE')
- resourceId (device ID)
- details (human-readable description)
- ipAddress (optional)
- userAgent (optional)
- timestamp

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 12.2: Assignment Audit Trail

**Objective**: Verify assignment history maintains complete audit trail

**Database Check**:
```sql
SELECT "assignedBy", "assignedAt", "unassignedBy", "unassignedAt", "unassignmentReason"
FROM deviceassignments WHERE "deviceId" = '<device_id>'
ORDER BY "assignedAt" DESC;
```

**Expected**:
- All assignments have assignedBy (staff ID)
- All unassignments have unassignedBy (staff ID)
- All unassignments have unassignmentReason
- Timestamps are accurate

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 12.3: Staff Resolution in Responses

**Objective**: Verify staff IDs are resolved to names in API responses

**Steps**:
1. Call GET `/api/v1/watchmanagement/assigned`

**Expected Response Fields**:
- `assignedBy`: "DOC0001" (staff ID)
- `assignedByName`: "Dr. John Smith" (resolved name)
- `assignedByRole`: "Doctor" (resolved role)

**Middleware Check**:
- ✅ `staff_resolution_middleware.resolve_staff_in_response()` applied
- ✅ All staff ID fields resolved

**Test Result**: [ ] PASS [ ] FAIL

---

## TEST SUITE 13: FRONTEND-SPECIFIC TESTS

### Test Case 13.1: Device Pool Tab - UI Rendering

**Objective**: Verify Device Pool Tab renders correctly

**Steps**:
1. Navigate to Device Management screen
2. Click "Device Pool" tab

**Expected UI Elements**:
- ✅ Pool Status Summary (5 stat cards: Total, Available, Assigned, Offline, Low Battery)
- ✅ Available Devices card (left side)
- ✅ Assigned Devices card (right side)
- ✅ Each device shows: icon, name, serial, location, battery, connection status
- ✅ Empty state if no devices

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 13.2: Assignment Tab - Patient & Device Selection

**Objective**: Verify assignment workflow UI

**Steps**:
1. Navigate to "Assign Device" tab
2. Verify patient selection dropdown
3. Verify device selection dropdown
4. Verify assignment reason dropdown

**Expected Behavior**:
- ✅ Dropdowns populated with data from API
- ✅ "Assign" button disabled until patient, device, and reason selected
- ✅ Success message displays after assignment
- ✅ Selections cleared after successful assignment

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 13.3: Assigned Devices Tab - Unassignment UI

**Objective**: Verify unassignment workflow UI

**Steps**:
1. Navigate to "Assigned Devices" tab
2. View list of assigned devices
3. Click "Unassign" button on a device
4. Confirm dialog

**Expected Behavior**:
- ✅ Confirmation dialog: "Unassign device [name] from patient [name]?"
- ✅ Success message after unassignment
- ✅ Device removed from assigned list
- ✅ Device pool refreshes automatically

**Test Result**: [ ] PASS [ ] FAIL

---

### Test Case 13.4: Real-Time Updates (WebSocket)

**Objective**: Verify device status updates in real-time

**Steps**:
1. Open Device Management screen on two browser tabs
2. Tab 1: Assign device to patient
3. Tab 2: Observe device list

**Expected Behavior**:
- ✅ Tab 2 shows device removed from available list (without manual refresh)
- ✅ Tab 2 shows device in assigned list (without manual refresh)
- ✅ WebSocket message received with updated device data

**Test Result**: [ ] PASS [ ] FAIL

---

## TEST EXECUTION SUMMARY

### Test Coverage:
```
Total Test Cases: 60+
- Device Pool Management: 4 tests
- Device Creation: 3 tests
- Device Assignment: 5 tests
- Device Unassignment: 4 tests
- Device Modification: 3 tests
- Device Removal: 4 tests
- Device Monitoring: 4 tests
- Watch-Specific: 4 tests
- Edge Cases: 5 tests
- Performance: 3 tests
- Security: 5 tests
- Data Integrity: 3 tests
- Frontend UI: 4 tests
```

### Pass/Fail Summary:
```
PASSED: _____ / 60
FAILED: _____ / 60
BLOCKED: _____ / 60
NOT RUN: _____ / 60

Pass Rate: _____%
```

---

## ISSUES FOUND

### Critical Issues:
1. [ ] ___________________________________________
2. [ ] ___________________________________________

### High Priority Issues:
1. [ ] ___________________________________________
2. [ ] ___________________________________________

### Medium Priority Issues:
1. [ ] ___________________________________________
2. [ ] ___________________________________________

### Low Priority Issues:
1. [ ] ___________________________________________
2. [ ] ___________________________________________

---

## RECOMMENDATIONS

### Immediate Fixes Required:
1. ___________________________________________
2. ___________________________________________
3. ___________________________________________

### Enhancements for Future:
1. ___________________________________________
2. ___________________________________________
3. ___________________________________________

---

## CODE QUALITY ASSESSMENT

### Backend Code Quality: **___/10**

**Strengths**:
- ✅ Clean API structure with clear endpoint naming
- ✅ Proper RBAC enforcement with `require_admin`, `require_medical_staff` dependencies
- ✅ Staff resolution middleware for audit trail
- ✅ Comprehensive error handling
- ✅ camelCase consistency (95%)
- ✅ Database transactions for atomic operations
- ✅ Audit logging on all state-changing operations

**Weaknesses**:
- ⚠️ No explicit validation to prevent updates to retired devices
- ⚠️ Device type list hardcoded (should be in database or config)
- ⚠️ Missing pagination on device list endpoints (potential performance issue with 1000+ devices)
- ⚠️ No rate limiting on device operations
- ⚠️ Some endpoints return 500 errors instead of more specific error codes

**Recommended Improvements**:
1. Add input validation middleware
2. Implement pagination (limit, offset) on list endpoints
3. Add rate limiting (e.g., 100 requests/minute per user)
4. Refactor error handling to return more specific HTTP status codes
5. Add device type enum in database

---

### Frontend Code Quality: **___/10**

**Strengths**:
- ✅ Clean component architecture with separation of concerns
- ✅ Custom hook (`useDeviceAssignment`) for state management
- ✅ Proper TypeScript typing
- ✅ Loading states and error handling
- ✅ Responsive UI with Tailwind CSS
- ✅ camelCase consistency
- ✅ Real-time data refresh capabilities

**Weaknesses**:
- ⚠️ No pagination UI for large device lists
- ⚠️ Limited error message specificity (generic "Failed to assign device")
- ⚠️ No optimistic UI updates (waits for API response before updating UI)
- ⚠️ Missing unit tests for components and hooks
- ⚠️ No accessibility (a11y) attributes on interactive elements

**Recommended Improvements**:
1. Add pagination component for device lists
2. Implement optimistic UI updates for better UX
3. Add more specific error messages based on API error codes
4. Add unit tests (Jest + React Testing Library)
5. Add ARIA labels and keyboard navigation support
6. Add loading skeletons instead of spinners

---

## SIGN-OFF

**Test Engineer**: ___________________________ Date: _________
**Backend Lead**: ___________________________ Date: _________
**Frontend Lead**: ___________________________ Date: _________
**QA Manager**: ___________________________ Date: _________

---

**END OF DEVICE MANAGEMENT E2E TEST PLAN**
