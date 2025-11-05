# Mode Switching ACTUAL Bug - Wrong Waveforms Displayed

**Date:** 2025-11-04
**Status:** 🔴 **CRITICAL BUG** - Mode label correct, but waveforms are from WRONG mode

---

## User Report (Clarified)

> "i swapped from ecg to eeg and can see ecg only. or vice versa the waveforms, but the mode in the top is correct."

**What this means:**
- Swap cable from ECG → EEG
- Mode label changes to "EEG" ✅
- **BUT waveforms shown are ECG waveforms** ❌
- OR vice versa: Mode says "ECG" but shows EEG waveforms

**This is NOT about stale data** - This is about **wrong buffer mapping**!

---

## Root Cause Hypothesis

The issue is likely in **ECGDisplayGrid.tsx getBufferIndex()** function:

```typescript
const getBufferIndex = (displayIndex: number): number => {
  if (isECGMode) {
    return displayIndex;  // ECG: direct 1:1 mapping (0-11)
  }
  // EEG: Skip T3/T4 buffer slots (18-19) when mapping O1/O2
  if (displayIndex < 6) {
    // Fp1, Fp2, F3, F4, C3, C4 → buffers 12-17
    return displayIndex + 12;
  } else {
    // O1, O2 → buffers 20-21 (skip T3/T4 at 18-19 by adding +14 instead of +12)
    return displayIndex + 14;
  }
};
```

**Problem scenarios:**

### Scenario 1: ECG data in buffers, but displaying as EEG

1. ESP32 sends ECG waveforms
2. Data goes to buffers 0-11 (correct)
3. User swaps cable to EEG
4. Mode switches to EEG
5. `getBufferIndex()` now maps to buffers 12-21
6. **BUT buffers 12-21 are empty!**
7. Canvas shows empty/baseline waveforms
8. User says "I see ECG" - probably means they see the WRONG scale/labels

### Scenario 2: Wrong data being written to buffers

Let me check if the WebSocket handler is writing to the correct buffers based on the incoming mode...

**Wait - I need to check if the issue is:**
1. ❌ Data being written to wrong buffers
2. ❌ Data being read from wrong buffers
3. ❌ `isECGMode` state not updating correctly

---

## Investigation Needed

I need to verify:
1. When ESP32 sends `waveformData.mode = 'eeg'`, does it go to buffers 12-21? ✅ (Lines 258-305 in useECGViewer.ts)
2. When ESP32 sends `waveformData.mode = 'ecg'`, does it go to buffers 0-11? ✅ (Lines 159-210 in useECGViewer.ts)
3. When `isECGMode = false`, does `getBufferIndex()` read from buffers 12-21? ✅ (Lines 91-97 in ECGDisplayGrid.tsx)
4. When `isECGMode = true`, does `getBufferIndex()` read from buffers 0-11? ✅ (Line 88 in ECGDisplayGrid.tsx)

**The code looks correct!**

So the bug must be something else...

---

## Possible Root Causes

### Hypothesis 1: `isECGMode` state not syncing with ESP32 mode

**File:** [useECGViewer.ts:122-128](hospital-display-app/src/hooks/useECGViewer.ts#L122-L128)

```typescript
// Auto-detect mode from ESP32 and switch display accordingly
if (waveformData.mode === 'ecg' && !isECGMode) {
  logger.log('🔄 Auto-switching to ECG mode (detected from device)');
  setIsECGMode(true);
} else if (waveformData.mode === 'eeg' && isECGMode) {
  logger.log('🔄 Auto-switching to EEG mode (detected from device)');
  setIsECGMode(false);
}
```

**What if:**
- ESP32 sends `mode: 'ecg'` BUT also sends `eegWaveform` data?
- OR ESP32 sends `mode: 'eeg'` BUT also sends `ecgWaveform` data?
- Frontend switches `isECGMode` based on `mode` field
- BUT data is written based on presence of `ecgWaveform` or `eegWaveform` fields

**This would cause:**
- Mode label: "EEG" (from `isECGMode = false`)
- Waveforms: ECG data (from `ecgWaveform` being present in buffers 0-11)
- Canvas reads: buffers 12-21 (mapped from `isECGMode = false`)
- Result: **Empty screen** (buffers 12-21 are empty)

**OR:**
- Mode label: "EEG" (from `isECGMode = false`)
- Waveforms: ECG data still in buffers 0-11 from before mode switch
- Canvas reads: buffers 12-21 (empty or old data)
- Result: **Wrong waveforms or empty screen**

### Hypothesis 2: ESP32 sends BOTH ecgWaveform AND eegWaveform

Look at lines 133 and 237:
```typescript
if (waveformData.ecgWaveform) {  // Line 133 - ALWAYS process if present
  // ... write to buffers 0-11
}

if (waveformData.eegWaveform) {  // Line 237 - ALWAYS process if present
  // ... write to buffers 12-21
}
```

**Key word: "ALWAYS process if present"**

This means:
- If ESP32 sends BOTH `ecgWaveform` AND `eegWaveform` in same message
- Both will be written to buffers
- Frontend switches mode based on `waveformData.mode`
- But data exists in BOTH buffer ranges

**This could happen if:**
- ESP32 simulator generates both ECG and EEG simultaneously
- Mode detection only looks at GPIO pin
- But simulator always runs both generators

---

## Next Steps - Debugging

I need to check the ESP32 code to see if it sends:
1. Only `ecgWaveform` when in ECG mode
2. Only `eegWaveform` when in EEG mode
3. OR both simultaneously?

Let me also add better logging to see what's actually in the WebSocket messages.

---

**STATUS: DIAGNOSIS IN PROGRESS**
