/**
 * MedicationList - List of medications with empty state
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data, no kebab-case
 */

import React from 'react';
import { Plus } from 'lucide-react';
import { medication, user, patient } from '../../types';
import { MedicationItem } from './MedicationItem';

interface MedicationListProps {
  medications: medication[];
  patient: patient;
  currentUser: user;
  onAdminister: (medication: medication) => void;
  onStatusChange: (medicationId: string, status: 'active' | 'discontinued' | 'held') => void;
  debounce: (func: (...args: any[]) => void, wait: number) => (...args: any[]) => void;
}

export const MedicationList: React.FC<MedicationListProps> = ({
  medications,
  patient,
  currentUser,
  onAdminister,
  onStatusChange,
  debounce
}) => {
  if (medications.length === 0) {
    return (
      <div className="text-center py-6 text-gray-500">
        <Plus className="w-10 h-10 mx-auto mb-3 opacity-50" />
        <p>No medications prescribed yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {medications.filter(med => med != null).map((med) => (
        <MedicationItem
          key={med.id}
          medication={med}
          patient={patient}
          currentUser={currentUser}
          onAdminister={onAdminister}
          onStatusChange={onStatusChange}
          debounce={debounce}
        />
      ))}
    </div>
  );
};
