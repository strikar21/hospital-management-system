/**
 * DashboardModals - Modal rendering component for Dashboard
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Handles all modal views including patient detail, charts, settings, and management interfaces
 */

import React from 'react';
import { X } from 'lucide-react';
import { user, patient, appsettings } from '../../types';
import { Header } from '../../Header';
import PatientDetail from '../../PatientDetail';
import { EnhancedVitalChart } from '../../EnhancedVitalChart';
import { ECGViewer } from '../../ECGViewer';
import { DeviceAssignment } from '../../DeviceAssignment';
import { PatientAdmission } from '../../PatientAdmission';
import { DeviceProvisioning } from '../../DeviceProvisioning';
import { NurseAdmissionProcessing } from '../../NurseAdmissionProcessing';
import StaffManagement from '../../StaffManagement';
import { SettingsPanel } from './SettingsPanel';

interface DashboardModalsProps {
  currentUser: user;
  settings: appsettings;
  isOnline: boolean;
  lastSync: Date;
  loading: boolean;
  patients: patient[];
  selectedPatient: patient | null;
  showVitalChart: {patient: patient, vital: string} | null;
  showECGViewer: patient | null;
  showSettings: boolean;
  showDeviceAssignment: boolean;
  showPatientAdmission: boolean;
  showDeviceProvisioning: boolean;
  showNurseAdmission: boolean;
  showStaffManagement: boolean;
  onUpdateSettings: (settings: appsettings) => void;
  onLogout: () => void;
  onBedsideMode: (patients: patient[], displayCount?: 1 | 2) => void;
  onVitalClick: (patient: patient, vitalType: string) => void;
  onPatientDischarge: (patientId: string) => void;
  onCloseModal: () => void;
  onCloseVitalChart: () => void;
  onCloseECGViewer: () => void;
  onCloseSettings: () => void;
  onCloseDeviceAssignment: () => void;
  onClosePatientAdmission: () => void;
  onCloseDeviceProvisioning: () => void;
  onCloseNurseAdmission: () => void;
  onCloseStaffManagement: () => void;
  onSetShowECGViewer: (patient: patient | null) => void;
  onToggleECGMode: (patient: patient) => void;
  onDualBedsideMode: () => void;
}

export const DashboardModals: React.FC<DashboardModalsProps> = ({
  currentUser,
  settings,
  isOnline,
  lastSync,
  loading,
  patients,
  selectedPatient,
  showVitalChart,
  showECGViewer,
  showSettings,
  showDeviceAssignment,
  showPatientAdmission,
  showDeviceProvisioning,
  showNurseAdmission,
  showStaffManagement,
  onUpdateSettings,
  onLogout,
  onBedsideMode,
  onVitalClick,
  onPatientDischarge,
  onCloseModal,
  onCloseVitalChart,
  onCloseECGViewer,
  onCloseSettings,
  onCloseDeviceAssignment,
  onClosePatientAdmission,
  onCloseDeviceProvisioning,
  onCloseNurseAdmission,
  onCloseStaffManagement,
  onSetShowECGViewer,
  onToggleECGMode,
  onDualBedsideMode
}) => {
  // ECG Viewer Modal
  if (showECGViewer) {
    return (
      <ECGViewer
        patient={showECGViewer}
        onClose={onCloseECGViewer}
      />
    );
  }

  // Enhanced Vital Chart Modal
  if (showVitalChart) {
    return (
      <EnhancedVitalChart
        patient={showVitalChart.patient}
        vitalType={showVitalChart.vital}
        currentUser={currentUser}
        onClose={onCloseVitalChart}
      />
    );
  }

  // Device Assignment Page
  if (showDeviceAssignment) {
    return (
      <DeviceAssignment
        currentUser={currentUser}
        onBack={onCloseDeviceAssignment}
      />
    );
  }

  // Patient Admission Page
  if (showPatientAdmission) {
    return (
      <PatientAdmission
        currentUser={currentUser}
        onBack={onClosePatientAdmission}
      />
    );
  }

  // Device Provisioning Page
  if (showDeviceProvisioning) {
    return (
      <DeviceProvisioning
        currentUser={currentUser}
        onBack={onCloseDeviceProvisioning}
      />
    );
  }

  // Nurse Admission Processing Page
  if (showNurseAdmission) {
    return (
      <NurseAdmissionProcessing
        currentUser={currentUser}
        onBack={onCloseNurseAdmission}
      />
    );
  }

  // Staff Management Page
  if (showStaffManagement) {
    return (
      <div className="h-screen flex flex-col bg-gray-50">
        <Header
          currentUser={currentUser}
          onLogout={onLogout}
          isOnline={isOnline}
          lastsync={lastSync}
          roomProximity={null}
          proximityScanning={false}
          showAllDepartments={false}
          loading={false}
          selectedWard="Staff Management"
          patients={[]}
          settings={settings}
          getWardOptions={() => []}
          onWardChange={() => {}}
          onDetectProximity={() => {}}
          onToggleReferralMode={() => {}}
          onRefreshData={() => {}}
          onShowSettings={() => {}}
        />
        <div className="flex-1 p-6">
          <button
            onClick={onCloseStaffManagement}
            className="mb-4 flex items-center space-x-2 text-blue-600 hover:text-blue-800 transition-colors"
          >
            <X className="h-5 w-5" />
            <span>Back to Dashboard</span>
          </button>
          <StaffManagement />
        </div>
      </div>
    );
  }

  // Patient Detail Modal
  if (selectedPatient) {
    return (
      <PatientDetail
        patient={selectedPatient}
        currentUser={currentUser}
        onClose={onCloseModal}
        onVitalClick={onVitalClick}
        onECGView={(patient: patient) => onSetShowECGViewer(patient)}
        onToggleECGMode={(patient: patient) => {
          // Removed console.log for production
        }}
        onPatientDischarge={onPatientDischarge}
      />
    );
  }

  // Settings Panel
  if (showSettings) {
    return (
      <SettingsPanel
        isOpen={showSettings}
        onClose={onCloseSettings}
        currentUser={currentUser}
        patients={patients}
        settings={settings}
        onUpdateSettings={onUpdateSettings}
        onBedsideMode={onDualBedsideMode}
      />
    );
  }

  return null;
};