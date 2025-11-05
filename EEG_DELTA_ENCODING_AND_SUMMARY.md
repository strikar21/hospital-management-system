# EEG Delta Encoding and Audit Summary

## Your Question
> "is eeg also delta encoded?"

## Answer: YES ✅

**File:** `esp32_hospital_watch_complete.ino:2066-2079`

```cpp
// ✅ v5.2.5: EEG mode - Delta encoded with proper capitalization
JsonObject eegWaveform = doc.createNestedObject("eegWaveform");

// Frontal channels (Fp1, Fp2, F3, F4)
JsonObject frontal = eegWaveform.createNestedObject("frontal");
addDeltaEncodedChannel(frontal, "Fp1", waveformAccumulator[0], 50);
addDeltaEncodedChannel(frontal, "Fp2", waveformAccumulator[1], 50);
addDeltaEncodedChannel(frontal, "F3", waveformAccumulator[2], 50);
addDeltaEncodedChannel(frontal, "F4", waveformAccumulator[3], 50);

// Central channels (C3, C4)
JsonObject central = eegWaveform.createNestedObject("central");
addDeltaEncodedChannel(central, "C3", waveformAccumulator[4], 50);
addDeltaEncodedChannel(central, "C4", waveformAccumulator[5], 50);

// Occipital channels (O1, O2)
JsonObject occipital = eegWaveform.createNestedObject("occipital");
addDeltaEncodedChannel(occipital, "O1", waveformAccumulator[6], 50);
addDeltaEncodedChannel(occipital, "O2", waveformAccumulator[7], 50);
```

**Delta encoding function (lines 1958-1965):**
```cpp
void addDeltaEncodedChannel(JsonObject& parent, const char* fieldName, int32_t* samples, int count) {
  JsonObject channel = parent.createNestedObject(fieldName);
  channel["baseline"] = samples[0];  // First sample (full value)
  JsonArray deltas = channel.createNestedArray("deltas");
  for (int i = 1; i < count; i++) {
    deltas.add(samples[i] - samples[i-1]);  // Subsequent samples (differences only)
  }
}
```

### Message Format Example:

```json
{
  "eegWaveform": {
    "frontal": {
      "Fp1": {
        "baseline": 8388608,
        "deltas": [234, -123, 456, ...]  // 49 deltas
      },
      "Fp2": { ... },
      "F3": { ... },
      "F4": { ... }
    },
    "central": {
      "C3": { ... },
      "C4": { ... }
    },
    "occipital": {
      "O1": { ... },
      "O2": { ... }
    }
  }
}
```

### Bandwidth Savings

**Same as ECG:** Delta encoding provides ~51% bandwidth reduction for EEG too.

**Why it works for EEG:**
- EEG waveforms are continuous and smooth
- Sample-to-sample changes are small (~1-50 μV typically)
- Delta values fit in smaller integers than full 24-bit ADC values

---

## EEG Anatomical Correctness Audit Summary

### ✅ Code IS Correct

**Simulator implementation (v5.2.11):**
- Frontal (Fp1, Fp2): 60% beta (fast) + 30% alpha → ~16-20 Hz
- Central (C3, C4): 60% alpha + 30% beta → ~11-13 Hz
- Occipital (O1, O2): 80% alpha (slow) + 10% beta → ~10-11 Hz

**This IS anatomically correct!**

### ⚠️ Why Channels May LOOK The Same

**Most Likely Issue:** Frontend auto-scaling

If the frontend auto-scales each EEG channel independently to fill the canvas:
```typescript
// BAD: Per-channel auto-scale
const minVal = Math.min(...channelData);
const maxVal = Math.max(...channelData);
const scale = canvasHeight / (maxVal - minVal);
```

This normalizes amplitude differences away, making all channels look identical.

**Fix:** Use fixed Y-axis scale for all EEG channels:
```typescript
// GOOD: Fixed scale for all EEG channels
const minVal = -100;  // μV
const maxVal = 100;   // μV
const scale = canvasHeight / (maxVal - minVal);
```

### Visual Comparison Test

**To verify channels are different:**

1. **Look at frontend EEG viewer**
2. **Compare Fp1 (channel 0) vs O1 (channel 6)**
3. **Expected differences:**
   - **Fp1:** Fast/busy waveforms (~16-20 waves/second)
   - **O1:** Slower/smoother waveforms (~10-11 waves/second)

If they look identical → Frontend auto-scaling is hiding the differences.

### Amplitude Comparison

**Expected raw amplitudes:**
- **Fp1 (frontal):** ~20-25 μV
- **O1 (occipital):** ~30-35 μV

Occipital should be ~60% larger amplitude than frontal.

---

## Summary

**Delta Encoding:** ✅ YES - Both ECG and EEG use delta encoding (v5.2.5)

**Anatomical Correctness:** ✅ YES - Code implements channel-specific frequency mixing (v5.2.11)

**Why Channels Look The Same:** ⚠️ **Frontend auto-scaling** likely normalizing amplitudes

**Next Step:** Check frontend rendering code for per-channel auto-scaling

**File to Check:** `hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx`

**Look for:** Auto-scaling logic that uses `Math.min()`/`Math.max()` per channel instead of fixed EEG scale.
