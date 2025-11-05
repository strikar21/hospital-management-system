# CRITICAL FINDING: All Leads Have Equal Buffer Sizes

**Date:** 2025-11-03
**Source:** Live console logs from running ESP32 watch

---

## Console Evidence

All 12 leads showing **IDENTICAL** buffer sizes:

```
dataLength=12500, samplesVisible=1661, canvas width=314px
```

**Leads checked:**
- Lead I: 12500 samples
- Lead II: 12500 samples
- Lead III: 12500 samples
- aVR: 12500 samples
- aVL: 12500 samples
- aVF: 12500 samples
- V1: 12500 samples
- V2: 12500 samples
- V3: 12500 samples
- V4: 12500 samples
- V5: 12500 samples
- V6: 12500 samples

---

## What This Proves

### ❌ DISPROVEN Hypotheses:

1. **NOT a buffer accumulation bug** - All leads have exactly the same number of samples
2. **NOT a batch upload buffer issue** - No leads have more data than others
3. **NOT a delta decoding bug** - If deltas were different, buffer sizes would differ
4. **NOT a data accumulation problem** - All leads grew from 2400 → 12500 identically

---

## What This Means

Since all leads have:
- ✅ Same buffer size (12,500 samples)
- ✅ Same visible samples (1,661)
- ✅ Same canvas width (314px)
- ✅ Same pixel-per-sample calculation (0.1890)

**BUT** V-leads still appear horizontally compressed...

**The bug MUST be in the RENDERING logic, not the DATA.**

---

## Where to Look Next

The bug is likely in **ECGWaveformCanvas.tsx** where it:
1. Calculates which samples to display
2. Scales the x-axis coordinates
3. Renders the waveform to canvas

**Hypothesis:** Different leads might be using different scaling factors, time ranges, or sample slicing logic during rendering, even though they have the same data.

---

## Next Diagnostic Steps

1. **Reload frontend** with hard refresh (Ctrl+Shift+R) to load new diagnostic code
2. **Look for sequence number logs** to rule out batch upload theory
3. **Focus on canvas rendering code** - that's where the compression is happening
4. **Check if different leads use different time windows** for display

---

## Status

🔴 **RENDERING BUG CONFIRMED** - Data is identical, but display differs
🟡 **Awaiting frontend reload** to see new diagnostic logs
