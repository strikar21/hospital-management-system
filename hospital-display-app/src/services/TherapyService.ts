// TherapyService.ts - Therapy and rehabilitation management (V2)
import { therapy } from '../types';
import { BaseService } from './BaseService';

export class TherapyService extends BaseService {

  // ================================
  // V2 RESPONSE HANDLER
  // ================================

  private static handleV2Response<T>(response: any): T[] {
    if (response?.therapy) return response.therapy;
    if (response?.sessions) return response.sessions;
    if (response?.data) return response.data;
    return Array.isArray(response) ? response : [];
  }

  // ================================
  // THERAPY MANAGEMENT (V2)
  // ================================

  static async getPatientTherapy(patientId: string): Promise<therapy[]> {
    try {
      const response = await this.fetchFromBackend(`/therapy/patient/${patientId}`);
      const therapySessions = this.handleV2Response<therapy>(response);

      console.log(`✅ Retrieved ${therapySessions.length} therapy sessions for patient ${patientId}`);
      return therapySessions;
    } catch (error) {
      console.error('❌ Error fetching patient therapy sessions:', error);
      return [];
    }
  }

  static async getActiveTherapy(patientId: string): Promise<therapy[]> {
    try {
      const response = await this.fetchFromBackend(`/therapy/patient/${patientId}/active`);
      const therapySessions = this.handleV2Response<therapy>(response);

      console.log(`✅ Retrieved ${therapySessions.length} active therapy sessions for patient ${patientId}`);
      return therapySessions;
    } catch (error) {
      console.error('❌ Error fetching active therapy sessions:', error);
      return [];
    }
  }

  static async addTherapy(patientId: string, therapy: Omit<therapy, 'id'>, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/therapy/patient/${patientId}/add`, {
        method: 'POST',
        body: JSON.stringify({
          ...therapy,
          prescribedBy: userId,
          prescribedAt: new Date().toISOString(),
          status: 'active'
        })
      });

      console.log('✅ Therapy added successfully');
      return true;
    } catch (error) {
      console.error('❌ Error adding therapy:', error);
      return false;
    }
  }

  static async updateTherapyStatus(sessionId: string, status: string, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/therapy/${sessionId}/status`, {
        method: 'PUT',
        body: JSON.stringify({
          status,
          modifiedBy: userId,
          modifiedAt: new Date().toISOString()
        })
      });

      console.log('✅ Therapy status updated successfully');
      return true;
    } catch (error) {
      console.error('❌ Error updating therapy status:', error);
      return false;
    }
  }

  static async completeTherapySession(sessionId: string, notes: string, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/therapy/${sessionId}/complete`, {
        method: 'POST',
        body: JSON.stringify({
          notes,
          completedBy: userId,
          completedAt: new Date().toISOString()
        })
      });

      console.log('✅ Therapy session completed successfully');
      return true;
    } catch (error) {
      console.error('❌ Error completing therapy session:', error);
      return false;
    }
  }

  // ================================
  // THERAPY TYPES (V2)
  // ================================

  static async getTherapyTypes(): Promise<any[]> {
    try {
      const response = await this.fetchFromBackend(`/therapy/types`);
      const types = this.handleV2Response<any>(response);

      console.log(`✅ Retrieved ${types.length} therapy types`);
      return types;
    } catch (error) {
      console.error('❌ Error fetching therapy types:', error);
      return [];
    }
  }

  // ================================
  // LEGACY SUPPORT METHODS
  // ================================

  static async updateTherapy(patientId: string, sessionId: string, updates: Partial<therapy>, userId: string): Promise<boolean> {
    try {
      // For v2, we use the status endpoint for most updates
      await this.fetchFromBackend(`/therapy/${sessionId}/status`, {
        method: 'PUT',
        body: JSON.stringify({
          ...updates,
          modifiedBy: userId,
          modifiedAt: new Date().toISOString()
        })
      });

      console.log('✅ Therapy updated successfully');
      return true;
    } catch (error) {
      console.error('❌ Error updating therapy:', error);
      return false;
    }
  }

  static async discontinueTherapy(patientId: string, sessionId: string, userId: string): Promise<boolean> {
    try {
      await this.updateTherapyStatus(sessionId, 'discontinued', userId);
      console.log('✅ Therapy discontinued successfully');
      return true;
    } catch (error) {
      console.error('❌ Error discontinuing therapy:', error);
      return false;
    }
  }

  static async getTherapyHistory(patientId: string, sessionId?: string): Promise<therapy[]> {
    try {
      // For v2, we get all therapy sessions and filter if needed
      const sessions = await this.getPatientTherapy(patientId);

      if (sessionId) {
        return sessions.filter(session => session.id === sessionId);
      }

      return sessions;
    } catch (error) {
      console.error('❌ Error fetching therapy history:', error);
      return [];
    }
  }

  static async getTherapyByStatus(patientId: string, status: string): Promise<therapy[]> {
    try {
      if (status === 'active') {
        return await this.getActiveTherapy(patientId);
      }

      // For other statuses, get all and filter
      const sessions = await this.getPatientTherapy(patientId);
      return sessions.filter(session => session.status === status);
    } catch (error) {
      console.error(`❌ Error fetching therapy sessions with status ${status}:`, error);
      return [];
    }
  }

  // ================================
  // THERAPY TIMELINE
  // ================================

  static async getTherapyTimeline(patientId: string, hoursBack: number = 48): Promise<therapy[]> {
    try {
      const sessions = await this.getPatientTherapy(patientId);

      // Filter by time if prescribedAt exists
      const cutoff = new Date();
      cutoff.setHours(cutoff.getHours() - hoursBack);

      return sessions.filter(session =>
        !(session as any).prescribedAt || new Date((session as any).prescribedAt) >= cutoff
      ).sort((a, b) => {
        // Sort by prescribedAt descending (newest first)
        const dateA = new Date((a as any).prescribedAt || 0);
        const dateB = new Date((b as any).prescribedAt || 0);
        return dateB.getTime() - dateA.getTime();
      });
    } catch (error) {
      console.error('❌ Error fetching therapy timeline:', error);
      return [];
    }
  }

  // ================================
  // THERAPY VALIDATION
  // ================================

  static validateTherapy(therapy: any): boolean {
    if (!therapy.name || !therapy.type) {
      return false;
    }

    // Basic validation for therapy fields
    const requiredFields = ['name', 'type'];
    return requiredFields.every(field => therapy[field]);
  }

  static formatTherapyDuration(duration: number): string {
    try {
      if (duration < 60) {
        return `${duration} minutes`;
      }

      const hours = Math.floor(duration / 60);
      const minutes = duration % 60;

      if (minutes === 0) {
        return `${hours} hour${hours > 1 ? 's' : ''}`;
      }

      return `${hours} hour${hours > 1 ? 's' : ''} ${minutes} minute${minutes > 1 ? 's' : ''}`;
    } catch (error) {
      console.error('❌ Error formatting therapy duration:', error);
      return 'Invalid duration';
    }
  }

  static calculateTherapyProgress(therapy: any): number {
    try {
      if (!therapy.totalSessions || therapy.totalSessions <= 0) {
        return 0;
      }

      const completedSessions = therapy.completedSessions || 0;
      return Math.min(100, Math.round((completedSessions / therapy.totalSessions) * 100));
    } catch (error) {
      console.error('❌ Error calculating therapy progress:', error);
      return 0;
    }
  }
}