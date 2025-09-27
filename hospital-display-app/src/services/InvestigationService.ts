// InvestigationService.ts - Medical investigations and lab tests (V2)
import { investigation } from '../types';
import { BaseService } from './BaseService';

export class InvestigationService extends BaseService {

  // ================================
  // V2 RESPONSE HANDLER
  // ================================

  private static handleV2Response<T>(response: any): T[] {
    if (response?.investigations) return response.investigations;
    if (response?.data) return response.data;
    return Array.isArray(response) ? response : [];
  }

  // ================================
  // INVESTIGATION MANAGEMENT (V2)
  // ================================

  static async getPatientInvestigations(patientId: string): Promise<investigation[]> {
    try {
      const response = await this.fetchFromBackend(`/investigations/patient/${patientId}`);
      const investigations = this.handleV2Response<investigation>(response);

      console.log(`✅ Retrieved ${investigations.length} investigations for patient ${patientId}`);
      return investigations;
    } catch (error) {
      console.error('❌ Error fetching patient investigations:', error);
      return [];
    }
  }

  static async getPendingInvestigations(patientId: string): Promise<investigation[]> {
    try {
      const response = await this.fetchFromBackend(`/investigations/patient/${patientId}/pending`);
      const investigations = this.handleV2Response<investigation>(response);

      console.log(`✅ Retrieved ${investigations.length} pending investigations for patient ${patientId}`);
      return investigations;
    } catch (error) {
      console.error('❌ Error fetching pending investigations:', error);
      return [];
    }
  }

  static async addInvestigation(patientId: string, investigation: Omit<investigation, 'id'>, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/investigations/patient/${patientId}/add`, {
        method: 'POST',
        body: JSON.stringify({
          ...investigation,
          orderedBy: userId,
          orderedAt: new Date().toISOString(),
          status: 'ordered'
        })
      });

      console.log('✅ Investigation added successfully');
      return true;
    } catch (error) {
      console.error('❌ Error adding investigation:', error);
      return false;
    }
  }

  static async updateInvestigationStatus(investigationId: string, status: string, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/investigations/${investigationId}/status`, {
        method: 'PUT',
        body: JSON.stringify({
          status,
          modifiedBy: userId,
          modifiedAt: new Date().toISOString()
        })
      });

      console.log('✅ Investigation status updated successfully');
      return true;
    } catch (error) {
      console.error('❌ Error updating investigation status:', error);
      return false;
    }
  }

  static async completeInvestigation(investigationId: string, results: any, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/investigations/${investigationId}/complete`, {
        method: 'POST',
        body: JSON.stringify({
          results,
          completedBy: userId,
          completedAt: new Date().toISOString()
        })
      });

      console.log('✅ Investigation completed successfully');
      return true;
    } catch (error) {
      console.error('❌ Error completing investigation:', error);
      return false;
    }
  }

  static async updateInvestigationResults(investigationId: string, results: any, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/investigations/${investigationId}/results`, {
        method: 'PUT',
        body: JSON.stringify({
          results,
          modifiedBy: userId,
          modifiedAt: new Date().toISOString()
        })
      });

      console.log('✅ Investigation results updated successfully');
      return true;
    } catch (error) {
      console.error('❌ Error updating investigation results:', error);
      return false;
    }
  }

  // ================================
  // INVESTIGATION TYPES (V2)
  // ================================

  static async getInvestigationTypes(): Promise<any[]> {
    try {
      const response = await this.fetchFromBackend(`/investigations/types`);
      const types = this.handleV2Response<any>(response);

      console.log(`✅ Retrieved ${types.length} investigation types`);
      return types;
    } catch (error) {
      console.error('❌ Error fetching investigation types:', error);
      return [];
    }
  }

  // ================================
  // LEGACY SUPPORT METHODS
  // ================================

  static async getInvestigationHistory(patientId: string, investigationId?: string): Promise<any[]> {
    try {
      // For v2, we get all investigations and filter if needed
      const investigations = await this.getPatientInvestigations(patientId);

      if (investigationId) {
        return investigations.filter(inv => inv.id === investigationId);
      }

      return investigations;
    } catch (error) {
      console.error('❌ Error fetching investigation history:', error);
      return [];
    }
  }

  static async getInvestigationsByStatus(patientId: string, status: string): Promise<investigation[]> {
    try {
      if (status === 'pending') {
        return await this.getPendingInvestigations(patientId);
      }

      // For other statuses, get all and filter
      const investigations = await this.getPatientInvestigations(patientId);
      return investigations.filter(inv => inv.status === status);
    } catch (error) {
      console.error(`❌ Error fetching investigations with status ${status}:`, error);
      return [];
    }
  }

  // ================================
  // INVESTIGATION TIMELINE
  // ================================

  static async getInvestigationTimeline(patientId: string, hoursBack: number = 48): Promise<investigation[]> {
    try {
      const investigations = await this.getPatientInvestigations(patientId);

      // Filter by time if orderedAt exists
      const cutoff = new Date();
      cutoff.setHours(cutoff.getHours() - hoursBack);

      return investigations.filter(inv =>
        !(inv as any).orderedAt || new Date((inv as any).orderedAt) >= cutoff
      ).sort((a, b) => {
        // Sort by orderedAt descending (newest first)
        const dateA = new Date((a as any).orderedAt || 0);
        const dateB = new Date((b as any).orderedAt || 0);
        return dateB.getTime() - dateA.getTime();
      });
    } catch (error) {
      console.error('❌ Error fetching investigation timeline:', error);
      return [];
    }
  }

  // ================================
  // INVESTIGATION VALIDATION
  // ================================

  static validateInvestigation(investigation: any): boolean {
    if (!investigation.name || !investigation.type) {
      return false;
    }

    // Basic validation for investigation fields
    const requiredFields = ['name', 'type'];
    return requiredFields.every(field => investigation[field]);
  }

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
      console.error('❌ Error formatting investigation results:', error);
      return 'Invalid results format';
    }
  }
}