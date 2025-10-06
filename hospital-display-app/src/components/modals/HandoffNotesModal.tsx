/**
 * HandoffNotesModal - Modal view for shift handoff notes
 * Provides a focused interface for viewing and adding handoff notes
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 */

import React from 'react';
import { MedicalModal } from './MedicalModal';
import { HandoffNotes } from '../PatientNotes/HandoffNotes';
import { user, caseSheetEntry } from '../../types';

interface HandoffNotesModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: user;
  caseSheet: caseSheetEntry[];
  addCaseSheetEntry: (entry: caseSheetEntry) => void;
}

export const HandoffNotesModal: React.FC<HandoffNotesModalProps> = ({
  isOpen,
  onClose,
  currentUser,
  caseSheet,
  addCaseSheetEntry
}) => {
  return (
    <MedicalModal
      isOpen={isOpen}
      onClose={onClose}
      title="Shift Handoff Notes"
      size="lg"
    >
      <HandoffNotes
        currentUser={currentUser}
        caseSheet={caseSheet}
        addCaseSheetEntry={addCaseSheetEntry}
      />
    </MedicalModal>
  );
};
