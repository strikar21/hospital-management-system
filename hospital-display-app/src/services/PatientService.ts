// PatientService.ts - Patient data and case management
import { patient, noteComment } from '../types';
import { BaseService } from './BaseService';
import { MedicalDataTransformer } from '../utils/dataTransformers';

export class PatientService extends BaseService {

  // ================================
  // PATIENT DATA MANAGEMENT
  // ================================

  // ================================
  // PATIENT RETRIEVAL
  // ================================

  static async getPatient(patientId: string): Promise<patient | null> {
    try {
      console.log(`🔍 Fetching complete patient data for: ${patientId}`);

      const response = await this.fetchFromBackend(`/patients/${patientId}`);

      if (!response) {
        console.warn(`⚠️ No patient found with ID: ${patientId}`);
        return null;
      }

      console.log(`✅ Raw patient data received for ${patientId}:`, response);

      // Transform and return patient data
      const transformedPatient = MedicalDataTransformer.transformPatientData(response);

      console.log(`🔄 Transformed patient data for ${patientId}:`, transformedPatient);

      return transformedPatient;
    } catch (error) {
      console.error(`❌ Error fetching patient ${patientId}:`, error);
      return null;
    }
  }

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

      console.log(`🔍 Fetching patients from: ${endpoint}`);
      const response = await this.fetchFromBackend(endpoint);

      // Handle v2 response format: {patients: [...], total: number, success: boolean}
      const patients = response?.patients || response;
      if (!Array.isArray(patients)) {
        console.warn('⚠️ Invalid patient list response format');
        return [];
      }

      console.log(`✅ Retrieved ${patients.length} patients`);

      // Transform all patient data
      return patients.map(p => MedicalDataTransformer.transformPatientData(p));
    } catch (error) {
      console.error('❌ Error fetching patients:', error);
      return [];
    }
  }

  static async searchPatients(query: string): Promise<patient[]> {
    try {
      const response = await this.fetchFromBackend(`/patients/search?q=${encodeURIComponent(query)}`);
      return Array.isArray(response) ? response.map(p => MedicalDataTransformer.transformPatientData(p)) : [];
    } catch (error) {
      console.error('❌ Error searching patients:', error);
      return [];
    }
  }

  static async getPatientsByStatus(status: 'stable' | 'critical' | 'emergency'): Promise<patient[]> {
    try {
      const response = await this.fetchFromBackend(`/patients/list?status=${status}`);
      return Array.isArray(response) ? response.map(p => MedicalDataTransformer.transformPatientData(p)) : [];
    } catch (error) {
      console.error('❌ Error fetching patients by status:', error);
      return [];
    }
  }

  // ================================
  // PATIENT NOTES
  // ================================

  static async addNoteComment(patientId: string, content: string, userId: string, username?: string, userrole?: string): Promise<any> {
    try {
      const response = await this.fetchFromBackend(`/patients/${patientId}/notes?createdBy=${encodeURIComponent(userId)}`, {
        method: 'POST',
        body: JSON.stringify({
          content,
          authorId: userId,
          authorName: username || 'Unknown',
          authorRole: userrole || 'Staff',
          timestamp: new Date().toISOString()
        })
      });
      console.log('✅ Note added successfully');
      return response;
    } catch (error) {
      console.error('❌ Error adding note:', error);
      throw error;
    }
  }

  static async editNoteComment(patientId: string, noteId: string, newContent: string, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/patients/${patientId}/notes/${noteId}`, {
        method: 'PUT',
        body: JSON.stringify({
          content: newContent,
          editedBy: userId,
          editedAt: new Date().toISOString()
        })
      });
      console.log('✅ Note edited successfully');
      return true;
    } catch (error) {
      console.error('❌ Error editing note:', error);
      return false;
    }
  }

  static async deleteNoteComment(patientId: string, noteId: string, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/patients/${patientId}/notes/${noteId}`, {
        method: 'DELETE',
        headers: {
          'X-Deleted-By': userId
        }
      });
      console.log('✅ Note deleted successfully');
      return true;
    } catch (error) {
      console.error('❌ Error deleting note:', error);
      return false;
    }
  }

  static canEditNote(note: noteComment, userId: string): boolean {
    return note.authorId === userId && this.canEditItem(note.timestamp);
  }

  // Public wrapper for protected canEditItem method
  static canEditItem(timestamp: string): boolean {
    return super.canEditItem(timestamp);
  }

  // ================================
  // CASE ENTRIES
  // ================================

  static async getCaseEntries(patientId: string): Promise<any[]> {
    try {
      const response = await this.fetchFromBackend(`/patients/${patientId}/case-entries`);
      return Array.isArray(response) ? response : [];
    } catch (error) {
      console.error('❌ Error fetching case entries:', error);
      return [];
    }
  }

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
          createdBy: userId,
          timestamp: new Date().toISOString()
        })
      });
      return true;
    } catch (error) {
      console.error('❌ Failed to add case entry:', error);
      return false;
    }
  }

  // ================================
  // PATIENT DISCHARGE
  // ================================

  static async dischargePatient(patientId: string, staffId: string): Promise<boolean> {
    try {
      // Use new workflow endpoints
      console.log(`🏥 Starting discharge process for patient: ${patientId}`);

      // Step 1: Initiate discharge workflow
      const workflowResponse = await this.fetchFromBackend('/discharge-workflow/initiate', {
        method: 'POST',
        body: JSON.stringify({
          patientId,
          initiatedBy: staffId,
          timestamp: new Date().toISOString()
        })
      });

      console.log('✅ Discharge workflow initiated:', workflowResponse);

      // Step 2: Auto-unassign devices
      try {
        const unassignResponse = await this.fetchFromBackend('/watch-management/bulk-unassign', {
          method: 'POST',
          body: JSON.stringify({
            patientId,
            reason: 'patient_discharge',
            unassignedBy: staffId
          })
        });
        console.log('✅ Devices unassigned:', unassignResponse);
      } catch (deviceError) {
        console.warn('⚠️ Device unassignment warning:', deviceError);
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

      console.log('✅ Patient discharge completed successfully:', completeResponse);
      return true;

    } catch (error) {
      console.error('❌ Discharge process failed:', error);
      return false;
    }
  }

  // ================================
  // ALERTS
  // ================================

  static async acknowledgeAlert(patientId: string, alertId: string, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/mobile/acknowledge-alert/${patientId}/${alertId}`, {
        method: 'POST',
        body: JSON.stringify({
          acknowledgedBy: userId,
          acknowledgedAt: new Date().toISOString()
        })
      });
      console.log('✅ Alert acknowledged successfully');
      return true;
    } catch (error) {
      console.error('❌ Error acknowledging alert:', error);
      return false;
    }
  }
}