# V-Leads Horizontal Compression - ACTUAL ROOT CAUSE (Research-Based)

**Date:** 2025-11-03
**Issue:** Lead I & II display normally, V1-V6 appear horizontally compressed (2-3× more heartbeats in same canvas width)

---

## What I Actually Researched

### ESP32 Firmware (Lines 1880-2016)
✅ **VERIFIED**: All 8 channels treated identically
- Line 1897: `simulator.fillSampleBuffer(microBatch)` - generates 10 samples for ALL 8 channels
- Lines 1900-1904: ALL 8 channels copied to accumulator identically
- Lines 1968-1978: ALL leads encoded with same `addDeltaEncodedChannel()` function, same count (50)

**CONCLUSION**: ESP32 sends IDENTICAL sample counts for all leads (50 samples per message).

---

### Frontend Code (useECGViewer.ts Lines 128-179)
✅ **VERIFIED**: All leads processed identically
- Lines 128-139: Lead I, II, III use same pattern
- Lines 156-179: V1-V6 use IDENTICAL pattern as Lead I/II
- All use: `getData()` → spread → slice(-maxBufferSize)

```typescript
// Lead I (line 130)
dataBufferRef.current[0] = [...dataBufferRef.current[0], ...samples].slice(-maxBufferSize);

// V1 (line 158) - IDENTICAL LOGIC
dataBufferRef.current[6] = [...dataBufferRef.current[6], ...samples].slice(-maxBufferSize);
```

**CONCLUSION**: Frontend treats all leads identically.

---

### Delta Decoding (medicalWaveformUtils.ts Lines 102-117)
✅ **VERIFIED**: Same decoding for all leads
```typescript
export function decodeDeltaChannel(deltaData: { baseline: number; deltas: number[] }): number[] {
  const samples: number[] = [deltaData.baseline];
  let currentValue = deltaData.baseline;
  for (const delta of deltaData.deltas) {
    currentValue += delta;
    samples.push(currentValue);
  }
  return samples;
}
```

**CONCLUSION**: Delta decoding produces samples.length = 1 + deltas.length. If deltas.length differs between leads, output differs.

---

## The REAL Questions (I Don't Have Answers Yet)

### Q1: Do V-leads have more deltas in their delta arrays?
**How to check**: Add logging to `getData()` in useECGViewer.ts:
```typescript
const getData = (leadData: any) => {
  if (!leadData) return [];
  if (leadData.baseline !== undefined && leadData.deltas !== undefined) {
    const decoded = decodeDeltaChannel(leadData);
    console.log(`📊 Delta decode: baseline=${leadData.baseline}, deltas=${leadData.deltas.length}, output=${decoded.length}`);
    return decoded;
  }
  if (Array.isArray(leadData)) {
    console.log(`📊 Raw array: length=${leadData.length}`);
    return leadData;
  }
  return [];
};
```

**If V-leads have more deltas** → more samples → horizontal compression ✅
**If all leads have same delta count** → bug is elsewhere ❌

---

### Q2: Are V-leads accumulating batch upload data differently?
**Hypothesis**: During batch upload (18 messages in 90ms), maybe:
- Lead I/II somehow skip some messages?
- V-leads process ALL 18 messages?
- Result: V-leads accumulate 18× more samples than Lead I/II?

**How to verify**: Add logging after each lead processes data:
```typescript
if (limb?.leadI) {
  const samples = getData(limb.leadI);
  dataBufferRef.current[0] = [...dataBufferRef.current[0], ...samples].slice(-maxBufferSize);
  console.log(`Lead I: +${samples.length} samples, total=${dataBufferRef.current[0].length}`);
}
// ... repeat for all leads
```

**Then check console during batch upload** - do all leads show same sample additions?

---

### Q3: Is the screenshot showing STALE DATA for V-leads?
**Hypothesis**: Maybe V-leads are displaying OLD buffered data that hasn't been cleared?

**Evidence needed**: Check if `dataBufferRef.current[6-11]` contains more samples than `dataBufferRef.current[0-1]`.

---

## What I CANNOT Determine Without More Data

1. **Actual buffer lengths** - Need console.log of `dataBufferRef.current[i].length` for each lead
2. **Incoming sample counts** - Need console.log of samples received per message per lead
3. **Delta array lengths** - Need console.log of `leadData.deltas.length` before decoding
4. **Batch upload timing** - Is this happening during batch upload or continuously?

---

## Proposed Diagnostic Plan (Requires Your Approval)

### Step 1: Add Buffer Length Logging
**File**: `hospital-display-app/src/hooks/useECGViewer.ts`
**Location**: After line 179 (after all leads processed)

```typescript
// Log buffer lengths every 10 messages
if (waveformData.sequence && waveformData.sequence % 10 === 0) {
  console.log('📊 Buffer lengths:', {
    leadI: dataBufferRef.current[0]?.length || 0,
    leadII: dataBufferRef.current[1]?.length || 0,
    v1: dataBufferRef.current[6]?.length || 0,
    v2: dataBufferRef.current[7]?.length || 0,
    v3: dataBufferRef.current[8]?.length || 0,
    v4: dataBufferRef.current[9]?.length || 0,
  });
}
```

---

### Step 2: Add Delta Decoding Logging
**File**: `hospital-display-app/src/hooks/useECGViewer.ts`
**Location**: Inside `getData()` helper (line 113-124)

```typescript
const getData = (leadData: any) => {
  if (!leadData) return [];
  if (leadData.baseline !== undefined && leadData.deltas !== undefined) {
    const decoded = decodeDeltaChannel(leadData);
    if (waveformData.sequence && waveformData.sequence % 10 === 0) {
      console.log(`  Delta: ${leadData.deltas.length} deltas → ${decoded.length} samples`);
    }
    return decoded;
  }
  if (Array.isArray(leadData)) {
    return leadData;
  }
  return [];
};
```

---

### Step 3: Add Per-Lead Sample Addition Logging
**File**: `hospital-display-app/src/hooks/useECGViewer.ts`
**Location**: After each lead processes (e.g., line 130)

```typescript
if (limb?.leadI) {
  const samples = getData(limb.leadI);
  const beforeLength = dataBufferRef.current[0].length;
  dataBufferRef.current[0] = [...dataBufferRef.current[0], ...samples].slice(-maxBufferSize);
  const afterLength = dataBufferRef.current[0].length;
  if (waveformData.sequence && waveformData.sequence % 10 === 0) {
    console.log(`  Lead I: +${samples.length} samples (${beforeLength} → ${afterLength})`);
  }
}
```

---

## Alternative Hypothesis: Frontend Bug in Rendering

**Maybe the BUFFERS are identical, but RENDERING is wrong?**

**Check**: ECGWaveformCanvas.tsx lines 104-106
```typescript
const pixelsPerSecond = mmToPixels(PAPER_SPEED_MM_PER_S);
const pixelsPerSample = pixelsPerSecond / SAMPLE_RATE_HZ;
const samplesVisible = Math.floor(width / pixelsPerSample);
```

**This is the SAME for all leads**, so if V-leads render compressed, they MUST have more data points in their buffers.

---

## What I Need From You

Please choose ONE:

**Option A**: Implement the diagnostic logging (Steps 1-3) so we can see actual data
**Option B**: Check browser console right now and tell me if you see any differences in buffer lengths
**Option C**: Tell me WHEN the compression happens (during batch upload only? or always?)

---

## My Honest Assessment

I **DO NOT KNOW** the root cause yet. I need actual runtime data to diagnose this properly. The code shows all leads are treated identically, so the difference must be in the DATA, not the LOGIC.

**Most likely causes** (ranked by probability):
1. **V-leads have more deltas in delta arrays** (ESP32 bug?)
2. **V-leads accumulate batch data differently** (timing bug?)
3. **V-leads have stale data not being cleared** (buffer management bug?)

I need your help to gather diagnostic data before I can propose a fix.
