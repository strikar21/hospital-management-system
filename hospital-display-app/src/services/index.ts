// services/index.ts - Centralized service exports
import { AuthService } from './AuthService';
import { PatientService } from './patient';
import { VitalService } from './VitalService';
import { MedicationService } from './MedicationService';
import { DeviceService } from './DeviceService';
import { InvestigationService } from './InvestigationService';
import { TherapyService } from './TherapyService';
// Removed unused services: ClinicalDecisionSupport, LabIntegration, ImagingService
import { BaseService } from './BaseService';

export { BaseService } from './BaseService';
export { AuthService } from './AuthService';
export { PatientService } from './patient';
export { VitalService } from './VitalService';
export { MedicationService } from './MedicationService';
export { DeviceService } from './DeviceService';
export { InvestigationService } from './InvestigationService';
export { TherapyService } from './TherapyService';
// Removed unused service exports

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
  // LEGACY COMPATIBILITY (Deprecated - Use individual services instead)
  // ================================

  // Note: These aliases are deprecated. Use individual service classes for better code organization.
  static addnotecomment = PatientService.addNoteComment;
  static editnotecomment = PatientService.editNoteComment;
  static deletenotecomment = PatientService.deleteNoteComment;
  static getpatientsbystatus = PatientService.getPatientsByStatus;
  static addmedication = MedicationService.addMedication;
  static updatemedication = MedicationService.updateMedication;
  static discontinuemedication = MedicationService.discontinueMedication;
  static addinvestigation = InvestigationService.addInvestigation;
  static updateinvestigation = InvestigationService.updateInvestigationStatus;
  static addtherapy = TherapyService.addTherapy;
  static updatetherapy = TherapyService.updateTherapy;
  static getecgreadings = VitalService.getECGReadings;
  static getvitaltimeseries = VitalService.getVitalTimeSeries;
  static getpatientdevice = DeviceService.getPatientDevice;

  // ================================
  // WEBSOCKET CONNECTION
  // ================================
  static createWebSocketConnection = BaseService.createWebSocketConnection;
}

// Default export for backward compatibility
export default HospitalAPI;