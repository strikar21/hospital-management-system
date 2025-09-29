/**
 * PatientCardContainer - Main patient card container component (Refactored)
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade patient card with modular architecture
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Heart, Activity, Thermometer, Droplets, Wind, Waves } from 'lucide-react';
import { patient, user } from '../../types';
import { MedicalUtils } from '../../utils/medicalUtils';
import auditService from '../../services/auditService';
import { PatientVitalStrip } from './PatientVitalStrip';
import { PatientCardHeader } from './PatientCardHeader';
import { PatientCardAlerts } from './PatientCardAlerts';
import { PatientCardWaveform } from './PatientCardWaveform';

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

  // State management - no mock alerts, only real backend alerts
  const [displayedAlerts, setDisplayedAlerts] = useState<any[]>([]);

  // MEDICAL SAFETY: Never auto-hide any medical alerts - all alerts must be manually dismissed
  useEffect(() => {
    setDisplayedAlerts(patient.alerts || []);
  }, [patient.alerts]);

  // ECG/EEG mode detection
  const isECGMode: boolean = patient.vitals?.isEcgMode !== undefined ? patient.vitals?.isEcgMode : true;

  // Medical calculations disabled - no mock alerts
  const arrhythmiaDetected = false;
  const seizureActivity = false;
  const fallRisk = 'low' as const;

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
    if (patient.vitals) {
      switch (vitalKey) {
        case 'heartRate':
          vitalStatus = patient.vitals.heartRate ? MedicalUtils.getVitalStatus(patient.vitals.heartRate, 'heartRate') : 'normal';
          break;
        case 'oxygenSaturation':
          vitalStatus = patient.vitals.oxygenSaturation ? MedicalUtils.getVitalStatus(patient.vitals.oxygenSaturation, 'oxygenSaturation') : 'normal';
          break;
        case 'skinTemperature':
          vitalStatus = patient.vitals.skinTemperature ? MedicalUtils.getVitalStatus(patient.vitals.skinTemperature, 'skinTemperature') : 'normal';
          break;
        case 'systolicPressure':
          vitalStatus = patient.vitals.systolicPressure ? MedicalUtils.getVitalStatus(patient.vitals.systolicPressure, 'systolicPressure', patient.vitals.diastolicPressure) : 'normal';
          break;
        case 'respiratoryRate':
          vitalStatus = patient.vitals.respiratoryRate ? MedicalUtils.getVitalStatus(patient.vitals.respiratoryRate, 'respiratoryRate') : 'normal';
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
        (vitalKey === 'bioelectricalImpedance' && message.includes('bioimpedance')) ||
        (vitalKey === 'tremorIntensity' && message.includes('tremorIntensity'))
      );
    });

    if (vitalAlerts.some(alert => alert.severity === 'critical')) return 'critical';
    if (vitalAlerts.some(alert => alert.severity === 'high')) return 'critical';
    if (vitalAlerts.some(alert => alert.severity === 'medium')) return 'warning';
    if (vitalAlerts.some(alert => alert.severity === 'low')) return 'warning';
    return vitalStatus;
  }, [patient.vitals, allCombinedAlerts]);

  // Memoize watch assignment status
  const hasWatchAssigned = useMemo(() => patient.assignedDeviceId, [patient.assignedDeviceId]);

  // Memoize all vitals calculation - expensive operation with alert status computation
  const allVitals = useMemo(() => [
    {
      key: 'heartRate',
      icon: Heart,
      label: 'HR',
      value: hasWatchAssigned ? (patient.vitals?.heartRate || '--') : '--',
      unit: hasWatchAssigned && patient.vitals?.heartRate ? 'BPM' : '',
      alertStatus: hasWatchAssigned ? getVitalAlertStatus('heartRate') : 'normal'
    },
    {
      key: 'oxygenSaturation',
      icon: Activity,
      label: 'SpO2',
      value: hasWatchAssigned ? (patient.vitals?.oxygenSaturation || '--') : '--',
      unit: hasWatchAssigned && patient.vitals?.oxygenSaturation ? '%' : '',
      alertStatus: hasWatchAssigned ? getVitalAlertStatus('oxygenSaturation') : 'normal'
    },
    {
      key: 'skinTemperature',
      icon: Thermometer,
      label: 'Temp',
      value: hasWatchAssigned ? (patient.vitals?.skinTemperature ? patient.vitals.skinTemperature.toFixed(1) : '--') : '--',
      unit: hasWatchAssigned && patient.vitals?.skinTemperature ? '°F' : '',
      alertStatus: hasWatchAssigned ? getVitalAlertStatus('skinTemperature') : 'normal'
    },
    {
      key: 'systolicPressure',
      icon: Droplets,
      label: 'BP',
      value: hasWatchAssigned ?
        (patient.vitals?.systolicPressure && patient.vitals?.diastolicPressure ?
          `${patient.vitals.systolicPressure}/${patient.vitals.diastolicPressure}` : '--/--') : '--/--',
      unit: hasWatchAssigned && patient.vitals?.systolicPressure && patient.vitals?.diastolicPressure ? 'mmHg' : '',
      alertStatus: hasWatchAssigned ? getVitalAlertStatus('systolicPressure') : 'normal'
    },
    {
      key: 'respiratoryRate',
      icon: Wind,
      label: 'RR',
      value: hasWatchAssigned ? (patient.vitals?.respiratoryRate || '--') : '--',
      unit: hasWatchAssigned && patient.vitals?.respiratoryRate ? '/min' : '',
      alertStatus: hasWatchAssigned ? getVitalAlertStatus('respiratoryRate') : 'normal'
    },
    {
      key: 'bioelectricalImpedance',
      icon: Waves,
      label: 'BioZ',
      value: hasWatchAssigned ? (patient.vitals?.bioelectricalImpedance || '--') : '--',
      unit: hasWatchAssigned && patient.vitals?.bioelectricalImpedance ? 'Ω' : '',
      alertStatus: hasWatchAssigned ? getVitalAlertStatus('bioelectricalImpedance') : 'normal'
    },
    {
      key: 'tremorIntensity',
      icon: Activity,
      label: 'Tremor',
      value: hasWatchAssigned ? (patient.vitals?.tremorIntensity ? patient.vitals.tremorIntensity.toFixed(1) : '--') : '--',
      unit: hasWatchAssigned && patient.vitals?.tremorIntensity ? '/10' : '',
      alertStatus: hasWatchAssigned ? getVitalAlertStatus('tremorIntensity') : 'normal'
    }
  ], [hasWatchAssigned, patient.vitals, getVitalAlertStatus]);

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
        patient={patient}
        currentUser={currentUser}
        unacknowledgedAlerts={allCombinedAlerts}
        arrhythmiaDetected={arrhythmiaDetected}
        seizureActivity={seizureActivity}
        onAcknowledgeAlert={onAcknowledgeAlert}
      />

      {/* Patient Header and Info */}
      <PatientCardHeader
        patient={patient}
        currentUser={currentUser}
        onBedsideMode={onBedsideMode}
        unacknowledgedAlerts={allCombinedAlerts}
        onAcknowledgeAlert={onAcknowledgeAlert}
      />

      {/* Main Content Area */}
      <div className="px-3 py-1 flex-1 flex flex-col min-h-0 overflow-hidden space-y-1">
        {/* Vital Signs Strip */}
        <PatientVitalStrip
          patient={patient}
          currentUser={currentUser}
          allVitals={allVitals}
          isECGMode={isECGMode}
          arrhythmiaDetected={arrhythmiaDetected}
          seizureActivity={seizureActivity}
          onVitalClick={onVitalClick}
        />

        {/* ECG/EEG Waveform Display */}
        <PatientCardWaveform
          patient={patient}
          currentUser={currentUser}
          isECGMode={isECGMode}
          arrhythmiaDetected={arrhythmiaDetected}
          seizureActivity={seizureActivity}
          onVitalClick={onVitalClick}
          onToggleECGMode={onToggleECGMode}
        />
      </div>
    </div>
  );
});

PatientCardContainer.displayName = 'PatientCardContainer';