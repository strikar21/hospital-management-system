/**
 * ECGDisplayGrid - Grid layout component for multiple ECG/EEG canvas views
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade display grid with info bars and real-time monitoring
 */

import React, { useEffect } from 'react';
import { ECGWaveformCanvas } from './ECGWaveformCanvas';
import { patient } from '../../types';

interface ECGDisplayGridProps {
  patient: patient;
  layout: number;
  selectedLead: string;
  leads: string[];
  isECGMode: boolean;
  isPaused: boolean;
  speed: number;
  dataBufferRef: React.MutableRefObject<number[][]>;
  canvasRefs: React.MutableRefObject<(HTMLCanvasElement | null)[]>;
  getLatestValue: () => string;
  drawAllWaveforms: () => void;
}

export const ECGDisplayGrid: React.FC<ECGDisplayGridProps> = ({
  patient,
  layout,
  selectedLead,
  leads,
  isECGMode,
  isPaused,
  speed,
  dataBufferRef,
  canvasRefs,
  getLatestValue,
  drawAllWaveforms
}) => {

  useEffect(() => {
    const interval = setInterval(() => {
      if (!isPaused) {
        drawAllWaveforms();
      }
    }, 16); // ~60 FPS

    return () => clearInterval(interval);
  }, [isPaused, drawAllWaveforms]);

  return (
    <div className="flex-1 p-4 overflow-hidden relative">
      <div className="bg-black rounded-lg border-2 border-gray-700 p-4 h-full flex flex-col">
        {/* Info Bar */}
        <div className="flex justify-between items-center mb-4 pb-2 border-b border-gray-800 flex-wrap">
          <div className="flex items-center space-x-4 text-sm">
            <span className={isECGMode ? 'text-green-400' : 'text-yellow-400'}>
              <strong>Mode:</strong> {isECGMode ? 'ECG' : 'EEG'}
            </span>
            <span className="text-blue-400">
              <strong>Speed:</strong> {speed}mm/s
            </span>
            <span className="text-yellow-400">
              <strong>Scaling:</strong> Auto-fit to window
            </span>
            <span className="text-purple-400">
              <strong>Filter:</strong> {isECGMode ? '0.5–40Hz' : '0.5–70Hz'}
            </span>
            {isPaused && <span className="text-red-400 font-bold">PAUSED</span>}
          </div>
          <div className="text-gray-400 text-sm">
            Live: {new Date().toLocaleTimeString()}
          </div>
        </div>

        {/* Latest Value (Top-Right Corner of Display Area) */}
        <div className="absolute top-2 right-2 bg-gray-800 bg-opacity-75 rounded px-2 py-1 text-sm z-10">
          <div className="font-medium">{getLatestValue()}</div>
        </div>

        {/* Grid of Views */}
        <div className={`grid ${layout === 4 ? 'grid-cols-2' : layout === 9 ? 'grid-cols-3' : 'grid-cols-1'} gap-4 flex-1 max-w-full max-h-full overflow-hidden`}>
          {Array.from({ length: layout }).map((_, viewIdx) => {
            const leadIdx = layout === 1 ? leads.findIndex((l) => l === selectedLead) : viewIdx;
            const lead = leads[leadIdx] || 'N/A';
            const data = dataBufferRef.current[leadIdx] || [];

            return (
              <ECGWaveformCanvas
                key={viewIdx}
                ref={(el) => {
                  canvasRefs.current[viewIdx] = el;
                  return undefined;
                }}
                leadIdx={leadIdx}
                leadName={lead}
                data={data}
                isECGMode={isECGMode}
                isPaused={isPaused}
                speed={speed}
                patientId={patient.id}
              />
            );
          })}
        </div>

        {/* Instructions */}
        <div className="mt-4 pt-2 border-t border-gray-800 text-center text-sm text-gray-400">
          <p>
            {isECGMode
              ? 'Continuous ECG monitoring • Real-time cardiac rhythm analysis • Auto-scaled to fit window'
              : 'Continuous EEG monitoring • Real-time brain activity analysis • Auto-scaled amplitude'}
          </p>
        </div>
      </div>
    </div>
  );
};