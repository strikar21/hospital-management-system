/**
 * MedicationService - Medication management and administration (V2 - Refactored)
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data
 *
 * Extends BaseMedicalRecordService for generic CRUD operations.
 * Adds medication-specific atomic operations and route mapping.
 *
 * @module MedicationService
 * @since 2.0.0
 */

import { medication } from '../types';
import { BaseMedicalRecordService, MedicalRecordConfig } from './base/BaseMedicalRecordService';

export class MedicationService extends BaseMedicalRecordService<medication> {

  // ================================
  // CONFIGURATION
  // ================================

  protected getConfig(): MedicalRecordConfig {
    return {
      recordType: 'medications',
      recordTypeSingular: 'medication',
      recordTypePlural: 'medications'
    };
  }

  // ================================
  // TYPE-SPECIFIC PAYLOAD TRANSFORMATION
  // ================================

  /**
   * Transform medication payload with route mapping
   * Maps frontend route abbreviations to backend expected values
   */
  protected transformAddPayload(medication: any, userId: string): any {
    // Medication-specific: Route mapping
    const routeMap: Record<string, string> = {
      'PO': 'Oral',
      'IV': 'IV',
      'IM': 'IM',
      'SC': 'SC',
      'Inhaled': 'Inhalation',
      'Topical': 'Topical',
      'Rectal': 'Rectal',
      'Sublingual': 'Sublingual',
      'Transdermal': 'Transdermal',
      'Intrathecal': 'Intrathecal',
      'Epidural': 'Epidural',
      'Other': 'Other'
    };

    const route = routeMap[medication.route] || medication.route;

    return {
      name: medication.name,
      dosage: medication.dosage,
      frequency: medication.frequency,
      route: route,
      duration: medication.duration,
      prescribedBy: medication.prescribedBy || userId,
      status: 'active'
    };
  }

  // ================================
  // STATIC WRAPPER METHODS (Backward Compatibility)
  // ================================

  /**
   * Get all medications for a patient
   * @param patientId - Patient ID
   * @returns Promise resolving to array of medications
   */
  static async getPatientMedications(patientId: string): Promise<medication[]> {
    const instance = new MedicationService();
    const medications = await instance.getPatientRecords(patientId);

    // Add console logs for debugging (like original)
    console.log('🔍 Fetching medications for patient:', patientId);
    console.log('✅ Parsed medications:', medications.length, 'total');
    if (medications.length > 0) {
      console.log('📋 Sample medication with staff names:', medications[0]);
    }

    return medications;
  }

  /**
   * Get active medications for a patient
   * @param patientId - Patient ID
   * @returns Promise resolving to array of active medications
   */
  static async getActiveMedications(patientId: string): Promise<medication[]> {
    return new MedicationService().getActiveRecords(patientId, 'active');
  }

  /**
   * Add new medication
   * @param patientId - Patient ID
   * @param medication - Medication data
   * @param userId - User ID
   * @returns Promise resolving to atomic response
   */
  static async addMedication(
    patientId: string,
    medication: Omit<medication, 'id' | 'history'>,
    userId: string
  ): Promise<any> {
    return new MedicationService().addRecord(patientId, medication, userId);
  }

  /**
   * Update medication (overloaded for backward compatibility)
   * @param patientId - Patient ID
   * @param medicationId - Medication ID
   * @param statusOrUpdates - Status string or updates object
   * @param userId - User ID
   * @returns Promise resolving to success boolean
   */
  static async updateMedication(
    patientId: string,
    medicationId: string,
    statusOrUpdates: any,
    userId: string
  ): Promise<boolean> {
    const status = typeof statusOrUpdates === 'string'
      ? statusOrUpdates
      : statusOrUpdates.status;

    return new MedicationService().updateRecordStatus(medicationId, status, userId);
  }

  /**
   * Discontinue medication
   * @param patientId - Patient ID
   * @param medicationId - Medication ID
   * @param userId - User ID
   * @returns Promise resolving to success boolean
   */
  static async discontinueMedication(
    patientId: string,
    medicationId: string,
    userId: string
  ): Promise<boolean> {
    try {
      await new MedicationService().fetchFromBackend(`/medications/${medicationId}/status`, {
        method: 'PUT',
        body: JSON.stringify({
          status: 'discontinued',
          discontinuedBy: userId,
          discontinuedAt: new Date().toISOString(),
          reason: 'Manual discontinuation'
        })
      });

      return true;
    } catch (error) {
      return false;
    }
  }

  /**
   * Record medication administration
   * @param patientId - Patient ID
   * @param medicationId - Medication ID
   * @param userId - User ID
   * @returns Promise resolving to success boolean
   */
  static async recordMedicationAdministration(
    patientId: string,
    medicationId: string,
    userId: string
  ): Promise<boolean> {
    try {
      await new MedicationService().fetchFromBackend(`/medications/${medicationId}/complete`, {
        method: 'POST',
        body: JSON.stringify({
          performedBy: userId,
          performedAt: new Date().toISOString(),
          notes: 'Medication administered as prescribed'
        })
      });

      return true;
    } catch (error) {
      return false;
    }
  }

  // ================================
  // ATOMIC OPERATIONS (Medication-Specific)
  // ================================

  /**
   * Change medication status atomically with automatic case entry creation
   * @param patientId - Patient ID
   * @param medicationId - Medication ID
   * @param status - New status (active, discontinued, held)
   * @param userId - User ID performing the action
   * @returns Promise resolving to atomic response with medicalRecord and caseEntry
   */
  static async changeMedicationStatusAtomic(
    patientId: string,
    medicationId: string,
    status: 'active' | 'discontinued' | 'held',
    userId: string
  ): Promise<any> {
    try {
      const response = await new MedicationService().fetchFromBackend(
        `/atomic/patients/${patientId}/medications/${medicationId}/status`,
        {
          method: 'POST',
          body: JSON.stringify({
            status: status,
            changedBy: userId
          })
        }
      );
      return response;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Administer medication atomically with automatic case entry creation
   * @param patientId - Patient ID
   * @param medicationId - Medication ID
   * @param userId - User ID administering the medication
   * @param notes - Optional administration notes
   * @returns Promise resolving to atomic response with caseEntry
   */
  static async administerMedicationAtomic(
    patientId: string,
    medicationId: string,
    userId: string,
    notes?: string
  ): Promise<any> {
    try {
      const response = await new MedicationService().fetchFromBackend(
        `/atomic/patients/${patientId}/medications/${medicationId}/administer`,
        {
          method: 'POST',
          body: JSON.stringify({
            administeredBy: userId,
            notes: notes || `Medication administered`
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
   * Get available medication types
   * @returns Promise resolving to array of medication types
   */
  static async getMedicationTypes(): Promise<any[]> {
    return new MedicationService().getRecordTypes();
  }

  /**
   * Get medication history
   * @param patientId - Patient ID
   * @param medicationId - Optional specific medication ID
   * @returns Promise resolving to medication history
   */
  static async getMedicationHistory(patientId: string, medicationId?: string): Promise<any[]> {
    return new MedicationService().getRecordHistory(patientId, medicationId);
  }

  /**
   * Get medication timeline
   * @param patientId - Patient ID
   * @param hoursBack - Hours to look back (default: 24)
   * @returns Promise resolving to medication timeline
   */
  static async getMedicationTimeline(patientId: string, hoursBack: number = 24) {
    return new MedicationService().getRecordTimeline(patientId, hoursBack, 'startDate');
  }

  // ================================
  // LEGACY SUPPORT - Medication Correlation
  // ================================

  /**
   * Get medication-correlated vitals
   * @param patientId - Patient ID
   * @param medicationId - Medication ID
   * @param hoursBack - Hours to look back (default: 24)
   * @returns Promise resolving to medication and vitals data
   */
  static async getMedicationCorrelatedVitals(
    patientId: string,
    medicationId: string,
    hoursBack: number = 24
  ): Promise<{ medication: any; vitals: any[] }> {
    try {
      const medications = await MedicationService.getPatientMedications(patientId);
      const medication = medications.find(med => med.id === medicationId);

      // Note: Vitals correlation would need a separate v2 vitals service
      return {
        medication: medication || null,
        vitals: []
      };
    } catch (error) {
      return { medication: null, vitals: [] };
    }
  }
}
