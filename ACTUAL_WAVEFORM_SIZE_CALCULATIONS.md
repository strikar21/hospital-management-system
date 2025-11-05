# Actual Waveform Size Calculations - YOUR SCREEN

## Your Setup
- **Canvas:** 1396 × 572 pixels
- **DPI:** ~121 (calculated from canvas dimensions)

## DPI-to-Pixel Conversion
```typescript
function mmToPixels(mm: number): number {
  const dpi = 121;
  const inches = mm / 25.4;
  return inches * dpi;
}
```

### Medical Grid Squares
- **1mm** = 121/25.4 = **4.76 pixels**
- **5mm (small square)** = **23.8 pixels**
- **10mm (big square horizontal)** = **47.6 pixels**

---

## 1. Calibration Pulse (Frontend Generated)

### From Code ([ECGViewerContainer.tsx:51-64](hospital-display-app/src/components/ECGViewer/ECGViewerContainer.tsx#L51-L64)):
```typescript
const pulseDuration = 0.2; // 200ms pulse
const pulseADC = 8388608 + (1 * 100000); // 1mV in ADC units
```

### Vertical Size (Amplitude):
- **Value:** 1.0 mV
- **Medical standard:** 10mm = 1mV
- **Your screen:** 10mm × 4.76 px/mm = **47.6 pixels**
- **In big squares:** 47.6 ÷ 23.8 = **2.0 big squares** ✅

### Horizontal Size (Time):
- **Duration:** 200ms = 0.2 seconds
- **Medical standard:** 25mm/s paper speed
- **Physical width:** 0.2s × 25mm/s = 5mm = **1 small square**
- **Your screen:** 5mm × 4.76 px/mm = **23.8 pixels**
- **In big squares:** 23.8 ÷ 23.8 = **1.0 big square** ✅

**Calibration pulse:** 2 big squares tall × 1 big square wide ✅ CORRECT!

---

## 2. P Wave (Atrial Depolarization)

### From ESP32 Code (Line 289):
```cpp
amplitude = 0.15 * sin(t * PI);  // Peak at +0.15mV
```

### Vertical Size:
- **Value:** 0.15 mV
- **Medical standard:** 10mm = 1mV → 1.5mm = 0.15mV
- **Your screen:** 1.5mm × 4.76 px/mm = **7.14 pixels**
- **In big squares:** 7.14 ÷ 47.6 = **0.15 big squares** (less than 1 square)

### Expected on Screen:
- **Height:** ~7 pixels above baseline
- **Should be:** Small rounded bump, barely visible

### ❌ PROBLEM: This is TOO SMALL!

**Real ECG P waves should be:** 0.5-2.5mm tall (not 1.5mm total, but 2.5-12.5mm!)

---

## 3. Q Wave (Initial Negative)

### From ESP32 Code (Line 301):
```cpp
amplitude = -0.15 * (t / 0.25);  // Max: -0.15mV
```

### Vertical Size:
- **Value:** -0.15 mV (negative)
- **Your screen:** 1.5mm × 4.76 px/mm = **7.14 pixels DOWN**

### Expected on Screen:
- **Small downward dip:** ~7 pixels below baseline
- **In big squares:** 0.15 big squares down

### ❌ PROBLEM: Also too small, but Q waves CAN be tiny or absent in some leads

---

## 4. R Wave (MAIN SPIKE) - THE BIGGEST PROBLEM

### From ESP32 Code (Line 306):
```cpp
amplitude = -0.15 + 1.7 * sin(r_t * PI);  // Peak at ~1.5 mV
// Calculation: -0.15 + (1.7 × 1.0) = 1.55mV peak
```

### Vertical Size:
- **Value:** 1.55 mV (peak)
- **Medical standard:** 10mm = 1mV → 15.5mm = 1.55mV
- **Your screen:** 15.5mm × 4.76 px/mm = **73.8 pixels**
- **In big squares:** 73.8 ÷ 47.6 = **1.55 big squares**

### Expected on Screen:
- **Height:** ~74 pixels above baseline
- **In big squares:** About **3.1 small squares** (or 1.55 big squares)

### ✅ This is CORRECT for Lead II! (Normal R wave is 5-15mm tall)

**BUT WAIT... Let's check what's ACTUALLY being displayed!**

---

## 5. S Wave (Final Negative)

### From ESP32 Code (Line 311):
```cpp
amplitude = -0.25 * (1.0 - s_t);  // Max: -0.25mV
```

### Vertical Size:
- **Value:** -0.25 mV
- **Your screen:** 2.5mm × 4.76 px/mm = **11.9 pixels DOWN**
- **In big squares:** 0.25 big squares down

### ❌ PROBLEM: Too small again

---

## 6. T Wave (Ventricular Repolarization)

### From ESP32 Code (Line 321):
```cpp
amplitude = 0.30 * sin(t * PI);  // Peak at +0.30mV
```

### Vertical Size:
- **Value:** 0.30 mV
- **Medical standard:** 3mm = 0.30mV
- **Your screen:** 3mm × 4.76 px/mm = **14.3 pixels**
- **In big squares:** 0.30 big squares (about 1.5 small squares)

### ✅ This is actually CORRECT! (T wave should be ~1-5mm)

---

## THE ACTUAL PROBLEM: ESP32 Amplitudes Are TOO SMALL!

### What SHOULD the values be for realistic ECG?

| Component | Current ESP32 | Should Be (Normal Adult) | Error |
|-----------|---------------|--------------------------|-------|
| **P wave** | 0.15 mV | **0.25 mV** (2.5mm) | ❌ 40% too small |
| **Q wave** | -0.15 mV | -0.1 to -0.3 mV | ✅ OK |
| **R wave** | 1.55 mV | **0.5-2.0 mV** (5-20mm) | ✅ OK |
| **S wave** | -0.25 mV | **-0.1 to -0.5 mV** | ✅ OK |
| **T wave** | 0.30 mV | **0.1-0.5 mV** (1-5mm) | ✅ OK |

### Lead-Specific Multipliers Make It Worse!

From ESP32 code (lines 333-360):
```cpp
case 0:  // Lead I
    leadMultiplier = 0.75;  // 75% amplitude
    // R wave becomes: 1.55 × 0.75 = 1.16mV ← Still OK

case 2:  // V1
    leadMultiplier = 0.50;  // 50% amplitude
    // R wave becomes: 1.55 × 0.50 = 0.775mV ← TOO SMALL!
    // P wave becomes: 0.15 × 0.50 = 0.075mV ← INVISIBLE!
```

---

## What You're Actually Seeing on Screen

### Canvas: 1396 × 572 pixels

### P Wave:
- **Lead II (1.0×):** 0.15mV × 47.6px/mV = **7.1 pixels** (barely visible)
- **V1 (0.5×):** 0.075mV × 47.6px/mV = **3.6 pixels** (INVISIBLE!)

### R Wave:
- **Lead II (1.0×):** 1.55mV × 47.6px/mV = **73.8 pixels** ✅ Good!
- **V1 (0.5×):** 0.775mV × 47.6px/mV = **36.9 pixels** (too small!)
- **V4 (1.25×):** 1.94mV × 47.6px/mV = **92.3 pixels** ✅ Perfect!

### T Wave:
- **Lead II (1.0×):** 0.30mV × 47.6px/mV = **14.3 pixels** ✅ Good!
- **V1 (0.5×):** 0.15mV × 47.6px/mV = **7.1 pixels** (barely visible)

---

## THE REAL BUG: Frontend Rendering Uses Wrong Scale!

Wait, let me check the frontend rendering code...

### From medicalWaveformUtils.ts (Line 338):
```typescript
pixelsPerUnit = mmToPixels(ECG_SCALE_MM_PER_MV);
```

### What is ECG_SCALE_MM_PER_MV?

Let me check the constants...

```typescript
export const ECG_SCALE_MM_PER_MV = 10; // 10mm = 1mV (medical standard)
```

So:
```typescript
pixelsPerUnit = mmToPixels(10) = 10mm × 4.76px/mm = 47.6 pixels per mV
```

### This is CORRECT! ✅

But wait, let me check the actual rendering...

### From Line 378-381:
```typescript
const value = adcToMillivolts(samplesToRender[i]);
const y = baseline - (value * pixelsPerUnit);
```

### And adcToMillivolts():
```typescript
export function adcToMillivolts(adc: number): number {
  const midpoint = 8388608; // 24-bit ADC center (0mV)
  const offset = adc - midpoint;
  return offset / 100000; // 100,000 ADC units = 1mV
}
```

---

## CALCULATION VERIFICATION

### Example: R wave peak from ESP32

**ESP32 generates:**
```cpp
amplitude = 1.55;  // mV
sample = 8388608 + (int32_t)(amplitude * 100000);
sample = 8388608 + 155000 = 8543608
```

**Frontend receives 8543608:**
```typescript
value = adcToMillivolts(8543608);
value = (8543608 - 8388608) / 100000;
value = 155000 / 100000 = 1.55 mV ✅

y = baseline - (1.55 * 47.6);
y = baseline - 73.78 pixels ✅ CORRECT!
```

---

## CONCLUSION

### ✅ What's CORRECT:
1. **Calibration pulse:** 2×1 big squares (1mV × 200ms) ✅
2. **Frontend rendering:** Uses correct 10mm/mV scale ✅
3. **ADC conversion:** Correctly converts to mV ✅
4. **R wave in Lead II:** 1.55mV = 73.8 pixels = 3.1 small squares ✅
5. **T wave:** 0.30mV = 14.3 pixels ✅

### ❌ What's WRONG (ESP32 Physiological Simulator):
1. **P wave TOO SMALL:** 0.15mV should be 0.25mV
2. **Lead multipliers too aggressive:** V1 at 0.5× makes everything tiny
3. **Q and S waves too small** (but less critical)

### The Math:
- **Your DPI:** 121
- **1mV on screen:** 47.6 pixels (correct!)
- **R wave:** 1.55mV = 73.8 pixels = **1.55 big squares tall** ✅
- **Calibration:** 1.0mV = 47.6 pixels = **2.0 big squares tall** ✅

**The rendering IS correct!** The ESP32 simulator just generates small P/Q/S waves, which is medically... actually somewhat realistic for certain leads!

---

## What You Should Actually See

On your 1396×572 canvas with 121 DPI:

### Calibration Pulse:
- **Height:** 48 pixels (2 big squares)
- **Width:** 24 pixels (1 big square)
- **Tail:** 24 pixels flat at 0mV

### Lead II (Standard View):
- **P wave:** 7 pixels tall (small bump)
- **Q wave:** 7 pixels down (small dip)
- **R wave:** 74 pixels tall (BIG spike - tallest part!)
- **S wave:** 12 pixels down (small dip)
- **T wave:** 14 pixels tall (medium bump)
- **Flat segments:** Exactly at centerline (0mV)

### Is This Realistic?

**YES!** Real ECG varies MASSIVELY:
- Some leads have tiny P waves
- Some leads have no Q wave at all
- V1 typically has small R and deep S (transitional lead)
- Lead II typically has tallest R wave

**Your system is rendering EXACTLY what the ESP32 is sending, with medically accurate scaling!** ✅

---

## IF You Want Bigger/More Visible Waveforms

You'd need to modify the ESP32 simulator amplitudes in `PhysiologicalSimulator.cpp`:

```cpp
// CURRENT:
amplitude = 0.15 * sin(t * PI);  // P wave: 0.15mV

// MAKE BIGGER:
amplitude = 0.25 * sin(t * PI);  // P wave: 0.25mV (more visible)
```

But the **frontend rendering is 100% CORRECT** - it's displaying exactly what it receives at the correct medical scale!
