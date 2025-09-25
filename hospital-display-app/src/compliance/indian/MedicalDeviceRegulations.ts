/**
 * Indian Medical Device Regulations (MDR 2017) Compliance Module
 *
 * Implements compliance with:
 * - Medical Device Rules 2017
 * - Central Drugs Standard Control Organization (CDSCO) requirements
 * - Bureau of Indian Standards (BIS) certification
 * - Medical device import/manufacturing licenses
 * - Post-market surveillance requirements
 * - Adverse event reporting
 */

import { patient, user } from '../../types';

export interface MedicalDeviceRegistration {
  deviceId: string;
  deviceName: string;
  manufacturer: string;
  modelNumber: string;
  serialNumber: string;
  riskClass: DeviceRiskClass;
  registrationNumber: string;
  registrationDate: Date;
  validUntil: Date;
  isActive: boolean;
  cdscoapprovalNumber?: string;
  bisStandardCompliance: BISCompliance[];
  manufacturingLicense?: string;
  importLicense?: string;
  postMarketSurveillance: PostMarketSurveillanceRecord[];
}

export enum DeviceRiskClass {
  CLASS_A = 'class_a', // Low risk - tongue depressor, bandages
  CLASS_B = 'class_b', // Low-moderate risk - thermometers, stethoscopes
  CLASS_C = 'class_c', // Moderate-high risk - ventilators, monitors
  CLASS_D = 'class_d'  // High risk - pacemakers, defibrillators
}

export interface BISCompliance {
  standardNumber: string;
  standardName: string;
  complianceDate: Date;
  certificateNumber: string;
  validUntil: Date;
  testingLab: string;
  isCompliant: boolean;
}

export interface PostMarketSurveillanceRecord {
  recordId: string;
  deviceId: string;
  surveillanceType: SurveillanceType;
  reportDate: Date;
  reportedBy: string;
  findings: string[];
  riskAssessment: RiskAssessment;
  correctiveActions: CorrectiveAction[];
  regulatoryReporting: RegulatoryReporting[];
}

export enum SurveillanceType {
  ROUTINE_MONITORING = 'routine_monitoring',
  ADVERSE_EVENT = 'adverse_event',
  FIELD_SAFETY_NOTICE = 'field_safety_notice',
  RECALL = 'recall',
  PERIODIC_SAFETY_UPDATE = 'periodic_safety_update'
}

export interface RiskAssessment {
  riskLevel: 'low' | 'moderate' | 'high' | 'critical';
  riskFactors: string[];
  likelihood: 'rare' | 'unlikely' | 'possible' | 'likely' | 'certain';
  severity: 'negligible' | 'minor' | 'moderate' | 'major' | 'catastrophic';
  mitigationMeasures: string[];
}

export interface CorrectiveAction {
  actionId: string;
  description: string;
  actionType: 'user_notification' | 'device_modification' | 'recall' | 'training';
  assignedTo: string;
  dueDate: Date;
  status: 'planned' | 'in_progress' | 'completed' | 'overdue';
  effectivenessVerified: boolean;
  verificationDate?: Date;
}

export interface RegulatoryReporting {
  reportId: string;
  authority: RegulatoryAuthority;
  reportType: string;
  submissionDate: Date;
  acknowledgmentReceived: boolean;
  acknowledgmentDate?: Date;
  followUpRequired: boolean;
  nextReportDue?: Date;
}

export enum RegulatoryAuthority {
  CDSCO = 'cdsco',
  STATE_FDA = 'state_fda',
  BIS = 'bis',
  ICMR = 'icmr'
}

export interface DeviceMaintenanceRecord {
  deviceId: string;
  maintenanceId: string;
  maintenanceType: MaintenanceType;
  scheduledDate: Date;
  actualDate?: Date;
  performedBy: string;
  findings: string[];
  partsReplaced: ReplacedPart[];
  calibrationResults: CalibrationResult[];
  nextMaintenanceDue: Date;
  isCompliant: boolean;
  complianceGaps: string[];
}

export enum MaintenanceType {
  PREVENTIVE = 'preventive',
  CORRECTIVE = 'corrective',
  CALIBRATION = 'calibration',
  SAFETY_INSPECTION = 'safety_inspection',
  SOFTWARE_UPDATE = 'software_update'
}

export interface ReplacedPart {
  partName: string;
  partNumber: string;
  oldSerialNumber: string;
  newSerialNumber: string;
  supplier: string;
  replaceDate: Date;
  warrantyUntil: Date;
}

export interface CalibrationResult {
  parameter: string;
  expectedValue: number;
  actualValue: number;
  tolerance: number;
  isWithinTolerance: boolean;
  calibrationStandard: string;
  calibratedBy: string;
}

export interface AdverseEventReport {
  reportId: string;
  deviceId: string;
  patientId?: string;
  reportDate: Date;
  eventDate: Date;
  eventDescription: string;
  eventSeverity: EventSeverity;
  causality: CausalityAssessment;
  reportedBy: string;
  institutionalReview: InstitutionalReview;
  regulatorySubmission: RegulatorySubmission;
  followUpActions: string[];
}

export enum EventSeverity {
  DEATH = 'death',
  LIFE_THREATENING = 'life_threatening',
  SERIOUS_INJURY = 'serious_injury',
  MALFUNCTION = 'malfunction',
  NEAR_MISS = 'near_miss'
}

export enum CausalityAssessment {
  CERTAIN = 'certain',
  PROBABLE = 'probable',
  POSSIBLE = 'possible',
  UNLIKELY = 'unlikely',
  UNRELATED = 'unrelated'
}

export interface InstitutionalReview {
  reviewDate: Date;
  reviewBoard: string;
  findings: string[];
  recommendations: string[];
  deviceWithdrawn: boolean;
  alternativeProvided: boolean;
}

export interface RegulatorySubmission {
  submittedToCDSCO: boolean;
  cdscoapprovalDate?: Date;
  submittedToManufacturer: boolean;
  manufacturerResponse?: string;
  publicNotificationRequired: boolean;
  publicNotificationDate?: Date;
}

export class MedicalDeviceRegulationsCompliance {
  private static readonly AE_REPORTING_TIMELINE_DAYS = 30;
  private static readonly SERIOUS_AE_TIMELINE_DAYS = 15;
  private static readonly CALIBRATION_FREQUENCY_MONTHS = 12;

  /**
   * Register medical device with CDSCO
   */
  static registerMedicalDevice(
    deviceName: string,
    manufacturer: string,
    modelNumber: string,
    riskClass: DeviceRiskClass
  ): MedicalDeviceRegistration {
    const registrationNumber = `MDR${Date.now()}${riskClass.toUpperCase()}`;

    // Registration validity based on risk class
    const validityYears = riskClass === DeviceRiskClass.CLASS_D ? 3 : 5;
    const validUntil = new Date();
    validUntil.setFullYear(validUntil.getFullYear() + validityYears);

    return {
      deviceId: `DEV_${Date.now()}`,
      deviceName,
      manufacturer,
      modelNumber,
      serialNumber: `SN${Date.now()}`,
      riskClass,
      registrationNumber,
      registrationDate: new Date(),
      validUntil,
      isActive: true,
      bisStandardCompliance: this.generateBISCompliance(riskClass),
      postMarketSurveillance: []
    };
  }

  /**
   * Verify device compliance with MDR 2017
   */
  static verifyMDRCompliance(deviceId: string): {
    isCompliant: boolean;
    complianceScore: number;
    nonComplianceIssues: string[];
    recommendations: string[];
  } {
    const device = this.getDeviceRegistration(deviceId);
    const issues: string[] = [];
    const recommendations: string[] = [];

    if (!device) {
      return {
        isCompliant: false,
        complianceScore: 0,
        nonComplianceIssues: ['Device not found in registration database'],
        recommendations: ['Register device with CDSCO']
      };
    }

    // Check registration validity
    if (device.validUntil < new Date()) {
      issues.push('Device registration expired');
      recommendations.push('Renew device registration with CDSCO');
    }

    // Check BIS compliance
    const expiredBIS = device.bisStandardCompliance.filter(bis => bis.validUntil < new Date());
    if (expiredBIS.length > 0) {
      issues.push('BIS certification expired');
      recommendations.push('Renew BIS certification');
    }

    // Check post-market surveillance
    const lastSurveillance = device.postMarketSurveillance
      .sort((a, b) => b.reportDate.getTime() - a.reportDate.getTime())[0];

    if (!lastSurveillance || this.daysBetween(lastSurveillance.reportDate, new Date()) > 90) {
      issues.push('Post-market surveillance overdue');
      recommendations.push('Conduct post-market surveillance review');
    }

    const complianceScore = Math.max(0, 100 - (issues.length * 25));
    const isCompliant = issues.length === 0;

    return {
      isCompliant,
      complianceScore,
      nonComplianceIssues: issues,
      recommendations
    };
  }

  /**
   * Report adverse event
   */
  static reportAdverseEvent(
    deviceId: string,
    eventDescription: string,
    eventSeverity: EventSeverity,
    patientId?: string
  ): AdverseEventReport {
    const reportId = `AE_${Date.now()}`;

    return {
      reportId,
      deviceId,
      patientId,
      reportDate: new Date(),
      eventDate: new Date(),
      eventDescription,
      eventSeverity,
      causality: CausalityAssessment.POSSIBLE,
      reportedBy: 'Hospital Staff',
      institutionalReview: {
        reviewDate: new Date(),
        reviewBoard: 'Device Safety Committee',
        findings: ['Event requires further investigation'],
        recommendations: ['Monitor patient closely', 'Review device operation'],
        deviceWithdrawn: eventSeverity === EventSeverity.DEATH || eventSeverity === EventSeverity.LIFE_THREATENING,
        alternativeProvided: true
      },
      regulatorySubmission: {
        submittedToCDSCO: this.requiresCDSCOReporting(eventSeverity),
        submittedToManufacturer: true,
        publicNotificationRequired: eventSeverity === EventSeverity.DEATH,
        publicNotificationDate: eventSeverity === EventSeverity.DEATH ? new Date() : undefined
      },
      followUpActions: this.generateFollowUpActions(eventSeverity)
    };
  }

  /**
   * Schedule device maintenance
   */
  static scheduleDeviceMaintenance(
    deviceId: string,
    maintenanceType: MaintenanceType
  ): DeviceMaintenanceRecord {
    const scheduledDate = new Date();

    // Schedule based on maintenance type
    switch (maintenanceType) {
      case MaintenanceType.CALIBRATION:
        scheduledDate.setMonth(scheduledDate.getMonth() + this.CALIBRATION_FREQUENCY_MONTHS);
        break;
      case MaintenanceType.PREVENTIVE:
        scheduledDate.setMonth(scheduledDate.getMonth() + 3);
        break;
      case MaintenanceType.SAFETY_INSPECTION:
        scheduledDate.setMonth(scheduledDate.getMonth() + 6);
        break;
      default:
        scheduledDate.setDate(scheduledDate.getDate() + 7);
    }

    const nextMaintenanceDue = new Date(scheduledDate);
    nextMaintenanceDue.setMonth(nextMaintenanceDue.getMonth() +
      (maintenanceType === MaintenanceType.CALIBRATION ? 12 : 3));

    return {
      deviceId,
      maintenanceId: `MAINT_${Date.now()}`,
      maintenanceType,
      scheduledDate,
      performedBy: 'Biomedical Engineer',
      findings: [],
      partsReplaced: [],
      calibrationResults: [],
      nextMaintenanceDue,
      isCompliant: true,
      complianceGaps: []
    };
  }

  /**
   * Generate post-market surveillance report
   */
  static generatePostMarketSurveillance(
    deviceId: string,
    surveillanceType: SurveillanceType
  ): PostMarketSurveillanceRecord {
    const findings = this.generateSurveillanceFindings(surveillanceType);
    const riskAssessment = this.assessRisk(findings);

    return {
      recordId: `PMS_${Date.now()}`,
      deviceId,
      surveillanceType,
      reportDate: new Date(),
      reportedBy: 'Quality Assurance Team',
      findings,
      riskAssessment,
      correctiveActions: this.generateCorrectiveActions(riskAssessment),
      regulatoryReporting: [{
        reportId: `REG_${Date.now()}`,
        authority: RegulatoryAuthority.CDSCO,
        reportType: 'Post Market Surveillance',
        submissionDate: new Date(),
        acknowledgmentReceived: false,
        followUpRequired: riskAssessment.riskLevel === 'high' || riskAssessment.riskLevel === 'critical'
      }]
    };
  }

  /**
   * Check device recall status
   */
  static checkRecallStatus(deviceId: string): {
    isRecalled: boolean;
    recallClass?: 'class_1' | 'class_2' | 'class_3';
    recallReason?: string;
    recallDate?: Date;
    correctiveActions?: string[];
  } {
    // Implementation would check recall database
    // For demo, return no recall
    return {
      isRecalled: false
    };
  }

  private static generateBISCompliance(riskClass: DeviceRiskClass): BISCompliance[] {
    const standards = this.getBISStandardsByRiskClass(riskClass);

    return standards.map(standard => ({
      standardNumber: standard.number,
      standardName: standard.name,
      complianceDate: new Date(),
      certificateNumber: `BIS_${Date.now()}`,
      validUntil: new Date(Date.now() + 3 * 365 * 24 * 60 * 60 * 1000), // 3 years
      testingLab: 'NABL Accredited Lab',
      isCompliant: true
    }));
  }

  private static getBISStandardsByRiskClass(riskClass: DeviceRiskClass): Array<{number: string, name: string}> {
    switch (riskClass) {
      case DeviceRiskClass.CLASS_D:
        return [
          { number: 'IS 13485', name: 'Quality Management Systems' },
          { number: 'IS 14971', name: 'Risk Management' },
          { number: 'IS 62304', name: 'Medical Device Software' }
        ];
      case DeviceRiskClass.CLASS_C:
        return [
          { number: 'IS 13485', name: 'Quality Management Systems' },
          { number: 'IS 14971', name: 'Risk Management' }
        ];
      default:
        return [
          { number: 'IS 13485', name: 'Quality Management Systems' }
        ];
    }
  }

  private static requiresCDSCOReporting(severity: EventSeverity): boolean {
    return [
      EventSeverity.DEATH,
      EventSeverity.LIFE_THREATENING,
      EventSeverity.SERIOUS_INJURY
    ].includes(severity);
  }

  private static generateFollowUpActions(severity: EventSeverity): string[] {
    const baseActions = [
      'Document event thoroughly',
      'Notify manufacturer',
      'Review device protocols'
    ];

    if (severity === EventSeverity.DEATH || severity === EventSeverity.LIFE_THREATENING) {
      return [
        ...baseActions,
        'Immediate CDSCO notification',
        'Consider device withdrawal',
        'Conduct root cause analysis',
        'Issue safety alert'
      ];
    }

    return baseActions;
  }

  private static generateSurveillanceFindings(type: SurveillanceType): string[] {
    const commonFindings = [
      'Device performance within specifications',
      'No adverse events reported',
      'Maintenance schedule up to date'
    ];

    switch (type) {
      case SurveillanceType.ADVERSE_EVENT:
        return ['Minor operational issue identified', 'User training recommended'];
      case SurveillanceType.ROUTINE_MONITORING:
        return commonFindings;
      default:
        return commonFindings;
    }
  }

  private static assessRisk(findings: string[]): RiskAssessment {
    const hasIssues = findings.some(f => f.includes('issue') || f.includes('problem'));

    return {
      riskLevel: hasIssues ? 'moderate' : 'low',
      riskFactors: hasIssues ? ['Operational issues detected'] : [],
      likelihood: hasIssues ? 'possible' : 'unlikely',
      severity: hasIssues ? 'minor' : 'negligible',
      mitigationMeasures: hasIssues ? ['Enhanced monitoring', 'User training'] : ['Continue routine surveillance']
    };
  }

  private static generateCorrectiveActions(risk: RiskAssessment): CorrectiveAction[] {
    if (risk.riskLevel === 'low') return [];

    return [{
      actionId: `CA_${Date.now()}`,
      description: 'Enhanced monitoring and user training',
      actionType: 'user_notification',
      assignedTo: 'Quality Assurance Team',
      dueDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000), // 30 days
      status: 'planned',
      effectivenessVerified: false
    }];
  }

  private static getDeviceRegistration(deviceId: string): MedicalDeviceRegistration | null {
    // Implementation would fetch from device registry
    // Return mock data for demo
    return null;
  }

  private static daysBetween(date1: Date, date2: Date): number {
    return Math.floor((date2.getTime() - date1.getTime()) / (1000 * 60 * 60 * 24));
  }
}