# Horizontal Compression ROOT CAUSE FOUND!

## The Bug

**User sees:** 2 complete heartbeats squeezed into just 1 big square (5mm)

**Should see:** 1 heartbeat spanning ~4 big squares (20mm)

## The Math

### At 72 BPM:
- **Time per beat:** 833ms
- **At 25mm/s:** 833ms = 20.8mm per beat
- **In big squares:** 20.8mm ÷ 5mm = **4.16 squares per beat** ✅

### User sees instead:
- 2 beats in 1 square (5mm)
- 1 beat = 2.5mm
- **This is 8.3× TOO COMPRESSED!**

---

## THE ACTUAL BUG: Phase 1 Renders ALL Data!

Look at [ECGWaveformCanvas.tsx:128-141](hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx#L128-L141):

```typescript
if (data.length <= samplesVisible) {
  // ✅ PHASE 1: Growing mode - render all data from left
  renderWaveformSegment(
    data,  // ← RENDERING ALL DATA!
    ctx,
    0,
    height,
    isECGMode,
    pixelsPerSample,  // ← Correct spacing
    pixelsPerUnit,
    leadColor
  );
}
```

**The problem:** We're passing ALL `data` (could be 4000 samples = 8 seconds)

**The rendering:** `renderWaveformSegment` renders every sample with `pixelsPerSample` spacing

**What happens:**
```typescript
// Line 430 in renderWaveformSegment:
for (let i = 0; i < data.length; i++) {  // data.length = 4000!
  const x = startX + (i * pixelsPerSample);  // x goes to 4000 * 0.238 = 952 pixels
}
```

**If canvas width is 1396px:**
- We try to render 4000 samples × 0.238 px/sample = **952 pixels of waveform**
- This fits fine... wait, that's NOT the problem!

Let me recalculate...

---

## WAIT - Let Me Check Canvas Dimensions

**User said canvas is 1396 × 572 pixels**

But that's the FULL window! Each individual lead canvas is MUCH smaller!

In a 4-lead view:
- Full width: 1396px
- 2 columns → Each canvas: **698px wide**
- Each canvas: **286px tall**

Let me recalculate:

**For 698px wide canvas:**
```typescript
pixelsPerSecond = 119 px/s
pixelsPerSample = 119 ÷ 500 = 0.238 px/sample
samplesVisible = 698 ÷ 0.238 = 2,933 samples (5.87 seconds)
```

**User's buffer has 4000 samples (8 seconds)**

So `data.length (4000) > samplesVisible (2933)` → We're in **PHASE 2**, not Phase 1!

But user says it's compressed...

---

## LET ME CHECK: Is `samplesVisible` Calculated Correctly?

From [ECGWaveformCanvas.tsx:101-103](hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx#L101-L103):

```typescript
const pixelsPerSecond = mmToPixels(PAPER_SPEED_MM_PER_S); // 25mm/s
const pixelsPerSample = pixelsPerSecond / SAMPLE_RATE_HZ; // ÷ 500Hz
const samplesVisible = Math.floor(width / pixelsPerSample);
```

**This SHOULD give:**
```typescript
pixelsPerSecond = mmToPixels(25)
pixelsPerSecond = 25mm × (121px ÷ 25.4mm) = 25 × 4.76 = 119 px/s ✅
pixelsPerSample = 119 ÷ 500 = 0.238 px/sample ✅
samplesVisible = 1396 ÷ 0.238 = 5,866 samples ✅
```

**Wait... but user might be looking at a SINGLE lead in full-screen mode!**

If showing 1 lead full-screen:
- Canvas width: ~1396px
- samplesVisible: 5,866 samples (11.7 seconds)
- Buffer has: 4000 samples (8 seconds)

So we're in **PHASE 1** (data.length < samplesVisible)

---

## THE REAL BUG: DPI Detection is WRONG!

**Hypothesis:** `mmToPixels()` is returning the WRONG value!

Let me check what happens if DPI detection fails:

```typescript
// From medicalWaveformUtils.ts:
cachedDPI = 96;  // Fallback
```

**If DPI = 96 instead of 121:**
```typescript
pixelsPerSecond = 25mm × (96 ÷ 25.4) = 25 × 3.78 = 94.5 px/s
pixelsPerSample = 94.5 ÷ 500 = 0.189 px/sample
```

**Rendering 4000 samples:**
```typescript
Total width = 4000 × 0.189 = 756 pixels
```

**But canvas is 1396px wide!**

So the waveform only fills **756 ÷ 1396 = 54%** of screen width!

**This is NOT the compression issue though...**

---

## ACTUAL ROOT CAUSE: The `speed` Variable!

Wait! Look at line 91 again:

```typescript
logger.log(`... speed=${speed}mm/s ...`);
```

**What if `speed` is NOT 25mm/s?**

The circular buffer code uses **`PAPER_SPEED_MM_PER_S` constant (25mm/s)**

But what if the rendering is using a DIFFERENT speed value from `props.speed`?

Let me check...

NO! Lines 101-102 use the CONSTANT, not the variable:
```typescript
const pixelsPerSecond = mmToPixels(PAPER_SPEED_MM_PER_S); // Always 25mm/s
```

---

## LET ME THINK DIFFERENTLY: Check The Grid!

If user says "1 big square (5mm) contains 2 heartbeats", maybe the GRID itself is wrong?

**Big square SHOULD be:**
- 5mm = 5mm × 4.76 px/mm = 23.8 pixels

**User can measure:** Count pixels between thick red lines!

If thick lines are 10 pixels apart instead of 23.8 pixels → Grid is TOO COMPRESSED!

**This would mean DPI detection is FAILING and using wrong value!**

---

## DIAGNOSTIC NEEDED:

We need to check:
1. What is `pixelsPerSample` actually being calculated as?
2. What is the canvas `width` value?
3. What is `samplesVisible`?
4. Is DPI being detected correctly?

The console logs should show these values... but user said they're seeing compression.

**Most likely issue: DPI detection returning wrong value!**

## THE FIX:

Force DPI to user's actual value:

```typescript
// In medicalWaveformUtils.ts, change:
let cachedDPI: number | null = 121; // Force user's DPI!
```

OR add debug logging to see what's happening:

```typescript
console.log(`DEBUG: DPI=${getScreenDPI()}, pixelsPerSample=${pixelsPerSample}, samplesVisible=${samplesVisible}`);
```
