import { useState, useCallback } from 'react';
import { noteComment, patient, user, caseSheetEntry } from '../types';
import { PatientService } from '../services';

interface UsePatientNotesProps {
  patient: patient;
  currentUser: user;
  notes: noteComment[];
  setNotes: React.Dispatch<React.SetStateAction<noteComment[]>>;
  addCaseSheetEntry: (entry: caseSheetEntry) => void;
}

export const usePatientNotes = ({
  patient,
  currentUser,
  notes,
  setNotes,
  addCaseSheetEntry
}: UsePatientNotesProps) => {
  const [isAddingNote, setIsAddingNote] = useState(false);
  const [newNote, setNewNote] = useState('');
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [isAddingHandoff, setIsAddingHandoff] = useState(false);
  const [newHandoff, setNewHandoff] = useState('');

  // Add new clinical note
  const handleAddNote = useCallback(async () => {
    if (!newNote.trim() || isAddingNote) return;

    setIsAddingNote(true);
    try {
      const timestamp = new Date().toISOString();
      const noteData = {
        comment: newNote.trim(),
        commentedBy: currentUser.name,
        timestamp,
        isHandoffNote: false
      };

      const response = await fetch(`http://localhost:8001/api/v2/patients/${patient.id}/notes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(noteData)
      });

      if (response.ok) {
        const result = await response.json();
        const newNoteEntry: noteComment = {
          id: result.id || 'note_' + Date.now(),
          comment: newNote.trim(),
          commentedBy: currentUser.name,
          timestamp,
          canEdit: PatientService.canEditItem(timestamp),
          isHandoffNote: false
        };

        setNotes(prev => [newNoteEntry, ...prev]);
        setNewNote('');

        // Add case sheet entry
        const newCaseEntry: caseSheetEntry = {
          id: 'cs_note_' + Date.now(),
          timestamp,
          type: 'note',
          description: `Clinical note added by ${currentUser.name}`,
          performedBy: currentUser.name,
          canEdit: PatientService.canEditItem(timestamp)
        };
        addCaseSheetEntry(newCaseEntry);
      } else {
        alert('Failed to add note. Please try again.');
      }
    } catch (error) {
      console.error('Failed to add note:', error);
      alert('Failed to add note. Please try again.');
    } finally {
      setIsAddingNote(false);
    }
  }, [newNote, isAddingNote, currentUser, patient.id, setNotes, addCaseSheetEntry]);

  // Add shift handoff note
  const handleAddHandoff = useCallback(async () => {
    if (!newHandoff.trim() || isAddingHandoff) return;

    setIsAddingHandoff(true);
    try {
      const timestamp = new Date().toISOString();
      const handoffData = {
        comment: newHandoff.trim(),
        commentedBy: currentUser.name,
        timestamp,
        isHandoffNote: true
      };

      const response = await fetch(`http://localhost:8001/api/v2/patients/${patient.id}/notes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(handoffData)
      });

      if (response.ok) {
        const result = await response.json();
        const newHandoffEntry: noteComment = {
          id: result.id || 'handoff_' + Date.now(),
          comment: newHandoff.trim(),
          commentedBy: currentUser.name,
          timestamp,
          canEdit: PatientService.canEditItem(timestamp),
          isHandoffNote: true
        };

        setNotes(prev => [newHandoffEntry, ...prev]);
        setNewHandoff('');

        // Add case sheet entry
        const newCaseEntry: caseSheetEntry = {
          id: 'cs_handoff_' + Date.now(),
          timestamp,
          type: 'shiftHandoff',
          description: `Shift handoff note by ${currentUser.name}: ${newHandoff.trim()}`,
          performedBy: currentUser.name,
          canEdit: PatientService.canEditItem(timestamp)
        };
        addCaseSheetEntry(newCaseEntry);
      } else {
        alert('Failed to add handoff note. Please try again.');
      }
    } catch (error) {
      console.error('Failed to add handoff note:', error);
      alert('Failed to add handoff note. Please try again.');
    } finally {
      setIsAddingHandoff(false);
    }
  }, [newHandoff, isAddingHandoff, currentUser, patient.id, setNotes, addCaseSheetEntry]);

  // Start editing a note
  const startEditNote = useCallback((noteId: string, currentText: string) => {
    setEditingNoteId(noteId);
    setEditText(currentText);
  }, []);

  // Save edited note
  const handleSaveEdit = useCallback(async (noteId: string) => {
    if (!editText.trim()) return;

    try {
      const response = await fetch(`http://localhost:8001/api/v2/patients/${patient.id}/notes/${noteId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          comment: editText.trim(),
          modifiedBy: currentUser.name
        })
      });

      if (response.ok) {
        setNotes(prev => prev.map(note =>
          note.id === noteId
            ? {
                ...note,
                comment: editText.trim(),
                modifiedBy: currentUser.name,
                updatedat: new Date().toISOString()
              }
            : note
        ));

        // Add case sheet entry for edit
        const newCaseEntry: caseSheetEntry = {
          id: 'cs_edit_' + Date.now(),
          timestamp: new Date().toISOString(),
          type: 'noteEdit',
          description: `Note edited by ${currentUser.name}`,
          performedBy: currentUser.name,
          canEdit: PatientService.canEditItem(new Date().toISOString())
        };
        addCaseSheetEntry(newCaseEntry);

        setEditingNoteId(null);
        setEditText('');
      } else {
        alert('Failed to update note. Please try again.');
      }
    } catch (error) {
      console.error('Failed to update note:', error);
      alert('Failed to update note. Please try again.');
    }
  }, [editText, patient.id, currentUser, setNotes, addCaseSheetEntry]);

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