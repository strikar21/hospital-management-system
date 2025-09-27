import React, { useState } from 'react';
import {
  MessageCircle, Plus, Send, X, Edit, Save, Clock
} from 'lucide-react';
import { patient, user, noteComment, caseSheetEntry } from '../types';
import { formatDateTime } from '../utils';
import { PermissionUtils } from '../utils/permissionUtils';
import { PatientService } from '../services';

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
  // Notes state
  const [isAddingNote, setIsAddingNote] = useState(false);
  const [newNoteContent, setNewNoteContent] = useState('');
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [editingNoteContent, setEditingNoteContent] = useState('');
  const [addingNote, setAddingNote] = useState(false);
  const [editingNote, setEditingNote] = useState(false);

  // Debounce utility
  const debounce = (func: (...args: any[]) => void, wait: number) => {
    let timeout: NodeJS.Timeout;
    return (...args: any[]) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => func(...args), wait);
    };
  };

  // Get role-based note type
  const getRoleBasedNoteType = (userRole: string): 'doctorNotes' | 'nursingNotes' | 'therapistNotes' | 'technicianNotes' | 'pharmacyNotes' | 'otherNotes' => {
    switch (userRole.toLowerCase()) {
      case 'doctor':
      case 'physician':
        return 'doctorNotes';
      case 'nurse':
      case 'nursing':
        return 'nursingNotes';
      case 'technician':
      case 'tech':
        return 'technicianNotes';
      case 'therapist':
      case 'therapy':
        return 'therapistNotes';
      case 'pharmacist':
        return 'pharmacyNotes';
      default:
        return 'otherNotes';
    }
  };

  // Handle Add Note
  const handleAddNote = async () => {
    if (addingNote) return; // Prevent multiple simultaneous calls
    if (!newNoteContent.trim()) return;

    setAddingNote(true);
    try {
      await PatientService.addNoteComment(patient.id, newNoteContent.trim(), currentUser.id, currentUser.name, currentUser.role);

      const newNote: noteComment = {
        id: 'note_' + Date.now(),
        content: newNoteContent.trim(),
        authorId: currentUser.id,
        authorName: currentUser.name,
        authorRole: currentUser.role,
        timestamp: new Date().toISOString(),
        canEdit: PatientService.canEditItem(new Date().toISOString()),
        isEdited: false
      };

      setNotes(prev => [...prev, newNote]);
      setNewNoteContent('');
      setIsAddingNote(false);

      // Add to case sheet
      try {
        const caseResponse = await fetch(`http://localhost:8001/api/v2/patients/${patient.id}/case-entries`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            entrytype: getRoleBasedNoteType(currentUser.role),
            description: `Note: "${newNoteContent.trim()}"`,
            performedBy: currentUser.name
          })
        });

        if (caseResponse.ok) {
          const caseResult = await caseResponse.json();
          const newCaseEntry: caseSheetEntry = {
            id: caseResult.id || 'cs_note_' + Date.now(),
            timestamp: new Date().toISOString(),
            type: getRoleBasedNoteType(currentUser.role),
            description: `Note: "${newNoteContent.trim()}"`,
            performedBy: currentUser.name,
            canEdit: PatientService.canEditItem(new Date().toISOString())
          };
          addCaseSheetEntry(newCaseEntry);
        }
      } catch (caseError) {
        console.warn('Failed to add note case sheet entry:', caseError);
      }

    } catch (error) {
      console.error('Failed to add note:', error);
      alert('Failed to add note. Please try again.');
    } finally {
      setAddingNote(false);
    }
  };

  // Handle Edit Note
  const handleEditNote = async (noteId: string) => {
    if (!editingNoteContent.trim()) return;

    setEditingNote(true);
    try {
      await PatientService.editNoteComment(patient.id, noteId, editingNoteContent.trim(), currentUser.id);

      setNotes(prev => prev.map(note =>
        note.id === noteId ? {
          ...note,
          content: editingNoteContent.trim(),
          isEdited: true,
          editedAt: new Date().toISOString(),
          canEdit: PatientService.canEditItem(new Date().toISOString())
        } : note
      ));

      setEditingNoteId(null);
      setEditingNoteContent('');

      // Add edit to case sheet
      try {
        const caseResponse = await fetch(`http://localhost:8001/api/v2/patients/${patient.id}/case-entries`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            entrytype: getRoleBasedNoteType(currentUser.role),
            description: `Note edited: "${editingNoteContent.trim()}"`,
            performedBy: currentUser.name
          })
        });

        if (caseResponse.ok) {
          const caseResult = await caseResponse.json();
          const editCaseEntry: caseSheetEntry = {
            id: caseResult.id || 'cs_edit_' + Date.now(),
            timestamp: new Date().toISOString(),
            type: getRoleBasedNoteType(currentUser.role),
            description: `Note edited: "${editingNoteContent.trim()}"`,
            performedBy: currentUser.name,
            canEdit: PatientService.canEditItem(new Date().toISOString())
          };
          addCaseSheetEntry(editCaseEntry);
        }
      } catch (caseError) {
        console.warn('Failed to add note edit case sheet entry:', caseError);
      }

    } catch (error) {
      console.error('Failed to edit note:', error);
      alert('Failed to edit note. Please try again.');
    } finally {
      setEditingNote(false);
    }
  };

  const startEditingNote = (note: noteComment) => {
    setEditingNoteId(note.id);
    setEditingNoteContent(note.content);
  };

  const cancelEditingNote = () => {
    setEditingNoteId(null);
    setEditingNoteContent('');
  };

  return (
    <div className="p-3 h-full flex flex-col">
      {PermissionUtils.canEditNotes(currentUser.role) && (
        <div className="flex justify-end mb-2">
          <button
            onClick={() => setIsAddingNote(true)}
            className="flex items-center space-x-2 px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
          >
            <MessageCircle className="w-4 h-4" />
            <span>Add Note</span>
          </button>
        </div>
      )}

      {/* Add New Note - Compact */}
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

      {/* Notes List - Compact scrollable area */}
      <div className="flex-1 overflow-y-auto space-y-2">
        {notes.slice().reverse().map((note) => (
          <div key={note.id} className="bg-white border rounded-lg p-2">
            <div className="flex items-start space-x-2">
              <div className={`text-white w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                note.authorRole === 'Doctor' ? 'bg-blue-600' :
                note.authorRole === 'Nurse' ? 'bg-green-600' :
                note.authorRole === 'Admin' ? 'bg-purple-600' :
                'bg-gray-600'
              }`}>
                {(note.authorName || 'U').split(' ').map(n => n[0]).join('')}
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-medium text-gray-900 text-sm">{note.authorName}</span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      note.authorRole === 'Doctor' ? 'bg-blue-100 text-blue-800' :
                      note.authorRole === 'Nurse' ? 'bg-green-100 text-green-800' :
                      note.authorRole === 'Admin' ? 'bg-purple-100 text-purple-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {note.authorRole}
                    </span>
                    <span className="text-xs text-gray-500">
                      {formatDateTime(note.timestamp)}
                    </span>
                    {note.isEdited && (
                      <span className="text-xs text-gray-400">
                        (edited {note.editedAt ? formatDateTime(note.editedAt) : ''})
                      </span>
                    )}
                  </div>
                  {note.canEdit && note.authorId === currentUser.id && PermissionUtils.canEditNotes(currentUser.role) && (
                    <button
                      onClick={() => startEditingNote(note)}
                      className="text-gray-500 hover:text-gray-700 p-1"
                      title="Edit note"
                    >
                      <Edit className="w-3 h-3" />
                    </button>
                  )}
                </div>

                {editingNoteId === note.id ? (
                  <div>
                    <textarea
                      value={editingNoteContent}
                      onChange={(e) => setEditingNoteContent(e.target.value)}
                      className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-sm"
                      rows={2}
                    />
                    <div className="flex space-x-2 mt-2">
                      <button
                        onClick={() => debounce(() => handleEditNote(note.id), 300)()}
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
                ) : (
                  <div className="text-gray-700 whitespace-pre-wrap text-sm">
                    {note.content}
                  </div>
                )}

                {!note.canEdit && note.authorId === currentUser.id && (
                  <div className="mt-1 text-xs text-gray-500 flex items-center space-x-1">
                    <Clock className="w-3 h-3" />
                    <span>Edit time expired (24h limit)</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
        {(notes || []).length === 0 && (
          <div className="text-center py-6 text-gray-500">
            <MessageCircle className="w-10 h-10 mx-auto mb-3 opacity-50" />
            <p>No clinical notes yet</p>
            {PermissionUtils.canEditNotes(currentUser.role) && (
              <button
                onClick={() => setIsAddingNote(true)}
                className="mt-3 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Add First Note
              </button>
            )}
          </div>
        )}
      </div>

      {/* Shift Handoff Notes Section */}
      <div className="mt-6 border-t pt-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-purple-800 flex items-center space-x-2">
            <div className="w-6 h-6 bg-purple-100 rounded-lg flex items-center justify-center">
              🔄
            </div>
            <span>Shift Handoff Notes</span>
          </h3>
          {PermissionUtils.canEditNotes(currentUser.role) && (
            <button
              onClick={() => {
                const shift = new Date().getHours() < 16 ? 'day' : new Date().getHours() < 23 ? 'evening' : 'night';
                const handoffNote = prompt(`Add handoff note for ${shift} shift:\n\nNote categories:\n• Medication changes\n• Assessment findings\n• Safety concerns\n• Family updates\n• Other\n\nEnter your handoff note:`);

                if (handoffNote && handoffNote.trim()) {
                  const priority = prompt('Set priority level:\n\n1 = Low\n2 = Medium\n3 = High\n4 = Critical\n\nEnter number (1-4):') || '2';
                  const priorityMap = { '1': 'low', '2': 'medium', '3': 'high', '4': 'critical' };
                  const priorityLevel = priorityMap[priority as keyof typeof priorityMap] || 'medium';

                  // Add to case sheet as handoff note
                  const handoffEntry: caseSheetEntry = {
                    id: 'handoff_' + Date.now(),
                    timestamp: new Date().toISOString(),
                    type: 'handoffNote',
                    description: `${shift.toUpperCase()} SHIFT HANDOFF - ${priorityLevel.toUpperCase()} PRIORITY: ${handoffNote}`,
                    performedBy: currentUser.name,
                    canEdit: PatientService.canEditItem(new Date().toISOString()),
                    details: {
                      shift,
                      priority: priorityLevel,
                      fromNurse: currentUser.name,
                      category: 'general',
                      note: handoffNote
                    }
                  };
                  addCaseSheetEntry(handoffEntry);

                  alert(`✅ Handoff note added for ${shift} shift!\n\nPriority: ${priorityLevel}\nFrom: ${currentUser.name}\n\nNote logged in case sheet for continuity of care.`);
                }
              }}
              className="flex items-center space-x-2 px-3 py-1 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm"
            >
              <Plus className="w-4 h-4" />
              <span>Add Handoff</span>
            </button>
          )}
        </div>

        {/* Display recent handoff notes from case sheet */}
        <div className="space-y-2">
          {caseSheet
            .filter(entry => entry.type === 'handoffNote')
            .slice(0, 3) // Show last 3 handoff notes
            .map((handoff) => (
              <div key={handoff.id} className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-medium text-purple-700">
                      {handoff.details?.shift?.toUpperCase() || 'GENERAL'} SHIFT
                    </span>
                    <div className={`px-2 py-0.5 rounded text-xs font-medium ${
                      handoff.details?.priority === 'critical' ? 'bg-red-100 text-red-800' :
                      handoff.details?.priority === 'high' ? 'bg-orange-100 text-orange-800' :
                      handoff.details?.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-green-100 text-green-800'
                    }`}>
                      {handoff.details?.priority?.toUpperCase() || 'MEDIUM'}
                    </div>
                    <span className="text-xs text-gray-500">
                      {formatDateTime(handoff.timestamp)}
                    </span>
                  </div>
                  <span className="text-xs text-purple-600 font-medium">
                    From: {handoff.performedBy}
                  </span>
                </div>
                <p className="text-sm text-gray-700">
                  {handoff.description.replace(/^.*PRIORITY:\s*/, '')}
                </p>
              </div>
            ))}

          {caseSheet.filter(entry => entry.type === 'handoffNote').length === 0 && (
            <div className="text-center py-4">
              <div className="text-gray-400 mb-2">
                <Clock className="w-8 h-8 mx-auto" />
              </div>
              <p className="text-sm text-gray-500">No handoff notes yet</p>
              <p className="text-xs text-gray-400 mt-1">Add shift handoff notes to ensure continuity of care</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PatientNotes;