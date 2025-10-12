/**
 * usePatientMedications - Medication-specific hook (Refactored)
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data
 *
 * Extends generic usePatientMedicalRecords hook with medication-specific operations.
 *
 * @module usePatientMedications
 * @since 2.0.0
 */

import { useState, useCallback } from 'react';
import { medication, patient, user, caseSheetEntry } from '../types';
import { MedicationService } from '../services';
import {
  usePatientMedicalRecords,
  UsePatientMedicalRecordsProps
} from './base/usePatientMedicalRecords';

/** Medication form state type */
interface MedicationFormState {
  name: string;
  dosage: string;
  frequency: string;
  route: string;
  duration: string;
}

/** Props interface for medication hook */
interface UsePatientMedicationsProps extends Omit<UsePatientMedicalRecordsProps<medication>, 'records' | 'setRecords'> {
  medications: medication[];
  setMedications: React.Dispatch<React.SetStateAction<medication[]>>;
}

/**
 * Medication-specific hook
 * Provides generic CRUD operations + medication-specific features
 */
export const usePatientMedications = (props: UsePatientMedicationsProps) => {
  const {
    medications,
    setMedications,
    ...baseProps
  } = props;

  // ================================
  // USE GENERIC HOOK
  // ================================

  const {
    isAdding,
    setIsAdding,
    formState,
    setFormState,
    adding,
    handleAdd,
    handleCancel,
    performAtomicOperation
  } = usePatientMedicalRecords<medication, MedicationFormState>(
    {
      ...baseProps,
      records: medications,
      setRecords: setMedications
    },
    {
      recordType: 'medications',
      recordTypePlural: 'medications',
      service: {
        add: MedicationService.addMedication
      },
      defaultFormState: {
        name: '',
        dosage: '',
        frequency: '',
        route: 'PO',
        duration: ''
      },
      validateForm: (form) => !!(form.name && form.dosage && form.frequency && form.duration),
      buildRecordData: (form, user) => ({
        name: form.name,
        dosage: form.dosage,
        frequency: form.frequency,
        route: form.route,
        duration: form.duration,
        status: 'active',
        startDate: new Date().toISOString(),
        prescribedBy: user.staffId,
        createdAt: new Date().toISOString(),
        canEdit: true
      } as Omit<medication, 'id'>),
      resetFormState: {
        name: '',
        dosage: '',
        frequency: '',
        route: 'PO',
        duration: ''
      },
      // Custom error handler for medication-specific FK violation messages
      handleAddError: (error: any, formState, currentUser) => {
        console.error('Add medication error:', error);

        const errorMessage = error?.response?.data?.detail ||
                            error?.response?.data?.message ||
                            error?.message ||
                            'Unknown error occurred';

        // Display user-friendly error messages based on backend FK violations
        if (errorMessage.includes('Patient') && errorMessage.includes('not found')) {
          alert('❌ Error: Patient not found.\n\nThe patient may have been discharged or the patient ID is invalid. Please refresh the page and try again.');
        } else if (errorMessage.includes('Prescriber') && errorMessage.includes('not found')) {
          alert(`❌ Error: Prescriber not found in staff directory.\n\nThe prescriber ID "${currentUser.staffId}" is not in the system. Please verify your staff credentials.`);
        } else if (errorMessage.includes('Creator') && errorMessage.includes('not found')) {
          alert('❌ Error: User account not found.\n\nYour user account may have been deactivated. Please contact an administrator.');
        } else if (errorMessage.includes('Duplicate medication')) {
          alert('❌ Error: Duplicate medication.\n\nThis medication may already be prescribed for this patient. Please check the medications list.');
        } else {
          alert(`❌ Failed to add medication.\n\nError: ${errorMessage}\n\nPlease try again or contact support if the issue persists.`);
        }
      }
    }
  );

  // ================================
  // MEDICATION-SPECIFIC OPERATIONS
  // ================================

  /**
   * Handle medication status change (active, discontinued, held)
   * Uses generic atomic operation wrapper
   */
  const handleMedicationStatusChange = useCallback(async (
    medicationId: string,
    status: 'active' | 'discontinued' | 'held'
  ) => {
    await performAtomicOperation(
      () => MedicationService.changeMedicationStatusAtomic(
        props.patient.id,
        medicationId,
        status,
        props.currentUser.id
      ),
      (prev, result) => prev.map(med =>
        med.id === medicationId ? result.medicalRecord : med
      ),
      `Failed to change medication status`
    );
  }, [performAtomicOperation, props.patient.id, props.currentUser.id]);

  /**
   * Handle medication administration
   * Uses generic atomic operation wrapper
   */
  const handleMedicationAdministration = useCallback(async (med: medication) => {
    try {
      await performAtomicOperation(
        () => MedicationService.administerMedicationAtomic(
          props.patient.id,
          med.id,
          props.currentUser.id,
          `Administered ${med.name} ${med.dosage} via ${med.route} route`
        ),
        (prev) => prev,  // No state change needed, just case entry
        `Failed to administer medication`
      );

      alert(`✅ ${med.name} ${med.dosage} administered successfully!\n\nTime: ${new Date().toLocaleTimeString()}\nAdministered by: ${props.currentUser.staffId}\n\nAdministration recorded in database and case sheet.`);
    } catch (error) {
      // Error already handled by performAtomicOperation
    }
  }, [performAtomicOperation, props.patient.id, props.currentUser]);

  // ================================
  // MEDICATION-SPECIFIC UTILITIES
  // ================================

  /**
   * Generate medication schedule times based on frequency
   * Medication-specific utility function
   */
  const generateScheduleTimes = useCallback((frequency: string) => {
    const freq = frequency.toLowerCase();
    let nextTimes: string[] = [];

    if (freq.includes('once daily')) nextTimes = ['08:00'];
    else if (freq.includes('twice daily')) nextTimes = ['08:00', '20:00'];
    else if (freq.includes('three times')) nextTimes = ['08:00', '14:00', '20:00'];
    else if (freq.includes('four times')) nextTimes = ['06:00', '12:00', '18:00', '22:00'];
    else if (freq.includes('every 8 hours')) nextTimes = ['06:00', '14:00', '22:00'];
    else if (freq.includes('every 6 hours')) nextTimes = ['06:00', '12:00', '18:00', '00:00'];

    const now = new Date();
    const currentTime = now.getHours() * 60 + now.getMinutes();
    const nextTime = nextTimes.find(time => {
      const [hours, minutes] = time.split(':').map(Number);
      return (hours * 60 + minutes) > currentTime;
    }) || nextTimes[0];

    return { nextTimes, nextTime };
  }, []);

  /**
   * Debounce utility for medication operations
   * Medication-specific utility function
   */
  const debounce = useCallback((func: (...args: any[]) => void, wait: number) => {
    let timeout: NodeJS.Timeout;
    return (...args: any[]) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => func(...args), wait);
    };
  }, []);

  // ================================
  // RETURN INTERFACE (Backward Compatible)
  // ================================

  return {
    // Generic state (aliased for backward compatibility)
    isAddingMedication: isAdding,
    setIsAddingMedication: setIsAdding,
    newMedication: formState,
    setNewMedication: setFormState,

    // Generic handlers (aliased for backward compatibility)
    handleAddMedication: handleAdd,

    // Medication-specific handlers
    handleMedicationStatusChange,
    handleMedicationAdministration,

    // Medication-specific utilities
    generateScheduleTimes,
    debounce
  };
};
