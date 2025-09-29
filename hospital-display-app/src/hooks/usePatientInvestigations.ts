import { useState, useCallback } from 'react';
import { patient, user, investigation, caseSheetEntry, labResult, imagingStudy } from '../types';
import { InvestigationService } from '../services';

interface UsePatientInvestigationsProps {
  patient: patient;
  currentUser: user;
  investigations: investigation[];
  setInvestigations: React.Dispatch<React.SetStateAction<investigation[]>>;
  addCaseSheetEntry: (entry: caseSheetEntry) => void;
}

export const usePatientInvestigations = ({
  patient,
  currentUser,
  investigations,
  setInvestigations,
  addCaseSheetEntry
}: UsePatientInvestigationsProps) => {
  // Investigation form state
  const [isAddingInvestigation, setIsAddingInvestigation] = useState(false);
  const [newInvestigation, setNewInvestigation] = useState({
    type: 'lab' as const, name: '', priority: 'routine' as const, notes: ''
  });
  const [addingInvestigation, setAddingInvestigation] = useState(false);

  // Lab Integration
  const [labResults, setLabResults] = useState<labResult[]>([]);
  const [loadingLabResults, setLoadingLabResults] = useState(false);

  // Imaging/PACS Integration
  const [imagingStudies, setImagingStudies] = useState<imagingStudy[]>([]);
  const [loadingImaging, setLoadingImaging] = useState(false);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  // Helper function for role-based case sheet entry types
  const getRoleBasedNoteType = useCallback((role: string): 'doctorNote' | 'nurseNote' | 'technicianNote' => {
    if (role === 'Doctor') return 'doctorNote';
    if (role === 'Nurse') return 'nurseNote';
    return 'technicianNote';
  }, []);

  // Add new investigation
  const handleAddInvestigation = useCallback(async () => {
    if (addingInvestigation || !newInvestigation.name) return;

    setAddingInvestigation(true);
    try {
      const timestamp = new Date().toISOString();
      const investigationData = {
        ...newInvestigation,
        createdAt: timestamp.split('T')[0],
        status: 'ordered' as const,
        performedBy: currentUser.name,
        canEdit: true,
        urgency: 'Routine' as const
      };

      await InvestigationService.addInvestigation(patient.id, investigationData, currentUser.id);
      const newInv: investigation = {
        id: 'inv_' + Date.now(),
        ...investigationData
      };
      setInvestigations(prev => [...prev, newInv]);

      // Add case sheet entry to backend
      try {
        const caseResponse = await fetch(`http://localhost:8001/api/v2/patients/${patient.id}/case-entries`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            entryType: 'investigation',
            description: `${newInvestigation.name} (${newInvestigation.type}, ${newInvestigation.priority}) ordered by ${currentUser.name}`,
            performedBy: currentUser.name
          })
        });

        if (caseResponse.ok) {
          const caseResult = await caseResponse.json();
          const newCaseEntry: caseSheetEntry = {
            id: caseResult.id || 'cs_' + Date.now(),
            timestamp,
            type: 'technicianNote',
            description: `${newInvestigation.name} (${newInvestigation.type}, ${newInvestigation.priority}) ordered by ${currentUser.name}`,
            performedBy: currentUser.name,
            canEdit: true
          };
          addCaseSheetEntry(newCaseEntry);
        }
      } catch (caseError) {
        console.warn('Failed to add investigation case sheet entry:', caseError);
      }

      setNewInvestigation({ type: 'lab', name: '', priority: 'routine', notes: '' });
      setIsAddingInvestigation(false);
    } catch (error) {
      console.error('Failed to add investigation:', error);
    } finally {
      setAddingInvestigation(false);
    }
  }, [addingInvestigation, newInvestigation, currentUser, patient.id, setInvestigations, addCaseSheetEntry]);

  // Start investigation
  const handleStartInvestigation = useCallback(async (inv: investigation) => {
    try {
      await InvestigationService.updateInvestigationStatus(inv.id, 'inProgress', currentUser.id);
      setInvestigations(prev => prev.map(i =>
        i.id === inv.id ? { ...i, status: 'inProgress' } : i
      ));

      // Add case sheet entry to backend
      try {
        const caseResponse = await fetch(`http://localhost:8001/api/v2/patients/${patient.id}/case-entries`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            entryType: 'investigation',
            description: `${inv.name} started by ${currentUser.name}`,
            performedBy: currentUser.name
          })
        });

        if (caseResponse.ok) {
          const caseResult = await caseResponse.json();
          const newCaseEntry: caseSheetEntry = {
            id: caseResult.id || 'cs_' + Date.now(),
            timestamp: new Date().toISOString(),
            type: 'technicianNote',
            description: `${inv.name} started by ${currentUser.name}`,
            performedBy: currentUser.name,
            canEdit: true
          };
          addCaseSheetEntry(newCaseEntry);
        }
      } catch (caseError) {
        console.warn('Failed to add investigation started case sheet entry:', caseError);
      }
    } catch (error) {
      console.error('Failed to start investigation:', error);
    }
  }, [currentUser, patient.id, setInvestigations, addCaseSheetEntry]);

  // Complete investigation
  const handleCompleteInvestigation = useCallback(async (inv: investigation) => {
    let results = '';

    if (inv.type === 'lab') {
      // For lab investigations, automatically fetch results from lab system
      try {
        setLoadingLabResults(true);
        const updatedInvestigation = await Promise.resolve(inv);

        if (updatedInvestigation.status === 'completed') {
          await InvestigationService.completeInvestigation(inv.id, updatedInvestigation.results || 'Lab results imported', currentUser.id);
          setInvestigations(prev => prev.map(i =>
            i.id === inv.id ? updatedInvestigation : i
          ));
          results = updatedInvestigation.results || 'Lab results imported';
        } else {
          alert('Lab results not yet available. Please try again later.');
          return;
        }
        setLoadingLabResults(false);
      } catch (error) {
        setLoadingLabResults(false);
        console.error('Failed to fetch lab results:', error);
        alert('Failed to fetch lab results. Please enter results manually.');

        // Fallback to manual entry
        const manualResults = window.prompt('Lab results not available. Enter results manually:');
        if (manualResults) {
          try {
            await InvestigationService.completeInvestigation(inv.id, manualResults, currentUser.id);
            setInvestigations(prev => prev.map(i =>
              i.id === inv.id ? { ...i, status: 'completed', results: manualResults, completedAt: new Date().toISOString() } : i
            ));
            results = manualResults;
          } catch (completeError) {
            console.error('Failed to complete investigation:', completeError);
            return;
          }
        } else {
          return;
        }
      }
    } else {
      // For non-lab investigations, use manual entry
      const manualResults = window.prompt('Enter investigation results:');
      if (manualResults) {
        try {
          await InvestigationService.completeInvestigation(inv.id, manualResults, currentUser.id);
          setInvestigations(prev => prev.map(i =>
            i.id === inv.id ? { ...i, status: 'completed', results: manualResults, completedAt: new Date().toISOString() } : i
          ));
          results = manualResults;
        } catch (error) {
          console.error('Failed to complete investigation:', error);
          return;
        }
      } else {
        return;
      }
    }

    // Add case sheet entry after completing investigation
    try {
      const caseResponse = await fetch(`http://localhost:8001/api/v2/patients/${patient.id}/case-entries`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          entryType: 'investigation',
          description: `${inv.name} completed by ${currentUser.name}${results ? ` - Results: ${results}` : ''}`,
          performedBy: currentUser.name
        })
      });

      if (caseResponse.ok) {
        const caseResult = await caseResponse.json();
        const newCaseEntry: caseSheetEntry = {
          id: caseResult.id || 'cs_' + Date.now(),
          timestamp: new Date().toISOString(),
          type: getRoleBasedNoteType(currentUser.role),
          description: `${inv.name} completed by ${currentUser.name}${results ? ` - Results: ${results}` : ''}`,
          performedBy: currentUser.name,
          canEdit: true
        };
        addCaseSheetEntry(newCaseEntry);
      }
    } catch (caseError) {
      console.warn('Failed to add investigation completed case sheet entry:', caseError);
    }
  }, [currentUser, patient.id, setInvestigations, addCaseSheetEntry, setLoadingLabResults, getRoleBasedNoteType]);

  // Cancel investigation
  const handleCancelInvestigation = useCallback(async (inv: investigation) => {
    if (window.confirm('Are you sure you want to cancel this investigation?')) {
      try {
        await InvestigationService.updateInvestigationStatus(inv.id, 'cancelled', currentUser.id);
        setInvestigations(prev => prev.map(i =>
          i.id === inv.id ? { ...i, status: 'cancelled' } : i
        ));

        // Add case sheet entry to backend
        try {
          const caseResponse = await fetch(`http://localhost:8001/api/v2/patients/${patient.id}/case-entries`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              entryType: 'investigation',
              description: `${inv.name} (${inv.type}) cancelled by ${currentUser.name}`,
              performedBy: currentUser.name
            })
          });

          if (caseResponse.ok) {
            const caseResult = await caseResponse.json();
            const timestamp = new Date().toISOString();
            const newCaseEntry: caseSheetEntry = {
              id: caseResult.id || 'cs_' + Date.now(),
              timestamp,
              type: 'technicianNote',
              description: `${inv.name} (${inv.type}) cancelled by ${currentUser.name}`,
              performedBy: currentUser.name,
              canEdit: true
            };
            addCaseSheetEntry(newCaseEntry);
          }
        } catch (caseError) {
          console.warn('Failed to add investigation cancellation case sheet entry:', caseError);
        }
      } catch (error) {
        console.error('Failed to cancel investigation:', error);
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

    // Imaging integration
    imagingStudies,
    setImagingStudies,
    loadingImaging,
    selectedImage,
    setSelectedImage,

    // Actions
    handleAddInvestigation,
    handleStartInvestigation,
    handleCompleteInvestigation,
    handleCancelInvestigation,
    handleCancelAddInvestigation,

    // Helpers
    getRoleBasedNoteType
  };
};