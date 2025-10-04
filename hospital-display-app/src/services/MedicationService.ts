// MedicationService.ts - Medication management and administration (V2)
import { medication } from '../types';
import { BaseService } from './BaseService';

export class MedicationService extends BaseService {

  // ================================
  // V2 RESPONSE HANDLER
  // ================================

  private static handleV2Response<T>(response: any): T[] {
    if (response?.medications) return response.medications;
    if (response?.data) return response.data;
    return Array.isArray(response) ? response : [];
  }

  // ================================
  // MEDICATION MANAGEMENT (V2)
  // ================================

  static async getPatientMedications(patientId: string): Promise<medication[]> {
    try {
      const response = await this.fetchFromBackend(`/medications/patient/${patientId}`);
      const medications = this.handleV2Response<medication>(response);

      // Removed console.log for production
      return medications;
    } catch (error) {
      // Error fetching patient medications - handle silently
      return [];
    }
  }

  static async getActiveMedications(patientId: string): Promise<medication[]> {
    try {
      const response = await this.fetchFromBackend(`/medications/patient/${patientId}/active`);
      const medications = this.handleV2Response<medication>(response);

      // Removed console.log for production
      return medications;
    } catch (error) {
      // Error fetching active medications - handle silently
      return [];
    }
  }

  static async addMedication(patientId: string, medication: Omit<medication, 'id' | 'history'>, userId: string): Promise<medication | null> {
    try {
      const response = await this.fetchFromBackend(`/medications/patient/${patientId}/add`, {
        method: 'POST',
        body: JSON.stringify({
          medicationName: medication.name, // Map 'name' to 'medicationName' for backend
          dosage: medication.dosage,
          frequency: medication.frequency,
          route: medication.route,
          duration: medication.duration,
          prescribedBy: medication.prescribedBy || userId,
          createdAt: new Date().toISOString(),
          status: 'active'
        })
      });

      // Removed console.log for production
      return response; // Return the actual medication object from backend
    } catch (error) {
      // Error adding medication - handle silently
      return null;
    }
  }

  // Overloaded method signatures for backward compatibility
  static async updateMedication(patientId: string, medicationId: string, status: 'active' | 'stopped' | 'held', userId: string): Promise<boolean>
  static async updateMedication(patientId: string, medicationId: string, updates: Partial<medication>, userId: string): Promise<boolean>
  static async updateMedication(patientId: string, medicationId: string, statusOrUpdates: any, userId: string): Promise<boolean> {
    try {
      const updates = typeof statusOrUpdates === 'string'
        ? { status: statusOrUpdates }
        : statusOrUpdates;

      await this.fetchFromBackend(`/medications/${medicationId}/status`, {
        method: 'PUT',
        body: JSON.stringify({
          ...updates,
          modifiedBy: userId,
          modifiedAt: new Date().toISOString()
        })
      });

      // Removed console.log for production
      return true;
    } catch (error) {
      // Error updating medication - handle silently
      return false;
    }
  }

  static async discontinueMedication(patientId: string, medicationId: string, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/medications/${medicationId}/status`, {
        method: 'PUT',
        body: JSON.stringify({
          status: 'discontinued',
          discontinuedBy: userId,
          discontinuedAt: new Date().toISOString(),
          reason: 'Manual discontinuation'
        })
      });

      // Removed console.log for production
      return true;
    } catch (error) {
      // Error discontinuing medication - handle silently
      return false;
    }
  }

  // ================================
  // MEDICATION ADMINISTRATION (V2)
  // ================================

  static async recordMedicationAdministration(patientId: string, medicationId: string, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/medications/${medicationId}/complete`, {
        method: 'POST',
        body: JSON.stringify({
          administeredBy: userId,
          administeredAt: new Date().toISOString(),
          notes: 'Medication administered as prescribed'
        })
      });

      // Removed console.log for production
      return true;
    } catch (error) {
      // Error recording medication administration - handle silently
      return false;
    }
  }

  // ================================
  // MEDICATION TYPES (V2)
  // ================================

  static async getMedicationTypes(): Promise<any[]> {
    try {
      const response = await this.fetchFromBackend(`/medications/types`);
      const types = this.handleV2Response<any>(response);

      // Removed console.log for production
      return types;
    } catch (error) {
      // Error fetching medication types - handle silently
      return [];
    }
  }

  // ================================
  // MEDICATION TIMELINE AND HISTORY (LEGACY SUPPORT)
  // ================================

  static async getMedicationTimeline(patientId: string, hoursBack: number = 24) {
    try {
      // Using active medications as timeline approximation
      const medications = await this.getActiveMedications(patientId);

      // Filter by time if lastAdministered exists
      const cutoff = new Date();
      cutoff.setHours(cutoff.getHours() - hoursBack);

      return medications.filter(med =>
        !(med as any).lastAdministered || new Date((med as any).lastAdministered) >= cutoff
      );
    } catch (error) {
      // Error fetching medication timeline - handle silently
      return [];
    }
  }

  static async getMedicationHistory(patientId: string, medicationId?: string): Promise<any[]> {
    try {
      // For v2, we get all medications and filter if needed
      const medications = await this.getPatientMedications(patientId);

      if (medicationId) {
        return medications.filter(med => med.id === medicationId);
      }

      return medications;
    } catch (error) {
      // Error fetching medication history - handle silently
      return [];
    }
  }

  // ================================
  // MEDICATION CORRELATIONS (LEGACY SUPPORT)
  // ================================

  static async getMedicationCorrelatedVitals(
    patientId: string,
    medicationId: string,
    hoursBack: number = 24
  ): Promise<{ medication: any; vitals: any[] }> {
    try {
      // Fetching medication-correlated vitals for patient - processing silently

      // For v2, we'll need to fetch medication and vitals separately
      const medications = await this.getPatientMedications(patientId);
      const medication = medications.find(med => med.id === medicationId);

      // Note: Vitals correlation would need a separate v2 vitals service
      // Warning: Vitals correlation not yet implemented in v2

      return {
        medication: medication || null,
        vitals: []
      };
    } catch (error) {
      // Error fetching medication-correlated vitals - handle silently
      return { medication: null, vitals: [] };
    }
  }

  // ================================
  // MEDICATION VALIDATION (UNCHANGED)
  // ================================

  static validateMedicationDosage(medication: any): boolean {
    if (!medication.dosage || !medication.frequency) {
      return false;
    }

    // Basic validation for common dosage formats
    const dosagePattern = /^\d+(\.\d+)?\s?(mg|g|ml|units?|mcg|μg)/i;
    const frequencyPattern = /^(once|twice|three times?|four times?|\d+\s?times?)\s?(daily|per day|a day|qd|bid|tid|qid)/i;

    return dosagePattern.test(medication.dosage) && frequencyPattern.test(medication.frequency);
  }

  static calculateNextDose(medication: any): Date | null {
    try {
      if (!medication.lastAdministered || !medication.frequency) {
        return null;
      }

      const lastDose = new Date(medication.lastAdministered);
      const frequency = medication.frequency.toLowerCase();

      let hoursInterval = 24; // Default to once daily

      if (frequency.includes('bid') || frequency.includes('twice')) {
        hoursInterval = 12;
      } else if (frequency.includes('tid') || frequency.includes('three')) {
        hoursInterval = 8;
      } else if (frequency.includes('qid') || frequency.includes('four')) {
        hoursInterval = 6;
      } else if (frequency.includes('q6h')) {
        hoursInterval = 6;
      } else if (frequency.includes('q8h')) {
        hoursInterval = 8;
      } else if (frequency.includes('q12h')) {
        hoursInterval = 12;
      }

      const nextDose = new Date(lastDose.getTime() + (hoursInterval * 60 * 60 * 1000));
      return nextDose;
    } catch (error) {
      // Error calculating next dose - handle silently
      return null;
    }
  }

  // ================================
  // MEDICATION ALERTS (LEGACY SUPPORT - V1 FALLBACK)
  // ================================

  static async getMedicationAlerts(patientId: string): Promise<any[]> {
    try {
      // V2 doesn't have dedicated medication alerts endpoint yet
      // Fall back to v1 for now
      const response = await this.fetchFromBackend(`/patients/${patientId}/medications/alerts`);
      return Array.isArray(response) ? response : [];
    } catch (error) {
      // Warning: Medication alerts not available in v2, falling back to empty array
      return [];
    }
  }

  static async acknowledgeMedicationAlert(patientId: string, alertId: string, userId: string): Promise<boolean> {
    try {
      // V2 doesn't have dedicated medication alerts endpoint yet
      // Fall back to v1 for now
      await this.fetchFromBackend(`/patients/${patientId}/medications/alerts/${alertId}/acknowledge`, {
        method: 'POST',
        body: JSON.stringify({
          acknowledgedBy: userId,
          acknowledgedAt: new Date().toISOString()
        })
      });

      // Removed console.log for production
      return true;
    } catch (error) {
      // Warning: Medication alert acknowledgment not available in v2
      return false;
    }
  }

  // ================================
  // MEDICATION INTERACTIONS (LEGACY SUPPORT - V1 FALLBACK)
  // ================================

  static async checkMedicationInteractions(patientId: string, newMedication: any): Promise<any[]> {
    try {
      // V2 doesn't have medication interactions endpoint yet
      // Fall back to v1 for now
      const response = await this.fetchFromBackend(`/patients/${patientId}/medications/check-interactions`, {
        method: 'POST',
        body: JSON.stringify(newMedication)
      });

      return Array.isArray(response) ? response : [];
    } catch (error) {
      // Warning: Medication interactions not available in v2, falling back to empty array
      return [];
    }
  }
}