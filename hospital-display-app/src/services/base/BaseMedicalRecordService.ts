/**
 * BaseMedicalRecordService - Generic medical record CRUD operations
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data
 *
 * Purpose: Single source of truth for medical record operations.
 * Eliminates 850+ lines of duplicated code across Medication, Investigation, and Therapy services.
 *
 * Generic Type Parameters:
 * @template T - The medical record type (medication | investigation | therapy)
 *
 * Subclass Requirements:
 * - Must implement getConfig() to return record type configuration
 * - Can override transformAddPayload() for type-specific field mapping
 * - Can add type-specific methods as needed
 *
 * @module BaseMedicalRecordService
 * @since 2.0.0
 */

import { BaseService } from '../BaseService';

/**
 * Configuration for medical record type
 */
export interface MedicalRecordConfig {
  /** API endpoint base (e.g., 'medications', 'investigations', 'therapy') */
  recordType: string;
  /** Singular form for messages (e.g., 'medication', 'investigation', 'therapy') */
  recordTypeSingular: string;
  /** Plural form for response parsing (e.g., 'medications', 'investigations', 'therapy') */
  recordTypePlural: string;
}

/**
 * Abstract base class for medical record services
 *
 * Provides generic CRUD operations for medical records (medications, investigations, therapies).
 * Subclasses must implement getConfig() and can override methods for type-specific behavior.
 *
 * @example
 * ```typescript
 * export class MedicationService extends BaseMedicalRecordService<medication> {
 *   protected getConfig(): MedicalRecordConfig {
 *     return {
 *       recordType: 'medications',
 *       recordTypeSingular: 'medication',
 *       recordTypePlural: 'medications'
 *     };
 *   }
 * }
 * ```
 */
export abstract class BaseMedicalRecordService<T> extends BaseService {

  // ================================
  // ABSTRACT CONFIGURATION
  // ================================

  /**
   * Get configuration for this record type
   * Must be implemented by subclasses
   * @returns Record type configuration
   */
  protected abstract getConfig(): MedicalRecordConfig;

  // ================================
  // INSTANCE WRAPPER FOR STATIC METHODS
  // ================================

  /**
   * Instance wrapper for static fetchFromBackend method
   * Allows instance methods to call the static BaseService.fetchFromBackend
   */
  protected async fetchFromBackend(endpoint: string, options: RequestInit = {}): Promise<any> {
    return (this.constructor as typeof BaseService).fetchFromBackend(endpoint, options);
  }

  // ================================
  // RESPONSE HANDLING
  // ================================

  /**
   * Parse V2 API response - handles multiple response formats
   *
   * The backend may return records in different formats:
   * - { medications: [...] }
   * - { investigations: [...] }
   * - { therapy: [...] }
   * - { sessions: [...] }
   * - { data: [...] }
   * - [...]
   *
   * @param response - Raw API response
   * @returns Array of records
   */
  protected handleV2Response(response: any): T[] {
    if (!response) {
      return [];
    }

    const config = this.getConfig();

    // Check for type-specific field (medications, investigations, therapy)
    if (response[config.recordTypePlural]) {
      return response[config.recordTypePlural];
    }

    // Check for generic data field
    if (response.data) {
      return response.data;
    }

    // Check for sessions field (therapies)
    if (response.sessions) {
      return response.sessions;
    }

    // Return as array or empty
    return Array.isArray(response) ? response : [];
  }

  // ================================
  // CRUD OPERATIONS
  // ================================

  /**
   * Get all records for a patient
   *
   * @param patientId - Patient ID
   * @returns Promise resolving to array of records
   *
   * @example
   * ```typescript
   * const medications = await MedicationService.getPatientMedications('P123');
   * ```
   */
  async getPatientRecords(patientId: string): Promise<T[]> {
    const config = this.getConfig();

    try {
      const response = await this.fetchFromBackend(
        `/${config.recordType}/patient/${patientId}`
      );

      return this.handleV2Response(response);
    } catch (error) {
      console.error(`Error fetching patient ${config.recordTypePlural}:`, error);
      return [];
    }
  }

  /**
   * Get active/pending records for a patient
   *
   * @param patientId - Patient ID
   * @param statusFilter - Status to filter by (default: 'active')
   * @returns Promise resolving to filtered records
   *
   * @example
   * ```typescript
   * const activeMeds = await service.getActiveRecords('P123', 'active');
   * const pendingTests = await service.getActiveRecords('P123', 'pending');
   * ```
   */
  async getActiveRecords(patientId: string, statusFilter: string = 'active'): Promise<T[]> {
    const config = this.getConfig();

    try {
      const response = await this.fetchFromBackend(
        `/${config.recordType}/patient/${patientId}/${statusFilter}`
      );

      return this.handleV2Response(response);
    } catch (error) {
      console.error(`Error fetching ${statusFilter} ${config.recordTypePlural}:`, error);
      return [];
    }
  }

  /**
   * Add new medical record atomically
   *
   * Creates record and case entry in single transaction.
   * Subclasses can override transformAddPayload() for type-specific field mapping.
   *
   * @param patientId - Patient ID
   * @param recordData - Record data to create
   * @param userId - User ID performing the action
   * @returns Promise resolving to atomic response {success, medicalRecord, caseEntry}
   *
   * @example
   * ```typescript
   * const result = await service.addRecord('P123', medicationData, 'DOC001');
   * if (result?.success) {
   *   console.log('Created:', result.medicalRecord);
   * }
   * ```
   */
  async addRecord(patientId: string, recordData: any, userId: string): Promise<any> {
    const config = this.getConfig();

    try {
      // Call type-specific payload transformer (can be overridden)
      const payload = this.transformAddPayload(recordData, userId);

      const response = await this.fetchFromBackend(
        `/atomic/patients/${patientId}/${config.recordType}?performedBy=${userId}`,
        {
          method: 'POST',
          body: JSON.stringify(payload)
        }
      );

      return response;
    } catch (error) {
      console.error(`Error adding ${config.recordTypeSingular}:`, error);
      return null;
    }
  }

  /**
   * Transform add payload - override in subclasses for type-specific logic
   *
   * Default implementation returns data as-is.
   * Subclasses can override to map field names or apply transformations.
   *
   * @param recordData - Raw record data from form
   * @param userId - User ID
   * @returns Transformed payload for API
   *
   * @example
   * ```typescript
   * // In MedicationService
   * protected transformAddPayload(medication: any, userId: string): any {
   *   return {
   *     ...medication,
   *     route: this.mapRoute(medication.route) // Type-specific transformation
   *   };
   * }
   * ```
   */
  protected transformAddPayload(recordData: any, userId: string): any {
    // Default implementation - subclasses override for specific field mapping
    return recordData;
  }

  /**
   * Update record status
   *
   * @param recordId - Record ID
   * @param status - New status
   * @param userId - User ID performing the action
   * @returns Promise resolving to success boolean
   *
   * @example
   * ```typescript
   * const success = await service.updateRecordStatus('MED123', 'discontinued', 'DOC001');
   * ```
   */
  async updateRecordStatus(recordId: string, status: string, userId: string): Promise<boolean> {
    const config = this.getConfig();

    try {
      await this.fetchFromBackend(
        `/${config.recordType}/${recordId}/status`,
        {
          method: 'PUT',
          body: JSON.stringify({
            status,
            modifiedBy: userId,
            modifiedAt: new Date().toISOString()
          })
        }
      );

      return true;
    } catch (error) {
      console.error(`Error updating ${config.recordTypeSingular} status:`, error);
      return false;
    }
  }

  // ================================
  // TYPE OPERATIONS
  // ================================

  /**
   * Get available record types
   *
   * @returns Promise resolving to array of type definitions
   *
   * @example
   * ```typescript
   * const types = await service.getRecordTypes();
   * // Returns: ['Oral', 'IV', 'IM', ...] or ['Lab', 'Radiology', ...]
   * ```
   */
  async getRecordTypes(): Promise<any[]> {
    const config = this.getConfig();

    try {
      const response = await this.fetchFromBackend(`/${config.recordType}/types`);
      return this.handleV2Response(response);
    } catch (error) {
      console.error(`Error fetching ${config.recordTypeSingular} types:`, error);
      return [];
    }
  }

  // ================================
  // HISTORY & TIMELINE
  // ================================

  /**
   * Get record history
   *
   * @param patientId - Patient ID
   * @param recordId - Optional specific record ID
   * @returns Promise resolving to history records
   *
   * @example
   * ```typescript
   * // Get all medication history
   * const allHistory = await service.getRecordHistory('P123');
   *
   * // Get specific medication history
   * const medHistory = await service.getRecordHistory('P123', 'MED123');
   * ```
   */
  async getRecordHistory(patientId: string, recordId?: string): Promise<T[]> {
    try {
      const records = await this.getPatientRecords(patientId);

      if (recordId) {
        return records.filter((rec: any) => rec.id === recordId);
      }

      return records;
    } catch (error) {
      console.error(`Error fetching record history:`, error);
      return [];
    }
  }

  /**
   * Get record timeline with time filtering
   *
   * @param patientId - Patient ID
   * @param hoursBack - Hours to look back (default: 24)
   * @param timeField - Field name for timestamp (default: 'createdAt')
   * @returns Promise resolving to filtered and sorted records
   *
   * @example
   * ```typescript
   * // Last 24 hours
   * const recent = await service.getRecordTimeline('P123');
   *
   * // Last 48 hours, sorted by start date
   * const timeline = await service.getRecordTimeline('P123', 48, 'startDate');
   * ```
   */
  async getRecordTimeline(
    patientId: string,
    hoursBack: number = 24,
    timeField: string = 'createdAt'
  ): Promise<T[]> {
    try {
      const records = await this.getPatientRecords(patientId);

      const cutoff = new Date();
      cutoff.setHours(cutoff.getHours() - hoursBack);

      return records
        .filter((rec: any) =>
          !rec[timeField] || new Date(rec[timeField]) >= cutoff
        )
        .sort((a: any, b: any) => {
          const dateA = new Date(a[timeField] || 0);
          const dateB = new Date(b[timeField] || 0);
          return dateB.getTime() - dateA.getTime(); // Newest first
        });
    } catch (error) {
      console.error(`Error fetching record timeline:`, error);
      return [];
    }
  }

  /**
   * Get records by status
   *
   * @param patientId - Patient ID
   * @param status - Status to filter by
   * @returns Promise resolving to filtered records
   *
   * @example
   * ```typescript
   * const completed = await service.getRecordsByStatus('P123', 'completed');
   * ```
   */
  async getRecordsByStatus(patientId: string, status: string): Promise<T[]> {
    try {
      // Try status-specific endpoint first
      if (status === 'active' || status === 'pending') {
        return await this.getActiveRecords(patientId, status);
      }

      // Fallback: get all and filter
      const records = await this.getPatientRecords(patientId);
      return records.filter((rec: any) => rec.status === status);
    } catch (error) {
      console.error(`Error fetching records with status ${status}:`, error);
      return [];
    }
  }

  // ================================
  // VALIDATION
  // ================================

  /**
   * Validate record data
   *
   * @param record - Record to validate
   * @param requiredFields - Array of required field names
   * @returns true if valid, false otherwise
   *
   * @example
   * ```typescript
   * const isValid = service.validateRecord(medication, ['name', 'dosage', 'frequency']);
   * ```
   */
  protected validateRecord(record: any, requiredFields: string[]): boolean {
    if (!record || typeof record !== 'object') {
      return false;
    }

    return requiredFields.every(field =>
      record[field] !== undefined &&
      record[field] !== null &&
      record[field] !== ''
    );
  }

  // ================================
  // STATIC FACTORY PATTERN
  // ================================

  /**
   * Create service instance - static factory method
   * Subclasses can use this to create instances without 'new'
   *
   * @returns New service instance
   *
   * @example
   * ```typescript
   * const medications = await MedicationService.instance().getPatientRecords(patientId);
   * ```
   */
  protected static instance<T extends BaseMedicalRecordService<any>>(): T {
    return new (this as any)();
  }

  // ================================
  // GENERIC UTILITY METHODS
  // ================================

  /**
   * Format JSON data for display
   * Generic utility for formatting complex data structures
   *
   * @param data - Data to format
   * @param fallback - Fallback string if formatting fails
   * @returns Formatted string
   */
  static formatDataForDisplay(data: any, fallback: string = 'No data available'): string {
    try {
      if (!data) return fallback;

      if (typeof data === 'string') {
        return data;
      }

      if (typeof data === 'object') {
        return JSON.stringify(data, null, 2);
      }

      return String(data);
    } catch (error) {
      return fallback;
    }
  }

  /**
   * Format duration in minutes to human-readable string
   * Generic utility for duration formatting
   *
   * @param minutes - Duration in minutes
   * @returns Formatted duration string
   */
  static formatDuration(minutes: number): string {
    try {
      if (!minutes || minutes < 0) return '0 minutes';

      if (minutes < 60) {
        return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
      }

      const hours = Math.floor(minutes / 60);
      const remainingMinutes = minutes % 60;

      if (remainingMinutes === 0) {
        return `${hours} hour${hours !== 1 ? 's' : ''}`;
      }

      return `${hours} hour${hours !== 1 ? 's' : ''} ${remainingMinutes} minute${remainingMinutes !== 1 ? 's' : ''}`;
    } catch (error) {
      return 'Invalid duration';
    }
  }

  /**
   * Calculate progress percentage
   * Generic utility for calculating completion percentage
   *
   * @param completed - Number of completed items
   * @param total - Total number of items
   * @returns Progress percentage (0-100)
   */
  static calculateProgress(completed: number, total: number): number {
    try {
      if (!total || total <= 0) {
        return 0;
      }

      const completedCount = completed || 0;
      return Math.min(100, Math.round((completedCount / total) * 100));
    } catch (error) {
      return 0;
    }
  }

  /**
   * Capitalize first letter of string
   * Generic utility for string formatting
   *
   * @param str - String to capitalize
   * @returns Capitalized string
   */
  static capitalize(str: string): string {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
  }
}
