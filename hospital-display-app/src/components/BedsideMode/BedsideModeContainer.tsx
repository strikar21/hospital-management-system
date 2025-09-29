/**
 * BedsideModeContainer - Main bedside monitor container component
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade ICU bedside monitoring system with dual display support
 */

import React from 'react';
import { AlertTriangle, Monitor } from 'lucide-react';
import { patient, user, appsettings } from '../../types';
import { MedicalUtils } from '../../utils/medicalUtils';
import { useBedsideMode } from '../../hooks/useBedsideMode';
import { PatientMonitor } from './PatientMonitor';
import { BedsideModeHeader } from './BedsideModeHeader';
import { NFCLoginModal } from './NFCLoginModal';

interface BedsideModeContainerProps {
  patients: patient[];
  displayCount: 1 | 2;
  onClose: () => void;
  onDisplayCountChange: (count: 1 | 2) => void;
  onNFCTap?: (user: user) => void;
  settings?: appsettings;
}

export const BedsideModeContainer: React.FC<BedsideModeContainerProps> = ({
  patients,
  displayCount,
  onClose,
  onDisplayCountChange,
  onNFCTap,
  settings
}) => {
  const {
    currentTime,
    isOnline,
    showSettings,
    showNFCLogin,
    audioAlarmsEnabled,
    isECGMode,
    currentPatientIndex,
    setShowSettings,
    setShowNFCLogin,
    setAudioAlarmsEnabled,
    setIsECGMode,
    handleNFCScan,
    handlePreviousPatient,
    handleNextPatient,
    handleDisplayModeChange
  } = useBedsideMode({ patients, settings, onNFCTap });

  // Handle display count change with patient index reset
  const handleDisplayCountChangeWrapper = (count: 1 | 2) => {
    handleDisplayModeChange(count, onDisplayCountChange);
  };

  return (
    <div className="fixed inset-0 bg-black z-50 flex flex-col">
      <BedsideModeHeader
        patients={patients}
        displayCount={displayCount}
        isECGMode={isECGMode}
        audioAlarmsEnabled={audioAlarmsEnabled}
        currentPatientIndex={currentPatientIndex}
        onClose={onClose}
        onDisplayCountChange={handleDisplayCountChangeWrapper}
        onECGModeChange={setIsECGMode}
        onAudioAlarmsToggle={() => setAudioAlarmsEnabled(!audioAlarmsEnabled)}
        onShowNFCLogin={() => setShowNFCLogin(true)}
        onShowSettings={() => setShowSettings(!showSettings)}
        onPreviousPatient={handlePreviousPatient}
        onNextPatient={handleNextPatient}
      />

      <NFCLoginModal
        showNFCLogin={showNFCLogin}
        onNFCScan={handleNFCScan}
        onClose={() => setShowNFCLogin(false)}
      />

      <div className="flex-1 flex overflow-hidden">
        {displayCount === 1 ? (
          // Single patient mode
          patients[currentPatientIndex] ? (
            <PatientMonitor
              key={patients[currentPatientIndex].id}
              patient={patients[currentPatientIndex]}
              position="single"
              displayCount={displayCount}
              isECGMode={isECGMode}
              isOnline={isOnline}
              currentTime={currentTime}
            />
          ) : (
            <div className="flex-1 flex items-center justify-center bg-gray-950 text-gray-400">
              <div className="text-center">
                <Monitor className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p className="text-xl">No Patient Data Available</p>
              </div>
            </div>
          )
        ) : (
          // Dual patient mode - show two patients side by side
          patients.slice(0, 2).map((patient, index) => (
            <PatientMonitor
              key={patient.id}
              patient={patient}
              position={index === 0 ? 'left' : 'right'}
              displayCount={displayCount}
              isECGMode={isECGMode}
              isOnline={isOnline}
              currentTime={currentTime}
            />
          ))
        )}
      </div>

      {patients.some(p =>
        p.alerts.some(a => !a.isAcknowledged && a.severity === 'critical') ||
        MedicalUtils.detectArrhythmia(p.vitals.heartRate, p.vitals.ecgReading)
      ) && (
        <div className="bg-red-900 text-red-100 py-3 px-6 text-center border-t-2 border-red-600">
          <div className="flex items-center justify-center space-x-3">
            <AlertTriangle className="w-5 h-5 animate-pulse" />
            <span className="text-base font-bold tracking-wide">CRITICAL ALERTS REQUIRE IMMEDIATE ATTENTION</span>
            <AlertTriangle className="w-5 h-5 animate-pulse" />
          </div>
        </div>
      )}
    </div>
  );
};