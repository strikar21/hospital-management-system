# Vital Strip Component - Detailed Height & Padding Breakdown

**File:** `hospital-display-app/src/components/PatientCard/PatientVitalStrip.tsx`

---

## Component Structure

```
PatientVitalStrip
└── Container (line 62)
    └── vital-scroll wrapper (line 63)
        └── vitals-infinite-scroll flex container (line 64-65)
            ├── Individual Vital Cards (line 73-92) x N (repeated 3 times for infinite scroll)
            └── ECG/EEG Cards (line 96-116) x 3 (repeated for infinite scroll)
```

---

## 1. Vital Strip Container (Line 62)

```tsx
<div className="bg-gray-50 rounded-lg px-1 flex-shrink-0 h-[70px] flex items-center">
```

### Dimensions:
- **Height:** `h-[70px]` = **70px (fixed)**
- **Width:** Full width (no constraint)

### Padding:
- **Top:** `0px` (no vertical padding)
- **Right:** `4px` (from `px-1`)
- **Bottom:** `0px` (no vertical padding)
- **Left:** `4px` (from `px-1`)
- **Total horizontal padding:** 8px (4px left + 4px right)
- **Total vertical padding:** 0px

### Other Styling:
- Background: `bg-gray-50` (light gray)
- Border radius: `rounded-lg` = 8px
- Display: `flex`
- Align items: `items-center` (vertically centered)
- Flex shrink: `flex-shrink-0` (won't shrink)

---

## 2. Vital Scroll Wrapper (Line 63)

```tsx
<div className="vital-scroll w-full">
```

### Dimensions:
- **Height:** Inherits from parent = **70px**
- **Width:** `w-full` = **100% of parent**

### Padding:
- **None** (0px all sides)

---

## 3. Vitals Infinite Scroll Container (Line 64-65)

```tsx
<div className="flex space-x-1 vitals-infinite-scroll"
     style={{ minWidth: 'max-content', scrollSnapType: 'x mandatory' }}>
```

### Dimensions:
- **Height:** Inherits from parent = **70px**
- **Width:** `minWidth: 'max-content'` (expands to fit all cards)

### Padding:
- **None** (0px all sides)

### Spacing:
- **Between children:** `space-x-1` = **4px horizontal gap** between each card

### Other Styling:
- Display: `flex`
- Scroll snap: `x mandatory` (for smooth scrolling)

---

## 4. Individual Vital Card (Line 75)

```tsx
<div className={`flex flex-col items-center justify-center p-1 rounded hover:bg-blue-50
     cursor-pointer transition-colors min-w-[60px] flex-shrink-0 h-full
     ${getVitalColorClass(vital.alertStatus)}`}>
```

### Dimensions:
- **Height:** `h-full` = **70px (inherits from container)**
- **Min-width:** `min-w-[60px]` = **60px minimum**
- **Actual width:** Auto (based on content, but at least 60px)

### Padding:
- **Top:** `4px` (from `p-1`)
- **Right:** `4px` (from `p-1`)
- **Bottom:** `4px` (from `p-1`)
- **Left:** `4px` (from `p-1`)
- **Total padding:** 4px all sides

### Internal Content (Line 87-91):

#### Icon + Label Row (Line 87-90):
```tsx
<div className="flex items-center space-x-1 mb-0.5">
  <vital.icon className="w-3 h-3" />
  <span className="text-xs font-medium">{vital.label}</span>
</div>
```
- **Icon size:** `w-3 h-3` = **12px × 12px**
- **Label font:** `text-xs` = **12px font size**
- **Gap between icon and label:** `space-x-1` = **4px**
- **Bottom margin:** `mb-0.5` = **2px**

#### Value Row (Line 91):
```tsx
<span className="text-xs font-bold">{vital.value}{vital.unit}</span>
```
- **Font size:** `text-xs` = **12px**
- **Font weight:** `font-bold` = **700**

### Color Classes (Based on Alert Status):
- **Critical:** `text-red-600 bg-red-50 border-l-4 border-red-500`
- **High:** `text-orange-600 bg-orange-50 border-l-4 border-orange-500`
- **Warning/Medium:** `text-yellow-600 bg-yellow-50 border-l-4 border-yellow-500`
- **Low:** `text-amber-600 bg-amber-50 border-l-4 border-amber-500`
- **Normal:** `text-green-600 bg-green-50 border-l-4 border-green-500`

### Border:
- **Left border:** `border-l-4` = **4px left border** (color varies by alert status)

### Other Styling:
- Display: `flex flex-col` (vertical layout)
- Alignment: `items-center` (horizontally centered)
- Justification: `justify-center` (vertically centered)
- Hover: `hover:bg-blue-50` (light blue on hover)
- Cursor: `cursor-pointer`
- Transitions: `transition-colors`
- Flex shrink: `flex-shrink-0` (won't shrink)

---

## 5. ECG/EEG Card (Line 99)

```tsx
<div className="flex flex-col items-center justify-center p-1 rounded hover:bg-blue-50
     cursor-pointer transition-colors min-w-[60px] flex-shrink-0 h-full
     bg-green-50 text-green-600">
```

### Dimensions:
- **Height:** `h-full` = **70px (inherits from container)**
- **Min-width:** `min-w-[60px]` = **60px minimum**

### Padding:
- **Top:** `4px` (from `p-1`)
- **Right:** `4px` (from `p-1`)
- **Bottom:** `4px` (from `p-1`)
- **Left:** `4px` (from `p-1`)
- **Total padding:** 4px all sides

### Internal Content (Line 105-109):

#### Icon + Label Row (Line 105-108):
```tsx
<div className="flex items-center space-x-1 mb-0.5">
  {isECGMode ? <Brain className="w-3 h-3" /> : <Heart className="w-3 h-3" />}
  <span className="text-xs font-medium">{isECGMode ? 'EEG' : 'ECG'}</span>
</div>
```
- **Icon size:** `w-3 h-3` = **12px × 12px**
- **Label font:** `text-xs` = **12px font size**
- **Gap between icon and label:** `space-x-1` = **4px**
- **Bottom margin:** `mb-0.5` = **2px**

#### Value Row (Line 109):
```tsx
<span className="text-xs font-bold">
```
- **Font size:** `text-xs` = **12px**
- **Font weight:** `font-bold` = **700**

### Color:
- **Background:** `bg-green-50` (light green)
- **Text:** `text-green-600` (green)

### Other Styling:
- Same as individual vital cards (flex, centered, hover effects, etc.)

---

## Summary Table

| Component | Height | Padding Top | Padding Right | Padding Bottom | Padding Left | Horizontal Gap |
|-----------|--------|-------------|---------------|----------------|--------------|----------------|
| **Vital Strip Container** | 70px | 0px | 4px | 0px | 4px | - |
| **Vital Scroll Wrapper** | 70px (inherited) | 0px | 0px | 0px | 0px | - |
| **Infinite Scroll Container** | 70px (inherited) | 0px | 0px | 0px | 0px | 4px (between cards) |
| **Individual Vital Card** | 70px (inherited) | 4px | 4px | 4px | 4px | - |
| **ECG/EEG Card** | 70px (inherited) | 4px | 4px | 4px | 4px | - |

---

## Visual Calculation

### Total Container Space:
```
┌─────────────────────────────────────────────────────────┐
│ Vital Strip Container: 70px height                      │
│ ┌───────────────────────────────────────────────────┐   │
│ │ 4px padding-left │ Cards │ 4px padding-right      │   │
│ │                                                    │   │
│ │  ┌────┐ 4px ┌────┐ 4px ┌────┐ 4px ┌────┐         │   │
│ │  │Card│ gap │Card│ gap │Card│ gap │Card│...      │   │
│ │  │60px│     │60px│     │60px│     │60px│         │   │
│ │  │min │     │min │     │min │     │min │         │   │
│ │  └────┘     └────┘     └────┘     └────┘         │   │
│ │                                                    │   │
│ └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Individual Card Space:
```
┌─────────────────────────────────────┐
│ Card: 70px height, 60px min-width   │
│ ┌─────────────────────────────────┐ │
│ │ 4px padding-top                 │ │
│ │ ┌─────────────────────────────┐ │ │
│ │ │  ╔═══╗                       │ │ │
│ │ │  ║ ♥ ║ HR                    │ │ │  ← Icon (12px) + Label (12px font)
│ │ │  ╚═══╝                       │ │ │
│ │ │  2px margin-bottom           │ │ │
│ │ │  75 bpm                      │ │ │  ← Value (12px font, bold)
│ │ └─────────────────────────────┘ │ │
│ │ 4px padding-bottom              │ │
│ └─────────────────────────────────┘ │
│   4px ←→ 4px                        │
│   padding                           │
└─────────────────────────────────────┘
```

---

## Total Space Used

### Horizontal (per card):
- Card min-width: 60px
- Card padding: 4px (left) + 4px (right) = 8px internal
- Gap after card: 4px
- **Total per card:** ~64px minimum

### Vertical:
- Container height: 70px
- Container padding: 0px (top/bottom)
- Card inherits full 70px height
- Card internal padding: 4px (top) + 4px (bottom) = 8px
- **Available content area:** 62px (70px - 8px padding)

---

## Notes

1. **No header in PatientVitalStrip** - component starts directly with cards
2. **Infinite scroll** - vitals array is repeated 3 times for seamless scrolling
3. **Alert-based coloring** - left border and background color change based on vital status
4. **Fixed heights** - all components use fixed 70px height for consistency
5. **Minimum width** - cards won't shrink below 60px
6. **Zero vertical padding on container** - no wasted space above/below vital strip
