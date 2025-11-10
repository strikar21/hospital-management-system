/**
 * ADC and conversion constants.
 */

// 24-bit ADC midpoint (2^23)
export const ADC_MIDPOINT = 8388608;

// ECG sensitivity (10 μV per LSB = 0.01 mV per LSB)
export const SENSITIVITY_MV = 0.01;

// EEG sensitivity (1 μV per LSB)
export const SENSITIVITY_UV = 0.001;

// Valid ADC range
export const ADC_MIN = 0;
export const ADC_MAX = 16777215; // 2^24 - 1

// Maximum delta value (compression limit)
export const MAX_DELTA = 32767; // int16 max
