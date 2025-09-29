/**
 * BedsideMode - Bedside Monitor (Refactored)
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade ICU bedside monitoring system - now modularized into 5 components
 */

import React from 'react';
import { patient, user, appsettings } from './types';
import { BedsideModeContainer } from './components/BedsideMode';

interface BedsideModeProps {
  patients: patient[];
  displayCount: 1 | 2;
  onClose: () => void;
  onDisplayCountChange: (count: 1 | 2) => void;
  onNFCTap?: (user: user) => void;
  settings?: appsettings;
}

export const BedsideMode: React.FC<BedsideModeProps> = (props) => {
  return <BedsideModeContainer {...props} />;
};