# EEG Timing Bug - ROOT CAUSE FOUND

**Date:** 2025-11-04
**Issue:** EEG waveforms look compressed (too fast, noisy)
**Root Cause:** Phase increments 8× per sample (once per channel instead of once per sample)
**Status:** 🔴 CRITICAL BUG - Needs immediate fix

---

## User's Question

> "they look compressed. bloody compressed. so check how the data is generated? is there 2ms thing after generating each lead? Or 2ms once after generating all leads?"

**Answer:** ❌ **2ms thing happens AFTER EACH LEAD (8 times)** when it should happen **ONCE after all leads!**

---

## The Bug - Exact Location

### File: [PhysiologicalSimulator.cpp:536-545](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L536-L545)

```cpp
void PhysiologicalSimulator::generateEEGSample(int channel, int32_t& sample) {
    // Generate EEG waveform with realistic frequency band mixing
    // EEG amplitude typically 20-100 μV (much smaller than ECG)

    // ❌ BUG: Update phase trackers for each frequency band (500 Hz = 2ms per sample)
    float timeStep = 0.002;  // 2ms in seconds
    alphaPhase += 10.5 * timeStep;   // ← INCREMENTS ON EVERY CALL
    betaPhase += 20.0 * timeStep;    // ← INCREMENTS ON EVERY CALL
    thetaPhase += 6.0 * timeStep;    // ← INCREMENTS ON EVERY CALL
    deltaPhase += 2.0 * timeStep;    // ← INCREMENTS ON EVERY CALL
```

### File: [PhysiologicalSimulator.cpp:493-498](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L493-L498)

```cpp
} else {
    // EEG: Generate samples for all channels
    for (int channel = 0; channel < 8; channel++) {
        generateEEGSample(channel, buffer[channel][i]);  // ← CALLED 8 TIMES!
    }
}
```

### Execution Flow:

```
Sample 0:
  generateEEGSample(0, buffer[0][0]) → alphaPhase += 0.021  (alphaPhase = 0.021)
  generateEEGSample(1, buffer[1][0]) → alphaPhase += 0.021  (alphaPhase = 0.042)
  generateEEGSample(2, buffer[2][0]) → alphaPhase += 0.021  (alphaPhase = 0.063)
  generateEEGSample(3, buffer[3][0]) → alphaPhase += 0.021  (alphaPhase = 0.084)
  generateEEGSample(4, buffer[4][0]) → alphaPhase += 0.021  (alphaPhase = 0.105)
  generateEEGSample(5, buffer[5][0]) → alphaPhase += 0.021  (alphaPhase = 0.126)
  generateEEGSample(6, buffer[6][0]) → alphaPhase += 0.021  (alphaPhase = 0.147)
  generateEEGSample(7, buffer[7][0]) → alphaPhase += 0.021  (alphaPhase = 0.168)
                                        ↑ 8× TOO FAST!
```

**Result:** Phase advances **8× faster** than it should!

---

## Mathematical Proof

### Expected Timing (Correct):

```
Alpha frequency: 10.5 Hz
Time per sample: 2ms = 0.002s
Phase increment per sample: 10.5 Hz × 0.002s = 0.021 cycles

Period (samples per cycle): 1 / 0.021 = 47.6 samples
Period (time per cycle): 47.6 × 2ms = 95.2ms ✅ CORRECT (10.5 Hz)
```

### Actual Timing (Bug):

```
Phase increment per sample: 0.021 × 8 channels = 0.168 cycles

Period (samples per cycle): 1 / 0.168 = 5.95 samples
Period (time per cycle): 5.95 × 2ms = 11.9ms ❌ WRONG!

Actual frequency: 1000ms / 11.9ms = 84 Hz ❌ 8× TOO FAST!
```

### Visual Comparison:

**Expected (10.5 Hz alpha):**
```
   /‾‾\    /‾‾\    /‾‾\    /‾‾\    /‾‾\    /‾‾\    /‾‾\
  /    \  /    \  /    \  /    \  /    \  /    \  /    \
 /      \/      \/      \/      \/      \/      \/      \
<--95ms--> <--95ms--> <--95ms-->
Smooth, visible oscillations
```

**Actual (84 Hz - 8× compressed):**
```
∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿
<12ms> <12ms> <12ms> <12ms>
Looks like noise/compressed horizontal lines
```

---

## Comparison to ECG (Which Works Correctly)

### ECG Code (CORRECT):

**File: [PhysiologicalSimulator.cpp:477-492](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L477-L492)**

```cpp
for (int i = 0; i < 10; i++) {
    if (currentMode == MODE_ECG) {
        // ECG: Calculate cardiac cycle phase for this sample
        float cycleDuration = 60000.0 / currentHeartRate;
        float phase = ecgCycleTime / cycleDuration;

        // Generate all 8 leads with same phase
        for (int lead = 0; lead < 8; lead++) {
            generateECGSampleWithPhase(lead, phase, buffer[lead][i]);  // ← Phase passed as parameter
        }

        // ✅ Increment time ONCE per sample (not per lead)
        ecgCycleTime += 2.0;  // ← OUTSIDE THE LEAD LOOP!
        if (ecgCycleTime >= cycleDuration) {
            ecgCycleTime = 0.0;
        }
    }
}
```

**Key Differences:**

| Aspect | ECG (Correct) | EEG (Broken) |
|--------|---------------|--------------|
| Phase calculation | Outside lead loop | Inside channel loop ❌ |
| Phase increment | ONCE per sample ✅ | 8× per sample ❌ |
| Result | Correct timing ✅ | 8× too fast ❌ |

---

## The Fix - Two Steps

### Step 1: Move Phase Updates Outside Channel Loop

**Location: [PhysiologicalSimulator.cpp:493-499](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L493-L499)**

**BEFORE (Broken):**
```cpp
} else {
    // EEG: Generate samples for all channels
    for (int channel = 0; channel < 8; channel++) {
        generateEEGSample(channel, buffer[channel][i]);  // ← Increments phase 8 times
    }
}
```

**AFTER (Fixed):**
```cpp
} else {
    // EEG: Generate samples for all channels
    for (int channel = 0; channel < 8; channel++) {
        generateEEGSampleWithPhase(channel, buffer[channel][i]);  // ← Use new method (no phase update)
    }

    // ✅ Increment phase ONCE per sample (not per channel)
    float timeStep = 0.002;  // 2ms in seconds
    alphaPhase += 10.5 * timeStep;   // 10.5 Hz (alpha)
    betaPhase += 20.0 * timeStep;    // 20 Hz (beta)
    thetaPhase += 6.0 * timeStep;    // 6 Hz (theta)
    deltaPhase += 2.0 * timeStep;    // 2 Hz (delta)
    eegPhase += timeStep;
    if (eegPhase > 1.0) eegPhase -= 1.0;
}
```

### Step 2: Create New Method (Like ECG)

**Location: [PhysiologicalSimulator.cpp](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp) - Add new method**

```cpp
// ✅ NEW: Generate EEG sample WITHOUT updating phase (phase is managed externally)
void PhysiologicalSimulator::generateEEGSampleWithPhase(int channel, int32_t& sample) {
    // Generate waveform based on activity state and channel
    float amplitude = generateEEGWaveform(eegPhase, channel);

    // ✅ NEW: Calculate representative EEG amplitude for dashboard display
    static int eegSampleCount = 0;
    static float eegAmplitudeSum = 0.0;

    eegAmplitudeSum += abs(amplitude);
    eegSampleCount++;

    if (eegSampleCount >= 50) {
        recentEEGAmplitude = eegAmplitudeSum / 50.0;
        eegAmplitudeSum = 0.0;
        eegSampleCount = 0;
    }

    // Convert to 24-bit ADC units
    sample = 8388608 + (int32_t)(amplitude * 1000);

    // Add realistic noise (~2 μV RMS)
    sample += random(-20, 21);

    // ✅ NOTE: Phase is updated by fillSampleBuffer(), NOT here
}
```

### Step 3: Update Header File

**Location: [PhysiologicalSimulator.h](esp32_hospital_watch_complete/PhysiologicalSimulator.h) - Add declaration**

```cpp
void generateEEGSampleWithPhase(int channel, int32_t& sample);
```

---

## Expected Results After Fix

### Timing:

**Before Fix:**
- Alpha: 84 Hz (8× too fast) ❌
- Beta: 160 Hz (8× too fast) ❌
- Theta: 48 Hz (8× too fast) ❌
- Delta: 16 Hz (8× too fast) ❌

**After Fix:**
- Alpha: 10.5 Hz ✅ Correct
- Beta: 20 Hz ✅ Correct
- Theta: 6 Hz ✅ Correct
- Delta: 2 Hz ✅ Correct

### Visual Appearance:

**Before Fix (Compressed):**
```
∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿  (looks like noise)
```

**After Fix (Smooth):**
```
   /‾‾\    /‾‾\    /‾‾\    /‾‾\    /‾‾\    /‾‾\
  /    \  /    \  /    \  /    \  /    \  /    \
 /      \/      \/      \/      \/      \/      \
(smooth, visible alpha waves)
```

### O1/O2 Channels:

**Before Both Fixes:**
- O1: Flat line (buffer index bug) ❌
- O2: Flat line (buffer index bug) ❌

**After Buffer Index Fix Only (Current State):**
- O1: Compressed noisy waveform (timing bug) ⚠️
- O2: Compressed noisy waveform (timing bug) ⚠️

**After Both Fixes:**
- O1: Smooth alpha waves (15% stronger) ✅
- O2: Smooth alpha waves (15% stronger) ✅

---

## Why This Bug Existed

### Historical Context:

1. **ECG code was fixed first** (v5.2.8) - moved phase increment outside lead loop
2. **EEG code was copied from older version** - never got the same fix
3. **Different function signature** - ECG uses `generateECGSampleWithPhase(lead, phase, sample)`, EEG uses `generateEEGSample(channel, sample)` (no phase parameter)
4. **No phase parameter** = phase must be managed internally = increments on every call

### The Pattern:

**ECG (Fixed v5.2.8):**
```cpp
// Phase calculated ONCE per sample
float phase = ecgCycleTime / cycleDuration;

// All leads use SAME phase
for (int lead = 0; lead < 8; lead++) {
    generateECGSampleWithPhase(lead, phase, buffer[lead][i]);
}

// Phase incremented ONCE per sample
ecgCycleTime += 2.0;
```

**EEG (Still Broken):**
```cpp
// No phase parameter
for (int channel = 0; channel < 8; channel++) {
    generateEEGSample(channel, buffer[channel][i]);  // ← Increments phase internally
}
```

---

## Priority

**CRITICAL** - This makes all EEG waveforms unusable for clinical interpretation.

**Impact:**
- ❌ Alpha waves look like noise
- ❌ Cannot assess visual cortex function (O1/O2)
- ❌ Cannot determine sleep state
- ❌ Cannot detect cognitive changes
- ❌ Waveforms 8× too fast = medically meaningless

---

## Testing Plan

1. **Flash ESP32** with fixed firmware
2. **Switch to EEG mode** (GPIO 4 LOW)
3. **Check console logs** - alpha frequency should match 10.5 Hz
4. **Visual inspection** - O1/O2 should show smooth oscillations, not noise
5. **Compare to ECG** - Both should have clean, smooth waveforms

---

**Status:** Ready to implement fix

**Files to modify:**
1. `PhysiologicalSimulator.cpp` - Move phase updates, add new method
2. `PhysiologicalSimulator.h` - Add method declaration

**Estimated fix time:** 5 minutes
**Testing time:** 2 minutes (ESP32 reflash + visual check)

---

**END OF ROOT CAUSE ANALYSIS**
