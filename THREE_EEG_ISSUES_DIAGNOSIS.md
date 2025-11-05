# Three EEG Issues - Root Cause Analysis

**Date:** 2025-11-04
**Reported Issues:**
1. Speed control changes label but not waveform spacing
2. Gain control changes label but not waveform amplitude
3. All waveforms look identical (just different colors)

**Status:** 🔴 THREE BUGS CONFIRMED

---

## Issue #1: Speed Control Not Working

### Symptoms:
- User changes speed slider (e.g., 25mm/s → 30mm/s)
- Label updates correctly
- **But waveform horizontal spacing doesn't change**

### Root Cause Analysis:

**File:** [ECGWaveformCanvas.tsx:104-106](hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx#L104-L106)

```typescript
// ✅ MEDICAL-STANDARD HORIZONTAL SCALING: Use actual speed prop (mm/s)
const pixelsPerSecond = mmToPixels(speed); // User-selected speed at detected DPI
const pixelsPerSample = pixelsPerSecond / SAMPLE_RATE_HZ; // speed ÷ 500Hz
const samplesVisible = Math.floor(width / pixelsPerSample);
```

**The calculation looks correct!** Speed is being used properly.

**Let me check if the issue is React dependencies...**

**Checking:** [ECGWaveformCanvas.tsx:54-62](hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx#L54-L62)

```typescript
useEffect(() => {
    let animationFrameId: number;
    const animate = (timestamp: number) => {
      drawWaveform(timestamp);
      if (!isPaused) animationFrameId = requestAnimationFrame(animate);
    };
    if (!isPaused) animationFrameId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrameId);
  }, [isPaused]);  // ← ONLY depends on isPaused!
```

### 🎯 ROOT CAUSE #1: Missing Dependency

**The useEffect doesn't depend on `speed` or `gain`!**

When speed/gain changes:
- Props update ✅
- Label updates ✅
- But **drawWaveform() keeps using OLD values** because useEffect doesn't re-trigger ❌

**The animation loop captures `speed` and `gain` from the initial render and never updates!**

---

## Issue #2: Gain Control Not Working

### Symptoms:
- User changes gain slider (e.g., 7μV/mm → 10μV/mm)
- Label updates correctly
- **But waveform vertical amplitude doesn't change**

### Root Cause:

**SAME BUG as Issue #1** - useEffect doesn't depend on `gain`

**File:** [ECGWaveformCanvas.tsx:116-118](hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx#L116-L118)

```typescript
const pixelsPerUnit = isECGMode
  ? mmToPixels(gain)  // ECG: gain mm/mV → pixels per mV
  : mmToPixels(1 / gain); // EEG: gain μV/mm → pixels per μV
```

**Calculation is correct**, but animation loop never re-reads the new `gain` value.

---

## Issue #3: All Waveforms Look Identical

### Symptoms:
- All 8 EEG channels (Fp1, Fp2, F3, F4, C3, C4, O1, O2) show identical waveforms
- Only difference is color
- Expected: Different brain regions should show different patterns

### Root Cause Analysis:

**File:** [PhysiologicalSimulator.cpp:622-625](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L622-L625)

```cpp
float alpha = sin(2 * PI * alphaPhase) * 40.0;   // 40 μV amplitude
float beta = sin(2 * PI * betaPhase) * 15.0;     // 15 μV amplitude
float theta = sin(2 * PI * thetaPhase) * 50.0;   // 50 μV amplitude
float delta = sin(2 * PI * deltaPhase) * 80.0;   // 80 μV amplitude
```

**ALL CHANNELS USE THE SAME PHASE VARIABLES:**
- `alphaPhase` - shared across all 8 channels
- `betaPhase` - shared across all 8 channels
- `thetaPhase` - shared across all 8 channels
- `deltaPhase` - shared across all 8 channels

**File:** [PhysiologicalSimulator.cpp:656-687](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L656-L687)

```cpp
// Channel-specific variations (simulate different brain regions)
float channelMultiplier = 1.0;
switch (channel) {
    case 0:  // Fp1 - Frontal pole left
        channelMultiplier = 0.85;  // Less alpha, more beta
        break;
    // ... more cases
    case 6:  // O1 - Occipital left
        channelMultiplier = 1.15;  // Strong alpha waves
        break;
}

return mixedSignal * channelMultiplier;  // ← ONLY AMPLITUDE DIFFERENCE!
```

### 🎯 ROOT CAUSE #3: Channel Multiplier Only Affects Amplitude

**What happens:**
1. All channels generate waveform using **SAME phases** (alphaPhase, betaPhase, etc.)
2. All channels get **IDENTICAL waveform shape**
3. Channel multiplier only scales **amplitude** (0.85× to 1.15×)
4. **Result:** All waveforms look identical except slightly different heights

**What SHOULD happen:**
- Frontal channels (Fp1, Fp2, F3, F4) should have **more beta** (faster oscillations)
- Central channels (C3, C4) should have **balanced** mix
- Occipital channels (O1, O2) should have **more alpha** (slower oscillations)

**Current code generates:**
```
Fp1: alpha*0.6 + beta*0.3 + theta*0.1 → multiply by 0.85
Fp2: alpha*0.6 + beta*0.3 + theta*0.1 → multiply by 0.85  (SAME!)
F3:  alpha*0.6 + beta*0.3 + theta*0.1 → multiply by 0.90  (SAME!)
F4:  alpha*0.6 + beta*0.3 + theta*0.1 → multiply by 0.90  (SAME!)
C3:  alpha*0.6 + beta*0.3 + theta*0.1 → multiply by 1.00  (SAME!)
C4:  alpha*0.6 + beta*0.3 + theta*0.1 → multiply by 1.00  (SAME!)
O1:  alpha*0.6 + beta*0.3 + theta*0.1 → multiply by 1.15  (SAME!)
O2:  alpha*0.6 + beta*0.3 + theta*0.1 → multiply by 1.15  (SAME!)
```

**What it SHOULD generate:**
```
Fp1: alpha*0.4 + beta*0.5 + theta*0.1 → multiply by 0.85  (more beta)
O1:  alpha*0.8 + beta*0.1 + theta*0.1 → multiply by 1.15  (more alpha)
```

---

## Summary of All Three Bugs

### Bug #1: Speed Control
**Location:** [ECGWaveformCanvas.tsx:62](hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx#L62)
**Problem:** useEffect doesn't depend on `speed` prop
**Impact:** Horizontal spacing never updates when speed changes

### Bug #2: Gain Control
**Location:** [ECGWaveformCanvas.tsx:62](hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx#L62)
**Problem:** useEffect doesn't depend on `gain` prop
**Impact:** Vertical amplitude never updates when gain changes

### Bug #3: Identical Waveforms
**Location:** [PhysiologicalSimulator.cpp:656-687](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L656-L687)
**Problem:** Channel multiplier only affects amplitude, not frequency mix
**Impact:** All channels show identical waveform shapes (only height differs)

---

## The Fixes

### Fix #1 & #2: Add Dependencies to useEffect

**File:** [ECGWaveformCanvas.tsx:62](hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx#L62)

**Before:**
```typescript
}, [isPaused]);  // ← Missing speed, gain, isECGMode
```

**After:**
```typescript
}, [isPaused, speed, gain, isECGMode]);  // ← Add all rendering dependencies
```

**Why this works:**
- When speed/gain changes, useEffect triggers
- Animation loop restarts with NEW captured values
- drawWaveform() uses updated speed/gain

**Potential issue:** This restarts animation loop on every change (might cause flicker)

**Better approach:**
```typescript
// Option A: Don't use useEffect closure, read props directly in drawWaveform
const drawWaveform = (timestamp: number) => {
  // Props are always fresh, no closure capture issue
  const currentSpeed = speed;
  const currentGain = gain;
  // ... use currentSpeed and currentGain
};

// useEffect can stay as:
}, [isPaused]);  // Only restart loop on pause/unpause
```

### Fix #3: Channel-Specific Frequency Mixing

**File:** [PhysiologicalSimulator.cpp:615-687](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L615-L687)

**Before:**
```cpp
// State-dependent mixing (SAME FOR ALL CHANNELS)
float mixedSignal = 0.0;
switch(currentState) {
    case RESTING:
        mixedSignal = alpha * 0.6 + beta * 0.3 + theta * 0.1;
        break;
}

// Channel-specific amplitude only
float channelMultiplier = 1.0;
switch (channel) {
    case 0:  channelMultiplier = 0.85;  break;
    // ...
}
return mixedSignal * channelMultiplier;
```

**After:**
```cpp
// Channel-specific frequency mixing BEFORE state mixing
float alphaWeight = 0.6;
float betaWeight = 0.3;
float thetaWeight = 0.1;

switch (channel) {
    case 0:  // Fp1 - Frontal pole (motor planning, more beta)
    case 1:  // Fp2
        alphaWeight = 0.4;
        betaWeight = 0.5;
        thetaWeight = 0.1;
        break;

    case 2:  // F3 - Frontal (moderate)
    case 3:  // F4
        alphaWeight = 0.5;
        betaWeight = 0.4;
        thetaWeight = 0.1;
        break;

    case 4:  // C3 - Central (baseline)
    case 5:  // C4
        alphaWeight = 0.6;
        betaWeight = 0.3;
        thetaWeight = 0.1;
        break;

    case 6:  // O1 - Occipital (visual cortex, STRONG ALPHA)
    case 7:  // O2
        alphaWeight = 0.8;  // ← DOMINANT ALPHA
        betaWeight = 0.1;
        thetaWeight = 0.1;
        break;
}

// Apply state-dependent mixing with channel-specific weights
float mixedSignal = 0.0;
switch(currentState) {
    case RESTING:
        mixedSignal = alpha * alphaWeight + beta * betaWeight + theta * thetaWeight;
        break;
    // ... other states
}

return mixedSignal;  // No channel multiplier needed (already in weights)
```

**Result:**
- Frontal channels show **more beta** (faster oscillations)
- Occipital channels show **more alpha** (slower oscillations)
- Each brain region has **unique waveform character**

---

## Medical Accuracy - Why This Matters

### Current (Wrong) Behavior:
All channels show same waveform = **medically impossible**

Real brain regions have different dominant frequencies:
- **Frontal lobe:** Motor planning = beta dominant (13-30 Hz)
- **Occipital lobe:** Visual cortex = alpha dominant (8-13 Hz) when eyes closed
- **Central lobe:** Sensory/motor = balanced mix

### After Fix (Correct) Behavior:
- Frontal channels (Fp1, Fp2) show **faster oscillations** (more beta)
- Occipital channels (O1, O2) show **slower oscillations** (more alpha)
- Central channels (C3, C4) show **intermediate** patterns

**This matches real clinical EEG!**

---

## Testing Plan

### Test #1: Speed Control
1. Set speed to 25mm/s
2. Note waveform horizontal spacing
3. Change speed to 30mm/s
4. **Expected:** Waveform compresses (same data fits in more space)
5. **Currently:** No change (bug)

### Test #2: Gain Control
1. Set gain to 7μV/mm
2. Note waveform vertical amplitude
3. Change gain to 10μV/mm
4. **Expected:** Waveform shrinks vertically (same voltage takes less space)
5. **Currently:** No change (bug)

### Test #3: Channel Differences
1. View all 8 EEG channels simultaneously
2. Compare Fp1 vs O1 waveform patterns
3. **Expected:** Fp1 faster oscillations, O1 slower oscillations
4. **Currently:** Identical waveforms (bug)

---

## Priority

**Priority:** 🔴 HIGH
- Issues #1 & #2: User controls don't work (UX bug)
- Issue #3: Medically inaccurate (clinical correctness bug)

**Impact:**
- Speed/gain controls are **completely non-functional**
- All EEG channels show **medically impossible identical patterns**
- Cannot demonstrate proper EEG monitoring capabilities

---

**END OF DIAGNOSIS**
