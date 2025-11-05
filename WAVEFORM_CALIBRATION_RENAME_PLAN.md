# Waveform Calibration Rename Plan

## New Terminology

**OLD:** `calibration` / `calibrate` / `triggerCalibration`
**NEW:** `waveformCalibration` / `waveformCalibrate` / `triggerWaveformCalibration`

This distinguishes it from device calibration (hardware sensor calibration).

## Files to Change

### 1. Backend - WebSocket Handler
**File:** `hospital-backend/app/api/v1/websocket.py`

**Changes:**
- Line 96: `triggerCalibration` → `triggerWaveformCalibration`
- Line 112: Comment "calibration pulse" → "waveform calibration"
- Line 113: `triggerCalibration` → `triggerWaveformCalibration`
- Line 117: `_triggerDeviceCalibration` → `_triggerWaveformCalibration`
- Line 118: Log message "Calibration triggered" → "Waveform calibration triggered"
- Line 120: Log message "Could not trigger calibration" → "Could not trigger waveform calibration"
- Line 243: Comment "CALIBRATION HELPERS" → "WAVEFORM CALIBRATION HELPERS"
- Line 261: Function name `_triggerDeviceCalibration` → `_triggerWaveformCalibration`
- Line 262: Comment "calibration command" → "waveform calibration command"
- Line 267: `'command': 'calibrate'` → `'command': 'waveformCalibrate'`
- Line 276: Log message "Calibration command sent" → "Waveform calibration command sent"

---

### 2. Frontend - WebSocket Service
**File:** `hospital-display-app/src/services/WebSocketService.ts`

**Changes:**
- Line 163: Parameter `triggerCalibration?: boolean` → `triggerWaveformCalibration?: boolean`
- Line 176: Parameter `triggerCalibration?: boolean` → `triggerWaveformCalibration?: boolean`
- Line 177: Variable `triggerCalibration` → `triggerWaveformCalibration`
- Line 179: Function `requestCalibration` → `requestWaveformCalibration`
- Line 222: Parameter `triggerCalibration?: boolean` → `triggerWaveformCalibration?: boolean`
- Line 236: Property `triggerCalibration` → `triggerWaveformCalibration`
- Line 240: Log message "calibration trigger" → "waveform calibration trigger"
- Line 244: Comment "Request calibration pulse" → "Request waveform calibration"
- Line 246: Function `requestCalibration` → `requestWaveformCalibration`
- Line 248: Log message "Cannot request calibration" → "Cannot request waveform calibration"
- Line 255: Property `triggerCalibration` → `triggerWaveformCalibration`
- Line 259: Log message "Calibration requested" → "Waveform calibration requested"

---

### 3. Frontend - useECGViewer Hook
**File:** `hospital-display-app/src/hooks/useECGViewer.ts`

**Changes:**
- Line 317: Comment "triggerCalibration=true for calibration pulse" → "triggerWaveformCalibration=true for waveform calibration"
- Line 317: Parameter `true` → remains `true` (but parameter name changes in WebSocketService)

---

### 4. ESP32 - Main Firmware
**File:** `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`

**Changes:**
- Line 226: `calibrationDue` → `waveformCalibrationDue`
- Line 941: Function name `handleCalibrationCommand` → `handleWaveformCalibrationCommand`
- Line 942: Log "Calibration command received" → "Waveform calibration command received"
- Line 944: Comment "calibration pulse" → "waveform calibration"
- Line 959: Topic `calibration_complete` → `waveform_calibration_complete`
- Line 969: Variable `calibrationDue` → `waveformCalibrationDue`
- Line 970: Message "Calibration pulse sent" → "Waveform calibration sent"
- Line 972: Log "Calibration pulse complete" → "Waveform calibration complete"
- Line 1696: Command check `"calibrate"` → `"waveformCalibrate"`
- Line 1697: Function call `handleCalibrationCommand` → `handleWaveformCalibrationCommand`

---

### 5. ESP32 - Simulator
**File:** `esp32_hospital_watch_complete/PhysiologicalSimulator.h`
**File:** `esp32_hospital_watch_complete/PhysiologicalSimulator.cpp`

**Changes:**
- Function `startCalibrationPulse()` → Keep as is (it's the actual implementation, "pulse" is accurate)
- Just update comments if they say "calibration" alone

---

## Order of Changes

1. **Backend** - Change function names and parameters
2. **Frontend** - Change function names and parameters
3. **ESP32** - Change command type and handlers
4. **Test** - Verify everything works

## Testing Plan

After renaming:
1. Open ECG viewer
2. Check frontend logs: Should see "🔧 Waveform calibration requested"
3. Check backend logs: Should see "🔧 Waveform calibration triggered"
4. Check ESP32 serial: Should see "🔧 Waveform calibration command received"
5. Verify 1mV square wave appears on waveforms

## Benefits

- **Clarity:** No confusion with device calibration (hardware)
- **Maintainability:** Easier to understand what the code does
- **Searchability:** Can grep for "waveformCalibration" vs "device calibration"
- **Documentation:** Self-documenting code
