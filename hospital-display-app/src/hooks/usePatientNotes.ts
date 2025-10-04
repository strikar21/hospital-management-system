import { useState, useCallback } from 'react';
import { noteComment, patient, user, caseSheetEntry } from '../types';
import { PatientService } from '../services';
import { useDataRefresh } from './useDataRefresh';
import { getApiUrl } from '../config/apiConfig';

interface UsePatientNotesProps {
  patient: patient;
  currentUser: user;
  notes: noteComment[];
  setNotes: React.Dispatch<React.SetStateAction<noteComment[]>>;
  addCaseSheetEntry: (entry: caseSheetEntry) => void;
  setCaseEntries: React.Dispatch<React.SetStateAction<caseSheetEntry[]>>;
}

export const usePatientNotes = ({
  patient,
  currentUser,
  notes,
  setNotes,
  addCaseSheetEntry,
  setCaseEntries
}: UsePatientNotesProps) => {
  // Initialize data refresh hook for single source of truth
  const { refreshNotes, refreshCaseEntries } = useDataRefresh(patient.id);
  const [isAddingNote, setIsAddingNote] = useState(false);
  const [newNote, setNewNote] = useState('');
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [isAddingHandoff, setIsAddingHandoff] = useState(false);
  const [newHandoff, setNewHandoff] = useState('');

  // Add new clinical note using atomic operation
  const handleAddNote = useCallback(async () => {
    if (!newNote.trim() || isAddingNote) return;

    setIsAddingNote(true);
    try {
      const noteData = {
        content: newNote.trim(),
        authorName: currentUser.name
      };

      // Use atomic endpoint - creates note and case entry in single transaction
      const response = await fetch(getApiUrl(`/atomic/patients/${patient.id}/notes`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(noteData)
      });

      if (!response.ok) {
        throw new Error(`Failed to add note: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.success) {
        // Refetch fresh data from backend (single source of truth)
        try {
          const freshNotes = await refreshNotes();
          setNotes(freshNotes);

          const freshCaseEntries = await refreshCaseEntries();
          setCaseEntries(freshCaseEntries);

          setNewNote('');
        } catch (refreshError) {
          // Failed to refresh data after adding note - handle silently
        }
      } else {
        throw new Error('Atomic operation failed');
      }
    } catch (error) {
      // Failed to add note - handle silently
      alert('Failed to add note. Please try again.');
    } finally {
      setIsAddingNote(false);
    }
  }, [newNote, isAddingNote, currentUser, patient.id, setNotes, setCaseEntries, refreshNotes, refreshCaseEntries]);

  // Add shift handoff note using atomic operation
  const handleAddHandoff = useCallback(async () => {
    if (!newHandoff.trim() || isAddingHandoff) return;

    setIsAddingHandoff(true);
    try {
      const handoffData = {
        content: newHandoff.trim(),
        authorName: currentUser.name
      };

      // Use atomic endpoint - creates handoff note and case entry in single transaction
      const response = await fetch(getApiUrl(`/atomic/patients/${patient.id}/notes`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(handoffData)
      });

      if (!response.ok) {
        throw new Error(`Failed to add handoff note: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.success) {
        // Refetch fresh data from backend (single source of truth)
        try {
          const freshNotes = await refreshNotes();
          setNotes(freshNotes);

          const freshCaseEntries = await refreshCaseEntries();
          setCaseEntries(freshCaseEntries);

          setNewHandoff('');
        } catch (refreshError) {
          // Failed to refresh data after adding handoff note - handle silently
        }
      } else {
        throw new Error('Atomic operation failed');
      }
    } catch (error) {
      // Failed to add handoff note - handle silently
      alert('Failed to add handoff note. Please try again.');
    } finally {
      setIsAddingHandoff(false);
    }
  }, [newHandoff, isAddingHandoff, currentUser, patient.id, setNotes, setCaseEntries, refreshNotes, refreshCaseEntries]);

  // Start editing a note
  const startEditNote = useCallback((noteId: string, currentText: string) => {
    setEditingNoteId(noteId);
    setEditText(currentText);
  }, []);

  // Save edited note using atomic operation
  const handleSaveEdit = useCallback(async (noteId: string) => {
    if (!editText.trim()) return;

    try {

      // Use atomic endpoint - updates note and creates case entry in single transaction
      const response = await fetch(getApiUrl(`/atomic/patients/${patient.id}/notes/${noteId}/edit`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          note_id: noteId,
          content: editText.trim(),
          edited_by: currentUser.staffId
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to edit note: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.success) {
        // Refetch fresh data from backend (single source of truth)
        try {
          const freshNotes = await refreshNotes();
          setNotes(freshNotes);

          const freshCaseEntries = await refreshCaseEntries();
          setCaseEntries(freshCaseEntries);

          setEditingNoteId(null);
          setEditText('');
        } catch (refreshError) {
          // Failed to refresh data after note edit - handle silently
        }
      } else {
        throw new Error('Atomic operation failed');
      }
    } catch (error) {
      // Error editing note - handle silently
      alert(`❌ Failed to edit note: ${(error as Error).message}`);
    }
  }, [editText, patient.id, currentUser, setNotes, setCaseEntries, refreshNotes, refreshCaseEntries]);

  // Cancel editing
  const cancelEdit = useCallback(() => {
    setEditingNoteId(null);
    setEditText('');
  }, []);

  // Filter notes by type
  const clinicalNotes = notes.filter(note => !note.isHandoffNote);
  const handoffNotes = notes.filter(note => note.isHandoffNote);

  return {
    isAddingNote,
    setIsAddingNote,
    newNote,
    setNewNote,
    editingNoteId,
    editText,
    setEditText,
    isAddingHandoff,
    setIsAddingHandoff,
    newHandoff,
    setNewHandoff,
    handleAddNote,
    handleAddHandoff,
    startEditNote,
    handleSaveEdit,
    cancelEdit,
    clinicalNotes,
    handoffNotes
  };
};