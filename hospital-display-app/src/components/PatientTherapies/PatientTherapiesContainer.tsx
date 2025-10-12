/**
 * PatientTherapiesContainer - Main therapies management container
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data, no kebab-case
 */

import React from 'react';
import { Heart } from 'lucide-react';
import { patient, user, therapy, caseSheetEntry } from '../../types';
import { PermissionUtils } from '../../utils/permissionUtils';
import { usePatientTherapies } from '../../hooks/usePatientTherapies';
import { AddTherapyForm, NewTherapy } from './AddTherapyForm';
import { TherapyList } from './TherapyList';

interface PatientTherapiesContainerProps {
  patient: patient;
  currentUser: user;
  therapies: therapy[];
  setTherapies: React.Dispatch<React.SetStateAction<therapy[]>>;
  addCaseSheetEntry: (entry: caseSheetEntry) => void;
  setCaseEntries: React.Dispatch<React.SetStateAction<caseSheetEntry[]>>;
  refreshPatientData?: () => Promise<void>;
}

export const PatientTherapiesContainer: React.FC<PatientTherapiesContainerProps> = ({
  patient,
  currentUser,
  therapies,
  setTherapies,
  addCaseSheetEntry,
  setCaseEntries,
  refreshPatientData
}) => {
  const {
    isAddingTherapy,
    setIsAddingTherapy,
    newTherapy,
    setNewTherapy,
    addingTherapy,
    handleAddTherapy,
    handleCancelAddTherapy,
    handleAddTherapySession,
    handleCompleteTherapy,
    handleCancelTherapy
  } = usePatientTherapies({
    patient,
    currentUser,
    therapies,
    setTherapies,
    addCaseSheetEntry,
    setCaseEntries,
    refreshPatientData
  });

  return (
    <div className="p-4 h-full flex flex-col">
      {/* Prescribe Button */}
      {PermissionUtils.canEditMedications(currentUser.role) && (
        <div className="flex justify-end mb-3">
          <button
            onClick={() => setIsAddingTherapy(true)}
            className="flex items-center space-x-2 px-3 py-1 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm"
          >
            <Heart className="w-4 h-4" />
            <span>Prescribe</span>
          </button>
        </div>
      )}

      {/* Add Therapy Form */}
      <AddTherapyForm
        currentUser={currentUser}
        isAddingTherapy={isAddingTherapy}
        newTherapy={newTherapy}
        addingTherapy={addingTherapy}
        setNewTherapy={setNewTherapy}
        onAdd={handleAddTherapy}
        onCancel={handleCancelAddTherapy}
      />

      {/* Therapies List */}
      <div className="flex-1 overflow-y-auto">
        <TherapyList
          therapies={therapies}
          currentUser={currentUser}
          onAddSession={handleAddTherapySession}
          onComplete={handleCompleteTherapy}
          onCancel={handleCancelTherapy}
        />
      </div>
    </div>
  );
};
