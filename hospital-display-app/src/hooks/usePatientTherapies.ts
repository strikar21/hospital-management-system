/**
 * usePatientTherapies - Therapy-specific hook (Refactored)
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data
 *
 * Extends generic usePatientMedicalRecords hook with therapy-specific operations.
 *
 * @module usePatientTherapies
 * @since 2.0.0
 */

import { useState, useCallback } from 'react';
import { patient, user, therapy, caseSheetEntry } from '../types';
import { TherapyService } from '../services';
import { NewTherapy } from '../components/PatientTherapies/AddTherapyForm';
import {
  usePatientMedicalRecords,
  UsePatientMedicalRecordsProps
} from './base/usePatientMedicalRecords';

/** Props interface for therapy hook */
interface UsePatientTherapiesProps extends Omit<UsePatientMedicalRecordsProps<therapy>, 'records' | 'setRecords'> {
  therapies: therapy[];
  setTherapies: React.Dispatch<React.SetStateAction<therapy[]>>;
  refreshPatientData?: () => Promise<void>;
}

/**
 * Therapy-specific hook
 * Provides generic CRUD operations + therapy-specific features
 */
export const usePatientTherapies = (props: UsePatientTherapiesProps) => {
  const {
    therapies,
    setTherapies,
    refreshPatientData,
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
  } = usePatientMedicalRecords<therapy, NewTherapy>(
    {
      ...baseProps,
      records: therapies,
      setRecords: setTherapies,
      refreshPatientData
    },
    {
      recordType: 'therapy',
      recordTypePlural: 'therapies',
      service: {
        add: TherapyService.addTherapy
      },
      defaultFormState: {
        type: 'physiotherapy',
        description: '',
        frequency: '',
        duration: ''
      },
      validateForm: (form) => !!form.description,
      buildRecordData: (form, user) => ({
        type: form.type,
        name: `${form.type.charAt(0).toUpperCase() + form.type.slice(1)} Therapy`,
        description: form.description,
        frequency: form.frequency,
        duration: form.duration,
        prescribedBy: user.staffId,
        status: 'active',
        startDate: new Date().toISOString(),
        sessions: [],
        canEdit: true,
        createdAt: new Date().toISOString()
      } as any as Omit<therapy, 'id'>),
      resetFormState: {
        type: 'physiotherapy',
        description: '',
        frequency: '',
        duration: ''
      }
    }
  );

  // ================================
  // THERAPY-SPECIFIC OPERATIONS
  // ================================

  /**
   * Add therapy session using atomic operation
   * Therapy-specific operation
   */
  const handleAddTherapySession = useCallback(async (therapy: therapy) => {
    const duration = window.prompt('Session duration (minutes):');
    const notes = window.prompt('Session notes:');

    if (duration && notes) {
      try {
        await performAtomicOperation(
          () => TherapyService.addTherapySessionAtomic(
            props.patient.id,
            therapy.id,
            parseInt(duration),
            notes,
            props.currentUser.id
          ),
          (prev, result) => prev.map(t =>
            t.id === therapy.id ? result.medicalRecord : t
          ),
          `Failed to record therapy session`
        );

        alert(`✅ Therapy session recorded successfully!`);
      } catch (error) {
        // Error already handled by performAtomicOperation
      }
    }
  }, [performAtomicOperation, props.patient.id, props.currentUser.id]);

  /**
   * Complete therapy using atomic operation
   * Therapy-specific operation
   */
  const handleCompleteTherapy = useCallback(async (therapy: therapy) => {
    if (window.confirm('Mark this therapy as completed?')) {
      try {
        await performAtomicOperation(
          () => TherapyService.completeTherapyAtomic(
            props.patient.id,
            therapy.id,
            props.currentUser.id
          ),
          (prev, result) => prev.map(t =>
            t.id === therapy.id ? result.medicalRecord : t
          ),
          `Failed to complete therapy`
        );
      } catch (error) {
        // Error already handled by performAtomicOperation
      }
    }
  }, [performAtomicOperation, props.patient.id, props.currentUser.id]);

  /**
   * Cancel therapy using atomic operation
   * Therapy-specific operation
   */
  const handleCancelTherapy = useCallback(async (therapy: therapy) => {
    if (window.confirm('Cancel this therapy?')) {
      try {
        await performAtomicOperation(
          () => TherapyService.cancelTherapyAtomic(
            props.patient.id,
            therapy.id,
            props.currentUser.id
          ),
          (prev, result) => prev.map(t =>
            t.id === therapy.id ? result.medicalRecord : t
          ),
          `Failed to cancel therapy`
        );
      } catch (error) {
        // Error already handled by performAtomicOperation
      }
    }
  }, [performAtomicOperation, props.patient.id, props.currentUser.id]);

  // ================================
  // RETURN INTERFACE (Backward Compatible)
  // ================================

  return {
    // Generic state (aliased for backward compatibility)
    isAddingTherapy: isAdding,
    setIsAddingTherapy: setIsAdding,
    newTherapy: formState,
    setNewTherapy: setFormState,
    addingTherapy: adding,

    // Generic handlers (aliased for backward compatibility)
    handleAddTherapy: handleAdd,
    handleCancelAddTherapy: handleCancel,

    // Therapy-specific handlers
    handleAddTherapySession,
    handleCompleteTherapy,
    handleCancelTherapy
  };
};
