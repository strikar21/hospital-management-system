// utils.ts - Utility functions for Hospital Display App

import { VitalType, VitalStatus } from './types';

export const getVitalStatus = (value: number, type: VitalType): VitalStatus => {
  switch (type) {
    case 'heartRate':
      if (value < 60 || value > 100) return 'critical';
      if (value < 65 || value > 95) return 'warning';
      return 'normal';
    case 'oxygenSat':
      if (value < 90) return 'critical';
      if (value < 95) return 'warning';
      return 'normal';
    case 'temperature':
      if (value < 96 || value > 102) return 'critical';
      if (value < 97 || value > 100) return 'warning';
      return 'normal';
    case 'skinTemperature':
      if (value < 95 || value > 103) return 'critical';
      if (value < 96 || value > 101) return 'warning';
      return 'normal';
    case 'bloodPressure':
      if (value < 90 || value > 160) return 'critical';
      if (value < 110 || value > 140) return 'warning';
      return 'normal';
    case 'respiratoryRate':
      if (value < 8 || value > 25) return 'critical';
      if (value < 12 || value > 20) return 'warning';
      return 'normal';
    case 'ecg':
      // ECG values are integers representing mV * 100, so 120 = 1.2mV
      if (value < 80 || value > 200) return 'critical';
      if (value < 100 || value > 150) return 'warning';
      return 'normal';
    case 'eeg':
      // EEG values in microvolts
      if (value < 5 || value > 80) return 'critical';
      if (value < 10 || value > 60) return 'warning';
      return 'normal';
    case 'bioimpedance':
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
};

export const detectArrhythmia = (heartRate: number, ecgValue: number): boolean => {
  // Detect arrhythmia based on multiple factors
  
  // 1. Heart rate irregularities
  const hrIrregular = heartRate < 50 || heartRate > 120; // Severe bradycardia or tachycardia
  
  // 2. ECG amplitude irregularities (simulated)
  const ecgIrregular = ecgValue < 90 || ecgValue > 180; // Abnormal ECG amplitude
  
  // 3. Simulated rhythm irregularity detection
  // In a real system, this would analyze R-R intervals
  const rhythmIrregular = Math.abs(heartRate - 75) > 30 && ecgValue < 110;
  
  // 4. Critical combinations
  const criticalCombination = (heartRate > 110 && ecgValue < 100) || (heartRate < 60 && ecgValue > 160);
  
  // Detect specific arrhythmia patterns (simplified simulation)
  const atrialFibrillation = heartRate > 100 && heartRate < 150 && ecgValue < 105;
  const ventricularTachycardia = heartRate > 150 && ecgValue > 140;
  const bradycardia = heartRate < 50;
  const prematureVentricularContraction = ecgValue > 170 && heartRate > 90;
  
  return hrIrregular || ecgIrregular || rhythmIrregular || criticalCombination || 
         atrialFibrillation || ventricularTachycardia || bradycardia || prematureVentricularContraction;
};

export const getArrhythmiaType = (heartRate: number, ecgValue: number): string | null => {
  if (!detectArrhythmia(heartRate, ecgValue)) return null;
  
  if (heartRate < 50) return 'Bradycardia';
  if (heartRate > 150 && ecgValue > 140) return 'Ventricular Tachycardia';
  if (heartRate > 100 && heartRate < 150 && ecgValue < 105) return 'Atrial Fibrillation';
  if (ecgValue > 170 && heartRate > 90) return 'PVC (Premature Ventricular Contraction)';
  if (heartRate > 120) return 'Tachycardia';
  if (ecgValue < 90) return 'Low Voltage ECG';
  if (ecgValue > 180) return 'High Voltage ECG';
  
  return 'Irregular Rhythm';
};

export const detectTremorEvent = (tremorValue: number, duration: number = 1): boolean => {
  // Detect significant tremor events
  return tremorValue > 4 && duration > 5; // Tremor intensity > 4 for more than 5 seconds
};

export const assessFallRisk = (tremor: number, heartRate: number, age: number): 'low' | 'medium' | 'high' => {
  let riskScore = 0;
  
  // Tremor increases fall risk
  if (tremor > 6) riskScore += 3;
  else if (tremor > 3) riskScore += 2;
  else if (tremor > 1) riskScore += 1;
  
  // Heart rate abnormalities increase fall risk
  if (heartRate < 50 || heartRate > 120) riskScore += 2;
  else if (heartRate < 60 || heartRate > 100) riskScore += 1;
  
  // Age factor
  if (age > 75) riskScore += 2;
  else if (age > 65) riskScore += 1;
  
  if (riskScore >= 5) return 'high';
  if (riskScore >= 3) return 'medium';
  return 'low';
};

export const detectSeizureActivity = (eegValue: number, heartRate: number): boolean => {
  // Simplified seizure detection based on EEG patterns and physiological changes
  const abnormalEEG = eegValue > 70 || eegValue < 5;
  const rapidHeartRate = heartRate > 110;
  
  // Look for combination of abnormal EEG and tachycardia
  return abnormalEEG && rapidHeartRate;
};

export const getStatusColor = (status: string): string => {
  switch (status) {
    case 'critical': return 'text-red-600 bg-red-50 border-red-200';
    case 'warning': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    case 'emergency': return 'text-red-800 bg-red-100 border-red-300';
    default: return 'text-green-600 bg-green-50 border-green-200';
  }
};

export const getVitalStatusColor = (status: VitalStatus): string => {
  switch (status) {
    case 'critical': return 'bg-red-100 text-red-600';
    case 'warning': return 'bg-yellow-100 text-yellow-600';
    default: return 'bg-green-100 text-green-600';
  }
};

export const formatTime = (date: Date): string => {
  return date.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    hour12: true 
  });
};

export const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric' 
  });
};

export const formatDateTime = (dateString: string | undefined): string => {
  if (!dateString) return '';
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return '';
  return date.toLocaleString('en-IN', { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric',
    hour: '2-digit', 
    minute: '2-digit',
    timeZone: 'Asia/Kolkata' // Your local timezone
  });
};

export const formatTimeOnly = (dateString: string | undefined): string => {
  if (!dateString) return '';
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return '';
  return date.toLocaleTimeString('en-IN', { 
    hour: '2-digit', 
    minute: '2-digit',
    second: '2-digit',
    timeZone: 'Asia/Kolkata' // Your local timezone
  });
};

export const getVitalDisplayName = (vitalType: string): string => {
  switch (vitalType) {
    case 'heartRate': return 'Heart Rate';
    case 'temperature': return 'Temperature';
    case 'skinTemperature': return 'Skin Temperature';
    case 'oxygenSat': return 'Oxygen Saturation';
    case 'respiratoryRate': return 'Respiratory Rate';
    case 'bloodPressure': return 'Blood Pressure';
    case 'ecg': return 'ECG';
    case 'eeg': return 'EEG';
    case 'bioimpedance': return 'Bioimpedance';
    case 'tremor': return 'Tremor Intensity';
    default: return vitalType;
  }
};

export const getVitalUnit = (vitalType: string): string => {
  switch (vitalType) {
    case 'heartRate': return 'BPM';
    case 'temperature': return '°F';
    case 'skinTemperature': return '°F';
    case 'oxygenSat': return '%';
    case 'respiratoryRate': return '/min';
    case 'bloodPressure': return 'mmHg';
    case 'ecg': return 'mV';
    case 'eeg': return 'μV';
    case 'bioimpedance': return 'Ω';
    case 'tremor': return '/10';
    default: return '';
  }
};

export const isNurseOrTechnician = (userRole: string): boolean => {
  return userRole === 'Nurse' || userRole === 'Senior Nurse' || userRole === 'Technician' || userRole === 'Provisioner';
};

export const canViewMedications = (userRole: string): boolean => {
  return userRole === 'Doctor' || userRole === 'Senior Consultant' || userRole === 'Nurse' || userRole === 'Admin';
};

export const canViewNotes = (userRole: string): boolean => {
  return userRole === 'Doctor' || userRole === 'Senior Consultant' || userRole === 'Nurse';
};

export const canEditNotes = (userRole: string): boolean => {
  return userRole === 'Doctor' || userRole === 'Senior Consultant' || userRole === 'Nurse';
};

export const canEditMedications = (userRole: string): boolean => {
  return userRole === 'Doctor' || userRole === 'Senior Consultant';
};

// ECG/EEG data generation removed - now handled by backend

export const getMedicationStatusColor = (status: string): string => {
  switch (status) {
    case 'active': return 'text-green-600 bg-green-50 border-green-200';
    case 'held': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    case 'stopped': return 'text-red-600 bg-red-50 border-red-200';
    default: return 'text-gray-600 bg-gray-50 border-gray-200';
  }
};

// Helper to ensure blood pressure is always integer
export const formatBloodPressure = (systolic: number, diastolic?: number): string => {
  const sys = Math.round(systolic); // Always integer
  const dia = diastolic ? Math.round(diastolic) : Math.round(systolic * 0.6); // Always integer
  return `${sys}/${dia}`;
};

// Enhanced vital sign interpretation with clinical context including new vitals
export const getVitalInterpretation = (
  heartRate: number, 
  bloodPressure: number, 
  oxygenSat: number, 
  temperature: number, 
  ecgValue: number,
  eegValue?: number,
  respiratoryRate?: number,
  skinTemperature?: number,
  bioimpedance?: number,
  tremor?: number
): string => {
  const interpretations: string[] = [];
  
  // Heart rate interpretation
  if (heartRate < 50) interpretations.push('Severe bradycardia detected');
  else if (heartRate < 60) interpretations.push('Bradycardia present');
  else if (heartRate > 120) interpretations.push('Tachycardia present');
  else if (heartRate > 100) interpretations.push('Mild tachycardia');
  
  // Blood pressure interpretation
  if (bloodPressure > 160) interpretations.push('Hypertensive crisis');
  else if (bloodPressure > 140) interpretations.push('Hypertension');
  else if (bloodPressure < 90) interpretations.push('Hypotension');
  
  // Oxygen saturation interpretation
  if (oxygenSat < 90) interpretations.push('Severe hypoxemia');
  else if (oxygenSat < 95) interpretations.push('Mild hypoxemia');
  
  // Temperature interpretation
  if (temperature > 102) interpretations.push('High fever');
  else if (temperature > 100.4) interpretations.push('Fever present');
  else if (temperature < 96) interpretations.push('Hypothermia');
  
  // Skin temperature interpretation
  if (skinTemperature) {
    if (skinTemperature > 103) interpretations.push('Elevated skin temperature');
    else if (skinTemperature < 95) interpretations.push('Low skin temperature');
  }
  
  // Respiratory rate interpretation
  if (respiratoryRate) {
    if (respiratoryRate > 25) interpretations.push('Tachypnea');
    else if (respiratoryRate < 8) interpretations.push('Bradypnea');
  }
  
  // Arrhythmia detection
  if (detectArrhythmia(heartRate, ecgValue)) {
    const arrhythmiaType = getArrhythmiaType(heartRate, ecgValue);
    if (arrhythmiaType) {
      interpretations.push(`${arrhythmiaType} detected`);
    }
  }
  
  // EEG interpretation
  if (eegValue) {
    if (detectSeizureActivity(eegValue, heartRate)) {
      interpretations.push('Possible seizure activity detected');
    } else if (eegValue > 70) {
      interpretations.push('Elevated brain activity');
    } else if (eegValue < 5) {
      interpretations.push('Low brain activity');
    }
  }
  
  // Tremor interpretation
  if (tremor) {
    if (tremor > 7) interpretations.push('Severe tremor detected');
    else if (tremor > 4) interpretations.push('Moderate tremor present');
    else if (tremor > 1) interpretations.push('Mild tremor noted');
  }
  
  // Bioimpedance interpretation
  if (bioimpedance) {
    if (bioimpedance < 350 || bioimpedance > 850) {
      interpretations.push('Abnormal bioimpedance reading');
    }
  }
  
  if (interpretations.length === 0) {
    return 'All vital signs within normal limits';
  }
  
  return interpretations.join('; ');
};

// Vital trend analysis
export const getVitalTrend = (currentValue: number, previousValue: number, vitalType: VitalType): 'rising' | 'falling' | 'stable' => {
  const threshold = getVitalTrendThreshold(vitalType);
  const difference = Math.abs(currentValue - previousValue);
  
  if (difference <= threshold) return 'stable';
  return currentValue > previousValue ? 'rising' : 'falling';
};

const getVitalTrendThreshold = (vitalType: VitalType): number => {
  switch (vitalType) {
    case 'heartRate': return 5;
    case 'temperature': return 0.5;
    case 'skinTemperature': return 0.3;
    case 'oxygenSat': return 2;
    case 'respiratoryRate': return 2;
    case 'bloodPressure': return 10;
    case 'ecg': return 10;
    case 'eeg': return 5;
    case 'bioimpedance': return 25;
    case 'tremor': return 0.5;
    default: return 1;
  }
};

// Generate realistic vital sign ranges for different patient conditions
export const getVitalRangesForCondition = (diagnosis: string) => {
  const baseRanges = {
    heartRate: { min: 60, max: 100 },
    temperature: { min: 97.0, max: 99.0 },
    skinTemperature: { min: 96.0, max: 98.0 },
    oxygenSat: { min: 95, max: 100 },
    respiratoryRate: { min: 12, max: 20 },
    bloodPressure: { min: 110, max: 140 },
    ecg: { min: 100, max: 150 },
    eeg: { min: 10, max: 60 },
    bioimpedance: { min: 450, max: 650 },
    tremor: { min: 0, max: 2 }
  };
  
  // Adjust ranges based on diagnosis
  if (diagnosis.toLowerCase().includes('cardiac') || diagnosis.toLowerCase().includes('heart')) {
    baseRanges.heartRate = { min: 70, max: 110 };
    baseRanges.ecg = { min: 90, max: 160 };
  }
  
  if (diagnosis.toLowerCase().includes('pneumonia') || diagnosis.toLowerCase().includes('respiratory')) {
    baseRanges.oxygenSat = { min: 92, max: 98 };
    baseRanges.respiratoryRate = { min: 14, max: 24 };
  }
  
  if (diagnosis.toLowerCase().includes('stroke') || diagnosis.toLowerCase().includes('neurological')) {
    baseRanges.eeg = { min: 5, max: 70 };
    baseRanges.tremor = { min: 0, max: 5 };
  }
  
  return baseRanges;
};