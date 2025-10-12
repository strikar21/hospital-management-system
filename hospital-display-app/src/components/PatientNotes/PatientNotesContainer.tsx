/**
 * PatientNotesContainer - Main notes management container (Refactored)
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data, no kebab-case
 *
 * Phase 5 Refactoring: Aligned with Medications/Investigations/Therapies pattern
 * - Uses usePatientNotes hook for all state and logic
 * - Container is rendering-only
 * - Consistent file structure
 */

import React, { useState } from 'react';
import { MessageCircle, Clock } from 'lucide-react';
import { patient, user, noteComment, caseSheetEntry } from '../../types';
import { PermissionUtils } from '../../utils/permissionUtils';
import { usePatientNotes } from '../../hooks/usePatientNotes';
import { NotesEditor, NotesViewer } from './';
import { HandoffNotesModal } from '../modals/HandoffNotesModal';

interface PatientNotesContainerProps {
  patient: patient;
  currentUser: user;
  notes: noteComment[];
  setNotes: React.Dispatch<React.SetStateAction<noteComment[]>>;
  caseSheet: caseSheetEntry[];
  addCaseSheetEntry: (entry: caseSheetEntry) => void;
  setCaseEntries: React.Dispatch<React.SetStateAction<caseSheetEntry[]>>;
  refreshPatientData?: () => Promise<void>;
}

export const PatientNotesContainer: React.FC<PatientNotesContainerProps> = ({
  patient,
  currentUser,
  notes,
  setNotes,
  caseSheet,
  addCaseSheetEntry,
  setCaseEntries,
  refreshPatientData
}) => {
  // ================================
  // HOOK USAGE - ALL LOGIC HERE
  // ================================

  const {
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
  } = usePatientNotes({
    patient,
    currentUser,
    notes,
    setNotes,
    addCaseSheetEntry,
    setCaseEntries
  });

  // ================================
  // UI-ONLY STATE (Not in hook)
  // ================================

  const [isHandoffModalOpen, setIsHandoffModalOpen] = useState(false);

  // ================================
  // WRAPPER FUNCTIONS (For NotesEditor compatibility)
  // ================================

  // Wrapper to match NotesEditor's expected callback signature
  const handleNoteAddedCallback = async (newNote: noteComment) => {
    // Refresh parent data if available
    if (refreshPatientData) {
      await refreshPatientData();
    }
  };

  const handleNoteEditedCallback = async (noteId: string, content: string, editedAt: string) => {
    // Refresh parent data if available
    if (refreshPatientData) {
      await refreshPatientData();
    }
  };

  // ================================
  // RENDERING ONLY
  // ================================

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
        onNoteAdded={handleNoteAddedCallback}
        onNoteEdited={handleNoteEditedCallback}
        addCaseSheetEntry={addCaseSheetEntry}
        editingNoteId={editingNoteId}
        setEditingNoteId={(id) => id ? startEditNote(id, editText) : cancelEdit()}
        editingNoteContent={editText}
        setEditingNoteContent={setEditText}
      />

      {/* Notes Viewer - Display Notes List */}
      <NotesViewer
        currentUser={currentUser}
        notes={clinicalNotes}
        onEditNote={(note) => startEditNote(note.id, note.content)}
        onAddFirstNote={() => setIsAddingNote(true)}
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

export default PatientNotesContainer;
