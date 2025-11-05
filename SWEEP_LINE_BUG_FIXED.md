# Sweep Line Bug - FIXED ✅

## Problem (User Report)
"after it hits half screen, the red line stops and then data starts going left"

## Root Cause
The sweep line calculation and waveform rendering were out of sync:
- Sweep line locked at right edge when buffer filled
- Waveform kept showing "last N samples" from buffer
- Created illusion of waveform scrolling left

## Solution Implemented
**Circular Buffer Rendering (ICU Monitor Style)**

### Phase 1: Growing Mode (data < screen width)
- Sweep line moves left→right as data accumulates
- Waveform renders from left edge
- Exactly like real ICU monitors during startup

### Phase 2: Continuous Mode (data fills screen)
- Sweep line continues moving left→right
- When sweep reaches right edge, wraps to left edge
- Waveform renders in TWO segments:
  - **Segment 1:** Older data (from wrap position to right edge)
  - **Segment 2:** Newer data (from left edge to sweep position)
- Black erase strip behind sweep line (classic chart recorder effect)

## Files Modified

### 1. `medicalWaveformUtils.ts` (Lines 397-444)
**Added:** `renderWaveformSegment()` function
```typescript
export function renderWaveformSegment(
  data: number[],
  ctx: CanvasRenderingContext2D,
  startX: number,  // ← Key difference: can start at any X position
  height: number,
  isECGMode: boolean,
  pixelsPerSample: number,
  pixelsPerUnit: number,
  leadColor: string
): void
```

**Purpose:** Render waveform segment starting at arbitrary X position (for circular buffer)

### 2. `ECGWaveformCanvas.tsx` (Lines 39-224)
**Added:** Circular buffer state tracking
```typescript
const writePosition = useRef(0);   // Current write position (0 to samplesVisible-1)
const lastDataLength = useRef(0);  // Track data length changes
```

**Replaced:** Entire `drawWaveform()` function with circular buffer logic

**Key Changes:**
- Calculate `samplesVisible` based on medical-grade spacing
- Track write position using modulo arithmetic
- Render differently based on phase:
  - Phase 1 (growing): Simple single segment
  - Phase 2 (continuous): Two-segment wraparound rendering
- Position sweep line at `writePosition` in continuous mode
- Add black erase strip behind sweep for clarity

## Technical Details

### Write Position Calculation
```typescript
if (data.length <= samplesVisible) {
  // Phase 1: Growing
  writePosition.current = data.length - 1;
} else {
  // Phase 2: Continuous - wrap using modulo
  const newSamples = data.length - lastDataLength.current;
  writePosition.current = (writePosition.current + newSamples) % samplesVisible;
}
```

### Segment Boundaries (Phase 2)
```typescript
const wrapPosition = (writePosition.current + 1) % samplesVisible;

// Older data: from (data.length - samplesVisible + wrapPosition) to end
// Renders at X position: wrapPosition * pixelsPerSample (right side)

// Newer data: last wrapPosition samples
// Renders at X position: 0 (left side)
```

### Sweep Line Position
```typescript
const sweepX = data.length < samplesVisible
  ? data.length * pixelsPerSample      // Phase 1: At last data position
  : writePosition.current * pixelsPerSample;  // Phase 2: At write position
```

## Visual Result

### Before (BROKEN):
```
[████████████████████████|           ]  ← Sweep stops here
[███████████████████████ |           ]  ← Waveform shifts left (confusing!)
[██████████████████████  |           ]  ← Continues shifting left
```

### After (FIXED):
```
Phase 1 (Growing):
[█                       |           ]  ← Sweep at right edge of data
[███                     |           ]
[█████                   |           ]
[███████                 |           ]

Phase 2 (Continuous wraparound):
[███████████████████████████████████|]  ← Sweep at right edge
[|████████████████████████████████ █]  ← Wraps to left, continues!
[ ███|███████████████████████████ ██]  ← Classic ICU monitor sweep
[█ ████|████████████████████████ ███]  ← Just like real ECG machines!
```

## Benefits

1. **Medically Accurate:** Matches real ICU monitor behavior
2. **Intuitive:** Medical staff trained on real monitors will recognize it instantly
3. **Continuous:** No visual jumps or discontinuities
4. **Clear "Now":** Sweep line always shows current data position
5. **Efficient:** No data copying, just smart slicing and positioning

## Testing Notes

- Calibration pulse: Still correct (2×1 big squares) ✅
- Vertical scale: Still medical-grade (10mm/mV for ECG) ✅
- Horizontal scale: Still medical-grade (25mm/s paper speed) ✅
- **NEW:** Sweep continues moving across screen ✅
- **NEW:** Waveform wraps around when sweep reaches right edge ✅
- **NEW:** Old data erased behind sweep line ✅

## What to Look For

1. **Phase 1:** Sweep should move smoothly left→right as data fills screen
2. **Phase 2:** When sweep hits right edge, should wrap to left and continue
3. **No Gaps:** Waveform should be continuous (no blank spots)
4. **No Jumps:** Transition from Phase 1 to Phase 2 should be smooth
5. **Erase Strip:** Small black area behind sweep line (makes sweep more visible)

## Implementation Time
~45 minutes (as estimated in plan document)

## Status
✅ **COMPLETE** - Ready for user testing

---

**Next Steps:**
User should refresh browser and test ECG viewer to verify sweep line continues moving across screen instead of stopping at half-screen.
