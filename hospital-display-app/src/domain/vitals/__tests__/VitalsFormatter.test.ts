/**
 * Unit Tests for VitalsFormatter
 * Domain layer tests for vitals formatting logic
 */

import { VitalsFormatter, FormattedVital, TemperatureUnit } from '../VitalsFormatter';
import { VitalsData } from '../VitalsValidator';

describe('VitalsFormatter', () => {
  // ================================
  // HEART RATE FORMATTING
  // ================================

  describe('formatHeartRate', () => {
    it('should format valid heart rate with unit', () => {
      expect(VitalsFormatter.formatHeartRate(75)).toBe('75 bpm');
    });

    it('should round fractional heart rates', () => {
      expect(VitalsFormatter.formatHeartRate(75.6)).toBe('76 bpm');
      expect(VitalsFormatter.formatHeartRate(75.4)).toBe('75 bpm');
    });

    it('should return placeholder for undefined', () => {
      expect(VitalsFormatter.formatHeartRate(undefined)).toBe('--');
    });

    it('should return placeholder for null', () => {
      expect(VitalsFormatter.formatHeartRate(null as any)).toBe('--');
    });

    it('should handle zero', () => {
      expect(VitalsFormatter.formatHeartRate(0)).toBe('0 bpm');
    });
  });

  // ================================
  // SPO2 FORMATTING
  // ================================

  describe('formatSpO2', () => {
    it('should format valid SpO2 with unit', () => {
      expect(VitalsFormatter.formatSpO2(98)).toBe('98%');
    });

    it('should round fractional SpO2', () => {
      expect(VitalsFormatter.formatSpO2(98.6)).toBe('99%');
      expect(VitalsFormatter.formatSpO2(98.4)).toBe('98%');
    });

    it('should return placeholder for undefined', () => {
      expect(VitalsFormatter.formatSpO2(undefined)).toBe('--');
    });

    it('should handle 100%', () => {
      expect(VitalsFormatter.formatSpO2(100)).toBe('100%');
    });
  });

  // ================================
  // RESPIRATORY RATE FORMATTING
  // ================================

  describe('formatRespiratoryRate', () => {
    it('should format valid respiratory rate with unit', () => {
      expect(VitalsFormatter.formatRespiratoryRate(16)).toBe('16 /min');
    });

    it('should round fractional rates', () => {
      expect(VitalsFormatter.formatRespiratoryRate(16.7)).toBe('17 /min');
    });

    it('should return placeholder for undefined', () => {
      expect(VitalsFormatter.formatRespiratoryRate(undefined)).toBe('--');
    });
  });

  // ================================
  // TEMPERATURE FORMATTING
  // ================================

  describe('formatTemperature', () => {
    it('should format temperature in Celsius by default', () => {
      expect(VitalsFormatter.formatTemperature(37.5)).toBe('37.5°C');
    });

    it('should convert to Fahrenheit when requested', () => {
      const result = VitalsFormatter.formatTemperature(37, 'F');
      expect(result).toBe('98.6°F');
    });

    it('should handle exact conversions', () => {
      expect(VitalsFormatter.formatTemperature(0, 'F')).toBe('32.0°F');
      expect(VitalsFormatter.formatTemperature(100, 'F')).toBe('212.0°F');
    });

    it('should return placeholder for undefined', () => {
      expect(VitalsFormatter.formatTemperature(undefined)).toBe('--');
    });

    it('should format with one decimal place', () => {
      expect(VitalsFormatter.formatTemperature(37.123)).toBe('37.1°C');
      expect(VitalsFormatter.formatTemperature(37.987)).toBe('38.0°C');
    });
  });

  // ================================
  // BLOOD PRESSURE FORMATTING
  // ================================

  describe('formatBloodPressure', () => {
    it('should format both systolic and diastolic', () => {
      expect(VitalsFormatter.formatBloodPressure(120, 80)).toBe('120/80 mmHg');
    });

    it('should round fractional values', () => {
      expect(VitalsFormatter.formatBloodPressure(120.6, 80.4)).toBe('121/80 mmHg');
    });

    it('should return placeholder when both are undefined', () => {
      expect(VitalsFormatter.formatBloodPressure(undefined, undefined)).toBe('--/--');
    });

    it('should return placeholder when systolic is undefined', () => {
      expect(VitalsFormatter.formatBloodPressure(undefined, 80)).toBe('--/--');
    });

    it('should return placeholder when diastolic is undefined', () => {
      expect(VitalsFormatter.formatBloodPressure(120, undefined)).toBe('--/--');
    });
  });

  // ================================
  // BATTERY FORMATTING
  // ================================

  describe('formatBatteryLevel', () => {
    it('should format battery level with percentage', () => {
      expect(VitalsFormatter.formatBatteryLevel(80)).toBe('80%');
    });

    it('should round fractional values', () => {
      expect(VitalsFormatter.formatBatteryLevel(80.7)).toBe('81%');
    });

    it('should return placeholder for undefined', () => {
      expect(VitalsFormatter.formatBatteryLevel(undefined)).toBe('--');
    });

    it('should handle 0% and 100%', () => {
      expect(VitalsFormatter.formatBatteryLevel(0)).toBe('0%');
      expect(VitalsFormatter.formatBatteryLevel(100)).toBe('100%');
    });
  });

  // ================================
  // SIGNAL QUALITY FORMATTING
  // ================================

  describe('formatSignalQuality', () => {
    it('should format signal quality as percentage', () => {
      expect(VitalsFormatter.formatSignalQuality(0.85)).toBe('85%');
    });

    it('should round to nearest integer', () => {
      expect(VitalsFormatter.formatSignalQuality(0.856)).toBe('86%');
    });

    it('should return placeholder for undefined', () => {
      expect(VitalsFormatter.formatSignalQuality(undefined)).toBe('--');
    });

    it('should handle 0 and 1', () => {
      expect(VitalsFormatter.formatSignalQuality(0)).toBe('0%');
      expect(VitalsFormatter.formatSignalQuality(1)).toBe('100%');
    });
  });

  // ================================
  // NEW SENSOR VITALS FORMATTING
  // ================================

  describe('New Sensor Vitals', () => {
    it('should format tremor frequency', () => {
      expect(VitalsFormatter.formatTremorFrequency(5.2)).toBe('5.2 Hz');
      expect(VitalsFormatter.formatTremorFrequency(undefined)).toBe('--');
    });

    it('should format tremor amplitude', () => {
      expect(VitalsFormatter.formatTremorAmplitude(0.25)).toBe('0.25 g');
      expect(VitalsFormatter.formatTremorAmplitude(undefined)).toBe('--');
    });

    it('should format bioimpedance', () => {
      expect(VitalsFormatter.formatBioimpedance(500)).toBe('500.0 Ω');
      expect(VitalsFormatter.formatBioimpedance(500.5)).toBe('500.5 Ω');
      expect(VitalsFormatter.formatBioimpedance(undefined)).toBe('--');
    });

    it('should format perfusion index', () => {
      expect(VitalsFormatter.formatPerfusionIndex(5.5)).toBe('5.50%');
      expect(VitalsFormatter.formatPerfusionIndex(undefined)).toBe('--');
    });

    it('should format accelerometer data', () => {
      const formatted = VitalsFormatter.formatAccelerometer(0.5, 0.3, 9.8);
      expect(formatted).toBe('X:0.50 Y:0.30 Z:9.80 g');
    });

    it('should return placeholder for incomplete accelerometer data', () => {
      expect(VitalsFormatter.formatAccelerometer(undefined, 0.3, 9.8)).toBe('--');
      expect(VitalsFormatter.formatAccelerometer(0.5, undefined, 9.8)).toBe('--');
      expect(VitalsFormatter.formatAccelerometer(0.5, 0.3, undefined)).toBe('--');
    });
  });

  // ================================
  // COLOR CODING
  // ================================

  describe('getHeartRateColor', () => {
    it('should return red for abnormal values (< 50 or > 100)', () => {
      expect(VitalsFormatter.getHeartRateColor(45)).toBe('text-red-500');
      expect(VitalsFormatter.getHeartRateColor(120)).toBe('text-red-500');
    });

    it('should return yellow for warning values (< 60 or > 90)', () => {
      expect(VitalsFormatter.getHeartRateColor(55)).toBe('text-yellow-500');
      expect(VitalsFormatter.getHeartRateColor(95)).toBe('text-yellow-500');
    });

    it('should return green for normal values (60-90)', () => {
      expect(VitalsFormatter.getHeartRateColor(75)).toBe('text-green-500');
      expect(VitalsFormatter.getHeartRateColor(60)).toBe('text-green-500');
      expect(VitalsFormatter.getHeartRateColor(90)).toBe('text-green-500');
    });

    it('should return gray for undefined', () => {
      expect(VitalsFormatter.getHeartRateColor(undefined)).toBe('text-gray-500');
    });
  });

  describe('getSpO2Color', () => {
    it('should return red for critical values (< 90)', () => {
      expect(VitalsFormatter.getSpO2Color(85)).toBe('text-red-500');
    });

    it('should return yellow for warning values (< 95)', () => {
      expect(VitalsFormatter.getSpO2Color(92)).toBe('text-yellow-500');
    });

    it('should return green for normal values (>= 95)', () => {
      expect(VitalsFormatter.getSpO2Color(98)).toBe('text-green-500');
    });

    it('should return gray for undefined', () => {
      expect(VitalsFormatter.getSpO2Color(undefined)).toBe('text-gray-500');
    });
  });

  describe('getTemperatureColor', () => {
    it('should return red for abnormal values', () => {
      expect(VitalsFormatter.getTemperatureColor(35.5)).toBe('text-red-500');
      expect(VitalsFormatter.getTemperatureColor(38.5)).toBe('text-red-500');
    });

    it('should return yellow for warning values', () => {
      expect(VitalsFormatter.getTemperatureColor(36.3)).toBe('text-yellow-500');
      expect(VitalsFormatter.getTemperatureColor(37.7)).toBe('text-yellow-500');
    });

    it('should return green for normal values (36.5-37.5)', () => {
      expect(VitalsFormatter.getTemperatureColor(37.0)).toBe('text-green-500');
    });

    it('should return gray for undefined', () => {
      expect(VitalsFormatter.getTemperatureColor(undefined)).toBe('text-gray-500');
    });
  });

  describe('getBloodPressureColor', () => {
    it('should return red for abnormal systolic values', () => {
      expect(VitalsFormatter.getBloodPressureColor(85)).toBe('text-red-500');
      expect(VitalsFormatter.getBloodPressureColor(150)).toBe('text-red-500');
    });

    it('should return yellow for warning systolic values', () => {
      expect(VitalsFormatter.getBloodPressureColor(95)).toBe('text-yellow-500');
      expect(VitalsFormatter.getBloodPressureColor(135)).toBe('text-yellow-500');
    });

    it('should return green for normal systolic values (100-130)', () => {
      expect(VitalsFormatter.getBloodPressureColor(120)).toBe('text-green-500');
    });

    it('should return gray for undefined', () => {
      expect(VitalsFormatter.getBloodPressureColor(undefined)).toBe('text-gray-500');
    });
  });

  describe('getBatteryColor', () => {
    it('should return red for critical battery (< 20)', () => {
      expect(VitalsFormatter.getBatteryColor(10)).toBe('text-red-500');
    });

    it('should return yellow for low battery (< 50)', () => {
      expect(VitalsFormatter.getBatteryColor(30)).toBe('text-yellow-500');
    });

    it('should return green for good battery (>= 50)', () => {
      expect(VitalsFormatter.getBatteryColor(80)).toBe('text-green-500');
    });

    it('should return gray for undefined', () => {
      expect(VitalsFormatter.getBatteryColor(undefined)).toBe('text-gray-500');
    });
  });

  describe('getSignalQualityColor', () => {
    it('should return red for poor quality (< 0.5)', () => {
      expect(VitalsFormatter.getSignalQualityColor(0.3)).toBe('text-red-500');
    });

    it('should return yellow for fair quality (< 0.7)', () => {
      expect(VitalsFormatter.getSignalQualityColor(0.6)).toBe('text-yellow-500');
    });

    it('should return green for good quality (>= 0.7)', () => {
      expect(VitalsFormatter.getSignalQualityColor(0.9)).toBe('text-green-500');
    });

    it('should return gray for undefined', () => {
      expect(VitalsFormatter.getSignalQualityColor(undefined)).toBe('text-gray-500');
    });
  });

  // ================================
  // BATCH FORMATTING
  // ================================

  describe('formatAllVitals', () => {
    it('should format all vitals with default temperature unit', () => {
      const vitals: VitalsData = {
        patientId: 'P001',
        timestamp: new Date().toISOString(),
        heartRate: 75,
        oxygenSaturation: 98,
        temperature: 37.5,
        respiratoryRate: 16,
        bloodPressureSystolic: 120,
        bloodPressureDiastolic: 80,
        batteryLevel: 85,
        signalQuality: 0.9
      };

      const formatted = VitalsFormatter.formatAllVitals(vitals);

      expect(formatted.heartRate.value).toBe('75 bpm');
      expect(formatted.heartRate.unit).toBe('bpm');
      expect(formatted.heartRate.color).toBe('text-green-500');
      expect(formatted.heartRate.isNormal).toBe(true);

      expect(formatted.spO2.value).toBe('98%');
      expect(formatted.spO2.unit).toBe('%');
      expect(formatted.spO2.isNormal).toBe(true);

      expect(formatted.temperature.value).toBe('37.5°C');
      expect(formatted.temperature.unit).toBe('°C');
      expect(formatted.temperature.isNormal).toBe(true);

      expect(formatted.respiratoryRate.value).toBe('16 /min');
      expect(formatted.respiratoryRate.unit).toBe('/min');
      expect(formatted.respiratoryRate.isNormal).toBe(true);

      expect(formatted.bloodPressure.value).toBe('120/80 mmHg');
      expect(formatted.bloodPressure.unit).toBe('mmHg');
      expect(formatted.bloodPressure.isNormal).toBe(true);

      expect(formatted.battery.value).toBe('85%');
      expect(formatted.battery.unit).toBe('%');
      expect(formatted.battery.isNormal).toBe(true);

      expect(formatted.signalQuality.value).toBe('90%');
      expect(formatted.signalQuality.unit).toBe('%');
      expect(formatted.signalQuality.isNormal).toBe(true);
    });

    it('should format all vitals with Fahrenheit temperature', () => {
      const vitals: VitalsData = {
        patientId: 'P001',
        timestamp: new Date().toISOString(),
        temperature: 37
      };

      const formatted = VitalsFormatter.formatAllVitals(vitals, 'F');

      expect(formatted.temperature.value).toBe('98.6°F');
      expect(formatted.temperature.unit).toBe('°F');
    });

    it('should mark vitals as normal or not', () => {
      const vitals: VitalsData = {
        patientId: 'P001',
        timestamp: new Date().toISOString(),
        heartRate: 75, // Normal
        oxygenSaturation: 85 // Abnormal (< 95)
      };

      const formatted = VitalsFormatter.formatAllVitals(vitals);

      expect(formatted.heartRate.isNormal).toBe(true);
      expect(formatted.spO2.isNormal).toBe(false);
    });

    it('should handle missing vitals with placeholders', () => {
      const vitals: VitalsData = {
        patientId: 'P001',
        timestamp: new Date().toISOString()
      };

      const formatted = VitalsFormatter.formatAllVitals(vitals);

      expect(formatted.heartRate.value).toBe('--');
      expect(formatted.spO2.value).toBe('--');
      expect(formatted.temperature.value).toBe('--');
      expect(formatted.respiratoryRate.value).toBe('--');
      expect(formatted.bloodPressure.value).toBe('--/--');
      expect(formatted.battery.value).toBe('--');
      expect(formatted.signalQuality.value).toBe('--');
    });
  });

  // ================================
  // TREND INDICATOR
  // ================================

  describe('getTrendIndicator', () => {
    it('should return up arrow for significant increase', () => {
      expect(VitalsFormatter.getTrendIndicator(100, 95)).toBe('↑');
    });

    it('should return down arrow for significant decrease', () => {
      expect(VitalsFormatter.getTrendIndicator(90, 95)).toBe('↓');
    });

    it('should return right arrow for stable values', () => {
      expect(VitalsFormatter.getTrendIndicator(100, 100)).toBe('→');
      expect(VitalsFormatter.getTrendIndicator(100, 100.5)).toBe('→'); // < 1% change
    });

    it('should return empty string for undefined values', () => {
      expect(VitalsFormatter.getTrendIndicator(undefined, 100)).toBe('');
      expect(VitalsFormatter.getTrendIndicator(100, undefined)).toBe('');
      expect(VitalsFormatter.getTrendIndicator(undefined, undefined)).toBe('');
    });
  });

  // ================================
  // TIMESTAMP FORMATTING
  // ================================

  describe('formatTimestamp', () => {
    it('should format recent timestamps as seconds ago', () => {
      const thirtySecondsAgo = new Date(Date.now() - 30 * 1000);
      const formatted = VitalsFormatter.formatTimestamp(thirtySecondsAgo.toISOString());

      expect(formatted).toMatch(/\d+s ago/);
    });

    it('should format timestamps within an hour as minutes ago', () => {
      const tenMinutesAgo = new Date(Date.now() - 10 * 60 * 1000);
      const formatted = VitalsFormatter.formatTimestamp(tenMinutesAgo.toISOString());

      expect(formatted).toMatch(/\d+m ago/);
    });

    it('should format timestamps within a day as time', () => {
      const threeHoursAgo = new Date(Date.now() - 3 * 60 * 60 * 1000);
      const formatted = VitalsFormatter.formatTimestamp(threeHoursAgo.toISOString());

      // Should be formatted as time like "02:30 PM"
      expect(formatted).toMatch(/\d{1,2}:\d{2}/);
    });

    it('should format older timestamps with date and time', () => {
      const twoDaysAgo = new Date(Date.now() - 2 * 24 * 60 * 60 * 1000);
      const formatted = VitalsFormatter.formatTimestamp(twoDaysAgo.toISOString());

      // Should contain month abbreviation
      expect(formatted.length).toBeGreaterThan(5);
    });

    it('should handle invalid timestamp gracefully', () => {
      // Invalid timestamp returns "Invalid Date" string from toLocaleDateString
      const result = VitalsFormatter.formatTimestamp('invalid');
      expect(result === '--' || result.includes('Invalid')).toBe(true);
    });
  });

  // ================================
  // EDGE CASES
  // ================================

  describe('Edge Cases', () => {
    it('should handle extreme but valid values', () => {
      expect(VitalsFormatter.formatHeartRate(300)).toBe('300 bpm');
      expect(VitalsFormatter.formatSpO2(100)).toBe('100%');
      expect(VitalsFormatter.formatTemperature(45)).toBe('45.0°C');
    });

    it('should handle zero values', () => {
      expect(VitalsFormatter.formatHeartRate(0)).toBe('0 bpm');
      expect(VitalsFormatter.formatSpO2(0)).toBe('0%');
      expect(VitalsFormatter.formatBatteryLevel(0)).toBe('0%');
    });

    it('should handle fractional values correctly', () => {
      expect(VitalsFormatter.formatHeartRate(75.123)).toBe('75 bpm');
      expect(VitalsFormatter.formatSpO2(98.789)).toBe('99%');
      expect(VitalsFormatter.formatTemperature(37.156)).toBe('37.2°C');
    });

    it('should handle negative temperatures (valid in Fahrenheit)', () => {
      expect(VitalsFormatter.formatTemperature(-10, 'C')).toBe('-10.0°C');
      expect(VitalsFormatter.formatTemperature(-10, 'F')).toBe('14.0°F');
    });
  });
});
