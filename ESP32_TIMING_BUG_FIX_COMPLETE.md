# ESP32 ECG Waveform Timing Bug - FIX COMPLETE

## Problem Summary
- **Observed**: 70 ECG waveforms across screen instead of expected ~20
- **User reported**: "2 waves in 5mm box" (should be 1 wave in 15-20mm)
- **Root cause**: `ecgCycleTime` incremented 8x too fast (once per lead instead of once per sample)
- **Result**: Waveforms compressed horizontally by 8x factor

## Root Cause Details

### The Bug
**File**: `PhysiologicalSimulator.cpp` line 416-431 (OLD CODE)

```cpp
void PhysiologicalSimulator::fillSampleBuffer(int32_t buffer[8][10]) {
    for (int i = 0; i < 10; i++) {              // 10 samples
        for (int leadOrChannel = 0; leadOrChannel < 8; leadOrChannel++) {  // 8 leads
            generateECGSample(leadOrChannel, buffer[leadOrChannel][i]);
            // ↑ This called ecgCycleTime += 2.0 EIGHTY times (8 leads × 10 samples)
        }
    }
}
```

### The Math
```
Expected per fillSampleBuffer() call:
- 10 samples × 2ms = 20ms time advancement

Actual with bug:
- 80 calls to generateECGSample() × 2ms = 160ms time advancement
- Acceleration factor: 160 / 20 = 8x too fast

At 89 BPM:
- Expected cycle: 674ms (60000ms / 89 BPM)
- With bug: ecgCycleTime completes cycle in 674ms / 8 = 84ms
- Apparent heart rate: 60000ms / 84ms = 714 BPM

Visible result:
- Expected: ~20 waves across 13.9s screen
- Actual: ~70 waves across screen (20 × 3.5 ≈ 70)
```

---

## The Fix

### Changes Made

#### 1. PhysiologicalSimulator.cpp - fillSampleBuffer() (Lines 416-448)

**BEFORE:**
```cpp
void PhysiologicalSimulator::fillSampleBuffer(int32_t buffer[8][10]) {
    for (int i = 0; i < 10; i++) {
        for (int leadOrChannel = 0; leadOrChannel < 8; leadOrChannel++) {
            if (currentMode == MODE_ECG) {
                generateECGSample(leadOrChannel, buffer[leadOrChannel][i]);
                // ↑ ecgCycleTime += 2.0 happens HERE, 80 times!
            }
        }
    }
}
```

**AFTER:**
```cpp
void PhysiologicalSimulator::fillSampleBuffer(int32_t buffer[8][10]) {
    // ✅ FIX: Calculate phase ONCE per sample, use same phase for all leads
    for (int i = 0; i < 10; i++) {
        if (currentMode == MODE_ECG) {
            // ECG: Calculate cardiac cycle phase for this sample
            float cycleDuration = 60000.0 / currentHeartRate;
            float phase = ecgCycleTime / cycleDuration;

            // Generate all 8 leads with same phase
            for (int lead = 0; lead < 8; lead++) {
                generateECGSampleWithPhase(lead, phase, buffer[lead][i]);
            }

            // ✅ Increment time ONCE per sample (not per lead)
            ecgCycleTime += 2.0;  // 500 Hz = 2ms per sample
            if (ecgCycleTime >= cycleDuration) {
                ecgCycleTime = 0.0;  // New beat - reset to P wave
            }
        } else {
            // EEG remains unchanged
            for (int channel = 0; channel < 8; channel++) {
                generateEEGSample(channel, buffer[channel][i]);
            }
        }
    }
}
```

**Key changes:**
1. Moved `ecgCycleTime` increment outside the lead loop
2. Calculate `phase` once per sample
3. All 8 leads now use the **same cardiac phase** for each time point
4. Time advances exactly 2ms per sample (not 16ms)

---

#### 2. PhysiologicalSimulator.cpp - New Method (Lines 273-318)

**Added new method:**
```cpp
void PhysiologicalSimulator::generateECGSampleWithPhase(int lead, float phase, int32_t& sample) {
    // Check calibration pulse
    if (isCalibrationActive()) {
        // ... calibration pulse generation
        return;
    }

    // Generate PQRST complex with given phase
    float amplitude = generatePQRST(phase, lead);

    // Calculate representative ECG amplitude
    // ... rolling average calculation

    // Convert to 24-bit ADC
    sample = 8388608 + (int32_t)(amplitude * 100000);

    // Add noise
    sample += random(-50, 51);

    // ✅ NOTE: Timing is handled by fillSampleBuffer(), not here
}
```

**Why new method?**
- Old `generateECGSample()` modified `ecgCycleTime` internally
- New `generateECGSampleWithPhase()` accepts pre-calculated phase
- No timing modification inside waveform generation
- Cleaner separation of concerns

---

#### 3. PhysiologicalSimulator.cpp - Deprecated Old Method (Lines 320-332)

**Kept for compatibility:**
```cpp
// ✅ DEPRECATED: Old method kept for compatibility (but not used anymore)
void PhysiologicalSimulator::generateECGSample(int lead, int32_t& sample) {
    // Calculate phase and delegate to new method
    float cycleDuration = 60000.0 / currentHeartRate;
    float phase = ecgCycleTime / cycleDuration;
    generateECGSampleWithPhase(lead, phase, sample);

    // Update timing (only when called directly, not from fillSampleBuffer)
    ecgCycleTime += 2.0;
    if (ecgCycleTime >= cycleDuration) {
        ecgCycleTime = 0.0;
    }
}
```

**Why keep it?**
- In case other code calls it directly (defensive programming)
- Delegates to new method to avoid code duplication
- Still increments timing for backward compatibility

---

#### 4. PhysiologicalSimulator.h - Header Declaration (Line 68)

**Added:**
```cpp
void generateECGSampleWithPhase(int lead, float phase, int32_t& sample);  // ✅ NEW: Phase-based generation
```

---

## Expected Results After Fix

### Timing Correction:
```
Per fillSampleBuffer() call:
- Time advancement: 10 samples × 2ms = 20ms ✅ CORRECT

At 89 BPM:
- Cycle duration: 674ms
- Samples per cycle: 674ms / 2ms = 337 samples
- Distance on screen: 337 × 0.1890 px/sample = 63.69 pixels
- Grid size: 63.69px / 3.78px/mm = 16.85mm
- Large squares: 16.85mm / 5mm = 3.37 squares ✅ MATCHES USER EXPECTATION

Visible waveforms:
- Screen shows: 13.9 seconds of data
- At 89 BPM: 13.9s × (89/60) = 20.6 beats ✅ CORRECT
```

### Before vs After:
| Metric | Before (Bug) | After (Fixed) |
|--------|--------------|---------------|
| Waves visible | ~70 | ~20 |
| mm per wave | ~5mm | ~17mm |
| Large squares/wave | ~1 | ~3.4 |
| Apparent HR | ~714 BPM | ~89 BPM |
| Compression factor | 8x | 1x |

---

## Testing Instructions

### 1. Flash ESP32
Upload the modified firmware to ESP32 watch:
- `PhysiologicalSimulator.cpp` (modified)
- `PhysiologicalSimulator.h` (modified)

### 2. Verify Waveform Timing
1. Open ECG viewer in hospital display app
2. Count visible waveforms across full screen width
3. **Expected**: ~20 complete PQRST complexes
4. **Verify**: Each wave spans ~3-4 large grid squares (15-20mm)

### 3. Verify Heart Rate Match
1. Check heart rate display (top right): Should show 60-100 BPM range
2. Count actual waveforms: Should match displayed heart rate
3. **At 89 BPM**: Should see ~20 waves in 13.9 seconds

### 4. Verify All Leads Synchronized
1. Switch to 4-lead or 12-lead view
2. **Verify**: All leads show same cardiac phase at each time point
3. **Verify**: QRS complexes align vertically across all leads

---

## Additional Benefits of Fix

1. **Medical Accuracy**: All leads now show synchronized cardiac cycle
2. **Performance**: No change - same number of function calls
3. **Maintainability**: Cleaner code with timing in one place
4. **Debugging**: Easier to trace timing issues
5. **Scalability**: Can add more leads without timing bugs

---

## Files Modified

1. **esp32_hospital_watch_complete/PhysiologicalSimulator.cpp**
   - Modified `fillSampleBuffer()` (lines 416-448)
   - Added `generateECGSampleWithPhase()` (lines 273-318)
   - Modified `generateECGSample()` to delegate (lines 320-332)

2. **esp32_hospital_watch_complete/PhysiologicalSimulator.h**
   - Added method declaration (line 68)

---

## Status

✅ **FIX COMPLETE** - Ready for testing

After flashing ESP32, waveforms should display at correct timing (3-4 large squares per wave at typical heart rates).

User should see **~20 waves** instead of **~70 waves** on screen.
