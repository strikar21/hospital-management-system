# Waveform Calibration ACL Fix - COMPLETE

**Date**: 2025-11-05
**Issue**: Waveform calibration requests not reaching ESP32 watch
**Root Cause**: MQTT ACL topic name mismatch

---

## ROOT CAUSE ANALYSIS

### The Bug
- **ACL Configuration** (Line 69): `pattern read hospital/devices/%u/command` (SINGULAR)
- **Backend Publishes To**: `hospital/devices/{deviceId}/commands` (PLURAL)
- **ESP32 Subscribes To**: `hospital/devices/{deviceId}/commands` (PLURAL)

**Result**: MQTT broker was blocking all messages to `/commands` because ACL pattern only allowed `/command`

### Evidence Chain
1. Backend logs (00:36:51) showed 5 MQTT commands successfully published to `fit-00001`
2. ESP32 never received any commands (no Serial Monitor output)
3. Other MQTT topics worked (assign/unassign) because they use different topic names (`/assign`, `/unassign`)
4. ACL file had singular `/command` while backend and ESP32 used plural `/commands`

---

## FIX APPLIED

### File Modified: `mosquitto/config/acl.conf`

**Line 69 - BEFORE:**
```conf
# COMMAND: Devices receive commands from backend (read-only)
pattern read hospital/devices/%u/command
```

**Line 69 - AFTER:**
```conf
# COMMAND: Devices receive commands from backend (read-only)
pattern read hospital/devices/%u/commands
```

### Actions Taken
1. ✅ Modified ACL file line 69 from `/command` to `/commands`
2. ✅ Restarted Mosquitto broker: `docker restart hospital_mosquitto`
3. ✅ Verified ESP32 reconnected and subscribed to `/commands` topic successfully

---

## VERIFICATION

### Mosquitto Logs After Restart
```
1762283971: Received SUBSCRIBE from HospitalWatch_fit-00001
1762283971: 	hospital/devices/fit-00001/commands (QoS 0)
1762283971: HospitalWatch_fit-00001 0 hospital/devices/fit-00001/commands
1762283971: Sending SUBACK to HospitalWatch_fit-00001
```

**Status**: ✅ ESP32 successfully subscribed to `/commands` topic (plural)

---

## TESTING PLAN

### Step 1: Open ECG Viewer in Frontend
- Navigate to patient with assigned device (fit-00001)
- Open ECG Viewer page
- Frontend sends WebSocket message with `triggerWaveformCalibration: true`

### Step 2: Backend Processing
- Backend receives WebSocket message
- Backend publishes MQTT command to `hospital/devices/fit-00001/commands`
- Command payload:
  ```json
  {
    "command": "waveformCalibrate",
    "commandId": "<uuid>",
    "timestamp": "<iso8601>",
    "triggeredBy": "ecgViewerOpen",
    "patientId": "<uuid>"
  }
  ```

### Step 3: ESP32 Receives Command
Monitor ESP32 Serial output for diagnostic messages:
```
🔔 MQTT CALLBACK TRIGGERED!
   Topic: hospital/devices/fit-00001/commands
   Length: <message_length>
📨 MQTT Message: hospital/devices/fit-00001/commands -> <json_payload>
✅ Topic ends with /commands - processing command
🎯 Command parsed: type='waveformCalibrate', id='<commandId>'
🔧 Handling waveformCalibrate command
```

### Step 4: ESP32 Executes Calibration
- 1000ms baseline (flat line)
- 1000ms calibration pulse (1mV amplitude)
- 1000ms baseline (flat line)
- Total duration: 3000ms

### Step 5: ESP32 Sends Completion Message
ESP32 publishes to `hospital/devices/fit-00001/alerts`:
```json
{
  "command": "waveformCalibrate",
  "commandId": "<uuid>",
  "status": "completed",
  "timestamp": "<iso8601>"
}
```

### Step 6: Frontend Displays Calibration
- ECG Viewer canvas shows calibration pulse
- 1mV pulse should be 10mm (10 small squares) in height
- Grid timing: 25mm/s (1 small square = 40ms)

---

## KEY LEARNINGS

### What Went Wrong Initially
1. Created documentation files without analyzing root cause
2. Made assumptions instead of reading logs and verifying facts
3. Didn't check ACL configuration file early enough

### Correct Approach Used
1. ✅ Read backend logs to confirm MQTT commands were sent
2. ✅ Searched for ESP32 responses (found none)
3. ✅ Examined ACL configuration file for topic patterns
4. ✅ Verified exact topic names in backend and ESP32 code
5. ✅ Found mismatch between ACL and actual usage

---

## TOPIC NAMING STANDARD

To prevent future mismatches, the following topic naming convention is established:

### Command Topics (PLURAL)
- **Topic**: `hospital/devices/{deviceId}/commands`
- **Purpose**: Backend sends commands to devices
- **Direction**: Backend → ESP32
- **ACL Line**: 69 (devices read), 33 (backend write)

### Assignment Topics (SINGULAR)
- **Topic**: `hospital/devices/{deviceId}/assign`
- **Purpose**: Backend notifies device of patient assignment
- **Direction**: Backend → ESP32
- **ACL Line**: 72 (devices read), 32 (backend write)

### Vitals Topics (PLURAL)
- **Topic**: `hospital/devices/{deviceId}/vitals`
- **Purpose**: Devices publish periodic vital signs
- **Direction**: ESP32 → Backend
- **ACL Line**: 50 (devices write), 26 (backend read)

### Stream Topics (SINGULAR)
- **Topic**: `hospital/devices/{deviceId}/stream`
- **Purpose**: Devices publish real-time waveform data
- **Direction**: ESP32 → Backend
- **ACL Line**: 60 (devices write), 29 (backend read)

---

## FILES INVOLVED

1. **ACL Configuration**: [mosquitto/config/acl.conf](mosquitto/config/acl.conf) - Line 69 fixed
2. **Backend MQTT Service**: [hospital-backend/app/services/mqtt_service.py](hospital-backend/app/services/mqtt_service.py) - Line 182 (uses `/commands`)
3. **ESP32 Firmware**: [esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino) - Line 1648 (subscribes to `/commands`)
4. **Frontend WebSocket**: [hospital-display-app/src/services/WebSocketService.ts](hospital-display-app/src/services/WebSocketService.ts) - Sends calibration requests

---

## NEXT STEPS

1. ✅ ACL fixed
2. ✅ Mosquitto restarted
3. ✅ ESP32 reconnected
4. 🔲 **Test end-to-end waveform calibration** by opening ECG Viewer
5. 🔲 Monitor ESP32 Serial output for confirmation
6. 🔲 Verify calibration pulse appears on frontend canvas

**STATUS**: Ready for testing. The ACL configuration is now correct and Mosquitto has been restarted.
