# ECG/EEG Viewer - Comprehensive Bug Audit

**Date:** 2025-11-01
**Status:** Pre-Fix Audit
**Severity:** CRITICAL - System is medically unusable in current state

---

## Executive Summary

The ECG/EEG viewer has **multiple critical bugs** that make it medically inaccurate and unusable for clinical monitoring:

1. ❌ **Waveform disappears** after ~5 seconds (infinite scroll bug)
2. ❌ **Calibration pulse wrong size** (6×17 squares instead of 2×1)
3. ❌ **Grid and waveform use different scales** (not synchronized)
4. ❌ **Browser zoom breaks medical accuracy** (DPI cached forever)
5. ⚠️ **Gain control doesn't work** (UI only, not applied to rendering)
6. ⚠️ **Speed control doesn't match medical standard** (broken translation)

**Medical Impact:** All amplitude measurements are 3× wrong, time measurements are 17× wrong, continuous monitoring is impossible.

---

## CRITICAL BUGS (Must Fix Before Any Clinical Use)

### Bug #1: Waveform Disappears After Seconds ❌

**Severity:** CRITICAL - Makes monitoring impossible
**File:** [ECGWaveformCanvas.tsx:98-102](hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx#L98-L102)

**Problem:**
```typescript
scrollOffset.current += mmToPixels(speed) * deltaTime; // Increases forever
ctx.translate(-scrollOffset.current, 0); // Translates waveform off-screen
```

**Root Cause:** `scrollOffset` increases infinitely without wrapping, so waveform scrolls off-screen left and never returns.

**Evidence:** After 10 seconds at 25mm/s: `scrollOffset = 1000 pixels`, waveform is completely off-screen.

**Medical Impact:**
- ❌ Cannot monitor patient continuously
- ❌ Arrhythmia detection impossible
- ❌ System is non-functional after ~5-10 seconds

**Detailed Analysis:** [WAVEFORM_DISAPPEARS_BUG.md](WAVEFORM_DISAPPEARS_BUG.md)

---

### Bug #2: Calibration Pulse Wrong Size ❌

**Severity:** CRITICAL - Makes all measurements medically inaccurate
**File:** [medicalWaveformUtils.ts:334-367](hospital-display-app/src/utils/medicalWaveformUtils.ts#L334-L367)

**User Report:** Calibration pulse appears as **6 big squares tall × 17 big squares wide**
**Expected:** Should be **2 big squares tall × 1 big square wide** (medical standard)

**Problem:**
```typescript
// Vertical scale (WRONG):
const mvRange = 4;
const pixelsPerUnit = height / mvRange; // ❌ Ignores grid scale!

// Horizontal scale (WRONG):
const pixelsPerSample = width / samplesToRender.length; // ❌ Stretches to fill width!
```

**Root Cause:** Grid uses `mmToPixels()` for DPI-accurate scaling, but waveform just divides canvas dimensions by arbitrary ranges. They are **completely independent** scales.

**Medical Impact:**
- ❌ Amplitude measurements 3× wrong (QRS, ST elevation)
- ❌ Time measurements 17× wrong (intervals)
- ❌ False LVH, STEMI diagnoses possible
- ❌ **Medically dangerous**

**Detailed Analysis:** [CALIBRATION_PULSE_SCALING_BUG.md](CALIBRATION_PULSE_SCALING_BUG.md)

---

### Bug #3: Browser Zoom Breaks Medical Scale ❌

**Severity:** HIGH - Variable medical accuracy
**File:** [medicalWaveformUtils.ts:44-77](hospital-display-app/src/utils/medicalWaveformUtils.ts#L44-L77)

**Problem:**
```typescript
let cachedDPI: number | null = null; // ❌ Cached forever!

export function getScreenDPI(): number {
  if (cachedDPI !== null) {
    return cachedDPI; // ❌ Never recalculates on zoom change
  }
  // ... detection code ...
}
```

**Root Cause:** DPI is detected once and cached. If user zooms browser (Ctrl+Plus), DPI is not recalculated, so grid scale becomes inaccurate.

**User Scenario:**
- User has browser at 125% zoom by default
- System detects DPI at 125% zoom, grid renders correctly ✅
- If user changes zoom to 150%, grid scale is wrong ❌
- Calibration pulse no longer matches grid squares

**Medical Impact:**
- ⚠️ Grid scale varies unpredictably with zoom
- ⚠️ Measurements inaccurate if zoom changes
- ⚠️ Training required: "Never zoom browser"

**Detailed Analysis:** [GRID_SCALING_ANALYSIS.md](GRID_SCALING_ANALYSIS.md)

---

## HIGH PRIORITY BUGS (Affect Usability)

### Bug #4: Gain Control Not Applied ⚠️

**Severity:** HIGH - Control doesn't work
**File:** [ECGViewerHeader.tsx:136-155](hospital-display-app/src/components/ECGViewer/ECGViewerHeader.tsx#L136-L155)

**Problem:**
- Gain dropdown in header allows selecting 5mm/mV, 10mm/mV, 20mm/mV
- `gain` state variable changes ✅
- But rendering code **doesn't use** `gain` variable ❌

**Current Rendering:**
```typescript
// medicalWaveformUtils.ts:338-339
const mvRange = 4; // ±2mV - HARDCODED, ignores gain setting!
const pixelsPerUnit = height / mvRange;
```

**Expected:**
- 10mm/mV (standard): Show ±2mV range
- 5mm/mV (half sensitivity): Show ±4mV range (useful for large QRS)
- 20mm/mV (double sensitivity): Show ±1mV range (useful for low voltage)

**Medical Impact:**
- ⚠️ Cannot adjust sensitivity for different patients
- ⚠️ Large QRS complexes go off-screen (cannot reduce gain)
- ⚠️ Small QRS complexes hard to see (cannot increase gain)

---

### Bug #5: Speed Control Doesn't Work Correctly ⚠️

**Severity:** MEDIUM - Control partially works
**File:** [ECGWaveformCanvas.tsx:98](hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx#L98)

**Problem:**
```typescript
scrollOffset.current += mmToPixels(speed) * deltaTime; // Uses speed for translation
```

But waveform horizontal scale is:
```typescript
const pixelsPerSample = width / samplesToRender.length; // ❌ Ignores speed!
```

**Result:**
- Speed affects scroll rate ✅
- Speed does NOT affect waveform horizontal scale ❌
- At 50mm/s, waveforms should be 2× wider than 25mm/s, but they're not

**Medical Impact:**
- ⚠️ Time measurements incorrect at non-standard speeds
- ⚠️ Cannot match paper ECG speeds (25mm/s vs 50mm/s)

---

### Bug #6: Sweep Line Calculation Wrong ⚠️

**Severity:** MEDIUM - Visual indicator incorrect
**File:** [ECGWaveformCanvas.tsx:118](hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx#L118)

**Problem:**
```typescript
const sweepX = (scrollOffset.current % (width * pixelsPerSample)) / pixelsPerSample;
```

**Issue:** This calculation assumes waveform width matches canvas width, but:
- When buffer has only 200 samples (calibration)
- Waveform is stretched to fill canvas width
- Sweep line calculation doesn't account for this stretch
- **Result:** Sweep line position is mathematically incorrect

**Visual Impact:**
- ⚠️ Red sweep line doesn't align with "now" position
- ⚠️ Confusing for medical staff monitoring

---

## MEDIUM PRIORITY BUGS (Affect Quality)

### Bug #7: Layout 12-Lead Not Implemented ⚠️

**Severity:** MEDIUM - Missing feature
**File:** [ECGViewerHeader.tsx:99](hospital-display-app/src/components/ECGViewer/ECGViewerHeader.tsx#L99)

**Problem:**
- Header has option for "Complete 12-Lead ECG" ✅
- But clicking it just shows 12 separate single-lead views ❌
- Real 12-lead ECG should show synchronized views with 10-second strips

**Expected Medical Standard:**
- All 12 leads visible simultaneously
- Synchronized time axis (same QRS visible across all leads)
- Standard 10-second strip format
- Grid visible behind all leads

**Current Behavior:**
- Just shows 12 independent canvases
- Not synchronized
- Different scroll positions

---

### Bug #8: No Real Data Flow from ESP32 ⚠️

**Severity:** HIGH - Depends on watch connection
**File:** [useECGViewer.ts:92-247](hospital-display-app/src/hooks/useECGViewer.ts#L92-L247)

**Problem:**
- WebSocket subscription implemented ✅
- But only calibration pulse visible ❌
- No real waveform data from ESP32 watch

**Possible Causes:**
1. Watch not assigned to patient (`assignedDeviceId` is null)
2. Watch not streaming (offline, battery dead)
3. Backend not forwarding data via WebSocket
4. Data format mismatch (wrong structure)

**Need to Diagnose:**
- Check if device is assigned
- Check ESP32 logs for MQTT publishing
- Check backend logs for WebSocket broadcasting
- Check WebSocket message format

---

### Bug #9: Pause Doesn't Pause Data Buffer ⚠️

**Severity:** MEDIUM - Pause partially broken
**File:** [useECGViewer.ts:107](hospital-display-app/src/hooks/useECGViewer.ts#L107)

**Problem:**
```typescript
if (isPaused) return; // Don't update buffers if paused
```

**But animation loop in canvas continues:**
```typescript
// ECGWaveformCanvas.tsx:98
scrollOffset.current += mmToPixels(speed) * deltaTime; // ❌ Still scrolls when paused!
```

**Result:**
- Pause stops new data from being added to buffer ✅
- But scroll offset keeps increasing ❌
- Frozen waveform continues to scroll off-screen

**Expected:**
- Pause should freeze waveform in place
- Scroll offset should not change
- Resume should continue from same position

---

### Bug #10: Console Log Spam 🔊

**Severity:** LOW - Performance impact
**Files:** All ECG viewer components

**Problem:**
- 60+ `console.log()` calls per second across components
- Logging every render frame, buffer update, scroll position
- Massive performance overhead in browser dev tools

**Example:**
```typescript
logger.log(`[ECGWaveformCanvas] Rendering: width=${width}, height=${height}...`); // 60fps
```

**Impact:**
- ⚠️ Browser dev tools slow down
- ⚠️ Log buffer fills up quickly
- ⚠️ Hard to find relevant log messages

**Fix:** Replace with `logger.debug()` or remove framerate logs

---

## ARCHITECTURAL ISSUES

### Issue #1: Grid and Waveform Not Synchronized 🏗️

**Root Problem:** Two independent rendering systems:

1. **Grid:** Uses `mmToPixels()` → DPI-aware → Medical standard
2. **Waveform:** Uses `height / range` → Canvas-relative → Arbitrary

**Solution Required:**
- Both must use `mmToPixels()` for all dimensions
- Vertical: `pixelsPerMV = mmToPixels(10)` (10mm = 1mV)
- Horizontal: `pixelsPerSample = mmToPixels(25) / 500` (25mm/s at 500Hz)

---

### Issue #2: Scrolling vs Sweep Mode 🏗️

**Current Approach:** Translate waveform left infinitely
- Doesn't match real ECG machines
- Causes disappearing waveform bug

**Real ICU Monitor Approach:** Sweep mode
- Fixed time window on screen (e.g., 8 seconds)
- Red sweep line moves left-to-right
- New data drawn at sweep position
- Old data erased behind sweep
- Wraps at right edge

**Recommendation:** Implement sweep mode (like real monitors)

---

### Issue #3: Canvas Sizing Not Medical-Aware 🏗️

**Current:** Canvas sized by Tailwind CSS classes
**Problem:** Doesn't account for medical requirements

**Medical Requirements:**
- Must show ±2mV at 10mm/mV scale (40mm vertical)
- Must show 8-10 seconds at 25mm/s (200-250mm horizontal)
- Minimum readable: 120px tall (already implemented)

**Solution:** Calculate required canvas size based on:
```typescript
const requiredHeight = mmToPixels(40); // ±2mV at 10mm/mV
const requiredWidth = mmToPixels(200); // 8 seconds at 25mm/s
```

---

## TESTING GAPS

### Missing Tests:

1. ❌ No unit tests for waveform rendering
2. ❌ No integration tests for data flow
3. ❌ No visual regression tests for grid/waveform alignment
4. ❌ No tests for different DPIs (96, 120, 192)
5. ❌ No tests for different canvas sizes
6. ❌ No tests for pause/resume
7. ❌ No tests for mode switching (ECG ↔ EEG)

---

## SUMMARY OF ALL BUGS

| # | Bug | Severity | Medical Impact | Est. Fix Time |
|---|-----|----------|----------------|---------------|
| 1 | Waveform disappears | CRITICAL | Monitoring impossible | 4 hours |
| 2 | Calibration wrong size | CRITICAL | 3× amplitude error | 3 hours |
| 3 | Browser zoom breaks scale | HIGH | Variable accuracy | 2 hours |
| 4 | Gain control not applied | HIGH | Cannot adjust sensitivity | 2 hours |
| 5 | Speed control wrong | MEDIUM | Time measurement error | 1 hour |
| 6 | Sweep line wrong | MEDIUM | Visual confusion | 1 hour |
| 7 | 12-lead not implemented | MEDIUM | Missing feature | 8 hours |
| 8 | No real data from watch | HIGH | Only test pulse visible | Diagnosis needed |
| 9 | Pause doesn't freeze scroll | MEDIUM | Pause half-broken | 1 hour |
| 10 | Console log spam | LOW | Performance hit | 1 hour |

**Total Estimated Fix Time:** 23-25 hours (excluding 12-lead implementation)

---

## RECOMMENDED FIX PRIORITY

### Phase 1: Critical Fixes (Must fix before any use) - 9 hours
1. ✅ Fix waveform disappearing (implement sweep mode) - 4 hours
2. ✅ Fix calibration pulse scaling (sync grid + waveform) - 3 hours
3. ✅ Add zoom detection warning - 2 hours

### Phase 2: High Priority (Improve usability) - 6 hours
4. ✅ Implement gain control - 2 hours
5. ✅ Fix speed control - 1 hour
6. ✅ Diagnose real data flow - 2 hours
7. ✅ Fix pause behavior - 1 hour

### Phase 3: Medium Priority (Polish) - 2 hours
8. ✅ Fix sweep line calculation - 1 hour
9. ✅ Remove console log spam - 1 hour

### Phase 4: Future Enhancement - 8 hours
10. ⏸️ Implement proper 12-lead layout - 8 hours (defer)

**Total Critical Path:** ~17 hours to make system medically usable

---

## USER DECISION REQUIRED

**Question for user:**

Do you want me to:

**Option A:** Fix all critical bugs now (Phase 1 + Phase 2) - ~15 hours
- Waveform stays visible ✅
- Calibration pulse correct size ✅
- Gain/speed controls work ✅
- Pause works correctly ✅
- Zoom warning added ✅

**Option B:** Fix only the most critical (Phase 1 only) - ~9 hours
- Waveform stays visible ✅
- Calibration pulse correct size ✅
- Zoom warning ✅
- Other issues remain for later

**Option C:** Create detailed fix plan, get approval, then implement
- Review proposed fixes first
- Approve each change
- Then implement together

---

## MEDICAL RISK ASSESSMENT

**Current System Risk Level:** 🔴 **CRITICAL - DO NOT USE CLINICALLY**

**Risks:**
- ❌ Amplitude measurements 3× wrong → False LVH diagnosis
- ❌ ST elevation wrong → Missed STEMI or false alarm
- ❌ Monitoring fails after seconds → Cannot detect arrhythmias
- ❌ No consistency across devices → Training impossible

**After Phase 1 Fixes:** 🟡 **CAUTION - Limited Clinical Use**
- ✅ Continuous monitoring works
- ✅ Measurements medically accurate (at 100% zoom)
- ⚠️ Gain/speed controls still broken
- ⚠️ Requires user training (no zoom)

**After Phase 1+2 Fixes:** 🟢 **ACCEPTABLE - Clinical Use Approved**
- ✅ All critical issues resolved
- ✅ Controls work correctly
- ✅ Medical accuracy confirmed
- ✅ Suitable for trained medical staff

---

## REFERENCES

- [WAVEFORM_DISAPPEARS_BUG.md](WAVEFORM_DISAPPEARS_BUG.md) - Bug #1 detailed analysis
- [CALIBRATION_PULSE_SCALING_BUG.md](CALIBRATION_PULSE_SCALING_BUG.md) - Bug #2 detailed analysis
- [GRID_SCALING_ANALYSIS.md](GRID_SCALING_ANALYSIS.md) - Bug #3 detailed analysis
- [CALIBRATION_PULSE_GRID_SQUARES.md](CALIBRATION_PULSE_GRID_SQUARES.md) - Medical standards reference
- [CALIBRATION_PULSE_ANALYSIS.md](CALIBRATION_PULSE_ANALYSIS.md) - Calibration pulse source analysis

---

**End of Comprehensive Audit**

**Next Step:** Await user decision on fix approach (Option A, B, or C)
