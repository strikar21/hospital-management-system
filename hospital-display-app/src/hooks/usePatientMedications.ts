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
        // Update medication in state with response data
        setMedications(prev => prev.map(med =>
          med.id === medicationId ? result.medical_record : med
        ));

        // Add case sheet entry from atomic response
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
      } else {
        throw new Error('Atomic operation failed');
      }
    } catch (error) {
      // Error changing medication status - handle silently
      alert(`❌ Failed to change medication status: ${(error as Error).message}`);
    }
  }, [patient.id, currentUser, setMedications, addCaseSheetEntry]);

  // Add new medication using atomic operation
  const handleAddMedication = useCallback(async () => {
    if (isAddingMedication) return;
    if (!newMedication.name || !newMedication.dosage || !newMedication.frequency || !newMedication.duration) return;

    setIsAddingMedication(true);
    try {
      const medicationData: Omit<medication, 'id' | 'history'> = {
        name: newMedication.name,
        dosage: newMedication.dosage,
        frequency: newMedication.frequency,
        route: newMedication.route,
        duration: newMedication.duration,
        status: 'active',
        startDate: new Date().toISOString(),
        prescribedBy: currentUser.staffId,
        createdAt: new Date().toISOString(),
        canEdit: true
      };

      // Use Service layer for API call
      const result = await MedicationService.addMedication(patient.id, medicationData, currentUser.staffId);

      if (result && result.success) {
        // Add medication to state from atomic response
        setMedications(prev => [...prev, result.medical_record]);

        // Add case sheet entry from atomic response
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

        setNewMedication({ name: '', dosage: '', frequency: '', route: 'PO', duration: '' });
      } else {
        throw new Error('Atomic operation failed');
      }
    } catch (error: any) {
      // Parse specific error messages from backend
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
    } finally {
      setIsAddingMedication(false);
    }
  }, [isAddingMedication, newMedication, patient.id, currentUser, setMedications, addCaseSheetEntry]);

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

      // Add case sheet entry from atomic response
      if (result.success && result.case_entry) {
        const adminEntry: caseSheetEntry = {
          id: result.case_entry.id,
          timestamp: result.case_entry.timestamp,
          type: result.case_entry.entryType,
          description: result.case_entry.description,
          performedBy: result.case_entry.performedBy,
          canEdit: true
        };
        addCaseSheetEntry(adminEntry);
      }

      alert(`✅ ${med.name} ${med.dosage} administered successfully!\n\nTime: ${new Date().toLocaleTimeString()}\nAdministered by: ${currentUser.staffId}\n\nAdministration recorded in database and case sheet.`);

    } catch (error) {
      // Error administering medication - handle silently
      alert(`❌ Failed to administer medication: ${(error as Error).message}`);
    }
  }, [patient.id, currentUser, addCaseSheetEntry]);

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