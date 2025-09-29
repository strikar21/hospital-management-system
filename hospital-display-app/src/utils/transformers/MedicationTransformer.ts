/**
 * MedicationTransformer - Medication data transformation utilities
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Handles pharmaceutical data transformation with regulatory compliance
 */

import { BaseTransformer } from './BaseTransformer';

export class MedicationTransformer extends BaseTransformer {

  // ================================
  // MEDICATION TRANSFORMATION
  // ================================

  /**
   * Transform medication data - CAMELCASE ONLY
   * Pharmaceutical-grade medication data transformation with compliance
   */
  static transformMedication(data: any, staffMapping?: { [key: string]: string }): any {
    if (!data) return null;

    try {
      // Validate required medication fields
      const requiredFields = ['name', 'dosage'];
      if (!this.validateMedicalData(data, requiredFields)) {
        console.warn('Medication data missing required fields:', data);
      }

      // Transform object keys to camelCase
      let transformed = this.transformObjectKeys(data);

      // Apply medication-specific defaults
      transformed = this.applyMedicationDefaults(transformed);

      // Add resolved staff names
      transformed = this.addResolvedNames(transformed, staffMapping);

      // Add edit permissions based on medical compliance window
      transformed.canEdit = this.canEditMedicalRecord(transformed.createdAt);

      // Add medication administration tracking
      transformed = this.addAdministrationTracking(transformed);

      // Apply pharmaceutical data sanitization
      transformed = this.sanitizeMedicalData(transformed, ['prescriptionId']);

      return transformed;
    } catch (error) {
      console.error('Error transforming medication data:', error);
      return data;
    }
  }

  /**
   * Apply medication-specific defaults and validation
   */
  private static applyMedicationDefaults(data: any): any {
    if (!data || typeof data !== 'object') return data;

    const withDefaults = { ...data };

    // Ensure medication name is properly formatted
    if (withDefaults.name) {
      withDefaults.medicationName = withDefaults.medicationName || withDefaults.name;
    }

    // Ensure duration field is never empty
    if (!withDefaults.duration || withDefaults.duration === '') {
      withDefaults.duration = 'Not specified';
    }

    // Ensure frequency field is never empty
    if (!withDefaults.frequency || withDefaults.frequency === '') {
      withDefaults.frequency = 'As needed';
    }

    // Ensure route field has valid value
    if (!withDefaults.route) {
      withDefaults.route = 'Oral';
    }

    // Ensure status field has valid value
    if (!withDefaults.status) {
      withDefaults.status = 'active';
    }

    // Format timestamps properly
    if (withDefaults.prescribedAt && typeof withDefaults.prescribedAt === 'string') {
      try {
        withDefaults.prescribedAt = new Date(withDefaults.prescribedAt).toISOString();
      } catch (error) {
        withDefaults.prescribedAt = new Date().toISOString();
      }
    }

    if (withDefaults.startDate && typeof withDefaults.startDate === 'string') {
      try {
        withDefaults.startDate = new Date(withDefaults.startDate).toISOString();
      } catch (error) {
        withDefaults.startDate = new Date().toISOString();
      }
    }

    // Set creation timestamp if not present
    if (!withDefaults.createdAt) {
      withDefaults.createdAt = new Date().toISOString();
    }

    return withDefaults;
  }

  /**
   * Add medication administration tracking
   */
  private static addAdministrationTracking(data: any): any {
    if (!data || typeof data !== 'object') return data;

    const withTracking = { ...data };

    // Add administration status
    withTracking.administrationStatus = this.calculateAdministrationStatus(withTracking);

    // Add next dose information
    withTracking.nextDoseTime = this.calculateNextDoseTime(withTracking);

    // Add adherence tracking
    withTracking.adherenceRate = this.calculateAdherenceRate(withTracking);

    return withTracking;
  }

  /**
   * Calculate medication administration status
   */
  private static calculateAdministrationStatus(medication: any): string {
    if (!medication.startDate) return 'not-started';
    if (medication.discontinuedAt) return 'discontinued';
    if (medication.endDate && new Date(medication.endDate) < new Date()) return 'completed';

    const now = new Date();
    const startDate = new Date(medication.startDate);

    if (startDate > now) return 'scheduled';
    if (medication.status === 'active') return 'active';

    return 'unknown';
  }

  /**
   * Calculate next dose time based on frequency
   */
  private static calculateNextDoseTime(medication: any): string | null {
    if (medication.administrationStatus !== 'active') return null;
    if (!medication.frequency) return null;

    // Simple frequency parsing - could be enhanced with more sophisticated logic
    const frequencyMap: { [key: string]: number } = {
      'once daily': 24,
      'twice daily': 12,
      'three times daily': 8,
      'four times daily': 6,
      'every 4 hours': 4,
      'every 6 hours': 6,
      'every 8 hours': 8,
      'every 12 hours': 12,
      'as needed': 0
    };

    const intervalHours = frequencyMap[medication.frequency.toLowerCase()] || 0;
    if (intervalHours === 0) return null;

    const lastAdministered = medication.lastAdministeredAt ?
      new Date(medication.lastAdministeredAt) : new Date(medication.startDate);

    const nextDose = new Date(lastAdministered.getTime() + (intervalHours * 60 * 60 * 1000));

    return nextDose.toISOString();
  }

  /**
   * Calculate medication adherence rate
   */
  private static calculateAdherenceRate(medication: any): number {
    // Placeholder for adherence calculation
    // In a real system, this would analyze administration records
    return medication.adherenceRate || 0;
  }

  /**
   * Transform medication array data
   */
  static transformMedicationArray(data: any[], staffMapping?: { [key: string]: string }): any[] {
    if (!Array.isArray(data)) return [];

    return data
      .map(medication => this.transformMedication(medication, staffMapping))
      .filter(medication => medication !== null) // Remove failed transformations
      .sort((a, b) => {
        // Sort by priority: active medications first, then by start date
        if (a.status === 'active' && b.status !== 'active') return -1;
        if (b.status === 'active' && a.status !== 'active') return 1;
        return new Date(b.startDate || 0).getTime() - new Date(a.startDate || 0).getTime();
      });
  }

  /**
   * Transform medication for prescription writing
   */
  static transformMedicationForPrescription(data: any, staffMapping?: { [key: string]: string }): any {
    if (!data) return null;

    const medication = this.transformMedication(data, staffMapping);
    if (!medication) return null;

    // Add prescription-specific validation
    const prescriptionRequiredFields = ['name', 'dosage', 'frequency', 'duration', 'prescribedBy'];
    if (!this.validateMedicalData(medication, prescriptionRequiredFields)) {
      throw new Error('Incomplete prescription data - missing required fields');
    }

    return {
      ...medication,
      prescriptionReady: true,
      prescribedAt: medication.prescribedAt || new Date().toISOString()
    };
  }

  /**
   * Transform medication for administration record
   */
  static transformMedicationForAdministration(data: any, administrationData: any): any {
    if (!data) return null;

    const medication = this.transformMedication(data);
    if (!medication) return null;

    return {
      ...medication,
      administeredAt: administrationData.administeredAt || new Date().toISOString(),
      administeredBy: administrationData.administeredBy,
      administeredByName: administrationData.administeredByName,
      administrationNotes: administrationData.notes || '',
      actualDosage: administrationData.dosage || medication.dosage,
      administrationRoute: administrationData.route || medication.route,
      administrationStatus: 'administered'
    };
  }

  /**
   * Transform medication summary for dashboard
   */
  static transformMedicationSummary(medications: any[], staffMapping?: { [key: string]: string }): any {
    const transformedMedications = this.transformMedicationArray(medications, staffMapping);

    const activeMedications = transformedMedications.filter(med => med.status === 'active');
    const dueMedications = activeMedications.filter(med =>
      med.nextDoseTime && new Date(med.nextDoseTime) <= new Date()
    );
    const overdueMedications = activeMedications.filter(med =>
      med.nextDoseTime && new Date(med.nextDoseTime) < new Date(Date.now() - 60 * 60 * 1000)
    );

    return {
      totalMedications: transformedMedications.length,
      activeMedications: activeMedications.length,
      dueMedications: dueMedications.length,
      overdueMedications: overdueMedications.length,
      medications: transformedMedications,
      dueMedicationsList: dueMedications,
      overdueMedicationsList: overdueMedications,
      lastUpdated: new Date().toISOString()
    };
  }

  /**
   * Validate medication interaction potential
   */
  static validateMedicationInteractions(medications: any[]): any {
    // Placeholder for drug interaction checking
    // In a real system, this would check against a drug interaction database
    const warnings: string[] = [];
    const interactions: any[] = [];

    // Basic interaction detection logic would go here
    return {
      hasInteractions: interactions.length > 0,
      interactions,
      warnings,
      safeToAdminister: interactions.length === 0
    };
  }
}