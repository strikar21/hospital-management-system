/**
 * Indian Healthcare Compliance Audit Logging System
 *
 * Centralized audit logging for all Indian healthcare compliance requirements:
 * - DPDP 2023 compliance events
 * - Clinical Establishments Act activities
 * - MCI/NMC professional standards
 * - Medical Device Regulations
 * - CERT-In security incidents
 * - NABH accreditation activities
 */

import { patient, user } from '../../types';
import { DataCategory, ProcessingPurpose } from './DPDP2023';
import { MedicalRecordType, PatientRight } from './ClinicalEstablishmentsAct';
import { MedicalStandard } from './MCIGuidelines';
import { DeviceRiskClass, EventSeverity } from './MedicalDeviceRegulations';

export interface ComplianceAuditLog {
  logId: string;
  timestamp: Date;
  complianceFramework: ComplianceFramework;
  eventType: ComplianceEventType;
  severity: AuditSeverity;
  userId?: string;
  patientId?: string;
  deviceId?: string;
  description: string;
  details: Record<string, any>;
  ipAddress?: string;
  userAgent?: string;
  sessionId?: string;
  location?: string;
  outcome: AuditOutcome;
  riskLevel: RiskLevel;
  followUpRequired: boolean;
  followUpDueDate?: Date;
  regulatoryReportingRequired: boolean;
  reportingAuthorities: RegulatoryAuthority[];
  evidenceAttached: boolean;
  evidenceFileIds: string[];
  reviewStatus: ReviewStatus;
  reviewedBy?: string;
  reviewedAt?: Date;
  reviewComments?: string;
}

export enum ComplianceFramework {
  DPDP_2023 = 'dpdp_2023',
  CLINICAL_ESTABLISHMENTS_ACT = 'clinical_establishments_act',
  MCI_GUIDELINES = 'mci_guidelines',
  MEDICAL_DEVICE_REGULATIONS = 'medical_device_regulations',
  CERT_IN_SECURITY = 'cert_in_security',
  NABH_ACCREDITATION = 'nabh_accreditation',
  AYUSH_COMPLIANCE = 'ayush_compliance',
  POCSO_ACT = 'pocso_act',
  MENTAL_HEALTHCARE_ACT = 'mental_healthcare_act',
  CONSUMER_PROTECTION_ACT = 'consumer_protection_act'
}

export enum ComplianceEventType {
  // DPDP 2023 Events
  CONSENT_GRANTED = 'consent_granted',
  CONSENT_WITHDRAWN = 'consent_withdrawn',
  DATA_ACCESS_REQUEST = 'data_access_request',
  DATA_PORTABILITY_REQUEST = 'data_portability_request',
  DATA_BREACH_DETECTED = 'data_breach_detected',
  DATA_CROSS_BORDER_TRANSFER = 'data_cross_border_transfer',

  // Clinical Establishments Act Events
  PATIENT_RIGHTS_COMMUNICATED = 'patient_rights_communicated',
  MEDICAL_RECORD_CREATED = 'medical_record_created',
  MEDICAL_RECORD_ACCESSED = 'medical_record_accessed',
  MEDICAL_RECORD_SEALED = 'medical_record_sealed',
  FACILITY_INSPECTION = 'facility_inspection',
  STAFF_QUALIFICATION_VERIFIED = 'staff_qualification_verified',

  // MCI Guidelines Events
  CME_COMPLETED = 'cme_completed',
  ETHICS_TRAINING_COMPLETED = 'ethics_training_completed',
  MEDICAL_AUDIT_CONDUCTED = 'medical_audit_conducted',
  PRESCRIPTION_REVIEW = 'prescription_review',
  PRACTICE_STANDARDS_ASSESSED = 'practice_standards_assessed',

  // Medical Device Events
  DEVICE_REGISTERED = 'device_registered',
  ADVERSE_EVENT_REPORTED = 'adverse_event_reported',
  DEVICE_MAINTENANCE = 'device_maintenance',
  POST_MARKET_SURVEILLANCE = 'post_market_surveillance',
  DEVICE_RECALL = 'device_recall',

  // Security Events
  UNAUTHORIZED_ACCESS_ATTEMPT = 'unauthorized_access_attempt',
  DATA_ENCRYPTION_FAILURE = 'data_encryption_failure',
  SYSTEM_INTRUSION_DETECTED = 'system_intrusion_detected',
  MALWARE_DETECTED = 'malware_detected',

  // General Compliance Events
  POLICY_VIOLATION = 'policy_violation',
  TRAINING_COMPLETED = 'training_completed',
  COMPLIANCE_ASSESSMENT = 'compliance_assessment',
  REGULATORY_REPORTING = 'regulatory_reporting'
}

export enum AuditSeverity {
  CRITICAL = 'critical',
  HIGH = 'high',
  MEDIUM = 'medium',
  LOW = 'low',
  INFORMATIONAL = 'informational'
}

export enum AuditOutcome {
  SUCCESS = 'success',
  FAILURE = 'failure',
  PARTIAL_SUCCESS = 'partial_success',
  PREVENTED = 'prevented',
  ESCALATED = 'escalated'
}

export enum RiskLevel {
  CRITICAL = 'critical',
  HIGH = 'high',
  MEDIUM = 'medium',
  LOW = 'low',
  NEGLIGIBLE = 'negligible'
}

export enum RegulatoryAuthority {
  CDSCO = 'cdsco',
  MCI_NMC = 'mci_nmc',
  STATE_FDA = 'state_fda',
  CERT_IN = 'cert_in',
  NABH = 'nabh',
  MINISTRY_OF_HEALTH = 'ministry_of_health',
  STATE_HEALTH_DEPT = 'state_health_dept',
  POLICE = 'police',
  CONSUMER_FORUM = 'consumer_forum'
}

export enum ReviewStatus {
  PENDING = 'pending',
  IN_REVIEW = 'in_review',
  REVIEWED = 'reviewed',
  ESCALATED = 'escalated',
  CLOSED = 'closed'
}

export interface ComplianceMetrics {
  period: string;
  totalEvents: number;
  criticalEvents: number;
  highRiskEvents: number;
  complianceViolations: number;
  regulatoryReports: number;
  frameworkMetrics: Record<ComplianceFramework, FrameworkMetric>;
  trendAnalysis: TrendAnalysis;
  actionItemsGenerated: number;
  actionItemsCompleted: number;
}

export interface FrameworkMetric {
  framework: ComplianceFramework;
  totalEvents: number;
  violations: number;
  complianceRate: number;
  averageResolutionTime: number;
  pendingActions: number;
}

export interface TrendAnalysis {
  complianceScore: number;
  trendDirection: 'improving' | 'stable' | 'declining';
  keyRisks: string[];
  recommendedActions: string[];
  benchmarkComparison: number;
}

export interface RegulatoryReport {
  reportId: string;
  reportType: string;
  framework: ComplianceFramework;
  authority: RegulatoryAuthority;
  generatedAt: Date;
  reportingPeriod: string;
  summary: string;
  eventsIncluded: string[];
  complianceStatus: 'compliant' | 'non_compliant' | 'under_review';
  actionPlan: string[];
  nextReportDue: Date;
  submissionStatus: 'draft' | 'submitted' | 'acknowledged' | 'under_review';
  submissionReference?: string;
}

export class ComplianceAuditLogger {
  private static instance: ComplianceAuditLogger;
  private logs: ComplianceAuditLog[] = [];

  public static getInstance(): ComplianceAuditLogger {
    if (!ComplianceAuditLogger.instance) {
      ComplianceAuditLogger.instance = new ComplianceAuditLogger();
    }
    return ComplianceAuditLogger.instance;
  }

  /**
   * Log DPDP 2023 compliance event
   */
  static logDPDPEvent(
    eventType: ComplianceEventType,
    patientId: string,
    dataCategories: DataCategory[],
    purpose: ProcessingPurpose,
    userId?: string,
    additionalDetails?: Record<string, any>
  ): void {
    const severity = this.determineDPDPSeverity(eventType);
    const riskLevel = this.determineRiskLevel(eventType, severity);

    const log: ComplianceAuditLog = {
      logId: "", // Backend will generate log ID
      timestamp: new Date(),
      complianceFramework: ComplianceFramework.DPDP_2023,
      eventType,
      severity,
      userId,
      patientId,
      description: this.getEventDescription(eventType),
      details: {
        dataCategories,
        purpose,
        ...additionalDetails
      },
      outcome: AuditOutcome.SUCCESS,
      riskLevel,
      followUpRequired: riskLevel === RiskLevel.HIGH || riskLevel === RiskLevel.CRITICAL,
      followUpDueDate: this.calculateFollowUpDate(riskLevel),
      regulatoryReportingRequired: this.requiresRegulatoryReporting(eventType, severity),
      reportingAuthorities: this.getReportingAuthorities(ComplianceFramework.DPDP_2023, eventType),
      evidenceAttached: false,
      evidenceFileIds: [],
      reviewStatus: ReviewStatus.PENDING
    };

    this.getInstance().addLog(log);
  }

  /**
   * Log Clinical Establishments Act event
   */
  static logClinicalEstablishmentEvent(
    eventType: ComplianceEventType,
    recordType: MedicalRecordType,
    patientId?: string,
    userId?: string,
    additionalDetails?: Record<string, any>
  ): void {
    const severity = this.determineClinicalSeverity(eventType);
    const riskLevel = this.determineRiskLevel(eventType, severity);

    const log: ComplianceAuditLog = {
      logId: "", // Backend will generate log ID
      timestamp: new Date(),
      complianceFramework: ComplianceFramework.CLINICAL_ESTABLISHMENTS_ACT,
      eventType,
      severity,
      userId,
      patientId,
      description: this.getEventDescription(eventType),
      details: {
        recordType,
        ...additionalDetails
      },
      outcome: AuditOutcome.SUCCESS,
      riskLevel,
      followUpRequired: riskLevel === RiskLevel.HIGH || riskLevel === RiskLevel.CRITICAL,
      followUpDueDate: this.calculateFollowUpDate(riskLevel),
      regulatoryReportingRequired: this.requiresRegulatoryReporting(eventType, severity),
      reportingAuthorities: this.getReportingAuthorities(ComplianceFramework.CLINICAL_ESTABLISHMENTS_ACT, eventType),
      evidenceAttached: false,
      evidenceFileIds: [],
      reviewStatus: ReviewStatus.PENDING
    };

    this.getInstance().addLog(log);
  }

  /**
   * Log MCI Guidelines compliance event
   */
  static logMCIEvent(
    eventType: ComplianceEventType,
    doctorId: string,
    standard?: MedicalStandard,
    additionalDetails?: Record<string, any>
  ): void {
    const severity = this.determineMCISeverity(eventType);
    const riskLevel = this.determineRiskLevel(eventType, severity);

    const log: ComplianceAuditLog = {
      logId: "", // Backend will generate log ID
      timestamp: new Date(),
      complianceFramework: ComplianceFramework.MCI_GUIDELINES,
      eventType,
      severity,
      userId: doctorId,
      description: this.getEventDescription(eventType),
      details: {
        standard,
        ...additionalDetails
      },
      outcome: AuditOutcome.SUCCESS,
      riskLevel,
      followUpRequired: riskLevel === RiskLevel.HIGH || riskLevel === RiskLevel.CRITICAL,
      followUpDueDate: this.calculateFollowUpDate(riskLevel),
      regulatoryReportingRequired: this.requiresRegulatoryReporting(eventType, severity),
      reportingAuthorities: this.getReportingAuthorities(ComplianceFramework.MCI_GUIDELINES, eventType),
      evidenceAttached: false,
      evidenceFileIds: [],
      reviewStatus: ReviewStatus.PENDING
    };

    this.getInstance().addLog(log);
  }

  /**
   * Log Medical Device Regulations event
   */
  static logMedicalDeviceEvent(
    eventType: ComplianceEventType,
    deviceId: string,
    riskClass: DeviceRiskClass,
    eventSeverity?: EventSeverity,
    additionalDetails?: Record<string, any>
  ): void {
    const severity = this.determineMDRSeverity(eventType, eventSeverity);
    const riskLevel = this.determineRiskLevel(eventType, severity);

    const log: ComplianceAuditLog = {
      logId: "", // Backend will generate log ID
      timestamp: new Date(),
      complianceFramework: ComplianceFramework.MEDICAL_DEVICE_REGULATIONS,
      eventType,
      severity,
      deviceId,
      description: this.getEventDescription(eventType),
      details: {
        riskClass,
        eventSeverity,
        ...additionalDetails
      },
      outcome: AuditOutcome.SUCCESS,
      riskLevel,
      followUpRequired: riskLevel === RiskLevel.HIGH || riskLevel === RiskLevel.CRITICAL,
      followUpDueDate: this.calculateFollowUpDate(riskLevel),
      regulatoryReportingRequired: this.requiresRegulatoryReporting(eventType, severity),
      reportingAuthorities: this.getReportingAuthorities(ComplianceFramework.MEDICAL_DEVICE_REGULATIONS, eventType),
      evidenceAttached: false,
      evidenceFileIds: [],
      reviewStatus: ReviewStatus.PENDING
    };

    this.getInstance().addLog(log);
  }

  /**
   * Generate compliance metrics report
   */
  static generateComplianceMetrics(
    startDate: Date,
    endDate: Date
  ): ComplianceMetrics {
    const logs = this.getInstance().getLogsByDateRange(startDate, endDate);

    const criticalEvents = logs.filter(log => log.severity === AuditSeverity.CRITICAL).length;
    const highRiskEvents = logs.filter(log => log.riskLevel === RiskLevel.HIGH || log.riskLevel === RiskLevel.CRITICAL).length;
    const complianceViolations = logs.filter(log => log.outcome === AuditOutcome.FAILURE).length;
    const regulatoryReports = logs.filter(log => log.regulatoryReportingRequired).length;

    const frameworkMetrics = this.calculateFrameworkMetrics(logs);
    const trendAnalysis = this.analyzeTrends(logs);

    return {
      period: `${startDate.toISOString().split('T')[0]} to ${endDate.toISOString().split('T')[0]}`,
      totalEvents: logs.length,
      criticalEvents,
      highRiskEvents,
      complianceViolations,
      regulatoryReports,
      frameworkMetrics,
      trendAnalysis,
      actionItemsGenerated: logs.filter(log => log.followUpRequired).length,
      actionItemsCompleted: logs.filter(log => log.reviewStatus === ReviewStatus.CLOSED).length
    };
  }

  /**
   * Generate regulatory report
   */
  static generateRegulatoryReport(
    framework: ComplianceFramework,
    authority: RegulatoryAuthority,
    startDate: Date,
    endDate: Date
  ): RegulatoryReport {
    const relevantLogs = this.getInstance().logs.filter(log =>
      log.complianceFramework === framework &&
      log.timestamp >= startDate &&
      log.timestamp <= endDate &&
      log.reportingAuthorities.includes(authority)
    );

    const complianceRate = relevantLogs.length > 0 ?
      (relevantLogs.filter(log => log.outcome === AuditOutcome.SUCCESS).length / relevantLogs.length) * 100 : 100;

    const complianceStatus = complianceRate >= 95 ? 'compliant' :
      complianceRate >= 80 ? 'under_review' : 'non_compliant';

    return {
      reportId: "", // Backend will generate report ID
      reportType: `${framework.replace(/_/g, ' ').toUpperCase()} Compliance Report`,
      framework,
      authority,
      generatedAt: new Date(),
      reportingPeriod: `${startDate.toISOString().split('T')[0]} to ${endDate.toISOString().split('T')[0]}`,
      summary: `Compliance assessment for ${framework.replace(/_/g, ' ')} covering ${relevantLogs.length} events with ${complianceRate.toFixed(1)}% compliance rate`,
      eventsIncluded: relevantLogs.map(log => log.logId),
      complianceStatus,
      actionPlan: this.generateActionPlan(relevantLogs),
      nextReportDue: new Date(endDate.getTime() + 90 * 24 * 60 * 60 * 1000), // 90 days
      submissionStatus: 'draft'
    };
  }

  private addLog(log: ComplianceAuditLog): void {
    this.logs.push(log);

    // Auto-escalate critical events
    if (log.severity === AuditSeverity.CRITICAL) {
      this.escalateLog(log);
    }

    // Removed console.log for production
  }

  private getLogsByDateRange(startDate: Date, endDate: Date): ComplianceAuditLog[] {
    return this.logs.filter(log =>
      log.timestamp >= startDate && log.timestamp <= endDate
    );
  }

  private escalateLog(log: ComplianceAuditLog): void {
    log.reviewStatus = ReviewStatus.ESCALATED;
    // Implementation would notify compliance officers
    // Removed console.log for production
  }

  private static determineDPDPSeverity(eventType: ComplianceEventType): AuditSeverity {
    switch (eventType) {
      case ComplianceEventType.DATA_BREACH_DETECTED:
        return AuditSeverity.CRITICAL;
      case ComplianceEventType.CONSENT_WITHDRAWN:
      case ComplianceEventType.DATA_CROSS_BORDER_TRANSFER:
        return AuditSeverity.HIGH;
      default:
        return AuditSeverity.MEDIUM;
    }
  }

  private static determineClinicalSeverity(eventType: ComplianceEventType): AuditSeverity {
    switch (eventType) {
      case ComplianceEventType.FACILITY_INSPECTION:
        return AuditSeverity.HIGH;
      case ComplianceEventType.MEDICAL_RECORD_SEALED:
        return AuditSeverity.MEDIUM;
      default:
        return AuditSeverity.LOW;
    }
  }

  private static determineMCISeverity(eventType: ComplianceEventType): AuditSeverity {
    switch (eventType) {
      case ComplianceEventType.MEDICAL_AUDIT_CONDUCTED:
        return AuditSeverity.HIGH;
      case ComplianceEventType.PRACTICE_STANDARDS_ASSESSED:
        return AuditSeverity.MEDIUM;
      default:
        return AuditSeverity.LOW;
    }
  }

  private static determineMDRSeverity(eventType: ComplianceEventType, eventSeverity?: EventSeverity): AuditSeverity {
    if (eventType === ComplianceEventType.ADVERSE_EVENT_REPORTED) {
      switch (eventSeverity) {
        case EventSeverity.DEATH:
        case EventSeverity.LIFE_THREATENING:
          return AuditSeverity.CRITICAL;
        case EventSeverity.SERIOUS_INJURY:
          return AuditSeverity.HIGH;
        default:
          return AuditSeverity.MEDIUM;
      }
    }
    return AuditSeverity.MEDIUM;
  }

  private static determineRiskLevel(eventType: ComplianceEventType, severity: AuditSeverity): RiskLevel {
    if (severity === AuditSeverity.CRITICAL) return RiskLevel.CRITICAL;
    if (severity === AuditSeverity.HIGH) return RiskLevel.HIGH;
    return RiskLevel.MEDIUM;
  }

  private static calculateFollowUpDate(riskLevel: RiskLevel): Date | undefined {
    if (riskLevel === RiskLevel.CRITICAL) {
      return new Date(new Date().setDate(new Date().getDate() + 1)); // 24 hours
    }
    if (riskLevel === RiskLevel.HIGH) {
      return new Date(new Date().setDate(new Date().getDate() + 7)); // 7 days
    }
    return undefined;
  }

  private static requiresRegulatoryReporting(eventType: ComplianceEventType, severity: AuditSeverity): boolean {
    return severity === AuditSeverity.CRITICAL ||
      [ComplianceEventType.DATA_BREACH_DETECTED, ComplianceEventType.ADVERSE_EVENT_REPORTED].includes(eventType);
  }

  private static getReportingAuthorities(framework: ComplianceFramework, eventType: ComplianceEventType): RegulatoryAuthority[] {
    switch (framework) {
      case ComplianceFramework.DPDP_2023:
        return [RegulatoryAuthority.CERT_IN];
      case ComplianceFramework.CLINICAL_ESTABLISHMENTS_ACT:
        return [RegulatoryAuthority.STATE_HEALTH_DEPT];
      case ComplianceFramework.MCI_GUIDELINES:
        return [RegulatoryAuthority.MCI_NMC];
      case ComplianceFramework.MEDICAL_DEVICE_REGULATIONS:
        return [RegulatoryAuthority.CDSCO];
      default:
        return [];
    }
  }

  private static getEventDescription(eventType: ComplianceEventType): string {
    return eventType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }

  private static calculateFrameworkMetrics(logs: ComplianceAuditLog[]): Record<ComplianceFramework, FrameworkMetric> {
    const frameworks = Object.values(ComplianceFramework);
    const metrics: Record<ComplianceFramework, FrameworkMetric> = {} as any;

    frameworks.forEach(framework => {
      const frameworkLogs = logs.filter(log => log.complianceFramework === framework);
      const violations = frameworkLogs.filter(log => log.outcome === AuditOutcome.FAILURE).length;

      metrics[framework] = {
        framework,
        totalEvents: frameworkLogs.length,
        violations,
        complianceRate: frameworkLogs.length > 0 ? ((frameworkLogs.length - violations) / frameworkLogs.length) * 100 : 100,
        averageResolutionTime: 24, // Mock average resolution time in hours
        pendingActions: frameworkLogs.filter(log => log.followUpRequired && log.reviewStatus === ReviewStatus.PENDING).length
      };
    });

    return metrics;
  }

  private static analyzeTrends(logs: ComplianceAuditLog[]): TrendAnalysis {
    const complianceRate = logs.length > 0 ?
      (logs.filter(log => log.outcome === AuditOutcome.SUCCESS).length / logs.length) * 100 : 100;

    return {
      complianceScore: Math.round(complianceRate),
      trendDirection: complianceRate >= 90 ? 'improving' : complianceRate >= 70 ? 'stable' : 'declining',
      keyRisks: [
        'Data breach vulnerabilities',
        'Medical device maintenance delays',
        'Documentation gaps'
      ],
      recommendedActions: [
        'Enhance staff training programs',
        'Improve audit frequency',
        'Strengthen preventive measures'
      ],
      benchmarkComparison: 85 // Industry benchmark comparison
    };
  }

  private static generateActionPlan(logs: ComplianceAuditLog[]): string[] {
    const actions = new Set<string>();

    logs.forEach(log => {
      if (log.riskLevel === RiskLevel.HIGH || log.riskLevel === RiskLevel.CRITICAL) {
        actions.add('Immediate risk mitigation required');
      }
      if (log.outcome === AuditOutcome.FAILURE) {
        actions.add('Root cause analysis and corrective action');
      }
      if (log.regulatoryReportingRequired) {
        actions.add('Submit regulatory notifications');
      }
    });

    return Array.from(actions);
  }
}