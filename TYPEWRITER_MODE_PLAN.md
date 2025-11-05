# Typewriter Mode Implementation Plan

## Current Behavior (LEFT-TO-RIGHT)
- New data starts at LEFT edge (x=0)
- Waveform grows RIGHTWARD →
- When full, wraps around in circular buffer

## Desired Behavior (RIGHT-TO-LEFT Typewriter)
- New data appears at RIGHT edge (x=1313px)
- Entire waveform scrolls LEFTWARD ←
- Old data disappears off LEFT edge
- Like watching paper feed through ECG machine

---

## Implementation Strategy

### Approach: Scrolling Canvas Translation

Instead of drawing waveform at fixed positions, we **translate the entire canvas** to create scrolling effect:

1. **Always draw newest sample at SAME position** (right edge)
2. **Shift ALL previous data to the LEFT** using canvas translation
3. **Clip/hide data that goes off left edge**

### Rendering Logic

**Phase 1: Filling Screen (Growing)**
- Buffer: 0 → 6947 samples (0 → 13.9 seconds)
- Draw from RIGHT, growing leftward
- `startX = width - (data.length * pixelsPerSample)`
- Waveform grows from right edge toward left

**Phase 2: Scrolling (Continuous)**
- Buffer: > 6947 samples (full screen)
- Always show LAST 6947 samples (most recent 13.9s)
- Draw from LEFT edge, but use canvas translation to shift
- OR: Calculate startX to show rightmost data

---

## Code Changes Required

### 1. ECGWaveformCanvas.tsx - Phase 1 (Growing from Right)

**Current (LEFT-TO-RIGHT):**
```typescript
const startX = 0;  // Start at left edge
```

**New (RIGHT-TO-LEFT):**
```typescript
const startX = width - (data.length * pixelsPerSample);  // Start at right, grow left
```

**Result:**
- 100 samples: startX = 1313 - 18.9 = 1294px (near right edge)
- 3000 samples: startX = 1313 - 567 = 746px (middle)
- 6947 samples: startX = 1313 - 1313 = 0px (fills screen)

### 2. ECGWaveformCanvas.tsx - Phase 2 (Scrolling Mode)

**Current (Circular Buffer Wrap):**
- Uses modulo arithmetic to wrap around
- Erases section behind sweep line
- Two segments: older data + newer data

**New (Continuous Scroll):**
```typescript
if (data.length > samplesVisible) {
  // Always show LAST samplesVisible samples (most recent data)
  const visibleData = data.slice(-samplesVisible);

  // Draw from left edge (data already trimmed to screen width)
  renderWaveformSegment(
    visibleData,
    ctx,
    0,  // Always start at left edge
    height,
    isECGMode,
    pixelsPerSample,
    pixelsPerUnit,
    leadColor
  );
}
```

**Result:**
- Buffer has 12500 samples (25 seconds)
- Screen shows LAST 6947 samples (13.9 seconds)
- As new data arrives, old data "scrolls off" left edge
- No wrap-around, no circular buffer confusion

### 3. Remove Sweep Line (No Longer Needed)

Sweep line (red vertical line) made sense for circular buffer wrap-around.
For typewriter mode, **NO SWEEP LINE** - just continuous scroll.

Remove lines 219-233.

### 4. Remove Erase Section (No Longer Needed)

Lines 193-205 erase behind sweep line - not needed for typewriter mode.

---

## Visual Comparison

### Current (Left-to-Right Circular):
```
[CAL]████████████░░░░░░░░░░░░░░░|    ← Waveform starts left, wraps
     ↑ Sweep line moves right →
```

### New (Right-to-Left Typewriter):
```
░░░░░░░░░░░░░░░░████████████[NEW]    ← New data appears right
← ← ← Everything scrolls left
```

---

## Benefits

1. **Intuitive** - Matches real ECG paper machines
2. **Simpler Logic** - No circular buffer, no wrap-around, no erase sections
3. **Always Show Recent** - Last N seconds always visible
4. **Medical Standard** - How doctors expect to see live ECG

---

## Testing Plan

1. Open fullscreen ECG viewer
2. Verify waveform starts from RIGHT edge
3. Verify waveform scrolls LEFTWARD as data arrives
4. Verify old data disappears off LEFT edge smoothly
5. Verify grid stays fixed (doesn't scroll with waveform)
6. Verify calibration pulse appears at RIGHT edge initially

---

## Files to Modify

1. **hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx**
   - Line 140: Change `startX = 0` to `startX = width - (data.length * pixelsPerSample)`
   - Lines 153-207: Replace circular buffer logic with simple slice
   - Lines 219-233: Remove sweep line
   - Lines 193-205: Remove erase section

---

**Estimated Time:** 15 minutes
**Complexity:** Medium (simplifies existing logic)
**Risk:** Low (makes code simpler, easier to debug)
