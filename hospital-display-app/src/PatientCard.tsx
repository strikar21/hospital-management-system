/**
 * PatientCard - Patient card component (Refactored)
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade patient card - now modularized into 2 components
 */

import React from 'react';
import { patient, user } from './types';
import { PatientCardContainer } from './components/PatientCard';

interface PatientCardProps {
  patient: patient;
  currentUser: user;
  onPatientClick: (patient: patient) => void;
  onVitalClick: (patient: patient, vitalType: string) => void;
  onAcknowledgeAlert: (patient: patient, alertId: string) => void;
  onBedsideMode: (patient: patient) => void;
  onToggleECGMode: (patient: patient) => void;
}

const PatientCard: React.FC<PatientCardProps> = (props) => {
  return <PatientCardContainer {...props} />;
};

// Memoize PatientCard for performance optimization
export default React.memo(PatientCard);