/**
 * VitalTransformer - Vital signs transformation utilities
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Handles medical-grade vital signs data transformation and time series processing
 */

import { BaseTransformer } from './BaseTransformer';

export class VitalTransformer extends BaseTransformer {

  // ================================
  // VITAL SIGNS TRANSFORMATION
  // ================================

  /**
   * Transform vital signs with medical accuracy - CAMELCASE ONLY
   * Backend now sends frontend field names - just pass through with defaults
   */
  static transformVitals(vitals: any): any {
    if (!vitals) return {};

    // Backend sends frontend field names - just pass through with defaults
    const result: any = {
      heartRate: this.transformField(vitals, 'heartRate', 0),
      systolicPressure: this.transformField(vitals, 'systolicPressure', 0),
      diastolicPressure: this.transformField(vitals, 'diastolicPressure', 0),
      respiratoryRate: this.transformField(vitals, 'respiratoryRate', 0),
      oxygenSaturation: this.transformField(vitals, 'oxygenSaturation', 0),
      skinTemperature: this.transformField(vitals, 'skinTemperature', 0),
      ecgReading: this.transformField(vitals, 'ecgReading', 0),
      eegReading: this.transformField(vitals, 'eegReading', 0),
      bioelectricalImpedance: this.transformField(vitals, 'bioelectricalImpedance', 0),
      tremorIntensity: this.transformField(vitals, 'tremorIntensity', 0),
      isEcgMode: this.transformField(vitals, 'isEcgMode', false),
      fallRisk: this.transformField(vitals, 'fallRisk', 'low'),
      lastDataReceived: this.transformField(vitals, 'lastDataReceived', new Date().toISOString()),
      dataQualityScore: this.transformField(vitals, 'dataQualityScore', 0),
      timestamp: this.transformField(vitals, 'timestamp', new Date().toISOString())
    };

    // Add nested ECG object if present (8-12 channel support)
    if (vitals.ecg) {
      result.ecg = vitals.ecg;
    }

    // Add nested EEG object if present (8-channel support)
    if (vitals.eeg) {
      result.eeg = vitals.eeg;
    }

    return result;
  }

  /**
   * Transform vital time series data - CAMELCASE ONLY
   * Medical-grade time series aggregation and validation
   */
  static transformVitalTimeSeriesData(data: any[]): any[] {
    if (!Array.isArray(data)) return [];

    const groupedData: { [key: string]: any } = {};

    data.forEach(item => {
      const timestamp = item.timestamp || item.time || new Date().toISOString();

      if (!groupedData[timestamp]) {
        groupedData[timestamp] = {
          timestamp,
          time: timestamp,
          heartRate: this.transformField(item, 'heartRate', 0),
          systolicPressure: this.transformField(item, 'systolicPressure', 0),
          diastolicPressure: this.transformField(item, 'diastolicPressure', 0),
          respiratoryRate: this.transformField(item, 'respiratoryRate', 0),
          oxygenSaturation: this.transformField(item, 'oxygenSaturation', 0),
          skinTemperature: this.transformField(item, 'skinTemperature', 0),
          ecgReading: this.transformField(item, 'ecgReading', 0),
          eegReading: this.transformField(item, 'eegReading', 0),
          bioelectricalImpedance: this.transformField(item, 'bioelectricalImpedance', 0),
          tremorIntensity: this.transformField(item, 'tremorIntensity', 0)
        };
      } else {
        // Update existing entry with non-zero values (latest data wins)
        if (item.heartRate) groupedData[timestamp].heartRate = item.heartRate;
        if (item.systolicPressure) groupedData[timestamp].systolicPressure = item.systolicPressure;
        if (item.diastolicPressure) groupedData[timestamp].diastolicPressure = item.diastolicPressure;
        if (item.respiratoryRate) groupedData[timestamp].respiratoryRate = item.respiratoryRate;
        if (item.oxygenSaturation) groupedData[timestamp].oxygenSaturation = item.oxygenSaturation;
        if (item.skinTemperature) groupedData[timestamp].skinTemperature = item.skinTemperature;
        if (item.ecgReading) groupedData[timestamp].ecgReading = item.ecgReading;
        if (item.eegReading) groupedData[timestamp].eegReading = item.eegReading;
        if (item.bioelectricalImpedance) groupedData[timestamp].bioelectricalImpedance = item.bioelectricalImpedance;
        if (item.tremorIntensity) groupedData[timestamp].tremorIntensity = item.tremorIntensity;
      }
    });

    return Object.values(groupedData).sort((a, b) =>
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
  }

  /**
   * Transform ECG waveform data for real-time display
   */
  static transformEcgWaveform(data: any[]): any[] {
    if (!Array.isArray(data)) return [];

    return data.map(point => ({
      timestamp: point.timestamp || new Date().toISOString(),
      value: this.transformField(point, 'ecgReading', 0),
      quality: this.transformField(point, 'dataQualityScore', 0),
      leadType: this.transformField(point, 'leadType', 'I')
    }));
  }

  /**
   * Transform EEG waveform data for neurological monitoring
   */
  static transformEegWaveform(data: any[]): any[] {
    if (!Array.isArray(data)) return [];

    return data.map(point => ({
      timestamp: point.timestamp || new Date().toISOString(),
      value: this.transformField(point, 'eegReading', 0),
      frequency: this.transformField(point, 'frequency', 0),
      amplitude: this.transformField(point, 'amplitude', 0),
      electrode: this.transformField(point, 'electrode', 'Fp1')
    }));
  }

  /**
   * Calculate vital signs trend analysis
   */
  static calculateVitalTrends(timeSeriesData: any[]): any {
    if (!Array.isArray(timeSeriesData) || timeSeriesData.length === 0) {
      return {
        heartRateTrend: 'stable',
        bloodPressureTrend: 'stable',
        temperatureTrend: 'stable',
        oxygenSaturationTrend: 'stable'
      };
    }

    const calculateTrend = (values: number[]): string => {
      if (values.length < 2) return 'stable';

      const recent = values.slice(-5); // Last 5 readings
      const firstValue = recent[0];
      const lastValue = recent[recent.length - 1];
      const change = ((lastValue - firstValue) / firstValue) * 100;

      if (Math.abs(change) < 5) return 'stable';
      return change > 0 ? 'increasing' : 'decreasing';
    };

    const heartRates = timeSeriesData.map(d => d.heartRate).filter(hr => hr > 0);
    const systolicValues = timeSeriesData.map(d => d.systolicPressure).filter(sp => sp > 0);
    const temperatures = timeSeriesData.map(d => d.skinTemperature).filter(t => t > 0);
    const oxygenSats = timeSeriesData.map(d => d.oxygenSaturation).filter(os => os > 0);

    return {
      heartRateTrend: calculateTrend(heartRates),
      bloodPressureTrend: calculateTrend(systolicValues),
      temperatureTrend: calculateTrend(temperatures),
      oxygenSaturationTrend: calculateTrend(oxygenSats),
      dataPoints: timeSeriesData.length,
      lastUpdated: timeSeriesData[timeSeriesData.length - 1]?.timestamp || new Date().toISOString()
    };
  }

  /**
   * Validate vital signs ranges for medical safety alerts
   */
  static validateVitalRanges(vitals: any): any {
    if (!vitals) return { valid: false, alerts: [] };

    const alerts: string[] = [];
    const ranges = {
      heartRate: { min: 30, max: 200, critical: { min: 20, max: 250 } },
      systolicPressure: { min: 70, max: 200, critical: { min: 60, max: 250 } },
      diastolicPressure: { min: 40, max: 120, critical: { min: 30, max: 150 } },
      respiratoryRate: { min: 8, max: 40, critical: { min: 5, max: 50 } },
      oxygenSaturation: { min: 85, max: 100, critical: { min: 70, max: 100 } },
      skinTemperature: { min: 35, max: 40, critical: { min: 32, max: 42 } }
    };

    Object.entries(ranges).forEach(([vital, range]) => {
      const value = vitals[vital];
      if (value && value > 0) {
        if (value < range.critical.min || value > range.critical.max) {
          alerts.push(`CRITICAL: ${vital} ${value} is outside safe range`);
        } else if (value < range.min || value > range.max) {
          alerts.push(`WARNING: ${vital} ${value} is outside normal range`);
        }
      }
    });

    return {
      valid: alerts.length === 0,
      alerts,
      criticalAlerts: alerts.filter(alert => alert.startsWith('CRITICAL')),
      warningAlerts: alerts.filter(alert => alert.startsWith('WARNING'))
    };
  }

  /**
   * Transform vital signs for dashboard summary
   */
  static transformVitalSummary(vitals: any): any {
    if (!vitals) return null;

    const transformed = this.transformVitals(vitals);
    const validation = this.validateVitalRanges(transformed);

    return {
      ...transformed,
      validation,
      bloodPressure: `${transformed.systolicPressure}/${transformed.diastolicPressure}`,  // Use frontend field names
      hasData: Object.values(transformed).some(value =>
        typeof value === 'number' && value > 0
      )
    };
  }

  /**
   * Transform vital signs for real-time monitoring display
   */
  static transformVitalForMonitoring(vitals: any): any {
    const transformed = this.transformVitals(vitals);
    const validation = this.validateVitalRanges(transformed);

    return {
      ...transformed,
      ...validation,
      displayReady: true,
      monitoringActive: transformed.lastDataReceived ?
        (new Date().getTime() - new Date(transformed.lastDataReceived).getTime()) < 60000 : false
    };
  }
}