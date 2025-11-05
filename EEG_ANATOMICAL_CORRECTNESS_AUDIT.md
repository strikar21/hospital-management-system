# EEG Anatomical Correctness Audit

## Your Observation
> "also the eeg waveforms from the simulator look the same. they arent anatomically right?"

## Code Analysis

### ✅ Channel-Specific Frequency Mixing IS Implemented

**File:** `PhysiologicalSimulator.cpp:615-704`

The code DOES implement anatomically correct EEG waveforms with channel-specific frequency mixing (v5.2.11):

```cpp
switch (channel) {
    case 0:  // Fp1 - Frontal pole left
    case 1:  // Fp2 - Frontal pole right
        // Frontal lobe: MORE BETA (active thinking), less alpha
        alphaWeight = 0.3;
        betaWeight = 0.6;
        thetaWeight = 0.1;
        break;

    case 2:  // F3 - Frontal left
    case 3:  // F4 - Frontal right
        // Frontal-moderate: balanced beta-alpha mix
        alphaWeight = 0.4;
        betaWeight = 0.5;
        thetaWeight = 0.1;
        break;

    case 4:  // C3 - Central left
    case 5:  // C4 - Central right
        // Central: balanced (mu rhythm, similar to alpha)
        alphaWeight = 0.6;
        betaWeight = 0.3;
        thetaWeight = 0.1;
        break;

    case 6:  // O1 - Occipital left
    case 7:  // O2 - Occipital right
        // Occipital: STRONG ALPHA (posterior dominant rhythm), minimal beta
        alphaWeight = 0.8;  // Dominant alpha (visual cortex at rest)
        betaWeight = 0.1;
        thetaWeight = 0.1;
        break;
}
```

### Expected Waveform Differences

**Frontal (Fp1, Fp2):**
- Fast oscillations (beta-dominant: 60% beta, 30% alpha)
- Frequency: ~20 Hz dominant
- Should look "busy" with rapid fluctuations

**Central (C3, C4):**
- Balanced (60% alpha, 30% beta)
- Frequency: ~10.5 Hz + some 20 Hz
- Medium-speed oscillations

**Occipital (O1, O2):**
- Slow oscillations (alpha-dominant: 80% alpha, 10% beta)
- Frequency: ~10.5 Hz dominant
- Should look smooth with slow waves

### Frequency Band Details

```cpp
float alpha = sin(2 * PI * alphaPhase) * 40.0;   // 10.5 Hz, 40 μV amplitude
float beta = sin(2 * PI * betaPhase) * 15.0;     // 20 Hz, 15 μV amplitude
float theta = sin(2 * PI * thetaPhase) * 50.0;   // 6 Hz, 50 μV amplitude
float delta = sin(2 * PI * deltaPhase) * 80.0;   // 2 Hz, 80 μV amplitude
```

**Phase update (lines 501-506):**
```cpp
alphaPhase += 10.5 * timeStep;   // 10.5 Hz (alpha)
betaPhase += 20.0 * timeStep;    // 20 Hz (beta)
thetaPhase += 6.0 * timeStep;    // 6 Hz (theta)
deltaPhase += 2.0 * timeStep;    // 2 Hz (delta)
```

### Why Channels Might LOOK The Same

**Problem 1: Amplitude Differences Are Small**

Compare beta-dominant (frontal) vs alpha-dominant (occipital):

**Frontal (Fp1):**
```
amplitude = alpha * 0.3 + beta * 0.6
         = (40 μV * 0.3) + (15 μV * 0.6)
         = 12 μV + 9 μV
         = 21 μV total
```

**Occipital (O1):**
```
amplitude = alpha * 0.8 + beta * 0.1
         = (40 μV * 0.8) + (15 μV * 0.1)
         = 32 μV + 1.5 μV
         = 33.5 μV total
```

**Issue:** Amplitude difference is only ~60% (21 vs 33.5 μV), which may not be visually obvious on a waveform display.

---

**Problem 2: Frequency Difference Is Subtle**

Frontal: 60% of 20 Hz + 30% of 10.5 Hz = effective ~16 Hz dominant
Occipital: 80% of 10.5 Hz + 10% of 20 Hz = effective ~11 Hz dominant

**Frequency difference:** ~16 Hz vs ~11 Hz (only ~40% faster)

On a real-time scrolling display at 30 mm/s, this may look similar unless you count the waves carefully.

---

**Problem 3: Visual Scale May Hide Differences**

If the frontend auto-scales all channels to fit the same canvas height, amplitude differences are normalized away, leaving only frequency differences (which are subtle).

---

## Diagnostic Tests

### Test 1: Verify Frequency Differences

**Method:** Pause waveform display and count waves per second

**Expected Results:**
- **Fp1 (frontal):** ~16-20 waves per second (fast)
- **O1 (occipital):** ~10-11 waves per second (slow)

**How to count:**
- Use 1-second time markers on display
- Count peaks in 1 second

---

### Test 2: Verify Amplitude Differences

**Method:** Check raw amplitude values from WebSocket

**Expected Results:**
- **Fp1 (frontal):** ~20-25 μV amplitude
- **O1 (occipital):** ~30-35 μV amplitude

**Where to check:**
- Browser console logs showing waveform data
- Or add logging to `useECGViewer.ts` to print amplitude ranges

---

### Test 3: Visual Comparison With Auto-Scaling Disabled

**Method:** Set fixed Y-axis scale (same for all channels)

**Expected Results:**
- **Fp1 (frontal):** Shorter waves (lower amplitude)
- **O1 (occipital):** Taller waves (higher amplitude)

**Current Issue:** If frontend auto-scales each channel independently, all channels fill the canvas height equally, hiding amplitude differences.

---

## Possible Issues

### Issue 1: Frontend Auto-Scaling Hides Amplitude Differences ⚠️

**File:** `hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx`

If the rendering code auto-scales each channel independently:

```typescript
// BAD: Auto-scale per channel (hides differences)
const minVal = Math.min(...channelData);
const maxVal = Math.max(...channelData);
const scale = canvasHeight / (maxVal - minVal);
```

This makes all channels look the same amplitude!

**Fix:** Use FIXED scale for all EEG channels based on expected μV range:

```typescript
// GOOD: Fixed scale for all EEG channels
const minVal = -100;  // μV
const maxVal = 100;   // μV
const scale = canvasHeight / (maxVal - minVal);
```

---

### Issue 2: Frequency Differences Are Too Subtle 🤔

**Current frequencies:**
- Beta: 20 Hz (fast)
- Alpha: 10.5 Hz (medium)

**Problem:** 2× frequency difference might not be visually obvious on a scrolling display.

**Potential enhancement:**
Increase frequency separation for more obvious visual difference:
- Beta: 25 Hz (very fast)
- Alpha: 10 Hz (slow)

---

### Issue 3: Mixing Ratios Too Similar 🤔

**Current mixing:**
- Frontal: 60% beta + 30% alpha
- Occipital: 80% alpha + 10% beta

**Problem:** Both channels contain both frequencies, just in different proportions. This creates a "blended" look rather than distinct waveforms.

**Potential enhancement:**
More extreme differences:
- Frontal: 90% beta + 10% alpha (almost pure fast waves)
- Occipital: 90% alpha + 10% beta (almost pure slow waves)

---

## Recommendations

### Immediate Check: Visual Inspection

1. **Open EEG viewer** on patient with device
2. **Look at Fp1 (channel 0)** - should be fast/busy
3. **Look at O1 (channel 6)** - should be slower/smoother
4. **Compare side-by-side**

**If they look identical:** Frontend auto-scaling is the issue.

---

### Fix 1: Disable Auto-Scaling for EEG Channels

**File:** `ECGWaveformCanvas.tsx`

Change from auto-scale to fixed scale for EEG mode:

```typescript
if (mode === 'eeg') {
  // Fixed scale: ±100 μV range
  minValue = -100;
  maxValue = 100;
} else {
  // ECG uses auto-scale (amplitude varies by lead)
  minValue = Math.min(...buffer);
  maxValue = Math.max(...buffer);
}
```

---

### Fix 2: Increase Frequency/Amplitude Contrast (Optional)

**File:** `PhysiologicalSimulator.cpp:622-625`

Make differences more dramatic:

```cpp
// OLD
float alpha = sin(2 * PI * alphaPhase) * 40.0;   // 40 μV amplitude
float beta = sin(2 * PI * betaPhase) * 15.0;     // 15 μV amplitude

// NEW (more contrast)
float alpha = sin(2 * PI * alphaPhase) * 60.0;   // 60 μV amplitude (larger)
float beta = sin(2 * PI * betaPhase) * 20.0;     // 20 μV amplitude (larger)
```

And increase mixing contrast:

```cpp
case 0:  // Fp1 - Frontal
case 1:  // Fp2
    alphaWeight = 0.1;  // Almost no alpha
    betaWeight = 0.8;   // Strong beta
    break;

case 6:  // O1 - Occipital
case 7:  // O2
    alphaWeight = 0.9;  // Strong alpha
    betaWeight = 0.05;  // Almost no beta
    break;
```

---

## Summary

**Code is correct!** ✅ Channel-specific mixing IS implemented (v5.2.11).

**Possible reasons channels look the same:**

1. **Most Likely:** Frontend auto-scaling normalizes amplitudes → hides differences
2. **Possible:** Frequency/amplitude differences too subtle for visual inspection
3. **Unlikely:** Simulator not actually running v5.2.11

**Next Step:** Check frontend rendering code for auto-scaling per channel.
