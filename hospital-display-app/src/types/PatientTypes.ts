/**
 * PatientTypes - Patient and vital signs type definitions
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Core patient data structures and vital sign monitoring types
 */

import { medication, investigation, therapy, allergy } from './MedicalTypes';

export interface patient {
  id: string;
  mrn?: string;  // Medical Record Number - optional for backward compatibility
  name: string;
  firstName: string;
  lastName: string;
  bedNumber: string;
  roomNumber: string;
  ward: string;
  room: string;
  department: string;
  assignedDoctor: string;
  attendingPhysician: string;
  attendingPhysicianName?: string;
  nurseInCharge: string;
  assignedDeviceId?: string;  // ID of assigned ESP32 watch device
  deviceStatus?: 'connected' | 'disconnected' | 'offline' | 'lowBattery';  // Real-time device status
  deviceBatteryLevel?: number;  // Device battery level (0-100) - matches backend field
  deviceLastSeen?: string;  // Device last seen timestamp - matches backend field
  deviceSerialNumber?: string;  // Device serial number
  deviceName?: string;  // Device display name
  deviceModel?: string;  // Device model
  deviceManufacturer?: string;  // Device manufacturer
  deviceMacAddress?: string;  // Device MAC address
  deviceFirmwareVersion?: string;  // Device firmware version
  deviceLocation?: string;  // Device location
  deviceAssignedAt?: string;  // When device was assigned
  deviceAssignedBy?: string;  // Who assigned the device
  deviceCalibrationDate?: string;  // Last calibration date
  deviceNextMaintenanceDate?: string;  // Next maintenance due date
  // Enhanced patient safety fields
  allergies?: allergy[];
  codeStatus?: 'fullcode' | 'dnr' | 'dnrcca' | 'comfortcare';
  activeProblems?: string[];
  lastMedicationTime?: string;
  nextMedicationDue?: string;
  vitals: {
    // Cardiovascular - STANDARDIZED NAMES
    heartRate: number; // Always integer - BPM
    systolicPressure: number; // mmHg
    diastolicPressure: number; // mmHg

    // Respiratory - STANDARDIZED NAMES
    respiratoryRate: number; // Always integer - breaths per minute
    oxygenSaturation: number; // Always integer - percentage

    // Temperature - STANDARDIZED NAME
    skinTemperature: number; // Can have decimals - Fahrenheit

    // Neurological/Cardiac Monitoring - STANDARDIZED NAMES
    ecgReading: number; // Always integer - mV * 100 (so 120 = 1.2mV)
    eegReading: number; // Always integer - μV (microvolts)
    isEcgMode: boolean; // true = ECG, false = EEG

    // Advanced Monitoring - BACKEND ALIGNED NAMES (Phase 2)
    bioimpedance: number; // 20-50Ω thoracic impedance from MAX86178
    tremor: number; // 0-10 scale from BMI323
    imuFallRisk: number; // 0-10 numeric fall risk from BMI323
    perfusionIndex?: number; // 0-20% perfusion index from MAX86178
    stepCount?: number; // Step count from BMI323 IMU
    watchWorn?: boolean; // Watch worn status from MAX86178 proximity
    lastMovementTime?: number; // Last movement timestamp in ms from BMI323

    // Nested ECG/EEG Analysis Objects (8-12 Channel Support)
    ecg?: {
      // Computed ECG metrics (backend calculates)
      rrInterval?: number; // RR interval in ms
      qrsDuration?: number; // QRS duration in ms
      qtInterval?: number; // QT interval in ms
      axis?: number; // Heart axis in degrees
      rhythm?: string; // Detected rhythm (sinus, afib, etc.)
      stSegment?: 'normal' | 'elevated' | 'depressed'; // ST segment analysis
    };
    eeg?: {
      // EEG band powers (backend calculates)
      alphaPower?: number; // Alpha band (8-13 Hz)
      betaPower?: number; // Beta band (13-30 Hz)
      thetaPower?: number; // Theta band (4-8 Hz)
      deltaPower?: number; // Delta band (0.5-4 Hz)
      gammaPower?: number; // Gamma band (30-100 Hz)
      dominantFrequency?: number; // Dominant frequency in Hz
      seizureActivity?: boolean; // Seizure detection flag
    };

    // Metadata - STANDARDIZED NAMES
    lastDataReceived: string;
    dataQualityScore: number; // 0-1 scale for data quality
  };
  status: 'stable' | 'critical' | 'emergency' | 'active' | 'pendingDischarge' | 'readyForNurse' | 'discharged' | 'dischargeApproved';
  dischargeStatus?: 'active' | 'requested' | 'adminapproved' | 'discharged';
  alerts: alert[];
  admissionDate: string;
  age: number;
  gender: string;
  weight: number; // in kg
  diagnosis: string;
  medications: medication[];
  investigations: investigation[];
  therapies: therapy[];
  notes: noteComment[];
  caseSheet: caseSheetEntry[];
  handoffNotes?: handoffNote[];
}

export interface alert {
  id: string;
  message: string;
  type?: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  timestamp: string;
  acknowledgedBy?: string;
  acknowledgedByName?: string;
  acknowledgedByRole?: string;
  acknowledgedAt?: string;
  isAcknowledged: boolean;
}

export interface noteComment {
  id: string;
  content: string;
  authorId: string;
  authorName?: string;  // Backend provides via LEFT JOIN staff lookup
  authorRole?: string;  // Backend provides via LEFT JOIN staff lookup
  timestamp: string;
  editedBy?: string;
  editedByName?: string;
  editedAt?: string;
  canEdit: boolean;
  isEdited: boolean;
  isHandoffNote?: boolean;
}

export interface handoffNote {
  id: string;
  patientId: string;
  shift: 'day' | 'evening' | 'night';
  fromNurse: string;
  toNurse: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  category: 'medication' | 'assessment' | 'procedure' | 'safety' | 'family' | 'other';
  note: string;
  timestamp: string;
  acknowledged: boolean;
  performedBy?: string;
  performedByName?: string;
  completedAt?: string;
}

export interface caseSheetEntry {
  id: string;
  timestamp: string;
  type: 'admission' | 'medication' | 'investigation' | 'therapy' | 'vitalAlert' | 'statusChange' | 'discharge' |
        'doctorNote' | 'nurseNote' | 'therapistNote' | 'pharmacistNote' | 'technicianNote' | 'clinicalNote' |
        'handoffNote' | 'medicationAdministration' | 'caseEntry' | 'note' |
        'alertTriggered' | 'alertAcknowledged' | 'alertResolved' | 'alertEscalated' |
        'medication_status_change' | 'medication_administration';  // Backend snake_case types
  description: string;
  performedBy: string;
  performedByName?: string;
  performedByRole?: string;
  details?: any;
  canEdit: boolean;
}

export interface vitalhistory {
  time: string;
  heartRate: number;
  skinTemperature: number;
  oxygenSaturation: number;
  respiratoryRate: number;
  systolicPressure: number; // mmHg
  diastolicPressure: number; // mmHg
  ecgReading: number;
  eegReading: number;
  bioimpedance: number; // 20-50Ω thoracic
  tremor: number; // 0-10 scale
  imuFallRisk?: number; // 0-10 scale
  perfusionIndex?: number; // 0-20%
  stepCount?: number;
}

export interface ecgreading {
  timestamp: string;
  duration: number;
  samplerate: number;
  data: number[];
  interpretation: string;
  performedBy: string;
  arrhythmiadetected?: boolean;
  arrhythmiatype?: string;
}

export interface eegreading {
  timestamp: string;
  duration: number;
  samplerate: number;
  data: number[];
  channels: string[]; // ['F3', 'F4', 'C3', 'C4'] etc
  interpretation: string;
  performedBy: string;
  seizureactivity?: boolean;
  abnormalpatterns?: string[];
}

export interface ecgpoint {
  x: number;
  y: number;
}

export interface roomproximity {
  tabletLocation: string;
  roomNumber: string;
  patientsInRoom: string[];
  lastDetection: string;
}

// Enhanced vital sign monitoring types
export interface vitaltrend {
  timestamp: string;
  value: number;
  status: vitalstatus;
  trend: 'rising' | 'falling' | 'stable';
}

export interface arrhythmiaevent {
  id: string;
  timestamp: string;
  patientId: string;
  type: 'bradycardia' | 'tachycardia' | 'atrialfibrillation' | 'ventriculartachycardia' | 'pvc' | 'irregularrhythm';
  severity: 'low' | 'medium' | 'high' | 'critical';
  heartRate: number;
  ecgvalue: number;
  description: string;
  acknowledged: boolean;
  performedBy?: string;
  completedAt?: string;
}

export interface tremorevent {
  id: string;
  timestamp: string;
  patientId: string;
  intensity: number; // 0-10 scale
  duration: number; // seconds
  type: 'resting' | 'action' | 'postural';
  frequency: number; // Hz
  acknowledged: boolean;
}

export interface fallevent {
  id: string;
  timestamp: string;
  patientId: string;
  risklevel: 'low' | 'medium' | 'high';
  accelerometerdata: number[];
  location: string;
  acknowledged: boolean;
  falsealarm?: boolean;
}

export interface patientoutcome {
  id: string;
  patientId: string;
  measureType: 'lengthOfStay' | 'readmission' | 'mortality' | 'infection' | 'satisfaction';
  value: number;
  expectedValue?: number;
  riskAdjusted: boolean;
  dischargeDate?: string;
  followUpDate?: string;
}

export interface dischargeRequest {
  id: number;
  patientId: string;
  status: 'requested' | 'approved' | 'completed' | 'cancelled';
  reason: string;
  notes?: string;

  requestedBy: string;
  requestedByName?: string;
  requestedAt: string;

  approvedBy?: string;
  approvedByName?: string;
  approvedAt?: string;
  approvalNotes?: string;

  performedBy?: string;
  performedByName?: string;
  performedAt?: string;
  dischargeNotes?: string;
}

// Type aliases for patient-related types
export type vitaltype = 'heartRate' | 'oxygenSaturation' | 'skinTemperature' | 'ecgReading' | 'eegReading' | 'systolicPressure' | 'diastolicPressure' | 'respiratoryRate' | 'bioimpedance' | 'tremor' | 'imuFallRisk' | 'perfusionIndex' | 'stepCount';
export type vitalstatus = 'normal' | 'warning' | 'critical';
export type timerange = '1h' | '6h' | '24h' | '7d';
export type patientstatus = 'stable' | 'critical' | 'emergency';
export type alertseverity = 'low' | 'medium' | 'high' | 'critical';
export type MonitoringMode = 'ecgReading' | 'eegReading';

// Medical record interface for edit time checking
export interface editableRecord {
  id: string;
  createdAt?: string;
  timestamp?: string;
  canEdit?: boolean;
}