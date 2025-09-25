// types.ts - Complete Type definitions with Extended Vitals Support

export interface user {
  id: string;
  name: string;
  role: 'Doctor' | 'Nurse' | 'Administrator' | 'Technician' | 'Provisioner';
  nfcId?: string;
  staffId: string;
  department: string;
}

export interface alert {
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

export interface patient {
  id: string;
  name: string;
  bedNumber: string;
  ward: string;
  room: string;
  department: string;
  assignedDoctor: string;
  attendingPhysicianName?: string;
  assignedDeviceId?: string;  // ID of assigned ESP32 watch device
  deviceStatus?: 'connected' | 'disconnected' | 'offline' | 'lowBattery';  // Real-time device status
  deviceBattery?: number;  // Device battery level (0-100)
  // Enhanced patient safety fields
  allergies?: allergy[];
  codeStatus?: 'fullcode' | 'dnr' | 'dnrcca' | 'comfortcare';
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
    isEcgMode: boolean; // true = ECG, false = EEG

    // Advanced Monitoring
    bioImpedance: number; // Ohms - bioelectrical impedance
    tremor: number; // 0-10 scale tremor intensity
    fallRisk: 'low' | 'medium' | 'high'; // Fall risk assessment

    // Metadata
    lastUpdated: string;
    lastSync: string;
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

export interface noteComment {
  id: string;
  content: string;
  authorId: string;
  authorName: string;  // Backend provides lowercase version with resolved name
  authorRole: string;
  timestamp: string;
  editedAt?: string;
  canEdit: boolean;
  isEdited: boolean;
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

export interface medication {
  id: string;
  name: string;
  dosage: string;
  frequency: string;
  route: string;
  status: 'active' | 'stopped' | 'held' | 'administered';
  startDate: string;
  endDate?: string;
  duration?: string;
  prescribedBy: string;
  prescribedByName?: string;
  createdAt: string;
  modifiedBy?: string;
  updatedAt?: string;
  canEdit?: boolean;
  history?: medicationHistoryEntry[];
}

export interface medicationHistoryEntry {
  id: string;
  action: 'prescribed' | 'held' | 'resumed' | 'stopped' | 'modified' | 'administered';
  timestamp: string;
  performedBy: string;
  reason?: string;
  previousState?: any;
  newState?: any;
}

export interface investigation {
  id: string;
  type: 'lab' | 'imaging' | 'biopsy' | 'culture';
  name: string;
  createdAt: string;
  scheduledAt?: string;
  completedAt?: string;
  status: 'ordered' | 'scheduled' | 'inProgress' | 'completed' | 'cancelled';
  results?: string;
  labResults?: labresult[]; // Detailed lab results
  performedBy: string;
  performedByName?: string;
  priority: 'routine' | 'urgent' | 'stat';
  urgency: 'STAT' | 'Emergency' | 'Urgent' | 'Routine'; // Added urgency field
  notes?: string;
  canEdit: boolean;
}

export interface therapy {
  id: string;
  type: 'physiotherapy' | 'occupational' | 'speech' | 'respiratory';
  name: string; // Added name field
  description: string;
  frequency: string;
  duration: string;
  startDate: string;
  endDate?: string;
  status: 'active' | 'completed' | 'cancelled';
  performedBy: string;
  performedByName?: string;
  therapist?: string;
  notes?: string;
  sessions: therapySession[];
  canEdit: boolean;
}

export interface therapySession {
  id: string;
  date: string;
  duration: number; // minutes
  notes: string;
  therapist: string;
  patientResponse: string;
}

export interface caseSheetEntry {
  id: string;
  timestamp: string;
  type: 'admission' | 'medication' | 'investigation' | 'therapy' | 'vitalAlert' | 'statusChange' | 'alertAcknowledged' | 'discharge' | 'doctorNotes' | 'nursingNotes' | 'therapistNotes' | 'technicianNotes' | 'pharmacyNotes' | 'otherNotes' | 'handoffNote' | 'medicationAdministration';
  description: string;
  performedBy: string;
  performedByName?: string;
  details?: any;
  canEdit: boolean;
}

export interface vitalhistory {
  time: string;
  heartRate: number;
  temperature: number;
  oxygenSat: number;
  respiratoryRate: number;
  bloodPressure: number; // systolic
  bloodPressureDiastolic?: number;
  ecg: number;
  eeg: number;
  bioImpedance: number;
  tremor: number;
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

export interface auditlog {
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

export interface appsettings {
  autologoutminutes: number;
  enableautologout: boolean;
  bedsidemode: boolean;
  // New settings for extended monitoring
  arrhythmiadetection?: boolean;
  eegmonitoring?: boolean;
  tremordetection?: boolean;
  falldetection?: boolean;
  audioalarms?: boolean;
  privacymode?: boolean;
  autoscrollspeed?: number; // pixels per second for auto-scroll
  enableautoscroll?: boolean;
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

export interface backenduser {
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

export interface authenticationresponse {
  success: boolean;
  user?: user;
  token?: string;
  message?: string;
  auditLogId?: string;
}

export interface systemstatus {
  online: boolean;
  lastSync: string;
  serverHealth: 'healthy' | 'degraded' | 'down';
  connectedDevices: number;
  activeUsers: number;
}

// Extended vital types
export type vitaltype = 'heartRate' | 'oxygenSat' | 'temperature' | 'skintemperature' | 'ecg' | 'eeg' | 'bloodPressure' | 'respiratoryRate' | 'bioImpedance' | 'tremor';
export type vitalstatus = 'normal' | 'warning' | 'critical';
export type timerange = '1h' | '6h' | '24h' | '7d';
export type authmethod = 'nfc' | 'credentials';
export type userRole = 'doctor' | 'nurse' | 'administrator' | 'technician' | 'provisioner';
export type patientstatus = 'stable' | 'critical' | 'emergency';
export type alertseverity = 'low' | 'medium' | 'high' | 'critical';
export type medicationstatus = 'active' | 'stopped' | 'held';
export type investigationstatus = 'ordered' | 'scheduled' | 'inProgress' | 'completed' | 'cancelled';
export type therapystatus = 'active' | 'completed' | 'cancelled';
export type MonitoringMode = 'ecg' | 'eeg';

// Enhanced monitoring configuration
export interface monitoringconfig {
  vitalSignThresholds: {
    heartRate: { min: number; max: number; criticalMin: number; criticalMax: number };
    bloodPressure: { min: number; max: number; criticalMin: number; criticalMax: number };
    temperature: { min: number; max: number; criticalMin: number; criticalMax: number };
    skinTemperature: { min: number; max: number; criticalMin: number; criticalMax: number };
    oxygenSat: { min: number; max: number; criticalMin: number; criticalMax: number };
    respiratoryRate: { min: number; max: number; criticalMin: number; criticalMax: number };
    ecg: { min: number; max: number; criticalMin: number; criticalMax: number };
    eeg: { min: number; max: number; criticalMin: number; criticalMax: number };
    bioImpedance: { min: number; max: number; criticalMin: number; criticalMax: number };
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
export interface clinicalalert {
  id: string;
  patientId: string;
  type: 'drugInteraction' | 'allergyWarning' | 'dosageAlert' | 'vitalThreshold' | 'arrhythmia' | 'seizure' | 'tremor' | 'fallRisk' | 'clinicalGuideline';
  severity: alertseverity;
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
export interface druginteraction {
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
export interface allergy {
  id: string;
  patientId: string;
  allergen: string;
  allergentype: 'medication' | 'food' | 'environmental' | 'other';
  reaction: string;
  severity: 'mild' | 'moderate' | 'severe' | 'life-threatening';
  onset: string;
  verificationstatus: 'confirmed' | 'unconfirmed' | 'entered-in-error';
  recordeddate: string;
  performedBy: string;
}

// Clinical Protocols
export interface clinicalprotocol {
  id: string;
  name: string;
  condition: string;
  department: string;
  steps: protocolstep[];
  triggers: string[];
  isActive: boolean;
  version: string;
  lastUpdated: string;
}

export interface protocolstep {
  id: string;
  stepNumber: number;
  action: string;
  condition?: string;
  timing: string;
  responsible: string[];
  documentation: string[];
}

// Barcode System
export interface barcodedata {
  type: 'patient' | 'medication' | 'equipment' | 'staff';
  id: string;
  data: string;
  timestamp: string;
  scannedBy: string;
}

export interface medicationbarcode {
  ndc: string;
  lotNumber: string;
  expirationDate: string;
  medicationName: string;
  dosage: string;
  manufacturer: string;
}

// Lab Integration
export interface labresult {
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
  completedat: string;
  performingLab: string;
  performedBy: string;
  performedByName?: string;
}

// Imaging/PACS
export interface imagingstudy {
  id: string;
  patientId: string;
  studyType: 'xray' | 'ct' | 'mri' | 'ultrasound' | 'mammography' | 'pet' | 'nuclear';
  bodyPart: string;
  createdAt: string;
  status: 'scheduled' | 'inProgress' | 'completed' | 'cancelled';
  images: imagingimage[];
  report?: imagingreport;
  performedBy: string;
  performedByName?: string;
  technologist?: string;
  radiologist?: string;
  urgency: 'routine' | 'urgent' | 'stat';
}

export interface imagingimage {
  id: string;
  url: string;
  thumbnail: string;
  series: string;
  instanceNumber: number;
  viewPosition?: string;
}

export interface imagingreport {
  id: string;
  findings: string;
  impression: string;
  recommendations: string;
  performedBy: string;
  createdAt: string;
  status: 'preliminary' | 'final' | 'addendum';
}

// Pharmacy Integration
export interface pharmacyorder {
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
export interface qualitymetric {
  id: string;
  name: string;
  value: number;
  target: number;
  unit: string;
  period: string;
  department?: string;
  trend: 'improving' | 'stable' | 'declining';
  lastcalculated: string;
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

// Integration APIs
export interface externalsystem {
  id: string;
  name: string;
  type: 'lab' | 'pharmacy' | 'imaging' | 'billing' | 'ehr' | 'other';
  endpoint: string;
  authtype: 'apiKey' | 'oauth' | 'basic' | 'certificate';
  status: 'active' | 'inactive' | 'error';
  lastSync?: string;
  version?: string;
}

// Medical record interface for edit time checking
export interface editableRecord {
  id: string;
  createdAt?: string;
  timestamp?: string;
  canEdit?: boolean;
}

// Type aliases for backward compatibility
export type clinicalAlert = clinicalalert;
export type labResult = labresult;
export type imagingStudy = imagingstudy;
