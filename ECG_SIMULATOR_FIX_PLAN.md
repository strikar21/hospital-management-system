# ECG Simulator Fix Plan - Anatomically Correct 12-Lead ECG

**Date:** 2025-11-03
**Status:** 📋 PLAN CREATED - Ready for implementation

---

## Problem Statement

**Current Issue:**
The `PhysiologicalSimulator` generates all 8 ECG leads by taking ONE reference PQRST waveform and multiplying it by a scalar for each lead. This produces anatomically IMPOSSIBLE ECGs because:

1. **V1-V2** should have **predominantly NEGATIVE** QRS complexes (rS pattern) - currently they're just scaled-down positive complexes
2. **aVR** should be **completely INVERTED** - currently not handled (calculated from leads I and II)
3. All leads show the **same P/T wave morphology** - real leads have different P and T wave shapes/polarities
4. No consideration of **electrical vector angles** - each lead views the heart from a different angle

---

## Anatomically Correct 12-Lead ECG Requirements

### Lead Vectors and Expected Morphologies:

| Lead | Angle | P Wave | QRS | T Wave | Notes |
|------|-------|--------|-----|--------|-------|
| **I** | 0° | + small | + moderate R | + | Lateral view |
| **II** | +60° | + tall | + tall R | + | Inferior, tallest |
| **III** | +120° | + variable | Variable (may be small) | + or - | Calculated: II - I |
| **aVR** | -150° | **- inverted** | **- deep QS** | **- inverted** | **COMPLETELY NEGATIVE** |
| **aVL** | -30° | + small | + or - | + or - | Lateral, variable |
| **aVF** | +90° | + | + R | + | Inferior |
| **V1** | Right | + small | **rS (- dominant)** | - or biphasic | Right precordial |
| **V2** | Right→Trans | + small | **RS (- significant)** | + small | Transitional |
| **V3** | Transitional | + | **R = S** | + | Transition zone |
| **V4** | Left | + | **Tall R, small S** | + tall | Left precordial, tallest R |
| **V5** | Left lateral | + | **Tall R, tiny S** | + | Lateral |
| **V6** | Left lateral | + | **R, no S** | + | Lateral |

---

## Solution: Component-Based Lead Vector Approach

Instead of:
```cpp
return amplitude * leadMultiplier;  // ❌ WRONG - just scales everything
```

We need:
```cpp
return P_amplitude * P_vector[lead] +
       Q_amplitude * Q_vector[lead] +
       R_amplitude * R_vector[lead] +
       S_amplitude * S_vector[lead] +
       T_amplitude * T_vector[lead];  // ✅ CORRECT - component-based vectors
```

---

## Implementation Plan

### Step 1: Extract PQRST Components

**Current code** generates P, Q, R, S, T sequentially in one amplitude variable.

**Modified approach:** Generate each component separately:

```cpp
float PhysiologicalSimulator::generatePQRST(float phase, int lead) {
    float P = 0.0, Q = 0.0, R = 0.0, S = 0.0, T = 0.0;

    // P wave (0-8% of cycle)
    if (phase < 0.08) {
        float t = phase / 0.08;
        P = 0.15 * sin(t * PI);  // Baseline P amplitude
    }

    // PR segment (8-16%) - isoelectric

    // QRS complex (16-24%)
    else if (phase >= 0.16 && phase < 0.24) {
        float t = (phase - 0.16) / 0.08;

        if (t < 0.25) {
            Q = -0.15 * (t / 0.25);  // Q wave
        }
        else if (t < 0.55) {
            float r_t = (t - 0.25) / 0.30;
            R = 1.7 * sin(r_t * PI);  // R wave (peak ~1.5mV)
        }
        else {
            float s_t = (t - 0.55) / 0.45;
            S = -0.25 * (1.0 - s_t);  // S wave
        }
    }

    // ST segment (24-32%) - isoelectric

    // T wave (32-56%)
    else if (phase >= 0.32 && phase < 0.56) {
        float t = (phase - 0.32) / 0.24;
        T = 0.30 * sin(t * PI);  // Baseline T amplitude
    }

    // Apply lead-specific vector weights
    return applyLeadVectors(P, Q, R, S, T, lead);
}
```

### Step 2: Implement Lead Vector Weighting

```cpp
float PhysiologicalSimulator::applyLeadVectors(float P, float Q, float R, float S, float T, int lead) {
    // Lead-specific vector projections
    // Positive multiplier = same polarity
    // Negative multiplier = inverted polarity
    // Zero = not visible in this lead

    float P_vec, Q_vec, R_vec, S_vec, T_vec;

    switch (lead) {
        case 0:  // Lead I (0° - Lateral)
            P_vec = 0.75;   // Small positive P
            Q_vec = 0.80;   // Small Q
            R_vec = 0.85;   // Moderate R
            S_vec = 0.60;   // Small S
            T_vec = 0.75;   // Positive T
            break;

        case 1:  // Lead II (+60° - Inferior, REFERENCE)
            P_vec = 1.0;    // Tallest P
            Q_vec = 1.0;    // Standard Q
            R_vec = 1.0;    // Tallest R (reference)
            S_vec = 1.0;    // Standard S
            T_vec = 1.0;    // Tallest T
            break;

        case 2:  // V1 (Right precordial - rS pattern)
            P_vec = 0.40;   // Small P
            Q_vec = 0.20;   // Tiny q or absent
            R_vec = 0.30;   // SMALL r wave (30% of normal)
            S_vec = 2.50;   // DEEP S wave (250% of normal) ← KEY FIX
            T_vec = -0.30;  // INVERTED or biphasic T
            break;

        case 3:  // V2 (Transitional - RS pattern)
            P_vec = 0.50;   // Small P
            Q_vec = 0.30;   // Small q
            R_vec = 0.65;   // Growing R (65% of normal)
            S_vec = 1.80;   // Still significant S (180%)
            T_vec = 0.40;   // Small positive T
            break;

        case 4:  // V3 (Transition zone - R = S)
            P_vec = 0.70;   // Moderate P
            Q_vec = 0.50;   // Small q
            R_vec = 1.00;   // R equals baseline
            S_vec = 1.00;   // S equals baseline (R = S)
            T_vec = 0.75;   // Moderate positive T
            break;

        case 5:  // V4 (Left precordial - TALLEST R)
            P_vec = 0.85;   // Good P
            Q_vec = 0.70;   // Small q
            R_vec = 1.40;   // TALLEST R wave (140%)
            S_vec = 0.40;   // Small S (40%)
            T_vec = 0.95;   // Tall positive T
            break;

        case 6:  // V5 (Lateral)
            P_vec = 0.80;   // Good P
            Q_vec = 0.60;   // Small q
            R_vec = 1.25;   // Tall R (125%)
            S_vec = 0.20;   // Tiny S (20%)
            T_vec = 0.85;   // Positive T
            break;

        case 7:  // V6 (Far lateral)
            P_vec = 0.75;   // Moderate P
            Q_vec = 0.50;   // Small q
            R_vec = 1.10;   // Tall R (110%)
            S_vec = 0.10;   // Almost no S (10%)
            T_vec = 0.80;   // Positive T
            break;

        default:
            P_vec = Q_vec = R_vec = S_vec = T_vec = 1.0;
            break;
    }

    return P * P_vec + Q * Q_vec + R * R_vec + S * S_vec + T * T_vec;
}
```

### Step 3: Fix Derived Leads (III, aVR, aVL, aVF)

These are calculated in the ESP32 main firmware from leads I and II.

**Current calculation (in esp32_hospital_watch_complete.ino):**
```cpp
// Lead III = II - I (✅ CORRECT)
int32_t lead3Array[50];
for (int i = 0; i < 50; i++) {
  lead3Array[i] = waveformAccumulator[1][i] - waveformAccumulator[0][i];
}

// aVR = -(I + II) / 2 (✅ CORRECT - will be inverted)
// aVL = I - II / 2 (✅ CORRECT)
// aVF = II - I / 2 (✅ CORRECT)
int32_t avrArray[50], avlArray[50], avfArray[50];
for (int i = 0; i < 50; i++) {
  int32_t ch0 = waveformAccumulator[0][i];  // Lead I
  int32_t ch1 = waveformAccumulator[1][i];  // Lead II
  avrArray[i] = -(ch0 + ch1) / 2;  // aVR will be negative
  avlArray[i] = ch0 - ch1 / 2;
  avfArray[i] = ch1 - ch0 / 2;
}
```

**Status:** ✅ **Derived lead calculations are already correct!**

Once we fix leads I and II to have proper vector projections, the derived leads (III, aVR, aVL, aVF) will automatically be anatomically correct through the Einthoven/Goldberger equations.

---

## Expected Results After Fix

### V1 (Right precordial):
**Before:**
```
P: small positive
QRS: small positive R (just scaled 0.5x)
T: small positive
```

**After:**
```
P: small positive
QRS: rS pattern (tiny r, DEEP negative S)
T: inverted or biphasic
```

### V4 (Left precordial):
**Before:**
```
P: moderate
QRS: tall R (scaled 1.25x)
T: moderate
```

**After:**
```
P: prominent positive
QRS: VERY TALL R, tiny S
T: tall positive
```

### aVR (calculated from I + II):
**Before:**
```
QRS: negative (but not deeply inverted)
```

**After:**
```
P: deeply inverted
QRS: deep QS complex (no R wave)
T: deeply inverted
ENTIRE LEAD IS NEGATIVE
```

---

## Files to Modify

1. **PhysiologicalSimulator.cpp** (lines 334-417)
   - Refactor `generatePQRST()` to extract P, Q, R, S, T components
   - Add new `applyLeadVectors()` method with proper vector weighting
   - Use component-based projection instead of simple scalar multiplication

2. **PhysiologicalSimulator.h** (add private method declaration)
   - Add: `float applyLeadVectors(float P, float Q, float R, float S, float T, int lead);`

---

## Testing Plan

### 1. Visual Inspection:
- Flash firmware to ESP32
- Open ECG Viewer
- Check each lead for proper morphology:
  - V1: Should show rS pattern (negative dominant)
  - V4: Should show tallest R wave
  - aVR: Should be completely inverted (all negative)

### 2. Calibration Pulse Test:
- Verify calibration pulse still works (1mV square wave)
- All leads should show same 1mV pulse during calibration

### 3. Amplitude Measurements:
- V1 QRS should be predominantly below baseline
- V4 R wave should be tallest of all precordial leads
- aVR should have deepest negative deflection

---

## Approval Required

**Before implementing, please confirm:**

1. ✅ Do you want anatomically correct 12-lead ECG with proper lead vectors?
2. ✅ Is it acceptable to modify the core PQRST generation logic?
3. ✅ Should I proceed with the component-based vector approach described above?

---

**Ready to implement once approved.**
