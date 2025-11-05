/**
 * useECGViewer - Custom hook for ECG/EEG viewer state management and real waveform streaming
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade ECG/EEG monitoring with real-time waveform data from ESP32 watches
 */

import { useState, useEffect, useRef } from 'react';
import { patient } from '../types';
import { useWebSocket } from './useWebSocket';
import waveformCacheService from '../services/WaveformCacheService';
import { logger } from '../utils/logger';
import { adcToMillivolts, adcToMicrovolts, decodeDeltaChannel } from '../utils/medicalWaveformUtils';
import {
  BUFFER_TIME_SECONDS,
  ECG_DEFAULT_SPEED,
  EEG_DEFAULT_SPEED,
  ECG_DEFAULT_GAIN,
  EEG_DEFAULT_GAIN
} from '../config/ecgConfig';

interface UseECGViewerProps {
  patient: patient;
}

export const useECGViewer = ({ patient }: UseECGViewerProps) => {
  const [isECGMode, setIsECGMode] = useState(true); // true = ECG, false = EEG
  // ✅ Mode-specific defaults (ECG: 25mm/s @ 10mm/mV, EEG: 30mm/s @ 7μV/mm)
  const [speed, setSpeed] = useState(ECG_DEFAULT_SPEED); // mm/s - changes per mode
  const [gain, setGain] = useState(ECG_DEFAULT_GAIN); // mm/mV for ECG, μV/mm for EEG - changes per mode
  const [isPaused, setIsPaused] = useState(false);
  const [selectedLead, setSelectedLead] = useState<string>('II'); // Default to Lead II for ECG
  const [layout, setLayout] = useState(1); // 1, 4, or 9 views
  const [showCalibration, setShowCalibration] = useState(true); // ✅ NEW: Calibration pulse state (vestigial - not used by canvas)

  const canvasRefs = useRef<(HTMLCanvasElement | null)[]>([]);
  // ✅ FIX: Always allocate 22 buffers (ECG: 0-11, EEG: 12-21) regardless of mode
  const dataBufferRef = useRef<number[][]>(Array(22).fill(null).map(() => []));
  const calibrationStartRef = useRef<number>(Date.now()); // ✅ NEW: Track calibration start time

  // Define leads for ECG and EEG
  const ecgLeads = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6'];
  // ✅ FIXED: 8 monopolar channels matching ADS1298 hardware (Fp1, Fp2, F3, F4, C3, C4, O1, O2)
  const eegLeads = ['Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4', 'O1', 'O2'];
  const leads = isECGMode ? ecgLeads : eegLeads;

  // WebSocket subscription for real waveform data
  const { subscribe, unsubscribe } = useWebSocket();

  // Update selected lead AND speed/gain defaults when switching modes
  useEffect(() => {
    const newSelectedLead = isECGMode ? 'II' : 'Fp1';
    setSelectedLead(newSelectedLead);

    // ✅ Update speed/gain to mode-specific medical standards
    setSpeed(isECGMode ? ECG_DEFAULT_SPEED : EEG_DEFAULT_SPEED);
    setGain(isECGMode ? ECG_DEFAULT_GAIN : EEG_DEFAULT_GAIN);

    // ✅ FIX: Don't reset buffers - they're pre-allocated with 22 elements
  }, [isECGMode]);

  // ✅ NEW: Reset calibration when patient, mode, or layout changes
  useEffect(() => {
    calibrationStartRef.current = Date.now();
    setShowCalibration(true);
    logger.log('🔧 Calibration pulse enabled (permanent display)');
  }, [patient.id, isECGMode, layout]);

  // Handle layout changes: adjust canvas refs
  useEffect(() => {
    canvasRefs.current = Array(layout).fill(null);
  }, [layout]);

  // ✅ Clear buffers when PATIENT or MODE changes to prevent stale/wrong data
  // Physical cable swap (ECG ↔ EEG) requires fresh buffers for new sensor configuration
  useEffect(() => {
    // Clear any existing cache
    waveformCacheService.invalidateCache(patient.id, isECGMode ? 'ecg' : 'eeg').catch(err => {
      logger.warn(`⚠️ Failed to invalidate cache: ${err}`);
    });

    // Clear existing data in all 22 buffers
    for (let i = 0; i < 22; i++) {
      dataBufferRef.current[i] = [];
    }
    logger.log(`🆕 Blank canvas initialized - 22 empty buffers ready for fresh ${isECGMode ? 'ECG' : 'EEG'} data`);
  }, [patient.id, isECGMode]); // ✅ Clear on both patient AND mode changes

  // Subscribe to real waveform data from WebSocket
  useEffect(() => {
    if (!patient.id || !patient.assignedDeviceId) {
      if (!patient.assignedDeviceId) {
        logger.log('⚠️ No device assigned - waveform display unavailable');
      }
      return;
    }
    // Cache loads in parallel - don't block streaming

    logger.log(`🔌 Subscribing to waveform data for patient ${patient.id.substring(0, 8)} with calibration trigger`);

    const subscriptionId = subscribe((message: any) => {
      // Only process waveformStream messages for this patient
      if (message.type !== 'waveformStream' || message.patientId !== patient.id) return;
      if (isPaused) return; // Don't update buffers if paused

      const waveformData = message.waveform;
      if (!waveformData) {
        logger.warn('⚠️ Received waveform message without data');
        return;
      }

      // Auto-detect mode from ESP32 and switch display accordingly
      if (waveformData.mode === 'ecg' && !isECGMode) {
        logger.log('🔄 Auto-switching to ECG mode (detected from device)');
        setIsECGMode(true);
      } else if (waveformData.mode === 'eeg' && isECGMode) {
        logger.log('🔄 Auto-switching to EEG mode (detected from device)');
        setIsECGMode(false);
      }

      // Process ECG waveform data (12 leads) - ALWAYS process if present
      // ECG uses buffer indices 0-11
      // ✅ v5.2.5: Supports delta-encoded format from ESP32
      if (waveformData.ecgWaveform) {
        const { limb, precordial, derived } = waveformData.ecgWaveform;
        // ✅ Use centralized buffer configuration from ecgConfig
        const maxBufferSize = Math.ceil((waveformData.sampleRate || 500) * BUFFER_TIME_SECONDS);

        // Helper: Check if data is delta-encoded or raw array
        const getData = (leadData: any, leadName?: string) => {
          if (!leadData) return [];
          // Delta-encoded: {baseline: number, deltas: number[]}
          if (leadData.baseline !== undefined && leadData.deltas !== undefined) {
            return decodeDeltaChannel(leadData);
          }
          // Raw array (legacy v5.2.4 and earlier)
          if (Array.isArray(leadData)) {
            return leadData;
          }
          return [];
        };

        // Limb leads (I, II, III) - REQUIRED
        // ✅ v5.2.5: leadI, leadII, leadIII (camelCase with Roman numerals)
        if (limb?.leadI) {
          const samples = getData(limb.leadI, 'Lead I');
          dataBufferRef.current[0] = [...dataBufferRef.current[0], ...samples].slice(-maxBufferSize);
        }
        if (limb?.leadII) {
          const samples = getData(limb.leadII, 'Lead II');
          dataBufferRef.current[1] = [...dataBufferRef.current[1], ...samples].slice(-maxBufferSize);
        }
        if (limb?.leadIII) {
          const samples = getData(limb.leadIII, 'Lead III');
          dataBufferRef.current[2] = [...dataBufferRef.current[2], ...samples].slice(-maxBufferSize);
        }

        // Derived leads (aVR, aVL, aVF) - OPTIONAL
        if (derived?.avr) {
          const samples = getData(derived.avr);
          dataBufferRef.current[3] = [...dataBufferRef.current[3], ...samples].slice(-maxBufferSize);
        }
        if (derived?.avl) {
          const samples = getData(derived.avl);
          dataBufferRef.current[4] = [...dataBufferRef.current[4], ...samples].slice(-maxBufferSize);
        }
        if (derived?.avf) {
          const samples = getData(derived.avf);
          dataBufferRef.current[5] = [...dataBufferRef.current[5], ...samples].slice(-maxBufferSize);
        }

        // Precordial leads (V1-V6) - OPTIONAL
        if (precordial?.v1) {
          const samples = getData(precordial.v1, 'V1');
          dataBufferRef.current[6] = [...dataBufferRef.current[6], ...samples].slice(-maxBufferSize);
        }
        if (precordial?.v2) {
          const samples = getData(precordial.v2, 'V2');
          dataBufferRef.current[7] = [...dataBufferRef.current[7], ...samples].slice(-maxBufferSize);
        }
        if (precordial?.v3) {
          const samples = getData(precordial.v3, 'V3');
          dataBufferRef.current[8] = [...dataBufferRef.current[8], ...samples].slice(-maxBufferSize);
        }
        if (precordial?.v4) {
          const samples = getData(precordial.v4, 'V4');
          dataBufferRef.current[9] = [...dataBufferRef.current[9], ...samples].slice(-maxBufferSize);
        }
        if (precordial?.v5) {
          const samples = getData(precordial.v5, 'V5');
          dataBufferRef.current[10] = [...dataBufferRef.current[10], ...samples].slice(-maxBufferSize);
        }
        if (derived?.v6) {
          const samples = getData(derived.v6, 'V6');
          dataBufferRef.current[11] = [...dataBufferRef.current[11], ...samples].slice(-maxBufferSize);
        }

        // Save ECG waveforms to cache
        waveformCacheService.saveWaveform(
          patient.id,
          'ecg',
          dataBufferRef.current.slice(0, 12),
          waveformData.sampleRate || 250
        );
      }

      // Process EEG waveform data (9 channels) - ALWAYS process if present
      // EEG uses buffer indices 12-20 to avoid collision with ECG
      // ✅ v5.2.5: Supports delta-encoded format from ESP32
      if (waveformData.eegWaveform) {
        const { frontal, central, temporal, occipital } = waveformData.eegWaveform;
        // ✅ Use centralized buffer configuration from ecgConfig
        const maxBufferSize = Math.ceil((waveformData.sampleRate || 500) * BUFFER_TIME_SECONDS);

        // Helper: Check if data is delta-encoded or raw array
        const getData = (channelData: any) => {
          if (!channelData) return [];
          // Delta-encoded: {baseline: number, deltas: number[]}
          if (channelData.baseline !== undefined && channelData.deltas !== undefined) {
            return decodeDeltaChannel(channelData);
          }
          // Raw array (legacy v5.2.4 and earlier)
          if (Array.isArray(channelData)) {
            return channelData;
          }
          return [];
        };

        // Frontal channels (Fp1, Fp2, F3, F4) - REQUIRED
        // ✅ v5.2.5: Fp1, Fp2, F3, F4 (proper capitalization)
        if (frontal?.Fp1) {
          const samples = getData(frontal.Fp1);
          dataBufferRef.current[12] = [...dataBufferRef.current[12], ...samples].slice(-maxBufferSize);
        }
        if (frontal?.Fp2) {
          const samples = getData(frontal.Fp2);
          dataBufferRef.current[13] = [...dataBufferRef.current[13], ...samples].slice(-maxBufferSize);
        }
        if (frontal?.F3) {
          const samples = getData(frontal.F3);
          dataBufferRef.current[14] = [...dataBufferRef.current[14], ...samples].slice(-maxBufferSize);
        }
        if (frontal?.F4) {
          const samples = getData(frontal.F4);
          dataBufferRef.current[15] = [...dataBufferRef.current[15], ...samples].slice(-maxBufferSize);
        }

        // Central channels (C3, C4) - REQUIRED
        // ✅ v5.2.5: C3, C4 (proper capitalization)
        if (central?.C3) {
          const samples = getData(central.C3);
          dataBufferRef.current[16] = [...dataBufferRef.current[16], ...samples].slice(-maxBufferSize);
        }
        if (central?.C4) {
          const samples = getData(central.C4);
          dataBufferRef.current[17] = [...dataBufferRef.current[17], ...samples].slice(-maxBufferSize);
        }

        // Temporal channels (T3, T4) - OPTIONAL
        if (temporal?.T3) {
          const samples = getData(temporal.T3);
          dataBufferRef.current[18] = [...dataBufferRef.current[18], ...samples].slice(-maxBufferSize);
        }
        if (temporal?.T4) {
          const samples = getData(temporal.T4);
          dataBufferRef.current[19] = [...dataBufferRef.current[19], ...samples].slice(-maxBufferSize);
        }

        // Occipital channels (O1, O2) - OPTIONAL
        // ✅ v5.2.5: O1, O2 (proper capitalization)
        if (occipital?.O1) {
          const samples = getData(occipital.O1);
          dataBufferRef.current[20] = [...dataBufferRef.current[20], ...samples].slice(-maxBufferSize);
        }
        if (occipital?.O2) {
          const samples = getData(occipital.O2);
          dataBufferRef.current[21] = [...dataBufferRef.current[21], ...samples].slice(-maxBufferSize);
        }

        // Save EEG waveforms to cache
        waveformCacheService.saveWaveform(
          patient.id,
          'eeg',
          dataBufferRef.current.slice(12, 21),
          waveformData.sampleRate || 250
        );
      }
    }, patient.id, true); // ← ADD patientId and triggerCalibration=true for calibration pulse

    return () => {
      logger.log(`🔌 Unsubscribing from waveform data for patient ${patient.id.substring(0, 8)}`);
      unsubscribe(subscriptionId);
    };
  }, [patient.id, patient.assignedDeviceId, isECGMode, isPaused, subscribe, unsubscribe]);

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

    // ✅ FIX: Convert RAW ADC value to mV/μV before displaying
    const rawADC = data[data.length - 1];
    const latestValue = isECGMode ? adcToMillivolts(rawADC) : adcToMicrovolts(rawADC);
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
    showCalibration, // ✅ NEW: Calibration pulse visibility

    // Refs
    canvasRefs,
    dataBufferRef,
    calibrationStartRef, // ✅ NEW: Calibration timing

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