/**
 * PatientInvestigationsContainer - Main investigations management container
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data, no kebab-case
 */

import React, { useState } from 'react';
import { TestTube } from 'lucide-react';
import { patient, user, investigation, caseSheetEntry } from '../../types';
import { PermissionUtils } from '../../utils/permissionUtils';
import { usePatientInvestigations } from '../../hooks/usePatientInvestigations';
import { AddInvestigationForm } from './AddInvestigationForm';
import { InvestigationList } from './InvestigationList';
import { InvestigationDetailModal } from '../modals/InvestigationDetailModal';

interface PatientInvestigationsContainerProps {
  patient: patient;
  currentUser: user;
  investigations: investigation[];
  setInvestigations: React.Dispatch<React.SetStateAction<investigation[]>>;
  addCaseSheetEntry: (entry: caseSheetEntry) => void;
  setCaseEntries: React.Dispatch<React.SetStateAction<caseSheetEntry[]>>;
  refreshPatientData?: () => Promise<void>;
}

export const PatientInvestigationsContainer: React.FC<PatientInvestigationsContainerProps> = ({
  patient,
  currentUser,
  investigations,
  setInvestigations,
  addCaseSheetEntry,
  setCaseEntries,
  refreshPatientData
}) => {
  const {
    isAddingInvestigation,
    setIsAddingInvestigation,
    newInvestigation,
    setNewInvestigation,
    addingInvestigation,
    loadingLabResults,
    handleAddInvestigation,
    handleStartInvestigation,
    handleCompleteInvestigation,
    handleCancelInvestigation,
    handleCancelAddInvestigation
  } = usePatientInvestigations({
    patient,
    currentUser,
    investigations,
    setInvestigations,
    addCaseSheetEntry,
    setCaseEntries,
    refreshPatientData
  });

  const [selectedInvestigation, setSelectedInvestigation] = useState<investigation | null>(null);

  return (
    <div className="p-4 h-full flex flex-col">
      {/* Order Test Button */}
      {PermissionUtils.canEditMedications(currentUser.role) && (
        <div className="flex justify-end mb-3">
          <button
            onClick={() => setIsAddingInvestigation(true)}
            className="flex items-center space-x-2 px-3 py-1 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm"
          >
            <TestTube className="w-4 h-4" />
            <span>Order Test</span>
          </button>
        </div>
      )}

      {/* Add Investigation Form */}
      <AddInvestigationForm
        currentUser={currentUser}
        isAddingInvestigation={isAddingInvestigation}
        newInvestigation={newInvestigation}
        addingInvestigation={addingInvestigation}
        setNewInvestigation={setNewInvestigation}
        onAdd={handleAddInvestigation}
        onCancel={handleCancelAddInvestigation}
      />

      {/* Investigations List */}
      <div className="flex-1 overflow-y-auto">
        <InvestigationList
          investigations={investigations}
          currentUser={currentUser}
          loadingLabResults={loadingLabResults}
          onStart={handleStartInvestigation}
          onComplete={handleCompleteInvestigation}
          onCancel={handleCancelInvestigation}
          onItemClick={setSelectedInvestigation}
        />
      </div>

      {/* Investigation Detail Modal */}
      {selectedInvestigation && (
        <InvestigationDetailModal
          isOpen={selectedInvestigation !== null}
          onClose={() => setSelectedInvestigation(null)}
          investigation={selectedInvestigation}
        />
      )}
    </div>
  );
};
