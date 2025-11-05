# Waveform Display Issues - User Report Diagnosis

**Date:** 2025-11-03
**User Report:** "derived leads don't work? leads v1-v6 are fucked? they aren't clean like lead 1 & 2"

---

## What's Happening

### The Good News (Working):
✅ **Lead I and Lead II** look "clean" - these are the two DIRECT hardware channels from the ESP32

### The Bad News (Problems):
❌ **V1-V6** (channels 2-7) look "fucked" - not clean
❌ **Derived leads** (III, aVR, aVL, aVF) "don't work"

---

## Root Cause Analysis

### Issue #1: Derived Lead Calculation BUGS

**File:** [esp32_hospital_watch_complete.ino:1984-1991](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1984-L1991)

```cpp
// ❌ WRONG - Integer division loses precision
int32_t avrArray[50], avlArray[50], avfArray[50];
for (int i = 0; i < 50; i++) {
  int32_t ch0 = waveformAccumulator[0][i];  // Lead I
  int32_t ch1 = waveformAccumulator[1][i];  // Lead II
  avrArray[i] = -(ch0 + ch1) / 2;  // ❌ INTEGER DIVISION
  avlArray[i] = ch0 - ch1 / 2;     // ❌ ORDER OF OPERATIONS BUG
  avfArray[i] = ch1 - ch0 / 2;     // ❌ ORDER OF OPERATIONS BUG
}
```

**Problems:**

1. **Integer division loses precision:**
   - `(ch0 + ch1) / 2` loses the fractional part if sum is odd
   - ADC values are 24-bit (8388608 midpoint) - losing precision adds noise

2. **Order of operations is WRONG:**
   ```cpp
   avlArray[i] = ch0 - ch1 / 2;  // ❌ WRONG - divides ch1 first, then subtracts
   // Should be: avlArray[i] = (ch0 - ch1) / 2;
   ```

   This calculates: `ch0 - (ch1 / 2)` instead of `(ch0 - ch1) / 2`

3. **Goldberger's equations are WRONG:**
   - Current: `aVL = I - II/2` (wrong order of operations)
   - Correct: `aVL = I - (II - I)/2 = (2I - II + I)/2 = (3I - II)/2`
   - Actually simplified: `aVL = (I - (II-I))/2 = (2I - II)/2`

**Correct Formulas:**
```
aVR = -(I + II) / 2         ← Actually correct in code
aVL = (I - III) / 2         ← But III = II - I, so aVL = (2I - II) / 2
aVF = (II + III) / 2        ← But III = II - I, so aVF = (2II - I) / 2
```

OR using just I and II:
```
aVR = -(I + II) / 2
aVL = (2I - II) / 2
aVF = (2II - I) / 2
```

---

### Issue #2: V1-V6 "Not Clean" - Possible Causes

#### Hypothesis 1: Noise Added During Generation
**File:** [PhysiologicalSimulator.cpp:312-315](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L312-L315)

```cpp
// Convert to 24-bit ADC units
sample = 8388608 + (int32_t)(amplitude * 100000);

// Add realistic noise (~10 μV RMS)
sample += random(-50, 51);  // ← NOISE ADDED TO ALL CHANNELS
```

**Lead I and Lead II look clean** → Maybe the noise is actually OK?

#### Hypothesis 2: Delta Encoding Accumulation Error
The delta encoding/decoding process might accumulate errors:

**ESP32 Encoding:**
```cpp
void addDeltaEncodedChannel(JsonObject& parent, const char* fieldName, int32_t* samples, int count) {
  channel["baseline"] = samples[0];
  JsonArray deltas = channel.createNestedArray("deltas");
  for (int i = 1; i < count; i++) {
    deltas.add(samples[i] - samples[i-1]);  // ← Calculates deltas
  }
}
```

**Frontend Decoding:**
```typescript
export function decodeDeltaChannel(deltaData: { baseline: number; deltas: number[] }): number[] {
  const samples: number[] = [deltaData.baseline];
  let currentValue = deltaData.baseline;

  for (const delta of deltaData.deltas) {
    currentValue += delta;  // ← Reconstructs by adding deltas
    samples.push(currentValue);
  }

  return samples;
}
```

This should be mathematically correct, but if there's JSON serialization error or type coercion...

#### Hypothesis 3: V1-V6 Component Vector Bug
**Our recent fix added component-based vectors for V1-V6:**

```cpp
case 2:  // V1
    R_vec = 0.30;   // Small r
    S_vec = 2.50;   // DEEP S
    // ...
```

If the S wave is 2.50x the baseline S amplitude, and baseline S = -0.25mV:
```
S_actual = -0.25 * 2.50 = -0.625mV
```

This is a VERY DEEP negative deflection. When converted to ADC:
```
sample = 8388608 + (-0.625 * 100000) = 8388608 - 62500 = 8326108
```

**This is mathematically correct, but might look "noisy" or "wrong" on the display if:**
- Frontend expects positive QRS
- Frontend scales assuming all leads are similar amplitude
- Frontend doesn't handle negative-dominant QRS well

#### Hypothesis 4: Lead I/II Are Clean Because They're Reference
- Lead I (ch0): P=0.75, R=0.85, S=0.60 - moderate, balanced
- Lead II (ch1): P=1.0, R=1.0, S=1.0 - reference, baseline
- V1 (ch2): P=0.40, R=0.30, **S=2.50**, T=-0.30 - **VERY DIFFERENT AMPLITUDES**

If all leads are displayed with the same scaling/gain on the frontend, V1-V6 might look "fucked" because they have very different morphologies now (which is anatomically correct, but visually different).

---

## What We Need to Check

### Question 1: What does "fucked" mean exactly?
- ❓ Noisy/jittery waveform?
- ❓ Wrong amplitude (too big/too small)?
- ❓ Waveform shape is wrong (not PQRST)?
- ❓ Waveform is flat/missing?
- ❓ Waveform has artifacts/spikes?

### Question 2: What does "derived leads don't work" mean?
- ❓ aVR/aVL/aVF are flat (zero)?
- ❓ aVR/aVL/aVF show noise only?
- ❓ aVR/aVL/aVF show wrong morphology?
- ❓ aVR/aVL/aVF are not displayed at all?

### Question 3: Is the ECG fix we just made causing this?
- ⚠️ **WE JUST MODIFIED THE SIMULATOR** - could be our fault!
- Need to test: Does reverting the simulator fix make V1-V6 "clean" again?

---

## Immediate Diagnostic Steps

### Step 1: Check Serial Monitor Output
Flash ESP32 and check if waveform generation shows errors:
```
🔧 Calibration command received
✅ Calibration pulse complete
📊 Vitals: Mode=ECG, HR=75, ...
```

### Step 2: Check Frontend Console
Open browser DevTools → Console, look for:
```javascript
❌ Invalid delta-encoded data: ...
❌ Invalid waveform data structure
```

### Step 3: Visual Inspection
Open ECG Viewer and compare:
- Lead I (ch0) - should be clean
- Lead II (ch1) - should be clean
- V1 (ch2) - should show rS pattern (small r, DEEP negative S) ← **This will look VERY different from I/II**
- V4 (ch5) - should show TALL R wave ← **This will also look different**
- aVR - should be inverted ← **Should look completely different**

### Step 4: Test Derived Lead Formulas
Add debug logging to ESP32:
```cpp
Serial.print("aVR[0] = -(");
Serial.print(ch0);
Serial.print(" + ");
Serial.print(ch1);
Serial.print(") / 2 = ");
Serial.println(avrArray[0]);
```

---

## Proposed Fixes

### Fix #1: Correct Derived Lead Formulas (CRITICAL)

**File:** [esp32_hospital_watch_complete.ino:1988-1990](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1988-L1990)

```cpp
// ❌ BEFORE (WRONG)
avrArray[i] = -(ch0 + ch1) / 2;  // OK
avlArray[i] = ch0 - ch1 / 2;     // ❌ WRONG order of operations
avfArray[i] = ch1 - ch0 / 2;     // ❌ WRONG order of operations

// ✅ AFTER (CORRECT)
avrArray[i] = -(ch0 + ch1) / 2;     // aVR correct
avlArray[i] = (ch0 * 2 - ch1) / 2;  // aVL = (2I - II) / 2
avfArray[i] = (ch1 * 2 - ch0) / 2;  // aVF = (2II - I) / 2
```

### Fix #2: Investigate "Clean" Definition
Need user clarification:
- What does "clean" mean?
- Are V1-V6 supposed to look the same as I/II? (They shouldn't!)
- Is the "not clean" issue visual (different morphology) or technical (actual noise)?

### Fix #3: Optional - Reduce V1-V2 S-wave Magnitude
If V1-V2 look "too extreme", could reduce S-wave vector:

```cpp
case 2:  // V1
    S_vec = 1.80;   // Less deep S (instead of 2.50)
```

But this would be LESS anatomically correct.

---

## Questions for User

1. **What exactly looks "fucked" about V1-V6?**
   - Noisy?
   - Wrong shape?
   - Too big/small?
   - Has artifacts?

2. **What does "derived leads don't work" mean?**
   - Do they display anything?
   - Are they flat?
   - Are they noisy?
   - Do they show wrong morphology?

3. **Did this happen AFTER our ECG fix, or was it already broken?**
   - Need to know if our fix caused this

4. **Can you share a screenshot of the ECG Viewer showing the "fucked" waveforms?**

---

## Status

🔴 **BLOCKED** - Need user clarification on what "fucked" and "don't work" mean specifically

**Next Action:** Wait for user response with:
- Screenshot of ECG Viewer
- Description of what looks wrong
- Whether this happened before or after our ECG fix
