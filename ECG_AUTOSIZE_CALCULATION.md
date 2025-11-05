# ECG Auto-Sizing Calculation for 1920x1024 Screen

**Date:** 2025-11-01 13:30
**User Screen:** 15.6" laptop, 1920x1024 resolution
**Requirement:** Auto-size waveforms to fit all leads on screen (no scrolling)

---

## Research Findings

### Medical ECG Standards (Web Search):
- **Paper Standard:** 10mm = 1mV, speed 25mm/s or 50mm/s
- **Grid Layout:** 4 columns × 3 rows for 12-lead
- **Commercial Devices:**
  - 10.1" screens @ 1024x600
  - 12.1" screens @ 800x600
  - 15" multi-touch displays
- **No explicit pixel height minimum** in medical standards
- Focus on **signal quality** (500 samples/sec) not display pixels

### Practical Observation:
- Commercial ECG devices use 800x600 to 1920x1080 displays
- 12-lead layout fits on these screens
- **Implies minimum waveform height: ~150-180px is clinically acceptable**

---

## User Screen Analysis

### Your Setup:
- **Resolution:** 1920 × 1024
- **Laptop:** 15.6" diagonal
- **Aspect:** 16:9 (wide)
- **Available height:** ~1024px

### Browser Chrome Overhead:
- Address bar + tabs: ~70-80px
- **Usable viewport:** ~944px height

---

## Available Space Calculation (Your Screen)

```
Viewport Height: 944px (1024px - 80px browser chrome)

ECG Viewer Layout:
├─ Header (ECGViewerHeader): ~93px
│    ├─ Title + subtitle: 60px
│    ├─ Padding (16px × 2): 32px
│    └─ Border: 1px
│
└─ Display Grid (ECGDisplayGrid): 851px remaining
     ├─ Info bar (Mode/Speed/Scaling): ~40px
     ├─ Outer padding (16px × 2): 32px
     ├─ Border (2px × 2): 4px
     ├─ Inner padding (16px × 2): 32px
     │
     └─ Actual grid space: 743px

Grid Space Breakdown:
─────────────────────────
944px (viewport)
-  93px (header)
-  40px (info bar)
-  68px (padding + borders)
═════════════════════════
 743px available for grid
```

---

## Layout Calculations

### 12-Lead Mode (4 columns × 3 rows):

**Current (broken):**
```
3 rows × 200px min = 600px
+ 2 gaps × 16px = 32px
= 632px needed
< 743px available ✅ SHOULD FIT!
```

**Wait, why doesn't it fit then?**

Let me recalculate including ALL spacing:

```
Grid gaps:
- Column gaps: 3 gaps × 16px = 48px (horizontal)
- Row gaps: 2 gaps × 16px = 32px (vertical)

Row height with minmax(200px, 1fr):
- CSS tries: 200px × 3 = 600px
- Plus gaps: 600 + 32 = 632px
- Available: 743px
- Each row gets: (743 - 32) / 3 = 237px ✅

ACTUALLY FITS on your screen!
```

**Aha! The problem is likely:**
1. **Smaller screens** (768px height) where it doesn't fit
2. **Or the calculation is wrong** - let me check the actual flex-1 behavior

---

## Flex Layout Reality Check

**ECGDisplayGrid outer div:**
```typescript
<div className="flex-1 p-4 overflow-hidden relative" style={{ minHeight: '400px' }}>
```

**Problem:** `flex-1` takes ALL remaining space, but:
- Parent is `flex flex-col` (ECGViewerContainer)
- Parent has `h-full` (100% of viewport)
- Header takes ~93px
- **ECGDisplayGrid should get: 944px - 93px = 851px**

**Inside ECGDisplayGrid:**
- Outer padding: 32px (16 × 2)
- Inner container has `h-full` with padding: 32px
- Info bar: ~40px
- **Grid gets: 851 - 32 - 32 - 40 = 747px** ✅

**With 3 rows:**
- Row gaps: 32px
- Each row: (747 - 32) / 3 = **238px per row** ✅

---

## Minimum Height Research

### From Commercial Devices:
- 800x600 screens show 12-lead ECG
- Header ~80px, info ~40px, spacing ~60px
- Grid space: 600 - 180 = 420px
- Per row (3 rows): 420 / 3 = **140px minimum**

### From Medical Practice:
- Cardiologists need to see:
  - P wave (~2-3mm = 20-30px at 10mm/mV)
  - QRS complex (~10-15mm = 100-150px at 10mm/mV)
  - T wave (~5mm = 50px at 10mm/mV)
- **Minimum readable: ~120-150px waveform height**

### Recommendation:
- **Absolute minimum: 120px** (emergency fallback)
- **Comfortable minimum: 150px** (readable for most cases)
- **Your screen gives: 238px** (excellent! plenty of room)

---

## Auto-Sizing Implementation Plan

### Strategy:
```typescript
const calculateRowHeight = (
  layout: number,
  viewportHeight: number
): string => {
  if (layout === 1) return '1fr'; // Single lead uses full space

  // Calculate rows
  const rows = layout === 12 ? 3 : layout === 9 ? 3 : layout === 4 ? 2 : 1;

  // Reserve overhead
  const headerHeight = 93;
  const infoBarHeight = 40;
  const paddingAndBorders = 68;
  const overhead = headerHeight + infoBarHeight + paddingAndBorders;

  // Calculate available space
  const availableHeight = viewportHeight - overhead;

  // Calculate gaps
  const gapSize = 16;
  const totalGaps = (rows - 1) * gapSize;

  // Calculate height per row
  const usableHeight = availableHeight - totalGaps;
  const heightPerRow = Math.floor(usableHeight / rows);

  // Apply minimum (120px absolute floor)
  const minHeight = 120;
  const finalHeight = Math.max(minHeight, heightPerRow);

  return `${finalHeight}px`;
};
```

### Results for Different Screens:

**Your screen (1920x1024, viewport 944px):**
- 12-lead: (944 - 201) / 3 = **247px per row** ✅ Excellent
- 9-lead: (944 - 201) / 3 = **247px per row** ✅ Excellent
- 4-lead: (944 - 201) / 2 = **371px per row** ✅ Spacious

**Common laptop (1920x1080, viewport 1000px):**
- 12-lead: (1000 - 201) / 3 = **266px per row** ✅ Excellent
- 9-lead: (1000 - 201) / 3 = **266px per row** ✅ Excellent

**Small laptop (1366x768, viewport 688px):**
- 12-lead: (688 - 201) / 3 = **162px per row** ✅ Readable
- 9-lead: (688 - 201) / 3 = **162px per row** ✅ Readable

**Tiny screen (1024x600, viewport 520px):**
- 12-lead: (520 - 201) / 3 = **106px per row** ❌ Too small
- Falls back to minimum: **120px** ⚠️ Acceptable but tight

---

## Implementation Changes

### Files to Modify:

1. **ECGDisplayGrid.tsx:**
   - Add viewport height tracking
   - Add `calculateRowHeight()` function
   - Use dynamic height in grid style
   - Remove `overflow-hidden` (not needed if sizing correctly)

2. **ECGViewerContainer.tsx:**
   - Remove `overflow-hidden` (allow fallback scrolling on tiny screens)

---

## Next Steps

**Ready to implement?**

This will:
- ✅ Auto-size waveforms to fit your 1920x1024 screen (247px per row)
- ✅ Work on common laptops (162px-266px per row)
- ✅ Maintain 120px minimum for readability
- ✅ Allow fallback scrolling only on very small screens (<600px height)
- ✅ No scrolling on normal screens

**Shall I proceed with implementation?**
