# EEG Mode Buffer Index Bug

**Date:** 2025-11-04
**Issue:** Frontend displays blank canvases in EEG mode
**Root Cause:** Buffer index mismatch between ECG and EEG data storage
**Severity:** HIGH - EEG mode completely non-functional

---

## Problem Diagnosis

### Symptoms
1. **ESP32 is in EEG mode** - Serial output: `Mode=EEG` ✅
2. **Frontend detects EEG mode** - Auto-switches `isECGMode = false` ✅
3. **EEG waveform data arrives** - `Waveform stream: EEG` ✅
4. **Canvas shows blank baseline** - No waveforms displayed ❌

### Root Cause

**Buffer Index Mismatch:**

The `useECGViewer` hook stores ECG and EEG data in **different buffer indices**:

```typescript
// ECG uses buffer indices 0-11
dataBufferRef.current[0] = Lead I
dataBufferRef.current[1] = Lead II
...
dataBufferRef.current[11] = V6

// EEG uses buffer indices 12-21
dataBufferRef.current[12] = Fp1
dataBufferRef.current[13] = Fp2
...
dataBufferRef.current[21] = O2
```

**But the canvas component uses raw indices 0-8 regardless of mode:**

```typescript
// ECGDisplayGrid.tsx Line 78
const visibleLeads = Array.from({ length: Math.min(layout, leads.length) }, (_, i) => i);
// This creates [0, 1, 2, 3, 4, 5, 6, 7, 8] for 9-lead layout
```

**Result:**
- In EEG mode, canvas tries to read `dataBufferRef.current[0-8]`
- But EEG data is in `dataBufferRef.current[12-21]`
- Canvas gets empty ECG buffers → displays blank baseline

---

## Evidence from Logs

### ESP32 Output (CORRECT ✅)
```
📊 Vitals: Mode=EEG, HR=72, Temp=36.4°C, SpO2=97%, RR=13
📈 Waveform stream: EEG (seq: 10, size: 2144 bytes)
```

### Frontend Console (PROBLEM ❌)
```
[ECGWaveformCanvas 081a5294-da91-4c74-bb8a-e5062f5851dd Lead I] No data, drawing baseline
[ECGWaveformCanvas 081a5294-da91-4c74-bb8a-e5062f5851dd Lead II] No data, drawing baseline
[ECGWaveformCanvas 081a5294-da91-4c74-bb8a-e5062f5851dd Lead III] No data, drawing baseline
```

**Why "Lead I, Lead II, Lead III"?**
- Canvas component is using ECG lead names
- Should be using EEG channel names (Fp1, Fp2, F3, F4, etc.)

---

## Technical Analysis

### File: `hospital-display-app/src/hooks/useECGViewer.ts`

**Lines 33-35: Defines lead names**
```typescript
const ecgLeads = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6'];
const eegLeads = ['F3-C3', 'F4-C4', 'C3-P3', 'C4-P4', 'P3-O1', 'P4-O2', 'F7-T3', 'F8-T4', 'T5-O1'];
const leads = isECGMode ? ecgLeads : eegLeads;
```

**Lines 138-189: ECG data storage (indices 0-11)**
```typescript
dataBufferRef.current[0] = [...dataBufferRef.current[0], ...lead I samples]
dataBufferRef.current[1] = [...dataBufferRef.current[1], ...lead II samples]
...
dataBufferRef.current[11] = [...dataBufferRef.current[11], ...V6 samples]
```

**Lines 237-284: EEG data storage (indices 12-21)**
```typescript
dataBufferRef.current[12] = [...dataBufferRef.current[12], ...Fp1 samples]
dataBufferRef.current[13] = [...dataBufferRef.current[13], ...Fp2 samples]
...
dataBufferRef.current[21] = [...dataBufferRef.current[21], ...O2 samples]
```

### File: `hospital-display-app/src/components/ECGViewer/ECGDisplayGrid.tsx`

**Lines 76-78: Creates lead indices without offset**
```typescript
const visibleLeads = layout === 1
  ? [leads.findIndex((l) => l === selectedLead)]
  : Array.from({ length: Math.min(layout, leads.length) }, (_, i) => i);
// For 9-lead layout, this creates [0, 1, 2, 3, 4, 5, 6, 7, 8]
// But EEG data is in indices [12, 13, 14, 15, 16, 17, 18, 19, 20]!
```

**Line 116: Uses leadIdx directly**
```typescript
const lead = leads[leadIdx] || 'N/A';
```

**Line 126: Passes leadIdx to canvas**
```typescript
<ECGWaveformCanvas
  leadIdx={leadIdx}  // ❌ Wrong! Should be leadIdx + 12 for EEG mode
  leadName={lead}
  dataBufferRef={dataBufferRef}
  isECGMode={isECGMode}
  ...
/>
```

---

## Solution

### Option 1: Add Buffer Offset in ECGDisplayGrid (Recommended)

**File:** `hospital-display-app/src/components/ECGViewer/ECGDisplayGrid.tsx`

```typescript
// Line 76-78: Add buffer offset for EEG mode
const visibleLeads = layout === 1
  ? [leads.findIndex((l) => l === selectedLead)]
  : Array.from({ length: Math.min(layout, leads.length) }, (_, i) => i);

// ✅ NEW: Map display index to actual buffer index
const getBufferIndex = (displayIndex: number): number => {
  // EEG data is stored in buffer indices 12-21
  // ECG data is stored in buffer indices 0-11
  return isECGMode ? displayIndex : displayIndex + 12;
};
```

**Then update Line 126:**
```typescript
<ECGWaveformCanvas
  leadIdx={getBufferIndex(leadIdx)}  // ✅ Correct buffer index
  leadName={lead}
  dataBufferRef={dataBufferRef}
  isECGMode={isECGMode}
  ...
/>
```

### Option 2: Consolidate Buffer Storage (Better Long-Term)

**File:** `hospital-display-app/src/hooks/useECGViewer.ts`

**Change EEG to use indices 0-8 when in EEG mode:**

```typescript
// Lines 237-284: Store EEG in indices 0-8, not 12-21
if (frontal?.Fp1) {
  const samples = getData(frontal.Fp1);
  dataBufferRef.current[0] = [...dataBufferRef.current[0], ...samples].slice(-maxBufferSize);  // Was 12
}
if (frontal?.Fp2) {
  const samples = getData(frontal.Fp2);
  dataBufferRef.current[1] = [...dataBufferRef.current[1], ...samples].slice(-maxBufferSize);  // Was 13
}
// ... etc
```

**Pros:**
- Simpler logic - always use indices 0-N for current mode
- No offset calculations needed
- Clearer separation between modes

**Cons:**
- Can't display both ECG and EEG simultaneously (but we don't need to)

---

## Recommendation

**Use Option 1** (Add buffer offset) for now:
- Quick fix
- Minimal code changes
- Preserves current architecture

**Consider Option 2** for future refactoring:
- Cleaner long-term design
- Simplifies canvas rendering logic

---

## Testing Plan

### After Fix:

1. **Connect GPIO 4 to GND** (EEG mode)
2. **Restart ESP32**
3. **Open ECG viewer**
4. **Verify console output:**
   ```
   🔄 Auto-switching to EEG mode (detected from device)
   ✅ EEG waveform data processed - XXX samples in buffer
   ```
5. **Verify canvas displays:**
   - 8 EEG channels: Fp1, Fp2, F3, F4, C3, C4, O1, O2
   - Alpha/beta/theta/delta waveforms visible
   - No "No data, drawing baseline" messages

6. **Disconnect GPIO 4** (ECG mode)
7. **Restart ESP32**
8. **Verify ECG mode still works:**
   - 12 ECG leads displayed
   - PQRST waveforms visible

---

## Files to Modify

| File | Lines | Change |
|------|-------|--------|
| `ECGDisplayGrid.tsx` | 76-78, 126 | Add `getBufferIndex()` helper and use it for leadIdx |

---

## Impact Assessment

- **ECG mode:** No impact (still uses indices 0-11)
- **EEG mode:** **FIXES** blank canvas bug
- **Performance:** Negligible (simple addition operation)
- **Compatibility:** No breaking changes

---

## Status

**Current:** Bug identified, solution designed
**Next:** Implement fix in ECGDisplayGrid.tsx
**Testing:** Required after implementation
