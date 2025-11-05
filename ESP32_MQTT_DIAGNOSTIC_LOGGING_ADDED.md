# ESP32 MQTT Diagnostic Logging - ADDED

**Date**: 2025-11-04
**Issue**: Waveform calibration commands not reaching ESP32 watch
**Status**: Added comprehensive diagnostic logging to identify root cause

---

## Problem Summary

✅ **Frontend** → WebSocket sends `triggerWaveformCalibration: true`
✅ **Backend** → Receives WebSocket message
✅ **Backend** → Publishes MQTT to `hospital/devices/fit-00001/commands`
❌ **ESP32 Watch** → Does NOT receive MQTT messages (no Serial output)

**Root Cause Location**: MQTT broker/routing layer between backend and ESP32

---

## Diagnostic Logging Added

### 1. MQTT Callback Entry (Line 1665-1667)
```cpp
void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  Serial.println("🔔 MQTT CALLBACK TRIGGERED!");
  Serial.println("   Topic: " + String(topic));
  Serial.println("   Length: " + String(length));
```

**What This Shows**:
- ✅ If you see "🔔 MQTT CALLBACK TRIGGERED!" → ESP32 is receiving MQTT messages
- ❌ If you DON'T see this → ESP32 MQTT subscription is broken or messages aren't being routed

---

### 2. MQTT Subscription Verification (Line 1642-1650)
```cpp
Serial.println("🔑 Current deviceId: '" + deviceId + "'");

String assignTopic = "hospital/devices/" + deviceId + "/assign";
bool assignSuccess = mqttClient.subscribe(assignTopic.c_str());
Serial.println("📡 Subscribed to: " + assignTopic + (assignSuccess ? " ✅" : " ❌"));

String commandTopic = "hospital/devices/" + deviceId + "/commands";
bool commandSuccess = mqttClient.subscribe(commandTopic.c_str());
Serial.println("📡 Subscribed to: " + commandTopic + (commandSuccess ? " ✅" : " ❌"));
```

**What This Shows**:
- Shows the actual `deviceId` being used for subscription
- Shows if MQTT subscription succeeds (✅) or fails (❌)
- **CRITICAL**: Verify deviceId matches what backend is publishing to (`fit-00001`)

---

### 3. Command Parsing Diagnostics (Line 1690-1714)
```cpp
if (String(topic).endsWith("/commands")) {
  Serial.println("✅ Topic ends with /commands - processing command");

  DeserializationError error = deserializeJson(doc, message);
  if (error == DeserializationError::Ok) {
    String commandType = doc["command"].as<String>();
    String commandId = doc["commandId"].as<String>();
    Serial.println("🎯 Command parsed: type='" + commandType + "', id='" + commandId + "'");

    if (commandType == "waveformCalibrate") {
      Serial.println("🔧 Handling waveformCalibrate command");
      handleWaveformCalibrationCommand(commandId);
```

**What This Shows**:
- If topic matching works correctly
- If JSON deserialization succeeds
- What command type is being parsed
- If `waveformCalibrate` handler is being called

---

## Testing Instructions

### Step 1: Flash Updated Firmware
```bash
# Open Arduino IDE
# Select ESP32 board and correct COM port
# Upload esp32_hospital_watch_complete.ino
```

### Step 2: Monitor Serial Output
```bash
# Open Serial Monitor at 115200 baud
# Watch for these messages during boot:
```

**Expected Boot Sequence**:
```
✅ MQTT Connected with client certificate (mTLS)!
🔑 Current deviceId: 'fit-00001'
📡 Subscribed to: hospital/devices/fit-00001/assign ✅
📡 Subscribed to: hospital/devices/fit-00001/commands ✅
```

**CRITICAL CHECKS**:
1. ✅ Does deviceId match `fit-00001`?
2. ✅ Do both subscriptions succeed (show ✅)?
3. ✅ Is MQTT connection stable (no reconnects)?

### Step 3: Trigger Waveform Calibration from Frontend
1. Open ECG Viewer page in frontend
2. Watch Serial Monitor for these messages:

**Expected Message Flow** (if working):
```
🔔 MQTT CALLBACK TRIGGERED!
   Topic: hospital/devices/fit-00001/commands
   Length: 156
📨 MQTT Message: hospital/devices/fit-00001/commands -> {"command":"waveformCalibrate",...}
✅ Topic ends with /commands - processing command
🎯 Command parsed: type='waveformCalibrate', id='...'
🔧 Handling waveformCalibrate command
🔧 Waveform calibration command received
✅ Waveform calibration complete - waveforms will contain calibration data
```

---

## Diagnostic Scenarios

### Scenario A: NO OUTPUT AT ALL
**Symptoms**:
- ❌ No "🔔 MQTT CALLBACK TRIGGERED!" message

**Root Cause**: MQTT messages not reaching ESP32

**Possible Issues**:
1. **Wrong deviceId** - ESP32 subscribed to different topic than backend publishes to
2. **MQTT broker ACL** - Access control blocking message delivery
3. **MQTT connection dropped** - ESP32 disconnected but hasn't reconnected
4. **Topic mismatch** - Typo in topic string construction

**Next Steps**:
- Verify deviceId in Serial output matches backend logs
- Check Mosquitto ACL configuration
- Test with `mosquitto_sub` to see if messages are published:
  ```bash
  mosquitto_sub -h localhost -p 8883 \
    -t "hospital/devices/fit-00001/commands" \
    --cafile hospital_ca.crt --cert client.crt --key client.key -v
  ```

---

### Scenario B: CALLBACK TRIGGERS BUT NO COMMAND PARSED
**Symptoms**:
- ✅ See "🔔 MQTT CALLBACK TRIGGERED!"
- ❌ Don't see "✅ Topic ends with /commands"

**Root Cause**: Topic string doesn't match expected format

**Possible Issues**:
- Topic name changed in backend but not ESP32
- String comparison issue (case sensitivity, extra characters)

**Next Steps**:
- Compare topic printed in Serial output with expected topic
- Check backend code for topic name changes

---

### Scenario C: COMMAND RECEIVED BUT JSON PARSE FAILS
**Symptoms**:
- ✅ See "🔔 MQTT CALLBACK TRIGGERED!"
- ✅ See "✅ Topic ends with /commands"
- ❌ See "❌ Failed to parse command JSON"

**Root Cause**: JSON format mismatch between backend and ESP32

**Possible Issues**:
- Backend sending different JSON structure than ESP32 expects
- JSON too large for ESP32 ArduinoJson buffer
- Malformed JSON from backend

**Next Steps**:
- Check the raw message printed in Serial output
- Compare with expected format: `{"command":"waveformCalibrate","commandId":"...","timestamp":"...","triggeredBy":"...","patientId":"..."}`
- Increase ArduinoJson buffer size if needed

---

### Scenario D: COMMAND PARSED BUT WRONG TYPE
**Symptoms**:
- ✅ See "🔔 MQTT CALLBACK TRIGGERED!"
- ✅ See "🎯 Command parsed: type='...'"
- ❌ Command type is NOT 'waveformCalibrate'

**Root Cause**: Backend sending wrong command type

**Possible Issues**:
- Backend code still using old "calibrate" instead of "waveformCalibrate"
- Typo in backend command generation

**Next Steps**:
- Check backend `_triggerWaveformCalibration()` function (websocket.py line 288)
- Verify command is: `{'command': 'waveformCalibrate', ...}`

---

## Files Modified

1. **esp32_hospital_watch_complete.ino**
   - Line 1665-1667: Added MQTT callback entry logging
   - Line 1642-1650: Added deviceId and subscription success logging
   - Line 1690-1714: Added command parsing diagnostic logging

---

## Expected Outcome

After flashing the updated firmware and triggering waveform calibration from the frontend, you should see a complete message flow in the Serial Monitor showing:

1. ✅ ESP32 boots and connects to MQTT
2. ✅ ESP32 subscribes to correct topics
3. ✅ ESP32 receives MQTT message on `/commands` topic
4. ✅ ESP32 parses `waveformCalibrate` command
5. ✅ ESP32 executes waveform calibration handler
6. ✅ ESP32 publishes completion notification

**If ANY step fails, the diagnostic logging will show exactly WHERE the failure occurs.**

---

## Next Actions for User

1. **Flash the updated firmware to ESP32 watch**
2. **Open Serial Monitor (115200 baud)**
3. **Verify MQTT connection and subscriptions at boot**
4. **Trigger waveform calibration from frontend ECG Viewer**
5. **Report back which diagnostic messages you see (or don't see)**

Based on the output, we can pinpoint the exact root cause:
- MQTT broker issue
- Topic mismatch
- JSON format issue
- Command type mismatch
- Or something else entirely

---

## Backend Verification

The backend is already confirmed working:
```
✅ Backend receives WebSocket: triggerWaveformCalibration=True
✅ Backend looks up patient and device
✅ Backend publishes MQTT: topic=hospital/devices/fit-00001/commands
✅ Backend logs: 📤 Command sent to fit-00001: {'command': 'waveformCalibrate', ...}
```

**The issue is in the MQTT layer between backend publish and ESP32 receive.**

---

**Status**: Ready for testing - please flash firmware and report Serial Monitor output.
