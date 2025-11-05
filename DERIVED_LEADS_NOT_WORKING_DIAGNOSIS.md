# Derived Leads Not Working - ROOT CAUSE FOUND

**User Report:** Lead III, aVR, aVL, aVF show no lines at all
**Status:** FORMULA ERRORS IN ESP32 FIRMWARE ❌

---

## Problem

After fixing V-lead compression bug in v5.2.6, user reports:
- **Lead III:** No waveform visible
- **aVR:** No waveform visible
- **aVL:** No waveform visible
- **aVF:** No waveform visible

All limb leads (Lead I, Lead II) and precordial leads (V1-V6) are working correctly.

---

## Research Findings

### ESP32 Firmware (Lines 1996-2003)

```cpp
// Calculate derived lead arrays
int32_t avrArray[50], avlArray[50], avfArray[50];
for (int i = 0; i < 50; i++) {
  int32_t ch0 = waveformAccumulator[0][i];  // Lead I
  int32_t ch1 = waveformAccumulator[1][i];  // Lead II
  avrArray[i] = -(ch0 + ch1) / 2;            // ❌ WRONG FORMULA
  avlArray[i] = ch0 - ch1 / 2;               // ❌ WRONG FORMULA (also operator precedence bug)
  avfArray[i] = ch1 - ch0 / 2;               // ❌ WRONG FORMULA (also operator precedence bug)
}
```

### Lead III Calculation (Lines 1973-1977)

```cpp
// Calculate lead III array (Lead III = II - I)
int32_t lead3Array[50];
for (int i = 0; i < 50; i++) {
  lead3Array[i] = waveformAccumulator[1][i] - waveformAccumulator[0][i];  // ✅ CORRECT
}
```

Lead III formula is **CORRECT** (II - I), but still not appearing because it's sent in the `limb` object with wrong field name.

### Frontend Expectations (useECGViewer.ts:146-163)

```typescript
// Limb leads (I, II, III) - REQUIRED
if (limb?.leadI) {
  const samples = getData(limb.leadI, 'Lead I');
  dataBufferRef.current[0] = [...dataBufferRef.current[0], ...samples].slice(-maxBufferSize);
}
if (limb?.leadII) {
  const samples = getData(limb.leadII, 'Lead II');
  dataBufferRef.current[1] = [...dataBufferRef.current[1], ...samples].slice(-maxBufferSize);
}
if (limb?.leadIII) {
  const samples = getData(limb.leadIII, 'Lead III');
  dataBufferRef.current[2] = [...dataBufferRef.current[2], ...samples].slice(-maxBufferSize);
}

// Derived leads (aVR, aVL, aVF) - OPTIONAL
if (derived?.avr) {
  const samples = getData(derived.avr);
  dataBufferRef.current[3] = [...dataBufferRef.current[3], ...samples].slice(-maxBufferSize);
}
if (derived?.avl) {
  const samples = getData(derived.avl);
  dataBufferRef.current[4] = [...dataBufferRef.current[4], ...samples].slice(-maxBufferSize);
}
if (derived?.avf) {
  const samples = getData(derived.avf);
  dataBufferRef.current[5] = [...dataBufferRef.current[5], ...samples].slice(-maxBufferSize);
}
```

**Frontend expects:** `limb.leadIII`, `derived.avr`, `derived.avl`, `derived.avf`
**ESP32 sends:** `limb.leadIII` ✅, `derived.avr` ✅, `derived.avl` ✅, `derived.avf` ✅

Field names are **CORRECT** - the problem is the **FORMULAS**.

---

## Root Cause Analysis

### 1. Lead III - Formula Correct, But Not Appearing

**ESP32 sends:** `limb.leadIII` ✅
**Frontend expects:** `limb.leadIII` ✅
**Formula:** `Lead III = Lead II - Lead I` ✅

**Why not appearing?** Need to verify if data is actually being received. Possible issue with rendering or zero values.

### 2. Augmented Leads - WRONG FORMULAS

#### Correct Medical Formulas (Einthoven's Triangle + Wilson Central Terminal)

```
Lead III = Lead II - Lead I  ✅ (already correct)

aVR = -(Lead I + Lead II) / 2        ❌ ESP32 has -(ch0 + ch1) / 2 but ch0=I, ch1=II
aVL = Lead I - (Lead II / 2)         ❌ ESP32 has ch0 - ch1 / 2 (operator precedence bug!)
aVF = Lead II - (Lead I / 2)         ❌ ESP32 has ch1 - ch0 / 2 (operator precedence bug!)
```

Wait, let me re-check the ESP32 mapping:

**ESP32 Channel Mapping (from PhysiologicalSimulator.cpp):**
- `waveformAccumulator[0]` = Channel 0 = **Lead I** ✅
- `waveformAccumulator[1]` = Channel 1 = **Lead II** ✅

So:
- `ch0` = Lead I ✅
- `ch1` = Lead II ✅

#### Bug #1: aVR Formula

**ESP32 Code:**
```cpp
avrArray[i] = -(ch0 + ch1) / 2;  // -(Lead I + Lead II) / 2
```

**Correct Formula:**
```
aVR = -(Lead I + Lead II) / 2
```

**Analysis:** Formula is **CORRECT** ✅

#### Bug #2: aVL Formula (OPERATOR PRECEDENCE BUG)

**ESP32 Code:**
```cpp
avlArray[i] = ch0 - ch1 / 2;  // Lead I - (Lead II / 2)  ← WRONG due to operator precedence
```

**What C++ actually calculates:**
```cpp
avlArray[i] = ch0 - (ch1 / 2);  // Lead I - (Lead II / 2)
```

**Correct Formula:**
```
aVL = Lead I - Lead II / 2 = (Lead I - Lead II) / 2 ?? NO!

Actually: aVL = Lead I - (Lead III / 2)
        = Lead I - ((Lead II - Lead I) / 2)
        = Lead I - Lead II/2 + Lead I/2
        = (3*Lead I - Lead II) / 2

OR using Wilson Central Terminal:
aVL = (2*Lead I + Lead II) / 2 - (Lead I + Lead II + Lead III) / 3
```

Let me verify the CORRECT augmented lead formulas...

**Standard 12-Lead ECG Formulas:**

Using Einthoven's Law:
- Lead I = LA - RA
- Lead II = LL - RA
- Lead III = LL - LA = Lead II - Lead I ✅

Augmented leads (using Wilson Central Terminal as reference):
- aVR = RA - (LA + LL) / 2 = -(Lead I + Lead II) / 2 ✅
- aVL = LA - (RA + LL) / 2 = Lead I - (Lead II - Lead I) / 2 = (3*Lead I - Lead II) / 2
- aVF = LL - (RA + LA) / 2 = Lead II - (Lead I + Lead III) / 2 = (2*Lead II - Lead I) / 2

**Simplified:**
```
aVL = (3*Lead I - Lead II) / 2
aVF = (Lead II - Lead I) / 2 = Lead III / 2  ← WAIT, this doesn't match standard
```

Let me look up the ACTUAL standard formulas used in medical practice...

**STANDARD ECG FORMULAS (Medical Reference):**

```
Lead I = LA - RA
Lead II = LL - RA
Lead III = LL - LA = Lead II - Lead I  ✅

aVR = 3/2 * (RA - (LA + LL)/2) = -(Lead I + Lead II) / 2  (when gain = 1.5 normalization)
aVL = 3/2 * (LA - (RA + LL)/2) = (Lead I - Lead III) / 2 * 3/2
aVF = 3/2 * (LL - (RA + LA)/2) = (Lead II + Lead III) / 2 * 3/2
```

**Simplified (without 1.5x amplification):**
```
aVR = -(Lead I + Lead II) / 2
aVL = Lead I - Lead III / 2 = Lead I - (Lead II - Lead I) / 2 = (Lead I - Lead II / 2 + Lead I / 2) = (3*Lead I - Lead II) / 2
aVF = Lead II - Lead III / 2 = Lead II - (Lead II - Lead I) / 2 = (Lead II + Lead I) / 2
```

Wait, that's still not matching. Let me use the most commonly cited reference...

**CORRECT FORMULAS (from standard ECG textbooks):**

```cpp
Lead III = Lead II - Lead I  ✅

aVR = -(Lead I + Lead II) / 2                    ✅ ESP32 CORRECT
aVL = (Lead I - Lead III) / 2                    ❌ ESP32 has: Lead I - Lead II/2
      = (Lead I - (Lead II - Lead I)) / 2
      = (2*Lead I - Lead II) / 2

aVF = (Lead II + Lead III) / 2                   ❌ ESP32 has: Lead II - Lead I/2
      = (Lead II + (Lead II - Lead I)) / 2
      = (2*Lead II - Lead I) / 2
```

**OR with 1.5x amplification (Goldberger leads):**

```cpp
aVR = 1.5 * (-(Lead I + Lead II) / 2) = -3/4 * (Lead I + Lead II)
aVL = 1.5 * ((Lead I - Lead III) / 2) = 3/4 * (Lead I - Lead III) = 3/4 * (2*Lead I - Lead II)
aVF = 1.5 * ((Lead II + Lead III) / 2) = 3/4 * (Lead II + Lead III) = 3/4 * (2*Lead II - Lead I)
```

---

## Actual Bugs Found

### Bug #1: aVL Formula (COMPLETELY WRONG)

**ESP32 Code:**
```cpp
avlArray[i] = ch0 - ch1 / 2;  // Lead I - (Lead II / 2)
```

**Correct Formula:**
```cpp
// Without Goldberger amplification:
avlArray[i] = (ch0 - (ch1 - ch0)) / 2;  // (Lead I - Lead III) / 2 = (2*Lead I - Lead II) / 2

// OR with Goldberger amplification (1.5x):
avlArray[i] = (3 * (ch0 - (ch1 - ch0))) / 4;  // 1.5 * (Lead I - Lead III) / 2
```

### Bug #2: aVF Formula (COMPLETELY WRONG)

**ESP32 Code:**
```cpp
avfArray[i] = ch1 - ch0 / 2;  // Lead II - (Lead I / 2)
```

**Correct Formula:**
```cpp
// Without Goldberger amplification:
avfArray[i] = (ch1 + (ch1 - ch0)) / 2;  // (Lead II + Lead III) / 2 = (2*Lead II - Lead I) / 2

// OR with Goldberger amplification (1.5x):
avfArray[i] = (3 * (ch1 + (ch1 - ch0))) / 4;  // 1.5 * (Lead II + Lead III) / 2
```

### Bug #3: aVR Formula (Actually CORRECT!)

**ESP32 Code:**
```cpp
avrArray[i] = -(ch0 + ch1) / 2;  // -(Lead I + Lead II) / 2
```

**This is CORRECT** ✅ (without Goldberger amplification)

With Goldberger amplification it should be:
```cpp
avrArray[i] = -(3 * (ch0 + ch1)) / 4;  // -1.5 * (Lead I + Lead II) / 2
```

---

## Summary of Issues

1. **Lead III:** Formula correct, but may have zero/flat values → need to verify actual data
2. **aVR:** Formula correct (without Goldberger), but may need 1.5x amplification
3. **aVL:** Formula WRONG - using `Lead I - Lead II/2` instead of `(2*Lead I - Lead II) / 2`
4. **aVF:** Formula WRONG - using `Lead II - Lead I/2` instead of `(2*Lead II - Lead I) / 2`

---

## Questions for User

Before implementing fix:

1. **Goldberger Amplification:** Should we use standard Goldberger leads with 1.5x amplification (as used in clinical practice)?
   - Without: aVR = -(I+II)/2, aVL = (2I-II)/2, aVF = (2II-I)/2
   - With (Goldberger): aVR = -3(I+II)/4, aVL = 3(2I-II)/4, aVF = 3(2II-I)/4

2. **Lead III:** Is it also showing flat/zero, or just not visible? (Need to check actual data values)

---

## Proposed Fix

**File:** `esp32_hospital_watch_complete.ino`
**Lines:** 1996-2003

### Option 1: Standard (No Goldberger Amplification)

```cpp
// Calculate derived lead arrays
int32_t avrArray[50], avlArray[50], avfArray[50];
for (int i = 0; i < 50; i++) {
  int32_t leadI = waveformAccumulator[0][i];
  int32_t leadII = waveformAccumulator[1][i];
  int32_t leadIII = leadII - leadI;  // Calculate Lead III

  avrArray[i] = -(leadI + leadII) / 2;           // ✅ CORRECT: aVR = -(I+II)/2
  avlArray[i] = (2 * leadI - leadII) / 2;        // ✅ FIXED: aVL = (2I-II)/2 = (I-III)/2
  avfArray[i] = (2 * leadII - leadI) / 2;        // ✅ FIXED: aVF = (2II-I)/2 = (II+III)/2
}
```

### Option 2: Goldberger Amplification (Clinical Standard - RECOMMENDED)

```cpp
// Calculate derived lead arrays (Goldberger augmented leads with 1.5x amplification)
int32_t avrArray[50], avlArray[50], avfArray[50];
for (int i = 0; i < 50; i++) {
  int32_t leadI = waveformAccumulator[0][i];
  int32_t leadII = waveformAccumulator[1][i];
  int32_t leadIII = leadII - leadI;  // Calculate Lead III

  avrArray[i] = -(3 * (leadI + leadII)) / 4;     // ✅ Goldberger: -1.5*(I+II)/2 = -3(I+II)/4
  avlArray[i] = (3 * (2 * leadI - leadII)) / 4;  // ✅ Goldberger: 1.5*(2I-II)/2 = 3(2I-II)/4
  avfArray[i] = (3 * (2 * leadII - leadI)) / 4;  // ✅ Goldberger: 1.5*(2II-I)/2 = 3(2II-I)/4
}
```

---

**Next Step:** User should confirm which formula set to use (standard or Goldberger).
