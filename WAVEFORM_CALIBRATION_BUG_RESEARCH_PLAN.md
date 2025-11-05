# Waveform Calibration Bug - Research & Audit Plan

## Issue Summary

**Problem:** Waveform calibration commands are not reaching the ESP32.

**Evidence:**
- ✅ Frontend logs show: `"🔧 Waveform calibration requested for patient: 081a5294..."`
- ❌ Backend logs show: **NOTHING** (no calibration messages at all)
- ❌ ESP32 never receives the command

**Status After Renaming:**
- ✅ All code renamed from "calibration" to "waveformCalibration"
- ❌ Bug still exists (command not reaching ESP32)

---

## Known Facts

### 1. ESP32 Can Send Data Successfully
- Vitals are being sent and received
- Waveforms are being sent and received
- Device is connected to MQTT
- Device ID is correct (otherwise no data would flow)

### 2. Frontend Sends Request Successfully
- WebSocket sends: `{type: 'subscribePatient', patientId: 'xxx', triggerWaveformCalibration: true}`
- Log shows: "Waveform calibration requested"

### 3. Backend Receives WebSocket Messages
- WebSocket connection is established
- Other messages work (subscribePatient without triggerWaveformCalibration)

### 4. Backend Has No Calibration Logs
- No "🔧 Waveform calibration triggered" message
- No "⚠️ Could not trigger waveform calibration" message
- No "📤 Waveform calibration command sent" message

**Conclusion:** Backend WebSocket handler is NOT executing the waveform calibration code.

---

## Root Cause Hypothesis

**Most Likely:** Line 113 condition is False

```python
if success and triggerWaveformCalibration:
    # This code never runs
```

**Possible reasons:**

1. **`success` is False** - `connectionManager.subscribeToPatient()` returns False
2. **`triggerWaveformCalibration` is None/False** - Message doesn't contain the field
3. **Code never reached** - Exception happens before this point

---

## Research Plan

### Phase 1: Verify Message Format

**Question:** Is the frontend sending `triggerWaveformCalibration` correctly?

**Check:**
1. Browser DevTools → Network tab → WebSocket frames
2. Look for outgoing message when ECG viewer opens
3. Verify message contains: `{"type": "subscribePatient", "patientId": "xxx", "triggerWaveformCalibration": true}`

**Expected:** Message should have `triggerWaveformCalibration: true`

**If missing:** Frontend is not sending the field (check WebSocketService.ts line 236)

---

### Phase 2: Add Backend Debug Logging

**Add logging to see exactly what's happening:**

**File:** `hospital-backend/app/api/v1/websocket.py`

**Changes:**
```python
async def handleClientMessage(connectionId: str, message: Dict[str, Any]) -> None:
    """Handle incoming messages from WebSocket clients"""

    logger.info(f"🔵 DEBUG: Received message: {message}")  # ← ADD THIS

    messageType = message.get('type')

    if messageType == 'subscribePatient':
        patientId = message.get('patientId')
        triggerWaveformCalibration = message.get('triggerWaveformCalibration', False)

        logger.info(f"🔵 DEBUG: subscribePatient - patientId={patientId}, trigger={triggerWaveformCalibration}")  # ← ADD THIS

        if patientId:
            async with getDbConnection() as conn:
                patient = await fetchOne(conn, "SELECT id FROM patients WHERE id = $1 AND status = 'active'", (patientId,))

                logger.info(f"🔵 DEBUG: Patient found: {patient is not None}")  # ← ADD THIS

                if patient:
                    success = connectionManager.subscribeToPatient(connectionId, patientId)

                    logger.info(f"🔵 DEBUG: subscribeToPatient success={success}")  # ← ADD THIS

                    # ... send subscription result ...

                    if success and triggerWaveformCalibration:
                        logger.info(f"🔵 DEBUG: About to trigger waveform calibration")  # ← ADD THIS
                        try:
                            deviceId = await _getDeviceForPatient(patientId)
                            logger.info(f"🔵 DEBUG: Device ID: {deviceId}")  # ← ADD THIS

                            if deviceId:
                                logger.info(f"🔵 DEBUG: Calling _triggerWaveformCalibration")  # ← ADD THIS
                                await _triggerWaveformCalibration(deviceId, patientId)
                                logger.info(f"🔧 Waveform calibration triggered for device {deviceId} (patient {patientId})")
                            else:
                                logger.warning(f"⚠️ No device found for patient {patientId}")
                        except Exception as e:
                            logger.error(f"⚠️ Could not trigger waveform calibration for patient {patientId}: {e}", exc_info=True)
                    else:
                        logger.info(f"🔵 DEBUG: Calibration NOT triggered - success={success}, trigger={triggerWaveformCalibration}")  # ← ADD THIS
```

**This will show:**
1. Is message being received?
2. What is patientId?
3. What is triggerWaveformCalibration value?
4. Is patient found in database?
5. Does subscribeToPatient return True or False?
6. Why calibration code doesn't run?

---

### Phase 3: Check ConnectionManager

**Question:** Why might `subscribeToPatient()` return False?

**File:** `hospital-backend/app/services/websocket_manager.py` (or wherever ConnectionManager is)

**Check:**
1. What conditions make `subscribeToPatient()` return False?
2. Are there any logs/warnings from ConnectionManager?

**Possible issues:**
- Patient ID not found in subscriptions
- Connection ID invalid
- Subscription limit reached
- Internal error (silently caught)

---

### Phase 4: Check MQTT Service Status

**Question:** Is MQTT service actually connected?

**File:** `hospital-backend/app/services/mqtt_service.py`

**Check:**
1. Is `mqttService.connected` True?
2. Are there any MQTT connection errors in backend logs?

**Test:**
```python
# Add to _triggerWaveformCalibration before publishing
logger.info(f"🔵 DEBUG: MQTT connected: {mqttService.connected}")
logger.info(f"🔵 DEBUG: MQTT client: {mqttService.client}")
```

---

### Phase 5: Manual MQTT Test

**Bypass backend entirely and publish directly to MQTT:**

```bash
cd c:\Users\Srika\OneDrive\Desktop\hospital-management-system\mosquitto

mosquitto_pub -h localhost -p 8883 ^
  --cafile certs/ca.crt ^
  --cert certs/client.crt ^
  --key certs/client.key ^
  -t "hospital/devices/fit-00001/commands" ^
  -m "{\"command\":\"waveformCalibrate\",\"commandId\":\"test-123\",\"timestamp\":\"2025-01-04T12:00:00Z\",\"triggeredBy\":\"manual\",\"patientId\":\"081a5294-da91-4c74-bb8a-e5062f5851dd\"}"
```

**Check ESP32 Serial Monitor:**
- Should see: "🔧 Waveform calibration command received"

**If ESP32 receives it:** Backend MQTT publishing is the issue
**If ESP32 doesn't receive it:** ESP32 subscription or MQTT broker is the issue

---

## Diagnostic Decision Tree

```
1. Open ECG viewer
   |
   v
2. Check frontend logs
   |
   +--[No "Waveform calibration requested"]
   |     → Frontend not sending request (bug in useECGViewer.ts)
   |
   +--[YES "Waveform calibration requested"]
       |
       v
   3. Check backend logs (with debug logging added)
       |
       +--[No "Received message"]
       |     → WebSocket not connected or message not received
       |
       +--[No "subscribePatient"]
       |     → Message type not recognized
       |
       +--[No "Patient found"]
       |     → Patient not in database or inactive
       |
       +--[subscribeToPatient success=False]
       |     → ConnectionManager issue (check Phase 3)
       |
       +--[trigger=False or None]
       |     → Message doesn't contain triggerWaveformCalibration field
       |
       +--[No "Device ID"]
       |     → _getDeviceForPatient returns None (no device assigned)
       |
       +--[No "Calling _triggerWaveformCalibration"]
       |     → deviceId is None
       |
       +--[Exception in _triggerWaveformCalibration]
       |     → Check exception details (MQTT error?)
       |
       +--[All debug logs present, still no ESP32 response]
             → MQTT publish failed silently (check Phase 4)
```

---

## Expected Outcomes

### Scenario A: Frontend Not Sending Field
**Symptom:** Backend logs show `trigger=False` or `trigger=None`
**Fix:** Check `WebSocketService.ts:236` - ensure `triggerWaveformCalibration: true` is in message

### Scenario B: subscribeToPatient Returns False
**Symptom:** Backend logs show `success=False`
**Fix:** Check ConnectionManager implementation - why is subscription failing?

### Scenario C: Patient Not Found
**Symptom:** Backend logs show `Patient found: False`
**Fix:** Check patient ID matches database, status is 'active'

### Scenario D: No Device Assigned
**Symptom:** Backend logs show `Device ID: None`
**Fix:** Verify device `fit-00001` is assigned to patient in database

### Scenario E: MQTT Not Connected
**Symptom:** Backend logs show `MQTT connected: False`
**Fix:** Restart backend, check MQTT broker status

### Scenario F: MQTT Publish Fails Silently
**Symptom:** All logs present, but ESP32 doesn't receive
**Fix:** Check MQTT ACL, topic permissions, QoS settings

---

## Next Steps

1. **Add debug logging** to backend WebSocket handler (Phase 2)
2. **Open ECG viewer** and trigger waveform calibration
3. **Check backend logs** - follow decision tree
4. **Identify exact failure point**
5. **Implement proper fix** based on findings

**Ready to add debug logging?**
