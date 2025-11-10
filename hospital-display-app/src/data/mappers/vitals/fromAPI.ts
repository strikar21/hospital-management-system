/**
 * Map vitals data from API response to domain model.
 */

import { parseISO } from '@/utils/datetime';

export interface VitalsDomain {
  heartRate?: number;
  respiratoryRate?: number;
  oxygenSaturation?: number;
  skinTemperature?: number;
  systolicPressure?: number;
  diastolicPressure?: number;
  batteryLevel?: number;
  signalQuality?: number;
  timestamp: Date;
  deviceId?: string;
}

export function mapVitalsFromAPI(apiVitals: any): VitalsDomain {
  /**
   * Map API vitals response to domain model.
   *
   * Handles:
   * - Timestamp parsing
   * - Optional field handling
   *
   * @param apiVitals - Vitals data from API
   * @returns Domain vitals model
   */
  return {
    heartRate: apiVitals.heartRate,
    respiratoryRate: apiVitals.respiratoryRate,
    oxygenSaturation: apiVitals.oxygenSaturation,
    skinTemperature: apiVitals.skinTemperature,
    systolicPressure: apiVitals.systolicPressure,
    diastolicPressure: apiVitals.diastolicPressure,
    batteryLevel: apiVitals.batteryLevel,
    signalQuality: apiVitals.signalQuality,
    timestamp: parseISO(apiVitals.timestamp || apiVitals.time),
    deviceId: apiVitals.deviceId
  };
}
