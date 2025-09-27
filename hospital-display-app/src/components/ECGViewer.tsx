import React, { useState, useEffect } from 'react';
import { Heart, Zap } from 'lucide-react';
import { patient } from '../types';

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
  const [isEcgMode, setIsECGMode] = useState<boolean>(patient.vitals?.isEcgMode ?? true);

  // Sync with patient vitals when they change
  useEffect(() => {
    setIsECGMode(patient.vitals?.isEcgMode || false);
  }, [patient.vitals?.isEcgMode]);

  // Handle ECG/EEG toggle
  const handleToggleECGMode = (newMode: boolean) => {
    setIsECGMode(newMode); // Update local state for simulation
    if (onToggleECGMode) {
      const updatedPatient = {
        ...patient,
        vitals: {
          ...patient.vitals,
          isEcgMode: newMode
        }
      };
      onToggleECGMode(updatedPatient); // Call parent callback if provided
    }
  };

  return (
    <div className="flex-1 bg-gray-50 rounded-lg p-2 min-h-0">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-base font-semibold flex items-center space-x-2">
          <Zap className="w-4 h-4 text-green-600" />
          <span>{isEcgMode ? 'ECG' : 'EEG'} Monitor</span>
        </h3>
        <div className="flex items-center space-x-3">
          <div className="text-right">
            <p className="text-sm font-medium text-gray-700">
              {isEcgMode ? 'Cardiac Rhythm' : 'Brain Activity'}
            </p>
            <p className="text-lg font-bold text-green-600">
              {isEcgMode ? (patient.vitals?.ecgReading || '--') : (patient.vitals?.eegReading || '--')}
              {isEcgMode ? ' mV' : ' μV'}
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
                isEcgMode ? 'bg-green-600 text-white' : 'text-gray-400 hover:text-white'
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
                !isEcgMode ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              <Zap className="w-3 h-3" />
              <span>EEG</span>
            </button>
          </div>

          <select
            className="text-sm border rounded px-2 py-1"
            defaultValue={isEcgMode ? 'II' : 'C3-C4'}
          >
            {isEcgMode ? (
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
              </>
            )}
          </select>
          <button
            onClick={() => onECGView ? onECGView(patient) : onVitalClick(patient, isEcgMode ? 'ecgReading' : 'eegReading')}
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
        onClick={() => onECGView ? onECGView(patient) : onVitalClick(patient, isEcgMode ? 'ecgReading' : 'eegReading')}
      >
        <div className="flex items-center justify-between mb-2 flex-shrink-0">
          <div className="flex items-center space-x-3">
            <div className={`w-2 h-2 rounded-full animate-pulse ${
              isEcgMode ? 'bg-green-400' : 'bg-blue-400'
            }`}></div>
            <span className={`text-sm font-medium ${
              isEcgMode ? 'text-green-400' : 'text-blue-400'
            }`}>
              {isEcgMode ? 'Cardiac Signal' : 'Brain Signal'} •
              {isEcgMode ? (patient.vitals?.ecgReading || '--') : (patient.vitals?.eegReading || '--')}
              {isEcgMode ? 'mV' : 'μV'}
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
              d="M 0 50 L 400 50"
              fill="none"
              stroke={isEcgMode ? "#10B981" : "#3B82F6"}
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