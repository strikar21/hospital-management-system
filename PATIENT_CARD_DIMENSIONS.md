# Patient Card Dimensions - Complete Breakdown

**File:** [PatientCardContainer.tsx](hospital-display-app/src/components/PatientCard/PatientCardContainer.tsx:247-319)

---

## Total Card Height: **330px** (fixed)

```tsx
className="... h-[330px] flex flex-col ..."
```

---

## Component Breakdown:

### 1. PatientCardAlerts
- **Position:** Top of card
- **Height:** Dynamic (based on alerts)
- **Padding:** Managed internally

### 2. PatientCardHeader
- **Height:** **90px** (fixed) - Line 43 in PatientCardHeader.tsx
- **Padding:** `p-2` (8px all around)
- **Border:** `border-b` (bottom border)
- **Internal Layout:**
  - Total height: 90px
  - Padding: 8px top/bottom/left/right
  - Content area: 90px - 16px (top+bottom padding) = 74px

### 3. Main Content Area (`<div className="px-2 flex-1 flex flex-col min-h-0 overflow-hidden">`)
- **Padding:** `px-2` (8px left/right only)
- **Height:** `flex-1` (takes remaining space)
- **Contains:**
  - PatientVitalStrip
  - PatientCardWaveform

#### 3a. PatientVitalStrip
- **Height:** **70px** (fixed) - [PatientVitalStrip.tsx:62](hospital-display-app/src/components/PatientCard/PatientVitalStrip.tsx:62)
- **Padding:** `px-1` (4px left/right)
- **Class:** `flex-shrink-0 h-[70px]`

#### 3b. PatientCardWaveform
- **Height:** **Calculated dynamically** - [PatientCardWaveform.tsx:43-48](hospital-display-app/src/components/PatientCard/PatientCardWaveform.tsx:43-48)
  - Waveform area: 30mm (converted to pixels based on screen DPI)
  - Header: 10px (fixed)
  - Bottom padding: 8px (`pb-2`)
  - **Total:** ~30mm in pixels + 18px ≈ **131px at 96 DPI** (113px + 18px)
- **Padding:** `px-2 pb-2` (8px left/right, 8px bottom)
- **Class:** `flex-shrink-0`

---

## Padding Summary:

### Card Container
- **Outer:** None (card itself has no padding)
- **Border:** `border-l-4` (4px left border for status color)

### Header Section
- **Padding:** `p-2` = 8px on all sides
- **Height:** 90px (includes padding)

### Main Content Area
- **Padding:** `px-2` = 8px left/right only (no top/bottom padding)
- **Height:** `flex-1` (fills remaining space after header)

### Alerts Section
- **Padding:** Managed within PatientCardAlerts component
- **Position:** Absolute or relative (need to check component)

---

## Calculation:

```
Total Card Height: 330px (FIXED)

Components:
- Header: 90px (fixed)
- Main Content Container: px-2 wrapper (8px L/R padding)
  - Vital Strip: 70px (fixed)
  - Waveform: ~131px at 96 DPI (calculated: 30mm + 18px)
- Alerts: Overlayed/positioned separately

Main Content Area Height:
= 330px - 90px (header) = 240px available

Breakdown:
- Vital Strip: 70px
- Waveform: 131px (at 96 DPI)
- Remaining/Spacing: ~39px

Note: The card IS fixed at 330px total height.
Both VitalStrip and Waveform use flex-shrink-0 (won't shrink).
```

---

## Visual Breakdown:

```
┌─────────────────────────────────────┐  ← Total: 330px (FIXED)
│ [Alerts Section - Overlayed]        │
├─────────────────────────────────────┤
│ Header (90px FIXED)                 │  ← h-[90px]
│ ├─ Padding: p-2 (8px all sides)    │
│ ├─ Content: 74px usable height     │
│ ├─ LEFT (30%) | CENTER (40%) |     │
│ │              RIGHT (30%)          │
│ └─ Border-bottom                    │
├─────────────────────────────────────┤
│ Main Content Container (240px)      │  ← flex-1
│ ├─ Padding: px-2 (8px L/R only)    │
│ ├─────────────────────────────────┤ │
│ │ Vital Strip (70px FIXED)        │ │  ← h-[70px] flex-shrink-0
│ │ px-1 padding                    │ │
│ ├─────────────────────────────────┤ │
│ │ Waveform (~131px at 96 DPI)     │ │  ← Calculated, flex-shrink-0
│ │ 30mm + 10px header + 8px pb     │ │
│ │ px-2 pb-2 padding               │ │
│ ├─────────────────────────────────┤ │
│ │ Remaining Space (~39px)         │ │  ← Spacing/flex gap
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
   ↑                                   ↑
   4px left border                    Card shadow
   (status color)
```

---

## Header Internal Layout (90px):

From [PatientCardHeader.tsx](hospital-display-app/src/components/PatientCard/PatientCardHeader.tsx:43):

```tsx
<div className="p-2 border-b flex-shrink-0 h-[90px]">
  <div className="flex items-start h-full gap-2">
    <!-- 30% LEFT | 40% CENTER | 30% RIGHT -->
  </div>
</div>
```

### Header Padding Details:
- **p-2** = padding: 0.5rem = 8px
- **Total Height:** 90px
- **Content Height:** 90px - 16px (8px top + 8px bottom) = **74px**
- **Column Gap:** `gap-2` = 8px between columns

### Header Column Widths:
- **LEFT:** w-[30%] = 30% of content width
- **CENTER:** w-[40%] = 40% of content width
- **RIGHT:** w-[30%] = 30% of content width
- **Gap between columns:** 8px (gap-2)

---

## Summary:

**Total Card:**
- **Height:** **330px** (FIXED - not dynamic)
- **Outer Padding:** None
- **Border:** 4px left (status color indicator)

**Header:**
- **Height:** **90px** (fixed)
- **Padding:** 8px all sides (`p-2`)
- **Usable Height:** 74px (90px - 16px padding)
- **Layout:** 30% LEFT | 40% CENTER | 30% RIGHT

**Vital Strip:**
- **Height:** **70px** (fixed)
- **Padding:** 4px left/right (`px-1`)
- **Class:** `flex-shrink-0` (won't shrink)

**Waveform:**
- **Height:** **~131px at 96 DPI** (calculated dynamically)
  - 30mm waveform area (113px at 96 DPI)
  - 10px header
  - 8px bottom padding
- **Padding:** 8px left/right, 8px bottom (`px-2 pb-2`)
- **Class:** `flex-shrink-0` (won't shrink)

**Main Content Container:**
- **Total Height:** 240px available (330px - 90px header)
- **Padding:** 8px left/right only (`px-2`)
- **Contains:** Vital Strip (70px) + Waveform (131px) + Spacing (~39px)

**All components use camelCase naming** ✅
