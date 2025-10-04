import { useState, useCallback } from 'react';
import { medication, patient, user, caseSheetEntry } from '../types';
import { MedicationService, PatientService } from '../services';
import { useDataRefresh } from './useDataRefresh';
import { getApiUrl } from '../config/apiConfig';

interface UsePatientMedicationsProps {
  patient: patient;
  currentUser: user;
  medications: medication[];
  setMedications: React.Dispatch<React.SetStateAction<medication[]>>;
  addCaseSheetEntry: (entry: caseSheetEntry) => void;
  setCaseEntries: React.Dispatch<React.SetStateAction<caseSheetEntry[]>>;
}

export const usePatientMedications = ({
  patient,
  currentUser,
  medications,
  setMedications,
  addCaseSheetEntry,
  setCaseEntries
}: UsePatientMedicationsProps) => {
  // Initialize data refresh hook for single source of truth
  const { refreshMedications, refreshCaseEntries } = useDataRefresh(patient.id);
  const [isAddingMedication, setIsAddingMedication] = useState(false);
  const [newMedication, setNewMedication] = useState({
    name: '', dosage: '', frequency: '', route: 'PO', duration: ''
  });

  // Debounce utility
  const debounce = useCallback((func: (...args: any[]) => void, wait: number) => {
    let timeout: NodeJS.Timeout;
    return (...args: any[]) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => func(...args), wait);
    };
  }, []);

  // Handle medication status changes using atomic operation
  const handleMedicationStatusChange = useCallback(async (
    medicationId: string,
    status: 'active' | 'stopped' | 'held'
  ) => {
    try {

      // Use atomic endpoint - updates medication and creates case entry in single transaction
      const response = await fetch(getApiUrl(`/atomic/patients/${patient.id}/medications/${medicationId}/status`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          medication_id: medicationId,
          status: status,
          changed_by: currentUser.staffId
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to change medication status: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.success) {
        // Refetch fresh data from backend (single source of truth)
        try {
          const freshMedications = await refreshMedications();
          setMedications(freshMedications);

          const freshCaseEntries = await refreshCaseEntries();
          setCaseEntries(freshCaseEntries);

        } catch (refreshError) {
          // Failed to refresh data after medication status change - handle silently
        }
      } else {
        throw new Error('Atomic operation failed');
      }
    } catch (error) {
      // Error changing medication status - handle silently
      alert(`❌ Failed to change medication status: ${(error as Error).message}`);
    }
  }, [patient.id, currentUser, setMedications, setCaseEntries, refreshMedications, refreshCaseEntries]);

  // Add new medication using atomic operation
  const handleAddMedication = useCallback(async () => {
    if (isAddingMedication) return;
    if (!newMedication.name || !newMedication.dosage || !newMedication.frequency || !newMedication.duration) return;

    setIsAddingMedication(true);
    try {
      const medicationData = {
        name: newMedication.name,
        dosage: newMedication.dosage,
        frequency: newMedication.frequency,
        route: newMedication.route,
        duration: newMedication.duration
        // startDate: backend will generate
      };

      // Use atomic endpoint - creates medication and case entry in single transaction
      const response = await fetch(getApiUrl(`/atomic/patients/${patient.id}/medications`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(medicationData)
      });

      if (!response.ok) {
        throw new Error(`Failed to add medication: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.success) {
        // Refetch fresh data from backend (single source of truth)
        try {
          const freshMedications = await refreshMedications();
          setMedications(freshMedications);

          const freshCaseEntries = await refreshCaseEntries();
          setCaseEntries(freshCaseEntries);

          setNewMedication({ name: '', dosage: '', frequency: '', route: 'PO', duration: '' });
        } catch (refreshError) {
          // Failed to refresh data after adding medication - handle silently
        }
      } else {
        throw new Error('Atomic operation failed');
      }
    } catch (error) {
      // Failed to add medication - handle silently
      alert('Failed to add medication. Please try again.');
    } finally {
      setIsAddingMedication(false);
    }
  }, [isAddingMedication, newMedication, patient.id, currentUser, setMedications, setCaseEntries, refreshMedications, refreshCaseEntries]);

  // Handle medication administration atomically with backend persistence
  const handleMedicationAdministration = useCallback(async (med: medication) => {
    try {

      const response = await fetch(getApiUrl(`/atomic/patients/${patient.id}/medications/${med.id}/administer`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          administered_by: currentUser.staffId,
          notes: `Administered ${med.name} ${med.dosage} via ${med.route} route`
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to administer medication: ${response.statusText}`);
      }

      const result = await response.json();

      // Refetch fresh data from backend (single source of truth)
      try {
        const freshCaseEntries = await refreshCaseEntries();
        setCaseEntries(freshCaseEntries);

      } catch (refreshError) {
        // Failed to refresh case entries after medication administration - handle silently
      }

      alert(`✅ ${med.name} ${med.dosage} administered successfully!\n\nTime: ${new Date().toLocaleTimeString()}\nAdministered by: ${currentUser.staffId}\n\nAdministration recorded in database and case sheet.`);

    } catch (error) {
      // Error administering medication - handle silently
      alert(`❌ Failed to administer medication: ${(error as Error).message}`);
    }
  }, [patient.id, currentUser, setCaseEntries, refreshCaseEntries]);

  // Generate medication schedule times
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

  return {
    isAddingMedication,
    setIsAddingMedication,
    newMedication,
    setNewMedication,
    handleMedicationStatusChange,
    handleAddMedication,
    handleMedicationAdministration,
    generateScheduleTimes,
    debounce
  };
};