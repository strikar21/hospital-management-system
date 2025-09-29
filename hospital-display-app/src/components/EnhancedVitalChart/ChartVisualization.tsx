/**
 * ChartVisualization - Chart rendering logic for enhanced vital chart
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade vital chart visualization with abnormal value detection
 */

import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { VitalDataPoint, MedicationEvent, ChartConfig } from './VitalChartContainer';

interface ChartDotProps {
  cx?: number;
  cy?: number;
  payload?: {
    isAbnormal?: boolean;
    diastolicAbnormal?: boolean;
  };
}

interface TooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    name: string;
    color: string;
    dataKey: string;
    payload: {
      timestamp: string;
      diastolic?: number;
      [key: string]: any;
    };
  }>;
  label?: string;
}

interface ChartVisualizationProps {
  vitalData: VitalDataPoint[];
  secondaryVitalData: VitalDataPoint[];
  medicationEvents: MedicationEvent[];
  loading: boolean;
  showMedications: boolean;
  showRawData: boolean;
  chartConfig: ChartConfig;
  secondaryChartConfig: ChartConfig;
  isBloodPressure: boolean;
  vitalType: string;
  getVitalDisplayName: () => string;
}

export const ChartVisualization: React.FC<ChartVisualizationProps> = ({
  vitalData,
  secondaryVitalData,
  medicationEvents,
  loading,
  showMedications,
  showRawData,
  chartConfig,
  secondaryChartConfig,
  isBloodPressure,
  vitalType,
  getVitalDisplayName
}) => {

  // Custom dot component for abnormal values
  const CustomDot = (props: ChartDotProps) => {
    const { cx, cy, payload } = props;
    if (payload?.isAbnormal) {
      return (
        <circle
          cx={cx}
          cy={cy}
          r="6"
          fill="#EF4444"
          stroke="#FFFFFF"
          strokeWidth="2"
          className="animate-pulse"
        />
      );
    }
    return <circle cx={cx} cy={cy} r="3" fill={isBloodPressure ? '#EF4444' : '#10B981'} />;
  };

  // Custom dot for diastolic values
  const CustomDiastolicDot = (props: ChartDotProps) => {
    const { cx, cy, payload } = props;
    if (payload?.diastolicAbnormal) {
      return (
        <circle
          cx={cx}
          cy={cy}
          r="6"
          fill="#3B82F6"
          stroke="#FFFFFF"
          strokeWidth="2"
          className="animate-pulse"
        />
      );
    }
    return <circle cx={cx} cy={cy} r="3" fill="#3B82F6" />;
  };

  // Custom tooltip component
  const CustomTooltip = ({ active, payload, label }: TooltipProps) => {
    if (active && payload && payload.length > 0) {
      const data = payload[0].payload;

      return (
        <div className="bg-gray-800 text-white p-3 rounded-lg shadow-lg border">
          <p className="font-medium">{`Time: ${label}`}</p>

          {/* Blood Pressure - Show both systolic and diastolic */}
          {isBloodPressure && data.diastolicValue !== undefined ? (
            <div>
              <p className="text-red-300">{`Systolic: ${payload[0].value.toFixed(0)} mmHg ${(data.isAbnormal && payload[0].value < 90) || payload[0].value > 140 ? '⚠️' : '✓'}`}</p>
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

  // Prepare chart data - combine primary and secondary data for blood pressure
  const chartData: Array<VitalDataPoint & {
    time: string;
    diastolicValue?: number;
    diastolicAbnormal?: boolean;
  }> = vitalData.map((point, index) => {
    const formattedTime = new Date(point.timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });

    const baseData = {
      time: formattedTime,
      timestamp: point.timestamp,
      value: point.value,
      isAbnormal: point.isAbnormal || false,
      qualityScore: point.qualityScore,
      dataPoints: point.dataPoints,
      maxValue: point.maxValue,
      minValue: point.minValue
    };

    // Add diastolic data for blood pressure charts
    if (isBloodPressure && secondaryVitalData[index]) {
      return {
        ...baseData,
        diastolicValue: secondaryVitalData[index].value,
        diastolicAbnormal: secondaryVitalData[index].isAbnormal || false
      };
    }

    return baseData;
  });

  return (
    <div className="flex-1 p-4 relative">
      {loading ? (
        <div className="flex items-center justify-center h-full">
          <div className="text-lg text-gray-600">Loading vital data...</div>
        </div>
      ) : showRawData ? (
        /* Raw Data Table View */
        <div className="overflow-auto h-full">
          <table className="w-full text-sm">
            <thead className="bg-gray-100 sticky top-0">
              <tr>
                <th className="p-2 text-left">Time</th>
                <th className="p-2 text-left">Value</th>
                {isBloodPressure && <th className="p-2 text-left">Diastolic</th>}
                <th className="p-2 text-left">Quality</th>
                <th className="p-2 text-left">Status</th>
              </tr>
            </thead>
            <tbody>
              {chartData.map((point, index) => (
                <tr key={index} className={point.isAbnormal ? 'bg-red-50' : ''}>
                  <td className="p-2 font-mono text-xs">{point.time}</td>
                  <td className="p-2 font-medium">
                    {point.value.toFixed(1)} {chartConfig.yAxisLabel}
                  </td>
                  {isBloodPressure && (
                    <td className="p-2 font-medium">
                      {point.diastolicValue?.toFixed(1)} {secondaryChartConfig.yAxisLabel}
                    </td>
                  )}
                  <td className="p-2">
                    {point.qualityScore ? (point.qualityScore * 100).toFixed(0) + '%' : 'N/A'}
                  </td>
                  <td className="p-2">
                    {point.isAbnormal ? (
                      <span className="text-red-600 font-medium">⚠️ Abnormal</span>
                    ) : (
                      <span className="text-green-600">✓ Normal</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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
  );
};