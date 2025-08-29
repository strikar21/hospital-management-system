// BedsideMode.tsx - Bedside Monitor

import React, { useState, useEffect } from 'react';
import { X, Settings, Monitor, Wifi, WifiOff, AlertTriangle, Heart, Activity, Thermometer, Droplets, Zap, CreditCard, Volume2, VolumeX } from 'lucide-react';
import { Patient, User, AppSettings } from './types';
import { getVitalStatus, detectArrhythmia } from './utils';
import { HospitalAPI } from './api';

interface BedsideModeProps {
  patients: Patient[];
  displayCount: 1 | 2;
  onClose: () => void;
  onDisplayCountChange: (count: 1 | 2) => void;
  onNFCTap?: (user: User) => void;
  settings?: AppSettings;
}

export const BedsideMode: React.FC<BedsideModeProps> = ({
  patients,
  displayCount,
  onClose,
  onDisplayCountChange,
  onNFCTap,
  settings
}) => {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [showSettings, setShowSettings] = useState(false);
  const [showNFCLogin, setShowNFCLogin] = useState(false);
  const [nfcScanning, setNfcScanning] = useState(false);
  const [audioAlarmsEnabled, setAudioAlarmsEnabled] = useState<boolean>(settings?.audioAlarms || true);
  const [isECGMode, setIsECGMode] = useState<boolean>(true);
  const [currentPatientIndex, setCurrentPatientIndex] = useState<number>(0);

  // Reset patient index if it's out of bounds
  useEffect(() => {
    if (currentPatientIndex >= patients.length) {
      setCurrentPatientIndex(0);
    }
  }, [patients.length, currentPatientIndex]);

  useEffect(() => {
    const interval = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

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

  // NFC scanning removed - backend-only mode
  const handleNFCScan = async () => {
    alert('NFC scanning requires backend integration. Please use credential login instead.');
    setShowNFCLogin(false);
  };

  const PatientMonitor = ({ patient, position }: { patient: Patient, position: 'left' | 'right' | 'single' }) => {
    const [ecgData, setEcgData] = useState<{x: number, y: number}[]>([]);
    
    useEffect(() => {
      const generateData = () => {
        // TODO: Replace with backend API call for waveform data
        // Placeholder: flat line data
        const processedData = Array.from({length: 400}, (_, x) => ({
          x,
          y: 25 // Flat line placeholder
        }));
        
        setEcgData(processedData);
      };
      
      generateData();
      const interval = setInterval(generateData, 1000);
      return () => clearInterval(interval);
    }, [patient.vitals.heartRate, patient.vitals.ecg, patient.vitals.eeg, isECGMode]);

    const pathData = ecgData.map((point, index) => 
      `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`
    ).join(' ');

    const unacknowledgedAlerts = patient.alerts.filter(alert => !alert.isAcknowledged);
    const hasCriticalAlert = unacknowledgedAlerts.some(alert => alert.severity === 'critical');
    const arrhythmiaDetected = detectArrhythmia(patient.vitals.heartRate, patient.vitals.ecg);

    const getVitalStatusColor = (value: number, type: string) => {
      const status = getVitalStatus(value, type as any);
      return status === 'critical' ? '#EF4444' : status === 'warning' ? '#F59E0B' : '#10B981';
    };

    return (
      <div className={`h-full ${displayCount === 2 ? 'w-1/2' : 'w-full'} bg-black text-white flex flex-col border-r border-gray-800`}>
        {(hasCriticalAlert || arrhythmiaDetected) && (
          <div className="bg-red-900 text-red-100 py-2 px-4 flex items-center justify-center border-b-2 border-red-600">
            <AlertTriangle className="w-5 h-5 mr-2 animate-pulse" />
            <span className={`${displayCount === 2 ? 'text-sm' : 'text-xl'} font-bold tracking-wide`}>
              {arrhythmiaDetected ? '⚠ ARRHYTHMIA' : '⚠ CRITICAL'}
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
                      {patient.vitals.heartRate}
                    </div>
                    <div className="text-red-300 text-sm font-medium">BPM</div>
                  </div>
                  <div className="text-xs text-gray-500 font-medium">
                    Normal: 60-100 • {getVitalStatus(patient.vitals.heartRate, 'heartRate').toUpperCase()}
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
                      {patient.vitals.bloodPressure}
                    </div>
                    <div className="text-blue-300 text-sm font-medium">mmHg</div>
                  </div>
                  <div className="text-xs text-gray-500 font-medium">
                    Normal: 90-140/60-90 • {getVitalStatus(patient.vitals.bloodPressureValue, 'bloodPressure').toUpperCase()}
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
                      {patient.vitals.oxygenSat}
                    </div>
                    <div className="text-cyan-300 text-sm font-medium">%</div>
                  </div>
                  <div className="text-xs text-gray-500 font-medium">
                    Normal: 95-100 • {getVitalStatus(patient.vitals.oxygenSat, 'oxygenSat').toUpperCase()}
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
                      {patient.vitals.temperature.toFixed(1)}
                    </div>
                    <div className="text-amber-300 text-sm font-medium">°F</div>
                  </div>
                  <div className="text-xs text-gray-500 font-medium">
                    Normal: 97.0-99.0 • {getVitalStatus(patient.vitals.temperature, 'temperature').toUpperCase()}
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
                    {arrhythmiaDetected && (
                      <span className="bg-yellow-800 text-yellow-100 px-3 py-1 rounded border border-yellow-500 text-xs font-bold">
                        ⚠ ARRHYTHMIA
                      </span>
                    )}
                  </div>
                  <div className="flex items-center space-x-4">
                    <div className="text-right">
                      <div className="text-green-400 text-xl font-mono font-bold">
                        {isECGMode ? `${patient.vitals.ecg} mV` : 'ACTIVE'}
                      </div>
                      <div className="text-green-300 text-xs font-medium">
                        {isECGMode ? 'Amplitude' : 'Brain Activity'}
                      </div>
                    </div>
                    <div className={`w-4 h-4 rounded-full ${arrhythmiaDetected ? 'bg-yellow-400' : 'bg-green-400'} animate-pulse`}></div>
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
                      stroke={arrhythmiaDetected ? "#F59E0B" : isECGMode ? "#10B981" : "#EAB308"}
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
                  {arrhythmiaDetected && (
                    <span className="text-yellow-400 font-bold animate-pulse">
                      ⚠ IRREGULAR RHYTHM
                    </span>
                  )}
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
                <div className="text-2xl font-mono font-bold text-red-400">{patient.vitals.heartRate}</div>
                <div className="text-red-300 text-xs">BPM</div>
              </div>

              <div className="bg-gray-900 rounded border-l-2 border-blue-600 p-2">
                <div className="flex items-center space-x-1 mb-1">
                  <Droplets className="w-4 h-4 text-blue-500" />
                  <span className="text-blue-300 text-xs font-bold">BP</span>
                </div>
                <div className="text-xl font-mono font-bold text-blue-400">{patient.vitals.bloodPressure}</div>
                <div className="text-blue-300 text-xs">mmHg</div>
              </div>

              <div className="bg-gray-900 rounded border-l-2 border-cyan-600 p-2">
                <div className="flex items-center space-x-1 mb-1">
                  <Activity className="w-4 h-4 text-cyan-500" />
                  <span className="text-cyan-300 text-xs font-bold">O2</span>
                </div>
                <div className="text-2xl font-mono font-bold text-cyan-400">{patient.vitals.oxygenSat}</div>
                <div className="text-cyan-300 text-xs">%</div>
              </div>

              <div className="bg-gray-900 rounded border-l-2 border-amber-600 p-2">
                <div className="flex items-center space-x-1 mb-1">
                  <Thermometer className="w-4 h-4 text-amber-500" />
                  <span className="text-amber-300 text-xs font-bold">TEMP</span>
                </div>
                <div className="text-xl font-mono font-bold text-amber-400">{patient.vitals.temperature.toFixed(1)}</div>
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
                  {isECGMode ? `${patient.vitals.ecg} mV` : 'ACTIVE'}
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
                    stroke={arrhythmiaDetected ? "#F59E0B" : isECGMode ? "#10B981" : "#EAB308"}
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

  return (
    <div className="fixed inset-0 bg-black z-50 flex flex-col">
      <div className="bg-gray-950 px-6 py-4 flex items-center justify-between border-b-2 border-gray-700">
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-3">
            <Monitor className="w-6 h-6 text-blue-400" />
            <span className="text-white font-bold text-lg tracking-wide">ICU BEDSIDE MONITOR</span>
          </div>
          
          <div className="flex items-center space-x-2 bg-gray-800 rounded-lg p-2 border border-gray-600">
            <button
              onClick={() => setIsECGMode(true)}
              className={`flex items-center space-x-2 px-4 py-2 rounded transition-all duration-200 ${
                isECGMode ? 'bg-green-700 text-white border border-green-500' : 'text-gray-400 hover:text-white hover:bg-gray-700'
              }`}
            >
              <Activity className="w-4 h-4" />
              <span className="font-medium">ECG</span>
            </button>
            <button
              onClick={() => setIsECGMode(false)}
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
              onClick={() => {
                onDisplayCountChange(1);
                setCurrentPatientIndex(0);
              }}
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
                onClick={() => setCurrentPatientIndex((prev) => (prev - 1 + patients.length) % patients.length)}
                className="p-1 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors"
                title="Previous Patient"
              >
                ←
              </button>
              <span className="text-white font-medium min-w-[3rem] text-center">
                {currentPatientIndex + 1} / {patients.length}
              </span>
              <button
                onClick={() => setCurrentPatientIndex((prev) => (prev + 1) % patients.length)}
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
            onClick={() => setAudioAlarmsEnabled(!audioAlarmsEnabled)}
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
            onClick={() => setShowNFCLogin(true)}
            className="flex items-center space-x-2 p-3 text-blue-400 hover:text-white hover:bg-blue-900 rounded-lg border border-blue-500 transition-all duration-200"
            title="NFC Login"
          >
            <CreditCard className="w-5 h-5" />
            <span className="text-sm font-medium">NFC</span>
          </button>
          <button
            onClick={() => setShowSettings(!showSettings)}
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

      {/* NFC Login Modal - Uses API for scanning */}
      {showNFCLogin && (
        <div className="absolute inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 max-w-sm w-full mx-4">
            <div className="text-center">
              <CreditCard className="w-16 h-16 text-blue-400 mx-auto mb-4" />
              <h3 className="text-xl font-bold text-white mb-3">NFC Authentication</h3>
              <p className="text-gray-300 mb-6 text-sm">
                {nfcScanning ? 'Scanning for NFC card...' : 'Tap NFC card to login'}
              </p>
              {nfcScanning ? (
                <div className="flex items-center justify-center space-x-2 text-blue-400">
                  <div className="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
                  <span className="text-sm">Scanning...</span>
                </div>
              ) : (
                <div className="space-y-3">
                  <button
                    onClick={handleNFCScan}
                    className="w-full flex items-center justify-center space-x-2 py-3 px-4 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm"
                  >
                    <CreditCard className="w-5 h-5" />
                    <span>Scan NFC</span>
                  </button>
                  <button
                    onClick={() => setShowNFCLogin(false)}
                    className="w-full py-2 px-4 bg-gray-600 text-white rounded hover:bg-gray-700 text-sm"
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="flex-1 flex overflow-hidden">
        {displayCount === 1 ? (
          // Single patient mode
          patients[currentPatientIndex] ? (
            <PatientMonitor
              key={patients[currentPatientIndex].id}
              patient={patients[currentPatientIndex]}
              position="single"
            />
          ) : (
            <div className="flex-1 flex items-center justify-center bg-gray-950 text-gray-400">
              <div className="text-center">
                <Monitor className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p className="text-xl">No Patient Data Available</p>
              </div>
            </div>
          )
        ) : (
          // Dual patient mode - show two patients side by side
          patients.slice(0, 2).map((patient, index) => (
            <PatientMonitor
              key={patient.id}
              patient={patient}
              position={index === 0 ? 'left' : 'right'}
            />
          ))
        )}
      </div>

      {patients.some(p => 
        p.alerts.some(a => !a.isAcknowledged && a.severity === 'critical') || 
        detectArrhythmia(p.vitals.heartRate, p.vitals.ecg)
      ) && (
        <div className="bg-red-900 text-red-100 py-3 px-6 text-center border-t-2 border-red-600">
          <div className="flex items-center justify-center space-x-3">
            <AlertTriangle className="w-5 h-5 animate-pulse" />
            <span className="text-base font-bold tracking-wide">CRITICAL ALERTS REQUIRE IMMEDIATE ATTENTION</span>
            <AlertTriangle className="w-5 h-5 animate-pulse" />
          </div>
        </div>
      )}
    </div>
  );
};