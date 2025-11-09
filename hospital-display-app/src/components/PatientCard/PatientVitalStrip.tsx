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

  return (
    <div className="bg-gray-50 rounded-lg px-2 py-1 flex-shrink-0 h-[60px] flex items-end">
      <div className="vital-scroll w-full h-full flex items-end">
        <div
          className="flex space-x-1 vitals-infinite-scroll h-full"
          style={{
            minWidth: 'max-content',
            scrollSnapType: 'x mandatory'
          }}
        >
          {/* Duplicate vitals array for seamless infinite scroll */}
          {[...allVitals, ...allVitals, ...allVitals].map((vital, index) => (
            <div
              key={`${vital.key}-${index}`}
              className={`flex flex-col items-center justify-end p-1 rounded hover:bg-blue-50 cursor-pointer transition-colors min-w-[60px] flex-shrink-0 self-stretch ${getVitalColorClass(vital.alertStatus)}`}
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
              <div className="flex items-center space-x-1 mb-0.5">
                <vital.icon className="w-3 h-3" />
                <span className="text-xs font-medium">{vital.label}</span>
              </div>
              <span className="text-xs font-bold">{vital.value}{vital.unit}</span>
            </div>
          ))}

          {/* Duplicate ECG/EEG displays for infinite scroll */}
          {[...Array(3)].map((_, repeatIndex) => (
            <div
              key={`ecg-eeg-${repeatIndex}`}
              className="flex flex-col items-center justify-end p-1 rounded hover:bg-blue-50 cursor-pointer transition-colors min-w-[60px] flex-shrink-0 self-stretch bg-green-50 text-green-600"
              onClick={(e) => {
                e.stopPropagation();
                onVitalClick(patient, isECGMode ? 'eegReading' : 'ecgReading');
              }}
            >
              <div className="flex items-center space-x-1 mb-0.5">
                {isECGMode ? <Brain className="w-3 h-3" /> : <Heart className="w-3 h-3" />}
                <span className="text-xs font-medium">{isECGMode ? 'EEG' : 'ECG'}</span>
              </div>
              <span className="text-xs font-bold">
                {isECGMode ? (patient.vitals?.eegReading || '--') : (patient.vitals?.ecgReading || '--')}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};