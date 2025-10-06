/**
 * PatientNotes - Container component for patient notes management (Refactored)
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade notes interface using modular architecture
 */

import React, { useState } from 'react';
import { MessageCircle, Clock } from 'lucide-react';
import { patient, user, noteComment, caseSheetEntry } from '../types';
import { PermissionUtils } from '../utils/permissionUtils';
import { NotesEditor, NotesViewer, HandoffNotes } from './PatientNotes/';
import { HandoffNotesModal } from './modals/HandoffNotesModal';
import { getApiUrl } from '../config/apiConfig';

interface PatientNotesProps {
  patient: patient;
  currentUser: user;
  notes: noteComment[];
  setNotes: React.Dispatch<React.SetStateAction<noteComment[]>>;
  caseSheet: caseSheetEntry[];
  addCaseSheetEntry: (entry: caseSheetEntry) => void;
}

const PatientNotes: React.FC<PatientNotesProps> = ({
  patient,
  currentUser,
  notes,
  setNotes,
  caseSheet,
  addCaseSheetEntry
}) => {
  // Editor state management
  const [isAddingNote, setIsAddingNote] = useState(false);
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [editingNoteContent, setEditingNoteContent] = useState('');
  const [isHandoffModalOpen, setIsHandoffModalOpen] = useState(false);

  // Handle note added from editor
  const handleNoteAdded = async (newNote: noteComment) => {
    // Notes come with patient data - just update local state
    // Backend refresh happens via parent component
    setNotes(prev => [newNote, ...prev]);
  };

  // Handle note edited from editor
  const handleNoteEdited = async (noteId: string, content: string, editedAt: string) => {
    // Refetch fresh data from backend (single source of truth)
    try {
      const notesResponse = await fetch(getApiUrl(`/patients/${patient.id}/notes`));
      if (notesResponse.ok) {
        const data = await notesResponse.json();
        setNotes(data.notes || data);
      }
    } catch (refreshError) {
      // Failed to refresh notes after editing - handle silently
    }
  };

  // Handle edit note initiation
  const handleEditNote = (note: noteComment) => {
    setEditingNoteId(note.id);
    setEditingNoteContent(note.content);
  };

  // Handle add first note
  const handleAddFirstNote = () => {
    setIsAddingNote(true);
  };

  return (
    <div className="p-3 h-full flex flex-col">
      {/* Add Note and Handoff Notes Buttons */}
      {PermissionUtils.canEditNotes(currentUser.role) && (
        <div className="flex justify-end gap-2 mb-2">
          <button
            onClick={() => setIsHandoffModalOpen(true)}
            className="flex items-center space-x-2 px-3 py-1 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm"
          >
            <Clock className="w-4 h-4" />
            <span>View Handoff Notes</span>
          </button>
          <button
            onClick={() => setIsAddingNote(true)}
            className="flex items-center space-x-2 px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
          >
            <MessageCircle className="w-4 h-4" />
            <span>Add Note</span>
          </button>
        </div>
      )}

      {/* Notes Editor - Add/Edit Interface */}
      <NotesEditor
        patient={patient}
        currentUser={currentUser}
        isAddingNote={isAddingNote}
        setIsAddingNote={setIsAddingNote}
        onNoteAdded={handleNoteAdded}
        onNoteEdited={handleNoteEdited}
        addCaseSheetEntry={addCaseSheetEntry}
        editingNoteId={editingNoteId}
        setEditingNoteId={setEditingNoteId}
        editingNoteContent={editingNoteContent}
        setEditingNoteContent={setEditingNoteContent}
      />

      {/* Notes Viewer - Display Notes List */}
      <NotesViewer
        currentUser={currentUser}
        notes={notes}
        onEditNote={handleEditNote}
        onAddFirstNote={handleAddFirstNote}
      />

      {/* Handoff Notes Modal */}
      <HandoffNotesModal
        isOpen={isHandoffModalOpen}
        onClose={() => setIsHandoffModalOpen(false)}
        currentUser={currentUser}
        caseSheet={caseSheet}
        addCaseSheetEntry={addCaseSheetEntry}
      />
    </div>
  );
};

export default PatientNotes;