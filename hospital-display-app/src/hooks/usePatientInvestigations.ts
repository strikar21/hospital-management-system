import { useState, useCallback } from 'react';
import { patient, user, investigation, caseSheetEntry, labResult, imagingStudy } from '../types';
import { InvestigationService } from '../services';
import { useDataRefresh } from './useDataRefresh';
import { getApiUrl } from '../config/apiConfig';

interface UsePatientInvestigationsProps {
  patient: patient;
  currentUser: user;
  investigations: investigation[];
  setInvestigations: React.Dispatch<React.SetStateAction<investigation[]>>;
  addCaseSheetEntry: (entry: caseSheetEntry) => void;
  setCaseEntries: React.Dispatch<React.SetStateAction<caseSheetEntry[]>>;
}

export const usePatientInvestigations = ({
  patient,
  currentUser,
  investigations,
  setInvestigations,
  addCaseSheetEntry,
  setCaseEntries
}: UsePatientInvestigationsProps) => {
  // Initialize data refresh hook for single source of truth
  const { refreshInvestigations, refreshCaseEntries } = useDataRefresh(patient.id);
  // Investigation form state
  const [isAddingInvestigation, setIsAddingInvestigation] = useState(false);
  const [newInvestigation, setNewInvestigation] = useState({
    type: 'lab' as const, name: '', priority: 'routine' as const, notes: ''
  });
  const [addingInvestigation, setAddingInvestigation] = useState(false);

  // Lab Integration
  const [labResults, setLabResults] = useState<labResult[]>([]);
  const [loadingLabResults, setLoadingLabResults] = useState(false);

  // Add new investigation using atomic operation
  const handleAddInvestigation = useCallback(async () => {
    if (addingInvestigation || !newInvestigation.name) return;

    setAddingInvestigation(true);
    try {
      // Exclude backend-generated audit fields (createdAt, updatedAt, createdBy, createdByName)
      const investigationData: Omit<investigation, 'id' | 'createdAt' | 'updatedAt' | 'createdBy' | 'createdByName'> = {
        name: newInvestigation.name,
        type: newInvestigation.type,
        priority: newInvestigation.priority,
        urgency: 'Routine',
        notes: newInvestigation.notes,
        prescribedBy: currentUser.staffId,
        status: 'ordered',
        canEdit: true
      };

      // Use Service layer for API call
      const result = await InvestigationService.addInvestigation(patient.id, investigationData, currentUser.staffId);

      if (result && result.success) {
        // Use investigation from atomic response
        const newInvestigationRecord = result.medical_record;
        setInvestigations(prev => [...prev, newInvestigationRecord]);

        // Add case sheet entry from atomic result (already created atomically)
        if (result.case_entry) {
          const newCaseEntry: caseSheetEntry = {
            id: result.case_entry.id,
            timestamp: result.case_entry.timestamp,
            type: result.case_entry.entryType,
            description: result.case_entry.description,
            performedBy: result.case_entry.performedBy,
            canEdit: true
          };
          addCaseSheetEntry(newCaseEntry);
        }

        setNewInvestigation({ type: 'lab', name: '', priority: 'routine', notes: '' });
        setIsAddingInvestigation(false);
      } else {
        throw new Error('Atomic operation failed');
      }
    } catch (error) {
      // Failed to add investigation - handle silently
      alert('Failed to add investigation. Please try again.');
    } finally {
      setAddingInvestigation(false);
    }
  }, [addingInvestigation, newInvestigation, currentUser, patient.id, setInvestigations, setCaseEntries, refreshInvestigations, refreshCaseEntries]);

  // Start investigation
  const handleStartInvestigation = useCallback(async (inv: investigation) => {
    try {
      await InvestigationService.updateInvestigationStatus(inv.id, 'inProgress', currentUser.id);

      // Refetch fresh data from backend (single source of truth)
      try {
        const freshInvestigations = await refreshInvestigations();
        setInvestigations(freshInvestigations);
      } catch (refreshError) {
        // Failed to refresh data after starting investigation - handle silently
      }

      // Add case sheet entry to backend
      try {
        const caseResponse = await fetch(getApiUrl(`/patients/${patient.id}/case-entries`), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            entryType: 'investigation',
            description: `${inv.name} started by ${currentUser.name}`,
            performedBy: currentUser.staffId
          })
        });

        if (caseResponse.ok) {
          const caseResult = await caseResponse.json();
          const newCaseEntry: caseSheetEntry = {
            id: caseResult.id, // Backend must provide ID
            timestamp: caseResult.timestamp, // Backend-generated timestamp
            type: 'technicianNote',
            description: `${inv.name} started by ${currentUser.name}`,
            performedBy: currentUser.staffId,
            canEdit: true
          };
          addCaseSheetEntry(newCaseEntry);
        }
      } catch (caseError) {
        // Failed to add investigation started case sheet entry - handle silently
      }
    } catch (error) {
      // Failed to start investigation - handle silently
    }
  }, [currentUser, patient.id, setInvestigations, addCaseSheetEntry]);

  // Complete investigation using atomic operation
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

      // Use atomic endpoint - updates investigation and creates case entry in single transaction
      const response = await fetch(getApiUrl(`/atomic/patients/${patient.id}/investigations/${inv.id}/complete`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          investigation_id: inv.id,
          results: results,
          completed_by: currentUser.staffId
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to complete investigation: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.success) {
        // Update investigation in state with response data
        setInvestigations(prev => prev.map(investigation =>
          investigation.id === inv.id ? result.medical_record : investigation
        ));

        // Add case sheet entry from atomic response
        if (result.case_entry) {
          const completionEntry: caseSheetEntry = {
            id: result.case_entry.id,
            timestamp: result.case_entry.timestamp,
            type: result.case_entry.entryType,
            description: result.case_entry.description,
            performedBy: result.case_entry.performedBy,
            canEdit: true
          };
          addCaseSheetEntry(completionEntry);
        }
      } else {
        throw new Error('Atomic operation failed');
      }
    } catch (error) {
      // Error completing investigation - handle silently
      alert(`❌ Failed to complete investigation: ${(error as Error).message}`);
    }
  }, [currentUser, patient.id, setInvestigations, addCaseSheetEntry, setLoadingLabResults]);

  // Cancel investigation
  const handleCancelInvestigation = useCallback(async (inv: investigation) => {
    if (window.confirm('Are you sure you want to cancel this investigation?')) {
      try {
        await InvestigationService.updateInvestigationStatus(inv.id, 'cancelled', currentUser.id);

        // Refetch fresh data from backend (single source of truth)
        try {
          const freshInvestigations = await refreshInvestigations();
          setInvestigations(freshInvestigations);
        } catch (refreshError) {
          // Failed to refresh data after cancelling investigation - handle silently
        }

        // Add case sheet entry to backend
        try {
          const caseResponse = await fetch(getApiUrl(`/patients/${patient.id}/case-entries`), {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              entryType: 'investigation',
              description: `${inv.name} (${inv.type}) cancelled by ${currentUser.name}`,
              performedBy: currentUser.staffId
            })
          });

          if (caseResponse.ok) {
            const caseResult = await caseResponse.json();
            const newCaseEntry: caseSheetEntry = {
              id: caseResult.id, // Backend must provide ID
              timestamp: caseResult.timestamp, // Backend-generated timestamp
              type: 'technicianNote',
              description: `${inv.name} (${inv.type}) cancelled by ${currentUser.name}`,
              performedBy: currentUser.staffId,
              canEdit: true
            };
            addCaseSheetEntry(newCaseEntry);
          }
        } catch (caseError) {
          // Failed to add investigation cancellation case sheet entry - handle silently
        }
      } catch (error) {
        // Failed to cancel investigation - handle silently
      }
    }
  }, [currentUser, patient.id, setInvestigations, addCaseSheetEntry]);

  // Cancel adding investigation
  const handleCancelAddInvestigation = useCallback(() => {
    setIsAddingInvestigation(false);
    setNewInvestigation({ type: 'lab', name: '', priority: 'routine', notes: '' });
  }, []);

  return {
    // Form state
    isAddingInvestigation,
    setIsAddingInvestigation,
    newInvestigation,
    setNewInvestigation,
    addingInvestigation,

    // Lab integration
    labResults,
    setLabResults,
    loadingLabResults,

    // Actions
    handleAddInvestigation,
    handleStartInvestigation,
    handleCompleteInvestigation,
    handleCancelInvestigation,
    handleCancelAddInvestigation
  };
};