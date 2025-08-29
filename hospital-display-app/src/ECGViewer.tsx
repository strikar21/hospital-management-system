// ECGViewer.tsx - Continuous Real-time ECG/EEG Display (Uses API for waveform data)

import React, { useState, useEffect, useRef } from 'react';
import { X, Activity, Zap } from 'lucide-react';
import { Patient } from './types';
// ECG data generation removed - now uses backend API

interface ECGViewerProps {
  patient: Patient;
  onClose: () => void;
}

export const ECGViewer: React.FC<ECGViewerProps> = ({ patient, onClose }) => {
  const [isECGMode, setIsECGMode] = useState(true); // true = ECG, false = EEG
  const [speed, setSpeed] = useState(25); // mm/s
  const [gain, setGain] = useState(10); // mm/mV for ECG, μV/mm for EEG
  const [isPaused, setIsPaused] = useState(false);
  const [selectedLead, setSelectedLead] = useState<string>('II'); // Default to Lead II for ECG
  const [layout, setLayout] = useState(1); // 1, 4, or 9 views
  const canvasRefs = useRef<(HTMLCanvasElement | null)[]>([]);
  const animationRef = useRef<number | null>(null);
  const dataBufferRef = useRef<number[][]>([]);
  const calibrationPulseRef = useRef<boolean[]>([]); // Track calibration pulse per lead

  // Define leads for ECG and EEG
  const ecgLeads = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6'];
  const eegLeads = ['F3-C3', 'F4-C4', 'C3-P3', 'C4-P4', 'P3-O1', 'P4-O2', 'F7-T3', 'F8-T4', 'T5-O1'];
  const leads = isECGMode ? ecgLeads : eegLeads;

  // Update selected lead and reset data buffers when switching modes
  useEffect(() => {
    const newSelectedLead = isECGMode ? 'II' : 'F3-C3';
    setSelectedLead(newSelectedLead);
    dataBufferRef.current = Array(leads.length).fill(null).map(() => []);
    calibrationPulseRef.current = Array(leads.length).fill(true); // Show calibration pulse on mode switch
  }, [isECGMode, leads.length]);

  // Handle layout changes: adjust canvas refs
  useEffect(() => {
    canvasRefs.current = Array(layout).fill(null);
  }, [layout]);

  // Generate continuous real-time data for all leads using patient vital data
  useEffect(() => {
    const generateRealTimeData = () => {
      if (isPaused) return;

      const sampleRate = 250; // 250 Hz
      const samplesPerFrame = Math.round(sampleRate / 60); // ~60 FPS

      for (let i = 0; i < samplesPerFrame; i++) {
        const timeIndex = (Date.now() / 1000) * sampleRate + i;

        for (let leadIdx = 0; leadIdx < leads.length; leadIdx++) {
          let value = 0;

          if (calibrationPulseRef.current[leadIdx]) {
            if (isECGMode) {
              // ECG calibration pulse: 1 mV for 0.2 s (50 samples at 250 Hz)
              if (timeIndex < 50) {
                value = timeIndex < 10 ? (timeIndex / 10) * 1.0 : timeIndex < 40 ? 1.0 : (50 - timeIndex) / 10;
              } else {
                calibrationPulseRef.current[leadIdx] = false;
              }
            } else {
              // EEG calibration pulse: 50 μV for 1 s (250 samples at 250 Hz)
              if (timeIndex < 250) {
                value = timeIndex < 50 ? (timeIndex / 50) * 50 : timeIndex < 200 ? 50 : (250 - timeIndex) / 50 * 50;
              } else {
                calibrationPulseRef.current[leadIdx] = false;
              }
            }
          } else {
            // TODO: Replace with backend API call for real ECG/EEG waveform data
            // Placeholder: use flat line until backend provides real waveform data
            if (isECGMode) {
              value = 0; // Flat line placeholder for ECG - awaiting backend waveform data
            } else {
              value = 0; // Flat line placeholder for EEG - awaiting backend waveform data
            }
          }

          dataBufferRef.current[leadIdx].push(value);

          const maxBufferSize = sampleRate * 10;
          if (dataBufferRef.current[leadIdx].length > maxBufferSize) {
            dataBufferRef.current[leadIdx].shift();
          }
        }
      }

      drawAllWaveforms();
      animationRef.current = requestAnimationFrame(generateRealTimeData);
    };

    generateRealTimeData();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [patient.vitals.heartRate, patient.vitals.ecg, patient.vitals.eeg, isPaused, isECGMode, speed, gain]);

  const drawAllWaveforms = () => {
    if (layout === 1) {
      const leadIdx = leads.findIndex((l) => l === selectedLead);
      if (leadIdx >= 0) {
        drawWaveform(leadIdx, 0);
      }
    } else {
      const visibleLeads = Array.from({ length: Math.min(layout, leads.length) }, (_, i) => i);
      visibleLeads.forEach((leadIdx, viewIdx) => {
        if (leadIdx >= 0 && leadIdx < leads.length) {
          drawWaveform(leadIdx, viewIdx);
        }
      });
    }
  };

  const drawWaveform = (leadIdx: number, viewIdx: number) => {
    const canvas = canvasRefs.current[viewIdx];
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.scale(dpr, dpr);
    }

    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, width, height);

    drawGrid(ctx, width, height);

    // Draw baseline (0 mV or 0 μV)
    ctx.strokeStyle = '#333333';
    ctx.lineWidth = 0.5;
    ctx.beginPath();
    ctx.moveTo(0, height / 2);
    ctx.lineTo(width, height / 2);
    ctx.stroke();

    const data = dataBufferRef.current[leadIdx];
    if (data.length < 2) return;

    // AUTO-SCALING: Calculate data range and scale to fit canvas
    const visibleSamples = Math.min(data.length, Math.floor(width * 2)); // Show ~width*2 samples
    const recentData = data.slice(-visibleSamples);
    
    if (recentData.length === 0) return;
    
    const dataMin = Math.min(...recentData);
    const dataMax = Math.max(...recentData);
    const dataRange = dataMax - dataMin;
    
    // If no variation, use default scaling
    if (dataRange === 0) return;
    
    // Use 80% of canvas height for the waveform (10% margin top/bottom)
    const margin = height * 0.1;
    const usableHeight = height - (2 * margin);
    
    // EEG colors cycle through yellow, cyan, pink
    const eegColors = ['#FFD700', '#00FFFF', '#FF69B4'];
    ctx.strokeStyle = isECGMode ? '#00FF00' : eegColors[leadIdx % eegColors.length];
    ctx.lineWidth = isECGMode ? 2 : 1.5;
    ctx.beginPath();

    const pixelsPerSecond = speed * 3.78; // 96 DPI: 25 mm/s = ~94.5 pixels/s
    const sampleRate = 250;
    const samplesPerPixel = sampleRate / pixelsPerSecond;

    const totalSamples = data.length;
    const visibleSamplesForDisplay = Math.min(width * samplesPerPixel, totalSamples);
    const startSample = Math.max(0, totalSamples - visibleSamplesForDisplay);

    let isFirst = true;
    for (let x = 0; x < width; x++) {
      const sampleIndex = Math.floor(startSample + x * samplesPerPixel);
      if (sampleIndex < data.length) {
        const value = data[sampleIndex];
        
        // AUTO-SCALE: Map data value to canvas coordinates
        let y;
        if (dataRange > 0) {
          // Scale value to fit in usable height
          const normalizedValue = (value - dataMin) / dataRange; // 0 to 1
          y = margin + usableHeight - (normalizedValue * usableHeight); // Flip Y axis
        } else {
          y = height / 2; // Center line if no range
        }
        
        // Clamp to canvas bounds
        y = Math.max(margin, Math.min(height - margin, y));

        if (isFirst) {
          ctx.moveTo(x, y);
          isFirst = false;
        } else {
          ctx.lineTo(x, y);
        }
      }
    }

    ctx.stroke();

    // Draw sweep line
    if (!isPaused) {
      const sweepX = width - 50;
      ctx.strokeStyle = '#FF0000';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(sweepX, 0);
      ctx.lineTo(sweepX, height);
      ctx.stroke();
    }

    // Draw amplitude scale indicators
    ctx.fillStyle = isECGMode ? '#00FF00' : eegColors[leadIdx % eegColors.length];
    ctx.font = '10px monospace';
    
    // Show min/max values for reference
    if (dataRange > 0) {
      ctx.fillText(`${dataMax.toFixed(1)} ${isECGMode ? 'mV' : 'μV'}`, 5, margin + 12);
      ctx.fillText(`${dataMin.toFixed(1)} ${isECGMode ? 'mV' : 'μV'}`, 5, height - margin - 2);
      ctx.fillText(`0`, 5, height / 2 + 5);
    }
  };

  const drawGrid = (ctx: CanvasRenderingContext2D, width: number, height: number) => {
    const smallGridColor = isECGMode ? '#FF6666' : '#444444'; // ECG: light red, EEG: gray
    const largeGridColor = isECGMode ? '#CC3333' : '#666666'; // ECG: darker red, EEG: lighter gray
    ctx.strokeStyle = smallGridColor;
    ctx.lineWidth = 0.5;

    for (let x = 0; x < width; x += 3.78) { // 1 mm = ~3.78 pixels at 96 DPI
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }

    for (let y = 0; y < height; y += 3.78) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    ctx.strokeStyle = largeGridColor;
    ctx.lineWidth = 1;

    for (let x = 0; x < width; x += 18.9) { // 5 mm = ~18.9 pixels
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }

    for (let y = 0; y < height; y += 18.9) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
  };

  // Get the latest value for the displayed lead(s)
  const getLatestValue = () => {
    let leadIdx = 0;
    if (layout === 1) {
      leadIdx = leads.findIndex((l) => l === selectedLead);
      if (leadIdx === -1) leadIdx = 0; // Fallback to first lead
    }
    
    const data = dataBufferRef.current[leadIdx];
    const lead = leads[leadIdx] || 'N/A';
    if (!data || data.length === 0) return `${lead}: N/A`;
    const latestValue = data[data.length - 1];
    const timestamp = new Date().toLocaleTimeString();
    return `${lead}: ${latestValue.toFixed(2)} ${isECGMode ? 'mV' : 'μV'} (${timestamp})`;
  };

  return (
    <div className="fixed inset-0 bg-black z-50 overflow-hidden">
      <div className="h-full w-full bg-black text-white flex flex-col">
        {/* Header */}
        <div className="p-4 bg-gray-900 border-b border-gray-700 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
            <div>
              <h2 className="text-xl font-bold text-white">
                Continuous {isECGMode ? 'ECG' : 'EEG'} - Bed {patient.bedNumber}
              </h2>
              <p className="text-sm text-gray-400">
                Room {patient.room} • {patient.ward} Ward • Auto-scaled to fit window
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-4 flex-wrap">
            {/* ECG/EEG Mode Toggle */}
            <div className="flex items-center space-x-2 bg-gray-800 rounded-lg p-2">
              <button
                onClick={() => setIsECGMode(true)}
                className={`flex items-center space-x-2 px-3 py-1 rounded transition-colors ${
                  isECGMode ? 'bg-green-600 text-white' : 'text-gray-400 hover:text-white'
                }`}
              >
                <Activity className="w-4 h-4" />
                <span>ECG</span>
              </button>
              <button
                onClick={() => setIsECGMode(false)}
                className={`flex items-center space-x-2 px-3 py-1 rounded transition-colors ${
                  !isECGMode ? 'bg-yellow-600 text-white' : 'text-gray-400 hover:text-white'
                }`}
              >
                <Zap className="w-4 h-4" />
                <span>EEG</span>
              </button>
            </div>

            {/* Layout Selector */}
            <div className="flex items-center space-x-2 bg-gray-800 rounded-lg p-2">
              <span className="text-sm text-gray-400">Layout:</span>
              <select
                value={layout}
                onChange={(e) => setLayout(Number(e.target.value))}
                className="bg-gray-700 text-white rounded px-2 py-1 text-sm"
              >
                <option value={1}>1 View</option>
                <option value={4}>2x2 (4 Views)</option>
                <option value={9}>3x3 (9 Views)</option>
              </select>
            </div>

            {/* Single Lead Selector (only visible in 1-view mode) */}
            {layout === 1 && (
              <div className="flex items-center space-x-2 bg-gray-800 rounded-lg p-2">
                <span className="text-sm text-gray-400">Lead:</span>
                <select
                  value={selectedLead}
                  onChange={(e) => setSelectedLead(e.target.value)}
                  className="bg-gray-700 text-white rounded px-2 py-1 text-sm"
                >
                  {leads.map((lead) => (
                    <option key={lead} value={lead}>
                      {lead}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Controls */}
            <div className="flex items-center space-x-2 bg-gray-800 rounded-lg p-2">
              <span className="text-sm text-gray-400">Speed:</span>
              <select
                value={speed}
                onChange={(e) => setSpeed(Number(e.target.value))}
                className="bg-gray-700 text-white rounded px-2 py-1 text-sm"
              >
                <option value={15}>15mm/s</option>
                <option value={25}>25mm/s</option>
                <option value={30}>30mm/s</option>
                <option value={50}>50mm/s</option>
              </select>

              <span className="text-sm text-gray-400 ml-3">Gain:</span>
              <select
                value={gain}
                onChange={(e) => setGain(Number(e.target.value))}
                className="bg-gray-700 text-white rounded px-2 py-1 text-sm"
              >
                {isECGMode ? (
                  <>
                    <option value={5}>5mm/mV</option>
                    <option value={10}>10mm/mV</option>
                    <option value={20}>20mm/mV</option>
                  </>
                ) : (
                  <>
                    <option value={5}>5μV/mm</option>
                    <option value={7}>7μV/mm</option>
                    <option value={10}>10μV/mm</option>
                  </>
                )}
              </select>

              <button
                onClick={() => setIsPaused(!isPaused)}
                className={`ml-3 px-3 py-1 rounded text-sm ${
                  isPaused ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                {isPaused ? 'Resume' : 'Pause'}
              </button>
            </div>

            {/* Current Values (Header) */}
            <div className="text-right text-sm">
              <div className="font-medium">
                {isECGMode ? `HR: ${patient.vitals.heartRate} BPM` : 'EEG Activity'}
              </div>
              <div className="text-gray-400">
                {isECGMode ? `${patient.vitals.ecg} mV` : `${patient.vitals.eeg || 45} μV • Auto-scaled`}
              </div>
            </div>
          </div>
        </div>

        {/* Display Area */}
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
                return (
                  <div
                    key={viewIdx}
                    className="relative border-2 border-gray-600 rounded overflow-hidden flex flex-col w-full h-full"
                  >
                    <canvas
                      ref={(el) => {
                        canvasRefs.current[viewIdx] = el;
                        return undefined; // Explicitly return void
                      }}
                      className="w-full h-full"
                    />
                    <div className="absolute top-2 left-2 bg-gray-800 bg-opacity-75 rounded px-2 py-1 text-xs">
                      <div
                        className={`w-2 h-2 rounded-full inline-block mr-2 ${
                          isPaused ? 'bg-red-500' : isECGMode ? 'bg-green-500 animate-pulse' : 'bg-yellow-500 animate-pulse'
                        }`}
                      ></div>
                      Lead: {lead} • {isPaused ? 'PAUSED' : 'AUTO-SCALED'}
                    </div>
                  </div>
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
      </div>
    </div>
  );
};