// PatientGrid.tsx - Patient grid display component
import React from 'react';
import { Users } from 'lucide-react';
import { patient, user } from '../../types';
import PatientCard from '../../PatientCard';

interface PatientGridProps {
  patients: patient[];
  currentUser: user;
  loading: boolean;
  settings: any;
  onPatientClick: (patient: patient) => void;
  onVitalClick: (patient: patient, vitalType: string) => void;
  onAcknowledgeAlert: (patient: patient, alertId: string) => void;
  onBedsideMode: (patient: patient) => void;
  onToggleECGMode: (patient: patient) => void;
  onRefreshData: () => void;
}

export const PatientGrid: React.FC<PatientGridProps> = ({
  patients,
  currentUser,
  loading,
  settings,
  onPatientClick,
  onVitalClick,
  onAcknowledgeAlert,
  onBedsideMode,
  onToggleECGMode,
  onRefreshData
}) => {
  // Get CSS animation speed based on settings
  const getScrollSpeed = () => {
    const speed = settings.autoscrollspeed || 30;
    const baseSpeed = Math.max(20, 100 - speed); // 20-70 seconds range

    // Adjust speed based on patient count to prevent insane scrolling
    const patientCount = patients.length;
    const minSpeedForCount = Math.max(30, patientCount * 3); // Minimum 30s, +3s per patient

    const finalSpeed = Math.max(baseSpeed, minSpeedForCount);

    if (patientCount > 10) {
      console.log(`🐌 Scroll speed adjusted: ${patientCount} patients, ${finalSpeed}s duration`);
    }

    return finalSpeed;
  };

  // Split patients into rows - 2 cards per row
  const topRowPatients = patients.filter((_, index) => {
    const groupOf4 = Math.floor(index / 4);
    const positionInGroup = index % 4;
    return positionInGroup < 2; // First 2 of each group of 4
  });

  const bottomRowPatients = patients.filter((_, index) => {
    const groupOf4 = Math.floor(index / 4);
    const positionInGroup = index % 4;
    return positionInGroup >= 2; // Last 2 of each group of 4
  });

  if (patients.length === 0 && !loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <Users className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Patients Found</h3>
          <p className="text-gray-600 mb-4">
            No patients are currently assigned or match the current filters.
          </p>
          <button
            onClick={onRefreshData}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Refresh Data
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col gap-1.5 relative">
      {/* Auto-scroll indicator */}
      {settings.enableautoscroll && patients.length > 4 && (
        <div className="absolute top-2 right-2 z-10 bg-blue-600 text-white px-3 py-1 rounded-full text-xs font-medium">
          Auto-scroll: {settings.autoscrollspeed || 30}px/s • {patients.length} patients
        </div>
      )}

      {/* Top Row - 2 Cards with Manual + Auto scroll */}
      <div className="flex-1 patient-row-scroll overflow-x-auto overflow-y-hidden">
        <div
          className={`h-full flex gap-1.5 ${settings.enableautoscroll && patients.length > 4 ? 'patient-infinite-scroll' : ''}`}
          style={{
            minWidth: 'max-content',
            animationDuration: settings.enableautoscroll ? `${getScrollSpeed()}s` : 'none',
            animationPlayState: settings.enableautoscroll ? 'running' : 'paused'
          }}
        >
          {/* Original patients */}
          {topRowPatients.map((patient) => (
            <div key={`top-original-${patient.id}`} className="flex-shrink-0 patient-card-container" style={{ width: '500px' }}>
              <PatientCard
                patient={patient}
                currentUser={currentUser}
                onPatientClick={onPatientClick}
                onVitalClick={onVitalClick}
                onAcknowledgeAlert={onAcknowledgeAlert}
                onBedsideMode={onBedsideMode}
                onToggleECGMode={onToggleECGMode}
              />
            </div>
          ))}
          {/* Duplicate for seamless scroll - only if auto-scroll enabled and enough patients */}
          {settings.enableautoscroll && patients.length > 4 && topRowPatients.map((patient) => (
            <div key={`top-duplicate-${patient.id}`} className="flex-shrink-0 patient-card-container" style={{ width: '500px' }}>
              <PatientCard
                patient={patient}
                currentUser={currentUser}
                onPatientClick={onPatientClick}
                onVitalClick={onVitalClick}
                onAcknowledgeAlert={onAcknowledgeAlert}
                onBedsideMode={onBedsideMode}
                onToggleECGMode={onToggleECGMode}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Bottom Row - 2 Cards with Manual + Auto scroll */}
      <div className="flex-1 patient-row-scroll overflow-x-auto overflow-y-hidden">
        <div
          className={`h-full flex gap-1.5 ${settings.enableautoscroll && patients.length > 4 ? 'patient-infinite-scroll' : ''}`}
          style={{
            minWidth: 'max-content',
            animationDuration: settings.enableautoscroll ? `${getScrollSpeed()}s` : 'none',
            animationPlayState: settings.enableautoscroll ? 'running' : 'paused'
          }}
        >
          {/* Original patients */}
          {bottomRowPatients.map((patient) => (
            <div key={`bottom-original-${patient.id}`} className="flex-shrink-0 patient-card-container" style={{ width: '500px' }}>
              <PatientCard
                patient={patient}
                currentUser={currentUser}
                onPatientClick={onPatientClick}
                onVitalClick={onVitalClick}
                onAcknowledgeAlert={onAcknowledgeAlert}
                onBedsideMode={onBedsideMode}
                onToggleECGMode={onToggleECGMode}
              />
            </div>
          ))}
          {/* Duplicate for seamless scroll - only if auto-scroll enabled and enough patients */}
          {settings.enableautoscroll && patients.length > 4 && bottomRowPatients.map((patient) => (
            <div key={`bottom-duplicate-${patient.id}`} className="flex-shrink-0 patient-card-container" style={{ width: '500px' }}>
              <PatientCard
                patient={patient}
                currentUser={currentUser}
                onPatientClick={onPatientClick}
                onVitalClick={onVitalClick}
                onAcknowledgeAlert={onAcknowledgeAlert}
                onBedsideMode={onBedsideMode}
                onToggleECGMode={onToggleECGMode}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};