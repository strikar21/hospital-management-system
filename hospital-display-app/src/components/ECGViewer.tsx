import React, { useRef } from 'react';
import { Heart, Zap } from 'lucide-react';
import { patient } from '../types';
import { useECGViewer } from '../hooks/useECGViewer';
import { ECGWaveformCanvas } from './ECGViewer/ECGWaveformCanvas';

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
  const { dataBufferRef, isECGMode, setIsECGMode, speed, gain } = useECGViewer({ patient });
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

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

  // Get buffer index: Lead II (index 1) for ECG, F3 (index 14) for EEG
  const leadIndex = isECGMode ? 1 : 14;
  const leadName = isECGMode ? 'Lead II' : 'F3';

  return (
    <div className="flex-1 bg-gray-50 rounded-lg p-2 min-h-0">
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-sm font-semibold flex items-center space-x-1.5">
          <Zap className="w-3.5 h-3.5 text-green-600" />
          <span>{isECGMode ? 'ECG' : 'EEG'} Monitor</span>
        </h3>
        <div className="flex items-center space-x-3">
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
        className="cursor-pointer hover:opacity-90 transition-opacity"
        style={{ height: 'calc(100% - 60px)' }}
        onClick={() => onECGView ? onECGView(patient) : onVitalClick(patient, isECGMode ? 'ecgReading' : 'eegReading')}
      >
        <ECGWaveformCanvas
          ref={canvasRef}
          leadIdx={leadIndex}
          leadName={leadName}
          dataBufferRef={dataBufferRef}
          isECGMode={isECGMode}
          isPaused={false}
          speed={speed}
          gain={gain}
          patientId={patient.id}
          isPatientCard={true}
        />
      </div>
    </div>
  );
};

export default ECGViewer;