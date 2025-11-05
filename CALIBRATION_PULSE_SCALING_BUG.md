# CRITICAL BUG: Calibration Pulse Wrong Size in Single-Lead View

## User Report

**Observed:** Calibration pulse is **6 big squares tall × 17 big squares wide**
**Expected:** Should be **2 big squares tall × 1 big square wide**

**View:** Single-lead fullscreen ECG viewer

---

## Root Cause Analysis

### Problem 1: Grid and Waveform Use Different Scales ❌

**Grid rendering:** [medicalWaveformUtils.ts:416-423](hospital-display-app/src/utils/medicalWaveformUtils.ts#L416-L423)
```typescript
const smallGridSpacing = mmToPixels(1); // Uses DPI detection
const largeGridSpacing = mmToPixels(5); // Uses DPI detection
```

**Waveform rendering:** [medicalWaveformUtils.ts:336-339](hospital-display-app/src/utils/medicalWaveformUtils.ts#L336-L339)
```typescript
// ECG: 10mm/mV standard → ±2mV visible range
const mvRange = 4; // -2mV to +2mV (covers normal QRS)
const pixelsPerUnit = height / mvRange; // ❌ IGNORES GRID SPACING!
```

**The bug:**
- Grid says: "1mm = `mmToPixels(1)` pixels" (uses DPI)
- Waveform says: "1mV = `height / 4` pixels" (ignores DPI, just divides canvas)

**These are completely independent calculations!**

---

## Problem 2: Vertical Scale Doesn't Match Grid

### Medical Standard:
- **1mV = 10mm** (vertical scale)
- If grid has 5mm big squares, then **1mV = 2 big squares**

### Current Code:
```typescript
const mvRange = 4; // ±2mV total range
const pixelsPerUnit = height / mvRange; // pixels per mV
```

**Example with user's display:**
- Canvas height: 600 pixels (assumed)
- `pixelsPerUnit = 600 / 4 = 150 pixels per mV`
- Grid big square: `mmToPixels(5)` = ~25 pixels (at user's zoom/DPI)
- **Calibration pulse:** 150 pixels tall = 150 / 25 = **6 big squares** ❌
- **Should be:** `mmToPixels(10)` = ~50 pixels = 50 / 25 = **2 big squares** ✅

---

## Problem 3: Horizontal Scale Stretches to Fill Width

### Current Code: [medicalWaveformUtils.ts:359-367](hospital-display-app/src/utils/medicalWaveformUtils.ts#L359-L367)

```typescript
const desiredSecondsVisible = 8; // 8 seconds time window
const sampleRateHz = 500;
const desiredSamples = 8 * 500 = 4000; // 4000 samples
const samplesToRender = data.slice(-Math.min(desiredSamples, data.length));
const pixelsPerSample = width / samplesToRender.length; // ❌ STRETCHES!
```

**Example in single-lead view:**
- Canvas width: 1600 pixels (wide fullscreen canvas)
- Only 200 samples in buffer (calibration pulse: 100 spacer + 100 pulse)
- `pixelsPerSample = 1600 / 200 = 8 pixels per sample`
- Calibration pulse width: 100 samples × 8 = **800 pixels**
- Grid big square: ~47 pixels (at user's zoom/DPI)
- **800 / 47 = 17 big squares wide** ❌

**Should be:**
- 100 samples at 500 Hz = 0.2 seconds
- 0.2 seconds at 25mm/s paper speed = 5mm
- 5mm = 1 big square ✅

---

## Why This Happens

### The Fatal Flaw:

The waveform rendering function **completely ignores the medical grid spacing**.

**Grid:** Uses `mmToPixels()` to convert physical mm → screen pixels based on DPI
**Waveform:** Just divides canvas dimensions by arbitrary ranges (4mV, 8 seconds, sample count)

**Result:** Grid and waveform scales are **completely unrelated** and almost always mismatched!

---

## Correct Implementation

### Vertical Scale (Amplitude):

**Wrong (current):**
```typescript
const pixelsPerMV = height / 4; // Ignores grid!
```

**Right (should be):**
```typescript
const pixelsPerMV = mmToPixels(10); // 10mm = 1mV (uses same DPI as grid)
```

**Then calculate required canvas height:**
```typescript
const mvRange = 4; // ±2mV visible range
const requiredHeight = mvRange * mmToPixels(10); // Height needed for ±2mV at correct scale
```

**This ensures:** 1mV waveform always matches grid scale (10mm = 2 big squares)

### Horizontal Scale (Time):

**Wrong (current):**
```typescript
const pixelsPerSample = width / samplesToRender.length; // Stretches to fill!
```

**Right (should be):**
```typescript
const pixelsPerSecond = mmToPixels(PAPER_SPEED_MM_PER_S); // 25mm/s at detected DPI
const pixelsPerSample = pixelsPerSecond / SAMPLE_RATE_HZ; // 25mm/s ÷ 500Hz
```

**This ensures:** Time axis matches grid spacing (1 big square = 200ms at 25mm/s)

---

## Impact

### Medical Consequences:

**Current behavior:**
- ❌ Doctor measures QRS as 6 big squares = 30mm = 3mV (WRONG!)
- ❌ Actual QRS: 1mV calibration pulse appearing as 6 squares
- ❌ **3x amplification error** in amplitude measurements
- ❌ Could lead to false LVH (Left Ventricular Hypertrophy) diagnosis
- ❌ ST elevation measurements completely wrong (STEMI missed or over-diagnosed)

**On different displays:**
- The error factor changes with screen size, DPI, zoom level
- No consistency between devices
- **Medically unusable for amplitude-dependent diagnosis**

---

## Testing Evidence

### User's Observation:
- Calibration pulse: 6 squares tall × 17 squares wide
- Should be: 2 squares tall × 1 square wide

**Vertical error:** 6 / 2 = **3x too tall**
**Horizontal error:** 17 / 1 = **17x too wide**

### Calculated Error Factors:

**Vertical:**
- Current: `height / 4` (canvas-relative)
- Correct: `mmToPixels(10)` (DPI-relative)
- If canvas height = 600px and mmToPixels(10) = 50px:
  - Current: 600 / 4 = 150 pixels per mV
  - Correct: 50 pixels per mV
  - **Error: 3x** ✅ Matches user observation!

**Horizontal:**
- Current: Stretches 200 samples to fill 1600px width = 8 px/sample
- Correct: mmToPixels(25) / 500 = ~0.2 px/sample (at 96 DPI)
- **Error: 40x** (but limited by buffer size to ~17x in practice)

---

## Solution

### Step 1: Fix Vertical Scale

**File:** [medicalWaveformUtils.ts:334-344](hospital-display-app/src/utils/medicalWaveformUtils.ts#L334-L344)

```typescript
// BEFORE (WRONG):
if (useFixedScale) {
  if (isECGMode) {
    const mvRange = 4;
    pixelsPerUnit = height / mvRange; // ❌ Ignores grid!
  }
}

// AFTER (CORRECT):
if (useFixedScale) {
  if (isECGMode) {
    // Use SAME scale as grid: 10mm = 1mV
    pixelsPerUnit = mmToPixels(ECG_SCALE_MM_PER_MV); // ✅ Matches grid!
  }
}
```

### Step 2: Fix Horizontal Scale

**File:** [medicalWaveformUtils.ts:356-367](hospital-display-app/src/utils/medicalWaveformUtils.ts#L356-L367)

```typescript
// BEFORE (WRONG):
const desiredSecondsVisible = 8;
const sampleRateHz = 500;
const desiredSamples = desiredSecondsVisible * sampleRateHz;
const samplesToRender = data.slice(-Math.min(desiredSamples, data.length));
const pixelsPerSample = width / samplesToRender.length; // ❌ Stretches!

// AFTER (CORRECT):
// Use SAME scale as grid: 25mm/s paper speed
const pixelsPerSecond = mmToPixels(PAPER_SPEED_MM_PER_S); // 25mm/s at detected DPI
const pixelsPerSample = pixelsPerSecond / SAMPLE_RATE_HZ; // Fixed: 0.05mm per sample at 500Hz

// Calculate how many samples fit on canvas at this fixed scale
const secondsVisible = width / pixelsPerSecond; // Variable time window based on canvas width
const samplesToRender = data.slice(-(secondsVisible * SAMPLE_RATE_HZ));
```

### Step 3: Handle Canvas Size Properly

**Current problem:** Canvas might be too small to show ±2mV at correct scale

**Solution:** Either:
1. Make canvas taller to fit ±2mV range at correct scale
2. Show smaller mV range (e.g., ±1mV) on small canvases
3. Add scrolling for amplitude if needed

---

## Implementation Priority

**CRITICAL - Must fix before any clinical use:**

1. ✅ Fix vertical scale (amplitude) - HIGHEST PRIORITY
2. ✅ Fix horizontal scale (time) - HIGHEST PRIORITY
3. ⚠️ Handle canvas sizing - MEDIUM PRIORITY
4. ⚠️ Test on multiple displays/zooms - HIGH PRIORITY

**Why critical:**
- Current system gives **medically inaccurate measurements**
- Could lead to **misdiagnosis** (LVH, STEMI, low voltage QRS)
- Scale varies **unpredictably** with screen size and zoom
- **Not suitable for clinical use** in current state

---

## Verification Test

### After fixing, verify:

1. ✅ Calibration pulse is exactly 2 big squares tall
2. ✅ Calibration pulse is exactly 1 big square wide
3. ✅ Works on different screen sizes (laptop, desktop, 4K)
4. ✅ Works at different zoom levels (if we fix zoom issue)
5. ✅ QRS complex measured on grid matches actual mV value
6. ✅ Time intervals measured on grid match actual duration

---

## Conclusion

**Current state:**
- ❌ Grid and waveform use completely different scales
- ❌ Calibration pulse appears as 6×17 squares instead of 2×1
- ❌ **Medically unusable** for amplitude measurements

**Required fix:**
- ✅ Use `mmToPixels()` for both grid AND waveform scaling
- ✅ Vertical: `pixelsPerMV = mmToPixels(10)` (matches medical standard)
- ✅ Horizontal: `pixelsPerSample = mmToPixels(25) / 500` (matches 25mm/s paper speed)

**Estimated fix time:** 2-3 hours (code changes + testing on multiple displays)

---

**Reference Files:**
- Waveform rendering: [medicalWaveformUtils.ts:318-397](hospital-display-app/src/utils/medicalWaveformUtils.ts#L318-L397)
- Grid rendering: [medicalWaveformUtils.ts:408-472](hospital-display-app/src/utils/medicalWaveformUtils.ts#L408-L472)
- Canvas component: [ECGWaveformCanvas.tsx:52-127](hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx#L52-L127)
