# Horizontal Compression Diagnosis - Waveforms Look Squeezed

**Date:** 2025-11-03
**Issue:** Waveforms appear **horizontally compressed** (not amplitude/vertical issue)

---

## What You're Seeing

**NOT about height** - the vertical amplitude (QRS height, P wave height) is fine
**About horizontal spacing** - the waveform looks **squeezed left-to-right**, like watching a video at 2x speed

**Visual example:**
```
Normal ECG (25mm/s):          Compressed ECG (looks like 50mm/s):
   __                               __
  |  |__                           | |_
__|      |___                   ___|   |__
```

The PQRST complexes are **too close together horizontally**.

---

## Root Cause Analysis

Let me check the actual horizontal scaling calculations in the code:

### From ECGWaveformCanvas.tsx (Lines 104-106)

```typescript
const pixelsPerSecond = mmToPixels(PAPER_SPEED_MM_PER_S); // 25mm/s at detected DPI
const pixelsPerSample = pixelsPerSecond / SAMPLE_RATE_HZ; // Fixed: 25mm/s ÷ 500Hz
const samplesVisible = Math.floor(width / pixelsPerSample);
```

**This is CORRECT** - using medical-grade 25mm/s paper speed.

---

### Actual Calculations (Let's Do The Math)

**Assume:**
- Screen DPI: 96 (standard)
- Canvas width: 1200px (typical)
- Sample rate: 500 Hz
- Paper speed: 25mm/s

**Step 1: Calculate pixelsPerSecond**
```typescript
pixelsPerSecond = mmToPixels(25)  // 25mm at 96 DPI
                = (25 / 25.4) * 96
                = 94.49 pixels/second
```

**Step 2: Calculate pixelsPerSample**
```typescript
pixelsPerSample = 94.49 / 500
                = 0.189 pixels/sample
```

**Step 3: Calculate samplesVisible**
```typescript
samplesVisible = Math.floor(1200 / 0.189)
               = Math.floor(6349)
               = 6349 samples visible
```

**Step 4: Convert to time duration**
```typescript
Time visible = 6349 samples / 500 Hz
             = 12.7 seconds
```

**This means your 1200px canvas should show 12.7 seconds of ECG data.**

---

## The Problem: Batch Upload May Be Duplicating Samples

**Hypothesis:** During batch upload, the frontend may be receiving **duplicate samples** or **re-processing old data**, causing the buffer to overfill.

### From useECGViewer.ts (Lines 128-179)

```typescript
// Lead I processing
if (limb?.leadI) {
  const samples = getData(limb.leadI);  // 50 new samples
  dataBufferRef.current[0] = [...dataBufferRef.current[0], ...samples].slice(-maxBufferSize);
}
```

**Each WebSocket message contains 50 samples** (100ms worth at 500Hz).

**Normal streaming:** 10 messages/second = 500 samples/second ✅
**During batch upload:** 18 messages in 90ms = 900 samples in 90ms ❌

---

## Diagnostic Test: Check Actual Sample Count

**What to check:**
1. Open browser console
2. Look for log: `[ECGWaveformCanvas] Phase 2 (Typewriter Scroll): showing last X samples of Y total`
3. Compare X (samples visible) vs Y (total samples in buffer)

**Expected:**
- `samplesVisible` should be ~6000-7000 (12-14 seconds at 500Hz)
- `data.length` should be exactly `maxBufferSize` (calculated from `BUFFER_TIME_SECONDS`)

**If you see:**
- `data.length` > `maxBufferSize` → Buffer overflow (slice not working)
- `samplesVisible` too large → Canvas width too big or pixelsPerSample too small
- `pixelsPerSample` < 0.15 → Waveform compressed horizontally

---

## Likely Causes

### Cause 1: Buffer Overflow During Batch Upload

**Problem:** `slice(-maxBufferSize)` may not execute fast enough during rapid batch uploads.

**Evidence needed:**
```typescript
// Line 130 in useECGViewer.ts
dataBufferRef.current[0] = [...dataBufferRef.current[0], ...samples].slice(-maxBufferSize);
```

**During batch upload (18 messages in 90ms):**
- Message 1: Add 50 samples → buffer = 50
- Message 2: Add 50 samples → buffer = 100
- ...
- Message 18: Add 50 samples → buffer = 900

**If React doesn't re-render fast enough, the spread operator creates new array 18 times:**
```typescript
[...oldArray, ...newSamples]  // Creates NEW array (slow!)
```

**This is expensive and may cause visual "compression" as too many samples try to fit on screen.**

---

### Cause 2: DPI Detection Issue

**Problem:** `getScreenDPI()` may be detecting incorrect DPI, making `pixelsPerSample` too small.

**Check browser console for:**
```
✅ DPI detected: 96 (cached for future use)
🔍 1mm = 3.78 pixels, 5mm big square = 18.90 pixels
```

**If DPI is wrong (e.g., detecting 192 DPI on a 96 DPI screen):**
```typescript
pixelsPerSecond = mmToPixels(25)  // Should be ~94 pixels
                = (25 / 25.4) * 192  // WRONG DPI
                = 188.98 pixels/second  // DOUBLE what it should be!

pixelsPerSample = 188.98 / 500
                = 0.378 pixels/sample  // DOUBLE what it should be!

samplesVisible = 1200 / 0.378
               = 3175 samples  // HALF the time visible
               = 6.35 seconds  // Too compressed!
```

---

### Cause 3: Canvas Width Calculation Wrong

**From ECGWaveformCanvas.tsx (Lines 82-84):**
```typescript
const width = canvas.clientWidth;
const height = canvas.clientHeight;
```

**If `canvas.clientWidth` is returning PHYSICAL pixels instead of CSS pixels:**
```typescript
// On a 2x Retina display:
canvas.clientWidth = 2400px  // PHYSICAL pixels (wrong!)
// Should be:
canvas.clientWidth = 1200px  // CSS pixels (correct)

// This makes samplesVisible DOUBLE:
samplesVisible = 2400 / 0.189 = 12700 samples = 25.4 seconds
// Waveform gets horizontally compressed to fit!
```

---

## Quick Diagnostic Steps

### Step 1: Check Console Logs

**Look for this log** (from line 110 in ECGWaveformCanvas.tsx):
```
🔍 [Lead II] DPI spacing: pixelsPerSecond=94.49, pixelsPerSample=0.189, samplesVisible=6349, canvas width=1200px
```

**What to check:**
1. `pixelsPerSecond` should be ~94-95 (for 96 DPI)
2. `pixelsPerSample` should be ~0.19 (for 500Hz at 25mm/s)
3. `samplesVisible` should be ~6000-7000 (for 12-14 second window)
4. `canvas width` should match your browser window width

---

### Step 2: Check Buffer Size

**Look for this log** (from line 168 in ECGWaveformCanvas.tsx):
```
[ECGWaveformCanvas] Phase 2 (Typewriter Scroll): showing last 6349 samples of 12500 total
```

**What to check:**
1. Total samples should equal `BUFFER_TIME_SECONDS * 500` (default: 25s × 500Hz = 12500)
2. If total samples > 12500 → buffer overflow during batch upload
3. If showing more than `samplesVisible` → rendering issue

---

### Step 3: Manually Test DPI Detection

**Open browser console and run:**
```javascript
// Test DPI detection
const div = document.createElement('div');
div.style.width = '1in';
div.style.position = 'absolute';
document.body.appendChild(div);
const dpi = div.offsetWidth;
document.body.removeChild(div);
console.log(`Detected DPI: ${dpi}`);
console.log(`Expected: 96 for standard display, 192 for Retina`);
```

---

## Potential Fixes

### Fix 1: Add Rate Limiting During Batch Upload

**Problem:** Spread operator is too slow during rapid updates.

**Solution:** Throttle buffer updates to max 60fps (16ms intervals).

**Location:** `hospital-display-app/src/hooks/useECGViewer.ts:128-179`

```typescript
// Add throttling
const lastUpdate = useRef(0);

// In WebSocket subscription:
const now = Date.now();
if (now - lastUpdate.current < 16) return; // 60fps max
lastUpdate.current = now;

// Then process data as normal...
```

---

### Fix 2: Use In-Place Array Modification (Faster)

**Problem:** `[...oldArray, ...newSamples].slice(-maxBufferSize)` creates new arrays.

**Solution:** Modify array in-place with `push()` and `splice()`.

**Location:** `hospital-display-app/src/hooks/useECGViewer.ts:130`

```typescript
// ❌ SLOW (creates 2 new arrays)
dataBufferRef.current[0] = [...dataBufferRef.current[0], ...samples].slice(-maxBufferSize);

// ✅ FAST (in-place modification)
dataBufferRef.current[0].push(...samples);
if (dataBufferRef.current[0].length > maxBufferSize) {
  dataBufferRef.current[0].splice(0, dataBufferRef.current[0].length - maxBufferSize);
}
```

---

### Fix 3: Force DPI to 96 (If Detection Is Wrong)

**Problem:** DPI detection may be returning wrong value for your display.

**Solution:** Hard-code DPI to 96 temporarily to test.

**Location:** `hospital-display-app/src/utils/medicalWaveformUtils.ts:45-79`

```typescript
export function getScreenDPI(): number {
  // TEMPORARY: Force 96 DPI to test if detection is wrong
  if (cachedDPI !== null) return cachedDPI;

  cachedDPI = 96;  // ← FORCE THIS
  console.log('🔧 DPI forced to 96 for testing');
  return 96;

  // Comment out original detection code...
}
```

---

### Fix 4: Implement Batch Upload Fix (From Previous Analysis)

**This is the ROOT CAUSE** - disable waveform queueing entirely.

**Location:** `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino:2030`

```cpp
// ❌ BEFORE
if (!mqttClient.connected() || !isAssigned) {
  offlineQueue.saveWaveform(payload);
  return;
}

// ✅ AFTER
if (!mqttClient.connected() || !isAssigned) {
  return;  // Drop waveforms when offline
}
```

**And comment out line 276:**
```cpp
// sendBatch("/queue/waveforms", "hospital/devices/" + deviceId + "/stream");
```

---

## Next Steps

**Please provide these diagnostic values from browser console:**

1. **DPI Detection:**
   ```
   ✅ DPI detected: ???
   🔍 1mm = ??? pixels, 5mm big square = ??? pixels
   ```

2. **Horizontal Spacing:**
   ```
   🔍 [Lead II] DPI spacing: pixelsPerSecond=???, pixelsPerSample=???, samplesVisible=???, canvas width=???px
   ```

3. **Buffer Status:**
   ```
   [ECGWaveformCanvas] Phase 2: showing last ??? samples of ??? total
   ```

4. **Is this happening:**
   - During batch upload (every 30 seconds)?
   - All the time (continuous)?
   - Only on specific leads (V1-V6)?

Once I have these values, I can pinpoint the exact root cause.
