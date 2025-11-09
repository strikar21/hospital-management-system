/**
 * PatientCardWaveform - ECG/EEG waveform display component
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade waveform visualization with lead selection
 */

import React, { useRef, useMemo } from 'react';
import { patient, user } from '../../types';
import { useECGViewer } from '../../hooks/useECGViewer';
import { ECGWaveformCanvas } from '../ECGViewer/ECGWaveformCanvas';
import { WaveformErrorBoundary } from '../ErrorBoundary';
import { mmToPixels } from '../../utils/medicalWaveformUtils';

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
  const { dataBufferRef, speed, gain } = useECGViewer({ patient });
  const canvasRef = useRef<HTMLCanvasElement | null>(null);


  // Get buffer index: Lead II (index 1) for ECG, F3 (index 14) for EEG
  const leadIndex = isECGMode ? 1 : 14;
  const leadName = isECGMode ? 'Lead II' : 'F3';

  // ✅ Calculate exact container height for 30mm medical-grade display
  // Extended ECG strip height: 30mm (better visibility for patient cards)
  const containerHeightPx = useMemo(() => {
    const waveformHeight = Math.round(mmToPixels(30)); // 30mm at detected DPI
    const headerHeight = 10; // Fixed header with ECG/EEG label
    const paddingBottom = 8; // pb-2 = 0.5rem = 8px (only bottom padding, no top)
    return waveformHeight + headerHeight + paddingBottom;
  }, []);

  return (
    <WaveformErrorBoundary waveformType={isECGMode ? 'ECG' : 'EEG'}>
      <div className="flex-shrink-0">
        <div
          style={{ height: `${containerHeightPx}px` }}
          className="px-2 pb-2 bg-gray-900 rounded-lg hover:bg-gray-800 transition-colors cursor-pointer flex flex-col"
          onClick={(e) => {
            e.stopPropagation();
            onVitalClick(patient, isECGMode ? 'ecgReading' : 'eegReading');
          }}
        >
        {/* All ECG/EEG text consolidated at top with smaller font - Hover for advanced metrics */}
        <div className="flex items-center justify-between mb-0.5 flex-shrink-0 relative group h-[10px]">
          <div className="flex items-center space-x-1.5">
            <div className={`w-1 h-1 rounded-full animate-pulse ${
              isECGMode
                ? (arrhythmiaDetected ? 'bg-yellow-400' : 'bg-green-400')
                : (seizureActivity ? 'bg-red-400' : 'bg-blue-400')
            }`}></div>
            <span className={`text-[10px] ${
              isECGMode ? 'text-green-400' : 'text-blue-400'
            }`}>
              {isECGMode ? 'ECG' : 'EEG'}
            </span>
            {isECGMode && arrhythmiaDetected && (
              <span className="text-yellow-400 text-[10px]">⚠️</span>
            )}
            {!isECGMode && seizureActivity && (
              <span className="text-red-400 text-[10px]">🚨</span>
            )}
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="text-[10px] text-gray-400">{patient.vitals?.heartRate || 0} BPM</span>
          </div>

          {/* Advanced Metrics Tooltip - Shows on hover */}
          <div className="absolute top-full left-0 right-0 mt-1 opacity-0 group-hover:opacity-100 transition-opacity bg-black bg-opacity-90 rounded p-2 z-10 pointer-events-none">
            <div className="text-white text-[10px] leading-tight">
              {isECGMode ? (
                // ECG Advanced Metrics
                patient.vitals?.ecg ? (
                  <div className="space-y-0.5">
                    <div className="font-bold text-green-400 mb-1">ECG Metrics:</div>
                    <div>RR: {patient.vitals.ecg.rrInterval ? `${patient.vitals.ecg.rrInterval}ms` : '--'} | QRS: {patient.vitals.ecg.qrsDuration ? `${patient.vitals.ecg.qrsDuration}ms` : '--'} | QT: {patient.vitals.ecg.qtInterval ? `${patient.vitals.ecg.qtInterval}ms` : '--'}</div>
                    <div>Rhythm: {patient.vitals.ecg.rhythm || '--'} | Axis: {patient.vitals.ecg.axis ? `${patient.vitals.ecg.axis}°` : '--'}</div>
                    <div>ST: {patient.vitals.ecg.stSegment || '--'}</div>
                  </div>
                ) : (
                  <div>No ECG metrics available</div>
                )
              ) : (
                // EEG Advanced Metrics
                patient.vitals?.eeg ? (
                  <div className="space-y-0.5">
                    <div className="font-bold text-blue-400 mb-1">EEG Bands:</div>
                    <div>
                      α: {patient.vitals.eeg.alphaPower ? `${patient.vitals.eeg.alphaPower.toFixed(0)}%` : '--'} |
                      β: {patient.vitals.eeg.betaPower ? `${patient.vitals.eeg.betaPower.toFixed(0)}%` : '--'} |
                      θ: {patient.vitals.eeg.thetaPower ? `${patient.vitals.eeg.thetaPower.toFixed(0)}%` : '--'}
                    </div>
                    <div>
                      δ: {patient.vitals.eeg.deltaPower ? `${patient.vitals.eeg.deltaPower.toFixed(0)}%` : '--'} |
                      γ: {patient.vitals.eeg.gammaPower ? `${patient.vitals.eeg.gammaPower.toFixed(0)}%` : '--'}
                    </div>
                    <div>Dominant: {patient.vitals.eeg.dominantFrequency ? `${patient.vitals.eeg.dominantFrequency.toFixed(1)} Hz` : '--'}</div>
                    {patient.vitals.eeg.seizureActivity && <div className="text-red-400 font-bold">⚠️ Seizure Activity</div>}
                  </div>
                ) : (
                  <div>No EEG metrics available</div>
                )
              )}
            </div>
          </div>
        </div>

        {/* Pure Waveform Area - Uses ECGWaveformCanvas (same as full ECG viewer) */}
        <div className="flex-1 min-h-0">
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
      </div>
    </WaveformErrorBoundary>
  );
});

PatientCardWaveform.displayName = 'PatientCardWaveform';