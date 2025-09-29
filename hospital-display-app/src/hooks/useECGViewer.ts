/**
 * useECGViewer - Custom hook for ECG/EEG viewer state management and data generation
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade ECG/EEG monitoring with real-time waveform generation
 */

import { useState, useEffect, useRef } from 'react';
import { patient } from '../types';

interface UseECGViewerProps {
  patient: patient;
}

export const useECGViewer = ({ patient }: UseECGViewerProps) => {
  const [isECGMode, setIsECGMode] = useState(true); // true = ECG, false = EEG
  const [speed, setSpeed] = useState(25); // mm/s
  const [gain, setGain] = useState(10); // mm/mV for ECG, μV/mm for EEG
  const [isPaused, setIsPaused] = useState(false);
  const [selectedLead, setSelectedLead] = useState<string>('II'); // Default to Lead II for ECG
  const [layout, setLayout] = useState(1); // 1, 4, or 9 views

  const canvasRefs = useRef<(HTMLCanvasElement | null)[]>([]);
  const animationRef = useRef<number | null>(null);
  const dataBufferRef = useRef<number[][]>([]);
  const calibrationPulseRef = useRef<boolean[]>([]);

  // Define leads for ECG and EEG
  const ecgLeads = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6'];
  const eegLeads = ['F3-C3', 'F4-C4', 'C3-P3', 'C4-P4', 'P3-O1', 'P4-O2', 'F7-T3', 'F8-T4', 'T5-O1'];
  const leads = isECGMode ? ecgLeads : eegLeads;

  // Update selected lead and reset data buffers when switching modes
  useEffect(() => {
    const newSelectedLead = isECGMode ? 'II' : 'F3-C3';
    setSelectedLead(newSelectedLead);
    dataBufferRef.current = Array(leads.length).fill(null).map(() => []);
    calibrationPulseRef.current = Array(leads.length).fill(true);
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
            // Generate realistic waveform data
            if (isECGMode) {
              // Generate realistic ECG waveform for different leads
              const lead = leads[leadIdx];
              const heartRate = patient.vitals?.heartRate || 0; // BPM
              const beatPeriod = heartRate > 0 ? 60.0 / heartRate : 1.0; // Default 1s period if no heartRate
              const phase = ((timeIndex / sampleRate) % beatPeriod) / beatPeriod;

              if (lead === 'II') {
                // Lead II - prominent P wave, R wave, T wave
                // P wave (0.05-0.15 phase)
                const pWave = (0.05 <= phase && phase <= 0.15) ?
                  0.2 * Math.exp(-Math.pow((phase - 0.1) * 20, 2)) : 0;

                // QRS complex (0.25-0.35 phase)
                let qrsWave = 0;
                if (0.25 <= phase && phase <= 0.35) {
                  const qrsPhase = (phase - 0.25) * 40;
                  if (qrsPhase < 2) {
                    qrsWave = -0.3 * Math.sin(qrsPhase * Math.PI); // Q wave
                  } else if (qrsPhase < 6) {
                    qrsWave = 1.2 * Math.sin((qrsPhase - 2) * Math.PI / 4); // R wave
                  } else {
                    qrsWave = -0.4 * Math.sin((qrsPhase - 6) * Math.PI / 4); // S wave
                  }
                }

                // T wave (0.5-0.7 phase)
                const tWave = (0.5 <= phase && phase <= 0.7) ?
                  0.3 * Math.exp(-Math.pow((phase - 0.6) * 15, 2)) : 0;

                // Add small noise
                const noise = 0.02 * (Math.sin(timeIndex * 0.4) + Math.sin(timeIndex * 0.6) * 0.5);

                value = pWave + qrsWave + tWave + noise;
              } else if (['I', 'III', 'aVR', 'aVL', 'aVF'].includes(lead)) {
                // Other limb leads - similar but different amplitudes
                const amplitudeFactor = ['I', 'III'].includes(lead) ? 0.7 : 0.5;
                value = amplitudeFactor * Math.sin(phase * 2 * Math.PI) * Math.exp(-Math.pow((phase - 0.3) * 8, 2));
              } else {
                // Precordial leads V1-V6
                value = 0.8 * Math.sin(phase * 2 * Math.PI) * Math.exp(-Math.pow((phase - 0.3) * 10, 2));
              }
            } else {
              // Generate realistic EEG patterns
              const t = timeIndex / sampleRate;
              // Alpha waves (8-12 Hz), Beta waves (13-30 Hz), etc.
              const alpha = 0.5 * Math.sin(2 * Math.PI * 10 * t);
              const beta = 0.2 * Math.sin(2 * Math.PI * 20 * t);
              const theta = 0.3 * Math.sin(2 * Math.PI * 6 * t);

              // Add some random noise
              const noise = 0.1 * Math.sin(2 * Math.PI * 50 * t) * Math.sin(2 * Math.PI * 0.1 * t);

              value = alpha + beta + theta + noise;
            }
          }

          dataBufferRef.current[leadIdx].push(value);

          const maxBufferSize = sampleRate * 10;
          if (dataBufferRef.current[leadIdx].length > maxBufferSize) {
            dataBufferRef.current[leadIdx].shift();
          }
        }
      }

      animationRef.current = requestAnimationFrame(generateRealTimeData);
    };

    generateRealTimeData();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [patient.vitals.heartRate, patient.vitals.ecgReading, patient.vitals.eegReading, isPaused, isECGMode, speed, gain, leads, layout, selectedLead]); // eslint-disable-line react-hooks/exhaustive-deps

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

  return {
    // State
    isECGMode,
    speed,
    gain,
    isPaused,
    selectedLead,
    layout,
    leads,

    // Refs
    canvasRefs,
    dataBufferRef,

    // Setters
    setIsECGMode,
    setSpeed,
    setGain,
    setIsPaused,
    setSelectedLead,
    setLayout,

    // Computed values
    getLatestValue
  };
};