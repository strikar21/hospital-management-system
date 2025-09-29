/**
 * PatientCaseService - Patient case management and alerts
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade case management with alert handling
 */

import { BaseService } from '../BaseService';
import { PatientTransformer } from '../../utils/transformers/PatientTransformer';

/**
 * PatientCaseService - Handles patient case entries and alerts
 *
 * Responsibilities:
 * - Medical case entry management
 * - Case history retrieval
 * - Alert acknowledgment
 * - Medical record operations
 */
export class PatientCaseService extends BaseService {


  /**
   * Retrieves all case entries (medical records) for a specific patient
   *
   * @param patientId - The unique identifier for the patient
   * @returns Promise resolving to array of case entry records
   * @throws {Error} When case entry retrieval fails
   */
  static async getCaseEntries(patientId: string): Promise<any[]> {
    try {
      const response = await this.fetchFromBackend(`/patients/${patientId}/case-entries`);
      const staffWithRoles = await this.getStaffWithRoles();

      // Extract the caseEntries array from the response
      const caseEntries = response?.caseEntries || [];

      // Transform using unified PatientTransformer with staff mapping for role detection
      const transformedEntries = PatientTransformer.transformCaseTimeline(caseEntries, staffWithRoles);

      return Array.isArray(transformedEntries) ? transformedEntries : [];
    } catch (error) {
      console.error('❌ Error fetching case entries:', error);
      return [];
    }
  }

  /**
   * Adds a new case entry to a patient's medical record
   *
   * @param patientId - The unique identifier for the patient
   * @param entryData - The case entry data containing medical information
   * @param userId - The ID of the user creating the entry
   * @returns Promise resolving to true if case entry was added successfully
   * @throws {Error} When case entry creation fails
   */
  static async addCaseEntry(patientId: string, entryData: {
    entryType: string;
    description: string;
    findings?: string;
    recommendations?: string;
    followUpDate?: string;
    severity?: string;
    category?: string;
  }, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/patients/${patientId}/case-entries`, {
        method: 'POST',
        body: JSON.stringify({
          ...entryData,
          createdBy: userId
          // Let backend handle timestamp creation to avoid datetime format issues
        })
      });
      return true;
    } catch (error) {
      console.error('❌ Failed to add case entry:', error);
      return false;
    }
  }

  /**
   * Acknowledges a patient alert
   *
   * @param patientId - The unique identifier for the patient
   * @param alertId - The unique identifier for the alert
   * @param userId - The ID of the user acknowledging the alert
   * @returns Promise resolving to true if alert was acknowledged successfully
   * @throws {Error} When alert acknowledgment fails
   */
  static async acknowledgeAlert(patientId: string, alertId: string, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/mobile/acknowledge-alert/${patientId}/${alertId}`, {
        method: 'POST',
        body: JSON.stringify({
          acknowledgedBy: userId
          // Let backend handle acknowledgedAt timestamp to avoid datetime format issues
        })
      });
      return true;
    } catch (error) {
      console.error('❌ Error acknowledging alert:', error);
      return false;
    }
  }
}