# Why Lead I & II Are Smooth But V1-V6 Are Jumpy - DIAGNOSIS

**Date:** 2025-11-03
**User Report:** "Lead 1 & 2 I don't have troubles, only with V leads"

---

## KEY FINDING

**The code treats ALL leads identically** - same buffer management, same rendering, same data source.

**But user sees Lead I & II smooth, V1-V6 jumpy during batch uploads.**

---

## Hypothesis: It's a VISUAL PERCEPTION Issue

### Why Lead I & II Might APPEAR Smooth:

**Lead I & II are the FIRST TWO leads processed and displayed:**

**Buffer indices:**
- Lead I: `dataBufferRef.current[0]`  ← Processed FIRST
- Lead II: `dataBufferRef.current[1]`  ← Processed SECOND
- Lead III: `dataBufferRef.current[2]`
- aVR: `dataBufferRef.current[3]`
- aVL: `dataBufferRef.current[4]`
- aVF: `dataBufferRef.current[5]`
- **V1**: `dataBufferRef.current[6]`  ← Processed 7th
- **V2**: `dataBufferRef.current[7]`  ← Processed 8th
- **V3**: `dataBufferRef.current[8]`  ← Processed 9th
- **V4**: `dataBufferRef.current[9]`  ← Processed 10th
- **V5**: `dataBufferRef.current[10]` ← Processed 11th
- **V6**: `dataBufferRef.current[11]` ← Processed 12th (LAST)

### Processing Order During Batch Upload:

**File:** [useECGViewer.ts:128-179](hospital-display-app/src/hooks/useECGViewer.ts#L128-L179)

```typescript
// Limb leads processed FIRST (indices 0-2)
if (limb?.leadI) {
  const samples = getData(limb.leadI);
  dataBufferRef.current[0] = [...dataBufferRef.current[0], ...samples].slice(-maxBufferSize);
}
if (limb?.leadII) {
  const samples = getData(limb.leadII);
  dataBufferRef.current[1] = [...dataBufferRef.current[1], ...samples].slice(-maxBufferSize);
}

// ... derived leads processed 3rd-6th ...

// Precordial leads processed LAST (indices 6-11)
if (precordial?.v1) {
  const samples = getData(precordial.v1);
  dataBufferRef.current[6] = [...dataBufferRef.current[6], ...samples].slice(-maxBufferSize);
}
// ... V2-V6 ...
```

### What Happens During Batch Upload (18 messages):

**Each MQTT message contains ALL 12 leads together.**

But processing takes TIME:
1. Decode delta encoding (50 samples × 12 leads = 600 decodings)
2. Append to buffers (12 array spreads)
3. Slice to max size (12 array slices)

**Total time per message:** ~2-5ms on fast machine, ~10-20ms on slow machine

**18 messages × 10ms = 180ms of rapid processing**

### Visual Effect:

**Lead I & II (processed first):**
- Get updated early in each batch message
- Canvas renders them smoothly because updates are spread out by natural processing time
- **APPEAR SMOOTH**

**V1-V6 (processed last):**
- Get updated late in each batch message
- All 6 V-leads update almost simultaneously (within 1-2ms of each other)
- Canvas sees rapid bursts of updates for V-leads
- **APPEAR JUMPY/RAPID**

---

## Alternative Hypothesis: Array Spread Performance

```typescript
dataBufferRef.current[0] = [...dataBufferRef.current[0], ...samples].slice(-maxBufferSize);
```

**This is EXPENSIVE when buffer is large:**
- Buffer size: ~5,000 samples (10 seconds at 500Hz)
- Spread creates NEW array of 5,050 elements
- Slice creates ANOTHER new array of 5,000 elements
- **Two array allocations per lead per message**
- **24 array allocations per message (12 leads × 2)**
- **432 array allocations for 18-message batch**

**Cumulative effect:**
- Lead I & II: Processed early, garbage collector hasn't kicked in yet → SMOOTH
- V1-V6: Processed late, memory pressure builds up, GC might pause → JUMPY

---

## Real Solution: Fix the Batch Upload Issue

**The ROOT problem is batch uploading 18 messages rapidly.**

### Option 1: Disable Waveform Queueing (Recommended)

**Why:** Real-time waveforms shouldn't be queued - they're stale by the time they're replayed.

**Fix ESP32:**
```cpp
// ❌ BEFORE
if (!mqttClient.connected() || !isAssigned) {
  offlineQueue.saveWaveform(payload);
  return;
}

// ✅ AFTER
if (!mqttClient.connected() || !isAssigned) {
  // Drop waveforms - real-time only
  Serial.println("⚠️  Dropping waveform (real-time only)");
  return;
}
```

**And disable batch processing:**
```cpp
// ❌ BEFORE
sendBatch("/queue/waveforms", "hospital/devices/" + deviceId + "/stream");

// ✅ AFTER (comment out)
// sendBatch("/queue/waveforms", ...); // Real-time only
```

### Option 2: Optimize Frontend Buffer Updates

**Replace expensive array spread with efficient push:**

```typescript
// ❌ BEFORE (expensive - creates 2 new arrays)
dataBufferRef.current[0] = [...dataBufferRef.current[0], ...samples].slice(-maxBufferSize);

// ✅ AFTER (efficient - in-place updates)
const buffer = dataBufferRef.current[leadIdx];
buffer.push(...samples);
if (buffer.length > maxBufferSize) {
  buffer.splice(0, buffer.length - maxBufferSize); // Remove old samples
}
```

But this won't solve the batch upload problem - just make it slightly less visible.

---

## Recommended Fix Order

### 1. **Fix Derived Lead Calculations (Critical Bug)**

**File:** [esp32_hospital_watch_complete.ino:1988-1990](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1988-L1990)

```cpp
// ❌ CURRENT (WRONG)
avlArray[i] = ch0 - ch1 / 2;     // Wrong order of operations
avfArray[i] = ch1 - ch0 / 2;     // Wrong order of operations

// ✅ FIXED
avlArray[i] = (ch0 * 2 - ch1) / 2;  // aVL = (2I - II) / 2
avfArray[i] = (ch1 * 2 - ch0) / 2;  // aVF = (2II - I) / 2
```

### 2. **Disable Waveform Queueing (Fixes Rapid Updates)**

**ESP32 firmware - two places:**
1. Don't save waveforms when offline (drop them)
2. Don't batch-process waveforms queue (comment out)

### 3. **Optional: Optimize Frontend (Minor Improvement)**

Replace array spread with in-place push/splice for better performance.

---

## Why You Don't See Issue with Lead I & II

**My best guess:**

1. **Processing order** - Lead I & II get updated first, so they have micro-delays between updates during batch processing
2. **Visual position** - Lead I & II are usually displayed at top of screen, V-leads at bottom - maybe you're focusing on V-leads more
3. **Amplitude differences** - After our ECG fix, V1-V6 have VERY different amplitudes (V1 has deep S wave, V4 has tall R) - this makes any jitter MORE VISIBLE

**But the real issue is batch uploading 18 messages.**

---

## Next Steps

**Please confirm:**

1. **Do you want me to:**
   - Fix derived lead calculations? (YES - this is a bug)
   - Disable waveform queueing? (YES - fixes rapid updates)
   - Optimize frontend buffers? (OPTIONAL - minor improvement)

2. **Can you test if disabling batch upload fixes the V-lead issue?**
   - Temporarily comment out line 276 in ESP32 firmware
   - Flash and test
   - See if V-leads become smooth

---

**Status:** Ready to implement all 3 fixes if approved.
