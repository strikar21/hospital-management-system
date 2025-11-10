/**
 * ADC value conversion to physical units.
 */

import { ADC_MIDPOINT, SENSITIVITY_MV, SENSITIVITY_UV } from './constants';

export function adcToMillivolts(adcValues: number[]): number[] {
  /**
   * Convert 24-bit ADC values to millivolts for ECG display.
   *
   * ADC Format (from ESP32):
   * - Midpoint: 8388608 (2^23, representing 0V)
   * - Range: ±1.0V full scale
   * - Sensitivity: ~10 μV per LSB
   *
   * Conversion formula:
   *   mV = (ADC_value - midpoint) * 0.01
   *
   * @param adcValues - Array of 24-bit ADC values
   * @returns Array of voltages in millivolts
   *
   * @example
   * adcToMillivolts([8388608, 8410496, 8366720])
   * // [0.00, 218.88, -218.88]
   */
  return adcValues.map(value => (value - ADC_MIDPOINT) * SENSITIVITY_MV);
}

export function adcToMicrovolts(adcValues: number[]): number[] {
  /**
   * Convert 24-bit ADC values to microvolts for EEG display.
   *
   * ADC Format (from ESP32):
   * - Midpoint: 8388608 (2^23, representing 0V)
   * - Range: ±0.1V full scale for EEG
   * - Sensitivity: ~1 μV per LSB
   *
   * Conversion formula:
   *   μV = (ADC_value - midpoint) * 0.001
   *
   * @param adcValues - Array of 24-bit ADC values
   * @returns Array of voltages in microvolts
   *
   * @example
   * adcToMicrovolts([8388608, 8389608, 8387608])
   * // [0.0, 1.0, -1.0]
   */
  return adcValues.map(value => (value - ADC_MIDPOINT) * SENSITIVITY_UV);
}
