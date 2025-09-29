/**
 * Dashboard - Main Dashboard Entry Point (Refactored)
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade dashboard system with modular architecture
 */

import React from 'react';
import { user, appsettings, patient } from './types';
import { DashboardContainer } from './components/Dashboard';

interface DashboardProps {
  currentUser: user;
  onLogout: () => void;
  settings: appsettings;
  onUpdateSettings: (settings: appsettings) => void;
  onBedsideMode: (patients: patient[], displayCount?: 1 | 2) => void;
}

export const Dashboard: React.FC<DashboardProps> = (props) => {
  return <DashboardContainer {...props} />;
};