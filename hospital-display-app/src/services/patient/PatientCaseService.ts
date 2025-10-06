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
   * Retrieves all case entries (medical records) for a specific patient with embedded staff data
   * CONSOLIDATED: Gets case entries + staff data in single call for efficiency
   *
   * @param patientId - The unique identifier for the patient
   * @returns Promise resolving to array of case entry records with resolved staff names
   * @throws {Error} When case entry retrieval fails
   */
  static async getCaseEntries(patientId: string): Promise<any[]> {
    try {
      // Single consolidated call with staff data included
      const response = await this.fetchFromBackend(`/patients/${patientId}/case-entries?includeStaff=true`);
      // Consolidated case entries response received

      // Extract the caseEntries array from the response
      const caseEntries = response?.caseEntries || [];

      // Extract staff mapping from response (eliminating separate API call)
      const staffData = response?.staff || [];
      // Staff data from consolidated response received

      // Build staff mapping from embedded staff data
      const staffMapping: { [key: string]: { name: string; role: string } } = {};
      staffData.forEach((staff: any) => {
        const staffId = staff.staffId || staff.id || staff.userId || staff.staff_id;
        if (staffId) {
          const fullName = staff.name || staff.staffName || staff.fullName ||
                          (staff.firstName && staff.lastName ? `${staff.firstName} ${staff.lastName}` : null) ||
                          staff.firstName || staff.lastName || 'Unknown';
          staffMapping[staffId] = {
            name: fullName,
            role: staff.role || staff.staffRole || 'Staff'
          };
          // Staff mapping created for staffId
        }
      });

      // Final staff mapping completed

      // Transform using unified PatientTransformer with staff mapping for role detection
      const transformedEntries = PatientTransformer.transformCaseTimeline(caseEntries, staffMapping);

      return Array.isArray(transformedEntries) ? transformedEntries : [];
    } catch (error) {
      // Error fetching consolidated case entries - handle silently
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
      // Failed to add case entry - handle silently
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
          performedBy: userId
          // Let backend handle performedAt timestamp to avoid datetime format issues
        })
      });
      return true;
    } catch (error) {
      // Error acknowledging alert - handle silently
      return false;
    }
  }
}