// VitalChart.tsx - Fixed Sizing and Close Button

import React from 'react';
import { X } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Patient, VitalHistory, TimeRange } from './types';
import { getVitalDisplayName, getVitalUnit } from './utils';

interface VitalChartProps {
  patient: Patient;
  vitalType: string;
  vitalHistory: VitalHistory[];
  timeRange: TimeRange;
  onClose: () => void;
  onTimeRangeChange: (range: TimeRange) => void;
}

export const VitalChart: React.FC<VitalChartProps> = ({
  patient,
  vitalType,
  vitalHistory,
  timeRange,
  onClose,
  onTimeRangeChange
}) => {
  // Prepare chart data based on vital type
  const chartData = vitalHistory.map(h => {
    const baseData = { time: h.time };
    
    if (vitalType === 'bloodPressure') {
      // For blood pressure, show both systolic and diastolic
      return {
        ...baseData,
        systolic: h.bloodPressure, // Always integer - systolic
        diastolic: h.bloodPressureDiastolic || Math.round(h.bloodPressure * 0.6) // Always integer - diastolic from API or calculated
      };
    } else {
      // For other vitals, show only the selected vital
      return {
        ...baseData,
        [vitalType]: vitalType === 'heartRate' ? h.heartRate :
                    vitalType === 'temperature' ? h.temperature :
                    vitalType === 'oxygenSat' ? h.oxygenSat :
                    vitalType === 'respiratoryRate' ? h.respiratoryRate :
                    vitalType === 'ecg' ? h.ecg :
                    vitalType === 'eeg' ? h.eeg :
                    vitalType === 'bioimpedance' ? h.bioimpedance :
                    vitalType === 'tremor' ? h.tremor :
                    h[vitalType as keyof VitalHistory]
      };
    }
  });

  const timeRanges: TimeRange[] = ['1h', '6h', '24h', '7d'];

  // Get current value for display
  const getCurrentValue = () => {
    if (vitalType === 'heartRate') return `${patient.vitals.heartRate} BPM`;
    if (vitalType === 'temperature') return `${patient.vitals.temperature.toFixed(1)}°F`;
    if (vitalType === 'oxygenSat') return `${patient.vitals.oxygenSat}%`;
    if (vitalType === 'respiratoryRate') return `${patient.vitals.respiratoryRate || 16}/min`;
    if (vitalType === 'bloodPressure') return patient.vitals.bloodPressure;
    if (vitalType === 'ecg') return `${patient.vitals.ecg} mV`;
    if (vitalType === 'eeg') return `${patient.vitals.eeg || 45} μV`;
    if (vitalType === 'bioimpedance') return `${patient.vitals.bioimpedance || 500} Ω`;
    if (vitalType === 'tremor') return `${(patient.vitals.tremor || 0).toFixed(1)}/10`;
    return '';
  };

  // Get Y-axis domain for the specific vital
  const getYAxisDomain = () => {
    switch (vitalType) {
      case 'heartRate':
        return [40, 160];
      case 'temperature':
        return [95, 105];
      case 'skinTemperature':
        return [94, 104];
      case 'oxygenSat':
        return [80, 100];
      case 'respiratoryRate':
        return [5, 35];
      case 'bloodPressure':
        return [40, 200]; // Range to accommodate both systolic and diastolic
      case 'ecg':
        return [50, 250];
      case 'eeg':
        return [0, 100];
      case 'bioimpedance':
        return [300, 900];
      case 'tremor':
        return [0, 10];
      default:
        return ['auto', 'auto'];
    }
  };

  // Get colors for the vital type
  const getVitalColor = (vital: string) => {
    switch (vital) {
      case 'heartRate': return '#EF4444'; // Red
      case 'temperature': return '#F59E0B'; // Orange
      case 'skinTemperature': return '#FB923C'; // Light Orange
      case 'oxygenSat': return '#3B82F6'; // Blue
      case 'respiratoryRate': return '#06B6D4'; // Cyan
      case 'systolic': return '#8B5CF6'; // Purple
      case 'diastolic': return '#EC4899'; // Pink
      case 'ecg': return '#10B981'; // Green
      case 'eeg': return '#3B82F6'; // Blue
      case 'bioimpedance': return '#14B8A6'; // Teal
      case 'tremor': return '#F472B6'; // Pink
      default: return '#6B7280'; // Gray
    }
  };

  // Custom tooltip formatter
  const formatTooltipValue = (value: any, name: string) => {
    if (name === 'heartRate') return [`${Math.round(value)} BPM`, 'Heart Rate'];
    if (name === 'temperature') return [`${Number(value).toFixed(1)}°F`, 'Temperature'];
    if (name === 'skinTemperature') return [`${Number(value).toFixed(1)}°F`, 'Skin Temperature'];
    if (name === 'oxygenSat') return [`${Math.round(value)}%`, 'Oxygen Saturation'];
    if (name === 'respiratoryRate') return [`${Math.round(value)}/min`, 'Respiratory Rate'];
    if (name === 'systolic') return [`${Math.round(value)} mmHg`, 'Systolic Pressure'];
    if (name === 'diastolic') return [`${Math.round(value)} mmHg`, 'Diastolic Pressure'];
    if (name === 'ecg') return [`${Math.round(value)} mV`, 'ECG'];
    if (name === 'eeg') return [`${Math.round(value)} μV`, 'EEG'];
    if (name === 'bioimpedance') return [`${Math.round(value)} Ω`, 'Bioimpedance'];
    if (name === 'tremor') return [`${Number(value).toFixed(1)}/10`, 'Tremor Intensity'];
    return [value, name];
  };

  // Get reference ranges for the vital
  const getReferenceRanges = () => {
    switch (vitalType) {
      case 'heartRate':
        return '• Normal Range: 60-100 BPM';
      case 'temperature':
        return '• Normal Range: 97.0-99.0°F';
      case 'skinTemperature':
        return '• Normal Range: 96.0-98.0°F';
      case 'oxygenSat':
        return '• Normal Range: 95-100%';
      case 'respiratoryRate':
        return '• Normal Range: 12-20 breaths/min';
      case 'bloodPressure':
        return '• Normal Range: Systolic 90-140 mmHg, Diastolic 60-90 mmHg';
      case 'ecg':
        return '• Normal Range: 100-150 mV';
      case 'eeg':
        return '• Normal Range: 10-60 μV';
      case 'bioimpedance':
        return '• Normal Range: 450-650 Ω';
      case 'tremor':
        return '• Normal Range: 0-2/10 (minimal tremor)';
      default:
        return '';
    }
  };

  // Get clinical interpretation
  const getClinicalInterpretation = () => {
    switch (vitalType) {
      case 'heartRate':
        return 'Heart rate reflects cardiac function and autonomic nervous system activity. Tachycardia may indicate fever, pain, stress, or cardiovascular issues.';
      case 'temperature':
        return 'Core body temperature regulation is critical for metabolic function. Fever indicates immune response to infection or inflammation.';
      case 'skinTemperature':
        return 'Skin temperature reflects peripheral circulation and thermoregulation. Changes may indicate vascular compromise or autonomic dysfunction.';
      case 'oxygenSat':
        return 'Oxygen saturation measures hemoglobin oxygen binding. Low levels indicate respiratory or circulatory compromise requiring immediate attention.';
      case 'respiratoryRate':
        return 'Respiratory rate reflects ventilation adequacy and metabolic demand. Tachypnea may indicate respiratory distress, pain, or metabolic acidosis.';
      case 'bloodPressure':
        return 'Blood pressure reflects cardiac output and vascular resistance. Hypertension increases cardiovascular risk. Hypotension may indicate shock.';
      case 'ecg':
        return 'ECG amplitude reflects cardiac electrical activity and muscle mass. Abnormal patterns may indicate arrhythmias or structural heart disease.';
      case 'eeg':
        return 'EEG activity reflects brain electrical function and arousal state. Abnormal patterns may indicate seizures or altered consciousness.';
      case 'bioimpedance':
        return 'Bioimpedance measures tissue electrical properties related to fluid status and body composition. Changes may indicate fluid retention.';
      case 'tremor':
        return 'Tremor intensity indicates involuntary muscle activity. High levels increase fall risk and may suggest neurological conditions.';
      default:
        return 'This vital sign provides important information about the patient\'s physiological status.';
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-6xl h-[90vh] flex flex-col">
        <div className="p-4 border-b flex items-center justify-between flex-shrink-0">
          <div>
            <h2 className="text-xl font-bold text-gray-900">
              {patient.name} - {getVitalDisplayName(vitalType)} Chart
            </h2>
            <p className="text-sm text-gray-600">
              Bed {patient.bedNumber} • Room {patient.room} • {patient.ward} Ward
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-6 h-6 text-gray-600" />
          </button>
        </div>
        
        <div className="p-4 flex items-center justify-between border-b flex-shrink-0">
          <div className="flex items-center space-x-4">
            <span className="text-sm font-medium text-gray-700">Time Range:</span>
            {timeRanges.map((range) => (
              <button
                key={range}
                onClick={() => onTimeRangeChange(range)}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                  timeRange === range
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {range}
              </button>
            ))}
          </div>
          
          <div className="flex items-center space-x-4 text-sm">
            <div className="flex items-center space-x-2">
              <div 
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: getVitalColor(vitalType === 'bloodPressure' ? 'systolic' : vitalType) }}
              ></div>
              <span className="text-gray-600">
                Current: <strong>{getCurrentValue()}</strong>
              </span>
            </div>
          </div>
        </div>

        <div className="flex-1 p-4 min-h-0">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
              <XAxis 
                dataKey="time" 
                tick={{ fontSize: 12 }}
                stroke="#6B7280"
              />
              <YAxis 
                domain={getYAxisDomain()}
                tick={{ fontSize: 12 }}
                stroke="#6B7280"
                label={{ 
                  value: getVitalUnit(vitalType), 
                  angle: -90, 
                  position: 'insideLeft',
                  style: { textAnchor: 'middle' }
                }}
              />
              <Tooltip 
                contentStyle={{
                  backgroundColor: '#374151',
                  border: 'none',
                  borderRadius: '8px',
                  color: 'white'
                }}
                labelStyle={{ color: '#D1D5DB' }}
                formatter={formatTooltipValue}
              />
              <Legend />
              
              {/* Render lines based on vital type */}
              {vitalType === 'bloodPressure' ? (
                // Blood pressure shows both systolic and diastolic
                <>
                  <Line 
                    type="monotone" 
                    dataKey="systolic" 
                    stroke={getVitalColor('systolic')}
                    strokeWidth={3}
                    name="Systolic Pressure (mmHg)"
                    dot={{ fill: getVitalColor('systolic'), strokeWidth: 2, r: 4 }}
                    activeDot={{ r: 6, stroke: getVitalColor('systolic'), strokeWidth: 2 }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="diastolic" 
                    stroke={getVitalColor('diastolic')}
                    strokeWidth={3}
                    name="Diastolic Pressure (mmHg)"
                    dot={{ fill: getVitalColor('diastolic'), strokeWidth: 2, r: 4 }}
                    activeDot={{ r: 6, stroke: getVitalColor('diastolic'), strokeWidth: 2 }}
                  />
                </>
              ) : (
                // Other vitals show only the selected vital
                <Line 
                  type="monotone" 
                  dataKey={vitalType} 
                  stroke={getVitalColor(vitalType)}
                  strokeWidth={3}
                  name={`${getVitalDisplayName(vitalType)} (${getVitalUnit(vitalType)})`}
                  dot={{ fill: getVitalColor(vitalType), strokeWidth: 2, r: 4 }}
                  activeDot={{ r: 6, stroke: getVitalColor(vitalType), strokeWidth: 2 }}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Reference Ranges and Clinical Information */}
        <div className="px-4 py-3 bg-gray-50 border-t space-y-2 flex-shrink-0">
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-1">Normal Reference Range:</h4>
            <div className="text-xs text-gray-600">
              {getReferenceRanges()}
            </div>
          </div>
          
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-1">Clinical Interpretation:</h4>
            <div className="text-xs text-gray-600 leading-relaxed">
              {getClinicalInterpretation()}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};