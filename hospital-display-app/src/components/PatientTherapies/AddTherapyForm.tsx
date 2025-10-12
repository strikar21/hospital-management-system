/**
 * AddTherapyForm - Therapy prescription form component
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data, no kebab-case
 */

import React from 'react';
import { Save, X } from 'lucide-react';
import { user } from '../../types';
import { PermissionUtils } from '../../utils/permissionUtils';

export interface NewTherapy {
  type: 'physiotherapy' | 'occupational' | 'speech' | 'respiratory';
  description: string;
  frequency: string;
  duration: string;
}

interface AddTherapyFormProps {
  currentUser: user;
  isAddingTherapy: boolean;
  newTherapy: NewTherapy;
  addingTherapy: boolean;
  setNewTherapy: React.Dispatch<React.SetStateAction<NewTherapy>>;
  onAdd: () => void;
  onCancel: () => void;
}

export const AddTherapyForm: React.FC<AddTherapyFormProps> = ({
  currentUser,
  isAddingTherapy,
  newTherapy,
  addingTherapy,
  setNewTherapy,
  onAdd,
  onCancel
}) => {
  if (!isAddingTherapy || !PermissionUtils.canEditMedications(currentUser.role)) {
    return null;
  }

  return (
    <div className="mb-3 p-3 bg-purple-50 rounded-lg border">
      <h4 className="font-medium mb-2 text-sm">Prescribe New Therapy</h4>
      <div className="grid grid-cols-2 gap-2">
        <select
          value={newTherapy.type}
          onChange={(e) => setNewTherapy(prev => ({ ...prev, type: e.target.value as any }))}
          className="px-2 py-1 border rounded text-sm"
        >
          <option value="physiotherapy">Physiotherapy</option>
          <option value="occupational">Occupational Therapy</option>
          <option value="speech">Speech Therapy</option>
          <option value="respiratory">Respiratory Therapy</option>
        </select>
        <input
          type="text"
          placeholder="Therapy description"
          value={newTherapy.description}
          onChange={(e) => setNewTherapy(prev => ({ ...prev, description: e.target.value }))}
          className="px-2 py-1 border rounded text-sm"
        />
        <input
          type="text"
          placeholder="Frequency (e.g., 3x per week)"
          value={newTherapy.frequency}
          onChange={(e) => setNewTherapy(prev => ({ ...prev, frequency: e.target.value }))}
          className="px-2 py-1 border rounded text-sm"
        />
        <input
          type="text"
          placeholder="Duration (e.g., 4 weeks)"
          value={newTherapy.duration}
          onChange={(e) => setNewTherapy(prev => ({ ...prev, duration: e.target.value }))}
          className="px-2 py-1 border rounded text-sm"
        />
      </div>
      <div className="flex space-x-2 mt-2">
        <button
          onClick={onAdd}
          disabled={addingTherapy || !newTherapy.description}
          className="flex items-center space-x-1 px-3 py-1 bg-purple-600 text-white rounded text-sm hover:bg-purple-700 disabled:bg-gray-400"
        >
          {addingTherapy ? (
            <>
              <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              <span>Adding...</span>
            </>
          ) : (
            <>
              <Save className="w-3 h-3" />
              <span>Prescribe</span>
            </>
          )}
        </button>
        <button
          onClick={onCancel}
          className="flex items-center space-x-1 px-3 py-1 bg-gray-600 text-white rounded text-sm hover:bg-gray-700"
        >
          <X className="w-3 h-3" />
          <span>Cancel</span>
        </button>
      </div>
    </div>
  );
};
