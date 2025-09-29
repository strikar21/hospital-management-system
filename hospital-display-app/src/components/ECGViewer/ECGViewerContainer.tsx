/**
 * ECGViewerContainer - Main container component for ECG/EEG viewer
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade continuous real-time ECG/EEG display with auto-scaling
 */

import React, { useCallback } from 'react';
import { patient } from '../../types';
import { useECGViewer } from '../../hooks/useECGViewer';
import { ECGViewerHeader } from './ECGViewerHeader';
import { ECGDisplayGrid } from './ECGDisplayGrid';

interface ECGViewerContainerProps {
  patient: patient;
  onClose: () => void;
}

export const ECGViewerContainer: React.FC<ECGViewerContainerProps> = ({ patient, onClose }) => {
  const {
    isECGMode,
    speed,
    gain,
    isPaused,
    selectedLead,
    layout,
    leads,
    canvasRefs,
    dataBufferRef,
    setIsECGMode,
    setSpeed,
    setGain,
    setIsPaused,
    setSelectedLead,
    setLayout,
    getLatestValue
  } = useECGViewer({ patient });

  // Draw all waveforms based on current layout
  const drawAllWaveforms = useCallback(() => {
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
  }, [layout, leads, selectedLead]);

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

  return (
    <div className="fixed inset-0 bg-black z-50 overflow-hidden">
      <div className="h-full w-full bg-black text-white flex flex-col">
        <ECGViewerHeader
          patient={patient}
          isECGMode={isECGMode}
          layout={layout}
          selectedLead={selectedLead}
          leads={leads}
          speed={speed}
          gain={gain}
          isPaused={isPaused}
          onClose={onClose}
          onECGModeChange={setIsECGMode}
          onLayoutChange={setLayout}
          onLeadChange={setSelectedLead}
          onSpeedChange={setSpeed}
          onGainChange={setGain}
          onPauseToggle={() => setIsPaused(!isPaused)}
        />

        <ECGDisplayGrid
          patient={patient}
          layout={layout}
          selectedLead={selectedLead}
          leads={leads}
          isECGMode={isECGMode}
          isPaused={isPaused}
          speed={speed}
          dataBufferRef={dataBufferRef}
          canvasRefs={canvasRefs}
          getLatestValue={getLatestValue}
          drawAllWaveforms={drawAllWaveforms}
        />
      </div>
    </div>
  );
};