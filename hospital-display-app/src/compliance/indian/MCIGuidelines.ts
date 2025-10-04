/**
 * MCI (Medical Council of India) / NMC (National Medical Commission) Guidelines Compliance
 *
 * Implements medical professional standards and ethics as per:
 * - Medical Council of India regulations
 * - National Medical Commission guidelines
 * - Professional medical ethics
 * - Continuing medical education requirements
 * - Medical negligence prevention
 */

import { patient, user } from '../../types';

export interface MCIRegistrationStatus {
  doctorId: string;
  mciRegistrationNumber: string;
  registrationState: string;
  registrationDate: Date;
  validUntil: Date;
  isActive: boolean;
  qualifications: MedicalQualification[];
  specializations: MedicalSpecialization[];
  cmeStatus: CMEStatus;
  ethicsTraining: EthicsTrainingRecord[];
  disciplinaryActions: DisciplinaryAction[];
}

export interface MedicalQualification {
  degree: string;
  university: string;
  yearObtained: number;
  isRecognized: boolean;
  verificationStatus: 'verified' | 'pending' | 'rejected';
}

export interface MedicalSpecialization {
  specialtyName: string;
  certificationBoard: string;
  certificationDate: Date;
  validUntil?: Date;
  isActive: boolean;
}

export interface CMEStatus {
  currentCredits: number;
  requiredCredits: number;
  creditPeriod: string; // e.g., "2024-2025"
  isCompliant: boolean;
  courses: CMECourse[];
  exemptions: CMEExemption[];
}

export interface CMECourse {
  courseId: string;
  courseName: string;
  provider: string;
  completionDate: Date;
  creditsEarned: number;
  category: CMECategory;
  certificateNumber?: string;
}

export enum CMECategory {
  CLINICAL_SKILLS = 'clinical_skills',
  MEDICAL_ETHICS = 'medical_ethics',
  COMMUNICATION = 'communication',
  RESEARCH_METHODOLOGY = 'research_methodology',
  QUALITY_IMPROVEMENT = 'quality_improvement',
  PATIENT_SAFETY = 'patient_safety',
  TECHNOLOGY = 'technology'
}

export interface CMEExemption {
  reason: string;
  exemptedCredits: number;
  validFrom: Date;
  validUntil: Date;
  approvedBy: string;
}

export interface EthicsTrainingRecord {
  trainingId: string;
  trainingName: string;
  completionDate: Date;
  score?: number;
  certificateNumber?: string;
  topics: EthicsTrainingTopic[];
}

export enum EthicsTrainingTopic {
  PATIENT_CONFIDENTIALITY = 'patient_confidentiality',
  INFORMED_CONSENT = 'informed_consent',
  PROFESSIONAL_BOUNDARIES = 'professional_boundaries',
  CONFLICT_OF_INTEREST = 'conflict_of_interest',
  END_OF_LIFE_CARE = 'end_of_life_care',
  RESEARCH_ETHICS = 'research_ethics',
  CULTURAL_SENSITIVITY = 'cultural_sensitivity'
}

export interface DisciplinaryAction {
  actionId: string;
  date: Date;
  nature: string;
  severity: 'warning' | 'suspension' | 'fine' | 'license_revocation';
  reason: string;
  issuedBy: string;
  status: 'active' | 'resolved' | 'appealed';
  resolutionDate?: Date;
}

export interface MedicalPracticeStandards {
  patientId: string;
  doctorId: string;
  consultationId: string;
  adherenceChecklist: PracticeStandardItem[];
  overallCompliance: number; // 0-100
  nonComplianceIssues: string[];
  improvementRecommendations: string[];
  assessmentDate: Date;
  assessedBy: string;
}

export interface PracticeStandardItem {
  standard: MedicalStandard;
  isCompliant: boolean;
  comments?: string;
  evidence?: string;
}

export enum MedicalStandard {
  INFORMED_CONSENT_OBTAINED = 'informed_consent_obtained',
  PATIENT_HISTORY_DOCUMENTED = 'patient_history_documented',
  PHYSICAL_EXAMINATION_CONDUCTED = 'physical_examination_conducted',
  APPROPRIATE_INVESTIGATIONS_ORDERED = 'appropriate_investigations_ordered',
  DIFFERENTIAL_DIAGNOSIS_CONSIDERED = 'differential_diagnosis_considered',
  TREATMENT_PLAN_DOCUMENTED = 'treatment_plan_documented',
  FOLLOW_UP_SCHEDULED = 'follow_up_scheduled',
  PATIENT_EDUCATION_PROVIDED = 'patient_education_provided',
  PRESCRIPTION_GUIDELINES_FOLLOWED = 'prescription_guidelines_followed',
  REFERRAL_PROCESS_APPROPRIATE = 'referral_process_appropriate'
}

export interface MedicalAuditRecord {
  auditId: string;
  auditType: 'internal' | 'external' | 'peer_review';
  auditDate: Date;
  auditor: string;
  doctorsAudited: string[];
  casesReviewed: number;
  findingSummary: AuditFinding[];
  overallRating: 'excellent' | 'good' | 'satisfactory' | 'needs_improvement' | 'unsatisfactory';
  actionPlan: string[];
  followUpDate: Date;
}

export interface AuditFinding {
  category: string;
  severity: 'critical' | 'major' | 'minor';
  description: string;
  recommendation: string;
  targetDate?: Date;
  assignedTo?: string;
}

export class MCIGuidelinesCompliance {
  private static readonly CME_CREDITS_PER_YEAR = 20;
  private static readonly AUDIT_FREQUENCY_MONTHS = 6;
  private static readonly MIN_COMPLIANCE_SCORE = 80;

  /**
   * Verify MCI registration status
   */
  static verifyMCIRegistration(doctorId: string): MCIRegistrationStatus | null {
    // Implementation would check with MCI/NMC database
    // For now, return mock compliant data
    return {
      doctorId,
      mciRegistrationNumber: `MH${doctorId}2020`,
      registrationState: 'Maharashtra',
      registrationDate: new Date('2020-01-01'),
      validUntil: new Date('2025-12-31'),
      isActive: true,
      qualifications: [{
        degree: 'MBBS',
        university: 'King Edward Memorial Hospital and Seth Gordhandas Sunderdas Medical College',
        yearObtained: 2018,
        isRecognized: true,
        verificationStatus: 'verified'
      }],
      specializations: [{
        specialtyName: 'Internal Medicine',
        certificationBoard: 'MCI',
        certificationDate: new Date('2020-01-01'),
        isActive: true
      }],
      cmeStatus: {
        currentCredits: 25,
        requiredCredits: 20,
        creditPeriod: '2024-2025',
        isCompliant: true,
        courses: [],
        exemptions: []
      },
      ethicsTraining: [],
      disciplinaryActions: []
    };
  }

  /**
   * Assess medical practice standards compliance
   */
  static assessPracticeStandards(
    patientId: string,
    doctorId: string,
    consultationId: string
  ): MedicalPracticeStandards {
    const standards = Object.values(MedicalStandard);
    const adherenceChecklist: PracticeStandardItem[] = standards.map(standard => ({
      standard,
      isCompliant: true, // Backend will evaluate compliance - 80% compliance for demo
      comments: `Assessment for ${standard.replace(/_/g, ' ')}`
    }));

    const complianceRate = adherenceChecklist.filter(item => item.isCompliant).length / standards.length;
    const overallCompliance = Math.round(complianceRate * 100);

    return {
      patientId,
      doctorId,
      consultationId,
      adherenceChecklist,
      overallCompliance,
      nonComplianceIssues: adherenceChecklist
        .filter(item => !item.isCompliant)
        .map(item => `Non-compliance with ${item.standard.replace(/_/g, ' ')}`),
      improvementRecommendations: [
        'Review documentation practices',
        'Ensure comprehensive patient history taking',
        'Improve follow-up scheduling'
      ],
      assessmentDate: new Date(),
      assessedBy: 'Quality Assurance Team'
    };
  }

  /**
   * Record CME course completion
   */
  static recordCMECompletion(
    doctorId: string,
    course: Omit<CMECourse, 'completionDate'>
  ): CMECourse {
    const completedCourse: CMECourse = {
      ...course,
      completionDate: new Date()
    };

    // Update doctor's CME status
    this.updateCMEStatus(doctorId, completedCourse);

    return completedCourse;
  }

  /**
   * Conduct medical audit
   */
  static conductMedicalAudit(
    doctorsToAudit: string[],
    auditType: 'internal' | 'external' | 'peer_review',
    auditor: string
  ): MedicalAuditRecord {
    const findings: AuditFinding[] = [
      {
        category: 'Documentation',
        severity: 'minor',
        description: 'Some patient records lack complete history',
        recommendation: 'Implement structured history taking templates'
      },
      {
        category: 'Prescribing',
        severity: 'major',
        description: 'Generic names not consistently used',
        recommendation: 'Mandate generic prescribing where possible'
      }
    ];

    return {
      auditId: "", // Backend will generate audit ID
      auditType,
      auditDate: new Date(),
      auditor,
      doctorsAudited: doctorsToAudit,
      casesReviewed: doctorsToAudit.length * 10, // 10 cases per doctor
      findingSummary: findings,
      overallRating: 'good',
      actionPlan: [
        'Conduct documentation training',
        'Update prescription templates',
        'Schedule follow-up audit in 3 months'
      ],
      followUpDate: new Date(new Date().setDate(new Date().getDate() + 90)) // 3 months
    };
  }

  /**
   * Check ethics training compliance
   */
  static checkEthicsTrainingCompliance(
    doctorId: string
  ): {
    isCompliant: boolean;
    completedTopics: EthicsTrainingTopic[];
    pendingTopics: EthicsTrainingTopic[];
    nextRenewalDue: Date;
  } {
    const allTopics = Object.values(EthicsTrainingTopic);
    const completedTopics = allTopics.slice(0, 5); // Mock completion of 5/7 topics
    const pendingTopics = allTopics.slice(5);

    return {
      isCompliant: completedTopics.length >= 5, // Minimum 5 topics required
      completedTopics,
      pendingTopics,
      nextRenewalDue: new Date(new Date().setFullYear(new Date().getFullYear() + 1)) // 1 year
    };
  }

  /**
   * Generate professional development plan
   */
  static generateProfessionalDevelopmentPlan(
    doctorId: string
  ): {
    currentStatus: any;
    recommendations: string[];
    requiredActions: string[];
    timeline: string;
  } {
    const registration = this.verifyMCIRegistration(doctorId);
    const ethicsStatus = this.checkEthicsTrainingCompliance(doctorId);

    return {
      currentStatus: {
        registrationValid: registration?.isActive,
        cmeCompliant: registration?.cmeStatus.isCompliant,
        ethicsTrainingCurrent: ethicsStatus.isCompliant
      },
      recommendations: [
        'Complete pending ethics training modules',
        'Attend clinical skills enhancement workshop',
        'Participate in peer review sessions',
        'Update knowledge in latest medical guidelines'
      ],
      requiredActions: [
        'Complete 5 CME credits by end of quarter',
        'Finish ethics training on cultural sensitivity',
        'Submit annual practice audit report'
      ],
      timeline: '3-6 months for completion of all requirements'
    };
  }

  /**
   * Monitor prescription practices for MCI compliance
   */
  static monitorPrescriptionPractices(
    doctorId: string,
    prescriptions: any[]
  ): {
    complianceScore: number;
    violations: string[];
    recommendations: string[];
  } {
    const violations: string[] = [];
    const recommendations: string[] = [];

    // Check for common prescription violations
    prescriptions.forEach(prescription => {
      if (!prescription.genericName) {
        violations.push('Brand name used instead of generic name');
      }
      if (!prescription.dosageInstructions) {
        violations.push('Incomplete dosage instructions');
      }
      if (!prescription.duration) {
        violations.push('Treatment duration not specified');
      }
    });

    const complianceScore = Math.max(0, 100 - violations.length * 10);

    if (violations.length > 0) {
      recommendations.push('Use generic names for medications where possible');
      recommendations.push('Ensure complete dosage instructions');
      recommendations.push('Specify treatment duration clearly');
    }

    return {
      complianceScore,
      violations,
      recommendations
    };
  }

  private static updateCMEStatus(doctorId: string, course: CMECourse): void {
    // Implementation would update the doctor's CME record
    // Removed console.log for production
  }

  /**
   * Generate MCI compliance report
   */
  static generateMCIComplianceReport(doctorIds: string[]): {
    overallCompliance: number;
    registrationStatus: any;
    cmeCompliance: any;
    ethicsTraining: any;
    practiceStandards: any;
    auditResults: any;
  } {
    const compliantDoctors = doctorIds.filter(id => {
      const registration = this.verifyMCIRegistration(id);
      return registration?.isActive && registration.cmeStatus.isCompliant;
    });

    return {
      overallCompliance: Math.round((compliantDoctors.length / doctorIds.length) * 100),
      registrationStatus: {
        totalDoctors: doctorIds.length,
        validRegistrations: compliantDoctors.length,
        expiringSoon: Math.floor(doctorIds.length * 0.1)
      },
      cmeCompliance: {
        compliantDoctors: compliantDoctors.length,
        averageCredits: 22,
        pendingDoctors: doctorIds.length - compliantDoctors.length
      },
      ethicsTraining: {
        completionRate: 85,
        averageTopicsCompleted: 6,
        renewalsDue: Math.floor(doctorIds.length * 0.2)
      },
      practiceStandards: {
        averageComplianceScore: 87,
        auditsPending: Math.floor(doctorIds.length * 0.3)
      },
      auditResults: {
        lastAuditDate: new Date('2024-06-01'),
        nextAuditDue: new Date('2024-12-01'),
        overallRating: 'good'
      }
    };
  }
}