import React, { useState, useEffect, useRef } from 'react';
import { X, Pill, TrendingUp, TrendingDown, ArrowLeft } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';
import { Patient } from './types';
import { HospitalAPI } from './api';
import auditService from './services/auditService';

interface EnhancedVitalChartProps {
  patient: Patient;
  vitalType: string;
  currentUser?: { id: string; staffId?: string; name: string; role: string };
  onClose: () => void;
}

interface VitalDataPoint {
  timestamp: string;
  value: number;
  maxValue?: number;
  minValue?: number;
  qualityScore?: number;
  dataPoints?: number;
}

interface MedicationEvent {
  timestamp: string;
  medicationName: string;
  action: string;
  eventType: string;
  displayLabel: string;
}

interface TimeframeOption {
  label: string;
  value: string;
  hours: number;
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

export const EnhancedVitalChart: React.FC<EnhancedVitalChartProps> = ({
  patient,
  vitalType,
  currentUser,
  onClose
}) => {
  const [vitalData, setVitalData] = useState<VitalDataPoint[]>([]);
  const [secondaryVitalData, setSecondaryVitalData] = useState<VitalDataPoint[]>([]); // For diastolic BP
  const [medicationEvents, setMedicationEvents] = useState<MedicationEvent[]>([]);
  const [selectedTimeframe, setSelectedTimeframe] = useState('5m');
  // Get hours automatically from selected timeframe
  const selectedHours = timeframeOptions.find(opt => opt.value === selectedTimeframe)?.hours || 6;
  const [loading, setLoading] = useState(true);
  const [showMedications, setShowMedications] = useState(true);
  const [showRawData, setShowRawData] = useState(false);
  const [chartConfig, setChartConfig] = useState<any>({});
  const [secondaryChartConfig, setSecondaryChartConfig] = useState<any>({});
  const modalRef = useRef<HTMLDivElement>(null);

  // Map frontend vital types to backend types
  const mapVitalType = (frontendType: string): string => {
    const mapping: { [key: string]: string } = {
      'heartRate': 'heartRate',
      'temperature': 'temperature',
      'bloodPressure': 'bloodPressureSystolic',
      'oxygenSat': 'oxygenSaturation',
      'respiratoryRate': 'respiratoryRate'
    };
    return mapping[frontendType] || frontendType;
  };

  const loadVitalData = async () => {
    setLoading(true);
    console.log('=== LOADING VITALS DATA ===');
    
    try {
      const backendVitalType = mapVitalType(vitalType);
      
      console.log('Patient Info:', patient);
      console.log('Request Parameters:', {
        patientId: patient.id,
        originalVitalType: vitalType,
        backendVitalType: backendVitalType,
        timeframe: selectedTimeframe,
        hours: selectedHours,
        raw: showRawData
      });
      
      console.log('Calling HospitalAPI.getVitalHistory (fallback)...');
      
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
      console.log('Mapped timeframe:', selectedTimeframe, '->', mappedTimeRange);
      
      const vitalHistoryData = await HospitalAPI.getVitalHistory(patient.id, mappedTimeRange);
      console.log('Vital history data:', vitalHistoryData.length, 'points');
      console.log('Raw vital history data:', vitalHistoryData);
      console.log('Sample data point:', vitalHistoryData[0]);
      
      if (vitalHistoryData && vitalHistoryData.length > 0) {
        // Convert VitalHistory format to chart data format
        const isBloodPressure = vitalType === 'bloodPressure';
        
        if (isBloodPressure) {
          console.log('Processing blood pressure data');
          
          // Convert to systolic BP data
          const systolicData = vitalHistoryData.map(point => ({
            timestamp: point.time,
            value: point.bloodPressure || 0,
            qualityScore: 0.9,
            dataPoints: 1
          }));
          
          // Convert to diastolic BP data
          const diastolicData = vitalHistoryData.map(point => ({
            timestamp: point.time,
            value: point.bloodPressureDiastolic || 0,
            qualityScore: 0.9,
            dataPoints: 1
          }));
          
          setVitalData(systolicData);
          setSecondaryVitalData(diastolicData);
          console.log('✅ Blood pressure data set - Systolic:', systolicData.length, 'Diastolic:', diastolicData.length);
          setChartConfig({ 
            title: 'Systolic Blood Pressure',
            color: '#dc2626',
            normalRange: { min: 90, max: 140 }
          });
          setSecondaryChartConfig({
            title: 'Diastolic Blood Pressure', 
            color: '#7c3aed',
            normalRange: { min: 60, max: 90 }
          });
        } else {
          // Convert single vital data
          // Map frontend vital types to VitalHistory property names
          const vitalKeyMap: { [key: string]: keyof typeof vitalHistoryData[0] } = {
            'heartRate': 'heartRate',
            'temperature': 'temperature', 
            'oxygenSat': 'oxygenSat',
            'respiratoryRate': 'respiratoryRate',
            'ecg': 'ecg',
            'eeg': 'eeg',
            'bioimpedance': 'bioimpedance',
            'tremor': 'tremor'
          };
          
          const vitalKey = vitalKeyMap[vitalType] || 'heartRate';
          console.log('Mapping vitalType:', vitalType, 'to key:', vitalKey);
          
          const chartData = vitalHistoryData.map(point => ({
            timestamp: point.time,
            value: (point[vitalKey] as number) || 0,
            qualityScore: 0.9,
            dataPoints: 1
          }));
          
          console.log('Sample converted data point:', chartData[0]);
          
          setVitalData(chartData);
          console.log('✅ Single vital data set:', vitalType, 'Points:', chartData.length);
          
          // Set chart config based on vital type
          const chartConfigs = {
            heartRate: { title: 'Heart Rate', color: '#dc2626', unit: 'BPM', normalRange: { min: 60, max: 100 }},
            temperature: { title: 'Temperature', color: '#f59e0b', unit: '°F', normalRange: { min: 97, max: 100 }},
            oxygenSat: { title: 'Oxygen Saturation', color: '#3b82f6', unit: '%', normalRange: { min: 95, max: 100 }},
            respiratoryRate: { title: 'Respiratory Rate', color: '#10b981', unit: '/min', normalRange: { min: 12, max: 20 }},
            ecg: { title: 'ECG', color: '#8b5cf6', unit: 'mV', normalRange: { min: 80, max: 160 }},
            eeg: { title: 'EEG', color: '#f97316', unit: 'μV', normalRange: { min: 30, max: 60 }}
          };
          
          const config = chartConfigs[vitalType as keyof typeof chartConfigs] || 
                        { title: vitalType, color: '#6b7280', unit: '', normalRange: { min: 0, max: 100 }};
          
          setChartConfig(config);
          console.log('✅ Successfully set vital data points:', chartData.length);
        }
      } else {
        console.log('❌ No vital history data available');
        setVitalData([]);
        setChartConfig({});
      }

      // Load medication timeline if showing medications
      if (showMedications) {
        console.log('Medication timeline disabled - using fallback mode');
        // Temporarily disable medication loading since analytics endpoint not available
        setMedicationEvents([]);
      }

    } catch (error) {
      console.error('=== ERROR LOADING VITALS ===');
      console.error('Error details:', error);
      console.error('Error stack:', error instanceof Error ? error.stack : 'No stack trace available');
    } finally {
      setLoading(false);
      console.log('=== LOADING COMPLETE ===');
    }
  };

  useEffect(() => {
    loadVitalData();
    
    // Log chart view on component mount (only on first load)
    if (vitalData.length === 0) {
      auditService.logChartInteraction(
        'openChart',
        patient.id,
        vitalType,
        `opened vital chart`,
        { timeframe: selectedTimeframe }
      ).catch(e => console.warn('Audit logging failed:', e));
    }
  }, [patient.id, vitalType, selectedTimeframe, showMedications, showRawData]);

  // Handle click outside to close modal
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(event.target as Node)) {
        onClose();
        auditService.logChartInteraction(
          'closeChart',
          patient.id,
          vitalType,
          `closed vital chart by clicking outside`,
          { timeframe: selectedTimeframe }
        ).catch(e => console.warn('Audit logging failed:', e));
      }
    };

    // Handle escape key
    const handleEscapeKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
        auditService.logChartInteraction(
          'closeChart',
          patient.id,
          vitalType,
          `closed vital chart with escape key`,
          { timeframe: selectedTimeframe }
        ).catch(e => console.warn('Audit logging failed:', e));
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscapeKey);
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscapeKey);
    };
  }, [onClose, patient.id, vitalType, selectedTimeframe]);
  
  // Custom dot component for abnormal values
  const CustomDot = (props: any) => {
    const { cx, cy, payload } = props;
    if (payload && payload.isAbnormal) {
      return (
        <circle 
          cx={cx} 
          cy={cy} 
          r={6} 
          fill="#ef4444" 
          stroke="#dc2626" 
          strokeWidth={2}
        />
      );
    }
    return null; // Use default dot for normal values
  };

  // Custom diastolic dot for BP
  const CustomDiastolicDot = (props: any) => {
    const { cx, cy, payload } = props;
    if (payload && payload.diastolicAbnormal) {
      return (
        <circle 
          cx={cx} 
          cy={cy} 
          r={6} 
          fill="#ef4444" 
          stroke="#dc2626" 
          strokeWidth={2}
        />
      );
    }
    return null; // Use default dot for normal values
  };
  
  const isBloodPressure = vitalType === 'bloodPressure';
  
  // Function to check if a vital value is abnormal
  const isAbnormal = (value: number, vitalType: string, isDiastolic: boolean = false) => {
    const ranges: { [key: string]: { min: number; max: number } } = {
      heartRate: { min: 60, max: 100 },
      temperature: { min: 97.0, max: 100.4 }, // °F
      oxygenSat: { min: 95, max: 100 },
      respiratoryRate: { min: 12, max: 20 },
      bloodPressure: isDiastolic 
        ? { min: 60, max: 90 }   // Diastolic: 60-90 mmHg 
        : { min: 90, max: 140 },  // Systolic: 90-140 mmHg
      ecg: { min: 80, max: 160 },
      eeg: { min: 30, max: 60 },
      bioimpedance: { min: 400, max: 600 },
      tremor: { min: 0, max: 0.5 }
    };
    
    const range = ranges[vitalType] || { min: 0, max: 100 };
    return value < range.min || value > range.max;
  };

  // Combine primary and secondary data for BP, or use single data for other vitals
  const chartData = vitalData.map((point, index) => {
    const isValueAbnormal = isAbnormal(point.value, vitalType);
    
    const formattedPoint: {
      time: string;
      value: number;
      timestamp: string;
      maxValue?: number;
      minValue?: number;
      qualityScore?: number;
      dataPoints?: number;
      diastolicValue?: number;
      isAbnormal?: boolean;
      pointColor?: string;
      diastolicAbnormal?: boolean;
    } = {
      time: point.timestamp, // Already formatted as "HH:MM"
      value: point.value, // Systolic for BP, or primary vital
      timestamp: point.timestamp,
      maxValue: point.maxValue,
      minValue: point.minValue,
      qualityScore: point.qualityScore,
      dataPoints: point.dataPoints,
      isAbnormal: isValueAbnormal,
      pointColor: isValueAbnormal ? '#ef4444' : (chartConfig.color || '#3b82f6') // Red for abnormal, normal color otherwise
    };
    
    // Add diastolic value if this is blood pressure
    if (isBloodPressure && secondaryVitalData[index]) {
      const diastolicValue = secondaryVitalData[index].value;
      const isDiastolicAbnormal = isAbnormal(diastolicValue, vitalType, true);
      
      if (index < 3) {
        console.log(`🩺 BP Analysis for point ${index}:`);
        console.log(`  Systolic: ${point.value} (abnormal: ${isValueAbnormal}) [normal: 90-140]`);
        console.log(`  Diastolic: ${diastolicValue} (abnormal: ${isDiastolicAbnormal}) [normal: 60-90]`);
      }
      
      formattedPoint.diastolicValue = diastolicValue;
      formattedPoint.diastolicAbnormal = isDiastolicAbnormal;
      
      // For BP, mark as abnormal if either systolic OR diastolic is abnormal
      formattedPoint.isAbnormal = isValueAbnormal || isDiastolicAbnormal;
      formattedPoint.pointColor = (isValueAbnormal || isDiastolicAbnormal) ? '#ef4444' : (chartConfig.color || '#dc2626');
    }
    
    if (index < 3) {
      console.log(`Chart point ${index}:`, formattedPoint);
    }
    
    return formattedPoint;
  });

  console.log('Final chartData length:', chartData.length);
  console.log('Final chartData sample:', chartData.slice(0, 2));

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      
      return (
        <div className="bg-gray-800 text-white p-3 rounded-lg shadow-lg border">
          <p className="font-medium">{`Time: ${label}`}</p>
          
          {/* Blood Pressure - Show both systolic and diastolic */}
          {isBloodPressure && data.diastolicValue !== undefined ? (
            <div>
              <p className="text-red-300">{`Systolic: ${payload[0].value.toFixed(0)} mmHg ${data.isAbnormal && payload[0].value < 90 || payload[0].value > 140 ? '⚠️' : '✓'}`}</p>
              <p className="text-purple-300">{`Diastolic: ${data.diastolicValue.toFixed(0)} mmHg ${data.diastolicAbnormal ? '⚠️' : '✓'}`}</p>
              <p className="text-blue-200 text-sm font-semibold">{`BP: ${payload[0].value.toFixed(0)}/${data.diastolicValue.toFixed(0)} mmHg`}</p>
              {(data.isAbnormal) && (
                <p className="text-red-400 text-sm">⚠️ Abnormal Reading</p>
              )}
            </div>
          ) : (
            /* Single vital display */
            <div>
              <p className="text-blue-300">{`${getVitalDisplayName()}: ${payload[0].value.toFixed(1)} ${chartConfig.yAxisLabel || ''}`}</p>
              {data.isAbnormal && (
                <p className="text-red-400 text-sm">⚠️ Abnormal Reading</p>
              )}
            </div>
          )}
          
          {data.maxValue && data.minValue && (
            <p className="text-gray-300 text-sm">{`Range: ${data.minValue.toFixed(1)} - ${data.maxValue.toFixed(1)}`}</p>
          )}
          {data.qualityScore && (
            <p className="text-green-300 text-sm">{`Quality: ${(data.qualityScore * 100).toFixed(0)}%`}</p>
          )}
          {data.dataPoints && (
            <p className="text-yellow-300 text-sm">{`Data Points: ${data.dataPoints}`}</p>
          )}
        </div>
      );
    }
    return null;
  };

  const getVitalDisplayName = () => {
    const names: { [key: string]: string } = {
      'heartRate': 'Heart Rate',
      'temperature': 'Temperature', 
      'bloodPressure': 'Blood Pressure',
      'oxygenSat': 'Oxygen Saturation',
      'respiratoryRate': 'Respiratory Rate'
    };
    return names[vitalType] || vitalType;
  };

  // Calculate statistics for visible data
  const getVisibleDataStats = () => {
    if (vitalData.length === 0) return null;
    
    const values = vitalData.map(point => point.value).filter(val => val != null);
    if (values.length === 0) return null;
    
    const calculateStats = (data: number[], unit: string) => {
      const sorted = [...data].sort((a, b) => a - b);
      const high = Math.max(...data);
      const low = Math.min(...data);
      const mean = data.reduce((sum, val) => sum + val, 0) / data.length;
      
      // Median
      const median = sorted.length % 2 === 0
        ? (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2
        : sorted[Math.floor(sorted.length / 2)];
      
      // Mode (most frequent value)
      const frequency: { [key: string]: number } = {};
      data.forEach(val => {
        const rounded = Math.round(val * 10) / 10; // Round to 1 decimal
        frequency[rounded] = (frequency[rounded] || 0) + 1;
      });
      
      const mode = Object.entries(frequency)
        .sort(([,a], [,b]) => b - a)[0]?.[0];
      
      return {
        high: Math.round(high * 10) / 10,
        low: Math.round(low * 10) / 10,
        mean: Math.round(mean * 10) / 10,
        median: Math.round(median * 10) / 10,
        mode: mode ? Math.round(parseFloat(mode) * 10) / 10 : mean,
        count: data.length,
        unit: unit
      };
    };
    
    // For blood pressure, return separate stats for systolic and diastolic
    if (isBloodPressure && secondaryVitalData.length > 0) {
      const diastolicValues = secondaryVitalData.map(point => point.value).filter(val => val != null);
      
      return {
        systolic: calculateStats(values, chartConfig.yAxisLabel || 'mmHg'),
        diastolic: calculateStats(diastolicValues, secondaryChartConfig.yAxisLabel || 'mmHg'),
        isBP: true
      };
    }
    
    // For single vitals, return single stats
    return calculateStats(values, chartConfig.yAxisLabel || '');
  };

  // Calculate dynamic Y-axis domain with padding
  const getYAxisDomain = () => {
    const allValues = [...vitalData.map(point => point.value)];
    if (secondaryVitalData.length > 0) {
      allValues.push(...secondaryVitalData.map(point => point.value));
    }
    
    if (allValues.length === 0) return [0, 100]; // Default range
    
    const min = Math.min(...allValues);
    const max = Math.max(...allValues);
    const range = max - min;
    
    // Add 10% padding on each side, with minimum padding of 1 unit
    const padding = Math.max(range * 0.1, 1);
    
    return [
      Math.max(0, Math.floor(min - padding)), // Don't go below 0 for most vitals
      Math.ceil(max + padding)
    ];
  };

  // Determine color based on vital value and thresholds
  const getVitalColor = (value: number, thresholds: any) => {
    if (!thresholds) return '#3B82F6'; // Default blue
    
    const { normalMin, normalMax, warningMin, warningMax } = thresholds;
    
    if (value < warningMin || value > warningMax) {
      return '#EF4444'; // Red for critical/abnormal
    } else if (value < normalMin || value > normalMax) {
      return '#F59E0B'; // Yellow/orange for warning/edge
    } else {
      return '#10B981'; // Green for normal
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div ref={modalRef} className="bg-white rounded-2xl shadow-2xl w-full max-w-7xl h-[95vh] flex flex-col">
        
        {/* Header */}
        <div className="p-4 border-b flex items-center justify-between flex-shrink-0">
          <div className="flex items-center">
            <button
              onClick={() => {
                onClose();
                auditService.logChartInteraction(
                  'closeChart',
                  patient.id,
                  vitalType,
                  `closed vital chart with back button`,
                  { timeframe: selectedTimeframe }
                );
              }}
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
            onClick={() => {
              onClose();
              auditService.logChartInteraction(
                'closeChart',
                patient.id,
                vitalType,
                `closed vital chart with X button`,
                { timeframe: selectedTimeframe }
              );
            }}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            title="Close"
          >
            <X className="w-6 h-6 text-gray-600" />
          </button>
        </div>
        
        {/* Controls */}
        <div className="p-4 border-b flex flex-wrap items-center justify-between gap-4">
          
          {/* Timeframe Selector */}
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium text-gray-700">Timeframe:</span>
            {timeframeOptions.map((option) => (
              <button
                key={option.value}
                onClick={() => {
                  setSelectedTimeframe(option.value);
                  auditService.logChartInteraction(
                    'changeTimeframe',
                    patient.id,
                    vitalType,
                    `changed chart timeframe to ${option.label}`,
                    { timeframe: option.value, hours: option.hours }
                  );
                }}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                  selectedTimeframe === option.value
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>

          {/* Toggle Controls */}
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setShowMedications(!showMedications)}
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                showMedications
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              <Pill className="w-4 h-4" />
              <span className="text-sm font-medium">Med Markers</span>
            </button>

            <button
              onClick={() => setShowRawData(!showRawData)}
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                showRawData
                  ? 'bg-orange-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              <span className="text-sm font-medium">1-sec Data</span>
            </button>

            <div className="text-sm text-gray-600">
              {vitalData.length} points • {selectedHours}h window
            </div>
          </div>
        </div>

        {/* Chart */}
        <div className="flex-1 p-4 min-h-0 relative">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-gray-600">Loading vital data...</p>
              </div>
            </div>
          ) : (
            <>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart 
                  data={chartData} 
                  margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                  <XAxis 
                    dataKey="time" 
                    tick={{ fontSize: 10 }}
                    stroke="#6B7280"
                    angle={-45}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis 
                    tick={{ fontSize: 12 }}
                    stroke="#6B7280"
                    domain={getYAxisDomain()}
                    label={{ 
                      value: chartConfig.yAxisLabel || '', 
                      angle: -90, 
                      position: 'insideLeft',
                      style: { textAnchor: 'middle' }
                    }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                  
                  {/* Main vital line (Systolic for BP, single line for others) */}
                  <Line 
                    type="monotone" 
                    dataKey="value" 
                    stroke={isBloodPressure ? '#EF4444' : '#10B981'} // Red for systolic, green for normal vitals
                    strokeWidth={chartConfig.lineWidth || 2}
                    name={isBloodPressure ? 'Systolic' : `${getVitalDisplayName()}`}
                    dot={<CustomDot />}
                    activeDot={{ 
                      r: (chartConfig.dotSize || 4) + 2, 
                      stroke: isBloodPressure ? '#EF4444' : '#10B981',
                      strokeWidth: 2 
                    }}
                  />
                  
                  {/* Diastolic line for blood pressure */}
                  {isBloodPressure && (
                    <Line 
                      type="monotone" 
                      dataKey="diastolicValue" 
                      stroke="#3B82F6" // Blue for diastolic
                      strokeWidth={chartConfig.lineWidth || 2}
                      name="Diastolic"
                      dot={<CustomDiastolicDot />}
                      activeDot={{ 
                        r: (chartConfig.dotSize || 4) + 2, 
                        stroke: '#3B82F6',
                        strokeWidth: 2 
                      }}
                    />
                  )}
                </LineChart>
              </ResponsiveContainer>

              {/* Medications if enabled - moved to overlay if needed */}
              {showMedications && medicationEvents.length > 0 && (
                <div className="absolute bottom-6 left-6 bg-white/95 rounded-lg p-2 shadow-lg border max-w-[200px]">
                  <div className="text-xs font-medium text-gray-700 mb-1">Recent Meds:</div>
                  {medicationEvents.slice(0, 2).map((event, index) => (
                    <div key={index} className="flex items-center space-x-1 mb-1">
                      <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                      <div className="text-xs text-gray-600 truncate">
                        <span className="font-medium">{event.medicationName.split(' ')[0]}</span>
                        <span className="text-gray-500 ml-1">
                          {new Date(event.timestamp).toLocaleTimeString('en-US', {
                            hour: '2-digit',
                            minute: '2-digit',
                            hour12: false
                          })}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        {/* Expanded Footer with Full Stats */}
        <div className="px-4 py-3 bg-gray-50 border-t">
          {/* Top row: Timeframe and Normal Range */}
          <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
            <div>
              {selectedTimeframe} • {selectedHours}h window
            </div>
            {chartConfig.thresholds && (
              <div>
                Normal: {chartConfig.thresholds.normalMin}-{chartConfig.thresholds.normalMax} {chartConfig.yAxisLabel}
              </div>
            )}
          </div>
          
          {/* Bottom row: Full Data Stats */}
          {(() => {
            const stats = getVisibleDataStats();
            if (!stats) return null;
            
            // Blood pressure - show separate systolic and diastolic stats
            if ('isBP' in stats && stats.isBP && 'systolic' in stats && 'diastolic' in stats) {
              return (
                <div className="space-y-1">
                  {/* Systolic stats */}
                  <div className="flex items-center justify-center space-x-4 text-xs">
                    <span className="text-red-700 font-bold">Systolic:</span>
                    <span className="text-red-600 font-medium">H: {stats.systolic.high}</span>
                    <span className="text-red-500">L: {stats.systolic.low}</span>
                    <span className="text-red-600">M: {stats.systolic.mean}</span>
                    <span className="text-red-500">Med: {stats.systolic.median}</span>
                    <span className="text-red-500">Mode: {stats.systolic.mode}</span>
                  </div>
                  {/* Diastolic stats */}
                  <div className="flex items-center justify-center space-x-4 text-xs">
                    <span className="text-blue-700 font-bold">Diastolic:</span>
                    <span className="text-blue-600 font-medium">H: {stats.diastolic.high}</span>
                    <span className="text-blue-500">L: {stats.diastolic.low}</span>
                    <span className="text-blue-600">M: {stats.diastolic.mean}</span>
                    <span className="text-blue-500">Med: {stats.diastolic.median}</span>
                    <span className="text-blue-500">Mode: {stats.diastolic.mode}</span>
                    <span className="text-gray-500 ml-2">{stats.systolic.count} pts</span>
                  </div>
                </div>
              );
            }
            
            // Single vital - show normal stats (type guard ensures correct properties)
            if ('high' in stats) {
              return (
                <div className="flex items-center justify-center space-x-6 text-xs">
                  <span className="text-red-600 font-medium">High: {stats.high} {stats.unit}</span>
                  <span className="text-blue-600 font-medium">Low: {stats.low} {stats.unit}</span>
                  <span className="text-gray-700 font-medium">Mean: {stats.mean} {stats.unit}</span>
                  <span className="text-gray-600">Median: {stats.median} {stats.unit}</span>
                  <span className="text-gray-600">Mode: {stats.mode} {stats.unit}</span>
                  <span className="text-gray-500">{stats.count} data points</span>
                </div>
              );
            }
            
            return null;
          })()}
        </div>
      </div>
    </div>
  );
};