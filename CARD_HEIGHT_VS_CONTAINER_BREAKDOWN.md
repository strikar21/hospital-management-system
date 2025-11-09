# Patient Card Height vs Container Size - Complete Breakdown

## Total Card Height: **330px** (fixed)

---

## Component Breakdown

### 1. **PatientCardContainer** (Outer Card)
```tsx
className="... h-[330px] flex flex-col ..."
```
- **Total Height:** 330px (fixed)
- **Layout:** `flex flex-col` (vertical stacking)
- **Padding:** None on container itself
- **Border:** `border-l-4` = 4px left border (decorative, doesn't affect internal space)

---

### 2. **PatientCardAlerts** (Alert Banner - Absolute Positioned)
```tsx
className="absolute top-0 left-0 right-0 ... px-2 py-1 rounded-t-xl"
```
- **Position:** `absolute` (overlays top, doesn't take layout space)
- **Height:** ~20-24px (text + 8px padding)
- **Padding:** `py-1` = 4px top + 4px bottom
- **Does NOT consume vertical space** in flex layout

---

### 3. **PatientCardHeader**
```tsx
className="p-2 border-b flex-shrink-0 h-[90px]"
```
- **Height:** 90px (fixed)
- **Padding:** `p-2` = 8px all sides (included in 90px)
- **Border-bottom:** 1px
- **Actual content space:** 90px - 16px (padding) = 74px
- **Space consumed:** 90px + 1px border = **91px**

---

### 4. **Main Content Area**
```tsx
className="px-2 flex-1 flex flex-col min-h-0 overflow-hidden"
```
- **Height:** `flex-1` = fills remaining space
- **Padding:** `px-2` = 8px left/right only (NO vertical padding)
- **Layout:** `flex flex-col` (vertical stacking)
- **Calculation:**
  - Total card: 330px
  - Minus header: 91px (90px + 1px border)
  - **Available: 239px**

---

### 5. **PatientVitalStrip** (Inside Main Content Area)
```tsx
className="bg-gray-50 rounded-lg px-1 flex-shrink-0 h-[70px] flex items-center"
```
- **Height:** 70px (fixed)
- **Padding:**
  - Left/Right: `px-1` = 4px each
  - Top/Bottom: 0px
- **Items-center:** Cards vertically centered within 70px
- **Space consumed:** **70px**

---

### 6. **PatientCardWaveform** (Inside Main Content Area)
```tsx
<div className="flex-shrink-0">
  <div style={{ height: `${containerHeightPx}px` }} className="px-2 pb-2 ...">
```

**Dynamic Height Calculation:**
```javascript
waveformHeight = mmToPixels(30)     // 30mm at detected DPI
headerHeight = 10                   // ECG/EEG label header
paddingBottom = 8                   // pb-2
total = waveformHeight + headerHeight + paddingBottom
```

**At different DPIs:**
- **96 DPI:** 131px + 10px + 8px = **149px**
- **120 DPI:** 160px + 10px + 8px = **178px**
- **144 DPI:** 188px + 10px + 8px = **206px**

**Padding:**
- Left/Right: `px-2` = 8px each
- Bottom: `pb-2` = 8px
- Top: 0px (removed)

---

## Space Usage Summary (at 96 DPI)

| Component | Height Used | Cumulative |
|-----------|-------------|------------|
| **PatientCardContainer (Total)** | 330px | 330px |
| **PatientCardAlerts** | 0px (absolute) | 0px |
| **PatientCardHeader** | 91px | 91px |
| **Main Content Area** | 239px available | - |
| ├─ **PatientVitalStrip** | 70px | 70px |
| └─ **PatientCardWaveform** | 149px | 219px |
| **Remaining/Gap** | 20px | 239px |

---

## Visual Layout Diagram

```
┌─────────────────────────────────────────────────────────┐
│ PatientCardContainer: 330px total height                │
│ ┌───────────────────────────────────────────────────┐   │
│ │ PatientCardAlerts (absolute): ~20px overlay      │   │
│ └───────────────────────────────────────────────────┘   │
│                                                          │
│ ┌───────────────────────────────────────────────────┐   │
│ │ PatientCardHeader: 90px + 1px border = 91px      │   │
│ │ (p-2 = 8px padding all sides)                    │   │
│ └───────────────────────────────────────────────────┘   │
│                                                          │
│ ┌───────────────────────────────────────────────────┐   │
│ │ Main Content Area: 239px (flex-1)                │   │
│ │ ┌─────────────────────────────────────────────┐   │   │
│ │ │ PatientVitalStrip: 70px                    │   │   │
│ │ │ (px-1 horizontal padding, items-center)    │   │   │
│ │ └─────────────────────────────────────────────┘   │   │
│ │                                                   │   │
│ │ ┌─────────────────────────────────────────────┐   │   │
│ │ │ PatientCardWaveform: 149px @ 96 DPI        │   │   │
│ │ │ (px-2, pb-2 padding)                       │   │   │
│ │ │   Header: 10px                             │   │   │
│ │ │   Canvas: 30mm = 131px @ 96 DPI           │   │   │
│ │ │   Bottom padding: 8px                      │   │   │
│ │ └─────────────────────────────────────────────┘   │   │
│ │                                                   │   │
│ │ Extra space: 239 - 70 - 149 = 20px               │   │
│ └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## Flex Space Distribution

**Main Content Area (239px available):**
- PatientVitalStrip: **70px** (flex-shrink-0)
- PatientCardWaveform: **149px** @ 96 DPI (flex-shrink-0)
- **Used:** 219px
- **Remaining:** 20px

**Where does the 20px go?**
- Flex distributes extra space based on flex-grow values
- Both components have `flex-shrink-0` (won't shrink)
- Neither has `flex-grow` (won't expand)
- The 20px remains as **unused space** at the bottom
- This space is inside the main content area but not allocated to any component

---

## DPI Variations

### At 96 DPI (Standard):
- Waveform: 131px + 10px + 8px = **149px**
- Main content: 70px + 149px = **219px used**
- Remaining: **20px**

### At 120 DPI (High):
- Waveform: 160px + 10px + 8px = **178px**
- Main content: 70px + 178px = **248px used**
- Remaining: **-9px** (overflow, but main content has overflow-hidden)

### At 144 DPI (Very High):
- Waveform: 188px + 10px + 8px = **206px**
- Main content: 70px + 206px = **276px used**
- Remaining: **-37px** (overflow, but main content has overflow-hidden)

**Note:** At higher DPIs, the waveform may be clipped due to overflow-hidden.

---

## Padding Summary

| Component | Top | Right | Bottom | Left | Total H | Total V |
|-----------|-----|-------|--------|------|---------|---------|
| **Container** | 0 | 0 | 0 | 0 | 0 | 0 |
| **Alerts (absolute)** | 4px | 8px | 4px | 8px | 16px | 8px |
| **Header** | 8px | 8px | 8px | 8px | 16px | 16px |
| **Main Content** | 0 | 8px | 0 | 8px | 16px | 0 |
| **Vital Strip** | 0 | 4px | 0 | 4px | 8px | 0 |
| **Waveform** | 0 | 8px | 8px | 8px | 16px | 8px |

---

## Key Findings

1. **Total fixed card height:** 330px
2. **Header consumes:** 91px (90px + 1px border) = **27.6%**
3. **Main content area:** 239px = **72.4%**
4. **Vital strip:** 70px = **21.2%** of total card
5. **Waveform:** 149px @ 96 DPI = **45.2%** of total card
6. **Unused space:** 20px @ 96 DPI = **6.1%** of total card

---

## Recommendations

If you want to use the remaining 20px space:

### Option 1: Increase Vital Strip Height
- Change from `h-[70px]` to `h-[80px]` or `h-[90px]`
- Uses more of the available space for vital cards

### Option 2: Increase Waveform Height
- Change from 30mm to 32mm or 35mm
- More waveform visibility

### Option 3: Reduce Card Height
- Change from `h-[330px]` to `h-[310px]`
- Eliminates wasted space, more compact cards

### Option 4: Add Gap/Spacing
- Add `gap-5` (20px) to main content area
- Explicitly spaces components instead of leaving unused space
