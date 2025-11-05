# ECG Waveform Spacing - Medical Standards Research

## Question: How many squares does 1 wave normally span?

---

## Medical Standards (25mm/s paper speed)

### Grid Specifications:
- **Small square**: 1mm × 1mm = 0.04 seconds (40ms)
- **Large square**: 5mm × 5mm = 0.2 seconds (200ms)
- **Paper speed**: 25mm/s (standard)

### Time Calculations:
```
1mm = 0.04 seconds = 40ms
5mm = 0.2 seconds = 200ms
25mm = 1.0 second
```

---

## Normal ECG Wave Components

### 1. QRS Complex (Just the QRS part, not full PQRST):
- **Duration**: 80-100ms (normal adult)
- **Maximum**: 120ms (beyond this is abnormal/wide)
- **Grid size**: 2-2.5 small squares (2-2.5mm)

### 2. Complete PQRST Complex (One cardiac cycle at different heart rates):

#### At 60 BPM (slowest normal):
```
Cycle length = 60000ms / 60 = 1000ms = 1 second
Distance = 1000ms ÷ 40ms/mm = 25mm
Grid squares = 25mm = 5 large squares = 25 small squares
```

#### At 72 BPM (typical resting):
```
Cycle length = 60000ms / 72 = 833ms
Distance = 833ms ÷ 40ms/mm = 20.8mm
Grid squares = 20.8mm ≈ 4.2 large squares ≈ 21 small squares
```

#### At 100 BPM (fastest normal):
```
Cycle length = 60000ms / 100 = 600ms
Distance = 600ms ÷ 40ms/mm = 15mm
Grid squares = 15mm = 3 large squares = 15 small squares
```

---

## Answer to User's Question

### "How many squares does 1 wave normally span?"

**Normal range**: **3 to 5 large squares** (15mm to 25mm)

- **At 100 BPM**: 3 large squares (15mm)
- **At 72 BPM**: 4.2 large squares (21mm) ← Most common
- **At 60 BPM**: 5 large squares (25mm)

**In small squares**: **15 to 25 small squares** (1mm each)

---

## User's Observation Analysis

### User said:
- "1 wave is 3-4 squares" (assuming LARGE squares = 3-4 × 5mm = 15-20mm)
- "I have 2 waves in a 5mm box" (2 waves in 1 large square)

### What user expects: **CORRECT** ✅
- 1 wave = 3-4 large squares = 15-20mm
- This matches heart rate of 75-100 BPM (normal range)

### What user sees: **WRONG** ❌
- 2 waves in 5mm (1 large square)
- Each wave = 2.5mm
- This means: 1 wave = 2.5mm ÷ 40ms/mm = 100ms per wave
- Heart rate = 60000ms / 100ms = **600 BPM** (IMPOSSIBLE!)

---

## Root Cause

The waveform is **horizontally compressed by 8x** (should be 20mm, but showing as 2.5mm)

**Calculation**:
```
Expected: 20mm per wave (at 72 BPM)
Actual: 2.5mm per wave
Compression factor = 20mm / 2.5mm = 8x
```

---

## Correction Factor

### User needs to multiply `pixelsPerSample` by **8x**:

```typescript
// Current (WRONG):
const pixelsPerSample = pixelsPerSecond / SAMPLE_RATE_HZ;

// Fixed (CORRECT):
const pixelsPerSample = (pixelsPerSecond / SAMPLE_RATE_HZ) * 8.0;
```

**Why 8x?**
- Current: 2 waves in 5mm → 2.5mm per wave
- Expected: 1 wave in 20mm (at 72 BPM)
- Multiplier = 20mm / 2.5mm = **8x**

---

## Alternative Analysis

If user means **small squares** (1mm) instead of large squares (5mm):

### User said "3-4 squares":
- If small squares: 3-4mm = 1 wave
- At 25mm/s: 3mm = 120ms per wave
- Heart rate = 500 BPM (STILL IMPOSSIBLE)

### Conclusion:
User definitely means **large squares** (5mm each), and the waveform is compressed **8x**.

---

## Medical Reference Summary

| Heart Rate | Cycle Time | Distance (25mm/s) | Large Squares | Small Squares |
|------------|------------|-------------------|---------------|---------------|
| 60 BPM     | 1000ms     | 25mm              | 5.0           | 25            |
| 72 BPM     | 833ms      | 20.8mm            | 4.2           | 21            |
| 75 BPM     | 800ms      | 20mm              | 4.0           | 20            |
| 100 BPM    | 600ms      | 15mm              | 3.0           | 15            |

**Normal range**: 3-5 large squares per complete PQRST complex

**User's expectation**: 3-4 large squares = 75-100 BPM ✅ CORRECT

**User's observation**: 2 waves in 1 large square = 600 BPM ❌ IMPOSSIBLE

**Fix**: Multiply `pixelsPerSample` by **8x**
