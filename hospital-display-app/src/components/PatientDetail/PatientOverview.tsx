/**
 * PatientOverview - Patient detail overview component
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade patient overview with vitals display and trending
 */

import React, { useMemo } from 'react';
import {
  Heart, Activity, Thermometer, Droplets, Waves, AlertTriangle, TrendingUp, Watch
} from 'lucide-react';
import { patient } from '../../types';
import { getVitalStatusColor } from '../../utils';
import { MedicalUtils } from '../../utils/medicalUtils';
import ECGViewer from '../ECGViewer';
import { usePatientVitals } from '../../hooks/usePatientVitals';

interface PatientOverviewProps {
  patient: patient;
  onVitalClick: (patient: patient, vitalType: string) => void;
  onECGView?: (patient: patient) => void;
  onToggleECGMode?: (patient: patient) => void;
}

export const PatientOverview: React.FC<PatientOverviewProps> = ({
  patient,
  onVitalClick,
  onECGView,
  onToggleECGMode
}) => {
  // WebSocket real-time vitals subscription
  const { vitals: realtimeVitals, isConnected: wsConnected } = usePatientVitals(patient.id);

  // Merge real-time vitals with patient prop vitals (WebSocket takes precedence)
  const currentVitals = useMemo(() => {
    if (realtimeVitals && wsConnected) {
      return { ...patient.vitals, ...realtimeVitals };
    }
    return patient.vitals;
  }, [patient.vitals, realtimeVitals, wsConnected]);

  return (
    <div className="p-2 h-full flex flex-col space-y-2">
      {/* Compact Info - Two Lines */}
      <div className="bg-gray-50 rounded px-2 py-1 mb-1 flex-shrink-0 text-xs">
        {/* Line 1: Medical Info */}
        <div className="flex gap-4 mb-1">
          <span><span className="text-gray-500">Diagnosis:</span> {patient.diagnosis}</span>
          <span><span className="text-gray-500">Dept:</span> {patient.department}</span>
          <span><span className="text-gray-500">Doctor:</span> Dr. {patient.assignedDoctor}</span>
        </div>
        {/* Line 2: Watch Status */}
        {patient.assignedDeviceId && (
          <div className="flex gap-4">
            <span><span className="text-gray-500">Watch:</span> 📟 {patient.assignedDeviceId}</span>
            <span>
              <span className="text-gray-500">Status:</span>{' '}
              <span className={patient.deviceStatus === 'connected' ? 'text-green-600' : 'text-amber-600'}>
                {patient.deviceStatus === 'connected' ? '🟢 Connected' : '🟡 Disconnected'}
              </span>
            </span>
            <span>
              <span className="text-gray-500">Battery:</span>{' '}
              <span className={`font-medium ${
                (patient.deviceBatteryLevel || 0) <= 20 ? 'text-red-600' :
                (patient.deviceBatteryLevel || 0) <= 40 ? 'text-amber-600' :
                'text-green-600'
              }`}>🔋 {patient.deviceBatteryLevel || '--'}%</span>
            </span>
          </div>
        )}
      </div>

      {/* Core Vitals - Two Rows (5+6=11 cards) */}
      <div className="bg-gray-50 rounded-lg p-1 mb-1 flex-shrink-0">
        {/* Row 1: Primary Vitals (5 cards) */}
        <div className="grid grid-cols-5 gap-2 mb-1">
          <div
            className="bg-white rounded p-1 cursor-pointer hover:bg-blue-50 transition-colors border"
            onClick={() => onVitalClick(patient, 'heartRate')}
          >
            <p className="text-xs text-gray-600 mb-0.5 text-center font-medium">Heart Rate</p>
            <div className="flex items-center justify-between">
              <div className={`p-0.5 rounded ${getVitalStatusColor(MedicalUtils.getVitalStatus(currentVitals?.heartRate || 0, 'heartRate'))}`}>
                <Heart className="w-4 h-4" />
              </div>
              <div className="text-right">
                <span className="font-bold text-lg text-red-600">{currentVitals?.heartRate || '--'}</span>
                <span className="text-xs text-gray-500 ml-0.5">BPM</span>
              </div>
            </div>
          </div>

          <div
            className="bg-white rounded p-1 cursor-pointer hover:bg-blue-50 transition-colors border"
            onClick={() => onVitalClick(patient, 'systolicPressure')}
          >
            <p className="text-xs text-gray-600 mb-0.5 text-center font-medium">Blood Pressure</p>
            <div className="flex items-center justify-between">
              <div className={`p-0.5 rounded ${getVitalStatusColor(MedicalUtils.getVitalStatus(currentVitals?.systolicPressure || 0, 'systolicPressure', currentVitals?.diastolicPressure || 0))}`}>
                <Droplets className="w-4 h-4" />
              </div>
              <div className="text-right">
                <span className="font-bold text-lg text-purple-600">{currentVitals?.systolicPressure || '--'}/{currentVitals?.diastolicPressure || '--'}</span>
                <span className="text-xs text-gray-500 ml-0.5">mmHg</span>
              </div>
            </div>
          </div>

          <div
            className="bg-white rounded p-1 cursor-pointer hover:bg-blue-50 transition-colors border"
            onClick={() => onVitalClick(patient, 'oxygenSaturation')}
          >
            <p className="text-xs text-gray-600 mb-0.5 text-center font-medium">Oxygen Sat</p>
            <div className="flex items-center justify-between">
              <div className={`p-0.5 rounded ${getVitalStatusColor(MedicalUtils.getVitalStatus(currentVitals?.oxygenSaturation || 0, 'oxygenSaturation'))}`}>
                <Activity className="w-4 h-4" />
              </div>
              <div className="text-right">
                <span className="font-bold text-lg text-blue-600">{currentVitals?.oxygenSaturation || '--'}</span>
                <span className="text-xs text-gray-500 ml-0.5">%</span>
              </div>
            </div>
          </div>

          <div
            className="bg-white rounded p-1 cursor-pointer hover:bg-blue-50 transition-colors border"
            onClick={() => onVitalClick(patient, 'skinTemperature')}
          >
            <p className="text-xs text-gray-600 mb-0.5 text-center font-medium">Temperature</p>
            <div className="flex items-center justify-between">
              <div className={`p-0.5 rounded ${getVitalStatusColor(MedicalUtils.getVitalStatus(currentVitals?.skinTemperature || 0, 'skinTemperature'))}`}>
                <Thermometer className="w-4 h-4" />
              </div>
              <div className="text-right">
                <span className="font-bold text-lg text-orange-600">{currentVitals?.skinTemperature ? currentVitals.skinTemperature.toFixed(1) : '--'}</span>
                <span className="text-xs text-gray-500 ml-0.5">°F</span>
              </div>
            </div>
          </div>

          <div
            className="bg-white rounded p-1 cursor-pointer hover:bg-blue-50 transition-colors border"
            onClick={() => onVitalClick(patient, 'respiratoryRate')}
          >
            <p className="text-xs text-gray-600 mb-0.5 text-center font-medium">Respiratory Rate</p>
            <div className="flex items-center justify-between">
              <div className={`p-0.5 rounded ${getVitalStatusColor(MedicalUtils.getVitalStatus(currentVitals?.respiratoryRate || 0, 'respiratoryRate'))}`}>
                <Activity className="w-4 h-4" />
              </div>
              <div className="text-right">
                <span className="font-bold text-lg text-green-600">{currentVitals?.respiratoryRate || '--'}</span>
                <span className="text-xs text-gray-500 ml-0.5">/min</span>
              </div>
            </div>
          </div>
        </div>

        {/* Row 2: Advanced Vitals (6 cards) */}
        <div className="grid grid-cols-6 gap-2">
          <div
            className="bg-white rounded p-1 cursor-pointer hover:bg-blue-50 transition-colors border"
            onClick={() => onVitalClick(patient, 'imuFallRisk')}
          >
            <p className="text-xs text-gray-600 mb-0.5 text-center font-medium">Fall Risk</p>
            <div className="flex items-center justify-between">
              <div className={`p-0.5 rounded ${
                currentVitals?.imuFallRisk && currentVitals.imuFallRisk > 7 ? 'bg-red-100 text-red-600' :
                currentVitals?.imuFallRisk && currentVitals.imuFallRisk > 5 ? 'bg-orange-100 text-orange-600' :
                'bg-green-100 text-green-600'
              }`}>
                <AlertTriangle className="w-4 h-4" />
              </div>
              <div className="text-right">
                <span className="font-bold text-lg text-red-600">{currentVitals?.imuFallRisk ? currentVitals.imuFallRisk.toFixed(1) : '--'}</span>
                <span className="text-xs text-gray-500 ml-0.5">/10</span>
              </div>
            </div>
          </div>

          <div
            className="bg-white rounded p-1 cursor-pointer hover:bg-blue-50 transition-colors border"
            onClick={() => onVitalClick(patient, 'perfusionIndex')}
          >
            <p className="text-xs text-gray-600 mb-0.5 text-center font-medium">Perfusion</p>
            <div className="flex items-center justify-between">
              <div className={`p-0.5 rounded ${
                currentVitals?.perfusionIndex && currentVitals.perfusionIndex < 0.5 ? 'bg-red-100 text-red-600' :
                currentVitals?.perfusionIndex && currentVitals.perfusionIndex < 2 ? 'bg-orange-100 text-orange-600' :
                'bg-green-100 text-green-600'
              }`}>
                <TrendingUp className="w-4 h-4" />
              </div>
              <div className="text-right">
                <span className="font-bold text-lg text-teal-600">{currentVitals?.perfusionIndex ? currentVitals.perfusionIndex.toFixed(1) : '--'}</span>
                <span className="text-xs text-gray-500 ml-0.5">%</span>
              </div>
            </div>
          </div>

          <div
            className="bg-white rounded p-1 cursor-pointer hover:bg-blue-50 transition-colors border"
            onClick={() => onVitalClick(patient, 'bioimpedance')}
          >
            <p className="text-xs text-gray-600 mb-0.5 text-center font-medium">Bioimpedance</p>
            <div className="flex items-center justify-between">
              <div className={`p-0.5 rounded ${getVitalStatusColor(MedicalUtils.getVitalStatus(currentVitals?.bioimpedance || 0, 'bioimpedance'))}`}>
                <Waves className="w-4 h-4" />
              </div>
              <div className="text-right">
                <span className="font-bold text-lg text-cyan-600">{currentVitals?.bioimpedance || '--'}</span>
                <span className="text-xs text-gray-500 ml-0.5">Ω</span>
              </div>
            </div>
          </div>

          <div
            className="bg-white rounded p-1 cursor-pointer hover:bg-blue-50 transition-colors border"
            onClick={() => onVitalClick(patient, 'tremor')}
          >
            <p className="text-xs text-gray-600 mb-0.5 text-center font-medium">Tremor</p>
            <div className="flex items-center justify-between">
              <div className={`p-0.5 rounded ${getVitalStatusColor(MedicalUtils.getVitalStatus(currentVitals?.tremor || 0, 'tremor'))}`}>
                <Activity className="w-4 h-4" />
              </div>
              <div className="text-right">
                <span className="font-bold text-lg text-pink-600">{currentVitals?.tremor ? currentVitals.tremor.toFixed(1) : '--'}</span>
                <span className="text-xs text-gray-500 ml-0.5">/10</span>
              </div>
            </div>
          </div>

          <div
            className="bg-white rounded p-1 cursor-pointer hover:bg-blue-50 transition-colors border"
            onClick={() => onVitalClick(patient, 'stepCount')}
          >
            <p className="text-xs text-gray-600 mb-0.5 text-center font-medium">Steps</p>
            <div className="flex items-center justify-between">
              <div className="p-0.5 rounded bg-green-100 text-green-600">
                <Activity className="w-4 h-4" />
              </div>
              <div className="text-right">
                <span className="font-bold text-lg text-green-600">{currentVitals?.stepCount || '--'}</span>
                <span className="text-xs text-gray-500 ml-0.5">steps</span>
              </div>
            </div>
          </div>

          <div
            className="bg-white rounded p-1 cursor-pointer hover:bg-blue-50 transition-colors border"
            onClick={() => onVitalClick(patient, 'watchWorn')}
          >
            <p className="text-xs text-gray-600 mb-0.5 text-center font-medium">Watch Status</p>
            <div className="flex items-center justify-between">
              <div className={`p-0.5 rounded ${currentVitals?.watchWorn === false ? 'bg-red-100 text-red-600' : 'bg-green-100 text-green-600'}`}>
                <Watch className="w-4 h-4" />
              </div>
              <div className="text-right">
                <span className={`font-bold text-lg ${currentVitals?.watchWorn === false ? 'text-red-600' : 'text-green-600'}`}>
                  {currentVitals?.watchWorn !== undefined ? (currentVitals.watchWorn ? 'ON' : 'OFF') : '--'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <ECGViewer
        patient={patient}
        onECGView={onECGView}
        onVitalClick={onVitalClick}
        onToggleECGMode={onToggleECGMode}
      />
    </div>
  );
};