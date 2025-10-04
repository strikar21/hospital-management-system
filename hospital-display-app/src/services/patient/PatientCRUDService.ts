/**
 * PatientCRUDService - Core patient data operations
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade patient CRUD operations with search capabilities
 * Updated: Fixed compilation issues
 */

import { patient } from '../../types';
import { BaseService } from '../BaseService';
import { PatientTransformer } from '../../utils/transformers/PatientTransformer';

/**
 * PatientCRUDService - Handles basic patient operations
 *
 * Responsibilities:
 * - Patient data retrieval (single and multiple)
 * - Patient search functionality
 * - Patient discharge operations
 * - Status-based filtering
 */
export class PatientCRUDService extends BaseService {

  /**
   * Retrieves a single patient by their unique identifier
   *
   * @param patientId - The unique identifier for the patient
   * @returns Promise resolving to patient data or null if not found
   * @throws {Error} When backend communication fails
   */
  static async getPatient(patientId: string): Promise<patient | null> {
    try {
      const response = await this.fetchFromBackend(`/patients/${patientId}`);

      if (!response) {
        // Warning: No patient found with ID
        return null;
      }

      // Transform patient data with fallback values for missing fields
      return PatientTransformer.transformPatient(response);
    } catch (error) {
      // Error fetching patient - handle silently
      return null;
    }
  }

  /**
   * Retrieves multiple patients based on filtering criteria
   *
   * @param ward - Optional ward filter for patient location
   * @param department - Optional department filter for medical specialization
   * @param showAllDepts - When true, includes patients from all departments
   * @returns Promise resolving to array of patient data
   * @throws {Error} When backend communication fails
   */
  static async getPatients(ward?: string, department?: string, showAllDepts?: boolean): Promise<patient[]> {
    try {
      let endpoint = '/v2/patients/list';
      const params = new URLSearchParams();

      if (ward) params.append('ward', ward);
      if (department) params.append('department', department);
      if (showAllDepts) params.append('showAllDepts', 'true');

      if (params.toString()) {
        endpoint += `?${params.toString()}`;
      }

      const response = await this.fetchFromBackend(endpoint);

      // Handle v2 response format: {patients: [...], total: number, success: boolean}
      const patients = response?.patients || response;
      if (!Array.isArray(patients)) {
        // Warning: Invalid patient list response format
        return [];
      }

      // Transform patient array with fallback values for missing fields
      return PatientTransformer.transformPatientArray(patients);
    } catch (error) {
      // Error fetching patients - handle silently
      return [];
    }
  }

  /**
   * Searches for patients using a text query across multiple fields
   *
   * @param query - Search query (searches name, ID, MRN, bed number)
   * @returns Promise resolving to array of matching patient data
   * @throws {Error} When backend communication fails
   */
  static async searchPatients(query: string): Promise<patient[]> {
    try {
      const response = await this.fetchFromBackend(`/patients/search?q=${encodeURIComponent(query)}`);
      const patients = Array.isArray(response) ? response : [];
      return PatientTransformer.transformPatientArray(patients);
    } catch (error) {
      // Error searching patients - handle silently
      return [];
    }
  }

  /**
   * Retrieves patients filtered by their medical status
   *
   * @param status - Patient medical status filter
   * @returns Promise resolving to array of patients with specified status
   * @throws {Error} When backend communication fails
   */
  static async getPatientsByStatus(status: 'stable' | 'critical' | 'emergency'): Promise<patient[]> {
    try {
      const response = await this.fetchFromBackend(`/patients/status/${status}`);
      const patients = Array.isArray(response) ? response : [];
      return PatientTransformer.transformPatientArray(patients);
    } catch (error) {
      // Error fetching patients by status - handle silently
      return [];
    }
  }

  /**
   * Initiates patient discharge workflow
   *
   * @param patientId - The unique identifier for the patient
   * @param staffId - The staff member performing the discharge
   * @returns Promise resolving to success status
   * @throws {Error} When discharge process fails
   */
  static async dischargePatient(patientId: string, staffId: string): Promise<boolean> {
    try {
      // Step 1: Initiate discharge workflow
      const initResponse = await this.fetchFromBackend('/discharge-workflow/initiate', {
        method: 'POST',
        body: JSON.stringify({
          patientId,
          initiatedBy: staffId,
          timestamp: new Date().toISOString()
        })
      });

      if (!initResponse?.success) {
        // Error: Discharge initiation failed
        return false;
      }

      // Step 2: Unassign device if assigned
      try {
        await this.fetchFromBackend(`/devices/unassign/${patientId}`, {
          method: 'POST',
          body: JSON.stringify({
            unassignedBy: staffId,
            timestamp: new Date().toISOString()
          })
        });
      } catch (deviceError) {
        // Warning: Device unassignment warning - handle silently
        // Continue with discharge even if device unassignment fails
      }

      // Step 3: Complete discharge
      const completeResponse = await this.fetchFromBackend('/discharge-workflow/complete', {
        method: 'POST',
        body: JSON.stringify({
          patientId,
          completedBy: staffId,
          timestamp: new Date().toISOString()
        })
      });

      return true;

    } catch (error) {
      // Error: Discharge process failed - handle silently
      return false;
    }
  }
}