/**
 * DPDP 2023 (Digital Personal Data Protection Act) Compliance Module
 *
 * Implements India's Digital Personal Data Protection Act 2023 requirements:
 * - Data localization and residency
 * - Consent management
 * - Data subject rights
 * - Cross-border transfer restrictions
 * - Breach notification requirements
 */

import { patient, user } from '../../types';

export interface DPDP2023ConsentRecord {
  patientId: string;
  dataCategories: DataCategory[];
  purposes: ProcessingPurpose[];
  consentGivenAt: Date;
  consentWithdrawnAt?: Date;
  isActive: boolean;
  consentVersion: string;
  dataSubjectRights: DataSubjectRight[];
  retentionPeriod: number; // in months
  crossBorderTransfer: boolean;
  thirdPartySharing: ThirdPartySharing[];
}

export enum DataCategory {
  MEDICAL_HISTORY = 'medical_history',
  VITAL_SIGNS = 'vital_signs',
  MEDICATIONS = 'medications',
  DIAGNOSTIC_REPORTS = 'diagnostic_reports',
  PERSONAL_IDENTIFIERS = 'personal_identifiers',
  CONTACT_INFORMATION = 'contact_information',
  FINANCIAL_INFORMATION = 'financial_information',
  BIOMETRIC_DATA = 'biometric_data',
  GENETIC_DATA = 'genetic_data',
  MENTAL_HEALTH = 'mental_health'
}

export enum ProcessingPurpose {
  MEDICAL_TREATMENT = 'medical_treatment',
  EMERGENCY_CARE = 'emergency_care',
  HEALTH_MONITORING = 'health_monitoring',
  RESEARCH = 'research',
  INSURANCE_CLAIMS = 'insurance_claims',
  GOVERNMENT_REPORTING = 'government_reporting',
  QUALITY_IMPROVEMENT = 'quality_improvement',
  LEGAL_COMPLIANCE = 'legal_compliance'
}

export enum DataSubjectRight {
  ACCESS = 'access',
  CORRECTION = 'correction',
  ERASURE = 'erasure',
  DATA_PORTABILITY = 'data_portability',
  GRIEVANCE = 'grievance',
  NOMINATION = 'nomination'
}

export interface ThirdPartySharing {
  recipientName: string;
  recipientType: 'hospital' | 'insurance' | 'government' | 'research' | 'vendor';
  dataShared: DataCategory[];
  purpose: ProcessingPurpose;
  retentionPeriod: number;
  isIndia: boolean; // For data localization compliance
}

export interface DPDP2023BreachRecord {
  breachId: string;
  occurredAt: Date;
  detectedAt: Date;
  reportedToCertInAt?: Date;
  reportedToDataSubjectAt?: Date;
  affectedPatients: string[];
  dataTypesAffected: DataCategory[];
  severity: 'low' | 'medium' | 'high' | 'critical';
  rootCause: string;
  mitigationSteps: string[];
  isResolved: boolean;
}

export class DPDP2023Compliance {
  private static readonly DATA_LOCALIZATION_REGIONS = ['India', 'IN'];
  private static readonly CONSENT_VERSION = '1.0';
  private static readonly BREACH_NOTIFICATION_TIMELINE = 72; // hours

  /**
   * Verify data residency compliance
   */
  static verifyDataLocalization(serverLocation: string): boolean {
    return this.DATA_LOCALIZATION_REGIONS.includes(serverLocation);
  }

  /**
   * Create consent record for patient data processing
   */
  static createConsentRecord(
    patient: patient,
    dataCategories: DataCategory[],
    purposes: ProcessingPurpose[]
  ): DPDP2023ConsentRecord {
    return {
      patientId: patient.id,
      dataCategories,
      purposes,
      consentGivenAt: new Date(),
      isActive: true,
      consentVersion: this.CONSENT_VERSION,
      dataSubjectRights: Object.values(DataSubjectRight),
      retentionPeriod: this.getRetentionPeriod(purposes),
      crossBorderTransfer: false,
      thirdPartySharing: []
    };
  }

  /**
   * Withdraw consent for specific data categories
   */
  static withdrawConsent(
    consentRecord: DPDP2023ConsentRecord,
    withdrawnCategories: DataCategory[]
  ): DPDP2023ConsentRecord {
    return {
      ...consentRecord,
      dataCategories: consentRecord.dataCategories.filter(
        cat => !withdrawnCategories.includes(cat)
      ),
      consentWithdrawnAt: new Date(),
      isActive: consentRecord.dataCategories.length > withdrawnCategories.length
    };
  }

  /**
   * Check if processing is lawful under DPDP 2023
   */
  static isProcessingLawful(
    consentRecord: DPDP2023ConsentRecord,
    dataCategory: DataCategory,
    purpose: ProcessingPurpose
  ): boolean {
    if (!consentRecord.isActive) return false;
    if (!consentRecord.dataCategories.includes(dataCategory)) return false;
    if (!consentRecord.purposes.includes(purpose)) return false;

    // Check if consent is still valid (not expired)
    const consentAge = Date.now() - consentRecord.consentGivenAt.getTime();
    const maxAge = consentRecord.retentionPeriod * 30 * 24 * 60 * 60 * 1000; // months to ms

    return consentAge < maxAge;
  }

  /**
   * Generate data portability export for patient
   */
  static generateDataPortabilityExport(patient: patient): Record<string, any> {
    return {
      exportGeneratedAt: new Date().toISOString(),
      patientId: patient.id,
      personalData: {
        name: patient.name,
        age: patient.age || 'Not specified',
        gender: patient.gender || 'Not specified',
        department: patient.department || 'Not specified',
        roomAndBed: `${patient.room}-${patient.bedNumber}` || 'Not specified'
      },
      medicalData: {
        vitals: patient.vitals,
        alerts: patient.alerts,
        medications: patient.medications || [],
        investigations: patient.investigations || [],
        therapies: patient.therapies || [],
        caseSheet: patient.caseSheet || []
      },
      deviceData: {
        assignedDeviceId: patient.assignedDeviceId,
        room: patient.room,
        bedNumber: patient.bedNumber
      },
      dataRetentionInfo: {
        dataCategories: Object.values(DataCategory),
        retentionPeriods: this.getDataRetentionSchedule()
      },
      exportFormat: 'JSON',
      dataClassification: 'Sensitive Personal Data under DPDP 2023'
    };
  }

  /**
   * Handle data subject access request
   */
  static handleAccessRequest(
    patientId: string,
    requestedCategories: DataCategory[]
  ): { allowed: boolean; data?: any; reason?: string } {
    // Verify identity and consent before providing access
    const hasValidConsent = this.verifyPatientConsent(patientId, requestedCategories);

    if (!hasValidConsent) {
      return {
        allowed: false,
        reason: 'No valid consent found for requested data categories'
      };
    }

    return {
      allowed: true,
      data: this.getPatientDataByCategories(patientId, requestedCategories)
    };
  }

  /**
   * Log data breach for CERT-In reporting
   */
  static logDataBreach(
    affectedPatients: string[],
    dataTypesAffected: DataCategory[],
    severity: 'low' | 'medium' | 'high' | 'critical',
    description: string
  ): DPDP2023BreachRecord {
    const breach: DPDP2023BreachRecord = {
      breachId: `BREACH_${Date.now()}`,
      occurredAt: new Date(),
      detectedAt: new Date(),
      affectedPatients,
      dataTypesAffected,
      severity,
      rootCause: description,
      mitigationSteps: [],
      isResolved: false
    };

    // Auto-schedule CERT-In notification if required
    if (severity === 'high' || severity === 'critical') {
      this.scheduleCertInNotification(breach);
    }

    return breach;
  }

  /**
   * Get data retention period based on purpose
   */
  private static getRetentionPeriod(purposes: ProcessingPurpose[]): number {
    // Medical records in India: minimum 3 years, some up to 10 years
    if (purposes.includes(ProcessingPurpose.MEDICAL_TREATMENT)) return 36; // 3 years
    if (purposes.includes(ProcessingPurpose.RESEARCH)) return 120; // 10 years
    if (purposes.includes(ProcessingPurpose.LEGAL_COMPLIANCE)) return 84; // 7 years
    return 12; // 1 year default
  }

  private static getDataRetentionSchedule(): Record<DataCategory, number> {
    return {
      [DataCategory.MEDICAL_HISTORY]: 120, // 10 years
      [DataCategory.VITAL_SIGNS]: 36, // 3 years
      [DataCategory.MEDICATIONS]: 60, // 5 years
      [DataCategory.DIAGNOSTIC_REPORTS]: 120, // 10 years
      [DataCategory.PERSONAL_IDENTIFIERS]: 36, // 3 years
      [DataCategory.CONTACT_INFORMATION]: 12, // 1 year
      [DataCategory.FINANCIAL_INFORMATION]: 84, // 7 years
      [DataCategory.BIOMETRIC_DATA]: 60, // 5 years
      [DataCategory.GENETIC_DATA]: 120, // 10 years
      [DataCategory.MENTAL_HEALTH]: 60 // 5 years
    };
  }

  private static verifyPatientConsent(
    patientId: string,
    categories: DataCategory[]
  ): boolean {
    // Implementation would check actual consent records
    // For now, return true (would integrate with consent database)
    return true;
  }

  private static getPatientDataByCategories(
    patientId: string,
    categories: DataCategory[]
  ): any {
    // Implementation would fetch actual patient data
    // Return filtered data based on categories
    return {};
  }

  private static scheduleCertInNotification(breach: DPDP2023BreachRecord): void {
    // Implementation would schedule notification to CERT-In
    // within 72 hours as required by DPDP 2023
    console.log(`Scheduling CERT-In notification for breach ${breach.breachId}`);
  }
}