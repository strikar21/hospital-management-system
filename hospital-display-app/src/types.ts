// types.ts - Complete Type definitions with Extended Vitals Support

export interface User {
  id: string;
  name: string;
  role: 'Doctor' | 'Nurse' | 'Administrator' | 'Technician' | 'Provisioner';
  nfcId?: string;
  staffId: string;
  department: string;
}

export interface Alert {
  id: string;
  message: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  timestamp: string;
  performedBy?: string;
  performedByName?: string;
  performedByRole?: string;
  completedAt?: string;
  isAcknowledged: boolean;
}

export interface Patient {
  id: string;
  name: string;
  bedNumber: string;
  ward: string;
  room: string;
  department: string;
  assignedDoctor: string;
  attendingphysicianname?: string;
  assignedDeviceId?: string;  // ID of assigned ESP32 watch device
  deviceStatus?: 'connected' | 'disconnected' | 'offline' | 'low_battery';  // Real-time device status
  deviceBattery?: number;  // Device battery level (0-100)
  // Enhanced patient safety fields
  allergies?: Allergy[];
  codeStatus?: 'fullCode' | 'dnr' | 'dnrCca' | 'comfortCare';
  activeProblems?: string[];
  lastMedicationTime?: string;
  nextMedicationDue?: string;
  vitals: {
    // Cardiovascular
    heartRate: number; // Always integer - BPM
    bloodPressure: string; // Formatted string "120/80"
    bloodPressureValue: number; // Always integer - systolic pressure
    
    // Respiratory
    respiratoryRate: number; // Always integer - breaths per minute
    oxygenSat: number; // Always integer - percentage
    
    // Temperature
    temperature: number; // Can have decimals - Fahrenheit
    
    // Neurological/Cardiac Monitoring
    ecg: number; // Always integer - mV * 100 (so 120 = 1.2mV)
    eeg: number; // Always integer - μV (microvolts)
    isECGMode: boolean; // true = ECG, false = EEG
    
    // Advanced Monitoring
    bioimpedance: number; // Ohms - bioelectrical impedance
    tremor: number; // 0-10 scale tremor intensity
    fallRisk: 'low' | 'medium' | 'high'; // Fall risk assessment
    
    // Metadata
    lastUpdated: string;
    lastSync: string;
  };
  status: 'stable' | 'critical' | 'emergency' | 'active' | 'pending_discharge' | 'ready_for_nurse' | 'discharged' | 'PENDING_DISCHARGE' | 'DISCHARGE_APPROVED' | 'discharge_approved';
  dischargeStatus?: 'active' | 'requested' | 'adminapproved' | 'discharged';
  alerts: Alert[];
  admissionDate: string;
  age: number;
  gender: string;
  weight: number; // in kg
  diagnosis: string;
  medications: Medication[];
  investigations: Investigation[];
  therapies: Therapy[];
  notes: NoteComment[];
  caseSheet: CaseSheetEntry[];
  handoffNotes?: HandoffNote[];
}

export interface NoteComment {
  id: string;
  content: string;
  authorId: string;
  authorName: string;
  authorname?: string;  // Backend provides lowercase version with resolved name
  authorRole: string;
  timestamp: string;
  editedAt?: string;
  canEdit: boolean;
  isEdited: boolean;
}

export interface HandoffNote {
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
  performedbyname?: string;
  completedAt?: string;
}

export interface Medication {
  id: string;
  name: string;
  dosage: string;
  frequency: string;
  route: string;
  status: 'active' | 'stopped' | 'held' | 'administered';
  startdate: string;
  enddate?: string;
  duration?: string;
  prescribedby: string;
  prescribedbyname?: string;
  createdat: string;
  modifiedBy?: string;
  updatedat?: string;
  canEdit?: boolean;
  history?: MedicationHistoryEntry[];
}

export interface MedicationHistoryEntry {
  id: string;
  action: 'prescribed' | 'held' | 'resumed' | 'stopped' | 'modified' | 'administered';
  timestamp: string;
  performedBy: string;
  reason?: string;
  previousState?: any;
  newState?: any;
}

export interface Investigation {
  id: string;
  type: 'lab' | 'imaging' | 'biopsy' | 'culture';
  name: string;
  createdat: string;
  scheduledat?: string;
  completedat?: string;
  status: 'ordered' | 'scheduled' | 'in_progress' | 'completed' | 'cancelled';
  results?: string;
  labResults?: LabResult[]; // Detailed lab results
  performedby: string;
  performedbyname?: string;
  priority: 'routine' | 'urgent' | 'stat';
  notes?: string;
  canEdit: boolean;
}

export interface Therapy {
  id: string;
  type: 'physiotherapy' | 'occupational' | 'speech' | 'respiratory';
  description: string;
  frequency: string;
  duration: string;
  startdate: string;
  enddate?: string;
  status: 'active' | 'completed' | 'cancelled';
  performedby: string;
  performedbyname?: string;
  therapist?: string;
  notes?: string;
  sessions: TherapySession[];
  canEdit: boolean;
}

export interface TherapySession {
  id: string;
  date: string;
  duration: number; // minutes
  notes: string;
  therapist: string;
  patientResponse: string;
}

export interface CaseSheetEntry {
  id: string;
  timestamp: string;
  type: 'admission' | 'medication' | 'investigation' | 'therapy' | 'vitalAlert' | 'statusChange' | 'alertAcknowledged' | 'discharge' | 'doctorNotes' | 'nursingNotes' | 'therapistNotes' | 'technicianNotes' | 'pharmacyNotes' | 'otherNotes' | 'handoffNote' | 'medicationAdministration';
  description: string;
  performedBy: string;
  performedbyname?: string;
  details?: any;
  canEdit: boolean;
}

export interface VitalHistory {
  time: string;
  heartRate: number;
  temperature: number;
  oxygenSat: number;
  respiratoryRate: number;
  bloodPressure: number; // systolic
  bloodPressureDiastolic?: number;
  ecg: number;
  eeg: number;
  bioimpedance: number;
  tremor: number;
}

export interface ECGReading {
  timestamp: string;
  duration: number;
  sampleRate: number;
  data: number[];
  interpretation: string;
  performedBy: string;
  arrhythmiaDetected?: boolean;
  arrhythmiaType?: string;
}

export interface EEGReading {
  timestamp: string;
  duration: number;
  sampleRate: number;
  data: number[];
  channels: string[]; // ['F3', 'F4', 'C3', 'C4'] etc
  interpretation: string;
  performedBy: string;
  seizureActivity?: boolean;
  abnormalPatterns?: string[];
}

export interface ECGPoint {
  x: number;
  y: number;
}

export interface RoomProximity {
  tabletLocation: string;
  roomNumber: string;
  patientsInRoom: string[];
  lastDetection: string;
}

export interface AuditLog {
  id: string;
  timestamp: string;
  userId: string;
  userRole: string;
  action: string;
  entityType: 'patient' | 'medication' | 'investigation' | 'therapy' | 'notes' | 'alert';
  entityId: string;
  changes: any;
  ipAddress: string;
  deviceInfo: string;
}

export interface AppSettings {
  autoLogoutMinutes: number;
  enableAutoLogout: boolean;
  bedsideMode: boolean;
  // New settings for extended monitoring
  arrhythmiaDetection?: boolean;
  eegMonitoring?: boolean;
  tremorDetection?: boolean;
  fallDetection?: boolean;
  audioAlarms?: boolean;
  privacyMode?: boolean;
  autoScrollSpeed?: number; // pixels per second for auto-scroll
  enableAutoScroll?: boolean;
}

// Enhanced vital sign monitoring types
export interface VitalTrend {
  timestamp: string;
  value: number;
  status: VitalStatus;
  trend: 'rising' | 'falling' | 'stable';
}

export interface ArrhythmiaEvent {
  id: string;
  timestamp: string;
  patientId: string;
  type: 'bradycardia' | 'tachycardia' | 'atrialFibrillation' | 'ventricularTachycardia' | 'pvc' | 'irregularRhythm';
  severity: 'low' | 'medium' | 'high' | 'critical';
  heartRate: number;
  ecgValue: number;
  description: string;
  acknowledged: boolean;
  performedBy?: string;
  completedAt?: string;
}

export interface TremorEvent {
  id: string;
  timestamp: string;
  patientId: string;
  intensity: number; // 0-10 scale
  duration: number; // seconds
  type: 'resting' | 'action' | 'postural';
  frequency: number; // Hz
  acknowledged: boolean;
}

export interface FallEvent {
  id: string;
  timestamp: string;
  patientId: string;
  riskLevel: 'low' | 'medium' | 'high';
  accelerometerData: number[];
  location: string;
  acknowledged: boolean;
  falseAlarm?: boolean;
}

export interface BackendUser {
  id: string;
  name: string;
  role: 'Doctor' | 'Nurse' | 'Administrator' | 'Technician' | 'Provisioner';
  nfcId: string;
  staffId: string;
  department: string;
  isActive: boolean;
  lastLogin?: string;
  passwordHash?: string;
}

export interface AuthenticationResponse {
  success: boolean;
  user?: User;
  token?: string;
  message?: string;
  auditLogId?: string;
}

export interface SystemStatus {
  online: boolean;
  lastSync: string;
  serverHealth: 'healthy' | 'degraded' | 'down';
  connectedDevices: number;
  activeUsers: number;
}

// Extended vital types
export type VitalType = 'heartRate' | 'oxygenSat' | 'temperature' | 'skinTemperature' | 'ecg' | 'eeg' | 'bloodPressure' | 'respiratoryRate' | 'bioimpedance' | 'tremor';
export type VitalStatus = 'normal' | 'warning' | 'critical';
export type TimeRange = '1h' | '6h' | '24h' | '7d';
export type AuthMethod = 'nfc' | 'credentials';
export type UserRole = 'Doctor' | 'Nurse' | 'Administrator' | 'Technician' | 'Provisioner';
export type PatientStatus = 'stable' | 'critical' | 'emergency';
export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical';
export type MedicationStatus = 'active' | 'stopped' | 'held';
export type InvestigationStatus = 'ordered' | 'scheduled' | 'in_progress' | 'completed' | 'cancelled';
export type TherapyStatus = 'active' | 'completed' | 'cancelled';
export type MonitoringMode = 'ecg' | 'eeg';

// Enhanced monitoring configuration
export interface MonitoringConfig {
  vitalSignThresholds: {
    heartRate: { min: number; max: number; criticalMin: number; criticalMax: number };
    bloodPressure: { min: number; max: number; criticalMin: number; criticalMax: number };
    temperature: { min: number; max: number; criticalMin: number; criticalMax: number };
    skinTemperature: { min: number; max: number; criticalMin: number; criticalMax: number };
    oxygenSat: { min: number; max: number; criticalMin: number; criticalMax: number };
    respiratoryRate: { min: number; max: number; criticalMin: number; criticalMax: number };
    ecg: { min: number; max: number; criticalMin: number; criticalMax: number };
    eeg: { min: number; max: number; criticalMin: number; criticalMax: number };
    bioimpedance: { min: number; max: number; criticalMin: number; criticalMax: number };
    tremor: { maxIntensity: number; maxDuration: number };
  };
  arrhythmiaDetection: {
    enabled: boolean;
    sensitivity: 'low' | 'medium' | 'high';
    algorithms: string[];
  };
  eegMonitoring: {
    enabled: boolean;
    seizureDetection: boolean;
    abnormalPatternDetection: boolean;
  };
  tremorDetection: {
    enabled: boolean;
    sensitivity: 'low' | 'medium' | 'high';
    threshold: number;
  };
  fallDetection: {
    enabled: boolean;
    sensitivity: 'low' | 'medium' | 'high';
    autoAlert: boolean;
  };
  alerting: {
    audioEnabled: boolean;
    visualEnabled: boolean;
    escalationTimeout: number; // minutes
    autoAcknowledgeTimeout: number; // minutes
  };
}

// Clinical decision support types
export interface ClinicalAlert {
  id: string;
  patientId: string;
  type: 'drugInteraction' | 'allergyWarning' | 'dosageAlert' | 'vitalThreshold' | 'arrhythmia' | 'seizure' | 'tremor' | 'fallRisk' | 'clinicalGuideline';
  severity: AlertSeverity;
  message: string;
  details: string;
  actionRequired: boolean;
  suggestedActions?: string[];
  timestamp: string;
  performedBy?: string;
  completedAt?: string;
  isAcknowledged: boolean;
}

// Drug Interaction System
export interface DrugInteraction {
  id: string;
  drug1: string;
  drug2: string;
  severity: 'mild' | 'moderate' | 'major' | 'contraindicated';
  description: string;
  clinicalSignificance: string;
  management: string;
  documentation: 'excellent' | 'good' | 'fair' | 'poor';
}

// Allergy System
export interface Allergy {
  id: string;
  patientId: string;
  allergen: string;
  allergenType: 'medication' | 'food' | 'environmental' | 'other';
  reaction: string;
  severity: 'mild' | 'moderate' | 'severe' | 'life-threatening';
  onset: string;
  verificationStatus: 'confirmed' | 'unconfirmed' | 'entered-in-error';
  recordedDate: string;
  performedBy: string;
}

// Clinical Protocols
export interface ClinicalProtocol {
  id: string;
  name: string;
  condition: string;
  department: string;
  steps: ProtocolStep[];
  triggers: string[];
  isActive: boolean;
  version: string;
  lastUpdated: string;
}

export interface ProtocolStep {
  id: string;
  stepNumber: number;
  action: string;
  condition?: string;
  timing: string;
  responsible: string[];
  documentation: string[];
}

// Barcode System
export interface BarcodeData {
  type: 'patient' | 'medication' | 'equipment' | 'staff';
  id: string;
  data: string;
  timestamp: string;
  scannedBy: string;
}

export interface MedicationBarcode {
  ndc: string;
  lotNumber: string;
  expirationDate: string;
  medicationName: string;
  dosage: string;
  manufacturer: string;
}

// Lab Integration
export interface LabResult {
  id: string;
  patientId: string;
  testName: string;
  testCode: string;
  result: string;
  normalRange: string;
  units: string;
  status: 'pending' | 'preliminary' | 'final' | 'corrected' | 'cancelled';
  abnormalFlag: 'normal' | 'high' | 'low' | 'criticalHigh' | 'criticalLow';
  createdAt: string;
  completedAt: string;
  performingLab: string;
  performedBy: string;
  performedbyname?: string;
}

// Imaging/PACS
export interface ImagingStudy {
  id: string;
  patientId: string;
  studyType: 'xray' | 'ct' | 'mri' | 'ultrasound' | 'mammography' | 'pet' | 'nuclear';
  bodyPart: string;
  createdat: string;
  status: 'scheduled' | 'in_progress' | 'completed' | 'cancelled';
  images: ImagingImage[];
  report?: ImagingReport;
  performedby: string;
  performedbyname?: string;
  technologist?: string;
  radiologist?: string;
  urgency: 'routine' | 'urgent' | 'stat';
}

export interface ImagingImage {
  id: string;
  url: string;
  thumbnail: string;
  series: string;
  instanceNumber: number;
  viewPosition?: string;
}

export interface ImagingReport {
  id: string;
  findings: string;
  impression: string;
  recommendations: string;
  performedby: string;
  createdat: string;
  status: 'preliminary' | 'final' | 'addendum';
}

// Pharmacy Integration
export interface PharmacyOrder {
  id: string;
  patientId: string;
  medicationId: string;
  prescriptionId: string;
  status: 'pending' | 'verified' | 'prepared' | 'dispensed' | 'administered' | 'cancelled';
  quantity: number;
  dispensedQuantity?: number;
  pharmacist?: string;
  performedBy?: string;
  completedAt?: string;
  notes?: string;
}

// Analytics/Reporting
export interface QualityMetric {
  id: string;
  name: string;
  value: number;
  target: number;
  unit: string;
  period: string;
  department?: string;
  trend: 'improving' | 'stable' | 'declining';
  lastCalculated: string;
}

export interface PatientOutcome {
  id: string;
  patientId: string;
  measureType: 'lengthOfStay' | 'readmission' | 'mortality' | 'infection' | 'satisfaction';
  value: number;
  expectedValue?: number;
  riskAdjusted: boolean;
  dischargeDate?: string;
  followUpDate?: string;
}

// Integration APIs
export interface ExternalSystem {
  id: string;
  name: string;
  type: 'lab' | 'pharmacy' | 'imaging' | 'billing' | 'ehr' | 'other';
  endpoint: string;
  authType: 'apiKey' | 'oauth' | 'basic' | 'certificate';
  status: 'active' | 'inactive' | 'error';
  lastSync?: string;
  version?: string;
}