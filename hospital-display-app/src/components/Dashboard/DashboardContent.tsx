/**
 * DashboardContent - Main content area for Dashboard patient display
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade patient grid display with empty state handling
 */

import React from 'react';
import { user, patient, roomproximity, appsettings } from '../../types';
import { PatientGrid } from './PatientGrid';
import { EmptyState } from './EmptyState';

interface DashboardContentProps {
  currentUser: user;
  patients: patient[];
  loading: boolean;
  totalPatients: number;
  selectedWard: string;
  roomProximity: roomproximity | null;
  proximityScanning: boolean;
  settings: appsettings;
  onPatientClick: (patient: patient) => void;
  onVitalClick: (patient: patient, vitalType: string) => void;
  onAcknowledgeAlert: (patient: patient, alertId: string) => void;
  onBedsideMode: (patient: patient) => void;
  onToggleECGMode: (patient: patient) => void;
  onDetectProximity: () => void;
  onRefreshData: () => void;
}

export const DashboardContent: React.FC<DashboardContentProps> = ({
  currentUser,
  patients,
  loading,
  totalPatients,
  selectedWard,
  roomProximity,
  proximityScanning,
  settings,
  onPatientClick,
  onVitalClick,
  onAcknowledgeAlert,
  onBedsideMode,
  onToggleECGMode,
  onDetectProximity,
  onRefreshData
}) => {
  return (
    <div className="flex-1 px-4 py-2 overflow-hidden">
      {totalPatients === 0 && !loading ? (
        <EmptyState
          currentUser={currentUser}
          selectedWard={selectedWard}
          roomProximity={roomProximity}
          proximityScanning={proximityScanning}
          onDetectProximity={onDetectProximity}
          onRefreshData={onRefreshData}
        />
      ) : (
        <PatientGrid
          patients={patients}
          currentUser={currentUser}
          loading={loading}
          settings={settings}
          onPatientClick={onPatientClick}
          onVitalClick={onVitalClick}
          onAcknowledgeAlert={onAcknowledgeAlert}
          onBedsideMode={onBedsideMode}
          onToggleECGMode={onToggleECGMode}
          onRefreshData={onRefreshData}
        />
      )}
    </div>
  );
};