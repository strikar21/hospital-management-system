/**
 * VitalChartControls - Controls and statistics for enhanced vital chart
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade vital chart controls with timeframe selection and statistics
 */

import React from 'react';
import { Pill, BarChart3 } from 'lucide-react';
import { patient } from '../../types';
import auditService from '../../services/auditService';
import { VitalDataPoint, TimeframeOption, ChartConfig } from './VitalChartContainer';

interface VitalChartControlsProps {
  selectedTimeframe: string;
  setSelectedTimeframe: (timeframe: string) => void;
  showMedications: boolean;
  setShowMedications: (show: boolean) => void;
  showRawData: boolean;
  setShowRawData: (show: boolean) => void;
  timeframeOptions: TimeframeOption[];
  patient: patient;
  vitalType: string;
  selectedHours: number;
  chartConfig: ChartConfig;
  vitalData: VitalDataPoint[];
  secondaryVitalData: VitalDataPoint[];
  isBloodPressure: boolean;
  secondaryChartConfig: ChartConfig;
}

export const VitalChartControls: React.FC<VitalChartControlsProps> = ({
  selectedTimeframe,
  setSelectedTimeframe,
  showMedications,
  setShowMedications,
  showRawData,
  setShowRawData,
  timeframeOptions,
  patient,
  vitalType,
  selectedHours,
  chartConfig,
  vitalData,
  secondaryVitalData,
  isBloodPressure,
  secondaryChartConfig
}) => {

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

  return (
    <>
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
              className={`px-3 py-1 text-sm rounded-lg border transition-colors ${
                selectedTimeframe === option.value
                  ? 'bg-blue-500 text-white border-blue-500'
                  : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>

        {/* Toggle Controls */}
        <div className="flex items-center space-x-4">
          {/* Medications Toggle */}
          <button
            onClick={() => {
              setShowMedications(!showMedications);
              auditService.logChartInteraction(
                'toggleMedications',
                patient.id,
                vitalType,
                `${showMedications ? 'hid' : 'showed'} medication overlay`,
                { timeframe: selectedTimeframe, showMedications: !showMedications }
              );
            }}
            className={`flex items-center space-x-2 px-3 py-1.5 text-sm rounded-lg border transition-colors ${
              showMedications
                ? 'bg-purple-500 text-white border-purple-500'
                : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
            }`}
          >
            <Pill className="w-4 h-4" />
            <span>Medications</span>
          </button>

          {/* Raw Data Toggle */}
          <button
            onClick={() => {
              setShowRawData(!showRawData);
              auditService.logChartInteraction(
                'toggleRawData',
                patient.id,
                vitalType,
                `${showRawData ? 'hid' : 'showed'} raw data view`,
                { timeframe: selectedTimeframe, showRawData: !showRawData }
              );
            }}
            className={`flex items-center space-x-2 px-3 py-1.5 text-sm rounded-lg border transition-colors ${
              showRawData
                ? 'bg-green-500 text-white border-green-500'
                : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            <span>Raw Data</span>
          </button>
        </div>
      </div>

      {/* Statistics Footer */}
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
    </>
  );
};