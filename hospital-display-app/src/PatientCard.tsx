// PatientCard.tsx - Fixed Complete File with Proper Scrolling

import React, { useState, useEffect } from 'react';
import { Heart, Activity, Thermometer, Droplets, AlertTriangle, Eye, CheckCircle, Zap, Brain, Wind, Waves } from 'lucide-react';
import { Patient, User } from './types';
import { getVitalStatus, getStatusColor, getVitalStatusColor, detectArrhythmia, detectSeizureActivity, assessFallRisk, formatTimeOnly } from './utils';
import auditService from './services/auditService';

interface PatientCardProps {
  patient: Patient;
  currentUser: User;
  onPatientClick: (patient: Patient) => void;
  onVitalClick: (patient: Patient, vitalType: string) => void;
  onAcknowledgeAlert: (patient: Patient, alertId: string) => void;
  onBedsideMode: (patient: Patient) => void;
  onToggleECGMode: (patient: Patient) => void;
}

export const PatientCard: React.FC<PatientCardProps> = ({
  patient,
  currentUser,
  onPatientClick,
  onVitalClick,
  onAcknowledgeAlert,
  onBedsideMode,
  onToggleECGMode
}) => {
  const [displayedAlerts, setDisplayedAlerts] = useState(patient.alerts);
  const [selectedLead, setSelectedLead] = useState<string>(patient.vitals.isECGMode ? 'II' : 'C3-C4');

  // Auto-hide acknowledged alerts after 3 seconds (reduced from 5 for faster disappear)
  useEffect(() => {
    const acknowledgedAlerts = patient.alerts.filter(alert => alert.isAcknowledged);
    if (acknowledgedAlerts.length > 0) {
      const timer = setTimeout(() => {
        setDisplayedAlerts(prev => prev.filter(alert => !alert.isAcknowledged));
      }, 3000); // Reduced timeout
      return () => clearTimeout(timer);
    }
  }, [patient.alerts]);

  // Update displayed alerts when patient alerts change
  useEffect(() => {
    setDisplayedAlerts(patient.alerts);
  }, [patient.alerts]);

  // Update selected lead when ECG/EEG mode changes
  useEffect(() => {
    setSelectedLead(patient.vitals.isECGMode ? 'II' : 'C3-C4');
  }, [patient.vitals.isECGMode]);

  // ECG/EEG waveform generation removed - now uses backend API
  const isECGMode: boolean = patient.vitals.isECGMode !== undefined ? patient.vitals.isECGMode : true;
  // TODO: Replace with backend API call for waveform data
  const pathData = "M 0 25 L 250 25"; // Flat line placeholder

  // Detect various conditions
  const arrhythmiaDetected = detectArrhythmia(patient.vitals.heartRate, patient.vitals.ecg);
  const seizureActivity = patient.vitals.eeg ? detectSeizureActivity(patient.vitals.eeg, patient.vitals.heartRate) : false;
  const fallRisk = assessFallRisk(patient.vitals.tremor || 0, patient.vitals.heartRate, patient.age);

  // Add fall risk alert to displayed alerts if high or medium risk
  const alertsWithFallRisk = [...displayedAlerts];
  if (fallRisk === 'high') {
    alertsWithFallRisk.push({
      id: `fall-risk-${patient.id}`,
      message: 'High fall risk detected',
      severity: 'high' as const,
      timestamp: new Date().toISOString(),
      isAcknowledged: false
    });
  } else if (fallRisk === 'medium') {
    alertsWithFallRisk.push({
      id: `fall-risk-${patient.id}`,
      message: 'Moderate fall risk',
      severity: 'medium' as const,
      timestamp: new Date().toISOString(),
      isAcknowledged: false
    });
  }

  // Get unacknowledged alerts from displayed alerts including fall risk
  const unacknowledgedAlerts = alertsWithFallRisk.filter(alert => !alert.isAcknowledged);
  const acknowledgedAlerts = alertsWithFallRisk.filter(alert => alert.isAcknowledged);

  const handleAcknowledgeClick = (e: React.MouseEvent, alertId: string) => {
    e.stopPropagation();
    onAcknowledgeAlert(patient, alertId);
    
    // Log alert acknowledgment
    auditService.logPatientInteraction(
      'acknowledgeAlert',
      patient.id,
      `acknowledged alert ${alertId}`,
      { alertId: alertId }
    );
  };

  // Helper function to get vital alert status
  const getVitalAlertStatus = (vitalKey: string) => {
    // Check if there are any unacknowledged alerts related to this vital
    const vitalAlerts = unacknowledgedAlerts.filter(alert => {
      const message = alert.message.toLowerCase();
      return (
        (vitalKey === 'heartRate' && (message.includes('heart') || message.includes('cardiac') || message.includes('hr'))) ||
        (vitalKey === 'oxygenSat' && (message.includes('oxygen') || message.includes('spo2') || message.includes('sat'))) ||
        (vitalKey === 'temperature' && (message.includes('temp') || message.includes('fever'))) ||
        (vitalKey === 'bloodPressure' && (message.includes('pressure') || message.includes('bp') || message.includes('hyper') || message.includes('hypo'))) ||
        (vitalKey === 'respiratoryRate' && (message.includes('respiratory') || message.includes('breathing') || message.includes('rr'))) ||
        (vitalKey === 'bioimpedance' && message.includes('bioimpedance')) ||
        (vitalKey === 'tremor' && message.includes('tremor'))
      );
    });

    if (vitalAlerts.length === 0) return 'normal';
    
    const hasCritical = vitalAlerts.some(alert => alert.severity === 'critical');
    const hasHigh = vitalAlerts.some(alert => alert.severity === 'high');
    const hasMedium = vitalAlerts.some(alert => alert.severity === 'medium');
    
    if (hasCritical) return 'critical';
    if (hasHigh) return 'high';
    if (hasMedium) return 'medium';
    return 'low';
  };

  // All vitals in compact format - neutral colors by default
  const allVitals = [
    {
      key: 'heartRate',
      icon: Heart,
      label: 'HR',
      value: patient.vitals.heartRate,
      unit: '',
      alertStatus: getVitalAlertStatus('heartRate')
    },
    {
      key: 'oxygenSat',
      icon: Activity,
      label: 'SpO2',
      value: patient.vitals.oxygenSat,
      unit: '%',
      alertStatus: getVitalAlertStatus('oxygenSat')
    },
    {
      key: 'temperature',
      icon: Thermometer,
      label: 'Temp',
      value: patient.vitals.temperature.toFixed(1),
      unit: '°F',
      alertStatus: getVitalAlertStatus('temperature')
    },
    {
      key: 'bloodPressure',
      icon: Droplets,
      label: 'BP',
      value: patient.vitals.bloodPressure,
      unit: '',
      alertStatus: getVitalAlertStatus('bloodPressure')
    },
    {
      key: 'respiratoryRate',
      icon: Wind,
      label: 'RR',
      value: patient.vitals.respiratoryRate || 16,
      unit: '/min',
      alertStatus: getVitalAlertStatus('respiratoryRate')
    },
    {
      key: 'bioimpedance',
      icon: Waves,
      label: 'BioZ',
      value: patient.vitals.bioimpedance || 500,
      unit: 'Ω',
      alertStatus: getVitalAlertStatus('bioimpedance')
    },
    {
      key: 'tremor',
      icon: Activity,
      label: 'Tremor',
      value: (patient.vitals.tremor || 0).toFixed(1),
      unit: '/10',
      alertStatus: getVitalAlertStatus('tremor')
    }
  ];

  const getVitalColorClass = (alertStatus: string) => {
    // Professional medical colors based on alert severity
    switch (alertStatus) {
      case 'critical':
        return 'text-red-600 bg-red-50 border-l-4 border-red-500'; // Red for critical
      case 'high':
        return 'text-orange-600 bg-orange-50 border-l-4 border-orange-500'; // Orange for high
      case 'medium':
        return 'text-yellow-600 bg-yellow-50 border-l-4 border-yellow-500'; // Yellow for medium
      case 'low':
        return 'text-amber-600 bg-amber-50 border-l-4 border-amber-500'; // Amber for low
      case 'normal':
      default:
        return 'text-green-600 bg-green-50 border-l-4 border-green-500'; // Green for normal/healthy
    }
  };

  return (
    <div
      className={`bg-white rounded-xl shadow-md border-l-4 cursor-pointer hover:shadow-lg transition-shadow h-[330px] flex flex-col relative overflow-hidden ${
        unacknowledgedAlerts.some(alert => alert.severity === 'critical') || arrhythmiaDetected || seizureActivity
          ? 'border-red-600'
          : unacknowledgedAlerts.some(alert => alert.severity === 'high' || alert.severity === 'medium')
          ? 'border-orange-500'
          : unacknowledgedAlerts.length > 0
          ? 'border-yellow-500'
          : 'border-green-600'
      }`}
      onClick={() => {
        onPatientClick(patient);
        auditService.logPatientInteraction(
          'viewDetails',
          patient.id,
          `opened patient detail view`,
          { source: 'patientCard' }
        );
      }}
    >
      {/* Permanent Status Bar - Color coded by alert severity */}
      <div className={`absolute top-0 left-0 right-0 text-white text-xs px-2 py-1 rounded-t-xl flex items-center justify-between z-10 ${
        unacknowledgedAlerts.some(alert => alert.severity === 'critical') || arrhythmiaDetected || seizureActivity
          ? 'bg-red-600'
          : unacknowledgedAlerts.some(alert => alert.severity === 'high' || alert.severity === 'medium')
          ? 'bg-orange-500'
          : unacknowledgedAlerts.length > 0
          ? 'bg-yellow-500'
          : 'bg-green-600'
      }`}>
        <div className="flex items-center space-x-1">
          <AlertTriangle className={`w-3 h-3 ${
            unacknowledgedAlerts.length > 0 || arrhythmiaDetected || seizureActivity ? 'animate-pulse' : ''
          }`} />
          <span className="font-medium">
            {seizureActivity ? 'SEIZURE ACTIVITY' : 
             arrhythmiaDetected ? 'ARRHYTHMIA' : 
             unacknowledgedAlerts.length > 0 ? 'ALERTS PRESENT' : 'ALL NORMAL'}
          </span>
        </div>
        <div className="bg-black bg-opacity-20 px-1 rounded text-xs">
          {unacknowledgedAlerts.length + (arrhythmiaDetected ? 1 : 0) + (seizureActivity ? 1 : 0)}
        </div>
      </div>

      {/* Patient Header - Fixed 90px height */}
      <div className="px-3 pt-6 pb-2 border-b flex-shrink-0 h-[90px]">
        <div className="flex items-start justify-between h-full">
          <div className="flex-1">
            <h3 className="font-semibold text-base text-gray-900 truncate">{patient.name}</h3>
            <p className="text-xs text-gray-600">
              {patient.age}y, {patient.gender}
            </p>
            <p className="text-xs text-gray-600 truncate">
              {patient.department}
            </p>
          </div>

          {/* Compact Alert Area with Centered Ack Button */}
          <div className="flex items-center space-x-2">
            {/* Alert List - Compact */}
            {unacknowledgedAlerts.length > 0 && (
              <div className="flex flex-col space-y-1 max-w-[180px]">
                {/* Critical Alerts */}
                {unacknowledgedAlerts.filter(alert => alert.severity === 'critical').slice(0, 1).map((alert) => (
                  <div key={alert.id} className="text-xs text-red-700 bg-red-50 px-2 py-1 rounded truncate">
                    🚨 {alert.message}
                  </div>
                ))}
                {/* High Alerts */}
                {unacknowledgedAlerts.filter(alert => alert.severity === 'high').slice(0, 1).map((alert) => (
                  <div key={alert.id} className="text-xs text-orange-700 bg-orange-50 px-2 py-1 rounded truncate">
                    ⚠️ {alert.message}
                  </div>
                ))}
                {/* Medium/Low Alerts */}
                {unacknowledgedAlerts.filter(alert => alert.severity === 'medium' || alert.severity === 'low').slice(0, 1).map((alert) => (
                  <div key={alert.id} className="text-xs text-yellow-700 bg-yellow-50 px-2 py-1 rounded truncate">
                    ⚡ {alert.message}
                  </div>
                ))}
              </div>
            )}

            {/* Centered Square Acknowledge Button */}
            {unacknowledgedAlerts.length > 0 && (
              <div className="flex items-center h-full">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    unacknowledgedAlerts.forEach(alert => {
                      if (!alert.id.includes('fall-risk')) { // Don't acknowledge fall risk alerts as they're dynamic
                        handleAcknowledgeClick(e, alert.id);
                      }
                    });
                  }}
                  className="w-8 h-8 bg-green-600 hover:bg-green-700 text-white rounded flex items-center justify-center"
                  title="Acknowledge all alerts"
                >
                  <CheckCircle className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
          
          <div className="flex flex-col items-end space-y-1 ml-3">
            <div className="flex items-center space-x-2">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onBedsideMode(patient);
                  auditService.logPatientInteraction(
                    'enterBedsideMode',
                    patient.id,
                    `entered bedside mode`,
                    { mode: 'bedside' }
                  );
                }}
                className="p-1 bg-purple-100 hover:bg-purple-200 text-purple-700 rounded transition-colors"
                title="Enter Bedside Mode"
              >
                <Eye className="w-3 h-3" />
              </button>
              <div className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(patient.status)}`}>
                {patient.status.toUpperCase()}
              </div>
            </div>
            
            <div className="text-xs text-gray-600 text-right">
              Bed {patient.bedNumber} • {patient.ward}
            </div>
            <div className="text-xs text-gray-500">
              Updated: {formatTimeOnly(patient.vitals.lastSync)}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content - Tighter spacing for exact proportions */}
      <div className="px-3 py-1 flex-1 flex flex-col min-h-0 overflow-hidden space-y-1">
        {/* All Vital Signs in Infinite Circular Scroll - Fixed 80px height */}
        <div className="bg-gray-50 rounded-lg px-2 py-2 flex-shrink-0 h-[80px] flex items-center">
          <div className="vital-scroll w-full">
            <div 
              className="flex space-x-3 vitals-infinite-scroll"
              style={{
                minWidth: 'max-content',
                scrollSnapType: 'x mandatory'
              }}
            >
              {/* Duplicate vitals array for seamless infinite scroll */}
              {[...allVitals, ...allVitals, ...allVitals].map((vital, index) => (
                <div 
                  key={`${vital.key}-${index}`}
                  className={`flex flex-col items-center justify-center py-2 px-2 rounded hover:bg-blue-50 cursor-pointer transition-colors min-w-[65px] flex-shrink-0 h-full ${getVitalColorClass(vital.alertStatus)}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onVitalClick(patient, vital.key);
                    auditService.logPatientInteraction(
                      'viewVital',
                      patient.id,
                      `opened ${vital.label} vital chart`,
                      { vitalType: vital.key, vitalValue: vital.value }
                    );
                  }}
                >
                  <div className="flex items-center space-x-1 mb-1">
                    <vital.icon className="w-3 h-3" />
                    <span className="text-sm font-medium">{vital.label}</span>
                  </div>
                  <span className="text-sm font-bold">{vital.value}{vital.unit}</span>
                  <div className={`w-1.5 h-1.5 rounded-full mt-1 ${
                    (() => {
                      switch (vital.alertStatus) {
                        case 'critical':
                          return 'bg-red-500 animate-pulse';
                        case 'high':
                          return 'bg-orange-500 animate-pulse';
                        case 'medium':
                          return 'bg-yellow-500';
                        case 'low':
                          return 'bg-amber-500';
                        case 'normal':
                        default:
                          return 'bg-green-500'; // Green for normal/healthy
                      }
                    })()
                  }`}></div>
                </div>
              ))}
              {/* Duplicate ECG/EEG displays for infinite scroll */}
              {[...Array(3)].map((_, repeatIndex) => (
                <div 
                  key={`ecg-eeg-${repeatIndex}`}
                  className="flex flex-col items-center justify-center py-2 px-2 rounded hover:bg-blue-50 cursor-pointer transition-colors min-w-[65px] flex-shrink-0 h-full bg-green-50 text-green-600"
                  onClick={(e) => {
                    e.stopPropagation();
                    onVitalClick(patient, isECGMode ? 'eeg' : 'ecg');
                  }}
                >
                  <div className="flex items-center space-x-1 mb-1">
                    {isECGMode ? <Brain className="w-3 h-3" /> : <Heart className="w-3 h-3" />}
                    <span className="text-sm font-medium">{isECGMode ? 'EEG' : 'ECG'}</span>
                  </div>
                  <span className="text-sm font-bold">{isECGMode ? (patient.vitals.eeg || 45) : patient.vitals.ecg}</span>
                  <div className={`w-1.5 h-1.5 rounded-full mt-1 ${
                    isECGMode ? (seizureActivity ? 'bg-red-500 animate-pulse' : 'bg-green-500') :
                    (arrhythmiaDetected ? 'bg-yellow-500 animate-pulse' : 'bg-green-500')
                  }`}></div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ECG/EEG Waveform Display - Fixed 85px height to prevent overflow */}
        <div className="flex-shrink-0">
          <div 
            className="h-[85px] p-2 bg-gray-900 rounded-lg hover:bg-gray-800 transition-colors cursor-pointer flex flex-col"
            onClick={(e) => {
              e.stopPropagation();
              onVitalClick(patient, isECGMode ? 'ecg' : 'eeg');
            }}
          >
            {/* All ECG/EEG text consolidated at top with smaller font */}
            <div className="flex items-center justify-between mb-0.5 flex-shrink-0">
              <div className="flex items-center space-x-1.5">
                <div className={`w-1 h-1 rounded-full animate-pulse ${
                  isECGMode 
                    ? (arrhythmiaDetected ? 'bg-yellow-400' : 'bg-green-400')
                    : (seizureActivity ? 'bg-red-400' : 'bg-blue-400')
                }`}></div>
                <span className={`text-[10px] ${
                  isECGMode ? 'text-green-400' : 'text-blue-400'
                }`}>
                  {isECGMode ? 'ECG' : 'EEG'} {isECGMode ? patient.vitals.ecg : patient.vitals.eeg || 45}{isECGMode ? 'mV' : 'μV'}
                </span>
                <span className="text-green-300 text-[10px]">25mm/s</span>
                <select 
                  value={selectedLead}
                  onChange={(e) => {
                    e.stopPropagation();
                    setSelectedLead(e.target.value);
                  }}
                  onClick={(e) => e.stopPropagation()}
                  className="text-[9px] bg-gray-800 text-green-300 border border-gray-600 rounded px-1"
                >
                  {isECGMode ? (
                    <>
                      <option value="I">Lead I</option>
                      <option value="II">Lead II</option>
                      <option value="III">Lead III</option>
                      <option value="aVR">aVR</option>
                      <option value="aVL">aVL</option>
                      <option value="aVF">aVF</option>
                      <option value="V1">V1</option>
                      <option value="V2">V2</option>
                      <option value="V3">V3</option>
                      <option value="V4">V4</option>
                      <option value="V5">V5</option>
                      <option value="V6">V6</option>
                    </>
                  ) : (
                    <>
                      <option value="F3-F4">F3-F4</option>
                      <option value="C3-C4">C3-C4</option>
                      <option value="P3-P4">P3-P4</option>
                      <option value="O1-O2">O1-O2</option>
                      <option value="T3-T4">T3-T4</option>
                      <option value="T5-T6">T5-T6</option>
                      <option value="Fp1-Fp2">Fp1-Fp2</option>
                      <option value="F7-F8">F7-F8</option>
                    </>
                  )}
                </select>
                {isECGMode && arrhythmiaDetected && (
                  <span className="text-yellow-400 text-[10px]">⚠️</span>
                )}
                {!isECGMode && seizureActivity && (
                  <span className="text-red-400 text-[10px]">🚨</span>
                )}
              </div>
              <div className="flex items-center space-x-1.5">
                <span className="text-[10px] text-gray-400">{patient.vitals.heartRate} BPM</span>
                {/* Compact ECG/EEG Toggle */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleECGMode(patient);
                  }}
                  className={`px-1.5 py-0.5 rounded text-[10px] transition-colors ${
                    isECGMode 
                      ? 'bg-green-600 text-white hover:bg-green-700' 
                      : 'bg-blue-600 text-white hover:bg-blue-700'
                  }`}
                  title={`Switch to ${isECGMode ? 'EEG' : 'ECG'} mode`}
                >
                  {isECGMode ? 'EEG' : 'ECG'}
                </button>
              </div>
            </div>
            
            {/* Pure Waveform Area - No bottom text */}
            <div className="flex-1 min-h-0 relative">
              <svg 
                width="100%" 
                height="100%" 
                viewBox="0 0 250 60"
                className="bg-gray-900 w-full h-full"
                preserveAspectRatio="none"
              >
                <defs>
                  <pattern id={`grid-${patient.id}`} width="8" height="8" patternUnits="userSpaceOnUse">
                    <path d="M 8 0 L 0 0 0 8" fill="none" stroke="#374151" strokeWidth="0.5" opacity="0.3"/>
                  </pattern>
                </defs>
                <rect width="100%" height="100%" fill={`url(#grid-${patient.id})`} />
                
                <path
                  d={pathData}
                  fill="none"
                  stroke={
                    isECGMode 
                      ? (arrhythmiaDetected ? "#FBBF24" : "#10B981")
                      : (seizureActivity ? "#EF4444" : "#3B82F6")
                  }
                  strokeWidth="2"
                  className="drop-shadow-sm"
                />
              </svg>
              
              <div className="absolute inset-0 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity bg-black bg-opacity-20 rounded">
                <span className="text-white text-xs">
                  Click for {isECGMode ? 'ECG' : 'EEG'} viewer
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};