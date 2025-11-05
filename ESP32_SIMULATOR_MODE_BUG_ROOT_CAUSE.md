# ESP32 Simulator Mode Bug - Root Cause Found

## Your Question
> "or the fuq, is it hardcoded to just make eeg in watch code now?"

## The Actual Bug

**YES - The ESP32 simulator mode is effectively "hardcoded" at boot time and never changes.**

## Root Cause Analysis

### What's Happening:

1. **Setup (Line 1068):**
   ```cpp
   bool initialECGMode = (digitalRead(MODE_SELECT_PIN) == HIGH);
   simulator.setMode(initialECGMode ? PhysiologicalSimulator::MODE_ECG : PhysiologicalSimulator::MODE_EEG);
   ```
   - Simulator mode is set **ONCE** based on GPIO 4 state at boot
   - Never checked again

2. **Loop (Line 1120):**
   ```cpp
   simulator.update();
   ```
   - Generates waveforms based on mode set at boot
   - **Never updates mode**

3. **Sending Messages (Lines 1872, 1987):**
   ```cpp
   bool isECGMode = digitalRead(MODE_SELECT_PIN);
   ```
   - Reads **current** GPIO 4 state
   - Sends "mode": "ecg" or "mode": "eeg" based on current GPIO

### The Problem:

**Simulator mode and message mode are out of sync:**

| Boot State | Simulator Generates | Change GPIO | Message Says | Result |
|------------|-------------------|-------------|--------------|---------|
| GPIO HIGH | ECG waveforms | GPIO LOW | "mode": "eeg" | ❌ EEG label, ECG data |
| GPIO LOW | EEG waveforms | GPIO HIGH | "mode": "ecg" | ❌ ECG label, EEG data |

### Why Frontend Shows Wrong Data:

1. ESP32 boots with GPIO 4 in some state (let's say LOW)
2. Simulator set to EEG mode forever
3. User changes GPIO 4 to HIGH
4. Messages say `"mode": "ecg"` (reading current GPIO)
5. But simulator still calls `generateEEGSample()` (stuck in EEG mode)
6. Frontend receives: `"mode": "ecg"` with EEG waveform data
7. Frontend shows "ECG" label but displays EEG waveforms

## The Fix

**Check GPIO pin every loop iteration and update simulator mode:**

```cpp
void loop() {
  unsigned long currentMillis = millis();

  // Check if mode changed
  bool currentECGMode = (digitalRead(MODE_SELECT_PIN) == HIGH);
  simulator.setMode(currentECGMode ? PhysiologicalSimulator::MODE_ECG : PhysiologicalSimulator::MODE_EEG);

  if (simulator.shouldUpdate(currentMillis)) {
    simulator.update();
  }
  // ... rest of loop
}
```

### Why This Works:

- Reads GPIO 4 state every loop iteration
- Updates simulator mode before generating new samples
- Simulator and messages now always in sync
- Mode switching works in real-time

## Testing:

1. Flash ESP32 with fix
2. Boot with GPIO 4 HIGH → Should see ECG waveforms
3. Change GPIO 4 to LOW → Should immediately switch to EEG waveforms
4. Change GPIO 4 to HIGH → Should immediately switch back to ECG waveforms

## Summary:

**You were right to be suspicious!** The ESP32 was indeed stuck in whatever mode it booted up with. The simulator mode was only set once at boot and never updated, even though messages claimed the mode was changing based on GPIO pin state.

This is why you saw mismatched data - the message "mode" field and the actual waveform data were coming from different sources (GPIO pin read vs. simulator state).

**Fix: Check GPIO pin every loop and update simulator mode dynamically.**
