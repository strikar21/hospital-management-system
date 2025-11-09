# Spacing Between Header Bottom Border and ECG/EEG Waveform

## Layout Breakdown:

```
┌─────────────────────────────────────┐
│ Header (90px)                       │
│ └─ border-b ─────────────────────── │ ← Header bottom border
├─────────────────────────────────────┤
│ Main Content Container              │ ← px-2 (8px L/R padding)
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Vital Strip (70px)              │ │ ← Starts immediately
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ ECG/EEG Waveform                │ │ ← Starts after Vital Strip
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

## Code Analysis:

### 1. Header (PatientCardHeader.tsx:43)
```tsx
<div className="pt-2 px-2 border-b flex-shrink-0 h-[90px]">
```
- Height: 90px
- Bottom border: border-b (thin line, ~1px)

### 2. Main Content Container (PatientCardContainer.tsx:288)
```tsx
<div className="px-2 flex-1 flex flex-col min-h-0 overflow-hidden">
```
- NO top/bottom padding (only `px-2` = left/right)
- Layout: `flex flex-col` (vertical stack)

### 3. Vital Strip (PatientVitalStrip.tsx:62)
```tsx
<div className="bg-gray-50 rounded-lg px-1 flex-shrink-0 h-[70px] flex items-center">
```
- Height: 70px
- NO margin-top or margin-bottom

### 4. Waveform (PatientCardWaveform.tsx:52-55)
```tsx
<div className="flex-shrink-0">
  <div style={{ height: `${containerHeightPx}px` }}
       className="px-2 pb-2 bg-gray-900 rounded-lg ...">
```
- NO margin-top or margin-bottom
- Starts immediately after Vital Strip

## Calculation:

**Distance from Header Bottom Border to ECG/EEG Waveform:**

```
Header bottom border
        ↓
        0px gap (Main Container has no top padding)
        ↓
Vital Strip starts (70px height)
        ↓
        0px gap (no margin between Vital Strip and Waveform)
        ↓
ECG/EEG Waveform starts
```

### Answer:

**Total Height = 70px**

This is ONLY the Vital Strip height. There is:
- **0px** gap between header bottom border and Vital Strip
- **0px** gap between Vital Strip and Waveform

The ECG/EEG waveform starts **exactly 70px below** the header's bottom border.

---

## Visual Representation:

```
Header (90px total)
├─ Top padding: 8px
├─ Content: 82px
└─ Bottom border ━━━━━━━━━━━━━━━━━━━━ ← Reference point (0px)
                                      ↓
Main Content Container (px-2 only)    ↓ 0px gap
                                      ↓
┌──────────────────────────────────┐  ↓
│ Vital Strip (70px)               │ ←┘
│ - bg-gray-50                     │
│ - rounded-lg                     │
│ - Scrolling vitals display       │
└──────────────────────────────────┘
                                      ↓ 0px gap
┌──────────────────────────────────┐  ↓
│ ECG/EEG Waveform (~131px)        │ ←┘ Starts here
│ - bg-gray-900                    │
│ - Medical waveform display       │
└──────────────────────────────────┘
```

---

## Summary:

- **Direct distance:** 70px (the Vital Strip)
- **No gaps/spacing** between components
- Components stack immediately one after another
- Main Container has `px-2` (horizontal padding only)
