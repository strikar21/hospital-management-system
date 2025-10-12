/**
 * PatientDetailContainer - Main patient detail container component
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade patient detail modal with modular architecture
 */

import React, { useState, useEffect } from 'react';
import { patient, user, investigation, therapy, caseSheetEntry, alert as alertType, noteComment } from '../../types';
import { PatientHeader, PatientTabs, PatientOverview, TabId } from './index';
import PatientAlerts from '../PatientAlerts';
import PatientMedications from '../PatientMedications';
import PatientInvestigations from '../PatientInvestigations';
import PatientTherapies from '../PatientTherapies';
import { PatientNotesContainer as PatientNotes } from '../PatientNotes';
import CaseSheetBook from '../../CaseSheetBook';
import { PatientCaseService, PatientCRUDService } from '../../services/patient';

interface PatientDetailContainerProps {
  patient: patient;
  currentUser: user;
  onClose: () => void;
  onVitalClick: (patient: patient, vitalType: string) => void;
  onECGView?: (patient: patient) => void;
  onToggleECGMode?: (patient: patient) => void;
  onPatientDischarge?: (patientId: string) => void;
}

export const PatientDetailContainer: React.FC<PatientDetailContainerProps> = ({
  patient,
  currentUser,
  onClose,
  onVitalClick,
  onECGView,
  onToggleECGMode,
  onPatientDischarge
}) => {

  // Tab state
  const [activeTab, setActiveTab] = useState<TabId>('overview');

  // Medical data state - synced with props
  const [medications, setMedications] = useState(patient.medications || []);
  const [investigations, setInvestigations] = useState<investigation[]>(patient.investigations || []);
  const [therapies, setTherapies] = useState<therapy[]>(patient.therapies || []);
  const [notes, setNotes] = useState<noteComment[]>(patient.notes || []);
  const [alerts, setAlerts] = useState<alertType[]>(patient.alerts || []);
  const [caseSheet, setCaseSheet] = useState<caseSheetEntry[]>(patient.caseSheet || []);

  // Sync local states with props when patient data changes
  useEffect(() => {
    // Initial load from props - subsequent updates come from backend refetch
    setCaseSheet(patient.caseSheet || []);
    setMedications(patient.medications || []);
    setInvestigations(patient.investigations || []);
    setTherapies(patient.therapies || []);
    setNotes(patient.notes || []);
    setAlerts(patient.alerts || []);
  }, [patient]);

  // Load comprehensive patient data with case sheet entries and staff data
  useEffect(() => {
    const loadComprehensivePatientData = async () => {
      try {
        // Comprehensive single API call for all patient data including staff - with authentication
        const patientResponse = await PatientCRUDService.getPatientComplete(patient.id);

        if (patientResponse) {
          // Production: Log to monitoring service - comprehensive patient data received

          // Update all states with fresh comprehensive data
          if (patientResponse.medications) setMedications(patientResponse.medications);
          if (patientResponse.investigations) setInvestigations(patientResponse.investigations);
          if (patientResponse.therapies) setTherapies(patientResponse.therapies);
          if (patientResponse.notes) setNotes(patientResponse.notes);
          if (patientResponse.alerts) setAlerts(patientResponse.alerts);
          if (patientResponse.caseSheet) setCaseSheet(patientResponse.caseSheet);

          // Store staff data globally for consistent name resolution across all tabs
          if (patientResponse.staff) {
            // Production: Log to monitoring service - staff data embedded in patient response
            // TODO: Store staff data in a global context or service for consistent access
          }
        }

        // Also load case sheet entries separately (with embedded staff) as backup
        const entries = await PatientCaseService.getCaseEntries(patient.id);
        // Production: Log to monitoring service - case sheet data received
        if (entries && entries.length > 0) {
          setCaseSheet(entries);
        }
      } catch (error) {
        // Error handled silently
      }
    };

    loadComprehensivePatientData();
  }, [patient.id]);

  // Centralized refresh function - single source of truth for all patient data
  const refreshPatientData = async () => {
    try {
      // Fetch complete patient data with all medical records and staff resolution
      const freshData = await PatientCRUDService.getPatientComplete(patient.id);

      if (freshData) {
        // Update ALL state with fresh data from backend
        if (freshData.medications) setMedications(freshData.medications);
        if (freshData.investigations) setInvestigations(freshData.investigations);
        if (freshData.therapies) setTherapies(freshData.therapies);
        if (freshData.notes) setNotes(freshData.notes);
        if (freshData.alerts) setAlerts(freshData.alerts);
        if (freshData.caseSheet) setCaseSheet(freshData.caseSheet);
      }

      // Also fetch case entries separately (backend doesn't include them in complete response)
      try {
        const caseEntries = await PatientCaseService.getCaseEntries(patient.id);
        if (caseEntries && caseEntries.length > 0) {
          setCaseSheet(caseEntries);
        }
      } catch (caseError) {
        // Failed to refresh case entries - handle silently
        console.error('Failed to refresh case entries:', caseError);
      }
    } catch (error) {
      // Failed to refresh patient data - handle silently
      console.error('Failed to refresh patient data:', error);
    }
  };

  // Legacy function for backwards compatibility - now uses centralized refresh
  const addCaseSheetEntry = async (entry: caseSheetEntry) => {
    // Refresh all patient data to ensure consistency
    await refreshPatientData();
  };

  // Handle tab changes
  const handleTabChange = (tabId: TabId) => {
    setActiveTab(tabId);
  };

  // Handle modal click outside to close
  const handleModalClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  // Prevent modal content clicks from bubbling up
  const handleContentClick = (e: React.MouseEvent) => {
    e.stopPropagation();
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
      onClick={handleModalClick}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-7xl h-[85vh] flex flex-col overflow-hidden"
        onClick={handleContentClick}
      >
        {/* Patient Header */}
        <PatientHeader
          patient={patient}
          currentUser={currentUser}
          onClose={onClose}
          onPatientDischarge={onPatientDischarge}
        />

        {/* Patient Alerts */}
        <PatientAlerts
          patient={patient}
          currentUser={currentUser}
          alerts={alerts}
          setAlerts={setAlerts}
        />


        {/* Tab Navigation */}
        <PatientTabs
          activeTab={activeTab}
          onTabChange={handleTabChange}
          notes={notes}
        />

        {/* Tab Content - Fixed Height to Prevent Scrolling */}
        <div className="flex-1 overflow-hidden">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <PatientOverview
              patient={patient}
              onVitalClick={onVitalClick}
              onECGView={onECGView}
              onToggleECGMode={onToggleECGMode}
            />
          )}

          {/* Notes Tab */}
          {activeTab === 'notes' && (
            <PatientNotes
              patient={patient}
              currentUser={currentUser}
              notes={notes}
              setNotes={setNotes}
              caseSheet={caseSheet}
              addCaseSheetEntry={addCaseSheetEntry}
              setCaseEntries={setCaseSheet}
              refreshPatientData={refreshPatientData}
            />
          )}

          {/* Medications Tab */}
          {activeTab === 'medications' && (
            <PatientMedications
              patient={patient}
              currentUser={currentUser}
              medications={medications}
              setMedications={setMedications}
              addCaseSheetEntry={addCaseSheetEntry}
              setCaseEntries={setCaseSheet}
              refreshPatientData={refreshPatientData}
            />
          )}

          {/* Investigation Tab */}
          {activeTab === 'investigations' && (
            <PatientInvestigations
              patient={patient}
              currentUser={currentUser}
              investigations={investigations}
              setInvestigations={setInvestigations}
              addCaseSheetEntry={addCaseSheetEntry}
              setCaseEntries={setCaseSheet}
              refreshPatientData={refreshPatientData}
            />
          )}

          {/* Therapy Tab */}
          {activeTab === 'therapy' && (
            <PatientTherapies
              patient={patient}
              currentUser={currentUser}
              therapies={therapies}
              setTherapies={setTherapies}
              addCaseSheetEntry={addCaseSheetEntry}
              setCaseEntries={setCaseSheet}
              refreshPatientData={refreshPatientData}
            />
          )}

          {/* Case Sheet Tab */}
          {activeTab === 'casesheet' && (
            <CaseSheetBook caseSheet={caseSheet} />
          )}
        </div>
      </div>
    </div>
  );
};