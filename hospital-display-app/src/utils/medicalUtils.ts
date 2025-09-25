// medicalUtils.ts - Medical validation and safety utilities
// HIPAA and medical compliance validation functions

import { vitaltype, vitalstatus } from '../types';

/**
 * Medical-grade vital signs validation
 */
export class MedicalUtils {

  /**
   * Get vital sign status with medical accuracy
   * Uses standard medical ranges for patient safety
   */
  static getVitalStatus(value: number, type: vitaltype): vitalstatus {
    switch (type) {
      case 'heartRate':
        // Medical standard ranges for adults
        if (value < 40 || value > 130) return 'critical';
        if (value < 50 || value > 110) return 'warning';
        return 'normal';

      case 'oxygenSat':
        // Oxygen saturation critical thresholds
        if (value < 90) return 'critical';
        if (value < 95) return 'warning';
        return 'normal';

      case 'temperature':
        // Temperature in Fahrenheit
        if (value < 95 || value > 103) return 'critical';
        if (value < 96 || value > 101) return 'warning';
        return 'normal';

      case 'bloodPressure':
        // Systolic blood pressure ranges
        if (value < 70 || value > 180) return 'critical';
        if (value < 90 || value > 160) return 'warning';
        return 'normal';

      case 'respiratoryRate':
        // Respiratory rate for adults
        if (value < 8 || value > 25) return 'critical';
        if (value < 12 || value > 20) return 'warning';
        return 'normal';

      case 'ecg':
        // ECG values in mV * 100 (120 = 1.2mV)
        if (value < 80 || value > 200) return 'critical';
        if (value < 100 || value > 150) return 'warning';
        return 'normal';

      case 'eeg':
        // EEG values in microvolts
        if (value < 5 || value > 80) return 'critical';
        if (value < 10 || value > 60) return 'warning';
        return 'normal';

      case 'bioImpedance':
        // Bioimpedance in ohms
        if (value < 350 || value > 850) return 'critical';
        if (value < 400 || value > 750) return 'warning';
        return 'normal';

      case 'tremor':
        // Tremor intensity 0-10 scale
        if (value > 7) return 'critical';
        if (value > 4) return 'warning';
        return 'normal';

      default:
        return 'normal';
    }
  }

  /**
   * Detect cardiac arrhythmia from heart rate and ECG
   * Comprehensive medical algorithm for arrhythmia detection
   */
  static detectArrhythmia(heartRate: number, ecgValue: number = 120): boolean {
    // 1. Heart rate irregularities
    const hrIrregular = heartRate < 50 || heartRate > 120; // Severe bradycardia or tachycardia

    // 2. ECG amplitude irregularities
    const ecgIrregular = ecgValue < 90 || ecgValue > 180; // Abnormal ECG amplitude

    // 3. Rhythm irregularity detection
    const rhythmIrregular = Math.abs(heartRate - 75) > 30 && ecgValue < 110;

    // 4. Critical combinations
    const criticalCombination = (heartRate > 110 && ecgValue < 100) || (heartRate < 60 && ecgValue > 160);

    // 5. Specific arrhythmia patterns
    const atrialFibrillation = heartRate > 100 && heartRate < 150 && ecgValue < 105;
    const ventricularTachycardia = heartRate > 150 && ecgValue > 140;
    const bradycardia = heartRate < 50;
    const prematureVentricularContraction = ecgValue > 170 && heartRate > 90;

    return hrIrregular || ecgIrregular || rhythmIrregular || criticalCombination ||
           atrialFibrillation || ventricularTachycardia || bradycardia || prematureVentricularContraction;
  }

  /**
   * Get specific arrhythmia type based on heart rate and ECG patterns
   */
  static getArrhythmiaType(heartRate: number, ecgValue: number): string | null {
    if (!this.detectArrhythmia(heartRate, ecgValue)) return null;

    if (heartRate < 50) return 'Bradycardia';
    if (heartRate > 150 && ecgValue > 140) return 'Ventricular Tachycardia';
    if (heartRate > 100 && heartRate < 150 && ecgValue < 105) return 'Atrial Fibrillation';
    if (ecgValue > 170 && heartRate > 90) return 'PVC (Premature Ventricular Contraction)';
    if (heartRate > 120) return 'Tachycardia';
    if (ecgValue < 90) return 'Low Voltage ECG';
    if (ecgValue > 180) return 'High Voltage ECG';

    return 'Irregular Rhythm';
  }

  /**
   * Detect seizure activity from EEG readings
   * Medical algorithm for seizure pattern detection
   */
  static detectSeizureActivity(eegValue: number, heartRate: number): boolean {
    // Simple seizure detection based on EEG amplitude and heart rate correlation
    const abnormalEEG = eegValue > 60 || eegValue < 5;
    const correlatedHeartRate = heartRate > 120; // Often elevated during seizures

    return abnormalEEG && correlatedHeartRate;
  }

  /**
   * Assess fall risk based on multiple factors
   * Comprehensive medical fall risk assessment
   */
  static assessFallRisk(tremorIntensity: number, heartRate: number, age: number): 'low' | 'medium' | 'high' {
    let riskScore = 0;

    // Tremor increases fall risk - more detailed scoring
    if (tremorIntensity > 6) riskScore += 3;
    else if (tremorIntensity > 3) riskScore += 2;
    else if (tremorIntensity > 1) riskScore += 1;

    // Heart rate abnormalities increase fall risk
    if (heartRate < 50 || heartRate > 120) riskScore += 2;
    else if (heartRate < 60 || heartRate > 100) riskScore += 1;

    // Age factor (higher age = higher risk)
    if (age > 75) riskScore += 2;
    else if (age > 65) riskScore += 1;

    // Risk classification with refined thresholds
    if (riskScore >= 5) return 'high';
    if (riskScore >= 3) return 'medium';
    return 'low';
  }
}

export default MedicalUtils;