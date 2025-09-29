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
import PatientNotes from '../PatientNotes';
import CaseSheetBook from '../../CaseSheetBook';
import { PatientCaseService } from '../../services/patient';

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
    setCaseSheet(patient.caseSheet || []);
    setMedications(patient.medications || []);
    setInvestigations(patient.investigations || []);
    setTherapies(patient.therapies || []);
    setNotes(patient.notes || []);
    setAlerts(patient.alerts || []);
  }, [patient]);

  // Load case sheet entries from backend
  useEffect(() => {
    const loadCaseSheetEntries = async () => {
      try {
        const entries = await PatientCaseService.getCaseEntries(patient.id);
        console.log('🏥 Case Sheet Data Received:', entries);
        if (entries && entries.length > 0) {
          setCaseSheet(entries);
        }
      } catch (error) {
        console.error('Failed to load case sheet entries:', error);
      }
    };

    loadCaseSheetEntries();
  }, [patient.id]);

  // Add case sheet entry helper function
  const addCaseSheetEntry = (entry: caseSheetEntry) => {
    setCaseSheet(prev => [...prev, entry]);
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