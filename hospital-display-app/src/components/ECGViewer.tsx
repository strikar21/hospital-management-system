import React from 'react';
import { Heart, Zap } from 'lucide-react';
import { patient } from '../types';
import { useECGViewer } from '../hooks/useECGViewer';
import { renderWaveform } from '../utils/medicalWaveformUtils';

interface ECGViewerProps {
  patient: patient;
  onECGView?: (patient: patient) => void;
  onVitalClick: (patient: patient, vital: string) => void;
  onToggleECGMode?: (patient: patient) => void;
}

const ECGViewer: React.FC<ECGViewerProps> = ({
  patient,
  onECGView,
  onVitalClick,
  onToggleECGMode
}) => {
  // Subscribe to real-time waveform data using WebSocket
  // Extract isECGMode from hook to use hook's internal state (single source of truth)
  const { dataBufferRef, isECGMode, setIsECGMode } = useECGViewer({ patient });

  // Handle ECG/EEG toggle - updates hook's internal state
  const handleToggleECGMode = (newMode: boolean) => {
    setIsECGMode(newMode); // Update hook's state
    if (onToggleECGMode) {
      const updatedPatient = {
        ...patient,
        vitals: {
          ...patient.vitals,
          isEcgMode: newMode
        }
      };
      onToggleECGMode(updatedPatient); // Notify parent
    }
  };

  // Generate SVG path from real waveform data (Lead II for ECG, F3 for EEG)
  // Uses MEDICAL-GRADE FIXED SCALE rendering (NOT auto-scaling)
  const generatePathData = () => {
    if (!patient.assignedDeviceId) {
      return "M 0 60 L 400 60"; // No device - flat line centered
    }

    // Get Lead II (ECG) at index 1 or F3 (EEG) at index 14
    // ECG uses indices 0-11, EEG uses indices 12-20
    const leadIndex = isECGMode ? 1 : 14;
    const data = dataBufferRef.current[leadIndex];

    if (!data || data.length === 0) {
      return "M 0 60 L 400 60"; // No data yet - flat line
    }

    // Use last 200 samples for 400px width (500Hz × 0.4s = 200 samples)
    const samples = data.slice(-200);

    // MEDICAL-GRADE RENDERING: Fixed 10mm/mV for ECG, 50μV/mm for EEG
    // NO auto-scaling - preserves clinical amplitude information
    const path = renderWaveform(
      samples,
      400,  // viewport width
      120,  // viewport height
      isECGMode,
      true  // useFixedScale = true (medical-grade)
    );

    return path;
  };

  // Call on every render (vitals update triggers re-render every 1 second)
  const pathData = generatePathData();

  return (
    <div className="flex-1 bg-gray-50 rounded-lg p-2 min-h-0">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-base font-semibold flex items-center space-x-2">
          <Zap className="w-4 h-4 text-green-600" />
          <span>{isECGMode ? 'ECG' : 'EEG'} Monitor</span>
        </h3>
        <div className="flex items-center space-x-3">
          <div className="text-right">
            <p className="text-sm font-medium text-gray-700">
              {isECGMode ? 'Cardiac Rhythm' : 'Brain Activity'}
            </p>
            <p className="text-lg font-bold text-green-600">
              {isECGMode ? (patient.vitals?.ecgReading ?? '--') : (patient.vitals?.eegReading ?? '--')}
              {isECGMode ? ' mV' : ' μV'}
            </p>
          </div>

          {/* ECG/EEG Mode Toggle */}
          <div className="flex items-center space-x-1 bg-gray-800 rounded-lg p-1">
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleToggleECGMode(true);
              }}
              className={`flex items-center space-x-1 px-2 py-1 rounded text-xs transition-colors ${
                isECGMode ? 'bg-green-600 text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              <Heart className="w-3 h-3" />
              <span>ECG</span>
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleToggleECGMode(false);
              }}
              className={`flex items-center space-x-1 px-2 py-1 rounded text-xs transition-colors ${
                !isECGMode ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              <Zap className="w-3 h-3" />
              <span>EEG</span>
            </button>
          </div>

{/* Standard lead label - embedded viewer shows Lead II (ECG) or F3 (EEG) */}
          <span className="text-xs text-gray-600 bg-gray-100 px-2 py-1 rounded border">
            {isECGMode ? 'Lead II' : 'F3'} <span className="text-gray-400">(Standard)</span>
          </span>
          <button
            onClick={() => onECGView ? onECGView(patient) : onVitalClick(patient, isECGMode ? 'ecgReading' : 'eegReading')}
            className="text-sm bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700 transition-colors"
          >
            Full View
          </button>
        </div>
      </div>

      {/* ECG/EEG Waveform - Takes Remaining Space */}
      <div
        className="bg-gray-900 rounded-lg cursor-pointer flex flex-col hover:bg-gray-800 transition-colors p-2"
        style={{ height: 'calc(100% - 60px)' }}
        onClick={() => onECGView ? onECGView(patient) : onVitalClick(patient, isECGMode ? 'ecgReading' : 'eegReading')}
      >
        <div className="flex items-center justify-between mb-2 flex-shrink-0">
          <div className="flex items-center space-x-3">
            <div className={`w-2 h-2 rounded-full animate-pulse ${
              isECGMode ? 'bg-green-400' : 'bg-blue-400'
            }`}></div>
            <span className={`text-sm font-medium ${
              isECGMode ? 'text-green-400' : 'text-blue-400'
            }`}>
              {isECGMode ? 'Cardiac Signal' : 'Brain Signal'} •
              {isECGMode ? (patient.vitals?.ecgReading ?? '--') : (patient.vitals?.eegReading ?? '--')}
              {isECGMode ? 'mV' : 'μV'}
            </span>
            <span className="text-green-300 text-sm">25mm/s • 10mm/mV</span>
          </div>
          <span className="text-gray-400 text-sm">Click for full view</span>
        </div>

        <div className="flex-1 min-h-0 relative">
          <svg
            width="100%"
            height="100%"
            viewBox="0 0 400 120"
            className="bg-gray-900 w-full h-full"
            preserveAspectRatio="none"
          >
            <defs>
              <pattern id={`grid-${patient.id}-detail`} width="10" height="10" patternUnits="userSpaceOnUse">
                <path d="M 10 0 L 0 0 0 10" fill="none" stroke="#374151" strokeWidth="0.5" opacity="0.4"/>
              </pattern>
              <pattern id={`grid-major-${patient.id}-detail`} width="50" height="50" patternUnits="userSpaceOnUse">
                <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#4B5563" strokeWidth="1" opacity="0.6"/>
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill={`url(#grid-${patient.id}-detail)`} />
            <rect width="100%" height="100%" fill={`url(#grid-major-${patient.id}-detail)`} />

            <path
              d={pathData}
              fill="none"
              stroke={isECGMode ? "#10B981" : "#3B82F6"}
              strokeWidth="2"
              className="drop-shadow-lg"
            />

            {/* Sweep line */}
            <line
              x1="380"
              y1="0"
              x2="380"
              y2="120"
              stroke="#EF4444"
              strokeWidth="1"
              opacity="0.7"
            />
          </svg>
        </div>
      </div>
    </div>
  );
};

export default ECGViewer;