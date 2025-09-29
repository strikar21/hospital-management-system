/**
 * useBedsideMode - Custom hook for bedside monitor state management
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade state management for ICU bedside monitoring system
 */

import { useState, useEffect } from 'react';
import { patient, user, appsettings } from '../types';

interface UseBedsideModeProps {
  patients: patient[];
  settings?: appsettings;
  onNFCTap?: (user: user) => void;
}

export const useBedsideMode = ({ patients, settings, onNFCTap }: UseBedsideModeProps) => {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [showSettings, setShowSettings] = useState(false);
  const [showNFCLogin, setShowNFCLogin] = useState(false);
  const [audioAlarmsEnabled, setAudioAlarmsEnabled] = useState<boolean>(settings?.audioAlarms || true);
  const [isECGMode, setIsECGMode] = useState<boolean>(true);
  const [currentPatientIndex, setCurrentPatientIndex] = useState<number>(0);

  // Medical safety: Reset patient index with proper bounds checking
  useEffect(() => {
    if (patients.length === 0) {
      // No patients available - ensure index is safe
      setCurrentPatientIndex(0);
    } else if (currentPatientIndex >= patients.length) {
      // Current index out of bounds - reset to last valid index
      setCurrentPatientIndex(Math.max(0, patients.length - 1));
    }
    // If currentPatientIndex is negative (edge case), reset to 0
    else if (currentPatientIndex < 0) {
      setCurrentPatientIndex(0);
    }
  }, [patients.length, currentPatientIndex]);

  // Time update effect
  useEffect(() => {
    const interval = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  // Online/offline status effect
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // NFC scanning handler - backend integration needed
  const handleNFCScan = async () => {
    alert('NFC scanning requires backend integration. Please use credential login instead.');
    setShowNFCLogin(false);
  };

  // Patient navigation handlers
  const handlePreviousPatient = () => {
    setCurrentPatientIndex((prev) => (prev - 1 + patients.length) % patients.length);
  };

  const handleNextPatient = () => {
    setCurrentPatientIndex((prev) => (prev + 1) % patients.length);
  };

  // Display mode handlers
  const handleDisplayModeChange = (count: 1 | 2, onDisplayCountChange: (count: 1 | 2) => void) => {
    if (count === 1) {
      setCurrentPatientIndex(0);
    }
    onDisplayCountChange(count);
  };

  return {
    // State
    currentTime,
    isOnline,
    showSettings,
    showNFCLogin,
    audioAlarmsEnabled,
    isECGMode,
    currentPatientIndex,

    // Setters
    setShowSettings,
    setShowNFCLogin,
    setAudioAlarmsEnabled,
    setIsECGMode,
    setCurrentPatientIndex,

    // Handlers
    handleNFCScan,
    handlePreviousPatient,
    handleNextPatient,
    handleDisplayModeChange
  };
};