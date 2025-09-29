/**
 * ECGViewer - Continuous Real-time ECG/EEG Display (Refactored)
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade ECG/EEG monitoring system - now modularized into 4 components
 */

import React from 'react';
import { patient } from './types';
import { ECGViewerContainer } from './components/ECGViewer/';

interface ECGViewerProps {
  patient: patient;
  onClose: () => void;
}

export const ECGViewer: React.FC<ECGViewerProps> = (props) => {
  return <ECGViewerContainer {...props} />;
};