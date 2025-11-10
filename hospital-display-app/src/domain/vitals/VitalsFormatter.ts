/**
 * VitalsFormatter - Frontend domain logic for formatting vitals for display
 *
 * Single source of truth for:
 * - Formatting vital signs with proper units
 * - Unit conversions (C to F, etc.)
 * - Display precision (decimal places)
 * - Color coding based on values
 *
 * All components should use these formatters for consistent display.
 */

import { VitalsData } from './VitalsValidator';

export type TemperatureUnit = 'C' | 'F';

export interface FormattedVital {
  value: string;
  unit: string;
  color?: string;
  isNormal?: boolean;
}

export class VitalsFormatter {
  /**
   * Format heart rate with unit
   */
  static formatHeartRate(hr: number | undefined): string {
    if (hr === undefined || hr === null) return '--';
    return `${Math.round(hr)} bpm`;
  }

  /**
   * Format oxygen saturation with unit
   */
  static formatSpO2(spo2: number | undefined): string {
    if (spo2 === undefined || spo2 === null) return '--';
    return `${Math.round(spo2)}%`;
  }

  /**
   * Format respiratory rate with unit
   */
  static formatRespiratoryRate(rr: number | undefined): string {
    if (rr === undefined || rr === null) return '--';
    return `${Math.round(rr)} /min`;
  }

  /**
   * Format temperature with unit conversion
   */
  static formatTemperature(
    temp: number | undefined,
    unit: TemperatureUnit = 'C'
  ): string {
    if (temp === undefined || temp === null) return '--';

    let value = temp;
    if (unit === 'F') {
      value = (temp * 9/5) + 32;
    }

    return `${value.toFixed(1)}°${unit}`;
  }

  /**
   * Format blood pressure (systolic/diastolic)
   */
  static formatBloodPressure(
    systolic: number | undefined,
    diastolic: number | undefined
  ): string {
    if (systolic === undefined || diastolic === undefined) return '--/--';
    return `${Math.round(systolic)}/${Math.round(diastolic)} mmHg`;
  }

  /**
   * Format battery level with percentage
   */
  static formatBatteryLevel(battery: number | undefined): string {
    if (battery === undefined || battery === null) return '--';
    return `${Math.round(battery)}%`;
  }

  /**
   * Format signal quality as percentage
   */
  static formatSignalQuality(quality: number | undefined): string {
    if (quality === undefined || quality === null) return '--';
    const percentage = Math.round(quality * 100);
    return `${percentage}%`;
  }

  /**
   * Format tremor frequency
   */
  static formatTremorFrequency(freq: number | undefined): string {
    if (freq === undefined || freq === null) return '--';
    return `${freq.toFixed(1)} Hz`;
  }

  /**
   * Format tremor amplitude
   */
  static formatTremorAmplitude(amp: number | undefined): string {
    if (amp === undefined || amp === null) return '--';
    return `${amp.toFixed(2)} g`;
  }

  /**
   * Format bioimpedance
   */
  static formatBioimpedance(bioz: number | undefined): string {
    if (bioz === undefined || bioz === null) return '--';
    return `${bioz.toFixed(1)} Ω`;
  }

  /**
   * Format perfusion index
   */
  static formatPerfusionIndex(pi: number | undefined): string {
    if (pi === undefined || pi === null) return '--';
    return `${pi.toFixed(2)}%`;
  }

  /**
   * Format accelerometer data
   */
  static formatAccelerometer(
    x: number | undefined,
    y: number | undefined,
    z: number | undefined
  ): string {
    if (x === undefined || y === undefined || z === undefined) return '--';
    return `X:${x.toFixed(2)} Y:${y.toFixed(2)} Z:${z.toFixed(2)} g`;
  }

  /**
   * Get color class for heart rate
   */
  static getHeartRateColor(hr: number | undefined): string {
    if (hr === undefined) return 'text-gray-500';
    if (hr < 50 || hr > 100) return 'text-red-500'; // Abnormal
    if (hr < 60 || hr > 90) return 'text-yellow-500'; // Warning
    return 'text-green-500'; // Normal
  }

  /**
   * Get color class for SpO2
   */
  static getSpO2Color(spo2: number | undefined): string {
    if (spo2 === undefined) return 'text-gray-500';
    if (spo2 < 90) return 'text-red-500'; // Critical
    if (spo2 < 95) return 'text-yellow-500'; // Warning
    return 'text-green-500'; // Normal
  }

  /**
   * Get color class for temperature
   */
  static getTemperatureColor(temp: number | undefined): string {
    if (temp === undefined) return 'text-gray-500';
    if (temp < 36.0 || temp > 38.0) return 'text-red-500'; // Abnormal
    if (temp < 36.5 || temp > 37.5) return 'text-yellow-500'; // Warning
    return 'text-green-500'; // Normal
  }

  /**
   * Get color class for blood pressure (using systolic)
   */
  static getBloodPressureColor(systolic: number | undefined): string {
    if (systolic === undefined) return 'text-gray-500';
    if (systolic < 90 || systolic > 140) return 'text-red-500'; // Abnormal
    if (systolic < 100 || systolic > 130) return 'text-yellow-500'; // Warning
    return 'text-green-500'; // Normal
  }

  /**
   * Get color class for battery level
   */
  static getBatteryColor(battery: number | undefined): string {
    if (battery === undefined) return 'text-gray-500';
    if (battery < 20) return 'text-red-500'; // Critical
    if (battery < 50) return 'text-yellow-500'; // Low
    return 'text-green-500'; // Good
  }

  /**
   * Get color class for signal quality
   */
  static getSignalQualityColor(quality: number | undefined): string {
    if (quality === undefined) return 'text-gray-500';
    if (quality < 0.5) return 'text-red-500'; // Poor
    if (quality < 0.7) return 'text-yellow-500'; // Fair
    return 'text-green-500'; // Good
  }

  /**
   * Format all vitals for display with colors
   */
  static formatAllVitals(vitals: VitalsData, tempUnit: TemperatureUnit = 'C'): {
    heartRate: FormattedVital;
    spO2: FormattedVital;
    respiratoryRate: FormattedVital;
    temperature: FormattedVital;
    bloodPressure: FormattedVital;
    battery: FormattedVital;
    signalQuality: FormattedVital;
  } {
    return {
      heartRate: {
        value: this.formatHeartRate(vitals.heartRate),
        unit: 'bpm',
        color: this.getHeartRateColor(vitals.heartRate),
        isNormal: vitals.heartRate !== undefined && vitals.heartRate >= 60 && vitals.heartRate <= 90
      },
      spO2: {
        value: this.formatSpO2(vitals.oxygenSaturation),
        unit: '%',
        color: this.getSpO2Color(vitals.oxygenSaturation),
        isNormal: vitals.oxygenSaturation !== undefined && vitals.oxygenSaturation >= 95
      },
      respiratoryRate: {
        value: this.formatRespiratoryRate(vitals.respiratoryRate),
        unit: '/min',
        color: 'text-gray-700',
        isNormal: vitals.respiratoryRate !== undefined && vitals.respiratoryRate >= 12 && vitals.respiratoryRate <= 20
      },
      temperature: {
        value: this.formatTemperature(vitals.temperature, tempUnit),
        unit: `°${tempUnit}`,
        color: this.getTemperatureColor(vitals.temperature),
        isNormal: vitals.temperature !== undefined && vitals.temperature >= 36.5 && vitals.temperature <= 37.5
      },
      bloodPressure: {
        value: this.formatBloodPressure(vitals.bloodPressureSystolic, vitals.bloodPressureDiastolic),
        unit: 'mmHg',
        color: this.getBloodPressureColor(vitals.bloodPressureSystolic),
        isNormal: vitals.bloodPressureSystolic !== undefined && vitals.bloodPressureSystolic >= 100 && vitals.bloodPressureSystolic <= 130
      },
      battery: {
        value: this.formatBatteryLevel(vitals.batteryLevel),
        unit: '%',
        color: this.getBatteryColor(vitals.batteryLevel),
        isNormal: vitals.batteryLevel !== undefined && vitals.batteryLevel >= 50
      },
      signalQuality: {
        value: this.formatSignalQuality(vitals.signalQuality),
        unit: '%',
        color: this.getSignalQualityColor(vitals.signalQuality),
        isNormal: vitals.signalQuality !== undefined && vitals.signalQuality >= 0.7
      }
    };
  }

  /**
   * Get trend indicator (↑ ↓ →)
   */
  static getTrendIndicator(current: number | undefined, previous: number | undefined): string {
    if (current === undefined || previous === undefined) return '';
    const diff = current - previous;
    const threshold = 0.01; // 1% change threshold

    if (Math.abs(diff / previous) < threshold) return '→';
    return diff > 0 ? '↑' : '↓';
  }

  /**
   * Format timestamp for display
   */
  static formatTimestamp(timestamp: string): string {
    try {
      const date = new Date(timestamp);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffSeconds = Math.floor(diffMs / 1000);

      if (diffSeconds < 60) {
        return `${diffSeconds}s ago`;
      } else if (diffSeconds < 3600) {
        const minutes = Math.floor(diffSeconds / 60);
        return `${minutes}m ago`;
      } else if (diffSeconds < 86400) {
        return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
      } else {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
      }
    } catch (e) {
      return '--';
    }
  }
}
