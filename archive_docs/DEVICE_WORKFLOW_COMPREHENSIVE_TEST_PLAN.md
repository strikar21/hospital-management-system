# Device Workflow - Comprehensive Test Plan

**Date:** 2025-10-13
**Backend:** http://localhost:8001
**Status:** READY TO EXECUTE

---

## 📊 Available Test Data (Researched from Database)

### Patients (5 Active, 1 Discharged)
1. **TEST001** - Test Patient (Active) ✅ BEST FOR TESTING
2. **7163182b-5d6e-412d-93d9-28ecfd86cc6e** - Robert Anderson (Active)
3. **9b1f89f3-577d-451e-983d-e6a97f937d76** - William Johnson (Active)
4. **081a5294-da91-4c74-bb8a-e5062f5851dd** - Thomas Brown (Active)
5. **6b851aa6-e564-40b6-963f-e1a5efdf024c** - Jennifer Lee (Discharged) - Skip

### Devices (1 Available)
1. **TEST_WATCH_001** - ESP32 Watch (Available, Battery 100%) ✅

### Current State
- **Active Assignments:** 0
- **Device Status:** TEST_WATCH_001 is available (not assigned)
- **Previous Assignment:** Jennifer Lee had TEST_WATCH_001 (now unassigned/inactive)

---

## 🎯 Test Workflow Sequence

### Phase 1: Device Assignment
**Test:** Assign TEST_WATCH_001 to TEST001 (Test Patient)

**API Endpoint:**
```
POST /api/v1/watch-management/watches/{watchId}/assign
Body: {"patientId": "TEST001"}
```

**Expected Results:**
- ✅ 200 OK response
- ✅ Assignment record created in deviceassignments table
- ✅ Assignment status = 'active'
- ✅ Device status changes to 'assigned' or remains 'available'
- ✅ assignedAt timestamp populated
- ✅ unassignedAt is NULL

**Verification Queries:**
```sql
-- Check deviceassignments table
SELECT * FROM deviceassignments WHERE "patientId" = 'TEST001' AND status = 'active'

-- Check device status
SELECT id, status, "deviceType" FROM devices WHERE id = 'TEST_WATCH_001'
```

---

### Phase 2: Data Sending (Device → Backend)

#### Test 2A: Send Vitals Data
**Test:** Simulate ESP32 watch sending vitals to backend

**API Endpoint:**
```
POST /api/v1/esp32/vitals
Body: {
  "deviceId": "TEST_WATCH_001",
  "patientId": "TEST001",
  "vitals": {
    "heartrate": 72,
    "temperature": 98.6,
    "oxygensat": 98,
    "respiratoryrate": 16,
    "bloodpressurevalue": 120
  },
  "timestamp": "2025-10-13T17:30:00Z"
}
```

**Expected Results:**
- ✅ 200 OK response
- ✅ Vitals stored in TimescaleDB (if available) or PostgreSQL
- ✅ WebSocket broadcast to connected clients
- ✅ Device lastSeen timestamp updated
- ✅ Battery level updated (if provided)

#### Test 2B: Send Device Heartbeat
**Test:** ESP32 watch sends heartbeat signal

**API Endpoint:**
```
POST /api/v1/esp32/heartbeat
Body: {
  "deviceId": "TEST_WATCH_001",
  "patientId": "TEST001",
  "battery": 95,
  "timestamp": "2025-10-13T17:31:00Z"
}
```

**Expected Results:**
- ✅ 200 OK response
- ✅ Device lastSeen updated
- ✅ Battery level updated to 95%
- ✅ Device status remains active

---

### Phase 3: Data Receiving (Backend → Device)

#### Test 3A: Send Command to Device
**Test:** Backend sends command to ESP32 watch

**API Endpoint:**
```
POST /api/v1/watch-management/watches/{watchId}/command
Body: {
  "command": "startMonitoring",
  "parameters": {
    "interval": 30,
    "vitals": ["heartrate", "oxygensat", "temperature"]
  }
}
```

**Expected Results:**
- ✅ 200 OK response
- ✅ Command sent via MQTT (if broker available) or queued
- ✅ Command logged in system

#### Test 3B: Query Device Status
**Test:** Get current device connection and health status

**API Endpoint:**
```
GET /api/v1/watch-management/watches/TEST_WATCH_001/connection-status
```

**Expected Results:**
- ✅ 200 OK response
- ✅ Returns connection state (online/offline)
- ✅ Returns battery level
- ✅ Returns last seen timestamp
- ✅ Returns assigned patient info

---

### Phase 4: Alert Generation and Handling

#### Test 4A: Device Generates Alert
**Test:** ESP32 watch sends emergency alert

**API Endpoint:**
```
POST /api/v1/esp32/alert
Body: {
  "deviceId": "TEST_WATCH_001",
  "patientId": "TEST001",
  "alertType": "emergency",
  "severity": "high",
  "message": "Patient fall detected",
  "timestamp": "2025-10-13T17:35:00Z"
}
```

**Expected Results:**
- ✅ 200 OK response
- ✅ Alert stored in database (if alerts table exists)
- ✅ WebSocket broadcast to all connected staff
- ✅ Alert includes patient info, device info, timestamp

#### Test 4B: Backend Generates Alert (Vitals Analysis)
**Test:** Backend detects abnormal vitals and generates alert

**Trigger:** Send abnormal vitals
```json
{
  "deviceId": "TEST_WATCH_001",
  "patientId": "TEST001",
  "vitals": {
    "heartrate": 180,  // Dangerously high
    "oxygensat": 85,   // Dangerously low
    "temperature": 103.5  // High fever
  }
}
```

**Expected Results:**
- ✅ Backend analyzes vitals
- ✅ Alert generated for critical vitals
- ✅ WebSocket broadcast with severity level
- ✅ Alert logged with patient context

#### Test 4C: Query Device Alerts
**API Endpoint:**
```
GET /api/v1/watch-management/watches/TEST_WATCH_001/alerts
```

**Expected Results:**
- ✅ 200 OK response
- ✅ Returns list of recent alerts for this device
- ✅ Includes alert type, severity, timestamp
- ✅ Includes acknowledgment status

---

### Phase 5: Device Reassignment

**Test:** Reassign TEST_WATCH_001 from TEST001 to another patient

**Step 1: Unassign from TEST001**
```
POST /api/v1/watch-management/watches/TEST_WATCH_001/unassign
```

**Expected Results:**
- ✅ Current assignment marked inactive
- ✅ unassignedAt timestamp set
- ✅ Device status changes to 'available'

**Step 2: Assign to Robert Anderson**
```
POST /api/v1/watch-management/watches/TEST_WATCH_001/assign
Body: {"patientId": "7163182b-5d6e-412d-93d9-28ecfd86cc6e"}
```

**Expected Results:**
- ✅ New assignment record created
- ✅ New assignment status = 'active'
- ✅ Device now associated with Robert Anderson
- ✅ Previous assignment remains inactive in history

**Verification:**
```sql
-- Should have 2 assignments: 1 inactive (TEST001), 1 active (Robert Anderson)
SELECT * FROM deviceassignments WHERE "deviceId" = 'TEST_WATCH_001' ORDER BY "assignedAt" DESC
```

---

### Phase 6: Device Disconnect/Unassignment

**Test:** Completely unassign device (end of patient care/discharge)

**API Endpoint:**
```
POST /api/v1/watch-management/watches/TEST_WATCH_001/unassign
```

**Expected Results:**
- ✅ 200 OK response
- ✅ Active assignment marked inactive
- ✅ unassignedAt timestamp set to NOW()
- ✅ Device status returns to 'available'
- ✅ Device ready for new assignment
- ✅ Assignment history preserved

**Verification:**
```sql
-- All assignments should be inactive
SELECT * FROM deviceassignments WHERE "deviceId" = 'TEST_WATCH_001' AND status = 'active'
-- Should return 0 rows

-- Device should be available
SELECT status FROM devices WHERE id = 'TEST_WATCH_001'
-- Should return 'available'
```

---

### Phase 7: Device Health Monitoring

#### Test 7A: Get Device Health Status
**API Endpoint:**
```
GET /api/v1/watch-management/watches/TEST_WATCH_001/health
```

**Expected Results:**
- ✅ Returns battery level
- ✅ Returns last seen timestamp
- ✅ Returns firmware version
- ✅ Returns calibration status
- ✅ Returns maintenance schedule

#### Test 7B: Check All Devices Status
**API Endpoint:**
```
GET /api/v1/device-management/devices
```

**Expected Results:**
- ✅ Returns all devices in system
- ✅ Includes assignment status
- ✅ Includes health metrics
- ✅ Includes last communication time

---

## 🧪 Test Execution Strategy

### Prerequisites
1. ✅ Backend running on http://localhost:8001
2. ✅ Database connection active
3. ✅ Admin authentication token obtained
4. ✅ Test data verified (5 patients, 1 device)

### Execution Order
1. **Phase 1** - Assignment (establishes baseline)
2. **Phase 2** - Data Sending (validate device → backend flow)
3. **Phase 3** - Data Receiving (validate backend → device flow)
4. **Phase 4** - Alerts (validate emergency workflows)
5. **Phase 5** - Reassignment (validate device reuse)
6. **Phase 6** - Disconnect (validate cleanup)
7. **Phase 7** - Health Monitoring (validate operational status)

### Test Data Flow
```
TEST001 (Patient) ← Assign → TEST_WATCH_001 (Device)
    ↓
  Send Vitals/Heartbeat (Device → Backend)
    ↓
  Send Commands (Backend → Device)
    ↓
  Generate Alerts (Both Directions)
    ↓
  Unassign from TEST001
    ↓
  Reassign to Robert Anderson
    ↓
  Final Unassign (Return to pool)
```

---

## 📋 Success Criteria

### Critical (Must Pass)
- ✅ Device assignment creates active record in deviceassignments
- ✅ Vitals data successfully reaches backend
- ✅ Device status updates correctly throughout lifecycle
- ✅ Unassignment properly deactivates assignment
- ✅ Reassignment creates new active record
- ✅ Assignment history preserved (no data loss)

### Important (Should Pass)
- ✅ WebSocket broadcasts work for vitals/alerts
- ✅ Backend → device commands work (if MQTT available)
- ✅ Alert generation and routing functional
- ✅ Health monitoring endpoints return correct data
- ✅ Battery level and lastSeen update properly

### Optional (Nice to Have)
- ✅ TimescaleDB vitals storage (if available)
- ✅ MQTT communication (if broker available)
- ✅ Alert acknowledgment workflow
- ✅ Device calibration tracking

---

## 🚨 Known Limitations

1. **Alerts Table:** Not currently in database - will test WebSocket alerts instead
2. **TimescaleDB:** Not available - will verify vitals via API responses
3. **MQTT Broker:** May not be running - will test HTTP fallback
4. **Physical Devices:** No real ESP32 hardware - will simulate via API calls

---

## 📊 Expected Test Output

### Test Script Structure
```python
# 1. Authenticate
# 2. Execute Phase 1 (Assignment)
# 3. Execute Phase 2 (Data Sending)
# 4. Execute Phase 3 (Data Receiving)
# 5. Execute Phase 4 (Alerts)
# 6. Execute Phase 5 (Reassignment)
# 7. Execute Phase 6 (Disconnect)
# 8. Execute Phase 7 (Health Monitoring)
# 9. Generate comprehensive report
```

### Report Format
```
Total Tests: XX
Passed: XX
Failed: XX
Warnings: XX
Critical Failures: XX
Success Rate: XX%
```

---

*Test plan created based on actual database research*
*Ready for execution - all test data verified*
*Date: 2025-10-13*
