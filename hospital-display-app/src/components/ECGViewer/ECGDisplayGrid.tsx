import React, { useState, useEffect } from 'react';
import { patient } from '../../types';
import { ECGWaveformCanvas } from './ECGWaveformCanvas';

// Props for the grid of waveform canvases
interface ECGDisplayGridProps {
  patient: patient;
  layout: number;
  selectedLead: string;
  leads: string[];
  isECGMode: boolean;
  isPaused: boolean;
  speed: number;
  gain: number; // mm/mV for ECG, μV/mm for EEG
  dataBufferRef: React.MutableRefObject<number[][]>;
  canvasRefs: React.MutableRefObject<(HTMLCanvasElement | null)[]>;
  getLatestValue: () => string;
}

// Calculate dynamic row height based on viewport and layout
const calculateRowHeight = (layout: number, viewportHeight: number): string => {
  if (layout === 1) return '1fr'; // Single lead uses full available space

  // Calculate number of rows based on layout
  const rows = layout === 12 ? 3 : layout === 9 ? 3 : layout === 4 ? 2 : 1;

  // Reserve space for fixed UI elements
  const headerHeight = 93;      // ECGViewerHeader
  const infoBarHeight = 40;     // Mode/Speed/Scaling info bar
  const paddingAndBorders = 68; // All padding + borders
  const overhead = headerHeight + infoBarHeight + paddingAndBorders;

  // Calculate available space for grid
  const availableHeight = viewportHeight - overhead;

  // Account for gaps between rows (16px Tailwind gap-4)
  const gapSize = 16;
  const totalGaps = (rows - 1) * gapSize;

  // Calculate height per row
  const usableHeight = availableHeight - totalGaps;
  const heightPerRow = Math.floor(usableHeight / rows);

  // Apply minimum height for clinical readability (120px absolute minimum)
  const minHeight = 120;
  const finalHeight = Math.max(minHeight, heightPerRow);

  return `${finalHeight}px`;
};

// Component to display multiple waveform canvases
export const ECGDisplayGrid: React.FC<ECGDisplayGridProps> = ({
  patient,
  layout,
  selectedLead,
  leads,
  isECGMode,
  isPaused,
  speed,
  gain,
  dataBufferRef,
  canvasRefs,
  getLatestValue
}) => {
  // ✅ REMOVED: Duplicate animation loops (was causing 360-840 render calls/second)
  // Canvas components handle their own rendering via requestAnimationFrame in ECGWaveformCanvas.tsx

  // Track viewport height for auto-sizing
  const [viewportHeight, setViewportHeight] = useState(window.innerHeight);

  useEffect(() => {
    const handleResize = () => setViewportHeight(window.innerHeight);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Map leads for display
  const visibleLeads = layout === 1
    ? [leads.findIndex((l) => l === selectedLead)]
    : Array.from({ length: Math.min(layout, leads.length) }, (_, i) => i);

  // ✅ FIX: Map display index to actual buffer index with T3/T4 gap handling
  // ECG data is stored in buffer indices 0-11 (12 leads)
  // EEG data is stored in buffer indices 12-21 (10 channels with T3/T4 reserved but unused)
  //   Fp1=12, Fp2=13, F3=14, F4=15, C3=16, C4=17, [T3=18, T4=19 empty], O1=20, O2=21
  const getBufferIndex = (displayIndex: number): number => {
    if (isECGMode) {
      return displayIndex;  // ECG: direct 1:1 mapping (0-11)
    }
    // EEG: Skip T3/T4 buffer slots (18-19) when mapping O1/O2
    if (displayIndex < 6) {
      // Fp1, Fp2, F3, F4, C3, C4 → buffers 12-17
      return displayIndex + 12;
    } else {
      // O1, O2 → buffers 20-21 (skip T3/T4 at 18-19 by adding +14 instead of +12)
      return displayIndex + 14;
    }
  };

  return (
    <div className="flex-1 p-4 overflow-y-auto relative" style={{ minHeight: '400px' }}>
      <div className="bg-black rounded-lg border-2 border-gray-700 p-4 h-full flex flex-col" style={{ height: '100%' }}>
        <div className="flex justify-between items-center mb-4 pb-2 border-b border-gray-800 flex-wrap">
          <div className="flex items-center space-x-4 text-sm">
            <span className={isECGMode ? 'text-green-400' : 'text-yellow-400'}>
              <strong>Mode:</strong> {isECGMode ? 'ECG' : 'EEG'}
            </span>
            <span className="text-blue-400">
              <strong>Speed:</strong> {speed}mm/s
            </span>
            <span className="text-yellow-400">
              <strong>Scaling:</strong> {isECGMode ? `${gain}mm/mV` : `${gain}μV/mm`}
            </span>
            <span className="text-purple-400">
              <strong>Filter:</strong> {isECGMode ? '0.5–40Hz' : '0.5–70Hz'}
            </span>
            {isPaused && <span className="text-red-400 font-bold">PAUSED</span>}
          </div>
          <div className="text-gray-400 text-sm" aria-live="polite">
            Live: {new Date().toLocaleTimeString()}
          </div>
        </div>
        <div className="absolute top-2 right-2 bg-gray-800 bg-opacity-75 rounded px-2 py-1 text-sm z-10">
          <div className="font-medium">{getLatestValue()}</div>
        </div>
        <div className={`grid ${
          layout === 12 ? 'grid-cols-4' :
          layout === 9 ? 'grid-cols-3' :
          layout === 4 ? 'grid-cols-2' :
          'grid-cols-1'
        } gap-4 flex-1 max-w-full max-h-full`}
          style={{
            gridAutoRows: calculateRowHeight(layout, viewportHeight)
          }}>
          {visibleLeads.map((leadIdx, viewIdx) => {
            const lead = leads[leadIdx] || 'N/A';
            const bufferIdx = getBufferIndex(leadIdx); // ✅ FIX: Use correct buffer index for EEG mode

            return (
              <ECGWaveformCanvas
                key={`${patient.id}-${leadIdx}-${viewIdx}`}
                ref={(el) => {
                  canvasRefs.current[viewIdx] = el;
                  return undefined;
                }}
                leadIdx={bufferIdx} // ✅ FIX: Pass buffer index, not display index
                leadName={lead}
                dataBufferRef={dataBufferRef}
                isECGMode={isECGMode}
                isPaused={isPaused}
                speed={speed}
                gain={gain}
                patientId={patient.id}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
};