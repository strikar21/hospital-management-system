/**
 * VitalChartContainer - Main container for enhanced vital chart modal
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade vital chart container with modal structure and state management
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { X, ArrowLeft } from 'lucide-react';
import { patient } from '../../types';
import { VitalService } from '../../services';
import auditService from '../../services/auditService';
import { VitalChartControls } from './VitalChartControls';
import { ChartVisualization } from './ChartVisualization';

export interface VitalDataPoint {
  timestamp: string;
  time?: string;  // For raw data display in tables
  value: number;
  maxValue?: number;
  minValue?: number;
  qualityScore?: number;
  dataPoints?: number;
  isAbnormal?: boolean;
  diastolicValue?: number;  // For blood pressure charts that show both systolic and diastolic
  [key: string]: any;
}

export interface MedicationEvent {
  timestamp: string;
  medicationName: string;
  action: string;
  eventType: string;
  displayLabel: string;
}

export interface TimeframeOption {
  label: string;
  value: string;
  hours: number;
}

export interface ChartConfig {
  title?: string;
  color?: string;
  normalRange?: { min: number; max: number };
  yAxisLabel?: string;
  lineWidth?: number;
  dotSize?: number;
  thresholds?: {
    normalMin: number;
    normalMax: number;
  };
}

interface VitalChartContainerProps {
  patient: patient;
  vitalType: string;
  currentUser?: { id: string; staffId?: string; name: string; role: string };
  onClose: () => void;
}

// Define timeframe options outside component to avoid re-creation
const timeframeOptions: TimeframeOption[] = [
  { label: '1 min', value: '1m', hours: 1 },      // 1hr window, 1min buckets
  { label: '5 min', value: '5m', hours: 6 },      // 6hr window, 5min buckets
  { label: '15 min', value: '15m', hours: 12 },   // 12hr window, 15min buckets
  { label: '30 min', value: '30m', hours: 24 },   // 24hr window, 30min buckets
  { label: '1 hour', value: '1h', hours: 48 },    // 48hr window, 1hr buckets
  { label: '4 hour', value: '4h', hours: 168 }    // 7day window, 4hr buckets
];

export const VitalChartContainer: React.FC<VitalChartContainerProps> = ({
  patient,
  vitalType,
  currentUser,
  onClose
}) => {

  // State management
  const [vitalData, setVitalData] = useState<VitalDataPoint[]>([]);
  const [secondaryVitalData, setSecondaryVitalData] = useState<VitalDataPoint[]>([]); // For diastolic BP
  const [medicationEvents, setMedicationEvents] = useState<MedicationEvent[]>([]);
  const [selectedTimeframe, setSelectedTimeframe] = useState('5m');
  const selectedHours = timeframeOptions.find(opt => opt.value === selectedTimeframe)?.hours || 6;
  const [loading, setLoading] = useState(true);
  const [showMedications, setShowMedications] = useState(true);
  const [showRawData, setShowRawData] = useState(false);
  const [chartConfig, setChartConfig] = useState<ChartConfig>({});
  const [secondaryChartConfig, setSecondaryChartConfig] = useState<ChartConfig>({});
  const modalRef = useRef<HTMLDivElement>(null);

  // Check if this is blood pressure
  const isBloodPressure = vitalType === 'systolicPressure' || vitalType === 'diastolicPressure';

  // Map frontend vital types to backend types
  const mapVitalType = (frontendType: string): string => {
    const mapping: { [key: string]: string } = {
      'heartRate': 'heartRate',
      'skinTemperature': 'skinTemperature',
      'systolicPressure': 'systolicPressure',
      'diastolicPressure': 'diastolicPressure',
      'oxygenSaturation': 'oxygenSaturation',
      'respiratoryRate': 'respiratoryRate',
      'ecgReading': 'ecgReading',
      'eegReading': 'eegReading',
      'bioelectricalImpedance': 'bioelectricalImpedance',
      'tremorIntensity': 'tremorIntensity'
    };
    return mapping[frontendType] || frontendType;
  };

  // Get vital display name
  const getVitalDisplayName = () => {
    const names: { [key: string]: string } = {
      'heartRate': 'Heart Rate',
      'skinTemperature': 'Skin Temperature',
      'systolicPressure': 'Systolic Pressure',
      'diastolicPressure': 'Diastolic Pressure',
      'oxygenSaturation': 'Oxygen Saturation',
      'respiratoryRate': 'Respiratory Rate',
      'ecgReading': 'ECG Reading',
      'eegReading': 'EEG Reading',
      'bioelectricalImpedance': 'Bioelectrical Impedance',
      'tremorIntensity': 'Tremor Intensity'
    };
    return names[vitalType] || vitalType;
  };

  // Load vital data function
  const loadVitalData = useCallback(async () => {
    setLoading(true);

    try {
      const backendVitalType = mapVitalType(vitalType);

      // Use working getVitalHistory method with fallback support
      const timeRangeMap: { [key: string]: '1h' | '6h' | '24h' | '7d' } = {
        '1m': '1h',
        '5m': '6h',
        '15m': '24h',
        '30m': '24h',
        '1h': '24h',
        '4h': '7d'
      };

      const mappedTimeRange = timeRangeMap[selectedTimeframe] || '6h';
      const vitalHistoryData = await VitalService.getVitalHistory(patient.id, mappedTimeRange);

      if (vitalHistoryData && vitalHistoryData.length > 0) {
        // Convert VitalHistory format to chart data format
        if (isBloodPressure) {
          // Convert to systolic BP data
          const systolicData = vitalHistoryData.map((point: VitalDataPoint) => ({
            timestamp: point.time,
            time: point.time,
            value: point.systolicPressure || 0,
            diastolicValue: point.diastolicPressure || 0,
            qualityScore: 0.9,
            dataPoints: 1
          }));

          // Convert to diastolic BP data
          const diastolicData = vitalHistoryData.map((point: VitalDataPoint) => ({
            timestamp: point.time,
            value: point.diastolicPressure || 0,
            qualityScore: 0.9,
            dataPoints: 1
          }));

          setVitalData(systolicData);
          setSecondaryVitalData(diastolicData);
          setChartConfig({
            title: 'Systolic Blood Pressure',
            color: '#dc2626',
            normalRange: { min: 90, max: 140 },
            yAxisLabel: 'mmHg',
            thresholds: { normalMin: 90, normalMax: 140 }
          });
          setSecondaryChartConfig({
            title: 'Diastolic Blood Pressure',
            color: '#7c3aed',
            normalRange: { min: 60, max: 90 },
            yAxisLabel: 'mmHg',
            thresholds: { normalMin: 60, normalMax: 90 }
          });
        } else {
          // Handle single vital types
          const vitalKeyMap: { [key: string]: string } = {
            'heartRate': 'heartRate',
            'skinTemperature': 'skinTemperature',
            'oxygenSaturation': 'oxygenSaturation',
            'respiratoryRate': 'respiratoryRate',
            'ecgReading': 'ecgReading',
            'eegReading': 'eegReading',
            'bioelectricalImpedance': 'bioelectricalImpedance',
            'tremorIntensity': 'tremorIntensity'
          };

          const vitalKey = vitalKeyMap[vitalType] || 'heartRate';
          const chartData = vitalHistoryData.map((point: VitalDataPoint) => ({
            timestamp: point.time,
            time: point.time,
            value: (point[vitalKey] as number) || 0,
            qualityScore: 0.9,
            dataPoints: 1
          }));

          setVitalData(chartData);

          // Set chart config based on vital type
          const chartConfigs: { [key: string]: any } = {
            heartRate: {
              title: 'Heart Rate',
              color: '#dc2626',
              yAxisLabel: 'bpm',
              thresholds: { normalMin: 60, normalMax: 100 }
            },
            skinTemperature: {
              title: 'Skin Temperature',
              color: '#f97316',
              yAxisLabel: '°F',
              thresholds: { normalMin: 97, normalMax: 99 }
            },
            oxygenSaturation: {
              title: 'Oxygen Saturation',
              color: '#059669',
              yAxisLabel: '%',
              thresholds: { normalMin: 95, normalMax: 100 }
            },
            respiratoryRate: {
              title: 'Respiratory Rate',
              color: '#7c3aed',
              yAxisLabel: '/min',
              thresholds: { normalMin: 12, normalMax: 20 }
            },
            ecgReading: {
              title: 'ECG Reading',
              color: '#dc2626',
              yAxisLabel: 'mV',
              thresholds: { normalMin: 0.5, normalMax: 2.0 }
            },
            eegReading: {
              title: 'EEG Reading',
              color: '#7c3aed',
              yAxisLabel: 'μV',
              thresholds: { normalMin: 10, normalMax: 100 }
            }
          };

          setChartConfig(chartConfigs[vitalType] || chartConfigs.heartRate);
        }
      }
    } catch (error) {
      console.error('Error loading vital data:', error);
      setVitalData([]);
      setSecondaryVitalData([]);
    } finally {
      setLoading(false);
    }
  }, [patient.id, vitalType, selectedTimeframe, isBloodPressure]);

  // Load data on mount and timeframe change
  useEffect(() => {
    loadVitalData();
  }, [loadVitalData]);

  // Handle close with audit logging
  const handleClose = () => {
    onClose();
    auditService.logChartInteraction(
      'closeChart',
      patient.id,
      vitalType,
      `closed vital chart`,
      { timeframe: selectedTimeframe }
    );
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div ref={modalRef} className="bg-white rounded-2xl shadow-2xl w-full max-w-7xl h-[95vh] flex flex-col">

        {/* Header */}
        <div className="p-4 border-b flex items-center justify-between flex-shrink-0">
          <div className="flex items-center">
            <button
              onClick={handleClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors mr-3"
              title="Go Back"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            <div>
              <h2 className="text-xl font-bold text-gray-900">
                {patient.name} - {getVitalDisplayName()} Analytics
              </h2>
              <p className="text-sm text-gray-600">
                Bed {patient.bedNumber} • Room {patient.room} • {patient.ward} Ward
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            title="Close"
          >
            <X className="w-6 h-6 text-gray-600" />
          </button>
        </div>

        {/* Controls */}
        <VitalChartControls
          selectedTimeframe={selectedTimeframe}
          setSelectedTimeframe={setSelectedTimeframe}
          showMedications={showMedications}
          setShowMedications={setShowMedications}
          showRawData={showRawData}
          setShowRawData={setShowRawData}
          timeframeOptions={timeframeOptions}
          patient={patient}
          vitalType={vitalType}
          selectedHours={selectedHours}
          chartConfig={chartConfig}
          vitalData={vitalData}
          secondaryVitalData={secondaryVitalData}
          isBloodPressure={isBloodPressure}
          secondaryChartConfig={secondaryChartConfig}
        />

        {/* Chart */}
        <ChartVisualization
          vitalData={vitalData}
          secondaryVitalData={secondaryVitalData}
          medicationEvents={medicationEvents}
          loading={loading}
          showMedications={showMedications}
          showRawData={showRawData}
          chartConfig={chartConfig}
          secondaryChartConfig={secondaryChartConfig}
          isBloodPressure={isBloodPressure}
          vitalType={vitalType}
          getVitalDisplayName={getVitalDisplayName}
        />
      </div>
    </div>
  );
};