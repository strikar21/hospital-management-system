/**
 * Patient Services - Service Factory and Barrel Exports
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade patient service aggregation with backwards compatibility
 */

import { PatientCRUDService } from './PatientCRUDService';
import { PatientNotesService } from './PatientNotesService';
import { PatientCaseService } from './PatientCaseService';

// Export individual services
export { PatientCRUDService } from './PatientCRUDService';
export { PatientNotesService } from './PatientNotesService';
export { PatientCaseService } from './PatientCaseService';

/**
 * PatientServiceFactory - Backwards compatibility wrapper
 *
 * Provides a unified interface that maintains backwards compatibility
 * with existing code while using the new modular services internally.
 *
 * This allows gradual migration from the monolithic PatientService
 * to the new focused services without breaking existing implementations.
 */
export class PatientService {
  // ================================
  // CRUD OPERATIONS
  // ================================

  static async getPatient(patientId: string) {
    return PatientCRUDService.getPatient(patientId);
  }

  static async getPatients(ward?: string, department?: string, showAllDepts?: boolean) {
    return PatientCRUDService.getPatients(ward, department, showAllDepts);
  }

  static async searchPatients(query: string) {
    return PatientCRUDService.searchPatients(query);
  }

  static async getPatientsByStatus(status: 'stable' | 'critical' | 'emergency') {
    return PatientCRUDService.getPatientsByStatus(status);
  }

  static async dischargePatient(patientId: string, staffId: string) {
    return PatientCRUDService.dischargePatient(patientId, staffId);
  }

  // ================================
  // NOTES OPERATIONS
  // ================================

  static async addNoteComment(patientId: string, content: string, userId: string, username?: string, userrole?: string) {
    return PatientNotesService.addNoteComment(patientId, content, userId, username, userrole);
  }

  static async editNoteComment(patientId: string, noteId: string, newContent: string, userId: string) {
    return PatientNotesService.editNoteComment(patientId, noteId, newContent, userId);
  }

  static async deleteNoteComment(patientId: string, noteId: string, userId: string) {
    return PatientNotesService.deleteNoteComment(patientId, noteId, userId);
  }

  static canEditNote(note: any, userId: string) {
    return PatientNotesService.canEditNote(note, userId);
  }

  static canEditItem(timestamp: string) {
    return PatientNotesService.canEditItem(timestamp);
  }

  // ================================
  // CASE MANAGEMENT
  // ================================

  static async getCaseEntries(patientId: string) {
    return PatientCaseService.getCaseEntries(patientId);
  }

  static async addCaseEntry(patientId: string, entryData: any, userId: string) {
    return PatientCaseService.addCaseEntry(patientId, entryData, userId);
  }

  static async acknowledgeAlert(patientId: string, alertId: string, userId: string) {
    return PatientCaseService.acknowledgeAlert(patientId, alertId, userId);
  }

  // ================================
  // VITAL MONITORING
  // ================================

  static async toggleECGMode(patientId: string, isECGMode: boolean, userId?: string) {
    const { VitalService } = await import('../VitalService');
    return VitalService.switchMonitoringMode(patientId, isECGMode, userId || 'system');
  }
}

// Default export for backwards compatibility
export default PatientService;