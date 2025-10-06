/**
 * HandoffNotes - Shift handoff notes management (Refactored)
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade shift handoff with priority levels
 */

import React from 'react';
import { Plus, Clock } from 'lucide-react';
import { user, caseSheetEntry } from '../../types';
import { formatDateTime } from '../../utils';
import { PermissionUtils } from '../../utils/permissionUtils';
import { PatientService } from '../../services';

interface HandoffNotesProps {
  currentUser: user;
  caseSheet: caseSheetEntry[];
  addCaseSheetEntry: (entry: caseSheetEntry) => void;
}

export const HandoffNotes: React.FC<HandoffNotesProps> = ({
  currentUser,
  caseSheet,
  addCaseSheetEntry
}) => {

  // Handle adding a new handoff note
  const handleAddHandoffNote = () => {
    // Determine current shift based on time
    const hour = new Date().getHours();
    const shift = hour < 16 ? 'day' : hour < 23 ? 'evening' : 'night';

    // Prompt for handoff note content
    const handoffNote = prompt(`Add handoff note for ${shift} shift:\n\nNote categories:\n• Medication changes\n• Assessment findings\n• Safety concerns\n• Family updates\n• Other\n\nEnter your handoff note:`);

    if (handoffNote && handoffNote.trim()) {
      // Prompt for priority level
      const priority = prompt('Set priority level:\n\n1 = Low\n2 = Medium\n3 = High\n4 = Critical\n\nEnter number (1-4):') || '2';
      const priorityMap = { '1': 'low', '2': 'medium', '3': 'high', '4': 'critical' };
      const priorityLevel = priorityMap[priority as keyof typeof priorityMap] || 'medium';

      // Create handoff case sheet entry - backend must provide proper ID and timestamp
      const handoffEntry: caseSheetEntry = {
        id: 'pending_handoff', // Will be replaced with backend-provided ID
        timestamp: new Date().toISOString(), // Medical action timestamp from frontend
        type: 'handoffNote',
        description: `${shift.toUpperCase()} SHIFT HANDOFF - ${priorityLevel.toUpperCase()} PRIORITY: ${handoffNote}`,
        performedBy: currentUser.staffId,
        canEdit: true, // Backend will determine final value
        details: {
          shift,
          priority: priorityLevel,
          fromNurse: currentUser.name,
          category: 'general',
          note: handoffNote
        }
      };

      addCaseSheetEntry(handoffEntry);

      // Show confirmation
      alert(`✅ Handoff note added for ${shift} shift!\n\nPriority: ${priorityLevel}\nFrom: ${currentUser.name}\n\nNote logged in case sheet for continuity of care.`);
    }
  };

  // Get priority styling
  const getPriorityStyles = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
      default:
        return 'bg-green-100 text-green-800';
    }
  };

  // Filter and sort handoff notes
  const handoffNotes = caseSheet
    .filter(entry => entry.type === 'handoffNote')
    .slice(0, 3); // Show last 3 handoff notes

  // Render individual handoff note
  const renderHandoffNote = (handoff: caseSheetEntry) => (
    <div key={handoff.id} className="bg-purple-50 border border-purple-200 rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <span className="text-xs font-medium text-purple-700">
            {handoff.details?.shift?.toUpperCase() || 'GENERAL'} SHIFT
          </span>
          <div className={`px-2 py-0.5 rounded text-xs font-medium ${
            getPriorityStyles(handoff.details?.priority)
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
  );

  // Render empty state
  const renderEmptyState = () => (
    <div className="text-center py-4">
      <div className="text-gray-400 mb-2">
        <Clock className="w-8 h-8 mx-auto" />
      </div>
      <p className="text-sm text-gray-500">No handoff notes yet</p>
      <p className="text-xs text-gray-400 mt-1">Add shift handoff notes to ensure continuity of care</p>
    </div>
  );

  return (
    <div>
      {/* Section Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-purple-800 flex items-center space-x-2">
          <div className="w-6 h-6 bg-purple-100 rounded-lg flex items-center justify-center">
            🔄
          </div>
          <span>Shift Handoff Notes</span>
        </h3>

        {/* Add Handoff Button */}
        {PermissionUtils.canEditNotes(currentUser.role) && (
          <button
            onClick={handleAddHandoffNote}
            className="flex items-center space-x-2 px-3 py-1 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm"
          >
            <Plus className="w-4 h-4" />
            <span>Add Handoff</span>
          </button>
        )}
      </div>

      {/* Handoff Notes List */}
      <div className="space-y-2">
        {handoffNotes.length > 0 ? (
          handoffNotes.map(renderHandoffNote)
        ) : (
          renderEmptyState()
        )}
      </div>
    </div>
  );
};