/**
 * EnhancedVitalChart - Enhanced vital chart component (Refactored)
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade vital chart modal - now modularized into 3 components
 */

import React from 'react';
import { patient } from './types';
import { VitalChartContainer } from './components/EnhancedVitalChart';

interface EnhancedVitalChartProps {
  patient: patient;
  vitalType: string;
  currentUser?: { id: string; staffId?: string; name: string; role: string };
  onClose: () => void;
}

export const EnhancedVitalChart: React.FC<EnhancedVitalChartProps> = (props) => {
  return <VitalChartContainer {...props} />;
};