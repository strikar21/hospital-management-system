import { useState, useCallback } from 'react';
import { patient, user, therapy, caseSheetEntry } from '../types';
import { TherapyService, PatientService } from '../services';
import { useDataRefresh } from './useDataRefresh';
import { getApiUrl } from '../config/apiConfig';

interface UsePatientTherapiesProps {
  patient: patient;
  currentUser: user;
  therapies: therapy[];
  setTherapies: React.Dispatch<React.SetStateAction<therapy[]>>;
  addCaseSheetEntry: (entry: caseSheetEntry) => void;
  setCaseEntries: React.Dispatch<React.SetStateAction<caseSheetEntry[]>>;
}

export const usePatientTherapies = ({
  patient,
  currentUser,
  therapies,
  setTherapies,
  addCaseSheetEntry,
  setCaseEntries
}: UsePatientTherapiesProps) => {
  // Initialize data refresh hook for single source of truth
  const { refreshTherapies, refreshCaseEntries } = useDataRefresh(patient.id);
  // Therapy form state
  const [isAddingTherapy, setIsAddingTherapy] = useState(false);
  const [newTherapy, setNewTherapy] = useState({
    type: 'physiotherapy' as const, description: '', frequency: '', duration: ''
  });
  const [addingTherapy, setAddingTherapy] = useState(false);

  // Add new therapy using atomic operation
  const handleAddTherapy = useCallback(async () => {
    if (addingTherapy || !newTherapy.description) return;

    setAddingTherapy(true);
    try {
      const therapyData = {
        type: newTherapy.type,
        description: newTherapy.description,
        frequency: newTherapy.frequency,
        duration: newTherapy.duration,
        prescribedBy: currentUser.staffId
      };

      // Use atomic endpoint - creates therapy and case entry in single transaction
      const response = await fetch(getApiUrl(`/atomic/patients/${patient.id}/therapies`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(therapyData)
      });

      if (!response.ok) {
        throw new Error(`Failed to add therapy: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.success) {
        // Refetch fresh data from backend (single source of truth)
        try {
          const freshTherapies = await refreshTherapies();
          setTherapies(freshTherapies);

          const freshCaseEntries = await refreshCaseEntries();
          setCaseEntries(freshCaseEntries);

          setNewTherapy({ type: 'physiotherapy', description: '', frequency: '', duration: '' });
          setIsAddingTherapy(false);
        } catch (refreshError) {
          // Failed to refresh data after adding therapy - handle silently
        }
      } else {
        throw new Error('Atomic operation failed');
      }
    } catch (error) {
      // Failed to add therapy - handle silently
      alert('Failed to add therapy. Please try again.');
    } finally {
      setAddingTherapy(false);
    }
  }, [addingTherapy, newTherapy, currentUser, patient.id, setTherapies, setCaseEntries, refreshTherapies, refreshCaseEntries]);

  // Cancel adding therapy
  const handleCancelAddTherapy = useCallback(() => {
    setIsAddingTherapy(false);
    setNewTherapy({ type: 'physiotherapy', description: '', frequency: '', duration: '' });
  }, []);

  // Add therapy session using atomic operation
  const handleAddTherapySession = useCallback(async (therapy: therapy) => {
    const duration = window.prompt('Session duration (minutes):');
    const notes = window.prompt('Session notes:');

    if (duration && notes) {
      try {
        // Use atomic endpoint - creates therapy session and case entry in single transaction
        const response = await fetch(getApiUrl(`/atomic/patients/${patient.id}/therapies/${therapy.id}/sessions`), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            therapy_id: therapy.id,
            duration: parseInt(duration),
            notes: notes,
            performed_by: currentUser.staffId
          })
        });

        if (!response.ok) {
          throw new Error(`Failed to record therapy session: ${response.statusText}`);
        }

        const result = await response.json();

        if (result.success) {
          // Refetch fresh data from backend (single source of truth)
          try {
            const freshTherapies = await refreshTherapies();
            setTherapies(freshTherapies);

            const freshCaseEntries = await refreshCaseEntries();
            setCaseEntries(freshCaseEntries);

            alert(`✅ Therapy session #${result.medical_record.sessionNumber} recorded successfully!`);
          } catch (refreshError) {
            // Failed to refresh data after adding therapy session - handle silently
          }
        } else {
          throw new Error('Atomic operation failed');
        }
      } catch (error) {
        // Failed to add therapy session - handle silently
        alert('Failed to record therapy session. Please try again.');
      }
    }
  }, [patient.id, currentUser, setTherapies, setCaseEntries, refreshTherapies, refreshCaseEntries]);

  // Complete therapy using atomic operation
  const handleCompleteTherapy = useCallback(async (therapy: therapy) => {
    if (window.confirm('Mark this therapy as completed?')) {
      try {

        // Use atomic endpoint - updates therapy and creates case entry in single transaction
        const response = await fetch(getApiUrl(`/atomic/patients/${patient.id}/therapies/${therapy.id}/complete`), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            therapy_id: therapy.id,
            completed_by: currentUser.staffId
          })
        });

        if (!response.ok) {
          throw new Error(`Failed to complete therapy: ${response.statusText}`);
        }

        const result = await response.json();

        if (result.success) {
          // Refetch fresh data from backend (single source of truth)
          try {
            const freshTherapies = await refreshTherapies();
            setTherapies(freshTherapies);

            const freshCaseEntries = await refreshCaseEntries();
            setCaseEntries(freshCaseEntries);

          } catch (refreshError) {
            // Failed to refresh data after therapy completion - handle silently
          }
        } else {
          throw new Error('Atomic operation failed');
        }
      } catch (error) {
        // Error completing therapy - handle silently
        alert(`❌ Failed to complete therapy: ${(error as Error).message}`);
      }
    }
  }, [patient.id, currentUser, setTherapies, setCaseEntries, refreshTherapies, refreshCaseEntries]);

  // Cancel therapy using atomic operation
  const handleCancelTherapy = useCallback(async (therapy: therapy) => {
    if (window.confirm('Cancel this therapy?')) {
      try {

        // Use atomic endpoint - updates therapy and creates case entry in single transaction
        const response = await fetch(getApiUrl(`/atomic/patients/${patient.id}/therapies/${therapy.id}/cancel`), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            therapy_id: therapy.id,
            cancelled_by: currentUser.staffId
          })
        });

        if (!response.ok) {
          throw new Error(`Failed to cancel therapy: ${response.statusText}`);
        }

        const result = await response.json();

        if (result.success) {
          // Refetch fresh data from backend (single source of truth)
          try {
            const freshTherapies = await refreshTherapies();
            setTherapies(freshTherapies);

            const freshCaseEntries = await refreshCaseEntries();
            setCaseEntries(freshCaseEntries);

          } catch (refreshError) {
            // Failed to refresh data after therapy cancellation - handle silently
          }
        } else {
          throw new Error('Atomic operation failed');
        }
      } catch (error) {
        // Error cancelling therapy - handle silently
        alert(`❌ Failed to cancel therapy: ${(error as Error).message}`);
      }
    }
  }, [patient.id, currentUser, setTherapies, setCaseEntries, refreshTherapies, refreshCaseEntries]);

  return {
    // Form state
    isAddingTherapy,
    setIsAddingTherapy,
    newTherapy,
    setNewTherapy,
    addingTherapy,

    // Actions
    handleAddTherapy,
    handleCancelAddTherapy,
    handleAddTherapySession,
    handleCompleteTherapy,
    handleCancelTherapy
  };
};