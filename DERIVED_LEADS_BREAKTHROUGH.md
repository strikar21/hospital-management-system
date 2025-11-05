# Derived Leads Breakthrough - Data is Flowing!

**Status:** Data is reaching canvas but waveforms not visible - need to inspect actual values

---

## Key Finding from Browser Console

```
[ECGWaveformCanvas ... Lead III] dataLength=12500, Phase 2 (Typewriter Scroll) ✅
[ECGWaveformCanvas ... Lead aVR] dataLength=12500, Phase 2 (Typewriter Scroll) ✅
[ECGWaveformCanvas ... Lead aVL] dataLength=12500, Phase 2 (Typewriter Scroll) ✅
[ECGWaveformCanvas ... Lead aVF] dataLength=12500, Phase 2 (Typewriter Scroll) ✅
```

**ALL DERIVED LEADS HAVE 12,500 SAMPLES!** This means:
- ✅ ESP32 firmware is sending the derived lead data
- ✅ Backend WebSocket is passing it through
- ✅ Frontend is receiving and buffering it
- ✅ Canvas is attempting to render it

**Problem is NOT:**
- ❌ Missing data
- ❌ Field name mismatch
- ❌ Data flow broken

**Problem IS:**
- ❓ Waveform values are flat/isoelectric (all at baseline)
- ❓ Formulas producing incorrect results
- ❓ Rendering issue (unlikely - same code works for I, II, V1-V6)

---

## Next Diagnostic Step

Add temporary logging to see ACTUAL ADC values being rendered:

###Option 1: Log in useECGViewer.ts (when data arrives)

```typescript
// After line 163 in useECGViewer.ts
if (derived?.avf) {
  const samples = getData(derived.avf);
  dataBufferRef.current[5] = [...dataBufferRef.current[5], ...samples].slice(-maxBufferSize);

  // 🔍 DIAGNOSTIC: Log first 10 values of aVF
  if (samples.length > 0 && waveformData.sequence % 10 === 0) {
    console.log(`🔍 aVF first 10 values:`, samples.slice(0, 10));
  }
}
```

### Option 2: Log in medicalWaveformUtils.ts (during rendering)

```typescript
// In adcToMillivolts() function after line 125
export function adcToMillivolts(adcValue: number): number {
  const mV = (adcValue - ADC_MIDPOINT) / ECG_ADC_SCALE_FACTOR;

  // 🔍 DIAGNOSTIC: Log first conversion (once per lead)
  if (!window._adcDebugLogged) {
    window._adcDebugLogged = {};
  }
  if (!window._adcDebugLogged[adcValue]) {
    console.log(`ADC ${adcValue} → ${mV.toFixed(3)} mV`);
    window._adcDebugLogged[adcValue] = true;
  }

  return mV;
}
```

---

## Hypothesis: Formula Errors Producing Flat Lines

Based on ESP32 formulas (lines 1996-2003):

```cpp
avrArray[i] = -(ch0 + ch1) / 2;  // ✅ Likely correct (aVR should be negative)
avlArray[i] = ch0 - ch1 / 2;     // ❌ WRONG: Operator precedence! = ch0 - (ch1/2)
avfArray[i] = ch1 - ch0 / 2;     // ❌ WRONG: Operator precedence! = ch1 - (ch0/2)
```

**What C++ actually calculates:**

Given typical values (Lead I and II are similar in resting state):
- Lead I (ch0) = 8388608 + 100000 = 8488608 (1mV)
- Lead II (ch1) = 8388608 + 100000 = 8488608 (1mV)

**aVL calculation:**
```cpp
avlArray[i] = ch0 - ch1 / 2;
            = 8488608 - (8488608 / 2)
            = 8488608 - 4244304
            = 4244304
```

**Wait, that should still show a waveform!** Let me recalculate...

Actually, if Lead I and Lead II are tracking the same heartbeat with similar amplitudes:

**During P wave (both positive, ~0.15mV):**
- ch0 = 8388608 + 15000 = 8403608
- ch1 = 8388608 + 15000 = 8403608
- aVL = 8403608 - (8403608 / 2) = 8403608 - 4201804 = **4201804**
  - Converting to mV: (4201804 - 8388608) / 100000 = **-41.9 mV** ❌ WAY TOO NEGATIVE!

**During baseline (both at 0mV):**
- ch0 = 8388608
- ch1 = 8388608
- aVL = 8388608 - (8388608 / 2) = 8388608 - 4194304 = **4194304**
  - Converting to mV: (4194304 - 8388608) / 100000 = **-41.9 mV** ❌ CONSTANT!

**EUREKA!** The wrong formula creates a **constant offset** instead of a waveform!

---

## Root Cause Confirmed

The operator precedence bug causes aVL and aVF to be **constant values** instead of waveforms:

**aVL formula (current, WRONG):**
```cpp
avlArray[i] = ch0 - ch1 / 2;  // = ch0 - (ch1 / 2) due to operator precedence
```

**What it calculates:**
- Resting state: ch0 ≈ ch1 ≈ 8388608
- avlArray[i] = 8388608 - (8388608 / 2) = 8388608 - 4194304 = **4194304** (constant!)
- Converts to: (4194304 - 8388608) / 100000 = **-41.9 mV** (way off scale!)

**Why it's invisible:**
- Canvas has fixed scale: -2mV to +2mV visible range
- aVL value is **-41.9 mV** (21× below visible range!)
- Waveform is rendered far below the canvas bottom edge

**Same problem for aVF:**
```cpp
avfArray[i] = ch1 - ch0 / 2;  // = ch1 - (ch0 / 2)
             = 8388608 - 4194304 = 4194304 (same constant!)
```

---

## Verification Plan

Add this diagnostic to useECGViewer.ts to see actual buffer values:

```typescript
// After line 163 in useECGViewer.ts (aVF processing)
if (waveformData.sequence && waveformData.sequence % 50 === 0) {
  console.log(`📊 Derived lead sample check (SEQ ${waveformData.sequence}):`, {
    'aVR first value': dataBufferRef.current[3]?.[0],
    'aVL first value': dataBufferRef.current[4]?.[0],
    'aVF first value': dataBufferRef.current[5]?.[0],
    'aVR in mV': dataBufferRef.current[3]?.[0] ?
      ((dataBufferRef.current[3][0] - 8388608) / 100000).toFixed(3) : 'N/A',
    'aVL in mV': dataBufferRef.current[4]?.[0] ?
      ((dataBufferRef.current[4][0] - 8388608) / 100000).toFixed(3) : 'N/A',
    'aVF in mV': dataBufferRef.current[5]?.[0] ?
      ((dataBufferRef.current[5][0] - 8388608) / 100000).toFixed(3) : 'N/A'
  });
}
```

**Expected output if my hypothesis is correct:**
```
aVR in mV: -1.500 ✅ (should vary with heartbeat)
aVL in mV: -41.943 ❌ (constant - way off scale!)
aVF in mV: -41.943 ❌ (constant - way off scale!)
```

---

## Fix Required

**ESP32 Firmware:** `esp32_hospital_watch_complete.ino` lines 1996-2003

**Current (WRONG):**
```cpp
avlArray[i] = ch0 - ch1 / 2;  // ❌ Operator precedence: ch0 - (ch1/2)
avfArray[i] = ch1 - ch0 / 2;  // ❌ Operator precedence: ch1 - (ch0/2)
```

**Correct (Goldberger formulas):**
```cpp
int32_t leadI = waveformAccumulator[0][i];
int32_t leadII = waveformAccumulator[1][i];

avlArray[i] = (3 * (2 * leadI - leadII)) / 4;  // ✅ Goldberger: 1.5*(2I-II)/2
avfArray[i] = (3 * (2 * leadII - leadI)) / 4;  // ✅ Goldberger: 1.5*(2II-I)/2
avrArray[i] = -(3 * (leadI + leadII)) / 4;     // ✅ Goldberger: -1.5*(I+II)/2
```

---

**Next Step:** Add diagnostic logging to confirm actual values before implementing fix.
