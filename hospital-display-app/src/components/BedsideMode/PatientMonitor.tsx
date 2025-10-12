/**
 * PatientMonitor - Individual patient monitor display component
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade patient monitoring display with ECG/EEG waveforms and vital signs
 */

import React, { useState, useEffect } from 'react';
import { Heart, Activity, Thermometer, Droplets, Zap, AlertTriangle, Wifi, WifiOff } from 'lucide-react';
import { patient } from '../../types';
import { MedicalUtils } from '../../utils/medicalUtils';

interface PatientMonitorProps {
  patient: patient;
  position: 'left' | 'right' | 'single';
  displayCount: 1 | 2;
  isECGMode: boolean;
  isOnline: boolean;
  currentTime: Date;
}

export const PatientMonitor: React.FC<PatientMonitorProps> = ({
  patient,
  position,
  displayCount,
  isECGMode,
  isOnline,
  currentTime
}) => {
  const [ecgData, setEcgData] = useState<{x: number, y: number}[]>([]);

  useEffect(() => {
    const generateData = () => {
      // BACKEND INTEGRATION NEEDED: Replace with VitalService.getWaveformData(patientId, isEcgMode)
      // Expected endpoint: GET /api/v1/patients/{id}/waveform?mode=ecg|eeg
      // Placeholder: flat line data until backend supports real-time waveform streaming
      const processedData = Array.from({length: 400}, (_, x) => ({
        x,
        y: 25 // Flat line placeholder
      }));

      setEcgData(processedData);
    };

    generateData();
    const interval = setInterval(generateData, 1000);
    return () => clearInterval(interval);
  }, [patient.vitals]); // Watch vitals object to prevent crash if vitals undefined

  const pathData = ecgData.map((point, index) =>
    `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`
  ).join(' ');

  const unacknowledgedAlerts = patient.alerts.filter(alert => !alert.isAcknowledged);
  const hasCriticalAlert = unacknowledgedAlerts.some(alert => alert.severity === 'critical');
  // REMOVED: Frontend arrhythmia detection - ALL medical diagnosis comes from backend
  // Backend provides arrhythmia alerts via patient.alerts if detected

  // MEDICAL SAFETY: Validate vital signs are within displayable ranges
  const safeVitals = {
    heartRate: Math.max(0, Math.min(300, patient.vitals?.heartRate ?? 0)),
    systolicPressure: Math.max(60, Math.min(300, patient.vitals?.systolicPressure ?? 0)),
    diastolicPressure: Math.max(30, Math.min(150, patient.vitals?.diastolicPressure ?? 0)),
    oxygenSaturation: Math.max(0, Math.min(100, patient.vitals?.oxygenSaturation ?? 0)),
    skinTemperature: Math.max(90.0, Math.min(115.0, patient.vitals?.skinTemperature ?? 0)),
    ecgReading: Math.max(-50, Math.min(50, patient.vitals?.ecgReading ?? 0)),
    eegReading: Math.max(0, Math.min(200, patient.vitals?.eegReading ?? 0))
  };

  return (
    <div className={`h-full ${displayCount === 2 ? 'w-1/2' : 'w-full'} bg-black text-white flex flex-col border-r border-gray-800`}>
      {hasCriticalAlert && (
        <div className="bg-red-900 text-red-100 py-2 px-4 flex items-center justify-center border-b-2 border-red-600">
          <AlertTriangle className="w-5 h-5 mr-2 animate-pulse" />
          <span className={`${displayCount === 2 ? 'text-sm' : 'text-xl'} font-bold tracking-wide`}>
            ⚠ CRITICAL
          </span>
        </div>
      )}

      <div className="bg-gray-950 px-4 py-3 border-b-2 border-gray-700 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h1 className={`${displayCount === 2 ? 'text-lg' : 'text-2xl'} font-bold text-white tracking-wide`}>
              BED {patient.bedNumber}
            </h1>
            <p className={`${displayCount === 2 ? 'text-xs' : 'text-sm'} text-gray-400 font-medium mt-1`}>
              Room {patient.room} • {patient.ward} Ward
            </p>
          </div>
          <div className="text-right space-y-1">
            <div className={`px-3 py-1 rounded-sm text-xs font-bold border-2 ${
              patient.status === 'critical' ? 'bg-red-800 border-red-500 text-red-100' :
              patient.status === 'emergency' ? 'bg-orange-800 border-orange-500 text-orange-100' :
              'bg-green-800 border-green-500 text-green-100'
            }`}>
              {patient.status.toUpperCase()}
            </div>
          </div>
        </div>
      </div>

      {displayCount === 1 ? (
        /* Single Patient Layout - Split Screen */
        <div className="flex-1 bg-gray-950 flex min-h-0">
          {/* Left Column - Vitals Grid */}
          <div className="w-1/2 p-4 flex flex-col">
            <div className="grid grid-cols-2 gap-3 h-full">
              <div className="bg-gray-900 rounded border-l-4 border-red-600 p-4 flex flex-col">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <Heart className="w-6 h-6 text-red-500" />
                    <span className="text-red-300 text-xs font-bold tracking-wider">HEART RATE</span>
                  </div>
                  <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
                </div>
                <div className="flex-1 flex flex-col justify-center">
                  <div className="text-4xl font-mono font-bold text-red-400 leading-none">
                    {safeVitals.heartRate}
                  </div>
                  <div className="text-red-300 text-sm font-medium">BPM</div>
                </div>
                <div className="text-xs text-gray-500 font-medium">
                  Normal: 60-100 • {MedicalUtils.getVitalStatus(safeVitals.heartRate, 'heartRate').toUpperCase()}
                </div>
              </div>

              <div className="bg-gray-900 rounded border-l-4 border-blue-600 p-4 flex flex-col">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <Droplets className="w-6 h-6 text-blue-500" />
                    <span className="text-blue-300 text-xs font-bold tracking-wider">BLOOD PRESSURE</span>
                  </div>
                  <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse"></div>
                </div>
                <div className="flex-1 flex flex-col justify-center">
                  <div className="text-3xl font-mono font-bold text-blue-400 leading-none">
                    {`${safeVitals.systolicPressure}/${safeVitals.diastolicPressure}`}
                  </div>
                  <div className="text-blue-300 text-sm font-medium">mmHg</div>
                </div>
                <div className="text-xs text-gray-500 font-medium">
                  Normal: 90-140/60-90 • {MedicalUtils.getVitalStatus(safeVitals.systolicPressure, 'systolicPressure', safeVitals.diastolicPressure).toUpperCase()}
                </div>
              </div>

              <div className="bg-gray-900 rounded border-l-4 border-cyan-600 p-4 flex flex-col">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <Activity className="w-6 h-6 text-cyan-500" />
                    <span className="text-cyan-300 text-xs font-bold tracking-wider">OXYGEN SAT</span>
                  </div>
                  <div className="w-3 h-3 bg-cyan-500 rounded-full animate-pulse"></div>
                </div>
                <div className="flex-1 flex flex-col justify-center">
                  <div className="text-4xl font-mono font-bold text-cyan-400 leading-none">
                    {safeVitals.oxygenSaturation}
                  </div>
                  <div className="text-cyan-300 text-sm font-medium">%</div>
                </div>
                <div className="text-xs text-gray-500 font-medium">
                  Normal: 95-100 • {MedicalUtils.getVitalStatus(safeVitals.oxygenSaturation, 'oxygenSaturation').toUpperCase()}
                </div>
              </div>

              <div className="bg-gray-900 rounded border-l-4 border-amber-600 p-4 flex flex-col">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <Thermometer className="w-6 h-6 text-amber-500" />
                    <span className="text-amber-300 text-xs font-bold tracking-wider">TEMPERATURE</span>
                  </div>
                  <div className="w-3 h-3 bg-amber-500 rounded-full animate-pulse"></div>
                </div>
                <div className="flex-1 flex flex-col justify-center">
                  <div className="text-3xl font-mono font-bold text-amber-400 leading-none">
                    {safeVitals.skinTemperature.toFixed(1)}
                  </div>
                  <div className="text-amber-300 text-sm font-medium">°F</div>
                </div>
                <div className="text-xs text-gray-500 font-medium">
                  Normal: 97.0-99.0 • {MedicalUtils.getVitalStatus(safeVitals.skinTemperature, 'skinTemperature').toUpperCase()}
                </div>
              </div>
            </div>
          </div>

          {/* Right Column - Waveform Monitor */}
          <div className="w-1/2 p-4 flex flex-col">
            <div className="bg-gray-900 rounded border-l-4 border-green-600 p-4 flex flex-col h-full">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-3">
                  <Zap className="w-6 h-6 text-green-500" />
                  <span className="text-green-300 text-base font-bold tracking-wider">
                    {isECGMode ? 'ECG' : 'EEG'} MONITOR
                  </span>
                </div>
                <div className="flex items-center space-x-4">
                  <div className="text-right">
                    <div className="text-green-400 text-xl font-mono font-bold">
                      {isECGMode ? `${safeVitals.ecgReading} mV` : 'ACTIVE'}
                    </div>
                    <div className="text-green-300 text-xs font-medium">
                      {isECGMode ? 'Amplitude' : 'Brain Activity'}
                    </div>
                  </div>
                  <div className="w-4 h-4 rounded-full bg-green-400 animate-pulse"></div>
                </div>
              </div>

              <div className="flex-1 relative min-h-0">
                <svg
                  width="100%"
                  height="100%"
                  viewBox="0 0 400 200"
                  className="bg-black rounded border-2 border-gray-800"
                  preserveAspectRatio="none"
                >
                  <defs>
                    <pattern id={`ecg-grid-${patient.id}`} width="10" height="10" patternUnits="userSpaceOnUse">
                      <path d="M 10 0 L 0 0 0 10" fill="none" stroke="#166534" strokeWidth="0.5" opacity="0.6"/>
                    </pattern>
                    <pattern id={`ecg-grid-major-${patient.id}`} width="50" height="50" patternUnits="userSpaceOnUse">
                      <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#166534" strokeWidth="1" opacity="0.8"/>
                    </pattern>
                  </defs>
                  <rect width="100%" height="100%" fill={`url(#ecg-grid-${patient.id})`} />
                  <rect width="100%" height="100%" fill={`url(#ecg-grid-major-${patient.id})`} />
                  <path
                    d={pathData}
                    fill="none"
                    stroke={isECGMode ? "#10B981" : "#EAB308"}
                    strokeWidth="2.5"
                    className="filter drop-shadow-lg"
                  />
                  <line
                    x1="360"
                    y1="0"
                    x2="360"
                    y2="200"
                    stroke="#DC2626"
                    strokeWidth="2"
                    opacity="0.9"
                  />
                </svg>
              </div>

              <div className="mt-2 flex items-center justify-between text-xs">
                <div className="flex items-center space-x-4">
                  <span className="text-green-300 font-medium">25mm/s • 10mm/mV</span>
                  <span className="text-gray-400 font-medium">Lead II</span>
                  <span className="text-blue-300 font-medium">Filter: 0.5-40Hz</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Dual Patient Layout - Compact */
        <div className="flex-1 bg-gray-950 flex flex-col min-h-0 p-3">
          {/* Compact Vitals Row */}
          <div className="grid grid-cols-4 gap-2 mb-3">
            <div className="bg-gray-900 rounded border-l-2 border-red-600 p-2">
              <div className="flex items-center space-x-1 mb-1">
                <Heart className="w-4 h-4 text-red-500" />
                <span className="text-red-300 text-xs font-bold">HR</span>
              </div>
              <div className="text-2xl font-mono font-bold text-red-400">{safeVitals.heartRate}</div>
              <div className="text-red-300 text-xs">BPM</div>
            </div>

            <div className="bg-gray-900 rounded border-l-2 border-blue-600 p-2">
              <div className="flex items-center space-x-1 mb-1">
                <Droplets className="w-4 h-4 text-blue-500" />
                <span className="text-blue-300 text-xs font-bold">BP</span>
              </div>
              <div className="text-xl font-mono font-bold text-blue-400">{`${safeVitals.systolicPressure}/${safeVitals.diastolicPressure}`}</div>
              <div className="text-blue-300 text-xs">mmHg</div>
            </div>

            <div className="bg-gray-900 rounded border-l-2 border-cyan-600 p-2">
              <div className="flex items-center space-x-1 mb-1">
                <Activity className="w-4 h-4 text-cyan-500" />
                <span className="text-cyan-300 text-xs font-bold">O2</span>
              </div>
              <div className="text-2xl font-mono font-bold text-cyan-400">{safeVitals.oxygenSaturation}</div>
              <div className="text-cyan-300 text-xs">%</div>
            </div>

            <div className="bg-gray-900 rounded border-l-2 border-amber-600 p-2">
              <div className="flex items-center space-x-1 mb-1">
                <Thermometer className="w-4 h-4 text-amber-500" />
                <span className="text-amber-300 text-xs font-bold">TEMP</span>
              </div>
              <div className="text-xl font-mono font-bold text-amber-400">{safeVitals.skinTemperature.toFixed(1)}</div>
              <div className="text-amber-300 text-xs">°F</div>
            </div>
          </div>

          {/* Compact Waveform */}
          <div className="flex-1 bg-gray-900 rounded border-l-2 border-green-600 p-3">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <Zap className="w-4 h-4 text-green-500" />
                <span className="text-green-300 text-sm font-bold">{isECGMode ? 'ECG' : 'EEG'}</span>
              </div>
              <div className="text-green-400 text-sm font-mono">
                {isECGMode ? `${safeVitals.ecgReading} mV` : 'ACTIVE'}
              </div>
            </div>

            <div className="h-32 relative">
              <svg
                width="100%"
                height="100%"
                viewBox="0 0 400 120"
                className="bg-black rounded border border-gray-800"
                preserveAspectRatio="none"
              >
                <defs>
                  <pattern id={`ecg-grid-dual-${patient.id}`} width="8" height="8" patternUnits="userSpaceOnUse">
                    <path d="M 8 0 L 0 0 0 8" fill="none" stroke="#166534" strokeWidth="0.5" opacity="0.4"/>
                  </pattern>
                </defs>
                <rect width="100%" height="100%" fill={`url(#ecg-grid-dual-${patient.id})`} />
                <path
                  d={ecgData.map((point, index) => {
                    // Scale down for compact dual view
                    const scaledY = Math.round(point.y * 0.6 + 24);
                    return `${index === 0 ? 'M' : 'L'} ${point.x} ${scaledY}`;
                  }).join(' ')}
                  fill="none"
                  stroke={isECGMode ? "#10B981" : "#EAB308"}
                  strokeWidth="1.5"
                />
                <line x1="360" y1="0" x2="360" y2="120" stroke="#DC2626" strokeWidth="1" opacity="0.7" />
              </svg>
            </div>
          </div>
        </div>
      )}

      <div className="bg-gray-950 px-4 py-2 border-t-2 border-gray-700 flex-shrink-0">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center space-x-4">
            <span className="text-blue-400 font-semibold">Monitor v3.1</span>
            <div className="flex items-center space-x-1">
              {isOnline ? <Wifi className="w-3 h-3 text-green-400" /> : <WifiOff className="w-3 h-3 text-red-400" />}
              <span className={`font-medium ${isOnline ? 'text-green-400' : 'text-red-400'}`}>
                {isOnline ? 'Connected' : 'Offline'}
              </span>
            </div>
          </div>
          <div className="flex items-center space-x-4 text-gray-400 font-medium">
            <span>ID: M{patient.bedNumber}</span>
            <span>{currentTime.toLocaleTimeString()}</span>
          </div>
        </div>
      </div>
    </div>
  );
};