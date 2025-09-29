/**
 * PatientDetail - Main Patient Detail Entry Point (Refactored)
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade patient detail system with modular architecture
 */

import React from 'react';
import { patient, user } from './types';
import { PatientDetailContainer } from './components/PatientDetail';

interface PatientDetailProps {
  patient: patient;
  currentUser: user;
  onClose: () => void;
  onVitalClick: (patient: patient, vitalType: string) => void;
  onECGView?: (patient: patient) => void;
  onToggleECGMode?: (patient: patient) => void;
  onPatientDischarge?: (patientId: string) => void;
}

export const PatientDetail: React.FC<PatientDetailProps> = (props) => {
  return <PatientDetailContainer {...props} />;
};

export default PatientDetail;