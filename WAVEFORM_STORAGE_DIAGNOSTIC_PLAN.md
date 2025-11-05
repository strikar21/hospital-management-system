# Waveform Storage Diagnostic Plan

## Current Status (2025-11-02 13:21 UTC)

### Confirmed Facts
1. **Backend running**: Port 8001, PID 67332 ✅
2. **ESP32 fit-00001 active**: Sending vitals every ~1 second ✅
3. **Vitals flowing to database**: 8 vitals in last 10 seconds in `vitals_realtime` table ✅
4. **Waveforms NOT being stored**: 0 rows in `waveform_snapshots` table ❌

### Code Locations
- **ESP32 Firmware**: [esp32_hospital_watch_complete.ino:1925](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1925) - Publishes to `/stream` topic
- **Backend MQTT Handler**: [mqtt_service.py:406-409](hospital-backend/app/services/mqtt_service.py#L406-L409) - Routes to `_handleWaveformStream()`
- **Backend Storage Code**: [mqtt_service.py:745-771](hospital-backend/app/services/mqtt_service.py#L745-L771) - Stores waveform snapshots (ADDED BY ME)

### Database Schema
- Table: `waveform_snapshots` (TimescaleDB hypertable)
- Columns: time, patientId, deviceId, mode, sampleRate, duration, ecgLimbLeads, etc. (ALL camelCase ✅)
- Created by: [migration 010](hospital-backend/migrations/010_create_neural_waveform_tables.sql)

## Problem Hypothesis

### Hypothesis 1: ESP32 Not Publishing to /stream Topic
**Test**: Check MQTT broker logs or backend logs for `/stream` messages
**Likelihood**: Medium
**Evidence Needed**: Backend log should show "MQTT STREAM MESSAGE RECEIVED" if messages arrive

### Hypothesis 2: Backend Not Receiving /stream Messages
**Test**: Check backend logs for MQTT routing messages
**Likelihood**: Medium
**Evidence Needed**: Log line "ROUTING stream message" should appear if routing is working

### Hypothesis 3: Storage Code Encountering Errors
**Test**: Check backend logs for storage errors
**Likelihood**: High
**Evidence Needed**: Log line "Stream packet storage failed (non-critical)" should show error details

### Hypothesis 4: Device Assignment Validation Failing
**Test**: Check if device assignment validation is blocking storage
**Likelihood**: Low (vitals are flowing, so assignment is valid)
**Evidence Needed**: Log line "Device assignment validated" should appear

## Diagnostic Steps (In Order)

### Step 1: Check Backend Logs for /stream Messages
**Action**: Search backend output for "MQTT STREAM MESSAGE RECEIVED"
**Expected**: Should see log entries if ESP32 is publishing to `/stream`
**Location**: Backend console output or log file

### Step 2: Check if _handleWaveformStream is Being Called
**Action**: Search backend output for "_handleWaveformStream ENTERED"
**Expected**: Should see function entry logs with payload details
**Location**: Backend console output

### Step 3: Check for Storage Errors
**Action**: Search backend output for "Stream packet storage failed"
**Expected**: Should see error details if storage is failing
**Location**: Backend console output

### Step 4: Verify ESP32 /stream Publishing
**Action**: Check ESP32 serial output or MQTT broker logs
**Expected**: Should see messages published to `hospital/devices/fit-00001/stream`
**Location**: ESP32 serial monitor or Mosquitto logs

### Step 5: Check Backend Storage Function
**Action**: Verify `_storeWaveformSnapshot()` function is working
**Expected**: Function should successfully insert into TimescaleDB
**Location**: [mqtt_service.py:594-645](hospital-backend/app/services/mqtt_service.py#L594-L645)

## Next Actions

1. **Immediate**: Check if backend is logging `/stream` messages
2. **If no logs**: ESP32 is not publishing to `/stream`, need to check firmware
3. **If logs exist**: Check for errors in storage code
4. **If errors found**: Fix the specific error encountered
5. **If no errors**: Verify database connection and table schema

## Questions to Answer

1. Is ESP32 actually publishing to `/stream` topic? (NOT VERIFIED)
2. Is backend receiving `/stream` messages? (NOT VERIFIED)
3. Is `_handleWaveformStream()` being called? (NOT VERIFIED)
4. Is storage code throwing errors? (NOT VERIFIED)
5. Is database connection working for waveform storage? (NOT VERIFIED)

## Success Criteria

- Backend logs show "MQTT STREAM MESSAGE RECEIVED" entries
- Backend logs show "_handleWaveformStream ENTERED" entries
- Backend logs show "Stream packet #X stored to database" (every 10th packet)
- Database query shows waveform_snapshots row count > 0
- Database query shows recent waveforms (last 10 seconds)
