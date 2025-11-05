# ECG Half-Screen Bug - Root Cause Analysis

## User's Observation
- Waveform starts from right ✅ (WORKING)
- But only fills HALF the screen width ❌ (BUG)
- User questions: "are you sure the pixels per mm and speed are required in the architecture?"

## The Real Question
**Why is the waveform only using half the available canvas width?**

## Possible Root Causes

### Theory 1: samplesVisible calculation is wrong
```typescript
const pixelsPerSecond = mmToPixels(PAPER_SPEED_MM_PER_S); // 25mm/s at detected DPI
const pixelsPerSample = pixelsPerSecond / SAMPLE_RATE_HZ; // ÷ 500Hz
const samplesVisible = Math.floor(width / pixelsPerSample);
```

If:
- Canvas width = 1396px (user's actual width)
- DPI = 121 (detected)
- pixelsPerSecond = 119 (25mm/s × 121/25.4)
- pixelsPerSample = 0.238 (119 ÷ 500)
- samplesVisible = 5865 (1396 ÷ 0.238)

**But the data buffer might only have ~3000 samples** (6 seconds × 500Hz)

This would explain why it only fills half! The buffer size is limiting it, not the rendering logic.

### Theory 2: Medical scaling is unnecessary
The user is questioning if we even NEED the medical mm/pixel calculations.

**Alternative approach:** Simple pixel-based rendering
- Just map available data to available canvas width
- Forget about "25mm/s paper speed" - this isn't paper!
- Use: `pixelsPerSample = canvasWidth / dataBuffer.length`

This would ALWAYS fill the screen, regardless of data length.

## What to Check

1. **What is the actual data buffer length?**
   - Check console logs for `dataLength=XXX`
   - Is it ~3000 samples? ~6000 samples?

2. **What is samplesVisible?**
   - Check console log: `samplesVisible=XXXX`
   - Does this match expectations?

3. **Architecture Decision:**
   - Do we want medical-accurate 25mm/s paper speed?
     - PRO: Matches real ECG paper recorders
     - CON: Waveform won't fill screen if data buffer is smaller

   - Or do we want full-screen adaptive rendering?
     - PRO: Always fills screen, easier to see
     - CON: Speed changes based on data buffer size (not medically standard)

## User's Likely Expectation

**Full-screen waveform display** - like an ICU monitor, not a paper ECG.

ICU monitors DON'T use fixed "25mm/s" speeds - they adapt to screen size and show a fixed time window (e.g., "show last 6 seconds").

## Recommended Fix

**Option A: Adaptive full-screen rendering (ICU monitor style)**
```typescript
// Ignore medical paper speed, just fill the screen
const pixelsPerSample = width / Math.min(data.length, maxSamples);
const startX = 0; // Always start at left
const endX = width; // Always fill to right
```

**Option B: Fixed medical speed with scrolling (paper ECG style)**
```typescript
// Keep 25mm/s speed, but show only most recent N samples that fit
const pixelsPerSample = mmToPixels(25) / 500; // Fixed medical speed
const samplesVisible = Math.floor(width / pixelsPerSample);
const visibleData = data.slice(-samplesVisible); // Show only recent data
const startX = 0;
```

## Next Steps

1. Ask user: **"Do you want ICU monitor style (full-screen adaptive) or paper ECG style (fixed 25mm/s speed)?"**

2. Based on answer:
   - ICU style → Remove all medical scaling, use simple `width / data.length`
   - Paper style → Keep scaling but show only most recent samples that fit

## My Assessment

The user wants **ICU monitor style** - full screen, always visible, adaptive rendering.

The medical paper speed calculations are causing confusion and limiting the display.

**Simplify the architecture:**
- Remove DPI detection
- Remove mm-to-pixels conversion
- Just render: `map data samples uniformly across canvas width`
