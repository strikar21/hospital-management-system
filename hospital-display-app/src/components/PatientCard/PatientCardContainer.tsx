/**
 * PatientCardContainer - Main patient card container component (Refactored)
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade patient card with modular architecture
 */

import React, { useState, useMemo, useCallback } from 'react';
import { Heart, Activity, Thermometer, Droplets, Wind, Waves, TrendingUp, AlertTriangle, Watch } from 'lucide-react';
import { patient, user } from '../../types';
import { MedicalUtils } from '../../utils/medicalUtils';
import auditService from '../../services/auditService';
import { PatientVitalStrip } from './PatientVitalStrip';
import { PatientCardHeader } from './PatientCardHeader';
import { PatientCardAlerts } from './PatientCardAlerts';
import { PatientCardWaveform } from './PatientCardWaveform';
import { WatchDetailsModal } from '../WatchDetailsModal';
import { usePatientVitals } from '../../hooks/usePatientVitals';
import { useRealtimeAlerts } from '../../hooks/useRealtimeAlerts';

interface PatientCardContainerProps {
  patient: patient;
  currentUser: user;
  onPatientClick: (patient: patient) => void;
  onVitalClick: (patient: patient, vitalType: string) => void;
  onAcknowledgeAlert: (patient: patient, alertId: string) => void;
  onBedsideMode: (patient: patient) => void;
  onToggleECGMode: (patient: patient) => void;
}

export const PatientCardContainer: React.FC<PatientCardContainerProps> = React.memo(({
  patient,
  currentUser,
  onPatientClick,
  onVitalClick,
  onAcknowledgeAlert,
  onBedsideMode,
  onToggleECGMode
}) => {

  // DEBUG: Log what we're receiving
  // console.log(`🔍 [${patient.id.substring(0,8)}] patient.vitals from API:`, patient.vitals);

  // WebSocket real-time vitals subscription - initialize with API vitals for instant display
  const { vitals: realtimeVitals, isConnected: wsConnected } = usePatientVitals(patient.id, patient.vitals);

  // WebSocket real-time alerts subscription - initialize with API alerts
  const { alerts: realtimeAlerts } = useRealtimeAlerts(patient.id, patient.alerts || []);

  // console.log(`🔍 [${patient.id.substring(0,8)}] realtimeVitals from hook:`, realtimeVitals, 'wsConnected:', wsConnected);

  // Merge real-time vitals with patient prop vitals (WebSocket takes precedence)
  const currentVitals = useMemo(() => {
    if (realtimeVitals && wsConnected) {
      // console.log(`✅ [${patient.id.substring(0,8)}] Using WebSocket vitals`);
      return { ...patient.vitals, ...realtimeVitals };
    }
    // console.log(`⚠️ [${patient.id.substring(0,8)}] Falling back to patient.vitals:`, patient.vitals);
    return patient.vitals;
  }, [patient.vitals, realtimeVitals, wsConnected, patient.id]);

  // State management - use real-time alerts from WebSocket
  const [watchDetailsPatient, setWatchDetailsPatient] = useState<patient | null>(null);

  // Use real-time alerts from WebSocket hook (includes both API and WebSocket alerts)
  const displayedAlerts = realtimeAlerts;

  // ECG/EEG mode detection
  const isECGMode: boolean = currentVitals?.isEcgMode !== undefined ? currentVitals?.isEcgMode : true;

  // Medical calculations disabled - no mock alerts (backend generates all alerts)
  const arrhythmiaDetected = false;
  const seizureActivity = false;

  // Use alerts from backend only - no synthetic fall risk alerts
  const alertsWithFallRisk = useMemo(() => {
    return [...(displayedAlerts || [])];
  }, [displayedAlerts]);

  // Memoize unacknowledged alerts filtering
  const unacknowledgedAlerts = useMemo(() =>
    alertsWithFallRisk.filter(alert => !alert.isAcknowledged),
    [alertsWithFallRisk]
  );

  // Use only backend alerts - no synthetic medical alerts
  const allCombinedAlerts = useMemo(() => {
    // Sort backend alerts by severity: critical first, then high, medium, low
    return unacknowledgedAlerts.sort((a, b) => {
      const severityOrder: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1 };
      return (severityOrder[b.severity] || 0) - (severityOrder[a.severity] || 0);
    });
  }, [unacknowledgedAlerts]);


  // Memoize vital alert status calculation
  const getVitalAlertStatus = useCallback((vitalKey: string) => {
    let vitalStatus = 'normal';
    if (currentVitals) {
      switch (vitalKey) {
        case 'heartRate':
          vitalStatus = currentVitals.heartRate ? MedicalUtils.getVitalStatus(currentVitals.heartRate, 'heartRate') : 'normal';
          break;
        case 'oxygenSaturation':
          vitalStatus = currentVitals.oxygenSaturation ? MedicalUtils.getVitalStatus(currentVitals.oxygenSaturation, 'oxygenSaturation') : 'normal';
          break;
        case 'skinTemperature':
          vitalStatus = currentVitals.skinTemperature ? MedicalUtils.getVitalStatus(currentVitals.skinTemperature, 'skinTemperature') : 'normal';
          break;
        case 'systolicPressure':
          vitalStatus = currentVitals.systolicPressure ? MedicalUtils.getVitalStatus(currentVitals.systolicPressure, 'systolicPressure', currentVitals.diastolicPressure) : 'normal';
          break;
        case 'respiratoryRate':
          vitalStatus = currentVitals.respiratoryRate ? MedicalUtils.getVitalStatus(currentVitals.respiratoryRate, 'respiratoryRate') : 'normal';
          break;
      }
    }

    const vitalAlerts = allCombinedAlerts.filter(alert => {
      const message = alert.message.toLowerCase();
      return (
        (vitalKey === 'heartRate' && (message.includes('heart') || message.includes('cardiac') || message.includes('hr'))) ||
        (vitalKey === 'oxygenSaturation' && (message.includes('oxygen') || message.includes('spo2') || message.includes('sat'))) ||
        (vitalKey === 'skinTemperature' && (message.includes('temp') || message.includes('fever'))) ||
        (vitalKey === 'systolicPressure' && (message.includes('pressure') || message.includes('bp') || message.includes('hyper') || message.includes('hypo'))) ||
        (vitalKey === 'respiratoryRate' && (message.includes('respiratory') || message.includes('breathing') || message.includes('rr'))) ||
        (vitalKey === 'bioimpedance' && message.includes('bioimpedance')) ||
        (vitalKey === 'tremor' && message.includes('tremor'))
      );
    });

    if (vitalAlerts.some(alert => alert.severity === 'critical')) return 'critical';
    if (vitalAlerts.some(alert => alert.severity === 'high')) return 'critical';
    if (vitalAlerts.some(alert => alert.severity === 'medium')) return 'warning';
    if (vitalAlerts.some(alert => alert.severity === 'low')) return 'warning';
    return vitalStatus;
  }, [currentVitals, allCombinedAlerts]);

  // Memoize watch assignment status
  const hasWatchAssigned = useMemo(() => patient.assignedDeviceId, [patient.assignedDeviceId]);

  // Watch details modal handler
  const handleViewWatchDetails = useCallback((patient: patient) => {
    setWatchDetailsPatient(patient);
  }, []);

  // Create updated patient object with real-time vitals for child components
  const patientWithCurrentVitals = useMemo(() => ({
    ...patient,
    vitals: currentVitals
  }), [patient, currentVitals]);

  // Memoize all vitals calculation - expensive operation with alert status computation
  const allVitals = useMemo(() => [
    {
      key: 'heartRate',
      icon: Heart,
      label: 'HR',
      value: hasWatchAssigned ? (currentVitals?.heartRate ?? '--') : '--',
      unit: hasWatchAssigned && currentVitals?.heartRate ? 'BPM' : '',
      alertStatus: hasWatchAssigned ? getVitalAlertStatus('heartRate') : 'normal'
    },
    {
      key: 'oxygenSaturation',
      icon: Activity,
      label: 'SpO2',
      value: hasWatchAssigned ? (currentVitals?.oxygenSaturation ?? '--') : '--',
      unit: hasWatchAssigned && currentVitals?.oxygenSaturation ? '%' : '',
      alertStatus: hasWatchAssigned ? getVitalAlertStatus('oxygenSaturation') : 'normal'
    },
    {
      key: 'skinTemperature',
      icon: Thermometer,
      label: 'Temp',
      value: hasWatchAssigned ? (currentVitals?.skinTemperature ? currentVitals.skinTemperature.toFixed(1) : '--') : '--',
      unit: hasWatchAssigned && currentVitals?.skinTemperature ? '°F' : '',
      alertStatus: hasWatchAssigned ? getVitalAlertStatus('skinTemperature') : 'normal'
    },
    {
      key: 'systolicPressure',
      icon: Droplets,
      label: 'BP',
      value: hasWatchAssigned ?
        (currentVitals?.systolicPressure && currentVitals?.diastolicPressure ?
          `${currentVitals.systolicPressure}/${currentVitals.diastolicPressure}` : '--/--') : '--/--',
      unit: hasWatchAssigned && currentVitals?.systolicPressure && currentVitals?.diastolicPressure ? 'mmHg' : '',
      alertStatus: hasWatchAssigned ? getVitalAlertStatus('systolicPressure') : 'normal'
    },
    {
      key: 'respiratoryRate',
      icon: Wind,
      label: 'RR',
      value: hasWatchAssigned ? (currentVitals?.respiratoryRate ?? '--') : '--',
      unit: hasWatchAssigned && currentVitals?.respiratoryRate ? '/min' : '',
      alertStatus: hasWatchAssigned ? getVitalAlertStatus('respiratoryRate') : 'normal'
    },
    {
      key: 'bioimpedance',
      icon: Waves,
      label: 'BioZ',
      value: hasWatchAssigned ? (currentVitals?.bioimpedance ?? '--') : '--',
      unit: hasWatchAssigned && currentVitals?.bioimpedance ? 'Ω' : '',
      alertStatus: hasWatchAssigned ? getVitalAlertStatus('bioimpedance') : 'normal'
    },
    {
      key: 'tremor',
      icon: Activity,
      label: 'Tremor',
      value: hasWatchAssigned ? (currentVitals?.tremor ? currentVitals.tremor.toFixed(1) : '--') : '--',
      unit: hasWatchAssigned && currentVitals?.tremor ? '/10' : '',
      alertStatus: hasWatchAssigned ? getVitalAlertStatus('tremor') : 'normal'
    },
    {
      key: 'imuFallRisk',
      icon: AlertTriangle,
      label: 'Fall Risk',
      value: hasWatchAssigned ? (currentVitals?.imuFallRisk ? currentVitals.imuFallRisk.toFixed(1) : '--') : '--',
      unit: hasWatchAssigned && currentVitals?.imuFallRisk ? '/10' : '',
      alertStatus: hasWatchAssigned && currentVitals?.imuFallRisk && currentVitals.imuFallRisk > 7 ? 'critical' : hasWatchAssigned && currentVitals?.imuFallRisk && currentVitals.imuFallRisk > 5 ? 'warning' : 'normal'
    },
    {
      key: 'perfusionIndex',
      icon: TrendingUp,
      label: 'Perfusion',
      value: hasWatchAssigned ? (currentVitals?.perfusionIndex ? currentVitals.perfusionIndex.toFixed(1) : '--') : '--',
      unit: hasWatchAssigned && currentVitals?.perfusionIndex ? '%' : '',
      alertStatus: hasWatchAssigned && currentVitals?.perfusionIndex && currentVitals.perfusionIndex < 0.5 ? 'critical' : hasWatchAssigned && currentVitals?.perfusionIndex && currentVitals.perfusionIndex < 2 ? 'warning' : 'normal'
    },
    {
      key: 'stepCount',
      icon: Activity,
      label: 'Steps',
      value: hasWatchAssigned ? (currentVitals?.stepCount ?? '--') : '--',
      unit: '',
      alertStatus: 'normal'
    },
    {
      key: 'watchWorn',
      icon: Watch,
      label: 'Watch',
      value: hasWatchAssigned ? (currentVitals?.watchWorn !== undefined ? (currentVitals.watchWorn ? 'ON' : 'OFF') : '--') : '--',
      unit: '',
      alertStatus: hasWatchAssigned && currentVitals?.watchWorn === false ? 'critical' : 'normal'
    }
  ], [hasWatchAssigned, currentVitals, getVitalAlertStatus]);

  return (
    <div
      className={`bg-white rounded-xl shadow-md border-l-4 cursor-pointer hover:shadow-lg transition-shadow h-[330px] flex flex-col relative overflow-hidden ${
        allCombinedAlerts.some(alert => alert.severity === 'critical')
          ? 'border-red-600'
          : allCombinedAlerts.some(alert => alert.severity === 'high' || alert.severity === 'medium')
          ? 'border-orange-500'
          : allCombinedAlerts.length > 0
          ? 'border-yellow-500'
          : 'border-green-600'
      }`}
      onClick={useCallback(() => {
        onPatientClick(patient);
        auditService.logPatientInteraction(
          'viewDetails',
          patient.id,
          `opened patient detail view`,
          { source: 'patientCard' }
        );
      }, [onPatientClick, patient])}
    >
      {/* Alert Status and Management */}
      <PatientCardAlerts
        patient={patientWithCurrentVitals}
        currentUser={currentUser}
        unacknowledgedAlerts={allCombinedAlerts}
        arrhythmiaDetected={arrhythmiaDetected}
        seizureActivity={seizureActivity}
        onAcknowledgeAlert={onAcknowledgeAlert}
      />

      {/* Patient Header and Info */}
      <PatientCardHeader
        patient={patientWithCurrentVitals}
        currentUser={currentUser}
        unacknowledgedAlerts={allCombinedAlerts}
        onAcknowledgeAlert={onAcknowledgeAlert}
        onViewWatchDetails={handleViewWatchDetails}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {/* Vital Signs Strip */}
        <PatientVitalStrip
          patient={patientWithCurrentVitals}
          currentUser={currentUser}
          allVitals={allVitals}
          isECGMode={isECGMode}
          arrhythmiaDetected={arrhythmiaDetected}
          seizureActivity={seizureActivity}
          onVitalClick={onVitalClick}
        />

        {/* ECG/EEG Waveform Display */}
        <PatientCardWaveform
          patient={patientWithCurrentVitals}
          currentUser={currentUser}
          isECGMode={isECGMode}
          arrhythmiaDetected={arrhythmiaDetected}
          seizureActivity={seizureActivity}
          onVitalClick={onVitalClick}
          onToggleECGMode={onToggleECGMode}
        />
      </div>

      {/* Watch Details Modal */}
      {watchDetailsPatient && (
        <WatchDetailsModal
          patient={watchDetailsPatient}
          onClose={() => setWatchDetailsPatient(null)}
        />
      )}
    </div>
  );
});

PatientCardContainer.displayName = 'PatientCardContainer';