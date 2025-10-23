# Device Testing Plan - ESP32 Watches & Device Pool

**Date:** 2025-10-12
**Purpose:** Test ESP32 watch device pool and device management system

---

## Architecture Overview

### Device Types Supported
From `device_management.py:device_management.py:22-31`:
- `watch` - ESP32 Patient Watch
- `tablet` - Tablet/Display Device
- `sensor` - IoT Sensor
- `doorScanner` - BLE Door Scanner
- `vitalMonitor` - Vital Signs Monitor
- `infusionPump` - Smart Infusion Pump
- `medicalEquipment` - Medical Equipment Interface
- `other` - Other Device

### Device Statuses
- `available` - Ready for assignment
- `assigned` - Currently assigned to a patient
- `maintenance` - Under maintenance
- `retired` - Removed from pool
- `offline` - Not connected

---

## Key Endpoints Identified

### 1. Device Management (`/api/v1/devices`)
**Authentication:** Requires admin role

- `GET /api/v1/devices/` - List all devices
- `GET /api/v1/devices/available` - Get available devices for assignment
- `GET /api/v1/devices/{deviceId}` - Get device details
- `POST /api/v1/devices/` - Create new device
- `PUT /api/v1/devices/{deviceId}` - Update device
- `DELETE /api/v1/devices/{deviceId}` - Remove device (soft delete)
- `GET /api/v1/devices/status/health` - Get device health status

### 2. Watch Management (`/api/v1/watchmanagement`)
**Authentication:** Requires medical staff role

- `GET /api/v1/watchmanagement/available` - Get available watches
- `GET /api/v1/watchmanagement/assigned` - Get assigned watches
- `GET /api/v1/watchmanagement/connection-status` - Watch connection status
- `GET /api/v1/watchmanagement/alerts` - Watch-related alerts (disconnect, low battery)
- `POST /api/v1/watchmanagement/assign` - Assign watch to patient
- `POST /api/v1/watchmanagement/unassign` - Unassign watch from patient

### 3. ESP32 Integration (`/api/v1/esp32`)
**Authentication:** Device key authentication

- `POST /api/v1/esp32/provision` - Provision new ESP32 device
- `POST /api/v1/esp32/register` - Register ESP32 device
- `POST /api/v1/esp32/online` - Mark device online
- `POST /api/v1/esp32/{deviceId}/heartbeat` - Device heartbeat
- `POST /api/v1/esp32/{deviceId}/vitals/{patientId}` - Submit vitals data
- `POST /api/v1/esp32/{deviceId}/alert` - Send emergency alert
- `POST /api/v1/esp32/door-scanner/{scannerId}/scan` - Door scanner detection

---

## Device Lifecycle

### 1. Provisioning (New Device)
```
ESP32 → POST /api/v1/esp32/provision
  - Requires: macAddress, provisionerId, provisionerPassword
  - Returns: deviceId, serialNumber
  - Creates device with status='available', location='Device Pool'
```

### 2. Registration (First Connection)
```
ESP32 → POST /api/v1/esp32/register
  - Requires: deviceId, macAddress, firmwareVersion
  - Updates lastSeen, status='available'
```

### 3. Assignment (Patient Admission)
```
Staff → POST /api/v1/watchmanagement/assign
  - Requires: patientId, deviceId, assignedBy
  - Creates deviceassignments record
  - Updates device status='assigned', assignedPatientId=patientId
  - Updates patient assignedDeviceId=deviceId
```

### 4. Active Monitoring
```
ESP32 → POST /api/v1/esp32/{deviceId}/heartbeat (periodic)
ESP32 → POST /api/v1/esp32/{deviceId}/vitals/{patientId} (continuous)
```

### 5. Unassignment (Discharge)
```
Staff → POST /api/v1/watchmanagement/unassign
  - Requires: patientId, deviceId, unassignedBy, reason
  - Updates assignment status='inactive'
  - Updates device status='available', assignedPatientId=NULL
  - Updates patient assignedDeviceId=NULL
```

---

## Testing Scenarios

### Scenario 1: Check Device Pool Status
**Goal:** Verify all devices in the system

**Steps:**
1. Login as admin or medical staff
2. GET `/api/v1/devices/` - List all devices
3. Verify response includes all device types
4. Check device statuses

**Expected Results:**
- JSON response with success=true
- Array of devices with fields: id, deviceType, serialNumber, status, batteryLevel, location, lastSeen
- Summary statistics

### Scenario 2: Check Available Watches
**Goal:** Find watches ready for assignment

**Steps:**
1. Login as medical staff
2. GET `/api/v1/watchmanagement/available`
3. Count available watches
4. Check connection status of each

**Expected Results:**
- JSON response with success=true
- Array of available watches
- Each watch shows: id, serialNumber, batteryLevel, connectionStatus
- connectionStatus calculated based on lastSeen:
  - `connected` - lastSeen within 5 minutes
  - `recentlySeen` - lastSeen within 1 hour
  - `offline` - lastSeen > 1 hour or NULL

### Scenario 3: Check Assigned Watches
**Goal:** See watches currently in use

**Steps:**
1. Login as medical staff
2. GET `/api/v1/watchmanagement/assigned`
3. Verify patient information
4. Check connection status

**Expected Results:**
- JSON response with success=true
- Array of assigned watches with patient info
- Each includes: deviceId, serialNumber, patientName, roomNumber, bedNumber, assignedAt

### Scenario 4: Watch Connection Status
**Goal:** Monitor all watch connections

**Steps:**
1. Login as medical staff
2. GET `/api/v1/watchmanagement/connection-status`
3. Review connection summary

**Expected Results:**
- All watches listed (available + assigned)
- Connection status for each
- Summary: {total, connected, recentlySeen, offline}

### Scenario 5: Watch Alerts
**Goal:** Check for watch-related issues

**Steps:**
1. Login as medical staff
2. GET `/api/v1/watchmanagement/alerts`
3. Review alerts

**Expected Alerts:**
- **watchDisconnect** (severity: high)
  - When assigned watch connectionStatus = 'offline'
  - Includes patient info and room location
- **lowBattery** (severity: medium/critical)
  - When batteryLevel ≤ 20%
  - Critical if ≤ 10%

### Scenario 6: Device Health Status
**Goal:** Overall device health across hospital

**Steps:**
1. Login as admin
2. GET `/api/v1/devices/status/health`
3. Review health metrics

**Expected Results:**
- Overall health percentage
- Breakdown by device type
- Online vs offline counts
- Available vs assigned counts

### Scenario 7: Provision New ESP32 Watch
**Goal:** Add new watch to pool

**Steps:**
1. Prepare provisioner credentials (role='Provisioner')
2. POST `/api/v1/esp32/provision`
   - Body: {macAddress, deviceType: 'esp32Watch', provisionerId, provisionerPassword}
3. Verify device created

**Expected Results:**
- success=true
- New deviceId assigned (format: `ESP32_WATCH_###`)
- New serialNumber assigned (format: `SN_W###`)
- Device status='available', location='Device Pool'
- Audit log created

### Scenario 8: Assign Watch to Patient
**Goal:** Connect watch to patient

**Prerequisites:**
- Available watch with status='available'
- Active patient with status='active'

**Steps:**
1. Login as medical staff (doctor or nurse)
2. POST `/api/v1/watchmanagement/assign`
   - Body: {patientId, deviceId, assignedBy}
3. Verify assignment

**Expected Results:**
- Assignment record created with status='active'
- Device updated: status='assigned', assignedPatientId=patientId
- Patient updated: assignedDeviceId=deviceId
- Response includes assignmentId and success message

**Error Cases:**
- Patient already has watch → HTTP 400
- Device not available → HTTP 404
- Patient not active → HTTP 404

### Scenario 9: Unassign Watch from Patient
**Goal:** Remove watch from patient

**Prerequisites:**
- Active assignment

**Steps:**
1. Login as medical staff
2. POST `/api/v1/watchmanagement/unassign`
   - Body: {patientId, deviceId, unassignedBy, reason}
3. Verify unassignment

**Expected Results:**
- Assignment status changed to 'inactive'
- Device status changed to 'available'
- Device assignedPatientId cleared
- Patient assignedDeviceId cleared

---

## Database Schema

### `devices` Table
```sql
- id (PK) - Device identifier
- deviceType - Type from DEVICE_TYPES
- serialNumber - Manufacturer serial
- macAddress - Hardware MAC address
- firmwareVersion - Current firmware
- batteryLevel - Battery percentage (0-100)
- status - Device status (available/assigned/maintenance/retired/offline)
- location - Physical location
- assignedPatientId - FK to patients (when assigned)
- lastSeen - Last heartbeat timestamp
- createdAt - Creation timestamp
- updatedAt - Last update timestamp
```

### `deviceassignments` Table
```sql
- id (PK) - Assignment identifier
- patientId (FK) - Assigned patient
- deviceId (FK) - Assigned device
- assignedAt - Assignment timestamp
- assignedBy - Staff who assigned
- unassignedAt - Unassignment timestamp
- unassignedBy - Staff who unassigned
- unassignmentReason - Reason for unassignment
- status - Assignment status (active/inactive)
```

---

## Code Locations

### Backend Files
- **Device Management API:** `hospital-backend/app/api/v1/device_management.py`
- **Watch Management API:** `hospital-backend/app/api/v1/watch_management.py`
- **ESP32 Integration API:** `hospital-backend/app/api/v1/esp32.py`
- **Database Config:** `hospital-backend/app/core/database.py`
- **Main App:** `hospital-backend/main.py` (lines 274-275 - device routers)

### Authentication
- **Auth Dependencies:** `hospital-backend/app/core/auth_dependencies.py`
- **Roles Required:**
  - Device Management: `require_admin` (admin only)
  - Watch Management: `require_medical_staff` (doctor or nurse)
  - ESP32 Endpoints: `verify_device_key` (device authentication)

---

## Test Execution Order

1. ✅ Backend health check (`/health`)
2. 🔍 Check device pool status (all devices)
3. 🔍 Check available watches
4. 🔍 Check assigned watches
5. 🔍 Check watch connection status
6. 🔍 Check watch alerts
7. 🔍 Check device health statistics
8. ➕ (Optional) Provision new watch
9. ➕ (Optional) Assign/unassign watch

---

## Authentication Setup

### Required Staff Accounts
```sql
SELECT id, name, role, password FROM staff WHERE role IN ('Admin', 'Provisioner', 'Doctor', 'Nurse');
```

### Login Process
```bash
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"staffId": "ADMIN001", "password": "admin123"}'
```

Response includes:
```json
{
  "success": true,
  "token": "eyJ...",
  "user": {...}
}
```

Use token in subsequent requests:
```bash
-H "Authorization: Bearer {token}"
```

---

## Next Steps

1. Create automated test script with authentication
2. Execute all test scenarios
3. Document actual device pool state
4. Create device pool report
5. Test watch assignment/unassignment flow
6. Test ESP32 vitals submission (if hardware available)

---

*Generated with Research-First Medical Developer approach*
*Ready for execution after authentication setup*
