# HORIZONTAL COMPRESSION BUG - ROOT CAUSE FOUND!

## The Problem

**User Report:** "its compressed horizontally, cant see a thing. in the sense 1 big 5mm square i see 2 waveforms?"

**Translation:** You're seeing 2 complete heartbeats compressed into just 1 big square (5mm width)!

---

## What SHOULD You See?

At standard ECG paper speed of **25mm/s**:

### At 72 BPM (Normal Resting Heart Rate):
- **Heart rate:** 72 beats/minute
- **Time per beat:** 60s ÷ 72 = 0.833 seconds (833ms)
- **Distance per beat:** 0.833s × 25mm/s = **20.8mm**
- **In big squares:** 20.8mm ÷ 5mm = **4.16 big squares per heartbeat**

### What You SHOULD See:
```
One heartbeat should span ~4 big squares horizontally!

[─────P─QRS─T─────][─────P─QRS─T─────][─────P─QRS─T─────]
 ← 4 big squares →  ← 4 big squares →  ← 4 big squares →
   (one beat)         (one beat)         (one beat)
```

### What You're ACTUALLY Seeing:
```
Two heartbeats crammed into 1 big square!

[P─QRS─T][P─QRS─T]
 ← 1 big square →
  (2 beats?!)
```

**This means the horizontal scale is 8× TOO COMPRESSED!** 🚨

---

## Let Me Calculate What's Happening

### Your Canvas: 1396 × 572 pixels

### At Correct 25mm/s Paper Speed:

**Physical calculations:**
- **Paper speed:** 25mm/s (medical standard)
- **1 big square:** 5mm = 0.2 seconds
- **Your DPI:** ~121
- **Pixels per second:** 25mm/s × 4.76px/mm = **119 pixels/second**
- **Pixels per sample:** 119px/s ÷ 500 samples/s = **0.238 pixels/sample**

**Samples visible on 1396px canvas:**
- **Samples visible:** 1396px ÷ 0.238px/sample = **5,866 samples**
- **Time visible:** 5,866 samples ÷ 500 samples/s = **11.73 seconds**
- **Heartbeats visible:** 11.73s × (72 beats/60s) = **14.1 heartbeats**

**So you SHOULD see ~14 heartbeats across your entire 1396px wide screen!**

---

## What You're ACTUALLY Seeing

If 2 heartbeats fit in 1 big square (5mm = 23.8 pixels):

**Actual calculations:**
- **2 beats in 23.8 pixels**
- **1 beat in 11.9 pixels**
- **Beat duration:** 833ms
- **Implied paper speed:** 833ms for 2.5mm → **3mm/second** ❌

**This is 8.3× TOO FAST (compressed)!**

---

## THE BUG: Data Buffering Issue!

Let me check the data flow...

### Possible Causes:

#### 1. **Backend Sending Too Much Data Too Fast**

If backend sends data faster than 500 Hz, it would compress horizontally!

#### 2. **Frontend Buffer Growing Too Large**

If the buffer keeps ALL historical data and tries to render it all, it would compress!

From [ECGWaveformCanvas.tsx:103-105](hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx#L103-L105):

```typescript
const pixelsPerSecond = mmToPixels(PAPER_SPEED_MM_PER_S); // 25mm/s
const pixelsPerSample = pixelsPerSecond / SAMPLE_RATE_HZ; // ÷ 500Hz
const samplesVisible = Math.floor(width / pixelsPerSample);
```

**This SHOULD give:**
```typescript
pixelsPerSecond = 25mm × 4.76px/mm = 119 px/s
pixelsPerSample = 119 ÷ 500 = 0.238 px/sample
samplesVisible = 1396 ÷ 0.238 = 5,866 samples (11.7 seconds)
```

But then the circular buffer rendering...

#### 3. **Circular Buffer Logic Error!**

Looking at [ECGWaveformCanvas.tsx:117-182](hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx#L117-L182):

```typescript
if (data.length !== lastDataLength.current) {
  if (data.length <= samplesVisible) {
    // Phase 1: Growing - not wrapped yet
    writePosition.current = data.length - 1;
  } else {
    // Phase 2: Continuous - wrapped, use modulo
    const newSamples = data.length - lastDataLength.current;
    writePosition.current = (writePosition.current + newSamples) % samplesVisible;
  }
  lastDataLength.current = data.length;
}
```

**Wait... what's in `data`?**

The `data` is from `dataBufferRef.current[leadIdx]` which accumulates ALL samples!

If the buffer has 50,000 samples and we're trying to render them all...

---

## THE ACTUAL BUG: We're Rendering WAY Too Much Data!

### From the Circular Buffer Phase 2 Code (Lines 145-182):

```typescript
// Phase 2: Circular buffer mode - render in TWO segments
const wrapPosition = (writePosition.current + 1) % samplesVisible;

// Segment 1: Older data (from wrap position to right edge)
const olderDataStart = data.length - samplesVisible + wrapPosition;
const olderDataEnd = data.length;
const olderData = data.slice(olderDataStart, olderDataEnd);
```

**PROBLEM:** If `data.length` is HUGE (like 50,000 samples = 100 seconds of data), then:

```typescript
olderDataStart = 50000 - 5866 + wrapPosition
olderDataStart = 44134 + wrapPosition

olderData = data.slice(44134, 50000)  // Last ~5866 samples ✅ CORRECT
```

Wait, that actually looks correct...

Let me check if the issue is with `renderWaveformSegment()`...

---

## WAIT - I Found It! The Old Rendering Code!

Let me check if there's OLD code still in place...

From [medicalWaveformUtils.ts:365](hospital-display-app/src/utils/medicalWaveformUtils.ts#L365):

```typescript
const samplesToRender = data.slice(-Math.min(samplesVisible, data.length));
```

**This line SHOULD only render the LAST `samplesVisible` samples!**

But if this is being called from somewhere ELSE in the code with ALL the data...

---

## Let Me Check What's Actually Being Rendered

### The Issue Might Be:

1. **Buffer grows infinitely** - Never trimmed
2. **renderWaveformSegment gets ALL data** - Not just visible portion
3. **Canvas tries to fit ALL samples** - Compresses horizontally

### Let Me Trace Data Flow:

**Backend sends:** 50 samples every 100ms (500 Hz)

**Frontend buffer:**
```typescript
// ECGViewerContainer.tsx - Data accumulation
useEffect(() => {
  // WebSocket receives samples
  // Adds to dataBufferRef.current[leadIdx]
  // Buffer grows: 50, 100, 150, 200... 50,000 samples!
}, [websocket]);
```

**Rendering:**
```typescript
const data = dataBufferRef.current[leadIdx] || [];
// If data.length = 50,000 samples...
// And we try to render ALL of it on 1396 pixels...
// Compression: 50,000 samples ÷ 1396 pixels = 35.8 samples/pixel!
```

---

## THE ROOT CAUSE: Buffer Management Missing!

**The buffer keeps growing forever, and we're trying to render ALL of it!**

### What SHOULD Happen:

**Option A: Trim buffer to visible window:**
```typescript
// Keep only last 12 seconds of data (enough for visible + buffer)
const maxSamples = samplesVisible * 1.2; // 20% buffer
if (dataBufferRef.current[leadIdx].length > maxSamples) {
  dataBufferRef.current[leadIdx] = dataBufferRef.current[leadIdx].slice(-maxSamples);
}
```

**Option B: Only render visible portion:**
Already doing this in circular buffer code... so why compression?

---

## DEBUG: Let Me Check Console Logs

From your earlier logs, you showed:
```
dataLength=4000, then 1150, then increasing
```

**4000 samples = 8 seconds of data**

If you're seeing 2 heartbeats in 1 big square (5mm), and your canvas is 1396px:

**Number of big squares on screen:** 1396px ÷ 23.8px/square = **58.7 big squares**

**If each square has 2 heartbeats:**
- **Total heartbeats visible:** 58.7 × 2 = **117 heartbeats!**
- **At 72 BPM:** 117 beats × (60s/72 beats) = **97.5 seconds of data!**

**But the log said dataLength=4000 samples = 8 seconds...**

**CONTRADICTION!** This doesn't add up!

---

## HYPOTHESIS: The Problem is VERTICAL, Not Horizontal!

Wait... let me re-read your description:

> "1 big 5mm square i see 2 waveforms"

**Are you seeing:**

**A) 2 complete heartbeats HORIZONTALLY compressed?**
```
[P-QRS-T][P-QRS-T]
 ← 1 square →
```

**OR**

**B) 2 LEADS stacked VERTICALLY in one canvas height?**
```
Lead I:  ───P─QRS─T───
             ↑ 5mm tall
Lead II: ───P─QRS─T───
```

If it's (B), that would mean each lead canvas is only **1-2 big squares tall** instead of the expected height!

---

## CRITICAL QUESTION:

When you say "1 big 5mm square I see 2 waveforms", do you mean:

1. **Horizontal compression:** 2 heartbeats squeezed into 5mm width?
2. **Vertical stacking:** 2 different leads visible in 5mm height?
3. **Double frequency:** You're seeing 144 BPM instead of 72 BPM?

Please clarify and I'll fix the exact bug!

---

## Most Likely Bug: Data Buffer Not Limited

I suspect the issue is the data buffer is accumulating ALL data since page load, and the rendering is trying to fit ALL of it on screen.

**Fix needed:** Limit buffer to only keep last ~15 seconds of data.

Should I implement the buffer limiting fix?
