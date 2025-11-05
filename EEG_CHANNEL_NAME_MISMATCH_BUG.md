# EEG Channel Name Mismatch Bug - ROOT CAUSE FOUND

**Date:** 2025-11-04
**Status:** ROOT CAUSE IDENTIFIED
**Severity:** CRITICAL - EEG mode completely non-functional

---

## Problem Summary

**Symptoms:**
- ESP32 sends EEG waveform data ✅
- Backend processes and forwards EEG data ✅
- Frontend stores data in buffer indices 12-21 ✅
- Frontend canvas shows `dataLength=0` (no data) ❌

**Root Cause:**
**CHANNEL NAME MISMATCH** - The frontend `eegLeads` array doesn't match the actual channel names being stored in buffers!

---

## The Mismatch

### What Frontend EXPECTS (eegLeads array):
```typescript
// Line 34 in useECGViewer.ts
const eegLeads = ['F3-C3', 'F4-C4', 'C3-P3', 'C4-P4', 'P3-O1', 'P4-O2', 'F7-T3', 'F8-T4', 'T5-O1'];
```

These are **bipolar derivations** (difference between two electrodes).

### What Frontend ACTUALLY STORES (buffer indices 12-21):
```typescript
// Lines 237-284 in useECGViewer.ts
dataBufferRef.current[12] = Fp1  // Frontal pole 1
dataBufferRef.current[13] = Fp2  // Frontal pole 2
dataBufferRef.current[14] = F3   // Frontal left
dataBufferRef.current[15] = F4   // Frontal right
dataBufferRef.current[16] = C3   // Central left
dataBufferRef.current[17] = C4   // Central right
dataBufferRef.current[18] = T3   // Temporal left (optional)
dataBufferRef.current[19] = T4   // Temporal right (optional)
dataBufferRef.current[20] = O1   // Occipital left
dataBufferRef.current[21] = O2   // Occipital right
```

These are **raw monopolar channels** (single electrode referenced to common).

### What ESP32/Backend SENDS:
```json
{
  "eegWaveform": {
    "frontal": {"Fp1": {...}, "Fp2": {...}, "F3": {...}, "F4": {...}},
    "central": {"C3": {...}, "C4": {...}},
    "occipital": {"O1": {...}, "O2": {...}}
  }
}
```

**8 raw channels** (not 9 bipolar derivations!)

---

## Why This Causes Blank Canvas

1. **Display Grid** creates canvas components for leads 0-8 based on `eegLeads` array
2. **Lead names** shown: 'F3-C3', 'F4-C4', 'C3-P3', etc. ✅
3. **Buffer index fix** correctly maps display index to buffer index +12 ✅
4. **But... the buffers are EMPTY!** ❌

Why empty? Because the code that **stores** the data uses channel names from the WebSocket message:

```typescript
// Line 237: Looks for frontal.Fp1
if (frontal?.Fp1) {
  const samples = getData(frontal.Fp1);
  dataBufferRef.current[12] = [...dataBufferRef.current[12], ...samples].slice(-maxBufferSize);
}
```

This works! Data IS being stored in buffer[12].

**BUT** the canvas is looking for a lead named "F3-C3" which doesn't exist in the leads array position mapping!

Wait... let me re-examine...

Actually, looking closer:

```typescript
// Line 76-78 in ECGDisplayGrid.tsx
const visibleLeads = Array.from({ length: Math.min(layout, leads.length) }, (_, i) => i);
// For 9-lead layout, creates [0, 1, 2, 3, 4, 5, 6, 7, 8]
```

Then:
```typescript
// Line 124
const bufferIdx = getBufferIndex(leadIdx); // leadIdx=0 → bufferIdx=12
```

So canvas[0] → buffer[12] = Fp1... but the lead NAME shown is `leads[0]` = "F3-C3"

**The visual labels are wrong, but that shouldn't affect data display!**

Let me check if there's a missing `temporal` field...

---

## Wait - Checking Actual Data Structure

Looking at backend (websocket_manager.py lines 411-432):

**Frontal channels:** Fp1, Fp2, F3, F4 (4 channels)
**Central channels:** C3, C4 (2 channels)
**Occipital channels:** O1, O2 (2 channels)
**Total:** 8 channels

But the frontend code (lines 266-273) also looks for **temporal.T3 and temporal.T4**!

```typescript
// Temporal channels (T3, T4) - OPTIONAL
if (temporal?.T3) {
  const samples = getData(temporal.T3);
  dataBufferRef.current[18] = [...dataBufferRef.current[18], ...samples].slice(-maxBufferSize);
}
```

**Does the backend send `temporal` field?**

NO! Looking at the backend code, there's NO temporal field in the WebSocket message!

---

## The REAL Problem

The frontend expects:
- `frontal`: Fp1, Fp2, F3, F4 (buffers 12-15) ✅
- `central`: C3, C4 (buffers 16-17) ✅
- `temporal`: T3, T4 (buffers 18-19) ❌ **NOT SENT BY BACKEND**
- `occipital`: O1, O2 (buffers 20-21) ✅

**Backend only sends:** frontal + central + occipital = 8 channels
**Frontend stores:** 8 channels but in indices 12-21 (expects 10 channels!)

---

## Solution

**Option 1:** Update `eegLeads` array to match actual 8 channels:
```typescript
const eegLeads = ['Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4', 'O1', 'O2'];
```

**Option 2:** Remove temporal field handling (it's never used)

**Option 3:** Add temporal field to backend (but ESP32 doesn't send it)

**RECOMMENDED: Option 1** - Update frontend to match the 8-channel reality

---

## Fix Plan

1. **Update `eegLeads` array** in [useECGViewer.ts:34](hospital-display-app/src/hooks/useECGViewer.ts#L34)
   ```typescript
   const eegLeads = ['Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4', 'O1', 'O2'];
   ```

2. **Remove temporal field handling** (lines 266-273) - it's dead code

3. **Update buffer storage** to use indices 12-19 instead of 12-21:
   - Fp1 → 12
   - Fp2 → 13
   - F3 → 14
   - F4 → 15
   - C3 → 16
   - C4 → 17
   - O1 → 18
   - O2 → 19

4. **Update `getBufferIndex`** offset to still work correctly

---

## Testing After Fix

1. Restart ESP32 in EEG mode
2. Open ECG viewer
3. Verify 8 channels displayed: Fp1, Fp2, F3, F4, C3, C4, O1, O2
4. Verify waveforms appear (not blank baseline)
5. Check console for "✅ EEG waveform data processed - XXX samples in buffer"

---

## Files to Modify

| File | Lines | Change |
|------|-------|--------|
| `useECGViewer.ts` | 34 | Change eegLeads to 8 channels |
| `useECGViewer.ts` | 266-273 | Remove temporal field handling |
| `useECGViewer.ts` | 277-283 | Change O1/O2 buffer indices to 18-19 |

---

## Impact

- ✅ EEG mode will finally work
- ✅ Correct channel names displayed
- ✅ 8-lead layout instead of 9-lead
- ⚠️ Users will see raw channels, not bipolar derivations (but that's what ESP32 actually sends)
