# Debug Logging Added - Ready to Test

## Changes Made

**File:** `hospital-backend/app/api/v1/websocket.py`

Added comprehensive debug logging to track waveform calibration flow:

### Debug Logs Added:

1. **Line 91:** Message received
   - `"🔵 DEBUG: Received WebSocket message: type=..., keys=..."`

2. **Line 100:** Parse subscribePatient parameters
   - `"🔵 DEBUG: subscribePatient - patientId=..., triggerWaveformCalibration=..."`

3. **Line 107:** Patient database lookup
   - `"🔵 DEBUG: Patient lookup - found=..."`

4. **Line 112:** subscribeToPatient result
   - `"🔵 DEBUG: subscribeToPatient returned success=..."`

5. **Line 123:** Check calibration condition
   - `"🔵 DEBUG: Checking waveform calibration - success=..., trigger=..."`

6. **Line 126:** About to trigger calibration
   - `"🔵 DEBUG: About to trigger waveform calibration for patient ..."`

7. **Line 129:** Device lookup result
   - `"🔵 DEBUG: Device lookup returned deviceId=..."`

8. **Line 132:** Calling trigger function
   - `"🔵 DEBUG: Calling _triggerWaveformCalibration for device ..."`

9. **Line 134:** Success
   - `"🔧 Waveform calibration triggered for device ..."`

10. **Line 136:** No device found
    - `"⚠️ No device found for patient ..."`

11. **Line 138:** Exception caught
    - `"⚠️ Could not trigger waveform calibration for patient ...: {exception}"`

12. **Line 140:** Calibration not triggered
    - `"🔵 DEBUG: Waveform calibration NOT triggered - success=..., trigger=..."`

---

## Testing Instructions

### Step 1: Restart Backend (if needed)

Backend should pick up changes automatically (FastAPI hot reload), but if not:

```bash
cd c:/Users/Srika/OneDrive/Desktop/hospital-management-system/hospital-backend
# Stop and restart backend
```

### Step 2: Open Backend Console

Make sure you can see backend logs in the terminal/console.

### Step 3: Open ECG Viewer

1. Open frontend: http://localhost:3000
2. Login as NUR0001
3. Click on patient "Thomas Brown" (081a5294...)
4. Click "View ECG" or open ECG viewer

### Step 4: Check Backend Logs

Look for the blue debug messages (🔵 DEBUG) in backend console.

**Expected log sequence:**

```
🔵 DEBUG: Received WebSocket message: type=subscribePatient, keys=['type', 'patientId', 'triggerWaveformCalibration']
🔵 DEBUG: subscribePatient - patientId=081a5294-da91-4c74-bb8a-e5062f5851dd, triggerWaveformCalibration=True
🔵 DEBUG: Patient lookup - found=True
🔵 DEBUG: subscribeToPatient returned success=True
🔵 DEBUG: Checking waveform calibration - success=True, trigger=True
🔵 DEBUG: About to trigger waveform calibration for patient 081a5294-da91-4c74-bb8a-e5062f5851dd
🔵 DEBUG: Device lookup returned deviceId=fit-00001
🔵 DEBUG: Calling _triggerWaveformCalibration for device fit-00001
🔧 Waveform calibration triggered for device fit-00001 (patient 081a5294-da91-4c74-bb8a-e5062f5851dd)
📤 Waveform calibration command sent to device fit-00001 (commandId: xxx-xxx-xxx)
```

---

## Diagnostic Scenarios

### Scenario A: No logs at all
**Meaning:** WebSocket message not reaching backend
**Action:** Check frontend WebSocket connection, check browser console

### Scenario B: `triggerWaveformCalibration=False`
**Meaning:** Frontend not sending the field correctly
**Action:** Check `WebSocketService.ts:236` - ensure field is in message

### Scenario C: `Patient lookup - found=False`
**Meaning:** Patient not in database or status != 'active'
**Action:** Check database patient table

### Scenario D: `subscribeToPatient returned success=False`
**Meaning:** ConnectionManager refusing subscription
**Action:** Check ConnectionManager implementation

### Scenario E: `Device lookup returned deviceId=None`
**Meaning:** No device assigned to patient
**Action:** Check deviceassignments table

### Scenario F: All logs present, but ESP32 doesn't respond
**Meaning:** MQTT publish failing or ESP32 not subscribed
**Action:** Check MQTT broker, ESP32 subscription

---

## What to Report

After testing, report:

1. **Did you see ANY debug logs?** (Yes/No)
2. **If yes, paste the logs** (all blue DEBUG lines)
3. **Where did the flow stop?** (which was the last log you saw)
4. **Any errors or warnings?** (red/yellow messages)

This will tell us EXACTLY where the bug is!
