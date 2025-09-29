import { useState, useCallback } from 'react';
import { patient, user, therapy, caseSheetEntry } from '../types';
import { TherapyService, PatientService } from '../services';

interface UsePatientTherapiesProps {
  patient: patient;
  currentUser: user;
  therapies: therapy[];
  setTherapies: React.Dispatch<React.SetStateAction<therapy[]>>;
  addCaseSheetEntry: (entry: caseSheetEntry) => void;
}

export const usePatientTherapies = ({
  patient,
  currentUser,
  therapies,
  setTherapies,
  addCaseSheetEntry
}: UsePatientTherapiesProps) => {
  // Therapy form state
  const [isAddingTherapy, setIsAddingTherapy] = useState(false);
  const [newTherapy, setNewTherapy] = useState({
    type: 'physiotherapy' as const, description: '', frequency: '', duration: ''
  });
  const [addingTherapy, setAddingTherapy] = useState(false);

  // Add new therapy
  const handleAddTherapy = useCallback(async () => {
    if (addingTherapy || !newTherapy.description) return;

    setAddingTherapy(true);
    try {
      const timestamp = new Date().toISOString();
      const therapyData = {
        ...newTherapy,
        therapyType: newTherapy.type, // Map type to therapyType for backend
        startDate: timestamp.split('T')[0],
        status: 'active' as const,
        performedBy: currentUser.staffId,
        canEdit: true,
        sessions: [],
        name: newTherapy.type + ' therapy'
      };

      await TherapyService.addTherapy(patient.id, therapyData, currentUser.id);
      const newTher: therapy = {
        ...therapyData,
        id: 'ther_' + Date.now()
      };
      setTherapies(prev => [...prev, newTher]);

      // Add case sheet entry to backend
      try {
        const caseResponse = await fetch(`http://localhost:8001/api/v2/patients/${patient.id}/case-entries`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            entryType: 'therapy',
            description: `${newTherapy.type}: ${newTherapy.description} (${newTherapy.frequency}, ${newTherapy.duration}) prescribed by ${currentUser.name}`,
            performedBy: currentUser.staffId
          })
        });

        if (caseResponse.ok) {
          const caseResult = await caseResponse.json();
          const newCaseEntry: caseSheetEntry = {
            id: caseResult.id || 'cs_' + Date.now(),
            timestamp,
            type: 'therapistNote',
            description: `${newTherapy.type}: ${newTherapy.description} (${newTherapy.frequency}, ${newTherapy.duration}) prescribed by ${currentUser.name}`,
            performedBy: currentUser.staffId,
            canEdit: true
          };
          addCaseSheetEntry(newCaseEntry);
        }
      } catch (caseError) {
        console.warn('Failed to add therapy case sheet entry:', caseError);
      }

      setNewTherapy({ type: 'physiotherapy', description: '', frequency: '', duration: '' });
      setIsAddingTherapy(false);
    } catch (error) {
      console.error('Failed to add therapy:', error);
    } finally {
      setAddingTherapy(false);
    }
  }, [addingTherapy, newTherapy, currentUser, patient.id, setTherapies, addCaseSheetEntry]);

  // Cancel adding therapy
  const handleCancelAddTherapy = useCallback(() => {
    setIsAddingTherapy(false);
    setNewTherapy({ type: 'physiotherapy', description: '', frequency: '', duration: '' });
  }, []);

  // Add therapy session
  const handleAddTherapySession = useCallback(async (therapy: therapy) => {
    const duration = window.prompt('Session duration (minutes):');
    const notes = window.prompt('Session notes:');
    const patientResponse = window.prompt('Patient response:');

    if (duration && notes && patientResponse) {
      try {
        const sessionData = {
          duration: parseInt(duration),
          notes: notes,
          therapist: currentUser.name,
          patientResponse: patientResponse
        };

        // BACKEND INTEGRATION NEEDED: Implement TherapyService.addTherapySession method
        // Expected endpoint: POST /api/v1/patients/{patientId}/therapies/{therapyId}/sessions
        // Payload: { duration, notes, therapist, patientResponse, performedBy }
        // await TherapyService.addTherapySession(patient.id, therapy.id, sessionData, currentUser.id);

        const newSession = {
          id: 'session_' + Date.now(),
          date: new Date().toISOString(),
          duration: sessionData.duration,
          notes: sessionData.notes,
          therapist: sessionData.therapist,
          patientResponse: sessionData.patientResponse
        };

        setTherapies(prev => prev.map(t =>
          t.id === therapy.id ? {
            ...t,
            sessions: [...(t.sessions || []), newSession],
            therapist: currentUser.name
          } : t
        ));

        const newCaseEntry: caseSheetEntry = {
          id: 'cs_' + Date.now(),
          timestamp: new Date().toISOString(),
          type: 'therapistNote',
          description: `${therapy.description} session completed by ${currentUser.name}`,
          performedBy: currentUser.staffId,
          canEdit: PatientService.canEditItem(new Date().toISOString())
        };
        addCaseSheetEntry(newCaseEntry);
      } catch (error) {
        console.error('Failed to add therapy session:', error);
      }
    }
  }, [currentUser, setTherapies, addCaseSheetEntry]);

  // Complete therapy
  const handleCompleteTherapy = useCallback(async (therapy: therapy) => {
    if (window.confirm('Mark this therapy as completed?')) {
      try {
        await TherapyService.updateTherapy(patient.id, therapy.id, { status: 'completed' }, currentUser.id);
        setTherapies(prev => prev.map(t =>
          t.id === therapy.id ? { ...t, status: 'completed', enddate: new Date().toISOString() } : t
        ));
        const newCaseEntry: caseSheetEntry = {
          id: 'cs_' + Date.now(),
          timestamp: new Date().toISOString(),
          type: 'therapistNote',
          description: `${therapy.description} completed by ${currentUser.name}`,
          performedBy: currentUser.staffId,
          canEdit: PatientService.canEditItem(new Date().toISOString())
        };
        addCaseSheetEntry(newCaseEntry);
      } catch (error) {
        console.error('Failed to complete therapy:', error);
      }
    }
  }, [patient.id, currentUser, setTherapies, addCaseSheetEntry]);

  // Cancel therapy
  const handleCancelTherapy = useCallback(async (therapy: therapy) => {
    if (window.confirm('Cancel this therapy?')) {
      try {
        await TherapyService.updateTherapy(patient.id, therapy.id, { status: 'cancelled' }, currentUser.id);
        setTherapies(prev => prev.map(t =>
          t.id === therapy.id ? { ...t, status: 'cancelled' } : t
        ));
        const newCaseEntry: caseSheetEntry = {
          id: 'cs_' + Date.now(),
          timestamp: new Date().toISOString(),
          type: 'therapistNote',
          description: `${therapy.description} cancelled by ${currentUser.name}`,
          performedBy: currentUser.staffId,
          canEdit: PatientService.canEditItem(new Date().toISOString())
        };
        addCaseSheetEntry(newCaseEntry);
      } catch (error) {
        console.error('Failed to cancel therapy:', error);
      }
    }
  }, [patient.id, currentUser, setTherapies, addCaseSheetEntry]);

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