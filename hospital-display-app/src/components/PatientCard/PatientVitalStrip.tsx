/**
 * PatientVitalStrip - Vital signs display strip component
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade vital signs display with infinite scroll and alert status indicators
 */

import React from 'react';
import { Heart, Activity, Thermometer, Droplets, Wind, Waves, Brain } from 'lucide-react';
import { patient, user } from '../../types';
import auditService from '../../services/auditService';

interface VitalDisplayItem {
  key: string;
  icon: React.ComponentType<any>;
  label: string;
  value: string | number;
  unit: string;
  alertStatus: string;
}

interface PatientVitalStripProps {
  patient: patient;
  currentUser: user;
  allVitals: VitalDisplayItem[];
  isECGMode: boolean;
  arrhythmiaDetected: boolean;
  seizureActivity: boolean;
  onVitalClick: (patient: patient, vitalType: string) => void;
}

export const PatientVitalStrip: React.FC<PatientVitalStripProps> = ({
  patient,
  currentUser,
  allVitals,
  isECGMode,
  arrhythmiaDetected,
  seizureActivity,
  onVitalClick
}) => {

  // Color class mapping for vital alert status
  const getVitalColorClass = (alertStatus: string) => {
    // Professional medical colors based on alert severity
    switch (alertStatus) {
      case 'critical':
        return 'text-red-600 bg-red-50 border-l-4 border-red-500'; // Red for critical
      case 'warning':
        return 'text-yellow-600 bg-yellow-50 border-l-4 border-yellow-500'; // Yellow for warning
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

  // Get status indicator dot color
  const getStatusDotClass = (alertStatus: string) => {
    switch (alertStatus) {
      case 'critical':
        return 'bg-red-500 animate-pulse';
      case 'warning':
        return 'bg-yellow-500 animate-pulse';
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
  };

  return (
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
              <div className={`w-1.5 h-1.5 rounded-full mt-1 ${getStatusDotClass(vital.alertStatus)}`}></div>
            </div>
          ))}

          {/* Duplicate ECG/EEG displays for infinite scroll */}
          {[...Array(3)].map((_, repeatIndex) => (
            <div
              key={`ecg-eeg-${repeatIndex}`}
              className="flex flex-col items-center justify-center py-2 px-2 rounded hover:bg-blue-50 cursor-pointer transition-colors min-w-[65px] flex-shrink-0 h-full bg-green-50 text-green-600"
              onClick={(e) => {
                e.stopPropagation();
                onVitalClick(patient, isECGMode ? 'eegReading' : 'ecgReading');
              }}
            >
              <div className="flex items-center space-x-1 mb-1">
                {isECGMode ? <Brain className="w-3 h-3" /> : <Heart className="w-3 h-3" />}
                <span className="text-sm font-medium">{isECGMode ? 'EEG' : 'ECG'}</span>
              </div>
              <span className="text-sm font-bold">
                {isECGMode ? (patient.vitals?.eegReading || '--') : (patient.vitals?.ecgReading || '--')}
              </span>
              <div className={`w-1.5 h-1.5 rounded-full mt-1 ${
                isECGMode ? (seizureActivity ? 'bg-red-500 animate-pulse' : 'bg-green-500') :
                (arrhythmiaDetected ? 'bg-yellow-500 animate-pulse' : 'bg-green-500')
              }`}></div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};