/**
 * ECGWaveformCanvas - Individual canvas component for ECG/EEG waveform display
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade canvas rendering with auto-scaling and grid display
 */

import React, { useEffect, forwardRef, useRef } from 'react';

interface ECGWaveformCanvasProps {
  leadIdx: number;
  leadName: string;
  data: number[];
  isECGMode: boolean;
  isPaused: boolean;
  speed: number;
  patientId: string;
}

export const ECGWaveformCanvas = forwardRef<HTMLCanvasElement, ECGWaveformCanvasProps>(({
  leadIdx,
  leadName,
  data,
  isECGMode,
  isPaused,
  speed,
  patientId
}, ref) => {
  const internalRef = useRef<HTMLCanvasElement>(null);

  // Create a callback that sets both the internal ref and the forwarded ref
  const setCanvasRef = (element: HTMLCanvasElement | null) => {
    internalRef.current = element;
    if (typeof ref === 'function') {
      ref(element);
    } else if (ref) {
      ref.current = element;
    }
  };

  useEffect(() => {
    drawWaveform();
  }, [data, isECGMode, isPaused, speed, leadIdx]);

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

  const drawWaveform = () => {
    const canvas = internalRef.current;
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

  return (
    <div className="relative border-2 border-gray-600 rounded overflow-hidden flex flex-col w-full h-full">
      <canvas
        ref={setCanvasRef}
        className="w-full h-full"
      />
      <div className="absolute top-2 left-2 bg-gray-800 bg-opacity-75 rounded px-2 py-1 text-xs">
        <div
          className={`w-2 h-2 rounded-full inline-block mr-2 ${
            isPaused ? 'bg-red-500' : isECGMode ? 'bg-green-500 animate-pulse' : 'bg-yellow-500 animate-pulse'
          }`}
        ></div>
        Lead: {leadName} • {isPaused ? 'PAUSED' : 'AUTO-SCALED'}
      </div>
    </div>
  );
});