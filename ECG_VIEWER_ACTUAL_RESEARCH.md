# ECG Viewer Layout - ACTUAL Research Findings

**Date:** 2025-11-01 13:15
**Task:** Understand why 9-lead and 12-lead don't fit on screen
**Method:** Read actual code files (not assumptions)

---

## Actual Code Structure Found

### File Hierarchy (verified by reading):
```
ECGViewer.tsx (entry point)
  └─> ECGViewerContainer.tsx (main container)
        ├─> ECGViewerHeader.tsx (controls header)
        └─> ECGDisplayGrid.tsx (grid of canvases)
              └─> ECGWaveformCanvas.tsx (individual waveform)
```

---

## Container Layout Analysis

### 1. ECGViewerContainer.tsx (Line 98-99)
```typescript
<div className="fixed inset-0 bg-black z-50 overflow-hidden">
  <div className="h-full w-full bg-black text-white flex flex-col">
```

**What this means:**
- `fixed inset-0` = Covers entire viewport (0,0 to 100vw, 100vh)
- `overflow-hidden` = **BLOCKS ALL SCROLLING** ❌
- `flex flex-col` = Vertical flex layout (header stacks above grid)
- `h-full` = 100% of viewport height

**Children:**
1. ECGViewerHeader (height: auto, ~80-100px based on content)
2. ECGDisplayGrid (takes remaining space)

---

### 2. ECGViewerHeader.tsx (Line 47)
```typescript
<div className="p-4 bg-gray-900 border-b border-gray-700 flex items-center justify-between">
```

**What this means:**
- No fixed height - grows based on content
- `p-4` = 16px padding (Tailwind: 4 × 4px = 16px)
- Content: Title (2 lines) + Controls (1 row)

**Estimated height:**
- Text: ~60px (title + subtitle)
- Padding: 32px (16px top + 16px bottom)
- Border: 1px
- **Total: ~93px**

---

### 3. ECGDisplayGrid.tsx (Line 41-42, 66-74)
```typescript
<div className="flex-1 p-4 overflow-hidden relative" style={{ minHeight: '400px' }}>
  <div className="bg-black rounded-lg border-2 border-gray-700 p-4 h-full flex flex-col" style={{ height: '100%' }}>
    {/* Info bar with Mode, Speed, Scaling, Filter */}
    <div className="flex justify-between items-center mb-4 pb-2 border-b border-gray-800 flex-wrap">
      ...
    </div>

    {/* THE ACTUAL GRID */}
    <div className={`grid ${
      layout === 12 ? 'grid-cols-4' :
      layout === 9 ? 'grid-cols-3' :
      layout === 4 ? 'grid-cols-2' :
      'grid-cols-1'
    } gap-4 flex-1 max-w-full max-h-full overflow-hidden`}
      style={{
        gridAutoRows: layout === 1 ? '1fr' : 'minmax(200px, 1fr)'
      }}>
```

**What this means:**
- `flex-1` = Takes ALL remaining space after header
- `overflow-hidden` = **BLOCKS SCROLLING AGAIN** ❌
- Inner info bar: ~40px height
- Padding: 32px (16px × 2)
- Border: 4px (2px × 2)
- **Actual grid space = viewport height - header - info bar - padding - border**

**Grid configuration:**
- `gridAutoRows: 'minmax(200px, 1fr)'` = **Each row MINIMUM 200px, maximum equal division**
- `gap-4` = 16px gap between cells
- `overflow-hidden` = **THIRD TIME BLOCKING SCROLLING** ❌

---

## The Math (Actual Calculation)

### Available Space Calculation:
```
Viewport Height = window.innerHeight (e.g., 768px on laptop)
- Header = ~93px
- Info bar = ~40px
- Padding = 32px (ECGDisplayGrid outer div)
- Border = 4px
- Padding = 32px (inner black container)
───────────────────────
Available for grid = 768 - 93 - 40 - 32 - 4 - 32 = 567px
```

### Grid Row Requirements:

**12-Lead Mode (4 columns × 3 rows):**
```
3 rows × minmax(200px, 1fr)
Gap between rows: 2 gaps × 16px = 32px
Total needed: (3 × 200px) + 32px = 632px
Available: 567px

OVERFLOW: 632px - 567px = 65px NOT VISIBLE ❌
```

**9-Lead Mode (3 columns × 3 rows):**
```
3 rows × minmax(200px, 1fr)
Gap between rows: 2 gaps × 16px = 32px
Total needed: (3 × 200px) + 32px = 632px
Available: 567px

OVERFLOW: 632px - 567px = 65px NOT VISIBLE ❌
```

**4-Lead Mode (2 columns × 2 rows):**
```
2 rows × minmax(200px, 1fr)
Gap between rows: 1 gap × 16px = 16px
Total needed: (2 × 200px) + 16px = 416px
Available: 567px

FITS: 567px - 416px = 151px extra space ✅
Each row gets: (567px - 16px) / 2 = 275px ✅
```

---

## The Problem (ROOT CAUSE)

**Three layers of `overflow-hidden` prevent scrolling:**
1. ECGViewerContainer.tsx:98 - `overflow-hidden`
2. ECGDisplayGrid.tsx:41 - `overflow-hidden`
3. ECGDisplayGrid.tsx:71 - `overflow-hidden`

**Fixed 200px minimum row height forces overflow:**
- `minmax(200px, 1fr)` sets 200px floor
- On 768px screens, grid needs 632px but only has 567px
- Content is cut off at bottom - **user cannot see bottom row** ❌

---

## Questions I Need to Ask User

Before implementing a fix, I need to know:

1. **Do you want all leads to shrink to fit the screen?**
   - Example: On 768px screen, each row becomes ~180px instead of 200px
   - Pros: Everything visible
   - Cons: Slightly smaller waveforms

2. **What is the minimum acceptable waveform height?**
   - Medical readability requirement
   - 120px? 150px? 180px?

3. **Should layout change on small screens?**
   - Example: 12-lead on small screen → auto-switch to 4-lead?
   - Or just shrink to fit?

4. **What screen sizes do we need to support?**
   - Laptop: 768px, 900px, 1080px?
   - Tablet: 1024px?
   - Large desktop: 1440px, 1920px?

---

## Potential Solutions (Need User Input)

### Option A: Remove minimum height, use only `1fr`
```typescript
gridAutoRows: '1fr' // No minimum
```
- **Result:** Rows shrink to fit available space
- **Risk:** May be too small on very small screens

### Option B: Reduce minimum from 200px to 150px
```typescript
gridAutoRows: layout === 1 ? '1fr' : 'minmax(150px, 1fr)'
```
- **Result:** Fits on 768px screens with room to spare
- **Risk:** Still might overflow on very small screens

### Option C: Dynamic minimum based on viewport
```typescript
const minHeight = Math.max(120, Math.floor((availableHeight - gaps) / rows));
gridAutoRows: `minmax(${minHeight}px, 1fr)`
```
- **Result:** Adapts to any screen size
- **Complexity:** Need to calculate available height and track resize

### Option D: Enable scrolling (user rejected this)
- ❌ User said "I don't want scrolling"

---

## What I Need from User Before Proceeding

**Please answer:**
1. Minimum acceptable waveform height for clinical use?
2. Should I shrink waveforms to fit, or auto-switch layouts?
3. What screen sizes should I test?

**I WILL NOT IMPLEMENT until you confirm the approach.**

---

**Status:** ⏸️ WAITING FOR USER INPUT
