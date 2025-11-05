# ESP32 v5.2.12 - Flash Instructions

## What This Version Fixes

**CRITICAL BUGFIX: Simulator mode now updates dynamically when GPIO pin changes**

### The Bug:
- Simulator mode was only set once at boot
- Changing GPIO 4 (ECG↔EEG cable swap) changed message "mode" field but not actual waveforms
- Frontend showed correct mode label but displayed wrong waveform type

### The Fix:
- Lines 1124-1125: Check GPIO 4 every 1 second and update simulator mode before generating new samples
- Mode switching now works in real-time without rebooting
- Waveforms always match the current GPIO pin state

### Changes:
```cpp
// OLD (v5.2.11 and earlier):
void setup() {
  simulator.setMode(...);  // ❌ Only set once at boot
}

// NEW (v5.2.12):
void loop() {
  bool currentMode = digitalRead(MODE_SELECT_PIN) == HIGH;
  simulator.setMode(currentMode ? MODE_ECG : MODE_EEG);  // ✅ Updates every 1s
  simulator.update();
}
```

## Flash Instructions

### 1. Open Arduino IDE
- File → Open → `esp32_hospital_watch_complete.ino`

### 2. Verify Code Compiles
- Click ✓ (Verify) button
- Check for compilation errors
- Should show: "Done compiling"

### 3. Connect ESP32
- Connect ESP32 via USB cable
- Select correct COM port: Tools → Port → COMx
- Select board: Tools → Board → ESP32 Dev Module

### 4. Flash Firmware
- Click → (Upload) button
- Wait for upload to complete
- Should show: "Hard resetting via RTS pin..."

### 5. Monitor Serial Output
- Open Serial Monitor: Tools → Serial Monitor
- Set baud rate: 115200
- Watch for boot messages

### 6. Test Mode Switching

#### Test 1: Boot in ECG Mode
1. Disconnect GPIO 4 (leave floating or pull HIGH)
2. Press RESET button on ESP32
3. Serial should show: "🔌 GPIO 4 configured for mode selection"
4. Wait 10 seconds for first waveform stream
5. Check frontend - should show ECG waveforms (Lead I, II, III, V1-V5)

#### Test 2: Switch to EEG Mode (No Reboot)
1. Connect GPIO 4 to GND (pull LOW)
2. Wait 1-2 seconds (next vitals cycle)
3. Frontend should switch to EEG waveforms (Fp1, Fp2, F3, F4, C3, C4, O1, O2)
4. No reboot needed!

#### Test 3: Switch Back to ECG Mode (No Reboot)
1. Disconnect GPIO 4 from GND (pull HIGH)
2. Wait 1-2 seconds (next vitals cycle)
3. Frontend should switch back to ECG waveforms
4. No reboot needed!

#### Expected Serial Output:
```
🔌 GPIO 4 configured for mode selection
✅ Simulator mode: ECG (GPIO 4 = HIGH)
💓 MQTT Vitals sent (mode: ecg)
📊 MQTT Waveform sent (mode: ecg, 50 samples)

[Change GPIO 4 to LOW]

✅ Simulator mode: EEG (GPIO 4 = LOW)
💓 MQTT Vitals sent (mode: eeg)
📊 MQTT Waveform sent (mode: eeg, 50 samples)
```

## Verification

### On ESP32:
- Serial monitor shows mode changes
- No reboot needed to switch modes
- Simulator updates within 1-2 seconds

### On Frontend:
- Mode label switches correctly (ECG ↔ EEG)
- Waveform shapes match the mode label
- ECG shows PQRST complexes, EEG shows alpha/beta waves
- No more mismatched mode labels and waveforms!

## Rollback Plan

If v5.2.12 causes issues:
1. Use git to revert: `git checkout HEAD~1 esp32_hospital_watch_complete/`
2. Reflash previous version (v5.2.11)
3. Report issue to development team

## Version Info
- **Version:** 5.2.12
- **Date:** 2025-01-04
- **Fix:** Simulator mode dynamic switching
- **Files Changed:** `esp32_hospital_watch_complete.ino` (lines 1124-1125, 74-77)
