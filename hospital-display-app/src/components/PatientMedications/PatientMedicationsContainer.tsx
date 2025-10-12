/**
 * PatientMedicationsContainer - Main medications management container
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data, no kebab-case
 */

import React from 'react';
import { Plus, Shield } from 'lucide-react';
import { patient, user, medication, caseSheetEntry } from '../../types';
import { PermissionUtils } from '../../utils/permissionUtils';
import { usePatientMedications } from '../../hooks/usePatientMedications';
import { AddMedicationForm } from './AddMedicationForm';
import { MedicationList } from './MedicationList';

interface PatientMedicationsContainerProps {
  patient: patient;
  currentUser: user;
  medications: medication[];
  setMedications: React.Dispatch<React.SetStateAction<medication[]>>;
  addCaseSheetEntry: (entry: caseSheetEntry) => void;
  setCaseEntries: React.Dispatch<React.SetStateAction<caseSheetEntry[]>>;
  refreshPatientData?: () => Promise<void>;
}

export const PatientMedicationsContainer: React.FC<PatientMedicationsContainerProps> = ({
  patient,
  currentUser,
  medications,
  setMedications,
  addCaseSheetEntry,
  setCaseEntries,
  refreshPatientData
}) => {
  // Use hook for all medication management logic
  const {
    isAddingMedication,
    setIsAddingMedication,
    newMedication,
    setNewMedication,
    handleAddMedication,
    handleMedicationStatusChange,
    handleMedicationAdministration,
    debounce
  } = usePatientMedications({
    patient,
    currentUser,
    medications,
    setMedications,
    addCaseSheetEntry,
    setCaseEntries,
    refreshPatientData
  });

  return (
    <div className="p-3 h-full flex flex-col">
      <div className="flex justify-end mb-2">
        {!PermissionUtils.canEditMedications(currentUser.role) && (
          <span className="text-xs bg-yellow-100 text-yellow-600 px-2 py-1 rounded-lg flex items-center space-x-1">
            <Shield className="w-3 h-3" />
            <span>View Only</span>
          </span>
        )}
        {PermissionUtils.canEditMedications(currentUser.role) && (
          <button
            onClick={() => setIsAddingMedication(true)}
            className="flex items-center space-x-2 px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
          >
            <Plus className="w-4 h-4" />
            <span>Prescribe</span>
          </button>
        )}
      </div>

      {/* Add Medication Form */}
      <AddMedicationForm
        currentUser={currentUser}
        showMedicationForm={isAddingMedication}
        newMedication={newMedication}
        isSubmitting={false} // Hook manages submission state internally
        setNewMedication={setNewMedication}
        onAdd={handleAddMedication}
        onCancel={() => {
          setIsAddingMedication(false);
          setNewMedication({ name: '', dosage: '', frequency: '', route: 'PO', duration: '' });
        }}
      />

      {/* Medications List */}
      <div className="flex-1 overflow-y-auto">
        <MedicationList
          medications={medications}
          patient={patient}
          currentUser={currentUser}
          onAdminister={handleMedicationAdministration}
          onStatusChange={handleMedicationStatusChange}
          debounce={debounce}
        />
      </div>
    </div>
  );
};
