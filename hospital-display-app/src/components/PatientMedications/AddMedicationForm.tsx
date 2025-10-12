/**
 * AddMedicationForm - Medication prescription form component
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data, no kebab-case
 */

import React from 'react';
import { Save, X } from 'lucide-react';
import { user } from '../../types';
import { PermissionUtils } from '../../utils/permissionUtils';

export interface NewMedication {
  name: string;
  dosage: string;
  frequency: string;
  route: string;
  duration: string;
}

interface AddMedicationFormProps {
  currentUser: user;
  showMedicationForm: boolean;
  newMedication: NewMedication;
  isSubmitting: boolean;
  setNewMedication: React.Dispatch<React.SetStateAction<NewMedication>>;
  onAdd: () => void;
  onCancel: () => void;
}

export const AddMedicationForm: React.FC<AddMedicationFormProps> = ({
  currentUser,
  showMedicationForm,
  newMedication,
  isSubmitting,
  setNewMedication,
  onAdd,
  onCancel
}) => {
  if (!showMedicationForm || !PermissionUtils.canEditMedications(currentUser.role)) {
    return null;
  }

  return (
    <div className="mb-2 p-2 bg-blue-50 rounded-lg border">
      <h4 className="font-medium mb-2 text-sm">Prescribe New Medication</h4>
      <div className="grid grid-cols-2 gap-2">
        <input
          type="text"
          placeholder="Medication name"
          value={newMedication.name}
          onChange={(e) => setNewMedication(prev => ({ ...prev, name: e.target.value }))}
          className="px-2 py-1 border rounded text-sm col-span-2"
        />
        <input
          type="text"
          placeholder="Dosage (e.g., 10mg)"
          value={newMedication.dosage}
          onChange={(e) => setNewMedication(prev => ({ ...prev, dosage: e.target.value }))}
          className="px-2 py-1 border rounded text-sm"
        />
        <input
          type="text"
          placeholder="Frequency (e.g., Twice daily)"
          value={newMedication.frequency}
          onChange={(e) => setNewMedication(prev => ({ ...prev, frequency: e.target.value }))}
          className="px-2 py-1 border rounded text-sm"
        />
        <input
          type="text"
          placeholder="Duration (e.g., 7 days)"
          value={newMedication.duration}
          onChange={(e) => setNewMedication(prev => ({ ...prev, duration: e.target.value }))}
          className="px-2 py-1 border rounded text-sm"
        />
        <select
          value={newMedication.route}
          onChange={(e) => setNewMedication(prev => ({ ...prev, route: e.target.value }))}
          className="px-2 py-1 border rounded text-sm"
        >
          <option value="PO">PO (Oral)</option>
          <option value="IV">IV (Intravenous)</option>
          <option value="IM">IM (Intramuscular)</option>
          <option value="SC">SC (Subcutaneous)</option>
          <option value="Inhaled">Inhaled</option>
          <option value="Topical">Topical</option>
        </select>
      </div>
      <div className="flex space-x-2 mt-2">
        <button
          onClick={onAdd}
          disabled={isSubmitting || !newMedication.name || !newMedication.dosage || !newMedication.frequency || !newMedication.duration}
          className="flex items-center space-x-1 px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:bg-gray-400"
        >
          {isSubmitting ? (
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
