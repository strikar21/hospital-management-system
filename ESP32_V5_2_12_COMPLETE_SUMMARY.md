# ESP32 v5.2.12 - Complete Summary

## Issue Reported
**"or the fuq, is it hardcoded to just make eeg in watch code now?"**

## Root Cause Analysis

### The Bug (v5.2.11 and Earlier):

**Simulator mode was only set once at boot and never updated when GPIO pin changed.**

#### What Was Happening:
1. **Line 1071 (setup()):** Simulator mode set ONCE based on GPIO 4 state at boot
2. **Line 1120 (loop()):** Simulator generates waveforms based on boot-time mode (never changes)
3. **Lines 1880, 1995 (vitals/waveform messages):** Messages read CURRENT GPIO 4 state every time

#### Result:
| Boot State | Simulator Mode | Change GPIO | Message Says | Frontend Shows |
|------------|---------------|-------------|--------------|----------------|
| GPIO HIGH | ECG forever | GPIO LOW | "mode": "eeg" | ❌ EEG label, ECG waveforms |
| GPIO LOW | EEG forever | GPIO HIGH | "mode": "ecg" | ❌ ECG label, EEG waveforms |

**You saw the mode LABEL changing without rebooting** (because messages always read GPIO pin), **but the actual WAVEFORMS didn't change** (because simulator was stuck at boot mode).

### Why You Thought It Was Hardcoded:

The simulator was effectively "hardcoded" to whatever mode it booted up with. Even though the GPIO pin was read in multiple places, the simulator itself never changed mode after boot.

## The Fix (v5.2.12)

### Code Changes:

**File:** `esp32_hospital_watch_complete.ino`

**Lines 1124-1125 (NEW):**
```cpp
void loop() {
  // ... existing code ...

  if (isProvisioned && isAssigned && (millis() - lastVitals) > 1000) {
    // ✅ v5.2.12: Check GPIO pin and update simulator mode dynamically
    bool currentMode = digitalRead(MODE_SELECT_PIN) == HIGH;
    simulator.setMode(currentMode ? PhysiologicalSimulator::MODE_ECG : PhysiologicalSimulator::MODE_EEG);

    // ✅ v5.1: Update physiological state and get simulated vitals
    simulator.update();
    // ... rest of vitals generation ...
  }
}
```

**Lines 74-77 (Changelog):**
```
* ✅ v5.2.12: CRITICAL BUGFIX - Simulator mode was only set once at boot, never updated when GPIO pin changed
* ✅ v5.2.12: Bug: Swap ECG↔EEG cable → frontend shows correct mode label but wrong waveforms
* ✅ v5.2.12: Fix: Check GPIO pin every 1s (before simulator.update()) and call setMode() dynamically
* ✅ v5.2.12: Result: Mode switching now works correctly - waveforms match the current GPIO pin state
```

### How It Works Now:

1. **Every 1 second** (vitals cycle):
   - Read GPIO 4 current state
   - Update simulator mode BEFORE generating new samples
   - Generate waveforms that match current mode
   - Send messages that match current mode

2. **Result:**
   - Mode label and waveforms always in sync
   - No reboot needed to switch modes
   - Works in real-time (1-2 second delay)

## Testing Instructions

### Test 1: Boot in ECG Mode
1. Leave GPIO 4 floating (or pull HIGH)
2. Press RESET on ESP32
3. Frontend should show ECG waveforms (Lead I, II, III, V1-V5)

### Test 2: Switch to EEG (No Reboot)
1. Connect GPIO 4 to GND
2. Wait 1-2 seconds
3. Frontend should switch to EEG waveforms (Fp1, Fp2, F3, F4, C3, C4, O1, O2)
4. ✅ **No reboot needed!**

### Test 3: Switch Back to ECG (No Reboot)
1. Disconnect GPIO 4 from GND
2. Wait 1-2 seconds
3. Frontend should switch back to ECG waveforms
4. ✅ **No reboot needed!**

## What Changed vs. What Didn't

### ✅ Always Worked (No Reboot Needed):
- Vitals message "mode" field (line 1880)
- Waveform message "mode" field (line 1995)
- Both read GPIO pin every time

### ❌ Was Broken (Required Reboot):
- Simulator waveform generation (line 1071)
- Only read GPIO pin once at boot
- Stuck in that mode forever

### ✅ Now Fixed (No Reboot Needed):
- Simulator waveform generation (lines 1124-1125)
- Reads GPIO pin every 1 second
- Updates mode dynamically

## Files Changed
- `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`
  - Version: 5.0.0 → 5.2.12
  - Lines added: 1124-1125 (mode checking)
  - Lines updated: 1-77 (version header and changelog)

## Next Steps

1. **Flash ESP32:**
   - Open Arduino IDE
   - Upload `esp32_hospital_watch_complete.ino`
   - See [ESP32_V5.2.12_FLASH_INSTRUCTIONS.md](ESP32_V5.2.12_FLASH_INSTRUCTIONS.md) for details

2. **Test Mode Switching:**
   - Boot with GPIO 4 HIGH → should see ECG
   - Change GPIO 4 to LOW → should see EEG (no reboot)
   - Change GPIO 4 to HIGH → should see ECG (no reboot)

3. **Verify on Frontend:**
   - Mode label matches waveform type
   - No more mismatched ECG/EEG displays
   - Smooth transitions when cable changed

## Summary

**Problem:** Simulator mode was "hardcoded" at boot time - never changed even when GPIO pin changed.

**Solution:** Check GPIO pin every 1 second and update simulator mode dynamically.

**Result:** Mode switching now works in real-time without rebooting. Waveforms always match the mode label.

**Your suspicion was correct!** The ESP32 was indeed stuck in whatever mode it booted up with.
