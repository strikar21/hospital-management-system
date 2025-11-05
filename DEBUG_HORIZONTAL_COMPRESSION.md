# Debug Horizontal Compression - ACTION REQUIRED

## What I've Done

Added debug logging to diagnose the "2 heartbeats in 1 big square" compression issue.

### Debug Logs Added:

**1. DPI Detection (in medicalWaveformUtils.ts)**
```typescript
console.log(`✅ DPI detected: ${dpi} (cached for future use)`);
console.log(`🔍 1mm = ${pixels} pixels, 5mm big square = ${pixels} pixels`);
```

**2. Spacing Calculations (in ECGWaveformCanvas.tsx)**
```typescript
console.log(`🔍 [Lead Name] DPI spacing: pixelsPerSecond=XX, pixelsPerSample=XX, samplesVisible=XX, canvas width=XXpx`);
```

---

## ACTION NEEDED: Check Your Browser Console

**Please refresh your browser** and open the developer console (F12), then look for these log messages:

### Look For:

1. **DPI Detection Message:**
   ```
   ✅ DPI detected: XXX (cached for future use)
   🔍 1mm = X.XX pixels, 5mm big square = XX.XX pixels
   ```
   **Expected values at your ~121 DPI:**
   - 1mm = 4.76 pixels
   - 5mm big square = 23.8 pixels

2. **Spacing Calculation Messages:**
   ```
   🔍 [Lead II] DPI spacing: pixelsPerSecond=XXX, pixelsPerSample=X.XXXX, samplesVisible=XXXX, canvas width=XXXXpx
   ```
   **Expected values:**
   - pixelsPerSecond = ~119 (for 25mm/s at 121 DPI)
   - pixelsPerSample = ~0.238 (119 ÷ 500Hz)
   - samplesVisible = depends on canvas width
   - canvas width = varies by layout

---

## What The Values Mean

### If DPI is WRONG (e.g., 96 instead of 121):
```
DPI detected: 96
1mm = 3.78 pixels  ← TOO SMALL!
5mm big square = 18.9 pixels  ← Should be 23.8!
pixelsPerSecond = 94.5  ← Should be 119!
pixelsPerSample = 0.189  ← Should be 0.238!
```

**Result:** Everything compressed horizontally by ~20%

### If DPI is CORRECT (121):
```
DPI detected: 121
1mm = 4.76 pixels  ✅
5mm big square = 23.8 pixels  ✅
pixelsPerSecond = 119  ✅
pixelsPerSample = 0.238  ✅
```

---

## Expected Heartbeat Spacing

**At 72 BPM with correct DPI:**
- Time per beat: 833ms
- Distance: 833ms × (25mm/s) = 20.8mm
- Pixels: 20.8mm × 4.76 px/mm = **99 pixels per heartbeat**
- Big squares: 99 ÷ 23.8 = **4.16 big squares per heartbeat** ✅

**What you're seeing (2 beats in 1 square):**
- 2 beats in 5mm = 1 beat in 2.5mm
- 2.5mm × 4.76 px/mm = **11.9 pixels per heartbeat** ❌
- **This is 8.3× TOO COMPRESSED!**

---

## Possible Causes

### 1. DPI Detection Failing
- Browser doesn't support measurement API
- Falls back to 96 DPI
- **Fix:** Force DPI to 121

### 2. Canvas Width Too Small
- If canvas is only ~300px wide instead of 1396px
- Each lead in multi-view gets small canvas
- **Fix:** Verify actual canvas dimensions

### 3. Wrong Data Being Rendered
- Rendering 10× too many samples
- **Fix:** Check `data.length` vs `samplesVisible`

---

## Please Report:

**Copy and paste from your browser console:**

1. The DPI detection line (should appear once when page loads)
2. A few spacing calculation lines (appear frequently)
3. Any error messages

**Also tell me:**
- How many ECG leads are you viewing? (1, 4, 9, or 12?)
- Are you in full-screen view or windowed?

This will help me identify the exact issue!

---

## Quick Test

**To verify the grid is correct:**

1. Open browser dev tools (F12)
2. Inspect canvas element
3. Check computed width and height
4. Measure distance between thick grid lines (should be ~24 pixels at your DPI)

If thick lines are closer together than 24 pixels → DPI detection failed!
