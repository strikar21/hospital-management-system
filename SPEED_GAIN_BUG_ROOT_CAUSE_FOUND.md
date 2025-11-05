# Speed/Gain Control Bug - ROOT CAUSE FOUND

**Date:** 2025-11-04
**Status:** 🔴 **BUG CONFIRMED** - Stale closure in animation loop

---

## User Report

> "but nothing ahppens hwen i change speed or gain?"

**User is correct** - controls change the label but waveform doesn't respond.

---

## Root Cause: Stale Closure in requestAnimationFrame Loop

**File:** [ECGWaveformCanvas.tsx:54-62](hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx#L54-L62)

### The Bug:

```typescript
// ❌ WRONG: drawWaveform defined at component scope
const drawWaveform = (timestamp: number) => {
  const pixelsPerSecond = mmToPixels(speed);  // Line 104 - reads prop
  const pixelsPerUnit = isECGMode ? mmToPixels(gain) : mmToPixels(1 / gain);  // Line 116-118 - reads prop
  // ... rest of function
};

// Animation loop with stale closure
useEffect(() => {
  let animationFrameId: number;
  const animate = (timestamp: number) => {
    drawWaveform(timestamp);  // ← Calls CAPTURED function reference
    if (!isPaused) animationFrameId = requestAnimationFrame(animate);
  };
  if (!isPaused) animationFrameId = requestAnimationFrame(animate);
  return () => cancelAnimationFrame(animationFrameId);
}, [isPaused]);  // ← ONLY depends on isPaused
```

### What Happens:

1. **Initial render**:
   - `speed = 25`, `gain = 10`
   - `drawWaveform` function created with access to these values
   - `animate` function captures reference to this `drawWaveform`
   - `requestAnimationFrame(animate)` starts loop

2. **User changes speed to 30**:
   - Component re-renders with `speed = 30`, `gain = 10`
   - **NEW** `drawWaveform` function created (would read speed=30)
   - **BUT**: useEffect dependency is `[isPaused]`, which hasn't changed
   - useEffect **DOES NOT RE-RUN**
   - Animation loop continues calling **OLD** `drawWaveform` (speed=25)

3. **Result**: Label changes to "30mm/s" but waveform still renders at 25mm/s

---

## Why My Initial Analysis Was Wrong

I said:
> "drawWaveform is NOT inside useEffect closure... reads props directly (not captured)"

**This was incorrect because:**
- While `drawWaveform` is not inside useEffect, the `animate` function **IS** inside useEffect
- `animate` captures the `drawWaveform` reference when useEffect runs
- When props change, component re-renders but useEffect doesn't re-run (dependency is `[isPaused]`)
- New `drawWaveform` is created but animation loop still calls the old one

---

## The Fix

**Add `speed`, `gain`, and `isECGMode` to useEffect dependencies:**

```typescript
// ✅ CORRECT: Re-run animation loop when speed/gain/mode change
useEffect(() => {
  let animationFrameId: number;
  const animate = (timestamp: number) => {
    drawWaveform(timestamp);
    if (!isPaused) animationFrameId = requestAnimationFrame(animate);
  };
  if (!isPaused) animationFrameId = requestAnimationFrame(animate);
  return () => cancelAnimationFrame(animationFrameId);
}, [isPaused, speed, gain, isECGMode]);  // ← ADD these dependencies
```

**Why this works:**
- When `speed` or `gain` change, component re-renders
- New `drawWaveform` function created with fresh prop values
- useEffect sees dependency changed, **cancels old animation loop**
- useEffect re-runs with new `animate` function that captures new `drawWaveform`
- New animation loop calls new `drawWaveform` with correct speed/gain

---

## Alternative Fix: Move drawWaveform Inside useEffect

```typescript
// ✅ ALTERNATIVE: Move drawWaveform inside useEffect
useEffect(() => {
  const drawWaveform = (timestamp: number) => {
    // ... function body (reads fresh props from closure)
  };

  let animationFrameId: number;
  const animate = (timestamp: number) => {
    drawWaveform(timestamp);
    if (!isPaused) animationFrameId = requestAnimationFrame(animate);
  };
  if (!isPaused) animationFrameId = requestAnimationFrame(animate);
  return () => cancelAnimationFrame(animationFrameId);
}, [isPaused, speed, gain, isECGMode, dataBufferRef, leadIdx, leadName, patientId]);
```

**Trade-off**: More dependencies, but clearer closure capture.

---

## Recommended Solution

**Use dependency array fix** (simpler, less code change):

```typescript
}, [isPaused, speed, gain, isECGMode]);
```

**Why:**
- Minimal code change
- Clear intent: "restart animation when these change"
- Properly cancels old loop before starting new one
- React Hook best practice

---

## Testing Plan

1. Open EEG viewer
2. Observe waveform rendering at default 30mm/s
3. Change speed to 25mm/s → waveform should compress horizontally
4. Change speed to 50mm/s → waveform should expand horizontally
5. Change gain from 7μV/mm to 10μV/mm → waveform should shrink vertically
6. Change gain from 10μV/mm to 5μV/mm → waveform should expand vertically

---

## Files to Modify

1. **ECGWaveformCanvas.tsx** - Line 62 (add dependencies to useEffect)

---

## Why Speed/Gain Controls Label Change But Waveform Doesn't

**Label change:**
- ECGDisplayGrid.tsx lines 109-112 render current speed/gain values
- These are React props, update immediately on state change
- Label re-renders with new values

**Waveform doesn't change:**
- ECGWaveformCanvas animation loop uses stale closure
- Old `drawWaveform` function still being called
- Old function reads old prop values (captured at initial render)

---

## Summary

**Bug:** Stale closure in requestAnimationFrame loop
**Cause:** useEffect depends only on `[isPaused]`, not on `[speed, gain, isECGMode]`
**Fix:** Add missing dependencies to useEffect
**Impact:** Speed/gain controls will work immediately after fix

**Status:** ✅ **ROOT CAUSE IDENTIFIED** - Ready to implement fix

---

**END OF ANALYSIS**
