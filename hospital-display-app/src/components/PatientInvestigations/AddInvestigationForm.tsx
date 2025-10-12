/**
 * AddInvestigationForm - Investigation ordering form component
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data, no kebab-case
 */

import React from 'react';
import { Save, X } from 'lucide-react';
import { user } from '../../types';
import { PermissionUtils } from '../../utils/permissionUtils';

export interface NewInvestigation {
  type: 'lab' | 'imaging' | 'biopsy' | 'culture';
  name: string;
  priority: 'routine' | 'urgent' | 'stat';
  notes: string;
}

interface AddInvestigationFormProps {
  currentUser: user;
  isAddingInvestigation: boolean;
  newInvestigation: NewInvestigation;
  addingInvestigation: boolean;
  setNewInvestigation: React.Dispatch<React.SetStateAction<NewInvestigation>>;
  onAdd: () => void;
  onCancel: () => void;
}

export const AddInvestigationForm: React.FC<AddInvestigationFormProps> = ({
  currentUser,
  isAddingInvestigation,
  newInvestigation,
  addingInvestigation,
  setNewInvestigation,
  onAdd,
  onCancel
}) => {
  if (!isAddingInvestigation || !PermissionUtils.canEditMedications(currentUser.role)) {
    return null;
  }

  return (
    <div className="mb-3 p-3 bg-green-50 rounded-lg border">
      <h4 className="font-medium mb-2 text-sm">Order New Investigation</h4>
      <div className="grid grid-cols-2 gap-2">
        <select
          value={newInvestigation.type}
          onChange={(e) => setNewInvestigation(prev => ({ ...prev, type: e.target.value as any }))}
          className="px-2 py-1 border rounded text-sm"
        >
          <option value="lab">Laboratory Test</option>
          <option value="imaging">Imaging Study</option>
          <option value="biopsy">Biopsy</option>
          <option value="culture">Culture</option>
        </select>
        <input
          type="text"
          placeholder="Investigation name"
          value={newInvestigation.name}
          onChange={(e) => setNewInvestigation(prev => ({ ...prev, name: e.target.value }))}
          className="px-2 py-1 border rounded text-sm"
        />
        <select
          value={newInvestigation.priority}
          onChange={(e) => setNewInvestigation(prev => ({ ...prev, priority: e.target.value as any }))}
          className="px-2 py-1 border rounded text-sm"
        >
          <option value="routine">Routine</option>
          <option value="urgent">Urgent</option>
          <option value="stat">STAT</option>
        </select>
        <input
          type="text"
          placeholder="Special instructions"
          value={newInvestigation.notes}
          onChange={(e) => setNewInvestigation(prev => ({ ...prev, notes: e.target.value }))}
          className="px-2 py-1 border rounded text-sm"
        />
      </div>
      <div className="flex space-x-2 mt-2">
        <button
          onClick={onAdd}
          disabled={addingInvestigation || !newInvestigation.name}
          className="flex items-center space-x-1 px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:bg-gray-400"
        >
          {addingInvestigation ? (
            <>
              <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              <span>Ordering...</span>
            </>
          ) : (
            <>
              <Save className="w-3 h-3" />
              <span>Order</span>
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
