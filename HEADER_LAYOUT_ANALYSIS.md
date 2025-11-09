# Patient Card Header - Layout Analysis & Recommendation

## Current Layout (30-40-30)

### LEFT Column (30%)
1. Patient Name (semibold, text-sm)
2. Age, Sex, Department
3. Diagnosis
4. **Doctor Name** ← Currently here

### CENTER Column (40%)
- Top 2 alerts (critical first)
- Acknowledge button
- OR "No alerts"

### RIGHT Column (30%)
1. Watch Status + Patient Status badge
2. Ward • Room • Bed

---

## Issues with Current Layout

1. **Doctor name is buried** - It's at the bottom of LEFT column, easy to miss
2. **Right column is sparse** - Only 2 lines vs 4 lines in LEFT
3. **Visual imbalance** - LEFT feels crowded, RIGHT feels empty
4. **Clinical priority unclear** - Doctor name is as important as location for handoffs

---

## Medical Display Best Practices

### Information Hierarchy (Most to Least Important):
1. **Patient Identity** - Name, Age, Sex (instant recognition)
2. **Clinical Status** - Alerts, Patient Status (immediate action needed)
3. **Care Team** - Attending Physician (who to call)
4. **Location** - Ward, Room, Bed (where to go)
5. **Medical Context** - Department, Diagnosis (background info)

### Visual Design Principles:
- **Top-left**: Most critical identity info (eye starts here)
- **Center**: Dynamic/actionable items (alerts, status changes)
- **Top-right**: Static reference info (location, contact)
- **Bottom**: Secondary context (diagnosis, details)

---

## Recommended Layout Options

### **Option A: Doctor to TOP of RIGHT** (RECOMMENDED)
**Rationale**: Doctor name is reference info like room/bed, both answer "where/who"

```
LEFT (30%)                 CENTER (40%)              RIGHT (30%)
────────────────────────   ──────────────────────    ────────────────────────
Patient Name               🚨 Alert 1                Dr. Sarah Johnson
35y, Male • Cardiology     ⚠️ Alert 2                ⚙️ STABLE
Acute MI                   [Acknowledge]             ICU • Room 301 • Bed A
```

**Pros:**
- Doctor name prominent (top-right, easy to scan)
- Balanced: LEFT=3 lines, CENTER=3 lines, RIGHT=3 lines
- Logical grouping: Identity (left), Alerts (center), Reference (right)
- Clean vertical alignment

**Cons:**
- None significant

---

### **Option B: Doctor to BOTTOM of RIGHT**
```
LEFT (30%)                 CENTER (40%)              RIGHT (30%)
────────────────────────   ──────────────────────    ────────────────────────
Patient Name               🚨 Alert 1                ⚙️ STABLE
35y, Male • Cardiology     ⚠️ Alert 2                ICU • Room 301 • Bed A
Acute MI                   [Acknowledge]             Dr. Sarah Johnson
```

**Pros:**
- Doctor name still in RIGHT
- Balanced line count

**Cons:**
- Doctor buried at bottom (scan pattern misses it)
- Less prominent than Option A

---

### **Option C: Keep Doctor in LEFT, Simplify**
```
LEFT (30%)                 CENTER (40%)              RIGHT (30%)
────────────────────────   ──────────────────────    ────────────────────────
Patient Name               🚨 Alert 1                ⚙️ STABLE
35y, M • Cardiology        ⚠️ Alert 2                ICU • Rm 301 • Bed A
Dr. Sarah Johnson          [Acknowledge]
Acute MI
```

**Pros:**
- Keeps doctor with patient identity
- Moves doctor up (more visible)

**Cons:**
- LEFT becomes 4 lines (crowded)
- Still imbalanced vs RIGHT (2 lines)

---

### **Option D: Doctor REPLACES Department**
**Rationale**: Doctor is more immediately useful than department

```
LEFT (30%)                 CENTER (40%)              RIGHT (30%)
────────────────────────   ──────────────────────    ────────────────────────
Patient Name               🚨 Alert 1                ⚙️ STABLE
35y, Male • Dr. Johnson    ⚠️ Alert 2                ICU • Room 301 • Bed A
Acute MI                   [Acknowledge]
```

**Pros:**
- Clean, compact (3-3-2 lines)
- Doctor highly visible (line 2)
- Department often redundant if diagnosis is shown

**Cons:**
- Loses department info (might be needed for patient routing)

---

## FINAL RECOMMENDATION: **Option A**

**Move Doctor Name to TOP of RIGHT Column**

### Why This is Best:

1. ✅ **Clinically Optimal**: "Who is caring" + "Where they are" grouped together
2. ✅ **Visually Balanced**: All columns have 3 lines
3. ✅ **Scan Pattern**: Doctor name in top-right (secondary scan position)
4. ✅ **Information Grouping**:
   - LEFT = Patient Identity (name, demographics, diagnosis)
   - CENTER = Dynamic Status (alerts, actions)
   - RIGHT = Care Reference (doctor, location, status)

### Proposed Implementation:

```tsx
LEFT (30%):
- Patient Name (bold)
- Age, Sex, Department
- Diagnosis

CENTER (40%):
- Alert 1 (most critical)
- Alert 2 (if exists)
- Acknowledge button

RIGHT (30%):
- Dr. [Name]                    ← MOVED HERE (top line)
- Watch + Status badge
- Ward • Room • Bed
```

---

## Alternative Consideration: **Option D** (If space is premium)

If vertical space is very limited, Option D is second-best:
- Combines doctor with demographics line
- Most compact (3 lines max per column)
- Still keeps doctor highly visible

---

## Implementation Impact

### Files to modify:
- `PatientCardHeader.tsx` (line 44-74, 163-204)

### Changes:
1. Remove doctor from LEFT column (line 66-73)
2. Add doctor as first line in RIGHT column
3. Adjust spacing (mb-1 between lines)
4. Right-align doctor name text

### Estimated effort:
- 5 minutes
- Low risk (just moving existing element)
