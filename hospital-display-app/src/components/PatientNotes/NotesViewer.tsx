/**
 * NotesViewer - Display notes list and note items (Refactored)
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade notes display with role-based styling
 */

import React from 'react';
import { MessageCircle, Edit, Clock } from 'lucide-react';
import { user, noteComment } from '../../types';
import { formatDateTime } from '../../utils';
import { PermissionUtils } from '../../utils/permissionUtils';

interface NotesViewerProps {
  currentUser: user;
  notes: noteComment[];
  onEditNote: (note: noteComment) => void;
  onAddFirstNote: () => void;
}

export const NotesViewer: React.FC<NotesViewerProps> = ({
  currentUser,
  notes,
  onEditNote,
  onAddFirstNote
}) => {

  // Get role-based styling for author badges
  const getRoleBadgeStyles = (authorRole: string) => {
    const role = authorRole.toLowerCase();
    if (role === 'doctor' || role === 'physician') {
      return {
        avatar: 'bg-blue-600',
        badge: 'bg-blue-100 text-blue-800'
      };
    }
    if (role === 'nurse' || role === 'nursing') {
      return {
        avatar: 'bg-green-600',
        badge: 'bg-green-100 text-green-800'
      };
    }
    if (role === 'admin') {
      return {
        avatar: 'bg-purple-600',
        badge: 'bg-purple-100 text-purple-800'
      };
    }
    return {
      avatar: 'bg-gray-600',
      badge: 'bg-gray-100 text-gray-800'
    };
  };

  // Render individual note item
  const renderNoteItem = (note: noteComment) => {
    const roleStyles = getRoleBadgeStyles(note.authorRole);
    const canUserEditNote = note.canEdit &&
      note.authorId === currentUser.id &&
      PermissionUtils.canEditNotes(currentUser.role);

    return (
      <div key={note.id} className="bg-white border rounded-lg p-2">
        <div className="flex items-start space-x-2">
          {/* Author Avatar */}
          <div className={`text-white w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${roleStyles.avatar}`}>
            {(note.authorName || 'U').split(' ').map(n => n[0]).join('')}
          </div>

          <div className="flex-1">
            {/* Note Header */}
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center space-x-2">
                <span className="font-medium text-gray-900 text-sm">{note.authorName}</span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${roleStyles.badge}`}>
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

              {/* Edit Button */}
              {canUserEditNote && (
                <button
                  onClick={() => onEditNote(note)}
                  className="text-gray-500 hover:text-gray-700 p-1"
                  title="Edit note"
                >
                  <Edit className="w-3 h-3" />
                </button>
              )}
            </div>

            {/* Note Content */}
            <div className="text-gray-700 whitespace-pre-wrap text-sm">
              {note.content}
            </div>

            {/* Edit Time Expired Notice */}
            {!note.canEdit && note.authorId === currentUser.id && (
              <div className="mt-1 text-xs text-gray-500 flex items-center space-x-1">
                <Clock className="w-3 h-3" />
                <span>Edit time expired (24h limit)</span>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  // Render empty state
  const renderEmptyState = () => (
    <div className="text-center py-6 text-gray-500">
      <MessageCircle className="w-10 h-10 mx-auto mb-3 opacity-50" />
      <p>No clinical notes yet</p>
      {PermissionUtils.canEditNotes(currentUser.role) && (
        <button
          onClick={onAddFirstNote}
          className="mt-3 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Add First Note
        </button>
      )}
    </div>
  );

  return (
    <div className="flex-1 overflow-y-auto space-y-2">
      {notes && notes.length > 0 ? (
        // Display notes in reverse chronological order (newest first)
        notes.slice().reverse().map(renderNoteItem)
      ) : (
        renderEmptyState()
      )}
    </div>
  );
};