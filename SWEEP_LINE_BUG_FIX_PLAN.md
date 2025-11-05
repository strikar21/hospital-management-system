# Sweep Line Bug Fix - Detailed Plan

## Problem Statement

**User Report:** "after it hits half screen, the red line stops and then data starts going left"

## Root Cause Analysis

### Current Behavior (BROKEN):
1. `ECGWaveformCanvas.tsx` calculates sweep position based on `data.length`
2. When `data.length >= samplesVisible`, sweep locks at right edge (`width - 1`)
3. BUT `renderWaveformCanvas()` takes LAST `samplesVisible` samples and renders from x=0
4. Result: Sweep stays right, waveform scrolls left = visual disconnect

### Code Evidence:

**ECGWaveformCanvas.tsx:110-129** (Sweep calculation):
```typescript
const sweepX = data.length >= samplesVisible
  ? width - 1  // ❌ LOCKS AT RIGHT EDGE
  : Math.min(data.length * pixelsPerSample, width - 1);
```

**medicalWaveformUtils.ts:365** (Waveform rendering):
```typescript
const samplesToRender = data.slice(-Math.min(samplesVisible, data.length));
// ❌ ALWAYS renders from x=0, shows LAST N samples
```

**The mismatch:** Sweep position doesn't match where new data appears on screen.

## Expected Behavior (Real ICU Monitors)

Real ECG monitors use **continuous sweep mode**:

1. **Phase 1 - Growing:** Sweep moves left→right as data fills screen
2. **Phase 2 - Continuous:** When sweep hits right edge, it wraps to left and continues
3. **Phase 3 - Erasing:** Area behind sweep is cleared (black or shows grid only)
4. **Result:** Classic "chart recorder" effect with moving sweep line

## Solution Architecture

### Option A: Circular Buffer Rendering (ICU Monitor Style) ✅ RECOMMENDED
- Maintain a circular write position that wraps around
- Render waveform in TWO segments when wrap occurs:
  - Segment 1: From wrap position to right edge (older data)
  - Segment 2: From left edge to sweep position (newer data)
- Erase strip behind sweep line

**Advantages:**
- Most authentic medical display
- Continuous smooth motion
- Clear visual indication of "now" (sweep line)
- Matches user expectations from real monitors

**Disadvantages:**
- More complex rendering logic
- Need to manage wrap-around state

### Option B: Sliding Window (Current, needs fix)
- Keep current "last N samples" approach
- But make sweep line match the rendering position
- Sweep always at right edge when buffer full

**Advantages:**
- Simpler code
- Less state management

**Disadvantages:**
- Doesn't match real ICU monitors
- Less intuitive for medical staff
- No clear "now" indication when buffer full

## Recommended Implementation: Option A (Circular Buffer)

### New State Required:

Add to `ECGWaveformCanvas.tsx`:
```typescript
const writePosition = useRef(0); // Circular write position (0 to samplesVisible-1)
const isFull = useRef(false);    // Has buffer wrapped around yet?
```

### Rendering Logic:

```typescript
function renderWaveformWithSweep() {
  const samplesVisible = Math.floor(width / pixelsPerSample);

  // Update write position based on new data length
  if (data.length <= samplesVisible) {
    // Phase 1: Growing - not wrapped yet
    writePosition.current = data.length - 1;
    isFull.current = false;
  } else {
    // Phase 2: Continuous - wrapped, use modulo
    const totalSamples = data.length;
    writePosition.current = (totalSamples - 1) % samplesVisible;
    isFull.current = true;
  }

  // Calculate sweep X position
  const sweepX = writePosition.current * pixelsPerSample;

  if (!isFull.current) {
    // Phase 1: Simple render from left
    renderWaveformCanvas(data, ctx, width, height, isECGMode, true, leadColor);
  } else {
    // Phase 2: Render in TWO segments with wrap-around
    const olderData = data.slice(-samplesVisible, -(writePosition.current + 1));
    const newerData = data.slice(-(writePosition.current + 1));

    // Segment 1: Older data (right side of canvas)
    const segment1Start = (writePosition.current + 1) * pixelsPerSample;
    renderSegment(olderData, segment1Start);

    // Segment 2: Newer data (left side of canvas)
    renderSegment(newerData, 0);

    // Erase strip behind sweep (optional for cleaner look)
    const eraseWidth = 10; // pixels
    ctx.fillStyle = '#000000';
    ctx.fillRect(sweepX + 2, 0, eraseWidth, height);
  }

  // Draw sweep line at write position
  ctx.strokeStyle = '#FF0000';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(sweepX, 0);
  ctx.lineTo(sweepX, height);
  ctx.stroke();
}
```

### Helper Function for Segment Rendering:

Add to `medicalWaveformUtils.ts`:
```typescript
export function renderWaveformSegment(
  data: number[],
  ctx: CanvasRenderingContext2D,
  startX: number, // Starting X pixel position
  height: number,
  isECGMode: boolean,
  pixelsPerSample: number,
  pixelsPerUnit: number,
  leadColor: string
): void {
  if (!data || data.length === 0) return;

  const baseline = height / 2;

  ctx.strokeStyle = leadColor;
  ctx.lineWidth = 2;
  ctx.beginPath();

  let isFirst = true;
  for (let i = 0; i < data.length; i++) {
    const x = startX + (i * pixelsPerSample);
    const value = isECGMode ? adcToMillivolts(data[i]) : adcToMicrovolts(data[i]);
    const y = baseline - (value * pixelsPerUnit);
    const clampedY = Math.max(0, Math.min(height, y));

    if (isFirst) {
      ctx.moveTo(x, clampedY);
      isFirst = false;
    } else {
      ctx.lineTo(x, clampedY);
    }
  }

  ctx.stroke();
}
```

## Implementation Steps

### Step 1: Add helper function to medicalWaveformUtils.ts
- Add `renderWaveformSegment()` function for partial rendering with offset

### Step 2: Modify ECGWaveformCanvas.tsx
- Add `writePosition` and `isFull` refs
- Replace current rendering with circular buffer logic
- Update sweep line calculation to use `writePosition`
- Add optional erase strip behind sweep

### Step 3: Test both phases
- Phase 1 (growing): Verify sweep moves left→right
- Phase 2 (continuous): Verify sweep wraps and continues
- Phase 3 (erasing): Verify old data disappears behind sweep

## Testing Checklist

- [ ] Sweep starts at left edge when data arrives
- [ ] Sweep moves smoothly left→right as data fills
- [ ] Sweep wraps to left when reaching right edge
- [ ] Old data on right side appears after wrap
- [ ] New data on left side grows after wrap
- [ ] No visual jumps or discontinuities
- [ ] Works correctly in all layouts (1, 4, 9, 12 view)
- [ ] Works correctly for both ECG and EEG modes
- [ ] Console logs show correct write positions

## Alternative: Simple Fix (If circular buffer too complex)

If circular buffer proves too complex, simpler fix:

**Just sync sweep to rendering:**
```typescript
// Always render from left, sweep always at right when full
const sweepX = data.length < samplesVisible
  ? data.length * pixelsPerSample
  : width - 1;

// And add visual indicator that buffer is in "continuous" mode
if (data.length >= samplesVisible) {
  ctx.fillText('CONTINUOUS', 10, 20);
}
```

But this doesn't match real ICU monitors and may confuse users.

## Recommendation

**Implement Option A (Circular Buffer)** - it's the medically accurate approach that matches real ICU monitors and will be most intuitive for medical staff who are trained on real ECG machines.

Estimated implementation time: 30-45 minutes
Risk: Medium (more complex state management, but well-defined logic)
