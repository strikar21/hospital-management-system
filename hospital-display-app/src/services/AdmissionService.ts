// services/AdmissionService.ts - Admission workflow service
// STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
import { BaseService } from './BaseService';

export class AdmissionService extends BaseService {

  /**
   * Get admission recommendations
   * @param status - Filter by status (pending, approved, rejected)
   * @returns Array of admission recommendations
   */
  static async getRecommendations(status: string = 'pending'): Promise<any[]> {
    try {
      const response = await this.fetchFromBackend(`/admission/recommendations?status=${status}`);
      return response?.recommendations || response || [];
    } catch (error) {
      console.error('Error fetching admission recommendations:', error);
      return [];
    }
  }

  /**
   * Get available devices for admission
   * @param deviceType - Type of device (watch, monitor, etc.)
   * @returns Array of available devices
   */
  static async getAvailableDevices(deviceType: string = 'watch'): Promise<any[]> {
    try {
      const response = await this.fetchFromBackend(`/admission/available-devices?devicetype=${deviceType}`);
      return response?.devices || response || [];
    } catch (error) {
      console.error('Error fetching available devices:', error);
      return [];
    }
  }

  /**
   * Process admission (Nurse completes admission from doctor's recommendation)
   * @param admissionData - Complete admission data (patient, room, bed, device, etc.)
   * @returns Created patient record
   */
  static async processAdmission(admissionData: any): Promise<any> {
    try {
      const response = await this.fetchFromBackend('/admission/process-admission', {
        method: 'POST',
        body: JSON.stringify(admissionData)
      });
      return response;
    } catch (error) {
      console.error('Error processing admission:', error);
      throw error;
    }
  }

  /**
   * Create admission recommendation (Doctor recommends admission)
   * @param recommendationData - Patient info, diagnosis, recommended ward, etc.
   * @returns Created recommendation
   */
  static async createRecommendation(recommendationData: any): Promise<any> {
    try {
      const response = await this.fetchFromBackend('/admission/recommendations', {
        method: 'POST',
        body: JSON.stringify(recommendationData)
      });
      return response;
    } catch (error) {
      console.error('Error creating admission recommendation:', error);
      throw error;
    }
  }
}
