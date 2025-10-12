/**
 * TherapyItem - Individual therapy display card
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data, no kebab-case
 */

import React from 'react';
import { Plus, XCircle } from 'lucide-react';
import { therapy, user } from '../../types';
import { PermissionUtils } from '../../utils/permissionUtils';

interface TherapyItemProps {
  therapy: therapy;
  currentUser: user;
  onAddSession: (therapy: therapy) => void;
  onComplete: (therapy: therapy) => void;
  onCancel: (therapy: therapy) => void;
}

export const TherapyItem: React.FC<TherapyItemProps> = ({
  therapy,
  currentUser,
  onAddSession,
  onComplete,
  onCancel
}) => {
  return (
    <div className="bg-white border rounded-lg p-3">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-3 mb-1">
            <h4 className="font-medium text-md">{therapy.description}</h4>
            <div className={`px-2 py-1 rounded-full text-xs font-medium ${
              therapy.status === 'active' ? 'bg-green-100 text-green-800' :
              therapy.status === 'completed' ? 'bg-blue-100 text-blue-800' :
              'bg-red-100 text-red-800'
            }`}>
              {therapy.status.toUpperCase()}
            </div>
          </div>
          <div className="text-sm text-gray-600 mb-2">
            <p>
              <span className="font-medium">Type:</span> {therapy.type} •
              <span className="font-medium"> Frequency:</span> {therapy.frequency}
            </p>
            <p>
              <span className="font-medium">Duration:</span> {therapy.duration} •
              <span className="font-medium"> Prescribed by:</span> {therapy.prescribedByName || therapy.prescribedBy || 'Unknown'}
            </p>
            {therapy.therapist && (
              <p><span className="font-medium">Therapist:</span> {therapy.therapist}</p>
            )}
            {therapy.sessions && therapy.sessions.length > 0 && (
              <p><span className="font-medium">Sessions:</span> {therapy.sessions.length} completed</p>
            )}
          </div>
        </div>

        {/* Therapy Actions */}
        {PermissionUtils.canEditMedications(currentUser.role) && therapy.canEdit && (
          <div className="flex items-center space-x-1">
            {therapy.status === 'active' && (
              <>
                <button
                  onClick={() => onAddSession(therapy)}
                  className="p-1 text-blue-600 hover:bg-blue-50 rounded transition-colors text-xs"
                  title="Add therapy session"
                >
                  <Plus className="w-4 h-4" />
                </button>
                <button
                  onClick={() => onComplete(therapy)}
                  className="p-1 text-green-600 hover:bg-green-50 rounded transition-colors text-xs"
                  title="Complete therapy"
                >
                  <XCircle className="w-4 h-4" />
                </button>
                <button
                  onClick={() => onCancel(therapy)}
                  className="p-1 text-red-600 hover:bg-red-50 rounded transition-colors text-xs"
                  title="Cancel therapy"
                >
                  <XCircle className="w-4 h-4" />
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
