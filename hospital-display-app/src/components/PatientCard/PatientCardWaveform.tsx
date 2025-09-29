/**
 * PatientCardWaveform - ECG/EEG waveform display component
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade waveform visualization with lead selection
 */

import React, { useState, useEffect } from 'react';
import { patient, user } from '../../types';

interface PatientCardWaveformProps {
  patient: patient;
  currentUser: user;
  isECGMode: boolean;
  arrhythmiaDetected: boolean;
  seizureActivity: boolean;
  onVitalClick: (patient: patient, vitalType: string) => void;
  onToggleECGMode: (patient: patient) => void;
}

export const PatientCardWaveform: React.FC<PatientCardWaveformProps> = React.memo(({
  patient,
  currentUser,
  isECGMode,
  arrhythmiaDetected,
  seizureActivity,
  onVitalClick,
  onToggleECGMode
}) => {
  const [selectedLead, setSelectedLead] = useState<string>(isECGMode ? 'II' : 'C3-C4');

  // Update selected lead when ECG/EEG mode changes
  useEffect(() => {
    setSelectedLead(isECGMode ? 'II' : 'C3-C4');
  }, [isECGMode]);

  // BACKEND INTEGRATION NEEDED: Replace with VitalService.getWaveformData(patientId, isECGMode)
  // Expected endpoint: GET /api/v1/patients/{id}/waveform?mode=ecg|eeg&lead={selectedLead}
  const pathData = "M 0 25 L 250 25"; // Flat line placeholder until real-time waveform data available

  return (
    <div className="flex-shrink-0">
      <div
        className="h-[85px] p-2 bg-gray-900 rounded-lg hover:bg-gray-800 transition-colors cursor-pointer flex flex-col"
        onClick={(e) => {
          e.stopPropagation();
          onVitalClick(patient, isECGMode ? 'ecgReading' : 'eegReading');
        }}
      >
        {/* All ECG/EEG text consolidated at top with smaller font */}
        <div className="flex items-center justify-between mb-0.5 flex-shrink-0">
          <div className="flex items-center space-x-1.5">
            <div className={`w-1 h-1 rounded-full animate-pulse ${
              isECGMode
                ? (arrhythmiaDetected ? 'bg-yellow-400' : 'bg-green-400')
                : (seizureActivity ? 'bg-red-400' : 'bg-blue-400')
            }`}></div>
            <span className={`text-[10px] ${
              isECGMode ? 'text-green-400' : 'text-blue-400'
            }`}>
              {isECGMode ? 'ECG' : 'EEG'} {isECGMode ? (patient.vitals?.ecgReading || '--') : (patient.vitals?.eegReading || '--')}{isECGMode ? 'mV' : 'μV'}
            </span>
            <span className="text-green-300 text-[10px]">25mm/s</span>
            <select
              value={selectedLead}
              onChange={(e) => {
                e.stopPropagation();
                setSelectedLead(e.target.value);
              }}
              onClick={(e) => e.stopPropagation()}
              className="text-[9px] bg-gray-800 text-green-300 border border-gray-600 rounded px-1"
            >
              {isECGMode ? (
                <>
                  <option value="I">Lead I</option>
                  <option value="II">Lead II</option>
                  <option value="III">Lead III</option>
                  <option value="aVR">aVR</option>
                  <option value="aVL">aVL</option>
                  <option value="aVF">aVF</option>
                  <option value="V1">V1</option>
                  <option value="V2">V2</option>
                  <option value="V3">V3</option>
                  <option value="V4">V4</option>
                  <option value="V5">V5</option>
                  <option value="V6">V6</option>
                </>
              ) : (
                <>
                  <option value="F3-F4">F3-F4</option>
                  <option value="C3-C4">C3-C4</option>
                  <option value="P3-P4">P3-P4</option>
                  <option value="O1-O2">O1-O2</option>
                  <option value="T3-T4">T3-T4</option>
                  <option value="T5-T6">T5-T6</option>
                  <option value="Fp1-Fp2">Fp1-Fp2</option>
                  <option value="F7-F8">F7-F8</option>
                </>
              )}
            </select>
            {isECGMode && arrhythmiaDetected && (
              <span className="text-yellow-400 text-[10px]">⚠️</span>
            )}
            {!isECGMode && seizureActivity && (
              <span className="text-red-400 text-[10px]">🚨</span>
            )}
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="text-[10px] text-gray-400">{patient.vitals?.heartRate || 0} BPM</span>
            {/* Compact ECG/EEG Toggle */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                onToggleECGMode(patient);
              }}
              className={`px-1.5 py-0.5 rounded text-[10px] transition-colors ${
                isECGMode
                  ? 'bg-green-600 text-white hover:bg-green-700'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              }`}
              title={`Switch to ${isECGMode ? 'EEG' : 'ECG'} mode`}
            >
              {isECGMode ? 'EEG' : 'ECG'}
            </button>
          </div>
        </div>

        {/* Pure Waveform Area - No bottom text */}
        <div className="flex-1 min-h-0 relative">
          <svg
            width="100%"
            height="100%"
            viewBox="0 0 250 60"
            className="bg-gray-900 w-full h-full"
            preserveAspectRatio="none"
          >
            <defs>
              <pattern id={`grid-${patient.id}`} width="8" height="8" patternUnits="userSpaceOnUse">
                <path d="M 8 0 L 0 0 0 8" fill="none" stroke="#374151" strokeWidth="0.5" opacity="0.3"/>
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill={`url(#grid-${patient.id})`} />

            <path
              d={pathData}
              fill="none"
              stroke={
                isECGMode
                  ? (arrhythmiaDetected ? "#FBBF24" : "#10B981")
                  : (seizureActivity ? "#EF4444" : "#3B82F6")
              }
              strokeWidth="2"
              className="drop-shadow-sm"
            />
          </svg>

          <div className="absolute inset-0 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity bg-black bg-opacity-20 rounded">
            <span className="text-white text-xs">
              Click for {isECGMode ? 'ECG' : 'EEG'} viewer
            </span>
          </div>
        </div>
      </div>
    </div>
  );
});

PatientCardWaveform.displayName = 'PatientCardWaveform';