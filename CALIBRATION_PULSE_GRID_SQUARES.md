# Calibration Pulse - Grid Square Calculation

**Question:** How many big squares does the calibration pulse span?

**Answer:** **2 big squares vertically × 1 big square horizontally**

---

## Medical Grid Background

Standard ECG paper has a grid with:
- **Small squares:** 1mm × 1mm
- **Big squares:** 5mm × 5mm (made up of 5×5 small squares)

Medical standards:
- **Vertical scale:** 10mm = 1mV (ECG amplitude)
- **Horizontal scale:** 25mm/s = paper speed (time axis)

---

## Calibration Pulse Dimensions

From code: [medicalWaveformUtils.ts:494-496](hospital-display-app/src/utils/medicalWaveformUtils.ts#L494-L496)

```typescript
// Medical standard: 1mV pulse = 10mm height, 200ms width (~5mm at 25mm/s)
const pulseHeight = mmToPixels(10); // 1mV = 10mm at detected DPI
const pulseWidth = mmToPixels(5);   // 5mm (~200ms at 25mm/s)
```

**Actual physical dimensions:**
- **Height:** 10mm (1mV standard pulse)
- **Width:** 5mm (200ms duration at 25mm/s paper speed)

---

## Calculation

### Vertical (Height):
- Pulse height: **10mm**
- Big square size: **5mm**
- **10mm ÷ 5mm = 2 big squares vertically**

### Horizontal (Width):
- Pulse width: **5mm**
- Big square size: **5mm**
- **5mm ÷ 5mm = 1 big square horizontally**

---

## Visual Representation

```
┌─────┬─────┬─────┬─────┐
│     │     │     │     │  ← Each square = 5mm × 5mm (big square)
├─────┼─────┼─────┼─────┤
│     │█████│     │     │  ← Calibration pulse spans:
├─────┼█████┼─────┼─────┤     - 2 big squares vertically (10mm = 1mV)
│     │     │     │     │     - 1 big square horizontally (5mm = 200ms)
├─────┼─────┼─────┼─────┤
│     │     │     │     │
└─────┴─────┴─────┴─────┘
```

---

## Why These Dimensions?

### Height: 10mm (2 big squares)

**Medical standard:** 10mm = 1mV for ECG amplitude
- This is THE universal ECG scale used worldwide
- Allows doctors to measure QRS amplitude by counting squares
- Example: QRS complex of 15mm = 1.5mV (potential Left Ventricular Hypertrophy if in lead V5/V6)

### Width: 5mm (1 big square)

**Typical duration:** 200ms at standard paper speed (25mm/s)
- 200ms × 25mm/s = 5mm
- This is the typical duration of a calibration pulse on real ECG machines
- Wide enough to be easily visible
- Not too wide to waste paper/screen space

**Time calculation:**
- 1 big square (5mm) at 25mm/s = 200ms
- This represents 0.2 seconds on the time axis

---

## Code Implementation Details

From [ECGViewerContainer.tsx:51-68](hospital-display-app/src/components/ECGViewer/ECGViewerContainer.tsx#L51-L68):

```typescript
const samplesPerSecond = 500;
const pulseDuration = 0.2; // 200ms pulse (matches 5mm width at 25mm/s)
const totalPulseSamples = Math.floor(samplesPerSecond * pulseDuration); // 100 samples
const pulseADC = 8388608 + (1 * 100000); // 1mV in ADC units (matches 10mm height)
```

**Sample count:**
- 500 samples/second × 0.2 seconds = **100 samples**
- This creates the 5mm wide (1 big square) pulse on screen

---

## Summary Table

| Dimension | Physical Size | Big Squares | Medical Meaning |
|-----------|--------------|-------------|-----------------|
| **Height** | 10mm | **2 big squares** | 1mV amplitude (standard calibration) |
| **Width** | 5mm | **1 big square** | 200ms duration at 25mm/s paper speed |

---

## Real ECG Machine Comparison

On actual hospital ECG machines (GE, Philips, Nihon Kohden):
- Calibration pulse: ✅ Same dimensions (10mm × 5mm)
- Position: Usually at the **start of each lead** on printouts
- Purpose: Verify scale accuracy before interpretation

Our implementation **exactly matches** real medical equipment standards.

---

## Conclusion

The calibration pulse spans:
- **2 big squares vertically** (10mm = 1mV)
- **1 big square horizontally** (5mm = 200ms at 25mm/s)

This is the **internationally standardized** calibration pulse size used in ECG machines worldwide.
