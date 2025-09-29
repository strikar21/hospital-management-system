/**
 * DashboardContainer - Main container component for Dashboard
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade dashboard container with state management and layout orchestration
 */

import React from 'react';
import { user, appsettings, patient } from '../../types';
import { useDashboard } from '../../hooks/useDashboard';
import { Header } from '../../Header';
import { DashboardModals } from './DashboardModals';
import { DashboardPagination } from './DashboardPagination';
import { DashboardContent } from './DashboardContent';

interface DashboardContainerProps {
  currentUser: user;
  onLogout: () => void;
  settings: appsettings;
  onUpdateSettings: (settings: appsettings) => void;
  onBedsideMode: (patients: patient[], displayCount?: 1 | 2) => void;
}

export const DashboardContainer: React.FC<DashboardContainerProps> = ({
  currentUser,
  onLogout,
  settings,
  onUpdateSettings,
  onBedsideMode
}) => {
  const {
    // State
    selectedWard,
    roomProximity,
    proximityScanning,
    showAllDepartments,
    isOnline,
    selectedPatient,
    showVitalChart,
    showECGViewer,
    showSettings,
    showDeviceAssignment,
    showPatientAdmission,
    showDeviceProvisioning,
    showNurseAdmission,
    showStaffManagement,
    currentPage,
    PATIENTS_PER_PAGE,
    totalPages,

    // Patient data
    patients,
    loading,
    lastSync,
    totalPatients,

    // State setters
    setSelectedWard,
    setCurrentPage,
    setShowSettings,
    setShowDeviceAssignment,
    setShowPatientAdmission,
    setShowDeviceProvisioning,
    setShowNurseAdmission,
    setShowStaffManagement,
    setSelectedPatient,
    setShowVitalChart,
    setShowECGViewer,

    // Handlers
    handleToggleECGMode,
    handleVitalClick,
    handlePatientDischarge,
    handleAcknowledgeAlert,
    handleSingleBedsideMode,
    handleDualBedsideMode,
    toggleReferralMode,
    handlePatientSelection,
    getWardOptions,
    detectProximity,
    loadPatients,
    closeAllModals
  } = useDashboard({
    currentUser,
    onLogout,
    settings,
    onBedsideMode
  });

  // Check if any modal is open
  const hasActiveModal = selectedPatient || showVitalChart || showECGViewer ||
    showDeviceAssignment || showPatientAdmission || showDeviceProvisioning ||
    showNurseAdmission || showStaffManagement;

  if (hasActiveModal) {
    return (
      <DashboardModals
        currentUser={currentUser}
        settings={settings}
        isOnline={isOnline}
        lastSync={lastSync}
        loading={loading}
        patients={patients}
        selectedPatient={selectedPatient}
        showVitalChart={showVitalChart}
        showECGViewer={showECGViewer}
        showSettings={showSettings}
        showDeviceAssignment={showDeviceAssignment}
        showPatientAdmission={showPatientAdmission}
        showDeviceProvisioning={showDeviceProvisioning}
        showNurseAdmission={showNurseAdmission}
        showStaffManagement={showStaffManagement}
        onUpdateSettings={onUpdateSettings}
        onLogout={onLogout}
        onBedsideMode={onBedsideMode}
        onVitalClick={handleVitalClick}
        onPatientDischarge={handlePatientDischarge}
        onCloseModal={() => setSelectedPatient(null)}
        onCloseVitalChart={() => setShowVitalChart(null)}
        onCloseECGViewer={() => setShowECGViewer(null)}
        onCloseSettings={() => setShowSettings(false)}
        onCloseDeviceAssignment={() => setShowDeviceAssignment(false)}
        onClosePatientAdmission={() => setShowPatientAdmission(false)}
        onCloseDeviceProvisioning={() => setShowDeviceProvisioning(false)}
        onCloseNurseAdmission={() => setShowNurseAdmission(false)}
        onCloseStaffManagement={() => setShowStaffManagement(false)}
        onSetShowECGViewer={setShowECGViewer}
        onToggleECGMode={handleToggleECGMode}
        onDualBedsideMode={handleDualBedsideMode}
      />
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50 overflow-hidden">
      <Header
        currentUser={currentUser}
        isOnline={isOnline}
        lastsync={lastSync}
        roomProximity={roomProximity}
        proximityScanning={proximityScanning}
        showAllDepartments={showAllDepartments}
        loading={loading}
        selectedWard={selectedWard}
        patients={patients}
        getWardOptions={getWardOptions}
        onWardChange={setSelectedWard}
        onDetectProximity={detectProximity}
        onToggleReferralMode={toggleReferralMode}
        onRefreshData={loadPatients}
        onShowSettings={() => setShowSettings(true)}
        onShowDeviceAssignment={() => setShowDeviceAssignment(true)}
        onShowPatientAdmission={() => setShowPatientAdmission(true)}
        onShowDeviceProvisioning={() => setShowDeviceProvisioning(true)}
        onShowNurseAdmission={() => setShowNurseAdmission(true)}
        onShowStaffManagement={() => setShowStaffManagement(true)}
        onLogout={onLogout}
        settings={settings}
      />

      <DashboardPagination
        currentPage={currentPage}
        totalPages={totalPages}
        totalPatients={totalPatients}
        patientsPerPage={PATIENTS_PER_PAGE}
        onPageChange={setCurrentPage}
      />

      <DashboardContent
        currentUser={currentUser}
        patients={patients}
        loading={loading}
        totalPatients={totalPatients}
        selectedWard={selectedWard}
        roomProximity={roomProximity}
        proximityScanning={proximityScanning}
        settings={settings}
        onPatientClick={handlePatientSelection}
        onVitalClick={handleVitalClick}
        onAcknowledgeAlert={handleAcknowledgeAlert}
        onBedsideMode={handleSingleBedsideMode}
        onToggleECGMode={handleToggleECGMode}
        onDetectProximity={detectProximity}
        onRefreshData={loadPatients}
      />

      {/* Settings Panel - renders separately to maintain modal behavior */}
      {showSettings && (
        <div className="fixed inset-0 z-50">
          <DashboardModals
            currentUser={currentUser}
            settings={settings}
            isOnline={isOnline}
            lastSync={lastSync}
            loading={loading}
            patients={patients}
            selectedPatient={null}
            showVitalChart={null}
            showECGViewer={null}
            showSettings={showSettings}
            showDeviceAssignment={false}
            showPatientAdmission={false}
            showDeviceProvisioning={false}
            showNurseAdmission={false}
            showStaffManagement={false}
            onUpdateSettings={onUpdateSettings}
            onLogout={onLogout}
            onBedsideMode={onBedsideMode}
            onVitalClick={handleVitalClick}
            onPatientDischarge={handlePatientDischarge}
            onCloseModal={() => setSelectedPatient(null)}
            onCloseVitalChart={() => setShowVitalChart(null)}
            onCloseECGViewer={() => setShowECGViewer(null)}
            onCloseSettings={() => setShowSettings(false)}
            onCloseDeviceAssignment={() => setShowDeviceAssignment(false)}
            onClosePatientAdmission={() => setShowPatientAdmission(false)}
            onCloseDeviceProvisioning={() => setShowDeviceProvisioning(false)}
            onCloseNurseAdmission={() => setShowNurseAdmission(false)}
            onCloseStaffManagement={() => setShowStaffManagement(false)}
            onSetShowECGViewer={setShowECGViewer}
            onToggleECGMode={handleToggleECGMode}
            onDualBedsideMode={handleDualBedsideMode}
          />
        </div>
      )}
    </div>
  );
};