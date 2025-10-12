/**
 * MedicalTypes - Medical care and treatment type definitions
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medication, investigation, therapy, and allergy management types
 */

/**
 * MedicalRecordAudit - Base interface for medical record audit fields
 */
interface MedicalRecordAudit {
  createdBy?: string;
  createdByName?: string;
  createdAt: string;
  updatedAt?: string;
}

export interface medication extends MedicalRecordAudit {
  id: string;
  name: string;
  dosage: string;
  frequency: string;
  route: string;
  status: 'active' | 'stopped' | 'held' | 'discontinued' | 'administered';
  startDate: string;
  endDate?: string;
  duration?: string;
  prescribedBy: string;
  prescribedByName?: string;
  modifiedBy?: string;
  canEdit?: boolean;
  history?: medicationHistoryEntry[];
}

export interface medicationAdministration extends MedicalRecordAudit {
  id: string;
  medicationId: string;
  patientId: string;
  scheduledTime: string;
  performedAt: string;
  performedBy: string;
  performedByName?: string;
  dosageGiven: string;
  route: string;
  status: 'scheduled' | 'completed' | 'missed' | 'refused';
  notes?: string;
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

export interface investigation extends MedicalRecordAudit {
  id: string;
  type: 'lab' | 'imaging' | 'biopsy' | 'culture';
  name: string;
  orderedAt?: string; // Add missing orderedAt field
  scheduledAt?: string;
  completedAt?: string;
  status: 'pending' | 'ordered' | 'scheduled' | 'inProgress' | 'completed' | 'cancelled';
  results?: string;
  labResults?: labresult[]; // Detailed lab results
  prescribedBy: string;
  prescribedByName?: string;
  performedBy?: string;
  performedByName?: string;
  priority: 'routine' | 'urgent' | 'stat';
  urgency: 'STAT' | 'Emergency' | 'Urgent' | 'Routine'; // Added urgency field
  notes?: string;
  canEdit: boolean;
}

export interface therapy extends MedicalRecordAudit {
  id: string;
  type: 'physiotherapy' | 'occupational' | 'speech' | 'respiratory';
  name: string; // Added name field
  description: string;
  frequency: string;
  duration: string;
  startDate: string;
  endDate?: string;
  status: 'active' | 'completed' | 'cancelled';
  prescribedBy: string;
  prescribedByName?: string;
  therapist?: string;
  notes?: string;
  sessions: therapySession[];
  canEdit: boolean;
  // Inherits: createdBy, createdByName, createdAt, updatedAt
}

export interface therapySession extends MedicalRecordAudit {
  id: string;
  therapyId: string;
  patientId: string;
  sessionNumber: number;
  scheduledDate?: string;
  completedAt?: string;
  performedBy?: string;
  performedByName?: string;
  sessionNotes?: string;
  status: 'scheduled' | 'completed' | 'cancelled';
  duration?: string;
  // Inherits: createdBy, createdByName, createdAt, updatedAt
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

// Type aliases for medical types
export type medicationstatus = 'active' | 'stopped' | 'held' | 'discontinued';
export type investigationstatus = 'pending' | 'ordered' | 'scheduled' | 'inProgress' | 'completed' | 'cancelled';
export type therapystatus = 'active' | 'completed' | 'cancelled';

// Vital Signs and Chart Types
export interface vitalDataPoint {
  timestamp: string;
  heartRate?: number;
  skinTemperature?: number;
  oxygenSaturation?: number;
  respiratoryRate?: number;
  systolicPressure?: number;
  diastolicPressure?: number;
  ecgReading?: number;
  eegReading?: number;
  bioelectricalImpedance?: number;
  tremorIntensity?: number;
}

export interface medicationEvent {
  timestamp: string;
  medicationName: string;
  dose: string;
  route: string;
}

export type timeframeOption = '1h' | '6h' | '24h' | '7d';

export interface chartConfig {
  vitalType: string;
  color: string;
  unit: string;
  normalRange: { min: number; max: number };
  criticalRange: { min: number; max: number };
}

// Type aliases for backward compatibility
export type labResult = labresult;
export type imagingStudy = imagingstudy;