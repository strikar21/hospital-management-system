/**
 * NotesEditor - Add and edit notes functionality (Refactored)
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade note editing with audit trail
 */

import React, { useState } from 'react';
import { Send, X, Save } from 'lucide-react';
import { patient, user, noteComment, caseSheetEntry } from '../../types';
import { PatientService } from '../../services';
import { PatientCaseService } from '../../services/patient';
import { PermissionUtils } from '../../utils/permissionUtils';
import { getApiUrl } from '../../config/apiConfig';

interface NotesEditorProps {
  patient: patient;
  currentUser: user;
  isAddingNote: boolean;
  setIsAddingNote: (adding: boolean) => void;
  onNoteAdded: (note: noteComment) => void;
  onNoteEdited: (noteId: string, content: string, editedAt: string) => void;
  addCaseSheetEntry: (entry: caseSheetEntry) => void;
  editingNoteId: string | null;
  setEditingNoteId: (id: string | null) => void;
  editingNoteContent: string;
  setEditingNoteContent: (content: string) => void;
}

export const NotesEditor: React.FC<NotesEditorProps> = ({
  patient,
  currentUser,
  isAddingNote,
  setIsAddingNote,
  onNoteAdded,
  onNoteEdited,
  addCaseSheetEntry,
  editingNoteId,
  setEditingNoteId,
  editingNoteContent,
  setEditingNoteContent
}) => {
  // Local state for add note functionality
  const [newNoteContent, setNewNoteContent] = useState('');
  const [addingNote, setAddingNote] = useState(false);
  const [editingNote, setEditingNote] = useState(false);

  // Debounce utility for edit operations
  const debounce = (func: (...args: any[]) => void, wait: number) => {
    let timeout: NodeJS.Timeout;
    return (...args: any[]) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => func(...args), wait);
    };
  };

  // Get role-based note type for case sheet entries
  // If staff role exists, use role-based type; otherwise use neutral 'note' for system entries
  const getRoleBasedNoteType = (userRole?: string): 'doctorNote' | 'nurseNote' | 'technicianNote' | 'clinicalNote' => {
    if (!userRole) return 'clinicalNote'; // System-generated entries
    switch (userRole) {
      case 'Doctor': return 'doctorNote';
      case 'Nurse': return 'nurseNote';
      case 'Technician': return 'technicianNote';
      case 'Administrator':
      case 'Provisioner': return 'clinicalNote';
      default: return 'clinicalNote'; // Unknown role fallback
    }
  };

  // Handle Add Note - includes case sheet entry creation
  const handleAddNote = async () => {
    if (addingNote) return; // Prevent multiple simultaneous calls
    if (!newNoteContent.trim()) return;

    setAddingNote(true);
    try {
      const result = await PatientService.addNoteComment(patient.id, newNoteContent.trim(), currentUser.id, currentUser.name, currentUser.role);

      if (result && result.success) {
        // Use note from atomic response (includes real ID from backend)
        const newNote: noteComment = result.medical_record;
        onNoteAdded(newNote);

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

        setNewNoteContent('');
        setIsAddingNote(false);
      } else {
        throw new Error('Atomic operation failed');
      }

    } catch (error) {
      // Error handled silently
      alert('Failed to add note. Please try again.');
    } finally {
      setAddingNote(false);
    }
  };

  // Handle Edit Note - includes case sheet audit entry
  const handleEditNote = async (noteId: string) => {
    if (!editingNoteContent.trim()) return;

    setEditingNote(true);
    try {
      await PatientService.editNoteComment(patient.id, noteId, editingNoteContent.trim(), currentUser.id);

      // Backend provides proper edit timestamp
      const editedAt = new Date().toISOString(); // Temporary - backend determines actual edit time
      onNoteEdited(noteId, editingNoteContent.trim(), editedAt);

      setEditingNoteId(null);
      setEditingNoteContent('');

      // Add edit to case sheet for audit trail using authenticated service
      try {
        const caseResult = await PatientCaseService.addCaseEntry(
          patient.id,
          {
            entryType: getRoleBasedNoteType(currentUser.role),
            description: `Note edited: "${editingNoteContent.trim()}"`,
            performedBy: currentUser.id
          },
          currentUser.id
        );

        if (caseResult) {
          const editCaseEntry: caseSheetEntry = {
            id: caseResult.id,
            timestamp: caseResult.timestamp || new Date().toISOString(),
            type: getRoleBasedNoteType(currentUser.role),
            description: `Note edited: "${editingNoteContent.trim()}"`,
            performedBy: currentUser.staffId,
            canEdit: PatientService.canEditItem(caseResult.timestamp || new Date().toISOString())
          };
          addCaseSheetEntry(editCaseEntry);
        }
      } catch (caseError) {
        // Warning noted
      }

    } catch (error) {
      // Error handled silently
      alert('Failed to edit note. Please try again.');
    } finally {
      setEditingNote(false);
    }
  };

  // Cancel editing
  const cancelEditingNote = () => {
    setEditingNoteId(null);
    setEditingNoteContent('');
  };

  if (!isAddingNote && !editingNoteId) {
    return null; // No editing interface needed
  }

  return (
    <>
      {/* Add New Note Interface */}
      {isAddingNote && PermissionUtils.canEditNotes(currentUser.role) && (
        <div className="mb-2 p-2 bg-blue-50 rounded-lg border">
          <div className="flex items-start space-x-2">
            <div className="bg-blue-600 text-white w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium">
              {currentUser.name.split(' ').map(n => n[0]).join('')}
            </div>
            <div className="flex-1">
              <div className="text-xs font-medium text-gray-900 mb-1">
                {currentUser.name} ({currentUser.role})
              </div>
              <textarea
                value={newNoteContent}
                onChange={(e) => setNewNoteContent(e.target.value)}
                placeholder="Add a clinical note..."
                className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-sm"
                rows={2}
              />
              <div className="flex space-x-2 mt-2">
                <button
                  onClick={handleAddNote}
                  disabled={addingNote || !newNoteContent.trim()}
                  className="flex items-center space-x-1 px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-sm"
                >
                  {addingNote ? (
                    <>
                      <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      <span>Adding...</span>
                    </>
                  ) : (
                    <>
                      <Send className="w-3 h-3" />
                      <span>Add</span>
                    </>
                  )}
                </button>
                <button
                  onClick={() => {
                    setIsAddingNote(false);
                    setNewNoteContent('');
                  }}
                  className="flex items-center space-x-1 px-3 py-1 bg-gray-600 text-white rounded-lg hover:bg-gray-700 text-sm"
                >
                  <X className="w-3 h-3" />
                  <span>Cancel</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit Note Interface */}
      {editingNoteId && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-4 w-full max-w-md">
            <h3 className="text-lg font-medium mb-3">Edit Note</h3>
            <textarea
              value={editingNoteContent}
              onChange={(e) => setEditingNoteContent(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-sm"
              rows={4}
            />
            <div className="flex justify-end space-x-2 mt-3">
              <button
                onClick={() => debounce(() => handleEditNote(editingNoteId), 300)()}
                disabled={editingNote || !editingNoteContent.trim()}
                className="flex items-center space-x-1 px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:bg-gray-400"
              >
                {editingNote ? (
                  <>
                    <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>Saving...</span>
                  </>
                ) : (
                  <>
                    <Save className="w-3 h-3" />
                    <span>Save</span>
                  </>
                )}
              </button>
              <button
                onClick={cancelEditingNote}
                className="flex items-center space-x-1 px-3 py-1 bg-gray-600 text-white rounded text-sm hover:bg-gray-700"
              >
                <X className="w-3 h-3" />
                <span>Cancel</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};