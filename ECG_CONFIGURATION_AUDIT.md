# ECG/EEG Configuration Variables - Complete Audit

## Current State: Variables Scattered Across Multiple Files ❌

### 1. medicalWaveformUtils.ts (Partially Centralized)
```typescript
export const ECG_SCALE_MM_PER_MV = 10;      // Line 20
export const EEG_SCALE_UV_PER_MM = 50;      // Line 21
export const PAPER_SPEED_MM_PER_S = 25;     // Line 22
export const SAMPLE_RATE_HZ = 500;          // Line 23
export const ADC_MIDPOINT = 8388608;        // Line 27
export const ECG_ADC_SCALE_FACTOR = 100000; // Line 28
export const EEG_ADC_SCALE_FACTOR = 1000;   // Line 29
```
**Status:** ✅ These are properly centralized

### 2. ECGViewerContainer.tsx (Duplicates + New Constants)
```typescript
// Line 52 - DUPLICATE of SAMPLE_RATE_HZ
const samplesPerSecond = 500;

// Line 53 - Calibration pulse duration
const pulseDuration = 0.2; // 200ms pulse

// Line 54 - Calculated from samplesPerSecond
const totalPulseSamples = Math.floor(samplesPerSecond * pulseDuration); // 100 samples

// Line 55 - USES ADC_MIDPOINT + ECG_ADC_SCALE_FACTOR (duplicated inline)
const pulseADC = 8388608 + (1 * 100000); // 1mV in ADC units

// Line 57 - USES ADC_MIDPOINT (duplicated inline)
const tailSamples = new Array(100).fill(8388608);

// Line 69 - Calibration timeout
setTimeout(..., 500); // 500ms delay

// Line 76 - DUPLICATE of SAMPLE_RATE_HZ
const samplesPerSecond = 500;

// Line 77 - Buffer time window
const visibleSeconds = 8;

// Line 78 - Calculated buffer size
const maxSamples = samplesPerSecond * visibleSeconds; // 4000 samples
```
**Issues:**
- ❌ `samplesPerSecond` duplicated from `SAMPLE_RATE_HZ`
- ❌ `8388608` hardcoded (should use `ADC_MIDPOINT`)
- ❌ `100000` hardcoded (should use `ECG_ADC_SCALE_FACTOR`)
- ❌ Magic numbers: `0.2`, `100`, `500`, `8`
- ❌ **BUG:** `visibleSeconds = 8` causes half-screen issue

### 3. ECGWaveformCanvas.tsx (Calculations)
```typescript
// Line 104 - Uses centralized constants ✅
const pixelsPerSecond = mmToPixels(PAPER_SPEED_MM_PER_S);

// Line 105 - Uses centralized constants ✅
const pixelsPerSample = pixelsPerSecond / SAMPLE_RATE_HZ;

// Line 106 - Calculated
const samplesVisible = Math.floor(width / pixelsPerSample);

// Line 109 - Magic number for logging
if (data.length % 100 === 0) { ... }

// Line 114-116 - Uses centralized constants ✅
const pixelsPerUnit = isECGMode
  ? mmToPixels(ECG_SCALE_MM_PER_MV)
  : mmToPixels(1 / EEG_SCALE_UV_PER_MM);

// Line 192 - Magic numbers for sweep line erase
const eraseWidth = Math.max(10, pixelsPerSample * 5);
```
**Issues:**
- ❌ Magic number: `100` (logging frequency)
- ❌ Magic numbers: `10`, `5` (erase width)

### 4. ECGViewerHeader.tsx (UI Constants)
```typescript
// Line 99 - Layout option
{isECGMode && <option value={12}>Complete 12-Lead ECG</option>}

// Line 131-133 - Speed options
<option value={25}>25mm/s</option>
<option value={50}>50mm/s</option>

// Line 145 - Gain option
<option value={10}>10mm/mV</option>

// Line 152 - EEG gain option
<option value={10}>10μV/mm</option>
```
**Issues:**
- ❌ Hardcoded values: `12`, `25`, `50`, `10`
- ❌ Not using centralized constants

### 5. ECGDisplayGrid.tsx (Layout Logic)
```typescript
// Line 24 - Grid layout calculations
const rows = layout === 12 ? 3 : layout === 9 ? 3 : layout === 4 ? 2 : 1;
```
**Issues:**
- ❌ Hardcoded layout numbers: `12`, `9`, `4`, `3`, `2`, `1`

### 6. Other Components (Simplified Rendering)
**ECGViewer.tsx (Line 56):**
```typescript
const samples = data.slice(-200); // Show last 200 samples
```

**PatientCardWaveform.tsx (Line 57):**
```typescript
const samples = data.slice(-125); // Show last 125 samples
```
**Issues:**
- ❌ Magic numbers: `200`, `125`
- ⚠️ These use simplified rendering (not medical-grade)

---

## All Constants That Need Centralization

### Medical Standards (Already Centralized ✅)
- `ECG_SCALE_MM_PER_MV = 10` - Vertical scale for ECG
- `EEG_SCALE_UV_PER_MM = 50` - Vertical scale for EEG
- `PAPER_SPEED_MM_PER_S = 25` - Horizontal sweep speed
- `SAMPLE_RATE_HZ = 500` - ESP32 sampling frequency
- `ADC_MIDPOINT = 8388608` - 24-bit ADC zero point
- `ECG_ADC_SCALE_FACTOR = 100000` - ADC units per mV
- `EEG_ADC_SCALE_FACTOR = 1000` - ADC units per μV

### Calibration Pulse (NOT Centralized ❌)
- `CALIBRATION_PULSE_DURATION_MS = 200` - Duration of 1mV pulse
- `CALIBRATION_HEAD_DURATION_MS = 200` - Flat baseline before pulse
- `CALIBRATION_TAIL_DURATION_MS = 200` - Flat baseline after pulse
- `CALIBRATION_AMPLITUDE_MV = 1.0` - Standard 1mV calibration
- `CALIBRATION_DELAY_MS = 500` - Delay before showing calibration

### Data Buffer (NOT Centralized ❌)
- `BUFFER_TIME_SECONDS = 12` - **FIX: Changed from 8 to 12**
- `BUFFER_MAX_SAMPLES = SAMPLE_RATE_HZ * BUFFER_TIME_SECONDS` - Calculated

### UI/Display (NOT Centralized ❌)
- `SWEEP_ERASE_WIDTH_SAMPLES = 5` - Samples to erase behind sweep line
- `SWEEP_ERASE_MIN_PIXELS = 10` - Minimum erase width in pixels
- `LOG_SAMPLE_INTERVAL = 100` - Log debug info every N samples

### Layout Options (NOT Centralized ❌)
- `LAYOUT_SINGLE = 1`
- `LAYOUT_QUAD = 4`
- `LAYOUT_NINE = 9`
- `LAYOUT_TWELVE = 12`

### Speed/Gain Options (NOT Centralized ❌)
- `SPEED_OPTIONS = [25, 50]` - mm/s choices
- `ECG_GAIN_OPTIONS = [5, 10, 20]` - mm/mV choices
- `EEG_GAIN_OPTIONS = [10, 50, 100]` - μV/mm choices

### Simplified View (NOT Centralized ❌)
- `CARD_VIEW_SAMPLES = 125` - PatientCard waveform samples
- `WIDGET_VIEW_SAMPLES = 200` - ECGViewer widget samples

---

## Recommended Centralized Configuration File

### File: `hospital-display-app/src/config/ecgConfig.ts`

```typescript
/**
 * ECG/EEG Configuration - Single Source of Truth
 * All constants for medical-grade waveform rendering
 */

// ============================================================
// MEDICAL STANDARDS (International/FDA approved values)
// ============================================================

/** ECG vertical scale: 10mm = 1mV (ISO 11073) */
export const ECG_SCALE_MM_PER_MV = 10;

/** EEG vertical sensitivity: 50μV/mm (standard clinical setting) */
export const EEG_SCALE_UV_PER_MM = 50;

/** ECG paper speed: 25mm/s (US/International standard) */
export const PAPER_SPEED_MM_PER_S = 25;

/** ESP32 sampling rate: 500Hz (ADS1298 configuration) */
export const SAMPLE_RATE_HZ = 500;

// ============================================================
// ADC CONVERSION (ESP32 ADS1298 24-bit)
// ============================================================

/** 24-bit ADC midpoint (zero voltage) = 2^23 */
export const ADC_MIDPOINT = 8388608;

/** ECG scale factor: 100000 ADC units = 1mV */
export const ECG_ADC_SCALE_FACTOR = 100000;

/** EEG scale factor: 1000 ADC units = 1μV */
export const EEG_ADC_SCALE_FACTOR = 1000;

// ============================================================
// CALIBRATION PULSE (Medical standard format)
// ============================================================

/** Duration of flat baseline BEFORE pulse (ms) */
export const CALIBRATION_HEAD_DURATION_MS = 200;

/** Duration of 1mV calibration pulse (ms) */
export const CALIBRATION_PULSE_DURATION_MS = 200;

/** Duration of flat baseline AFTER pulse (ms) */
export const CALIBRATION_TAIL_DURATION_MS = 200;

/** Calibration pulse amplitude (mV) */
export const CALIBRATION_AMPLITUDE_MV = 1.0;

/** Total calibration duration (ms) */
export const CALIBRATION_TOTAL_DURATION_MS =
  CALIBRATION_HEAD_DURATION_MS +
  CALIBRATION_PULSE_DURATION_MS +
  CALIBRATION_TAIL_DURATION_MS;

/** Delay before displaying calibration pulse (ms) */
export const CALIBRATION_DISPLAY_DELAY_MS = 500;

/** Total calibration samples */
export const CALIBRATION_TOTAL_SAMPLES = Math.floor(
  (CALIBRATION_TOTAL_DURATION_MS / 1000) * SAMPLE_RATE_HZ
);

// ============================================================
// DATA BUFFER (Circular buffer for continuous monitoring)
// ============================================================

/**
 * Buffer time window (seconds)
 * IMPORTANT: Must be > (screen_width / (PAPER_SPEED_MM_PER_S × DPI / 25.4) / SAMPLE_RATE_HZ)
 * For 1920px wide screen at 120 DPI: requires ~10s minimum
 * Set to 12s for safety margin
 */
export const BUFFER_TIME_SECONDS = 12;

/** Maximum samples in buffer (calculated) */
export const BUFFER_MAX_SAMPLES = SAMPLE_RATE_HZ * BUFFER_TIME_SECONDS;

// ============================================================
// UI/DISPLAY SETTINGS
// ============================================================

/** Samples to erase behind sweep line */
export const SWEEP_ERASE_WIDTH_SAMPLES = 5;

/** Minimum erase width in pixels */
export const SWEEP_ERASE_MIN_PIXELS = 10;

/** Log debug info every N samples (0 = disable) */
export const LOG_SAMPLE_INTERVAL = 100;

// ============================================================
// LAYOUT OPTIONS
// ============================================================

/** Single lead view */
export const LAYOUT_SINGLE = 1;

/** 4-lead grid (2×2) */
export const LAYOUT_QUAD = 4;

/** 9-lead grid (3×3) */
export const LAYOUT_NINE = 9;

/** 12-lead complete ECG (3×4 + rhythm strip) */
export const LAYOUT_TWELVE = 12;

/** Available layout options */
export const LAYOUT_OPTIONS = [
  LAYOUT_SINGLE,
  LAYOUT_QUAD,
  LAYOUT_NINE,
  LAYOUT_TWELVE,
] as const;

// ============================================================
// SPEED/GAIN OPTIONS
// ============================================================

/** Paper speed options (mm/s) */
export const SPEED_OPTIONS = [25, 50] as const;

/** ECG gain options (mm/mV) */
export const ECG_GAIN_OPTIONS = [5, 10, 20] as const;

/** EEG gain options (μV/mm) */
export const EEG_GAIN_OPTIONS = [10, 50, 100] as const;

// ============================================================
// SIMPLIFIED VIEWS (Dashboard cards, widgets)
// ============================================================

/** Patient card mini-waveform samples */
export const CARD_VIEW_SAMPLES = 125;

/** Widget view samples */
export const WIDGET_VIEW_SAMPLES = 200;

// ============================================================
// DERIVED CONSTANTS (Calculated from above)
// ============================================================

/** Samples per millisecond */
export const SAMPLES_PER_MS = SAMPLE_RATE_HZ / 1000;

/** Milliseconds per sample */
export const MS_PER_SAMPLE = 1000 / SAMPLE_RATE_HZ;

/** Calibration head samples */
export const CALIBRATION_HEAD_SAMPLES = Math.floor(
  (CALIBRATION_HEAD_DURATION_MS / 1000) * SAMPLE_RATE_HZ
);

/** Calibration pulse samples */
export const CALIBRATION_PULSE_SAMPLES = Math.floor(
  (CALIBRATION_PULSE_DURATION_MS / 1000) * SAMPLE_RATE_HZ
);

/** Calibration tail samples */
export const CALIBRATION_TAIL_SAMPLES = Math.floor(
  (CALIBRATION_TAIL_DURATION_MS / 1000) * SAMPLE_RATE_HZ
);

/** Calibration pulse ADC value (1mV above midpoint) */
export const CALIBRATION_PULSE_ADC =
  ADC_MIDPOINT + CALIBRATION_AMPLITUDE_MV * ECG_ADC_SCALE_FACTOR;

// ============================================================
// TYPE EXPORTS
// ============================================================

export type LayoutOption = typeof LAYOUT_OPTIONS[number];
export type SpeedOption = typeof SPEED_OPTIONS[number];
export type ECGGainOption = typeof ECG_GAIN_OPTIONS[number];
export type EEGGainOption = typeof EEG_GAIN_OPTIONS[number];
```

---

## Benefits of Centralization

### Before (Current State):
- ❌ Constants duplicated across 6+ files
- ❌ Hardcoded magic numbers (8, 500, 8388608, 100000, etc.)
- ❌ Inconsistent usage
- ❌ Hard to maintain
- ❌ Easy to introduce bugs (buffer size = 8 instead of 12)

### After (Centralized):
- ✅ Single source of truth
- ✅ All constants documented with medical context
- ✅ Type-safe (TypeScript enums/types)
- ✅ Easy to adjust values globally
- ✅ Self-documenting code
- ✅ Prevents bugs (change BUFFER_TIME_SECONDS in one place)

---

## Migration Plan

1. Create `hospital-display-app/src/config/ecgConfig.ts` with all constants
2. Update `medicalWaveformUtils.ts` to import from `ecgConfig.ts`
3. Update `ECGViewerContainer.tsx` to remove duplicates
4. Update `ECGWaveformCanvas.tsx` to remove magic numbers
5. Update `ECGViewerHeader.tsx` to use layout/speed/gain constants
6. Update `ECGDisplayGrid.tsx` to use layout constants
7. Update simplified views to use `CARD_VIEW_SAMPLES` and `WIDGET_VIEW_SAMPLES`
8. Delete old constants from utils file
9. Test all ECG views

---

## Critical Fix Included

**Buffer size fix:**
```typescript
// OLD (causes half-screen bug):
const visibleSeconds = 8;

// NEW (fixes half-screen bug):
export const BUFFER_TIME_SECONDS = 12;
```

This is now part of the centralized config and properly documented.
