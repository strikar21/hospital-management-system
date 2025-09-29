/**
 * ClinicalTypes - Clinical decision support and advanced medical type definitions
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Clinical protocols, alerts, and decision support system types
 */

// Clinical decision support types
export interface clinicalalert {
  id: string;
  patientId: string;
  type: 'drugInteraction' | 'allergyWarning' | 'dosageAlert' | 'vitalThreshold' | 'arrhythmia' | 'seizure' | 'tremor' | 'fallRisk' | 'clinicalGuideline';
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  details: string;
  actionRequired: boolean;
  suggestedActions?: string[];
  timestamp: string;
  performedBy?: string;
  completedAt?: string;
  isAcknowledged: boolean;
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

// Type aliases for clinical types
export type clinicalAlert = clinicalalert;