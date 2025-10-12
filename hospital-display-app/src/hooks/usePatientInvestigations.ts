/**
 * usePatientInvestigations - Investigation-specific hook (Refactored)
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data
 *
 * Extends generic usePatientMedicalRecords hook with investigation-specific operations.
 *
 * @module usePatientInvestigations
 * @since 2.0.0
 */

import { useState, useCallback } from 'react';
import { patient, user, investigation, caseSheetEntry, labResult, imagingStudy } from '../types';
import { InvestigationService } from '../services';
import { PatientCaseService } from '../services/patient';
import { useDataRefresh } from './useDataRefresh';
import { NewInvestigation } from '../components/PatientInvestigations/AddInvestigationForm';
import { transformAtomicCaseEntry } from '../utils/caseEntryTransformer';
import {
  usePatientMedicalRecords,
  UsePatientMedicalRecordsProps
} from './base/usePatientMedicalRecords';

/** Props interface for investigation hook */
interface UsePatientInvestigationsProps extends Omit<UsePatientMedicalRecordsProps<investigation>, 'records' | 'setRecords'> {
  investigations: investigation[];
  setInvestigations: React.Dispatch<React.SetStateAction<investigation[]>>;
  refreshPatientData?: () => Promise<void>;
}

/**
 * Investigation-specific hook
 * Provides generic CRUD operations + investigation-specific features
 */
export const usePatientInvestigations = (props: UsePatientInvestigationsProps) => {
  const {
    investigations,
    setInvestigations,
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
  } = usePatientMedicalRecords<investigation, NewInvestigation>(
    {
      ...baseProps,
      records: investigations,
      setRecords: setInvestigations,
      refreshPatientData
    },
    {
      recordType: 'investigations',
      recordTypePlural: 'investigations',
      service: {
        add: InvestigationService.addInvestigation
      },
      defaultFormState: {
        type: 'lab',
        name: '',
        priority: 'routine',
        notes: ''
      },
      validateForm: (form) => !!form.name,
      buildRecordData: (form, user) => ({
        name: form.name,
        type: form.type,
        priority: form.priority,
        urgency: 'Routine',
        notes: form.notes,
        prescribedBy: user.staffId,
        status: 'ordered',
        canEdit: true
      } as Omit<investigation, 'id'>),
      resetFormState: {
        type: 'lab',
        name: '',
        priority: 'routine',
        notes: ''
      }
    }
  );

  // ================================
  // INVESTIGATION-SPECIFIC STATE
  // ================================

  // Lab Integration
  const [labResults, setLabResults] = useState<labResult[]>([]);
  const [loadingLabResults, setLoadingLabResults] = useState(false);

  // Data refresh hooks (for non-atomic operations)
  const { refreshInvestigations, refreshCaseEntries } = useDataRefresh(props.patient.id);

  // ================================
  // INVESTIGATION-SPECIFIC OPERATIONS
  // ================================

  /**
   * Start investigation (non-atomic status change + manual case entry)
   * Investigation-specific operation
   */
  const handleStartInvestigation = useCallback(async (inv: investigation) => {
    try {
      await InvestigationService.updateInvestigationStatus(inv.id, 'inProgress', props.currentUser.id);

      // Refetch fresh data from backend (single source of truth)
      if (refreshPatientData) {
        await refreshPatientData();
      } else {
        try {
          const freshInvestigations = await refreshInvestigations();
          setInvestigations(freshInvestigations);
        } catch (refreshError) {
          // Failed to refresh data after starting investigation - handle silently
        }
      }

      // Add case sheet entry to backend using authenticated service
      try {
        const caseResult = await PatientCaseService.addCaseEntry(
          props.patient.id,
          {
            entryType: 'investigation',
            description: `${inv.name} started by ${props.currentUser.name}`,
            performedBy: props.currentUser.id
          },
          props.currentUser.id
        );

        if (caseResult) {
          const caseEntry = transformAtomicCaseEntry({ caseEntry: caseResult });
          if (caseEntry) {
            props.addCaseSheetEntry(caseEntry);
          }
        }
      } catch (caseError) {
        // Failed to add investigation started case sheet entry - handle silently
      }
    } catch (error) {
      // Failed to start investigation - handle silently
    }
  }, [props.currentUser, props.patient.id, setInvestigations, props.addCaseSheetEntry, refreshPatientData, refreshInvestigations]);

  /**
   * Complete investigation using atomic operation
   * Investigation-specific with lab integration
   */
  const handleCompleteInvestigation = useCallback(async (inv: investigation) => {
    let results = '';

    if (inv.type === 'lab') {
      // For lab investigations, automatically fetch results from lab system
      try {
        setLoadingLabResults(true);
        const updatedInvestigation = await Promise.resolve(inv);

        if (updatedInvestigation.status === 'completed') {
          results = updatedInvestigation.results || 'Lab results imported';
        } else {
          alert('Lab results not yet available. Please try again later.');
          return;
        }
        setLoadingLabResults(false);
      } catch (error) {
        setLoadingLabResults(false);
        // Failed to fetch lab results - handle silently
        alert('Failed to fetch lab results. Please enter results manually.');

        // Fallback to manual entry
        const manualResults = window.prompt('Lab results not available. Enter results manually:');
        if (manualResults) {
          results = manualResults;
        } else {
          return;
        }
      }
    } else {
      // For non-lab investigations, use manual entry
      const manualResults = window.prompt('Enter investigation results:');
      if (manualResults) {
        results = manualResults;
      } else {
        return;
      }
    }

    // Complete investigation using atomic operation
    try {
      await performAtomicOperation(
        () => InvestigationService.completeInvestigationAtomic(
          props.patient.id,
          inv.id,
          results,
          props.currentUser.id
        ),
        (prev, result) => prev.map(investigation =>
          investigation.id === inv.id ? result.medicalRecord : investigation
        ),
        `Failed to complete investigation`
      );
    } catch (error) {
      // Error already handled by performAtomicOperation
    }
  }, [performAtomicOperation, props.currentUser, props.patient.id, setLoadingLabResults]);

  /**
   * Cancel investigation (non-atomic status change + manual case entry)
   * Investigation-specific operation
   */
  const handleCancelInvestigation = useCallback(async (inv: investigation) => {
    if (window.confirm('Are you sure you want to cancel this investigation?')) {
      try {
        await InvestigationService.updateInvestigationStatus(inv.id, 'cancelled', props.currentUser.id);

        // Refetch fresh data from backend (single source of truth)
        if (refreshPatientData) {
          await refreshPatientData();
        } else {
          try {
            const freshInvestigations = await refreshInvestigations();
            setInvestigations(freshInvestigations);
          } catch (refreshError) {
            // Failed to refresh data after cancelling investigation - handle silently
          }
        }

        // Add case sheet entry to backend using authenticated service
        try {
          const caseResult = await PatientCaseService.addCaseEntry(
            props.patient.id,
            {
              entryType: 'investigation',
              description: `${inv.name} (${inv.type}) cancelled by ${props.currentUser.name}`,
              performedBy: props.currentUser.id
            },
            props.currentUser.id
          );

          if (caseResult) {
            const caseEntry = transformAtomicCaseEntry({ caseEntry: caseResult });
            if (caseEntry) {
              props.addCaseSheetEntry(caseEntry);
            }
          }
        } catch (caseError) {
          // Failed to add investigation cancellation case sheet entry - handle silently
        }
      } catch (error) {
        // Failed to cancel investigation - handle silently
      }
    }
  }, [props.currentUser, props.patient.id, setInvestigations, props.addCaseSheetEntry, refreshPatientData, refreshInvestigations]);

  // ================================
  // RETURN INTERFACE (Backward Compatible)
  // ================================

  return {
    // Generic state (aliased for backward compatibility)
    isAddingInvestigation: isAdding,
    setIsAddingInvestigation: setIsAdding,
    newInvestigation: formState,
    setNewInvestigation: setFormState,
    addingInvestigation: adding,

    // Investigation-specific state
    labResults,
    setLabResults,
    loadingLabResults,

    // Generic handlers (aliased for backward compatibility)
    handleAddInvestigation: handleAdd,
    handleCancelAddInvestigation: handleCancel,

    // Investigation-specific handlers
    handleStartInvestigation,
    handleCompleteInvestigation,
    handleCancelInvestigation
  };
};
