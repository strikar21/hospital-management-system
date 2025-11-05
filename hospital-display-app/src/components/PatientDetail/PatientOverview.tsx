/**
 * PatientOverview - Patient detail overview component
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade patient overview with vitals display and trending
 */

import React, { useMemo } from 'react';
import {
  Heart, Activity, Thermometer, Droplets, Zap
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
      {/* Patient Info Row */}
      <div className="bg-gray-50 rounded-lg p-3 mb-2 flex-shrink-0">
        <h3 className="text-sm font-semibold mb-2">Patient Information</h3>
        <div className="grid grid-cols-3 gap-4 text-xs">
          <div>
            <p><span className="font-medium text-gray-600">Age:</span> {patient.age}y • <span className="font-medium text-gray-600">Gender:</span> {patient.gender}</p>
            <p><span className="font-medium text-gray-600">Weight:</span> {patient.weight}kg • <span className="font-medium text-gray-600">BMI:</span> {(patient.weight / Math.pow(1.75, 2)).toFixed(1)}</p>
          </div>
          <div>
            <p><span className="font-medium text-gray-600">Room:</span> {patient.room} • <span className="font-medium text-gray-600">Ward:</span> {patient.ward}</p>
            <p><span className="font-medium text-gray-600">Department:</span> {patient.department}</p>
          </div>
          <div>
            <p><span className="font-medium text-gray-600">Diagnosis:</span> {patient.diagnosis}</p>
            <p><span className="font-medium text-gray-600">Doctor:</span> {patient.assignedDoctor}</p>
          </div>
        </div>
      </div>

      {/* Device & Monitoring Section */}
      {patient.assignedDeviceId && (
        <div className="bg-blue-50 rounded-lg p-3 mb-2 flex-shrink-0">
          <h3 className="text-sm font-semibold text-blue-800 mb-2">📟 Assigned Watch</h3>
          <div className="grid grid-cols-4 gap-3 text-xs">
            <div>
              <span className="font-medium text-gray-600">Device ID:</span>{' '}
              <span className="text-gray-900">{patient.assignedDeviceId}</span>
            </div>
            <div>
              <span className="font-medium text-gray-600">Status:</span>
              <span className={`ml-1 px-2 py-0.5 rounded font-medium ${
                patient.deviceStatus === 'connected'
                  ? 'bg-green-100 text-green-800'
                  : 'bg-amber-100 text-amber-800'
              }`}>
                {patient.deviceStatus === 'connected' ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            <div>
              <span className="font-medium text-gray-600">Battery:</span>{' '}
              <span className={`font-medium ${
                (patient.deviceBatteryLevel || 0) <= 20 ? 'text-red-600' :
                (patient.deviceBatteryLevel || 0) <= 40 ? 'text-amber-600' :
                'text-green-600'
              }`}>
                {patient.deviceBatteryLevel || '--'}%
              </span>
            </div>
            <div>
              <span className="font-medium text-gray-600">Last Seen:</span>{' '}
              <span className="text-gray-900">
                {patient.deviceLastSeen
                  ? new Date(patient.deviceLastSeen).toLocaleTimeString('en-US', {
                      hour: '2-digit',
                      minute: '2-digit'
                    })
                  : '--'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* All Vitals - Single Row Layout (8×1) */}
      <div className="bg-gray-50 rounded-lg p-1 mb-2 flex-shrink-0">
        <div className="grid grid-cols-8 gap-2">
          <div
            className="bg-white rounded-lg p-2 cursor-pointer hover:bg-blue-50 transition-colors border"
            onClick={() => onVitalClick(patient, 'heartRate')}
          >
            <p className="text-xs text-gray-600 mb-2 text-center font-medium">Heart Rate</p>
            <div className="flex items-center justify-between">
              <div className={`p-1 rounded-lg ${getVitalStatusColor(MedicalUtils.getVitalStatus(currentVitals?.heartRate || 0, 'heartRate'))}`}>
                <Heart className="w-5 h-5" />
              </div>
              <div className="text-right">
                <span className="font-bold text-xl text-red-600">{currentVitals?.heartRate || '--'}</span>
                <span className="text-xs text-gray-500 ml-1">BPM</span>
              </div>
            </div>
          </div>

          <div
            className="bg-white rounded-lg p-2 cursor-pointer hover:bg-blue-50 transition-colors border"
            onClick={() => onVitalClick(patient, 'systolicPressure')}
          >
            <p className="text-xs text-gray-600 mb-2 text-center font-medium">Blood Pressure</p>
            <div className="flex items-center justify-between">
              <div className={`p-1 rounded-lg ${getVitalStatusColor(MedicalUtils.getVitalStatus(currentVitals?.systolicPressure || 0, 'systolicPressure', currentVitals?.diastolicPressure || 0))}`}>
                <Droplets className="w-5 h-5" />
              </div>
              <div className="text-right">
                <span className="font-bold text-lg text-purple-600">{currentVitals?.systolicPressure || '--'}/{currentVitals?.diastolicPressure || '--'}</span>
                <span className="text-xs text-gray-500 ml-1">mmHg</span>
              </div>
            </div>
          </div>

          <div
            className="bg-white rounded-lg p-2 cursor-pointer hover:bg-blue-50 transition-colors border"
            onClick={() => onVitalClick(patient, 'oxygenSaturation')}
          >
            <p className="text-xs text-gray-600 mb-2 text-center font-medium">Oxygen Sat</p>
            <div className="flex items-center justify-between">
              <div className={`p-1 rounded-lg ${getVitalStatusColor(MedicalUtils.getVitalStatus(currentVitals?.oxygenSaturation || 0, 'oxygenSaturation'))}`}>
                <Activity className="w-5 h-5" />
              </div>
              <div className="text-right">
                <span className="font-bold text-xl text-blue-600">{currentVitals?.oxygenSaturation || '--'}</span>
                <span className="text-xs text-gray-500 ml-1">%</span>
              </div>
            </div>
          </div>

          <div
            className="bg-white rounded-lg p-2 cursor-pointer hover:bg-blue-50 transition-colors border"
            onClick={() => onVitalClick(patient, 'skinTemperature')}
          >
            <p className="text-xs text-gray-600 mb-2 text-center font-medium">Temperature</p>
            <div className="flex items-center justify-between">
              <div className={`p-1 rounded-lg ${getVitalStatusColor(MedicalUtils.getVitalStatus(currentVitals?.skinTemperature || 0, 'skinTemperature'))}`}>
                <Thermometer className="w-5 h-5" />
              </div>
              <div className="text-right">
                <span className="font-bold text-xl text-orange-600">{currentVitals?.skinTemperature ? currentVitals.skinTemperature.toFixed(1) : '--'}</span>
                <span className="text-xs text-gray-500 ml-1">°F</span>
              </div>
            </div>
          </div>

          <div
            className="bg-white rounded-lg p-2 cursor-pointer hover:bg-blue-50 transition-colors border"
            onClick={() => onVitalClick(patient, 'respiratoryRate')}
          >
            <p className="text-xs text-gray-600 mb-2 text-center font-medium">Respiratory Rate</p>
            <div className="flex items-center justify-between">
              <div className={`p-1 rounded-lg ${getVitalStatusColor(MedicalUtils.getVitalStatus(currentVitals?.respiratoryRate || 0, 'respiratoryRate'))}`}>
                <Activity className="w-5 h-5" />
              </div>
              <div className="text-right">
                <span className="font-bold text-xl text-green-600">{currentVitals?.respiratoryRate || '--'}</span>
                <span className="text-xs text-gray-500 ml-1">/min</span>
              </div>
            </div>
          </div>

          <div
            className="bg-white rounded-lg p-2 cursor-pointer hover:bg-blue-50 transition-colors border"
            onClick={() => onVitalClick(patient, 'ecgReading')}
          >
            <p className="text-xs text-gray-600 mb-2 text-center font-medium">ECG Reading</p>
            <div className="flex items-center justify-between">
              <div className={`p-1 rounded-lg ${getVitalStatusColor(MedicalUtils.getVitalStatus(currentVitals?.ecgReading || 0, 'ecgReading'))}`}>
                <Zap className="w-5 h-5" />
              </div>
              <div className="text-right">
                <span className="font-bold text-xl text-yellow-600">{currentVitals?.ecgReading || '--'}</span>
                <span className="text-xs text-gray-500 ml-1">mV</span>
              </div>
            </div>
          </div>

          <div
            className="bg-white rounded-lg p-2 cursor-pointer hover:bg-blue-50 transition-colors border"
            onClick={() => onVitalClick(patient, 'eegReading')}
          >
            <p className="text-xs text-gray-600 mb-2 text-center font-medium">EEG Reading</p>
            <div className="flex items-center justify-between">
              <div className={`p-1 rounded-lg ${getVitalStatusColor(MedicalUtils.getVitalStatus(currentVitals?.eegReading || 0, 'eegReading'))}`}>
                <Activity className="w-5 h-5" />
              </div>
              <div className="text-right">
                <span className="font-bold text-xl text-indigo-600">{currentVitals?.eegReading || '--'}</span>
                <span className="text-xs text-gray-500 ml-1">μV</span>
              </div>
            </div>
          </div>

          <div
            className="bg-white rounded-lg p-2 cursor-pointer hover:bg-blue-50 transition-colors border"
            onClick={() => onVitalClick(patient, 'tremorIntensity')}
          >
            <p className="text-xs text-gray-600 mb-2 text-center font-medium">Tremor</p>
            <div className="flex items-center justify-between">
              <div className={`p-1 rounded-lg ${getVitalStatusColor(MedicalUtils.getVitalStatus(currentVitals?.tremorIntensity || 0, 'tremorIntensity'))}`}>
                <Activity className="w-5 h-5" />
              </div>
              <div className="text-right">
                <span className="font-bold text-xl text-pink-600">{currentVitals?.tremorIntensity ? currentVitals.tremorIntensity.toFixed(1) : '--'}</span>
                <span className="text-xs text-gray-500 ml-1">/10</span>
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