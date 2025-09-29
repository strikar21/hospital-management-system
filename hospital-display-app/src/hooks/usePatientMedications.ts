import { useState, useCallback } from 'react';
import { medication, patient, user, caseSheetEntry } from '../types';
import { MedicationService, PatientService } from '../services';

interface UsePatientMedicationsProps {
  patient: patient;
  currentUser: user;
  medications: medication[];
  setMedications: React.Dispatch<React.SetStateAction<medication[]>>;
  addCaseSheetEntry: (entry: caseSheetEntry) => void;
}

export const usePatientMedications = ({
  patient,
  currentUser,
  medications,
  setMedications,
  addCaseSheetEntry
}: UsePatientMedicationsProps) => {
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

  // Handle medication status changes
  const handleMedicationStatusChange = useCallback(async (
    medicationId: string,
    status: 'active' | 'stopped' | 'held'
  ) => {
    try {
      await MedicationService.updateMedication(patient.id, medicationId, status, currentUser.id);

      setMedications(prev => prev.map(med =>
        med.id === medicationId ? {
          ...med,
          status,
          modifiedBy: currentUser.name,
          updatedat: new Date().toISOString(),
          canEdit: PatientService.canEditItem(new Date().toISOString()),
          history: [...(med.history || []), {
            id: 'hist_' + Date.now(),
            action: status === 'active' ? 'resumed' : status,
            timestamp: new Date().toISOString(),
            performedBy: currentUser.name
          }]
        } : med
      ));

      const medication = medications.find(m => m.id === medicationId);
      if (medication) {
        const newCaseEntry: caseSheetEntry = {
          id: 'cs_' + Date.now(),
          timestamp: new Date().toISOString(),
          type: 'pharmacistNote',
          description: `${medication.name} ${status} by ${currentUser.name}`,
          performedBy: currentUser.name,
          canEdit: PatientService.canEditItem(new Date().toISOString())
        };
        addCaseSheetEntry(newCaseEntry);
      }
    } catch (error) {
      console.error('Failed to update medication:', error);
      alert('Failed to update medication. Please try again.');
    }
  }, [patient.id, currentUser, medications, setMedications, addCaseSheetEntry]);

  // Add new medication
  const handleAddMedication = useCallback(async () => {
    if (isAddingMedication) return;
    if (!newMedication.name || !newMedication.dosage || !newMedication.frequency || !newMedication.duration) return;

    setIsAddingMedication(true);
    try {
      const timestamp = new Date().toISOString();
      const medicationData = {
        ...newMedication,
        status: 'active' as const,
        startDate: timestamp.split('T')[0],
        prescribedBy: currentUser.name,
        createdAt: timestamp,
        canEdit: true
      };

      const newMed = await MedicationService.addMedication(patient.id, medicationData, currentUser.id);
      if (newMed) {
        const medicationWithHistory: medication = {
          ...newMed,
          history: newMed.history || [{
            id: 'hist_' + Date.now(),
            action: 'prescribed' as const,
            timestamp,
            performedBy: currentUser.name
          }]
        };
        setMedications(prev => [...prev, medicationWithHistory]);
      } else {
        console.error('Failed to add medication - no response from backend');
        alert('Failed to add medication. Please try again.');
        setIsAddingMedication(false);
        return;
      }

      setNewMedication({ name: '', dosage: '', frequency: '', route: 'PO', duration: '' });
      setIsAddingMedication(false);

      // Add case sheet entry to backend
      try {
        const caseResponse = await fetch(`http://localhost:8001/api/v2/patients/${patient.id}/case-entries`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            entryType: 'medication',
            description: `${newMedication.name} (${newMedication.dosage}, ${newMedication.frequency}, ${newMedication.duration}) prescribed by ${currentUser.name}`,
            performedBy: currentUser.name
          })
        });

        if (caseResponse.ok) {
          const caseResult = await caseResponse.json();
          const newCaseEntry: caseSheetEntry = {
            id: caseResult.id || 'cs_' + Date.now(),
            timestamp,
            type: 'pharmacistNote',
            description: `${newMedication.name} (${newMedication.dosage}, ${newMedication.frequency}, ${newMedication.duration}) prescribed by ${currentUser.name}`,
            performedBy: currentUser.name,
            canEdit: true
          };
          addCaseSheetEntry(newCaseEntry);
        }
      } catch (caseError) {
        console.warn('Failed to add medication case sheet entry:', caseError);
      }
    } catch (error) {
      console.error('Failed to add medication:', error);
    } finally {
      setIsAddingMedication(false);
    }
  }, [isAddingMedication, newMedication, patient.id, currentUser, setMedications, addCaseSheetEntry]);

  // Handle medication administration
  const handleMedicationAdministration = useCallback((med: medication) => {
    const now = new Date().toISOString();
    const adminEntry: caseSheetEntry = {
      id: 'admin_' + Date.now(),
      timestamp: now,
      type: 'medicationAdministration',
      description: `Administered ${med.name} ${med.dosage} via ${med.route} route`,
      performedBy: currentUser.name,
      canEdit: PatientService.canEditItem(now),
      details: {
        medicationId: med.id,
        medicationName: med.name,
        dosage: med.dosage,
        route: med.route,
        administeredby: currentUser.name,
        administeredat: now
      }
    };
    addCaseSheetEntry(adminEntry);

    alert(`✅ ${med.name} ${med.dosage} administered successfully!\n\nTime: ${new Date().toLocaleTimeString()}\nAdministered by: ${currentUser.name}\n\nAdministration logged in case sheet.`);
  }, [currentUser, addCaseSheetEntry]);

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