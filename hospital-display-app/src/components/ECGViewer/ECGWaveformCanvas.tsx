import React, { useEffect, forwardRef, useRef } from 'react';
import {
  renderWaveformSegment,
  drawMedicalGrid,
  mmToPixels
} from '../../utils/medicalWaveformUtils';
import {
  SAMPLE_RATE_HZ,
  LOG_SAMPLE_INTERVAL
} from '../../config/ecgConfig';

// Props for individual waveform canvas
interface ECGWaveformCanvasProps {
  leadIdx: number;
  leadName: string;
  dataBufferRef: React.MutableRefObject<number[][]>;
  isECGMode: boolean;
  isPaused: boolean;
  speed: number;
  gain: number; // mm/mV for ECG, μV/mm for EEG
  patientId: string;
  isPatientCard?: boolean; // Optional: true for patient card, false/undefined for full ECG viewer
}

// Canvas component for rendering a single lead's waveform
export const ECGWaveformCanvas = forwardRef<HTMLCanvasElement, ECGWaveformCanvasProps>(({
  leadIdx,
  leadName,
  dataBufferRef,
  isECGMode,
  isPaused,
  speed,
  gain,
  patientId,
  isPatientCard = false
}, ref) => {
  const internalRef = useRef<HTMLCanvasElement>(null);

  // ✅ NEW: Circular buffer state for ICU monitor-style sweep
  const writePosition = useRef(0);   // Current write position (0 to samplesVisible-1)
  const lastDataLength = useRef(0);  // Track data length changes

  // Set canvas ref
  const setCanvasRef = (element: HTMLCanvasElement | null) => {
    internalRef.current = element;
    if (typeof ref === 'function') {
      ref(element);
    } else if (ref) {
      ref.current = element;
    }
  };

  // Continuous animation loop
  // ✅ FIX: Add speed, gain, isECGMode to dependencies to prevent stale closure
  // When these props change, cancel old animation loop and start new one with fresh values
  useEffect(() => {
    let animationFrameId: number;
    const animate = () => {
      drawWaveform();
      if (!isPaused) animationFrameId = requestAnimationFrame(animate);
    };
    if (!isPaused) animationFrameId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrameId);
  }, [isPaused, speed, gain, isECGMode]);

  // Draw grid, waveform, and sweep line with circular buffer (ICU monitor style)
  const drawWaveform = () => {
    const canvas = internalRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // ✅ Read fresh data from ref on every animation frame (60fps)
    const data = dataBufferRef.current[leadIdx] || [];

    const dpr = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.scale(dpr, dpr);
    }

    // Clear canvas
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, width, height);

    // ✅ Baseline position:
    // ECG: 70% for patient card (more headroom for R-waves), 50% for full viewer
    // EEG: Always 50% centered (symmetrical brain waves)
    const baselineRatio = isECGMode
      ? (isPatientCard ? 0.7 : 0.5)  // ECG: 70% in card, 50% in full viewer
      : 0.5;                          // EEG: Always centered

    // Draw grid with appropriate baseline
    drawMedicalGrid(ctx, width, height, isECGMode, baselineRatio);

    // ✅ MEDICAL-STANDARD HORIZONTAL SCALING: Use actual speed prop (mm/s)
    // speed is in mm/s (e.g., 25mm/s for ECG, 30mm/s for EEG)
    const pixelsPerSecond = mmToPixels(speed); // User-selected speed at detected DPI
    const pixelsPerSample = pixelsPerSecond / SAMPLE_RATE_HZ; // speed ÷ 500Hz
    const samplesVisible = Math.floor(width / pixelsPerSample);

    // 🔍 DEBUG: Log actual spacing calculations (uses centralized LOG_SAMPLE_INTERVAL)
    if (LOG_SAMPLE_INTERVAL > 0 && data.length % LOG_SAMPLE_INTERVAL === 0) {
    }

    // ✅ MEDICAL-STANDARD VERTICAL SCALING: Use actual gain prop
    // ECG: gain is mm/mV (e.g., 10mm/mV), so 1mV = gain mm = gain * pixelsPerMm pixels
    // EEG: gain is μV/mm (e.g., 7μV/mm), so 1μV = (1/gain) mm = (1/gain) * pixelsPerMm pixels
    const pixelsPerUnit = isECGMode
      ? mmToPixels(gain)  // ECG: gain mm/mV → pixels per mV
      : mmToPixels(1 / gain); // EEG: gain μV/mm → pixels per μV

    // Draw waveform
    if (data.length >= 2) {
      const eegColors = ['#FFD700', '#00FFFF', '#FF69B4'];
      const leadColor = isECGMode ? '#00FF00' : eegColors[leadIdx % eegColors.length];

      // Update write position based on new data
      if (data.length !== lastDataLength.current) {
        if (data.length <= samplesVisible) {
          // Phase 1: Growing - not wrapped yet
          writePosition.current = data.length - 1;
        } else {
          // Phase 2: Continuous - wrapped, use modulo
          const newSamples = data.length - lastDataLength.current;
          writePosition.current = (writePosition.current + newSamples) % samplesVisible;
        }
        lastDataLength.current = data.length;
      }

      if (data.length <= samplesVisible) {
        // ✅ PHASE 1: ICU Monitor Typewriter Mode - render from RIGHT edge, growing leftward
        const waveformWidth = data.length * pixelsPerSample;
        const startX = width - waveformWidth;  // Start at right edge, grow left
        renderWaveformSegment(
          data,
          ctx,
          startX,
          height,
          isECGMode,
          pixelsPerSample,
          pixelsPerUnit,
          leadColor,
          baselineRatio
        );
      } else {
        // ✅ PHASE 2: ICU Monitor Typewriter Mode - show LAST samplesVisible samples (scrolling)
        // Always show most recent data, old data "scrolls off" left edge
        const visibleData = data.slice(-samplesVisible);

        renderWaveformSegment(
          visibleData,
          ctx,
          0,  // Fill entire screen from left to right
          height,
          isECGMode,
          pixelsPerSample,
          pixelsPerUnit,
          leadColor,
          baselineRatio
        );
      }
    } else {
      // No data - draw flat baseline at correct position
      ctx.strokeStyle = isECGMode ? '#00FF00' : '#FFD700';
      ctx.lineWidth = 2;
      ctx.beginPath();
      const baselineY = height * baselineRatio;
      ctx.moveTo(0, baselineY);
      ctx.lineTo(width, baselineY);
      ctx.stroke();
    }

    // ✅ ICU TYPEWRITER MODE: No sweep line needed - waveform scrolls continuously left
  };

  return (
    <div className="relative border-2 border-gray-600 rounded overflow-hidden flex flex-col w-full h-full">
      <canvas ref={setCanvasRef} className="w-full h-full" />
    </div>
  );
});