import { useState, useEffect, useCallback } from 'react';
import { patient } from '../types';

interface UseECGViewerProps {
  patient: patient;
  onToggleECGMode?: (patient: patient) => void;
}

export const useECGViewer = ({ patient, onToggleECGMode }: UseECGViewerProps) => {
  const [isEcgMode, setIsECGMode] = useState<boolean>(patient.vitals?.isEcgMode ?? true);

  // Sync with patient vitals when they change
  useEffect(() => {
    setIsECGMode(patient.vitals?.isEcgMode || false);
  }, [patient.vitals?.isEcgMode]);

  // Handle ECG/EEG toggle
  const handleToggleECGMode = useCallback((newMode: boolean) => {
    setIsECGMode(newMode); // Update local state for simulation
    if (onToggleECGMode) {
      const updatedPatient = {
        ...patient,
        vitals: {
          ...patient.vitals,
          isEcgMode: newMode
        }
      };
      onToggleECGMode(updatedPatient); // Call parent callback if provided
    }
  }, [patient, onToggleECGMode]);

  // Get current reading based on mode
  const getCurrentReading = useCallback(() => {
    if (isEcgMode) {
      return {
        reading: patient.vitals?.ecgReading || '--',
        unit: 'mV',
        type: 'ECG'
      };
    } else {
      return {
        reading: patient.vitals?.eegReading || '--',
        unit: 'μV',
        type: 'EEG'
      };
    }
  }, [isEcgMode, patient.vitals]);

  // Get lead options based on mode
  const getLeadOptions = useCallback(() => {
    if (isEcgMode) {
      return [
        { value: 'I', label: 'Lead I' },
        { value: 'II', label: 'Lead II' },
        { value: 'III', label: 'Lead III' },
        { value: 'aVR', label: 'aVR' },
        { value: 'aVL', label: 'aVL' },
        { value: 'aVF', label: 'aVF' },
        { value: 'V1', label: 'V1' },
        { value: 'V2', label: 'V2' },
        { value: 'V3', label: 'V3' },
        { value: 'V4', label: 'V4' },
        { value: 'V5', label: 'V5' },
        { value: 'V6', label: 'V6' }
      ];
    } else {
      return [
        { value: 'F3-F4', label: 'F3-F4' },
        { value: 'C3-C4', label: 'C3-C4' },
        { value: 'P3-P4', label: 'P3-P4' },
        { value: 'O1-O2', label: 'O1-O2' },
        { value: 'T3-T4', label: 'T3-T4' },
        { value: 'T5-T6', label: 'T5-T6' }
      ];
    }
  }, [isEcgMode]);

  // Get default selected lead
  const getDefaultLead = useCallback(() => {
    return isEcgMode ? 'II' : 'C3-C4';
  }, [isEcgMode]);

  // Get display colors
  const getDisplayColors = useCallback(() => {
    return {
      primary: isEcgMode ? '#10B981' : '#3B82F6', // green for ECG, blue for EEG
      secondary: isEcgMode ? 'text-green-400' : 'text-blue-400',
      background: isEcgMode ? 'bg-green-400' : 'bg-blue-400',
      button: isEcgMode ? 'bg-green-600' : 'bg-blue-600',
      buttonHover: isEcgMode ? 'hover:bg-green-700' : 'hover:bg-blue-700'
    };
  }, [isEcgMode]);

  // Get signal description
  const getSignalDescription = useCallback(() => {
    return {
      title: isEcgMode ? 'Cardiac Rhythm' : 'Brain Activity',
      signal: isEcgMode ? 'Cardiac Signal' : 'Brain Signal'
    };
  }, [isEcgMode]);

  return {
    isEcgMode,
    handleToggleECGMode,
    getCurrentReading,
    getLeadOptions,
    getDefaultLead,
    getDisplayColors,
    getSignalDescription
  };
};