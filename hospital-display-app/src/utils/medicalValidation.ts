// medicalValidation.ts - Medical-grade validation utilities for patient safety
import { patient, medication, alert } from '../types';

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  severity: 'info' | 'warning' | 'error' | 'critical';
}

export interface VitalValidationResult extends ValidationResult {
  criticalFlags: string[];
  requiresImmediateAttention: boolean;
}

export interface MedicationValidationResult extends ValidationResult {
  allergyWarnings: string[];
  interactionWarnings: string[];
  dosageFlags: string[];
}

export const medicalValidation = {
  /**
   * Validate vital signs with medical ranges and critical thresholds
   */
  validateVitals: (vitals: any, patientAge?: number, patientWeight?: number): VitalValidationResult => {
    const errors: string[] = [];
    const warnings: string[] = [];
    const criticalFlags: string[] = [];
    let severity: 'info' | 'warning' | 'error' | 'critical' = 'info' as any;
    let requiresImmediateAttention = false;

    // Heart Rate Validation
    if (vitals.heartRate !== undefined) {
      if (vitals.heartRate < 30 || vitals.heartRate > 250) {
        errors.push(`Heart rate ${vitals.heartRate} BPM outside survivable range (30-250)`);
        criticalFlags.push('CRITICAL_HEART_RATE');
        severity = 'critical';
        requiresImmediateAttention = true;
      } else if (vitals.heartRate < 50 || vitals.heartRate > 180) {
        warnings.push(`Heart rate ${vitals.heartRate} BPM outside normal range`);
        if (severity !== 'critical' && severity !== 'error') severity = 'warning';
      }
    }

    // Blood Pressure Validation
    if (vitals.systolicPressure !== undefined) {
      const systolic = vitals.systolicPressure;
      if (systolic < 60 || systolic > 250) {
        errors.push(`Systolic BP ${systolic} mmHg outside survivable range (60-250)`);
        criticalFlags.push('CRITICAL_BLOOD_PRESSURE');
        severity = 'critical';
        requiresImmediateAttention = true;
      } else if (systolic < 90 || systolic > 180) {
        warnings.push(`Blood pressure ${systolic}/${vitals.diastolicPressure || Math.round(systolic * 0.67)} outside normal range`);
        if (severity !== 'critical' && severity !== 'error') severity = 'warning';
      }
    }

    // Oxygen Saturation Validation
    if (vitals.oxygenSaturation !== undefined) {
      if (vitals.oxygenSaturation < 70 || vitals.oxygenSaturation > 100) {
        errors.push(`Oxygen saturation ${vitals.oxygenSaturation}% invalid range - verify sensor`);
        criticalFlags.push('INVALID_OXYGEN_SAT');
        severity = 'critical';
        requiresImmediateAttention = true;
      } else if (vitals.oxygenSaturation < 90) {
        warnings.push(`Oxygen saturation ${vitals.oxygenSaturation}% below normal (90-100%)`);
        criticalFlags.push('LOW_OXYGEN_SAT');
        if (severity !== 'critical') severity = 'error';
        requiresImmediateAttention = true;
      }
    }

    // Temperature Validation (assuming Fahrenheit)
    if (vitals.skinTemperature !== undefined) {
      if (vitals.skinTemperature < 85 || vitals.skinTemperature > 110) {
        errors.push(`Temperature ${vitals.skinTemperature}°F outside survivable range (85-110°F)`);
        criticalFlags.push('CRITICAL_TEMPERATURE');
        severity = 'critical';
        requiresImmediateAttention = true;
      } else if (vitals.skinTemperature < 95 || vitals.skinTemperature > 104) {
        warnings.push(`Temperature ${vitals.skinTemperature}°F outside normal range (95-104°F)`);
        if (severity !== 'critical' && severity !== 'error') severity = 'warning';
      }
    }

    // Respiratory Rate Validation
    if (vitals.respiratoryRate !== undefined) {
      if (vitals.respiratoryRate < 5 || vitals.respiratoryRate > 60) {
        errors.push(`Respiratory rate ${vitals.respiratoryRate} breaths/min outside survivable range`);
        criticalFlags.push('CRITICAL_RESPIRATORY_RATE');
        severity = 'critical';
        requiresImmediateAttention = true;
      } else if (vitals.respiratoryRate < 12 || vitals.respiratoryRate > 25) {
        warnings.push(`Respiratory rate ${vitals.respiratoryRate} breaths/min outside normal range (12-25)`);
        if (severity !== 'critical' && severity !== 'error') severity = 'warning';
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
      criticalFlags,
      severity,
      requiresImmediateAttention
    };
  },

  /**
   * Validate medication against patient allergies and basic safety checks
   */
  validateMedication: (medication: medication, patient: patient): MedicationValidationResult => {
    const errors: string[] = [];
    const warnings: string[] = [];
    const allergyWarnings: string[] = [];
    const interactionWarnings: string[] = [];
    const dosageFlags: string[] = [];
    let severity: 'info' | 'warning' | 'error' | 'critical' = 'info' as any;

    // Check against patient allergies
    if (patient.allergies && patient.allergies.length > 0) {
      for (const allergy of patient.allergies) {
        const medicationName = medication.name.toLowerCase();
        const allergen = allergy.allergen.toLowerCase();
        
        if (medicationName.includes(allergen) || allergen.includes(medicationName.split(' ')[0])) {
          const warningMessage = `ALLERGY WARNING: patient allergic to ${allergy.allergen} (${allergy.severity})`;
          allergyWarnings.push(warningMessage);
          
          if (allergy.severity === 'life-threatening' || allergy.severity === 'severe') {
            errors.push(warningMessage);
            severity = 'critical';
          } else {
            warnings.push(warningMessage);
            if (severity !== 'critical' && severity !== 'error') severity = 'warning';
          }
        }
      }
    }

    // Basic medication validation
    if (!medication.name || medication.name.trim().length === 0) {
      errors.push('medication name is required');
      severity = 'error';
    }

    if (!medication.dosage || medication.dosage.trim().length === 0) {
      errors.push('medication dosage is required');
      severity = 'error';
    }

    if (!medication.route || medication.route.trim().length === 0) {
      errors.push('medication route is required');
      severity = 'error';
    }

    // High-alert medications (simplified list)
    const highAlertmedications = [
      'insulin', 'heparin', 'warfarin', 'morphine', 'fentanyl', 'midazolam',
      'epinephrine', 'norepinephrine', 'dopamine', 'potassium', 'chemotherapy'
    ];

    const isHighAlert = highAlertmedications.some(alertMed => 
      medication.name.toLowerCase().includes(alertMed)
    );

    if (isHighAlert) {
      warnings.push('HIGH-ALERT MEDICATION: Requires double verification');
      dosageFlags.push('HIGH_ALERT_MEDICATION');
      if (severity !== 'critical' && severity !== 'error') severity = 'warning';
    }

    // Check for dosage format
    if (medication.dosage && !medication.dosage.match(/\d+(\.\d+)?\s*(mg|mcg|g|ml|units|iu)/i)) {
      warnings.push('Dosage format may be invalid - ensure proper units (mg, mcg, ml, units)');
      dosageFlags.push('DOSAGE_FORMAT_WARNING');
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
      allergyWarnings,
      interactionWarnings,
      dosageFlags,
      severity
    };
  },

  /**
   * Validate patient identification for safety (Two patient Identifiers)
   */
  validatePatientIdentification: (patient: patient): ValidationResult => {
    const errors: string[] = [];
    const warnings: string[] = [];
    let severity: 'info' | 'warning' | 'error' | 'critical' = 'info' as any;

    // Check for required identifiers
    if (!patient.id || patient.id.trim().length === 0) {
      errors.push('patient ID is required');
      severity = 'critical';
    }

    if (!patient.name || patient.name.trim().length === 0) {
      errors.push('patient name is required');
      severity = 'critical';
    }

    if (!patient.bedNumber || patient.bedNumber.trim().length === 0) {
      warnings.push('Bed number not specified - may affect patient identification');
      if (severity !== 'critical') severity = 'warning';
    }

    // Check for age appropriateness
    if (patient.age !== undefined) {
      if (patient.age < 0 || patient.age > 150) {
        errors.push(`patient age ${patient.age} is invalid`);
        severity = 'error';
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
      severity
    };
  },

  /**
   * Validate alert criticality and response requirements
   */
  validateAlert: (alert: alert): ValidationResult => {
    const errors: string[] = [];
    const warnings: string[] = [];
    let severity: 'info' | 'warning' | 'error' | 'critical' = 'info' as any;

    if (!alert.message || alert.message.trim().length === 0) {
      errors.push('Alert message is required');
      severity = 'error';
    }

    if (!alert.severity) {
      errors.push('Alert severity is required');
      severity = 'error';
    }

    // Critical alerts require immediate acknowledgment
    if (alert.severity === 'critical' && !alert.isAcknowledged) {
      const alertTime = new Date(alert.timestamp);
      const now = new Date();
      const minutesSinceAlert = (now.getTime() - alertTime.getTime()) / (1000 * 60);

      if (minutesSinceAlert > 5) {
        warnings.push('CRITICAL ALERT: Unacknowledged for over 5 minutes - requires immediate attention');
        severity = 'critical';
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
      severity
    };
  },

  /**
   * Format validation results for display
   */
  formatValidationResults: (result: ValidationResult): string => {
    const messages: string[] = [];
    
    if (result.errors.length > 0) {
      messages.push('ERRORS: ' + result.errors.join('; '));
    }
    
    if (result.warnings.length > 0) {
      messages.push('WARNINGS: ' + result.warnings.join('; '));
    }
    
    return messages.join('\n');
  }
};

export default medicalValidation;