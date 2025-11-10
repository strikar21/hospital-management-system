/**
 * VitalsValidator - Frontend domain logic for validating vitals data
 *
 * Single source of truth for:
 * - Validating incoming vitals have required fields
 * - Checking vitals are within displayable ranges
 * - Detecting stale/old vitals
 * - Data quality validation
 *
 * Matches backend VitalsNormalizer pattern for consistency.
 */

export interface VitalsData {
  patientId: string;
  deviceId?: string;
  timestamp: string;
  heartRate?: number;
  oxygenSaturation?: number;
  respiratoryRate?: number;
  temperature?: number;
  bloodPressureSystolic?: number;
  bloodPressureDiastolic?: number;
  batteryLevel?: number;
  signalQuality?: number;

  // New sensor vitals (Phase 3 addition)
  tremorFrequency?: number;
  tremorAmplitude?: number;
  bioimpedance?: number;
  perfusionIndex?: number;
  accelerometerX?: number;
  accelerometerY?: number;
  accelerometerZ?: number;
}

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

export class VitalsValidator {
  /**
   * Validate vitals data completeness and quality
   */
  static validate(vitals: VitalsData): ValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    // Check required fields
    if (!this.hasRequiredFields(vitals)) {
      errors.push('Missing required fields (patientId or timestamp)');
    }

    // Check timestamp freshness
    if (!this.hasRecentTimestamp(vitals)) {
      warnings.push('Vitals data is stale (older than 5 minutes)');
    }

    // Check vitals are within displayable ranges
    const rangeErrors = this.checkDisplayRanges(vitals);
    errors.push(...rangeErrors);

    // Check data quality
    const qualityWarnings = this.checkDataQuality(vitals);
    warnings.push(...qualityWarnings);

    return {
      isValid: errors.length === 0,
      errors,
      warnings
    };
  }

  /**
   * Quick validation - just check if vitals are displayable
   */
  static isValid(vitals: VitalsData): boolean {
    return this.hasRequiredFields(vitals) &&
           this.hasRecentTimestamp(vitals);
  }

  /**
   * Check for required fields
   */
  static hasRequiredFields(vitals: VitalsData): boolean {
    return !!(vitals.patientId && vitals.timestamp);
  }

  /**
   * Check if timestamp is recent (within 5 minutes)
   */
  static hasRecentTimestamp(vitals: VitalsData, maxAgeSeconds: number = 300): boolean {
    try {
      const now = Date.now();
      const vitalTime = new Date(vitals.timestamp).getTime();
      const ageSeconds = (now - vitalTime) / 1000;
      return ageSeconds >= 0 && ageSeconds < maxAgeSeconds;
    } catch (e) {
      return false; // Invalid timestamp format
    }
  }

  /**
   * Check vitals are within displayable ranges
   * These are UI limits, not medical thresholds
   */
  static checkDisplayRanges(vitals: VitalsData): string[] {
    const errors: string[] = [];

    // Heart rate: 0-300 bpm (display range)
    if (vitals.heartRate !== undefined) {
      if (vitals.heartRate < 0 || vitals.heartRate > 300) {
        errors.push(`Heart rate out of display range: ${vitals.heartRate}`);
      }
    }

    // Oxygen saturation: 0-100%
    if (vitals.oxygenSaturation !== undefined) {
      if (vitals.oxygenSaturation < 0 || vitals.oxygenSaturation > 100) {
        errors.push(`SpO2 out of range: ${vitals.oxygenSaturation}`);
      }
    }

    // Respiratory rate: 0-60 breaths/min
    if (vitals.respiratoryRate !== undefined) {
      if (vitals.respiratoryRate < 0 || vitals.respiratoryRate > 60) {
        errors.push(`Respiratory rate out of range: ${vitals.respiratoryRate}`);
      }
    }

    // Temperature: 20-45°C (display range)
    if (vitals.temperature !== undefined) {
      if (vitals.temperature < 20 || vitals.temperature > 45) {
        errors.push(`Temperature out of display range: ${vitals.temperature}`);
      }
    }

    // Blood pressure: 0-300 mmHg
    if (vitals.bloodPressureSystolic !== undefined) {
      if (vitals.bloodPressureSystolic < 0 || vitals.bloodPressureSystolic > 300) {
        errors.push(`Systolic BP out of range: ${vitals.bloodPressureSystolic}`);
      }
    }

    if (vitals.bloodPressureDiastolic !== undefined) {
      if (vitals.bloodPressureDiastolic < 0 || vitals.bloodPressureDiastolic > 200) {
        errors.push(`Diastolic BP out of range: ${vitals.bloodPressureDiastolic}`);
      }
    }

    // Battery level: 0-100%
    if (vitals.batteryLevel !== undefined) {
      if (vitals.batteryLevel < 0 || vitals.batteryLevel > 100) {
        errors.push(`Battery level out of range: ${vitals.batteryLevel}`);
      }
    }

    // Signal quality: 0-1 (0-100%)
    if (vitals.signalQuality !== undefined) {
      if (vitals.signalQuality < 0 || vitals.signalQuality > 1) {
        errors.push(`Signal quality out of range: ${vitals.signalQuality}`);
      }
    }

    return errors;
  }

  /**
   * Check data quality and generate warnings
   */
  static checkDataQuality(vitals: VitalsData): string[] {
    const warnings: string[] = [];

    // Warn if no core vitals present
    const hasCoreVitals = !!(
      vitals.heartRate ||
      vitals.oxygenSaturation ||
      vitals.temperature
    );

    if (!hasCoreVitals) {
      warnings.push('No core vitals (HR, SpO2, Temp) present');
    }

    // Warn if signal quality is low
    if (vitals.signalQuality !== undefined && vitals.signalQuality < 0.5) {
      warnings.push(`Low signal quality: ${(vitals.signalQuality * 100).toFixed(0)}%`);
    }

    // Warn if battery is low
    if (vitals.batteryLevel !== undefined && vitals.batteryLevel < 20) {
      warnings.push(`Low battery: ${vitals.batteryLevel}%`);
    }

    return warnings;
  }

  /**
   * Get age of vitals in seconds
   */
  static getAgeSeconds(vitals: VitalsData): number {
    try {
      const now = Date.now();
      const vitalTime = new Date(vitals.timestamp).getTime();
      return (now - vitalTime) / 1000;
    } catch (e) {
      return Infinity;
    }
  }

  /**
   * Check if vitals are stale (older than threshold)
   */
  static isStale(vitals: VitalsData, thresholdMinutes: number = 5): boolean {
    const ageSeconds = this.getAgeSeconds(vitals);
    return ageSeconds > (thresholdMinutes * 60);
  }

  /**
   * Check if vitals have minimum required data for display
   */
  static hasMinimumData(vitals: VitalsData): boolean {
    // At least one vital sign must be present
    return !!(
      vitals.heartRate ||
      vitals.oxygenSaturation ||
      vitals.temperature ||
      vitals.bloodPressureSystolic ||
      vitals.respiratoryRate
    );
  }

  /**
   * Get list of available vitals
   */
  static getAvailableVitals(vitals: VitalsData): string[] {
    const available: string[] = [];

    if (vitals.heartRate !== undefined) available.push('Heart Rate');
    if (vitals.oxygenSaturation !== undefined) available.push('SpO2');
    if (vitals.temperature !== undefined) available.push('Temperature');
    if (vitals.bloodPressureSystolic !== undefined) available.push('Blood Pressure');
    if (vitals.respiratoryRate !== undefined) available.push('Respiratory Rate');
    if (vitals.tremorFrequency !== undefined) available.push('Tremor');
    if (vitals.bioimpedance !== undefined) available.push('Bioimpedance');
    if (vitals.perfusionIndex !== undefined) available.push('Perfusion Index');

    return available;
  }

  /**
   * Calculate data completeness score (0-1)
   */
  static calculateCompleteness(vitals: VitalsData): number {
    const possibleVitals = [
      'heartRate',
      'oxygenSaturation',
      'temperature',
      'bloodPressureSystolic',
      'bloodPressureDiastolic',
      'respiratoryRate'
    ];

    const presentCount = possibleVitals.filter(
      vital => vitals[vital as keyof VitalsData] !== undefined
    ).length;

    return presentCount / possibleVitals.length;
  }
}
