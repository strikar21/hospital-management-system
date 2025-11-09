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
import { AlertService } from '../../services/AlertService';
import { formatTimeOnly } from '../../utils';

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

  // Load complete alert history when Alerts tab is opened
  useEffect(() => {
    const loadAlertHistory = async () => {
      if (activeTab === 'alerts') {
        try {
          // Fetch ALL alerts including acknowledged ones from database
          const allAlerts = await AlertService.getPatientAlerts(patient.id, true);

          // ✅ NORMALIZE: Map alertTimestamp → timestamp for frontend compatibility
          const normalizedAlerts = (allAlerts || []).map((alert: any) => ({
            ...alert,
            // Fallback chain: timestamp (if exists) → alertTimestamp (backend) → createdAt (default) → now
            timestamp: alert.timestamp || alert.alertTimestamp || alert.createdAt || new Date().toISOString()
          }));

          // Always update alerts state, even if empty array (to show "No alerts" message)
          setAlerts(normalizedAlerts);
        } catch (error) {
          console.error('Failed to load alert history:', error);
          // Set to empty array on error to show proper empty state
          setAlerts([]);
        }
      }
    };

    loadAlertHistory();
  }, [activeTab, patient.id]);

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
          alerts={alerts}
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

          {/* Alerts Tab */}
          {activeTab === 'alerts' && (
            <div className="h-full overflow-y-auto p-3">
              <h3 className="text-base font-semibold mb-2">Alert History</h3>
              {alerts.length === 0 ? (
                <div className="text-center text-gray-500 py-4 text-sm">
                  No alerts recorded for this patient
                </div>
              ) : (
                <div className="space-y-1">
                  {alerts
                    .sort((a, b) => {
                      const timeA = new Date(a.timestamp || 0).getTime();
                      const timeB = new Date(b.timestamp || 0).getTime();
                      return timeB - timeA;  // Descending (newest first)
                    })
                    .map((alert) => (
                      <div
                        key={alert.id}
                        className={`px-2 py-1 rounded border ${
                          alert.severity === 'critical' ? 'bg-red-50 border-red-200' :
                          alert.severity === 'high' ? 'bg-orange-50 border-orange-200' :
                          alert.severity === 'medium' ? 'bg-yellow-50 border-yellow-200' :
                          'bg-blue-50 border-blue-200'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2 flex-1 min-w-0">
                            <span className="text-sm flex-shrink-0">
                              {alert.severity === 'critical' ? '🚨' :
                               alert.severity === 'high' ? '⚠️' :
                               alert.severity === 'medium' ? '⚡' : 'ℹ️'}
                            </span>
                            <span className={`text-xs font-bold uppercase flex-shrink-0 ${
                              alert.severity === 'critical' ? 'text-red-700' :
                              alert.severity === 'high' ? 'text-orange-700' :
                              alert.severity === 'medium' ? 'text-yellow-700' :
                              'text-blue-700'
                            }`}>
                              {alert.severity}
                            </span>
                            <span className="text-xs text-gray-900 truncate">{alert.message}</span>
                          </div>
                          <div className="flex items-center space-x-2 flex-shrink-0 ml-2">
                            <span className="text-xs text-gray-500">
                              {formatTimeOnly(alert.timestamp)}
                            </span>
                            {alert.acknowledgedBy && (
                              <span className="text-xs text-green-600">✓</span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              )}
            </div>
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