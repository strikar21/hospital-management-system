// services/index.ts - Centralized service exports
import { AuthService } from './AuthService';
import { PatientService } from './PatientService';
import { VitalService } from './VitalService';
import { MedicationService } from './MedicationService';
import { DeviceService } from './DeviceService';
import { InvestigationService } from './InvestigationService';
import { TherapyService } from './TherapyService';
import { ClinicalDecisionSupportService } from './ClinicalDecisionSupport';
import { LabIntegrationService } from './LabIntegration';
import { ImagingService } from './ImagingService';
import { BaseService } from './BaseService';

export { BaseService } from './BaseService';
export { AuthService } from './AuthService';
export { PatientService } from './PatientService';
export { VitalService } from './VitalService';
export { MedicationService } from './MedicationService';
export { DeviceService } from './DeviceService';
export { InvestigationService } from './InvestigationService';
export { TherapyService } from './TherapyService';
export { ClinicalDecisionSupportService } from './ClinicalDecisionSupport';
export { LabIntegrationService } from './LabIntegration';
export { ImagingService } from './ImagingService';

// Legacy compatibility layer - HospitalAPI class that delegates to services

export class HospitalAPI extends BaseService {
  // ================================
  // AUTHENTICATION METHODS
  // ================================
  static authenticateNFC = AuthService.authenticateNFC;
  static authenticateCredentials = AuthService.authenticateCredentials;
  static checkAuthType = AuthService.checkAuthType;
  static logout = AuthService.logout;
  static getCurrentUser = AuthService.getCurrentUser;
  static isAuthenticated = AuthService.isAuthenticated;
  static getUserRole = AuthService.getUserRole;
  static getUserId = AuthService.getUserId;
  static getUserName = AuthService.getUserName;

  // ================================
  // PATIENT METHODS
  // ================================
  static getPatient = PatientService.getPatient;
  static getPatients = PatientService.getPatients;
  static searchPatients = PatientService.searchPatients;
  static getPatientsByStatus = PatientService.getPatientsByStatus;
  static addNoteComment = PatientService.addNoteComment;
  static editNoteComment = PatientService.editNoteComment;
  static deleteNoteComment = PatientService.deleteNoteComment;
  static canEditNote = PatientService.canEditNote;
  static getCaseEntries = PatientService.getCaseEntries;
  static addCaseEntry = PatientService.addCaseEntry;
  static dischargePatient = PatientService.dischargePatient;
  static acknowledgeAlert = PatientService.acknowledgeAlert;

  // ================================
  // VITAL SIGNS METHODS
  // ================================
  static getVitalTimeSeries = VitalService.getVitalTimeSeries;
  static getVitalHistory = VitalService.getVitalHistory;
  static getMedicationCorrelatedVitals = VitalService.getMedicationCorrelatedVitals;
  static updatePatientVitals = VitalService.updatePatientVitals;
  static getECGReadings = VitalService.getECGReadings;
  static switchMonitoringMode = VitalService.switchMonitoringMode;
  static detectRoomProximity = VitalService.detectRoomProximity;
  static getMedicationTimeline = VitalService.getMedicationTimeline;
  static getSystemStatus = VitalService.getSystemStatus;

  // ================================
  // MEDICATION METHODS
  // ================================
  static addMedication = MedicationService.addMedication;
  static updateMedication = MedicationService.updateMedication;
  static discontinueMedication = MedicationService.discontinueMedication;
  static recordMedicationAdministration = MedicationService.recordMedicationAdministration;

  // ================================
  // DEVICE METHODS
  // ================================
  static getFreeDevices = DeviceService.getFreeDevices;
  static getDevicePoolStatus = DeviceService.getDevicePoolStatus;
  static assignDevice = DeviceService.assignDevice;
  static unassignDevice = DeviceService.unassignDevice;
  static reassignDevice = DeviceService.reassignDevice;
  static getPatientDevice = DeviceService.getPatientDevice;
  static getAssignmentHistory = DeviceService.getAssignmentHistory;
  static bulkUnassignPatientDevices = DeviceService.bulkUnassignPatientDevices;
  static logNfcTap = DeviceService.logNfcTap;

  // ================================
  // INVESTIGATION METHODS
  // ================================
  static addInvestigation = InvestigationService.addInvestigation;
  static updateInvestigation = InvestigationService.updateInvestigationStatus;
  static completeInvestigation = InvestigationService.completeInvestigation;

  // ================================
  // THERAPY METHODS
  // ================================
  static addTherapy = TherapyService.addTherapy;
  static updateTherapy = TherapyService.updateTherapy;
  // static addTherapySession = TherapyService.addTherapy; // Use addTherapy instead

  // ================================
  // LEGACY METHOD ALIASES
  // ================================

  // Maintain backward compatibility with existing method names
  static addnotecomment = PatientService.addNoteComment;
  static editnotecomment = PatientService.editNoteComment;
  static deletenotecomment = PatientService.deleteNoteComment;
  static addmedication = MedicationService.addMedication;
  static updatemedication = MedicationService.updateMedication;
  static discontinuemedication = MedicationService.discontinueMedication;
  static recordmedicationAdministration = MedicationService.recordMedicationAdministration;
  static addinvestigation = InvestigationService.addInvestigation;
  static updateinvestigation = InvestigationService.updateInvestigationStatus;
  static completeinvestigation = InvestigationService.completeInvestigation;
  static addtherapy = TherapyService.addTherapy;
  static updatetherapy = TherapyService.updateTherapy;
  // static addtherapysession = TherapyService.addTherapy; // Use addtherapy instead
  static getecgreadings = VitalService.getECGReadings;
  static getvitaltimeseries = VitalService.getVitalTimeSeries;
  static getmedicationCorrelatedVitals = VitalService.getMedicationCorrelatedVitals;
  static getmedicationTimeline = VitalService.getMedicationTimeline;
  static getpatientsbystatus = PatientService.getPatientsByStatus;
  static getpatientdevice = DeviceService.getPatientDevice;

  // ================================
  // WEBSOCKET CONNECTION
  // ================================
  static createWebSocketConnection = BaseService.createWebSocketConnection;
}

// Default export for backward compatibility
export default HospitalAPI;