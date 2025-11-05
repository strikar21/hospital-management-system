/**
 * PatientCardWaveform - ECG/EEG waveform display component
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade waveform visualization with lead selection
 */

import React from 'react';
import { patient, user } from '../../types';
import { useECGViewer } from '../../hooks/useECGViewer';
import { renderWaveform, adcToMillivolts, adcToMicrovolts } from '../../utils/medicalWaveformUtils';
import { WaveformErrorBoundary } from '../ErrorBoundary';

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
  isECGMode,
  arrhythmiaDetected,
  seizureActivity,
  onVitalClick,
  onToggleECGMode
}) => {
  // Subscribe to real-time waveform data using WebSocket
  const { dataBufferRef } = useECGViewer({ patient });

  console.log(`[PatientCardWaveform] Component render for patient ${patient.id.substring(0, 8)}`);

  // Generate SVG path from real waveform data (Lead II for ECG, F3 for EEG)
  // Uses MEDICAL-GRADE FIXED SCALE rendering (NOT auto-scaling)
  const generatePathData = () => {
    if (!patient.assignedDeviceId) {
      console.log(`[PatientCardWaveform ${patient.id.substring(0, 8)}] No device assigned - showing flat line`);
      return "M 0 30 L 250 30"; // No device - flat line
    }

    // Get Lead II (ECG) at index 1 or F3 (EEG) at index 14
    // ECG uses indices 0-11, EEG uses indices 12-20
    const leadIndex = isECGMode ? 1 : 14;
    const data = dataBufferRef.current[leadIndex];

    if (!data || data.length === 0) {
      return "M 0 30 L 250 30"; // No data yet - flat line
    }

    // Use last 125 samples for 250px width (500Hz × 0.25s = 125 samples)
    const samples = data.slice(-125);

    // MEDICAL-GRADE RENDERING: Fixed 10mm/mV for ECG, 50μV/mm for EEG
    // NO auto-scaling - preserves clinical amplitude information
    const path = renderWaveform(
      samples,
      250,  // viewport width
      60,   // viewport height
      isECGMode,
      true  // useFixedScale = true (medical-grade)
    );

    return path;
  };

  // Call the function to generate path data
  // This runs on every render (which happens every 1 second when vitals update)
  const pathData = generatePathData();

  return (
    <WaveformErrorBoundary waveformType={isECGMode ? 'ECG' : 'EEG'}>
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
              {isECGMode ? 'ECG' : 'EEG'} {isECGMode ? (patient.vitals?.ecgReading ?? '--') : (patient.vitals?.eegReading ?? '--')}{isECGMode ? 'mV' : 'μV'}
            </span>
            <span className="text-green-300 text-[10px]">25mm/s</span>
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
    </WaveformErrorBoundary>
  );
});

PatientCardWaveform.displayName = 'PatientCardWaveform';