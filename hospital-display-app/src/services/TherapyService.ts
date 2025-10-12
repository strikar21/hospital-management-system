/**
 * TherapyService - Therapy and rehabilitation management (V2 - Refactored)
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data
 *
 * Extends BaseMedicalRecordService for generic CRUD operations.
 * Adds therapy-specific field mapping and session management.
 *
 * @module TherapyService
 * @since 2.0.0
 */

import { therapy } from '../types';
import { BaseMedicalRecordService, MedicalRecordConfig } from './base/BaseMedicalRecordService';

export class TherapyService extends BaseMedicalRecordService<therapy> {

  // ================================
  // CONFIGURATION
  // ================================

  protected getConfig(): MedicalRecordConfig {
    return {
      recordType: 'therapies',       // FIXED: Backend endpoint uses plural
      recordTypeSingular: 'therapy',
      recordTypePlural: 'therapies'  // FIXED: Backend response uses plural
    };
  }

  // ================================
  // TYPE-SPECIFIC PAYLOAD TRANSFORMATION
  // ================================

  /**
   * Transform therapy payload with field mapping
   * Maps frontend field names to backend validator expectations
   */
  protected transformAddPayload(therapy: any, userId: string): any {
    return {
      therapyType: therapy.type,           // Backend expects "therapyType" not "type"
      description: therapy.description,
      startDate: therapy.startDate,        // Backend expects datetime
      frequency: therapy.frequency,
      prescribedBy: userId,
      status: 'scheduled',                 // Backend enum: scheduled|in-progress|completed|discontinued|on-hold
      notes: therapy.notes
      // Omit: name, duration, sessions (backend doesn't accept these)
    };
  }

  // ================================
  // STATIC WRAPPER METHODS (Backward Compatibility)
  // ================================

  /**
   * Get all therapy sessions for a patient
   * @param patientId - Patient ID
   * @returns Promise resolving to array of therapy sessions
   */
  static async getPatientTherapy(patientId: string): Promise<therapy[]> {
    const instance = new TherapyService();
    return await instance.getPatientRecords(patientId);
  }

  /**
   * Get active therapy sessions for a patient
   * @param patientId - Patient ID
   * @returns Promise resolving to array of active therapy sessions
   */
  static async getActiveTherapy(patientId: string): Promise<therapy[]> {
    return new TherapyService().getActiveRecords(patientId, 'active');
  }

  /**
   * Add new therapy
   * @param patientId - Patient ID
   * @param therapy - Therapy data (excluding backend-generated fields)
   * @param userId - User ID
   * @returns Promise resolving to atomic response
   */
  static async addTherapy(
    patientId: string,
    therapy: Omit<therapy, 'id' | 'createdAt' | 'updatedAt' | 'createdBy' | 'createdByName'>,
    userId: string
  ): Promise<any> {
    return new TherapyService().addRecord(patientId, therapy, userId);
  }

  /**
   * Update therapy status
   * @param sessionId - Therapy session ID
   * @param status - New status
   * @param userId - User ID
   * @returns Promise resolving to success boolean
   */
  static async updateTherapyStatus(sessionId: string, status: string, userId: string): Promise<boolean> {
    return new TherapyService().updateRecordStatus(sessionId, status, userId);
  }

  /**
   * Complete therapy session (legacy method)
   * @param sessionId - Therapy session ID
   * @param notes - Session notes
   * @param userId - User ID
   * @returns Promise resolving to success boolean
   */
  static async completeTherapySession(sessionId: string, notes: string, userId: string): Promise<boolean> {
    try {
      await new TherapyService().fetchFromBackend(`/therapy/${sessionId}/complete`, {
        method: 'POST',
        body: JSON.stringify({
          notes,
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
   * Update therapy (legacy method)
   * @param patientId - Patient ID
   * @param sessionId - Therapy session ID
   * @param updates - Partial therapy updates
   * @param userId - User ID
   * @returns Promise resolving to success boolean
   */
  static async updateTherapy(
    patientId: string,
    sessionId: string,
    updates: Partial<therapy>,
    userId: string
  ): Promise<boolean> {
    try {
      await new TherapyService().fetchFromBackend(`/therapy/${sessionId}/status`, {
        method: 'PUT',
        body: JSON.stringify({
          ...updates,
          modifiedBy: userId,
          modifiedAt: new Date().toISOString()
        })
      });

      return true;
    } catch (error) {
      return false;
    }
  }

  /**
   * Discontinue therapy
   * @param patientId - Patient ID
   * @param sessionId - Therapy session ID
   * @param userId - User ID
   * @returns Promise resolving to success boolean
   */
  static async discontinueTherapy(patientId: string, sessionId: string, userId: string): Promise<boolean> {
    try {
      await TherapyService.updateTherapyStatus(sessionId, 'discontinued', userId);
      return true;
    } catch (error) {
      return false;
    }
  }

  // ================================
  // ATOMIC OPERATIONS (Therapy-Specific)
  // ================================

  /**
   * Add therapy session atomically with automatic case entry creation
   * @param patientId - Patient ID
   * @param therapyId - Therapy ID
   * @param duration - Session duration in minutes
   * @param notes - Session notes
   * @param userId - User ID performing the action
   * @returns Promise resolving to atomic response with medicalRecord and caseEntry
   */
  static async addTherapySessionAtomic(
    patientId: string,
    therapyId: string,
    duration: number,
    notes: string,
    userId: string
  ): Promise<any> {
    try {
      const response = await new TherapyService().fetchFromBackend(
        `/atomic/patients/${patientId}/therapies/${therapyId}/sessions`,
        {
          method: 'POST',
          body: JSON.stringify({
            therapyId: therapyId,
            duration: duration,
            notes: notes,
            performedBy: userId
          })
        }
      );
      return response;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Complete therapy atomically with automatic case entry creation
   * @param patientId - Patient ID
   * @param therapyId - Therapy ID
   * @param userId - User ID performing the action
   * @returns Promise resolving to atomic response with medicalRecord and caseEntry
   */
  static async completeTherapyAtomic(
    patientId: string,
    therapyId: string,
    userId: string
  ): Promise<any> {
    try {
      const response = await new TherapyService().fetchFromBackend(
        `/atomic/patients/${patientId}/therapies/${therapyId}/status?new_status=completed&performedBy=${userId}`,
        {
          method: 'PUT'
        }
      );
      return response;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Cancel therapy atomically with automatic case entry creation
   * @param patientId - Patient ID
   * @param therapyId - Therapy ID
   * @param userId - User ID performing the action
   * @returns Promise resolving to atomic response with medicalRecord and caseEntry
   */
  static async cancelTherapyAtomic(
    patientId: string,
    therapyId: string,
    userId: string
  ): Promise<any> {
    try {
      const response = await new TherapyService().fetchFromBackend(
        `/atomic/patients/${patientId}/therapies/${therapyId}/status?new_status=cancelled&performedBy=${userId}`,
        {
          method: 'PUT'
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
   * Get available therapy types
   * @returns Promise resolving to array of therapy types
   */
  static async getTherapyTypes(): Promise<any[]> {
    return new TherapyService().getRecordTypes();
  }

  /**
   * Get therapy history
   * @param patientId - Patient ID
   * @param sessionId - Optional specific therapy session ID
   * @returns Promise resolving to therapy history
   */
  static async getTherapyHistory(patientId: string, sessionId?: string): Promise<therapy[]> {
    return new TherapyService().getRecordHistory(patientId, sessionId);
  }

  /**
   * Get therapy sessions by status
   * @param patientId - Patient ID
   * @param status - Status to filter by
   * @returns Promise resolving to filtered therapy sessions
   */
  static async getTherapyByStatus(patientId: string, status: string): Promise<therapy[]> {
    return new TherapyService().getRecordsByStatus(patientId, status);
  }

  /**
   * Get therapy timeline
   * @param patientId - Patient ID
   * @param hoursBack - Hours to look back (default: 48)
   * @returns Promise resolving to therapy timeline
   */
  static async getTherapyTimeline(patientId: string, hoursBack: number = 48): Promise<therapy[]> {
    return new TherapyService().getRecordTimeline(patientId, hoursBack, 'prescribedAt');
  }

  // ================================
  // UTILITY METHODS (Therapy-Specific)
  // ================================

  /**
   * Validate therapy data
   * @param therapy - Therapy to validate
   * @returns true if valid, false otherwise
   */
  static validateTherapy(therapy: any): boolean {
    if (!therapy.name || !therapy.type) {
      return false;
    }

    // Basic validation for therapy fields
    const requiredFields = ['name', 'type'];
    return requiredFields.every(field => therapy[field]);
  }

  /**
   * Format therapy duration for display
   * @param duration - Duration in minutes
   * @returns Formatted duration string
   */
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
      return 'Invalid duration';
    }
  }

  /**
   * Calculate therapy progress percentage
   * @param therapy - Therapy session with totalSessions and completedSessions
   * @returns Progress percentage (0-100)
   */
  static calculateTherapyProgress(therapy: any): number {
    try {
      if (!therapy.totalSessions || therapy.totalSessions <= 0) {
        return 0;
      }

      const completedSessions = therapy.completedSessions || 0;
      return Math.min(100, Math.round((completedSessions / therapy.totalSessions) * 100));
    } catch (error) {
      return 0;
    }
  }
}
