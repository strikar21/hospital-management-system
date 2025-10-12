/**
 * usePatientMedicalRecords - Generic hook for medical record operations
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data
 *
 * Purpose: Single source of truth for medical record hook patterns.
 * Eliminates 308+ lines of duplicated code across Medication, Investigation, and Therapy hooks.
 *
 * Generic Type Parameters:
 * @template T - The medical record type (medication | investigation | therapy)
 * @template FormState - The form state type (specific to each medical record type)
 *
 * @module usePatientMedicalRecords
 * @since 2.0.0
 */

import { useState, useCallback } from 'react';
import { patient, user, caseSheetEntry } from '../../types';
import { useDataRefresh } from '../useDataRefresh';
import { transformAndAddCaseEntry } from '../../utils/caseEntryTransformer';

/**
 * Configuration for medical record hook
 */
export interface MedicalRecordHookConfig<T, FormState> {
  /** Record type identifier (e.g., 'medications', 'investigations', 'therapy') */
  recordType: 'medications' | 'investigations' | 'therapy';

  /** Plural form for refresh hook (e.g., 'medications', 'investigations', 'therapies') */
  recordTypePlural: 'medications' | 'investigations' | 'therapies';

  /** Service methods for API calls */
  service: {
    /** Add new record method */
    add: (patientId: string, data: any, userId: string) => Promise<any>;
  };

  /** Default form state (initial values) */
  defaultFormState: FormState;

  /** Validate form before submission */
  validateForm: (formState: FormState) => boolean;

  /** Build record data from form state */
  buildRecordData: (formState: FormState, currentUser: user) => Omit<T, 'id'>;

  /** Form state to reset after successful add */
  resetFormState: FormState;

  /** Optional custom error handler for add operation */
  handleAddError?: (error: any, formState: FormState, currentUser: user) => void;
}

/**
 * Props interface for medical record hooks
 */
export interface UsePatientMedicalRecordsProps<T> {
  /** Current patient */
  patient: patient;

  /** Current user performing actions */
  currentUser: user;

  /** Medical records array */
  records: T[];

  /** Set records state */
  setRecords: React.Dispatch<React.SetStateAction<T[]>>;

  /** Add case sheet entry callback */
  addCaseSheetEntry: (entry: caseSheetEntry) => void;

  /** Set case entries state */
  setCaseEntries: React.Dispatch<React.SetStateAction<caseSheetEntry[]>>;

  /** Optional refresh all patient data callback */
  refreshPatientData?: () => Promise<void>;
}

/**
 * Return type for generic medical record hook
 */
export interface UsePatientMedicalRecordsReturn<FormState> {
  /** Form modal visibility state */
  isAdding: boolean;

  /** Set form modal visibility */
  setIsAdding: React.Dispatch<React.SetStateAction<boolean>>;

  /** Form data state */
  formState: FormState;

  /** Set form data */
  setFormState: React.Dispatch<React.SetStateAction<FormState>>;

  /** Loading state during add operation */
  adding: boolean;

  /** Add new record handler */
  handleAdd: () => Promise<void>;

  /** Cancel adding (reset form and hide modal) */
  handleCancel: () => void;

  /** Generic atomic operation wrapper */
  performAtomicOperation: (
    operation: () => Promise<any>,
    updateFn: (prev: any[], result: any) => any[],
    errorMessage?: string
  ) => Promise<void>;
}

/**
 * Generic hook for medical record operations
 *
 * Provides common functionality for all medical record hooks:
 * - Form state management
 * - Add record with atomic operation
 * - Generic atomic operation wrapper
 * - Optimistic update vs refreshPatientData pattern
 *
 * @example
 * ```typescript
 * const { handleAdd, performAtomicOperation, ... } = usePatientMedicalRecords<medication, MedicationFormState>(
 *   props,
 *   {
 *     recordType: 'medications',
 *     recordTypePlural: 'medications',
 *     service: { add: MedicationService.addMedication },
 *     defaultFormState: { name: '', dosage: '', frequency: '', route: 'PO', duration: '' },
 *     validateForm: (form) => !!(form.name && form.dosage && form.frequency && form.duration),
 *     buildRecordData: (form, user) => ({ ...form, prescribedBy: user.staffId }),
 *     resetFormState: { name: '', dosage: '', frequency: '', route: 'PO', duration: '' }
 *   }
 * );
 * ```
 */
export function usePatientMedicalRecords<T, FormState = any>(
  props: UsePatientMedicalRecordsProps<T>,
  config: MedicalRecordHookConfig<T, FormState>
): UsePatientMedicalRecordsReturn<FormState> {

  const {
    patient,
    currentUser,
    records,
    setRecords,
    addCaseSheetEntry,
    setCaseEntries,
    refreshPatientData
  } = props;

  const {
    recordType,
    recordTypePlural,
    service,
    defaultFormState,
    validateForm,
    buildRecordData,
    resetFormState,
    handleAddError
  } = config;

  // ================================
  // STATE MANAGEMENT
  // ================================

  // Form modal visibility
  const [isAdding, setIsAdding] = useState(false);

  // Form data
  const [formState, setFormState] = useState<FormState>(defaultFormState);

  // Loading state during add operation
  const [adding, setAdding] = useState(false);

  // Initialize data refresh hook
  const refreshHook = useDataRefresh(patient.id);
  const refreshRecords = (refreshHook as any)[`refresh${recordTypePlural.charAt(0).toUpperCase() + recordTypePlural.slice(1)}`];
  const refreshCaseEntries = refreshHook.refreshCaseEntries;

  // ================================
  // GENERIC ADD RECORD HANDLER
  // ================================

  /**
   * Add new medical record with atomic operation
   * Handles validation, API call, state update, and case entry creation
   */
  const handleAdd = useCallback(async () => {
    // Prevent double submission
    if (adding) return;

    // Validate form
    if (!validateForm(formState)) return;

    setAdding(true);
    try {
      // Build record data from form state
      const recordData = buildRecordData(formState, currentUser);

      // Call service layer with atomic operation
      const result = await service.add(patient.id, recordData, currentUser.id);

      if (result && result.success) {
        // Check if refreshPatientData callback provided
        if (refreshPatientData) {
          // Option 1: Refresh all patient data (preferred for consistency)
          await refreshPatientData();
        } else {
          // Option 2: Optimistic update (fallback)
          const newRecord = result.medicalRecord;
          setRecords(prev => [...prev, newRecord]);

          // Add case sheet entry from atomic result
          transformAndAddCaseEntry(result, addCaseSheetEntry);
        }

        // Reset form state
        setFormState(resetFormState);
        setIsAdding(false);
      } else {
        throw new Error('Atomic operation failed');
      }
    } catch (error: any) {
      // Use custom error handler if provided, otherwise default
      if (handleAddError) {
        handleAddError(error, formState, currentUser);
      } else {
        // Default error handling
        const errorMessage = error?.response?.data?.detail ||
                            error?.response?.data?.message ||
                            error?.message ||
                            'Unknown error occurred';
        alert(`❌ Failed to add ${recordType.slice(0, -1)}.\n\nError: ${errorMessage}\n\nPlease try again.`);
      }
    } finally {
      setAdding(false);
    }
  }, [adding, formState, validateForm, buildRecordData, currentUser, service, patient.id, refreshPatientData, setRecords, addCaseSheetEntry, resetFormState, recordType, handleAddError]);

  // ================================
  // GENERIC CANCEL HANDLER
  // ================================

  /**
   * Cancel adding record - reset form and hide modal
   */
  const handleCancel = useCallback(() => {
    setIsAdding(false);
    setFormState(resetFormState);
  }, [resetFormState]);

  // ================================
  // GENERIC ATOMIC OPERATION WRAPPER
  // ================================

  /**
   * Generic atomic operation wrapper
   * Handles refreshPatientData vs optimistic update pattern
   *
   * @param operation - Async operation that returns atomic result {success, medicalRecord, caseEntry}
   * @param updateFn - Function to update records array (prev, result) => newArray
   * @param errorMessage - Optional custom error message
   */
  const performAtomicOperation = useCallback(async (
    operation: () => Promise<any>,
    updateFn: (prev: T[], result: any) => T[],
    errorMessage?: string
  ) => {
    try {
      const result = await operation();

      if (result && result.success) {
        // Check if refreshPatientData callback provided
        if (refreshPatientData) {
          // Option 1: Refresh all patient data (preferred)
          await refreshPatientData();
        } else {
          // Option 2: Optimistic update (fallback)
          setRecords(prev => updateFn(prev, result));

          // Add case sheet entry from atomic result
          transformAndAddCaseEntry(result, addCaseSheetEntry);
        }
      } else {
        throw new Error('Atomic operation failed');
      }
    } catch (error) {
      const message = errorMessage || `Failed to perform ${recordType.slice(0, -1)} operation`;
      alert(`❌ ${message}: ${(error as Error).message}`);
      throw error;  // Re-throw for caller to handle if needed
    }
  }, [refreshPatientData, setRecords, addCaseSheetEntry, recordType]);

  // ================================
  // RETURN INTERFACE
  // ================================

  return {
    // Form state
    isAdding,
    setIsAdding,
    formState,
    setFormState,
    adding,

    // Generic handlers
    handleAdd,
    handleCancel,

    // Generic atomic operation wrapper
    performAtomicOperation
  };
}
