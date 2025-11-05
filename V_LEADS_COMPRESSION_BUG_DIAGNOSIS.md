# V-Leads Horizontal Compression Bug - REAL ISSUE

**Date:** 2025-11-03
**Issue:** Lead I & II render correctly (wide, proper spacing), but V1-V6 are horizontally compressed (multiple heartbeats squeezed together)

---

## Evidence from Screenshot

**Lead I & Lead II:**
- ✅ ~3-4 heartbeats visible across the canvas
- ✅ Proper horizontal spacing
- ✅ Clear PQRST complexes
- ✅ Normal ECG appearance

**V1, V2, V3, V4, V5, V6:**
- ❌ 8-10 heartbeats squeezed into same canvas width
- ❌ Horizontally compressed (2-3× more beats than Lead I/II)
- ❌ PQRST complexes bunched together
- ❌ Looks like 2× or 3× speed playback

**Lead III, aVR, aVL, aVF:**
- ❌ Appear flat/empty (different issue - possibly missing data)

---

## This is NOT a Canvas Width Issue

**All canvases are 314px wide** (confirmed by console logs), but:
- Lead I shows ~4 heartbeats in 314px ✅
- V1-V6 show ~10 heartbeats in 314px ❌

**This means V-leads have MORE DATA POINTS** than Lead I/II for the same time period.

---

## Possible Root Causes

### Hypothesis 1: V-Leads Receiving Duplicate Data

**Problem:** V-leads may be receiving data multiple times per WebSocket message.

**Check:**
- Are V-leads being processed multiple times in the WebSocket handler?
- Is the batch upload issue causing V-leads to accumulate data faster?

**Evidence needed:**
- Console log showing buffer lengths for each lead
- Check if `dataBufferRef.current[6-11]` (V-leads) have more samples than `dataBufferRef.current[0-1]` (Lead I/II)

---

### Hypothesis 2: Sample Rate Mismatch

**Problem:** V-leads may be sampled at a different rate than Lead I/II.

**From ESP32 firmware:**
- All leads should be sampled at **500 Hz** from ADS1298
- But if V-leads are somehow getting extra samples...

**Check:**
- ESP32 code: Does `waveformAccumulator` treat all 8 channels equally?
- Are V-leads (indices 2-7) being added to accumulator more frequently?

---

### Hypothesis 3: Delta Encoding Bug

**Problem:** Delta decoding may be producing different sample counts for V-leads.

**From `decodeDeltaChannel()`:**
```typescript
// Delta format: {baseline: number, deltas: number[]}
// Reconstructs: [baseline, baseline+deltas[0], baseline+deltas[0]+deltas[1], ...]
```

**If V-leads have more deltas** → more samples → horizontal compression

**Check:**
- Do V-lead delta arrays have more elements than Lead I/II?
- Is ESP32 sending different delta counts per lead?

---

### Hypothesis 4: Buffer Overflow for V-Leads

**Problem:** V-leads may be accumulating samples without proper `slice()` limiting.

**From code (line 158):**
```typescript
dataBufferRef.current[6] = [...dataBufferRef.current[6], ...samples].slice(-maxBufferSize);
```

**If `slice()` isn't working** → buffer grows indefinitely → more samples rendered → compression

**But this should affect all leads equally...**

---

## Diagnostic Steps

### Step 1: Log Buffer Lengths

**Add console log after processing each lead:**

```typescript
// After line 179 in useECGViewer.ts
console.log('📊 Buffer lengths:', {
  leadI: dataBufferRef.current[0]?.length || 0,
  leadII: dataBufferRef.current[1]?.length || 0,
  v1: dataBufferRef.current[6]?.length || 0,
  v2: dataBufferRef.current[7]?.length || 0,
  v3: dataBufferRef.current[8]?.length || 0,
  v4: dataBufferRef.current[9]?.length || 0,
  v5: dataBufferRef.current[10]?.length || 0,
  v6: dataBufferRef.current[11]?.length || 0,
});
```

**Expected:** All buffers should have ~12500 samples (25 seconds × 500 Hz)
**If V-leads have MORE:** Found the root cause

---

### Step 2: Log Incoming Sample Counts

**Add console log in WebSocket handler:**

```typescript
// After line 157 in useECGViewer.ts
if (precordial?.v1) {
  const samples = getData(precordial.v1);
  console.log(`V1 received ${samples.length} samples`);
  dataBufferRef.current[6] = [...dataBufferRef.current[6], ...samples].slice(-maxBufferSize);
}
```

**Expected:** All leads receive 50 samples per message (100ms × 500Hz)
**If V-leads receive MORE:** Found the root cause

---

### Step 3: Check ESP32 Data Generation

**Read ESP32 firmware line 1974-1996:**

```cpp
// Lines 1974-1996: Add precordial leads to JSON
addDeltaEncodedChannel(precordial, "v1", waveformAccumulator[2], 50);
addDeltaEncodedChannel(precordial, "v2", waveformAccumulator[3], 50);
addDeltaEncodedChannel(precordial, "v3", waveformAccumulator[4], 50);
addDeltaEncodedChannel(precordial, "v4", waveformAccumulator[5], 50);
addDeltaEncodedChannel(precordial, "v5", waveformAccumulator[6], 50);
```

**Check:**
- Is `waveformAccumulator[2-6]` being filled correctly?
- Are V-leads using the correct array indices?
- Is `addDeltaEncodedChannel()` creating more deltas for V-leads?

---

### Step 4: Check Rendering Code

**The rendering treats all leads identically:**

```typescript
// From ECGWaveformCanvas.tsx:104-106
const pixelsPerSecond = mmToPixels(PAPER_SPEED_MM_PER_S);
const pixelsPerSample = pixelsPerSecond / SAMPLE_RATE_HZ;
const samplesVisible = Math.floor(width / pixelsPerSample);
```

**This is the same for all leads**, so if V-leads look compressed, they MUST have more data points.

---

## Most Likely Root Cause

Based on the screenshot, **V-leads have 2-3× more data points** than Lead I/II.

**Two possible sources:**

1. **ESP32 is sending more samples for V-leads** (unlikely - all channels sampled simultaneously from ADS1298)

2. **Frontend is accumulating V-lead data faster** (more likely - batch upload issue from [WHY_BATCH_HAPPENS_ROOT_CAUSE.md](WHY_BATCH_HAPPENS_ROOT_CAUSE.md))

**Recall:** You mentioned V-leads look "jumpy" during batch uploads. This suggests:
- During batch upload (18 messages in 90ms), V-leads receive ALL 18 batches
- But Lead I/II somehow skip or drop some batches?
- Result: V-leads accumulate 18 × 50 = 900 extra samples
- This would explain the 2-3× compression

---

## Immediate Test

**Open browser console and type:**
```javascript
// Check buffer lengths
console.log('Lead I length:', dataBufferRef.current[0].length);
console.log('Lead II length:', dataBufferRef.current[1].length);
console.log('V1 length:', dataBufferRef.current[6].length);
console.log('V2 length:', dataBufferRef.current[7].length);
```

**If V1-V6 have significantly more samples than Lead I/II**, we've found the bug.

---

## Next Steps

Please provide the buffer lengths from the console so I can confirm the root cause and implement the fix.
