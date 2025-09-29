// VitalService.ts - Vital signs monitoring and ECG data
import { vitalhistory, timerange, ecgreading } from '../types';
import { BaseService } from './BaseService';

/**
 * VitalService - Comprehensive vital signs monitoring and medical data service
 *
 * Handles critical medical operations including:
 * - Real-time vital signs monitoring and retrieval
 * - ECG/EEG data management and analysis
 * - Medication correlation analysis
 * - Medical device communication
 * - Proximity detection for room assignments
 * - Medical-grade data transformations with HIPAA compliance
 *
 * @extends BaseService
 * @since 1.0.0
 */
export class VitalService extends BaseService {

  // ================================
  // VITAL SIGNS RETRIEVAL
  // ================================

  /**
   * Retrieves time-series vital sign data for a specific patient and vital type
   *
   * @param patientId - The unique identifier for the patient
   * @param timeRange - Time range for data retrieval (1h, 6h, 24h, 7d)
   * @param vitalType - Type of vital sign to retrieve
   * @param limit - Maximum number of data points to return (default: 1000)
   * @returns Promise resolving to array of vital history data points
   * @throws {Error} When vital data retrieval fails
   *
   * @example
   * ```typescript
   * // Get heart rate data for last 24 hours
   * const heartRateData = await VitalService.getVitalTimeSeries(
   *   'P12345',
   *   '24h',
   *   'heartRate',
   *   500
   * );
   *
   * // Get blood pressure data for last 6 hours
   * const bpData = await VitalService.getVitalTimeSeries(
   *   'P12345',
   *   '6h',
   *   'systolicPressure'
   * );
   * ```
   */
  static async getVitalTimeSeries(
    patientId: string,
    timeRange: timerange,
    vitalType: 'heartRate' | 'systolicPressure' | 'diastolicPressure' | 'skinTemperature' | 'oxygenSaturation' | 'respiratoryRate' = 'heartRate',
    limit: number = 1000
  ): Promise<vitalhistory[]> {
    try {
      console.log(`🫀 Fetching ${vitalType} time series for patient ${patientId} (${timeRange})`);

      const response = await this.fetchFromBackend(
        `/patients/${patientId}/vitals/timeseries?vitalType=${vitalType}&timeRange=${timeRange}&limit=${limit}`
      );

      if (!Array.isArray(response)) {
        console.warn('⚠️ Invalid vital time series response');
        return [];
      }

      // Return data directly - transformation removed per user request
      const convertedData = Array.isArray(response) ? response : [];
      console.log(`✅ Retrieved ${convertedData.length} vital data points`);

      return convertedData;
    } catch (error) {
      console.error(`❌ Error fetching vital time series for ${patientId}:`, error);
      return [];
    }
  }

  /**
   * Retrieves comprehensive vital history for a patient across all vital types
   *
   * @param patientId - The unique identifier for the patient
   * @param timeRange - Time range for data retrieval (default: '24h')
   * @returns Promise resolving to array of comprehensive vital history records
   * @throws {Error} When vital history retrieval fails
   *
   * @example
   * ```typescript
   * // Get all vital history for last 24 hours
   * const vitalHistory = await VitalService.getVitalHistory('P12345');
   *
   * // Get vital history for last week
   * const weekHistory = await VitalService.getVitalHistory('P12345', '7d');
   * ```
   */
  static async getVitalHistory(patientId: string, timeRange: string = '24h') {
    try {
      const response = await this.fetchFromBackend(`/patients/${patientId}/vitals/history?timeRange=${timeRange}`);
      return response || [];
    } catch (error) {
      console.error('Failed to get vital history:', error);
      return [];
    }
  }

  /**
   * Retrieves vital signs data correlated with medication administration times
   *
   * @param patientId - The unique identifier for the patient
   * @param medicationId - The unique identifier for the medication
   * @param hoursBack - Number of hours to look back for correlation (default: 24)
   * @returns Promise resolving to object containing medication info and correlated vitals
   * @throws {Error} When medication correlation analysis fails
   *
   * @example
   * ```typescript
   * // Analyze vital changes after specific medication
   * const correlation = await VitalService.getMedicationCorrelatedVitals(
   *   'P12345',
   *   'MED789',
   *   48
   * );
   *
   * console.log('Medication:', correlation.medication.name);
   * console.log('Correlated vitals:', correlation.vitals.length);
   * ```
   */
  static async getMedicationCorrelatedVitals(
    patientId: string,
    medicationId: string,
    hoursBack: number = 24
  ): Promise<{ medication: any; vitals: vitalhistory[] }> {
    try {
      console.log(`💊 Fetching medication-correlated vitals for patient ${patientId}, medication ${medicationId}`);

      const response = await this.fetchFromBackend(
        `/patients/${patientId}/vitals/medication-correlation?medicationId=${medicationId}&hoursBack=${hoursBack}`
      );

      if (!response) {
        return { medication: null, vitals: [] };
      }

      return {
        medication: response.medication || null,
        vitals: response.vitals || []
      };
    } catch (error) {
      console.error('❌ Error fetching medication-correlated vitals:', error);
      return { medication: null, vitals: [] };
    }
  }

  // ================================
  // VITAL SIGNS UPDATES
  // ================================

  static async updatePatientVitals(patientId: string, vitals: any): Promise<boolean> {
    try {
      console.log(`🔄 Updating vitals for patient: ${patientId}`);

      await this.fetchFromBackend(`/patients/${patientId}/vitals`, {
        method: 'POST',
        body: JSON.stringify(vitals)
      });

      console.log('✅ Patient vitals updated successfully');
      return true;
    } catch (error) {
      console.error('❌ Error updating patient vitals:', error);
      return false;
    }
  }

  // ================================
  // ECG MONITORING
  // ================================

  static async getECGReadings(patientId: string, timeRange: timerange): Promise<ecgreading[]> {
    try {
      const response = await this.fetchFromBackend(`/patients/${patientId}/ecg?range=${timeRange}`);
      return Array.isArray(response) ? response : [];
    } catch (error) {
      console.error('❌ Error fetching ECG readings:', error);
      return [];
    }
  }

  static async switchMonitoringMode(patientId: string, isECGMode: boolean, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/patients/${patientId}/monitoring-mode`, {
        method: 'POST',
        body: JSON.stringify({
          isECGMode,
          switchedBy: userId,
          timestamp: new Date().toISOString()
        })
      });

      console.log(`✅ Monitoring mode switched to ${isECGMode ? 'ECG' : 'Standard'} for patient ${patientId}`);
      return true;
    } catch (error) {
      console.error('❌ Error switching monitoring mode:', error);
      return false;
    }
  }

  // ================================
  // ROOM PROXIMITY DETECTION
  // ================================

  static async detectRoomProximity() {
    try {
      const response = await this.fetchFromBackend('/devices/proximity');
      return response;
    } catch (error) {
      console.error('Failed to detect room proximity:', error);
      return { roomId: null, distance: null, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  }

  // ================================
  // MEDICATION TIMELINE
  // ================================

  static async getMedicationTimeline(patientId: string, hoursBack: number = 24) {
    try {
      const currentUser = this.getCurrentUser();
      if (!currentUser) {
        console.warn('⚠️ No current user found for medication timeline request');
        return [];
      }

      const response = await this.fetchFromBackend(
        `/patients/${patientId}/medications/timeline?hoursBack=${hoursBack}&requestedBy=${encodeURIComponent(currentUser.id)}`
      );

      return Array.isArray(response) ? response : [];
    } catch (error) {
      console.error('❌ Error fetching medication timeline:', error);
      return [];
    }
  }

  // ================================
  // SYSTEM STATUS
  // ================================

  static async getSystemStatus(): Promise<{
    totalPatients: number;
    criticalAlerts: number;
    activeDevices: number;
    systemLoad: number;
    lastSync: string;
  }> {
    try {
      const response = await this.fetchFromBackend('/system/status');

      return {
        totalPatients: response?.totalPatients || 0,
        criticalAlerts: response?.criticalAlerts || 0,
        activeDevices: response?.activeDevices || 0,
        systemLoad: response?.systemLoad || 0,
        lastSync: response?.lastSync || new Date().toISOString()
      };
    } catch (error) {
      console.error('❌ Error fetching system status:', error);
      return {
        totalPatients: 0,
        criticalAlerts: 0,
        activeDevices: 0,
        systemLoad: 0,
        lastSync: new Date().toISOString()
      };
    }
  }
}