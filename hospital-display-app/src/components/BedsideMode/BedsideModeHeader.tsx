/**
 * BedsideModeHeader - Header component for bedside monitor controls
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade header with ECG/EEG toggle, display controls, and patient navigation
 */

import React from 'react';
import { X, Settings, Monitor, Activity, Zap, CreditCard, Volume2, VolumeX } from 'lucide-react';
import { patient } from '../../types';

interface BedsideModeHeaderProps {
  patients: patient[];
  displayCount: 1 | 2;
  isECGMode: boolean;
  audioAlarmsEnabled: boolean;
  currentPatientIndex: number;
  onClose: () => void;
  onDisplayCountChange: (count: 1 | 2) => void;
  onECGModeChange: (mode: boolean) => void;
  onAudioAlarmsToggle: () => void;
  onShowNFCLogin: () => void;
  onShowSettings: () => void;
  onPreviousPatient: () => void;
  onNextPatient: () => void;
}

export const BedsideModeHeader: React.FC<BedsideModeHeaderProps> = ({
  patients,
  displayCount,
  isECGMode,
  audioAlarmsEnabled,
  currentPatientIndex,
  onClose,
  onDisplayCountChange,
  onECGModeChange,
  onAudioAlarmsToggle,
  onShowNFCLogin,
  onShowSettings,
  onPreviousPatient,
  onNextPatient
}) => {
  return (
    <div className="bg-gray-950 px-6 py-4 flex items-center justify-between border-b-2 border-gray-700">
      <div className="flex items-center space-x-6">
        <div className="flex items-center space-x-3">
          <Monitor className="w-6 h-6 text-blue-400" />
          <span className="text-white font-bold text-lg tracking-wide">ICU BEDSIDE MONITOR</span>
        </div>

        <div className="flex items-center space-x-2 bg-gray-800 rounded-lg p-2 border border-gray-600">
          <button
            onClick={() => onECGModeChange(true)}
            className={`flex items-center space-x-2 px-4 py-2 rounded transition-all duration-200 ${
              isECGMode ? 'bg-green-700 text-white border border-green-500' : 'text-gray-400 hover:text-white hover:bg-gray-700'
            }`}
          >
            <Activity className="w-4 h-4" />
            <span className="font-medium">ECG</span>
          </button>
          <button
            onClick={() => onECGModeChange(false)}
            className={`flex items-center space-x-2 px-4 py-2 rounded transition-all duration-200 ${
              !isECGMode ? 'bg-yellow-700 text-white border border-yellow-500' : 'text-gray-400 hover:text-white hover:bg-gray-700'
            }`}
          >
            <Zap className="w-4 h-4" />
            <span className="font-medium">EEG</span>
          </button>
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-gray-300 text-sm font-medium">Display:</span>
          <button
            onClick={() => onDisplayCountChange(1)}
            className={`px-4 py-2 rounded transition-all duration-200 text-sm font-medium border ${
              displayCount === 1 ? 'bg-blue-700 text-white border-blue-500' : 'bg-gray-700 text-gray-300 border-gray-600 hover:bg-gray-600'
            }`}
          >
            Single
          </button>
          <button
            onClick={() => onDisplayCountChange(2)}
            disabled={patients.length < 2}
            className={`px-4 py-2 rounded transition-all duration-200 text-sm font-medium border ${
              displayCount === 2 ? 'bg-blue-700 text-white border-blue-500' : 'bg-gray-700 text-gray-300 border-gray-600'
            } ${patients.length < 2 ? 'opacity-50 cursor-not-allowed' : 'hover:bg-gray-600'}`}
          >
            Dual {patients.length < 2 ? '(Need 2+ Patients)' : ''}
          </button>
        </div>

        {/* Patient Navigation (only show in single view mode with multiple patients) */}
        {displayCount === 1 && patients.length > 1 && (
          <div className="flex items-center space-x-3 bg-gray-800 rounded-lg p-2 border border-gray-600">
            <span className="text-gray-300 text-sm font-medium">Patient:</span>
            <button
              onClick={onPreviousPatient}
              className="p-1 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors"
              title="Previous Patient"
            >
              ←
            </button>
            <span className="text-white font-medium min-w-[3rem] text-center">
              {currentPatientIndex + 1} / {patients.length}
            </span>
            <button
              onClick={onNextPatient}
              className="p-1 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors"
              title="Next Patient"
            >
              →
            </button>
          </div>
        )}
      </div>

      <div className="flex items-center space-x-4">
        <button
          onClick={onAudioAlarmsToggle}
          className={`p-3 rounded-lg transition-all duration-200 border ${
            audioAlarmsEnabled
              ? 'text-blue-400 border-blue-500 hover:bg-blue-900'
              : 'text-gray-400 border-gray-600 hover:text-white hover:bg-gray-700'
          }`}
          title="Toggle Audio Alarms"
        >
          {audioAlarmsEnabled ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5" />}
        </button>
        <button
          onClick={onShowNFCLogin}
          className="flex items-center space-x-2 p-3 text-blue-400 hover:text-white hover:bg-blue-900 rounded-lg border border-blue-500 transition-all duration-200"
          title="NFC Login"
        >
          <CreditCard className="w-5 h-5" />
          <span className="text-sm font-medium">NFC</span>
        </button>
        <button
          onClick={onShowSettings}
          className="p-3 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg border border-gray-600 transition-all duration-200"
          title="Settings"
        >
          <Settings className="w-5 h-5" />
        </button>
        <button
          onClick={onClose}
          className="p-3 text-gray-400 hover:text-white hover:bg-red-900 rounded-lg border border-red-600 transition-all duration-200"
          title="Exit Monitor"
        >
          <X className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};