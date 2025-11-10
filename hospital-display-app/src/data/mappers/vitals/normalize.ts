/**
 * Normalize vitals data (round, clamp, validate).
 */

import { VitalsDomain } from './fromAPI';

export function normalizeVitals(vitals: VitalsDomain): VitalsDomain {
  /**
   * Normalize vitals data for display.
   *
   * - Rounds values to appropriate precision
   * - Clamps values to valid ranges
   *
   * @param vitals - Raw vitals data
   * @returns Normalized vitals data
   */
  return {
    ...vitals,
    heartRate: vitals.heartRate !== undefined
      ? Math.round(vitals.heartRate)
      : undefined,
    respiratoryRate: vitals.respiratoryRate !== undefined
      ? Math.round(vitals.respiratoryRate)
      : undefined,
    oxygenSaturation: vitals.oxygenSaturation !== undefined
      ? Math.round(vitals.oxygenSaturation)
      : undefined,
    skinTemperature: vitals.skinTemperature !== undefined
      ? Math.round(vitals.skinTemperature * 10) / 10 // 1 decimal
      : undefined,
    systolicPressure: vitals.systolicPressure !== undefined
      ? Math.round(vitals.systolicPressure)
      : undefined,
    diastolicPressure: vitals.diastolicPressure !== undefined
      ? Math.round(vitals.diastolicPressure)
      : undefined,
    batteryLevel: vitals.batteryLevel !== undefined
      ? Math.round(vitals.batteryLevel)
      : undefined,
    signalQuality: vitals.signalQuality !== undefined
      ? Math.round(vitals.signalQuality)
      : undefined
  };
}
