/**
 * InvestigationService - Medical investigations and lab tests (V2 - Refactored)
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data
 *
 * Extends BaseMedicalRecordService for generic CRUD operations.
 * Adds investigation-specific field mapping and result formatting.
 *
 * @module InvestigationService
 * @since 2.0.0
 */

import { investigation } from '../types';
import { BaseMedicalRecordService, MedicalRecordConfig } from './base/BaseMedicalRecordService';

export class InvestigationService extends BaseMedicalRecordService<investigation> {

  // ================================
  // CONFIGURATION
  // ================================

  protected getConfig(): MedicalRecordConfig {
    return {
      recordType: 'investigations',
      recordTypeSingular: 'investigation',
      recordTypePlural: 'investigations'
    };
  }

  // ================================
  // TYPE-SPECIFIC PAYLOAD TRANSFORMATION
  // ================================

  /**
   * Transform investigation payload with field mapping and capitalization
   * Maps frontend field names to backend validator expectations
   */
  protected transformAddPayload(investigation: any, userId: string): any {
    // Helper to capitalize first letter
    const capitalize = (str: string): string => {
      return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
    };

    // Capitalize testType and priority for backend validation
    const testType = capitalize(investigation.type);  // 'lab' → 'Lab'
    const priority = capitalize(investigation.priority);  // 'routine' → 'Routine'
    const urgency = investigation.urgency ? capitalize(investigation.urgency) : undefined;  // 'urgent' → 'Urgent'

    return {
      testName: investigation.name,        // Backend expects "testName" not "name"
      testType: testType,                  // Backend expects "testType" capitalized: 'Lab', 'Radiology', etc.
      priority: priority,                  // Backend expects capitalized: 'Routine', 'High', 'Critical'
      urgency: urgency,                    // Backend expects capitalized: 'Routine', 'Urgent', 'STAT'
      notes: investigation.notes,
      prescribedBy: userId,
      status: 'pending'  // Backend validator accepts: pending, scheduled, in-progress, completed, cancelled
    };
  }

  // ================================
  // STATIC WRAPPER METHODS (Backward Compatibility)
  // ================================

  /**
   * Get all investigations for a patient
   * @param patientId - Patient ID
   * @returns Promise resolving to array of investigations
   */
  static async getPatientInvestigations(patientId: string): Promise<investigation[]> {
    const instance = new InvestigationService();
    return await instance.getPatientRecords(patientId);
  }

  /**
   * Get pending investigations for a patient
   * @param patientId - Patient ID
   * @returns Promise resolving to array of pending investigations
   */
  static async getPendingInvestigations(patientId: string): Promise<investigation[]> {
    return new InvestigationService().getActiveRecords(patientId, 'pending');
  }

  /**
   * Add new investigation
   * @param patientId - Patient ID
   * @param investigation - Investigation data (excluding backend-generated fields)
   * @param userId - User ID
   * @returns Promise resolving to atomic response
   */
  static async addInvestigation(
    patientId: string,
    investigation: Omit<investigation, 'id' | 'createdAt' | 'updatedAt' | 'createdBy' | 'createdByName'>,
    userId: string
  ): Promise<any> {
    return new InvestigationService().addRecord(patientId, investigation, userId);
  }

  /**
   * Update investigation status
   * @param investigationId - Investigation ID
   * @param status - New status
   * @param userId - User ID
   * @returns Promise resolving to success boolean
   */
  static async updateInvestigationStatus(investigationId: string, status: string, userId: string): Promise<boolean> {
    return new InvestigationService().updateRecordStatus(investigationId, status, userId);
  }

  /**
   * Complete investigation (legacy method)
   * @param investigationId - Investigation ID
   * @param results - Investigation results
   * @param userId - User ID
   * @returns Promise resolving to success boolean
   */
  static async completeInvestigation(investigationId: string, results: any, userId: string): Promise<boolean> {
    try {
      await new InvestigationService().fetchFromBackend(`/investigations/${investigationId}/complete`, {
        method: 'POST',
        body: JSON.stringify({
          results,
          completedBy: userId,
          completedAt: new Date().toISOString()
        })
      });

      return true;
    } catch (error) {
      return false;
    }
  }

  /**
   * Update investigation results
   * @param investigationId - Investigation ID
   * @param results - Investigation results
   * @param userId - User ID
   * @returns Promise resolving to success boolean
   */
  static async updateInvestigationResults(investigationId: string, results: any, userId: string): Promise<boolean> {
    try {
      await new InvestigationService().fetchFromBackend(`/investigations/${investigationId}/results`, {
        method: 'PUT',
        body: JSON.stringify({
          results,
          modifiedBy: userId,
          modifiedAt: new Date().toISOString()
        })
      });

      return true;
    } catch (error) {
      return false;
    }
  }

  // ================================
  // ATOMIC OPERATIONS (Investigation-Specific)
  // ================================

  /**
   * Complete investigation atomically with automatic case entry creation
   * @param patientId - Patient ID
   * @param investigationId - Investigation ID
   * @param results - Investigation results/findings
   * @param userId - User ID completing the investigation
   * @returns Promise resolving to atomic response with medicalRecord and caseEntry
   */
  static async completeInvestigationAtomic(
    patientId: string,
    investigationId: string,
    results: string,
    userId: string
  ): Promise<any> {
    try {
      const response = await new InvestigationService().fetchFromBackend(
        `/atomic/patients/${patientId}/investigations/${investigationId}/complete`,
        {
          method: 'POST',
          body: JSON.stringify({
            investigationId: investigationId,
            results: results,
            completedBy: userId
          })
        }
      );
      return response;
    } catch (error) {
      throw error;
    }
  }

  // ================================
  // TYPE & HISTORY METHODS (Delegate to Base)
  // ================================

  /**
   * Get available investigation types
   * @returns Promise resolving to array of investigation types
   */
  static async getInvestigationTypes(): Promise<any[]> {
    return new InvestigationService().getRecordTypes();
  }

  /**
   * Get investigation history
   * @param patientId - Patient ID
   * @param investigationId - Optional specific investigation ID
   * @returns Promise resolving to investigation history
   */
  static async getInvestigationHistory(patientId: string, investigationId?: string): Promise<any[]> {
    return new InvestigationService().getRecordHistory(patientId, investigationId);
  }

  /**
   * Get investigations by status
   * @param patientId - Patient ID
   * @param status - Status to filter by
   * @returns Promise resolving to filtered investigations
   */
  static async getInvestigationsByStatus(patientId: string, status: string): Promise<investigation[]> {
    return new InvestigationService().getRecordsByStatus(patientId, status);
  }

  /**
   * Get investigation timeline
   * @param patientId - Patient ID
   * @param hoursBack - Hours to look back (default: 48)
   * @returns Promise resolving to investigation timeline
   */
  static async getInvestigationTimeline(patientId: string, hoursBack: number = 48): Promise<investigation[]> {
    return new InvestigationService().getRecordTimeline(patientId, hoursBack, 'orderedAt');
  }

  // ================================
  // UTILITY METHODS (Investigation-Specific)
  // ================================

  /**
   * Validate investigation data
   * @param investigation - Investigation to validate
   * @returns true if valid, false otherwise
   */
  static validateInvestigation(investigation: any): boolean {
    if (!investigation.name || !investigation.type) {
      return false;
    }

    // Basic validation for investigation fields
    const requiredFields = ['name', 'type'];
    return requiredFields.every(field => investigation[field]);
  }

  /**
   * Format investigation results for display
   * @param results - Investigation results
   * @returns Formatted results string
   */
  static formatInvestigationResults(results: any): string {
    try {
      if (typeof results === 'string') {
        return results;
      }

      if (typeof results === 'object') {
        return JSON.stringify(results, null, 2);
      }

      return String(results);
    } catch (error) {
      return 'Invalid results format';
    }
  }
}
