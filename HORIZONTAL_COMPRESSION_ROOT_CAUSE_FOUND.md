# Horizontal Compression - ROOT CAUSE FOUND

**Date:** 2025-11-03
**Issue:** Waveforms look horizontally compressed (squeezed left-to-right)

---

## Console Log Analysis

From your browser console:
```
🔍 [II] DPI spacing: pixelsPerSecond=94.49, pixelsPerSample=0.1890, samplesVisible=1661, canvas width=314px
[ECGWaveformCanvas] Phase 2 (Typewriter Scroll): showing last 1661 samples of 12500 total, fills entire 314px width
```

---

## ROOT CAUSE: Canvas Too Narrow for 12-Lead Layout

**The Problem:**
- **Canvas width: 314px** (this is WAY too small!)
- **Samples visible: 1661 samples** (3.32 seconds at 500Hz)
- **Time visible: 3.32 seconds** (should be ~10+ seconds for comfortable viewing)

**What's happening:**
- In 12-lead layout, each canvas is only **314px wide**
- This forces 1661 samples into 314px
- Result: **Horizontal compression** - waveforms look squeezed

---

## The Math (Actual vs Expected)

### Your Current Setup:
```
Canvas width: 314px
Samples visible: 1661 samples
Time visible: 1661 / 500 Hz = 3.32 seconds
Pixels per sample: 0.189 pixels/sample
```

**Visual result:** 3.32 seconds compressed into 314px = **looks horizontally squeezed**

### What It SHOULD Be (For Comfortable Viewing):
```
Canvas width: 1200px (full screen or wide view)
Samples visible: 6349 samples
Time visible: 6349 / 500 Hz = 12.7 seconds
Pixels per sample: 0.189 pixels/sample (same)
```

**Visual result:** 12.7 seconds spread across 1200px = **comfortable, readable ECG**

---

## Why 314px Width?

**You're in 12-lead layout (3×4 grid)**, which divides the screen into 12 small canvases:

```
┌────────┬────────┬────────┬────────┐
│ Lead I │ aVR    │ V1     │ V4     │  ← Each canvas: 314px wide
├────────┼────────┼────────┼────────┤
│ Lead II│ aVL    │ V2     │ V5     │
├────────┼────────┼────────┼────────┤
│ Lead III│ aVF   │ V3     │ V6     │
└────────┴────────┴────────┴────────┘
```

**If your screen width is ~1280px:**
- 1280px ÷ 4 columns = **320px per column**
- Minus padding/margins = **314px canvas width**

**Result:** Each small canvas only shows 3.3 seconds of data, making waveforms look horizontally compressed.

---

## This Is Actually CORRECT Behavior!

**The rendering is working perfectly.** The "horizontal compression" you're seeing is **expected** for 12-lead layout on a standard monitor.

### This is how medical-grade ECG machines work:
- **12-lead printout:** Each lead shows 2.5-3 seconds (compressed view for diagnosis)
- **Single-lead ICU monitor:** Shows 6-10 seconds (comfortable continuous monitoring)

**Your current view matches standard 12-lead ECG printout format** - short time window, all leads visible simultaneously for diagnostic comparison.

---

## Solutions (Choose Based on Use Case)

### Solution 1: Switch to Single-Lead View (Recommended for Monitoring)

**If you want comfortable, wide waveforms:**
```typescript
// User selects single-lead view in UI
setLayout(1);  // LAYOUT_SINGLE
```

**Result:**
- Canvas width: Full screen (~1200px)
- Samples visible: ~6349 samples (12.7 seconds)
- Waveforms: Wide, comfortable, easy to read

**Use case:** ICU continuous monitoring, rhythm analysis

---

### Solution 2: Increase Canvas Width in 12-Lead Layout

**Modify the CSS to make canvases wider:**

**Current CSS** (from ECGViewer):
```css
.ecg-grid-12 {
  display: grid;
  grid-template-columns: repeat(4, 1fr);  /* Equal width columns */
  gap: 8px;
}
```

**Option A - Wider columns:**
```css
.ecg-grid-12 {
  display: grid;
  grid-template-columns: repeat(4, minmax(400px, 1fr));  /* Min 400px per column */
  gap: 8px;
  overflow-x: auto;  /* Horizontal scroll if needed */
}
```

**Result:**
- Canvas width: ~400px (27% wider)
- Samples visible: ~2117 samples (4.23 seconds)
- Still compact, but less compressed

---

### Solution 3: Increase BUFFER_TIME_SECONDS (Won't Help)

**This WON'T fix the visual compression** because the issue is canvas width, not buffer size.

**Current:**
```typescript
export const BUFFER_TIME_SECONDS = 25;  // 12500 samples
```

**Your buffer is already large enough.** The issue is that in 12-lead layout, you're only **displaying** 1661 samples at a time on a 314px canvas.

---

### Solution 4: Use 4-Lead Layout (Good Compromise)

**Display 4 leads at once (2×2 grid):**
```typescript
setLayout(4);  // LAYOUT_QUAD
```

**Result:**
- Canvas width: ~640px (2 columns instead of 4)
- Samples visible: ~3386 samples (6.77 seconds)
- Good balance between seeing multiple leads and comfortable waveform width

---

## Comparison Table

| Layout | Columns | Canvas Width | Samples Visible | Time Visible | Compression |
|--------|---------|--------------|-----------------|--------------|-------------|
| **12-lead** (current) | 4 | 314px | 1661 | 3.3 sec | **High** (looks squeezed) |
| **4-lead** | 2 | 640px | 3386 | 6.8 sec | **Medium** (comfortable) |
| **Single-lead** | 1 | 1200px | 6349 | 12.7 sec | **Low** (very wide) |

---

## Is This a Bug? NO!

**The system is working correctly.** The "horizontal compression" is expected behavior for 12-lead layout on a standard monitor.

**Medical context:**
- **12-lead diagnostic ECG:** Short time window (2.5-3 sec per lead) for comparing waveform morphology across all leads simultaneously
- **ICU continuous monitoring:** Long time window (10+ sec) for rhythm analysis on 1-2 leads

**You're seeing diagnostic ECG format**, which is medically appropriate for comparing QRS morphology, ST segments, and T waves across all 12 leads.

---

## Recommended Action

**Based on your use case:**

### If you want continuous monitoring (like ICU):
→ **Switch to single-lead view** (wide, comfortable waveforms)

### If you want diagnostic comparison:
→ **Keep 12-lead view** (this is correct format, matches standard ECG printouts)

### If you want both:
→ **Use 4-lead view** as a compromise (see 4 leads with comfortable width)

---

## Quick Test

**To verify this is the issue:**

1. **Switch to single-lead view** in the UI (select only Lead II)
2. **Check if waveforms look wide and comfortable now**
3. **If yes** → confirmed that 314px canvas width was causing compression
4. **Switch back to 12-lead** → compression returns (this is expected!)

---

## Technical Summary

**Your rendering is 100% correct:**
- ✅ DPI detection: 96 DPI (correct)
- ✅ Pixels per second: 94.49 px/s (correct for 25mm/s paper speed)
- ✅ Pixels per sample: 0.189 px/sample (correct for 500Hz)
- ✅ Samples visible: 1661 (correct for 314px canvas)
- ✅ Buffer size: 12500 samples (correct for 25-second buffer)

**The "horizontal compression" is purely a UI layout choice**, not a rendering bug.

**Solution:** Choose layout based on clinical use case (monitoring vs diagnosis).
