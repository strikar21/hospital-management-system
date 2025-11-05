# Waveform Calibration Rename - Complete ✅

## Summary

Successfully renamed all "calibration" references to "waveformCalibration" across backend, frontend, and ESP32 to distinguish from device calibration (hardware sensor calibration).

## Files Changed

### 1. Backend - `hospital-backend/app/api/v1/websocket.py`

**Changes:**
- Line 96: `triggerCalibration` → `triggerWaveformCalibration`
- Line 112: Comment updated to "waveform calibration"
- Line 113: `triggerCalibration` → `triggerWaveformCalibration`
- Line 117: `_triggerDeviceCalibration` → `_triggerWaveformCalibration`
- Line 118: Log "Calibration triggered" → "Waveform calibration triggered"
- Line 120: Log "Could not trigger calibration" → "Could not trigger waveform calibration"
- Line 243: Comment "CALIBRATION HELPERS" → "WAVEFORM CALIBRATION HELPERS"
- Line 261: Function `_triggerDeviceCalibration` → `_triggerWaveformCalibration`
- Line 262: Comment "calibration command" → "waveform calibration command"
- Line 268: `'command': 'calibrate'` → `'command': 'waveformCalibrate'`
- Line 276: Log "Calibration command sent" → "Waveform calibration command sent"

---

### 2. Frontend - `hospital-display-app/src/services/WebSocketService.ts`

**Changes:**
- Line 163: Parameter `triggerCalibration?` → `triggerWaveformCalibration?`
- Line 176: Parameter `triggerCalibration` → `triggerWaveformCalibration`
- Line 177: Variable `triggerWaveformCalibration` in condition
- Line 179: Function call `requestCalibration` → `requestWaveformCalibration`
- Line 222: Parameter `triggerCalibration?` → `triggerWaveformCalibration?`
- Line 236: Property `triggerCalibration` → `triggerWaveformCalibration`
- Line 240: Log "calibration trigger" → "waveform calibration trigger"
- Line 244: Comment "Request calibration pulse" → "Request waveform calibration"
- Line 246: Function `requestCalibration` → `requestWaveformCalibration`
- Line 248: Log "Cannot request calibration" → "Cannot request waveform calibration"
- Line 255: Property `triggerCalibration` → `triggerWaveformCalibration`
- Line 259: Log "Calibration requested" → "Waveform calibration requested"

---

### 3. ESP32 - `esp32_hospital_watch_complete.ino`

**Changes:**
- Line 226: `calibrationDue` → `waveformCalibrationDue`
- Line 941: Function `handleCalibrationCommand` → `handleWaveformCalibrationCommand`
- Line 942: Log "Calibration command received" → "Waveform calibration command received"
- Line 944: Comment "calibration pulse" → "waveform calibration"
- Line 959: Topic `calibration_complete` → `waveform_calibration_complete`
- Line 969: Variable `calibrationDue` → `waveformCalibrationDue`
- Line 970: Message "Calibration pulse sent" → "Waveform calibration sent"
- Line 972: Log "Calibration pulse complete" → "Waveform calibration complete"
- Line 1696: Command check `"calibrate"` → `"waveformCalibrate"`
- Line 1697: Function call `handleCalibrationCommand` → `handleWaveformCalibrationCommand`

---

## New Data Flow

```
Frontend (ECG Viewer)
  → sends: {type: 'subscribePatient', patientId: 'xxx', triggerWaveformCalibration: true}

Backend (WebSocket Handler)
  → receives: triggerWaveformCalibration
  → calls: _triggerWaveformCalibration(deviceId, patientId)
  → sends MQTT: {command: 'waveformCalibrate', commandId: 'xxx', ...}
  → topic: hospital/devices/{deviceId}/commands

ESP32
  → receives: {command: 'waveformCalibrate', ...}
  → calls: handleWaveformCalibrationCommand(commandId)
  → executes: simulator.startCalibrationPulse()
  → publishes: hospital/devices/{deviceId}/waveform_calibration_complete
```

---

## Benefits

1. **Clear Distinction:** No confusion between waveform calibration (visual reference) and device calibration (hardware)
2. **Searchability:** Can grep for "waveformCalibration" vs "device calibration"
3. **Maintainability:** Self-documenting code
4. **Consistency:** Same terminology across all layers (frontend, backend, ESP32)

---

## Next Step: Fix the Bug

Now that renaming is complete, we need to fix why waveform calibration commands aren't reaching the ESP32.

**Known Issue:** Frontend logs show "🔧 Waveform calibration requested" but backend logs show nothing.

**Most Likely Cause:** `success = connectionManager.subscribeToPatient()` returns False, so `if success and triggerWaveformCalibration:` never executes.

**Next Action:** Add debug logging to backend to diagnose why the code isn't executing.
