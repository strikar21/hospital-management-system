/**
 * ECGViewerHeader - Header component for ECG/EEG viewer with controls
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade header with mode toggles, layout controls, and patient information
 */

import React from 'react';
import { X, Activity, Zap } from 'lucide-react';
import { patient } from '../../types';

interface ECGViewerHeaderProps {
  patient: patient;
  isECGMode: boolean;
  layout: number;
  selectedLead: string;
  leads: string[];
  speed: number;
  gain: number;
  isPaused: boolean;
  onClose: () => void;
  onECGModeChange: (mode: boolean) => void;
  onLayoutChange: (layout: number) => void;
  onLeadChange: (lead: string) => void;
  onSpeedChange: (speed: number) => void;
  onGainChange: (gain: number) => void;
  onPauseToggle: () => void;
}

export const ECGViewerHeader: React.FC<ECGViewerHeaderProps> = ({
  patient,
  isECGMode,
  layout,
  selectedLead,
  leads,
  speed,
  gain,
  isPaused,
  onClose,
  onECGModeChange,
  onLayoutChange,
  onLeadChange,
  onSpeedChange,
  onGainChange,
  onPauseToggle
}) => {
  return (
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
            onClick={() => onECGModeChange(true)}
            className={`flex items-center space-x-2 px-3 py-1 rounded transition-colors ${
              isECGMode ? 'bg-green-600 text-white' : 'text-gray-400 hover:text-white'
            }`}
          >
            <Activity className="w-4 h-4" />
            <span>ECG</span>
          </button>
          <button
            onClick={() => onECGModeChange(false)}
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
            onChange={(e) => onLayoutChange(Number(e.target.value))}
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
              onChange={(e) => onLeadChange(e.target.value)}
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
            onChange={(e) => onSpeedChange(Number(e.target.value))}
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
            onChange={(e) => onGainChange(Number(e.target.value))}
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
            onClick={onPauseToggle}
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
            {isECGMode ? `${patient.vitals.ecgReading} mV` : `${patient.vitals.eegReading || '--'} μV • Auto-scaled`}
          </div>
        </div>
      </div>
    </div>
  );
};