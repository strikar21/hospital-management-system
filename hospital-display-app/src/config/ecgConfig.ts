/**
 * ECG/EEG Configuration - Single Source of Truth
 * All constants for medical-grade waveform rendering
 *
 * @module ecgConfig
 * @description Centralized configuration for ECG/EEG monitoring system
 * Following international medical standards (ISO 11073, FDA guidelines, IEC 60601)
 */

// ============================================================
// MEDICAL STANDARDS (International/FDA approved values)
// ============================================================

/** ECG vertical scale: 10mm = 1mV (ISO 11073 standard) */
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
// CALIBRATION PULSE (Extended for better visibility)
// ============================================================

/** Duration of flat baseline BEFORE pulse (ms) */
export const CALIBRATION_HEAD_DURATION_MS = 1000;

/** Duration of 1mV calibration pulse (ms) */
export const CALIBRATION_PULSE_DURATION_MS = 1000;

/** Duration of flat baseline AFTER pulse (ms) */
export const CALIBRATION_TAIL_DURATION_MS = 1000;

/** Calibration pulse amplitude (mV) - Medical standard */
export const CALIBRATION_AMPLITUDE_MV = 1.0;

/** Total calibration duration (ms) */
export const CALIBRATION_TOTAL_DURATION_MS =
  CALIBRATION_HEAD_DURATION_MS +
  CALIBRATION_PULSE_DURATION_MS +
  CALIBRATION_TAIL_DURATION_MS;

/** Delay before displaying calibration pulse (ms) */
export const CALIBRATION_DISPLAY_DELAY_MS = 500;

// ============================================================
// DATA BUFFER (Circular buffer for continuous monitoring)
// ============================================================

/**
 * Buffer time window (seconds)
 *
 * Extended viewing window for comprehensive rhythm analysis
 * Allows viewing multiple cardiac cycles with proper ECG spacing
 *
 * At 500Hz: 25 seconds = 12500 samples
 * Waveform enters circular sweep mode when buffer fills
 */
export const BUFFER_TIME_SECONDS = 25;

/** Maximum samples in buffer (calculated) */
export const BUFFER_MAX_SAMPLES = SAMPLE_RATE_HZ * BUFFER_TIME_SECONDS;

// ============================================================
// UI/DISPLAY SETTINGS
// ============================================================

/** Samples to erase behind sweep line (creates clean sweep effect) */
export const SWEEP_ERASE_WIDTH_SAMPLES = 5;

/** Minimum erase width in pixels (ensures visibility) */
export const SWEEP_ERASE_MIN_PIXELS = 10;

/** Log debug info every N samples (0 = disable logging) */
export const LOG_SAMPLE_INTERVAL = 100;

// ============================================================
// LAYOUT OPTIONS
// ============================================================

/** Single lead view (full-screen single waveform) */
export const LAYOUT_SINGLE = 1;

/** 4-lead grid (2×2) */
export const LAYOUT_QUAD = 4;

/** 9-lead grid (3×3) - Extended monitoring */
export const LAYOUT_NINE = 9;

/** 12-lead complete ECG (3×4 + rhythm strip) - Full diagnostic */
export const LAYOUT_TWELVE = 12;

/** Available layout options */
export const LAYOUT_OPTIONS = [
  LAYOUT_SINGLE,
  LAYOUT_QUAD,
  LAYOUT_NINE,
  LAYOUT_TWELVE,
] as const;

// ============================================================
// SPEED/GAIN OPTIONS (User-selectable settings)
// ============================================================

/** ECG paper speed options (mm/s) - 25mm/s is US/International standard */
export const ECG_SPEED_OPTIONS = [15, 25, 50] as const;

/** EEG paper speed options (mm/s) - 30mm/s is ACNS clinical standard */
export const EEG_SPEED_OPTIONS = [15, 25, 30, 50] as const;

/** ECG gain options (mm/mV) - Standard is 10mm/mV (ISO 11073) */
export const ECG_GAIN_OPTIONS = [5, 10, 20] as const;

/** EEG gain options (μV/mm) - 7μV/mm is ACNS standard for clinical EEG */
export const EEG_GAIN_OPTIONS = [5, 7, 10, 15, 20] as const;

/** ECG default paper speed (mm/s) */
export const ECG_DEFAULT_SPEED = 25;

/** EEG default paper speed (mm/s) - ACNS 2023 guideline */
export const EEG_DEFAULT_SPEED = 30;

/** ECG default gain (mm/mV) - ISO 11073 standard */
export const ECG_DEFAULT_GAIN = 10;

/** EEG default gain (μV/mm) - ACNS standard clinical setting */
export const EEG_DEFAULT_GAIN = 7;

// ============================================================
// SIMPLIFIED VIEWS (Dashboard cards, widgets)
// ============================================================

/** Patient card mini-waveform samples (0.25 seconds @ 500Hz) */
export const CARD_VIEW_SAMPLES = 125;

/** Widget view samples (0.4 seconds @ 500Hz) */
export const WIDGET_VIEW_SAMPLES = 200;

// ============================================================
// DERIVED CONSTANTS (Calculated from above - DO NOT MODIFY)
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

/** Total calibration samples (head + pulse + tail) */
export const CALIBRATION_TOTAL_SAMPLES =
  CALIBRATION_HEAD_SAMPLES +
  CALIBRATION_PULSE_SAMPLES +
  CALIBRATION_TAIL_SAMPLES;

/** Calibration pulse ADC value (1mV above midpoint) */
export const CALIBRATION_PULSE_ADC =
  ADC_MIDPOINT + CALIBRATION_AMPLITUDE_MV * ECG_ADC_SCALE_FACTOR;

/** Calibration baseline ADC value (0mV = midpoint) */
export const CALIBRATION_BASELINE_ADC = ADC_MIDPOINT;

// ============================================================
// TYPE EXPORTS (TypeScript type safety)
// ============================================================

export type LayoutOption = typeof LAYOUT_OPTIONS[number];
export type ECGSpeedOption = typeof ECG_SPEED_OPTIONS[number];
export type EEGSpeedOption = typeof EEG_SPEED_OPTIONS[number];
export type ECGGainOption = typeof ECG_GAIN_OPTIONS[number];
export type EEGGainOption = typeof EEG_GAIN_OPTIONS[number];

// ============================================================
// CONFIGURATION SUMMARY (For Documentation)
// ============================================================

/**
 * Current Configuration Summary:
 *
 * - Sample Rate: 500 Hz (2ms per sample)
 * - Paper Speed: 25 mm/s (standard)
 * - ECG Scale: 10 mm/mV (standard)
 * - EEG Scale: 50 μV/mm (standard clinical)
 * - Buffer Size: 25 seconds (12500 samples)
 * - Calibration: 3000ms total (1000ms head + 1000ms pulse + 1000ms tail)
 * - ADC: 24-bit (ADS1298), midpoint = 8388608
 * - Layouts: 1, 4, 9, 12 lead configurations
 */
