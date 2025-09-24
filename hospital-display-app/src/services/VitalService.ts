// VitalService.ts - Vital signs monitoring and ECG data
import { vitalhistory, timerange, ecgreading } from '../types';
import { BaseService } from './BaseService';

export class VitalService extends BaseService {

  // ================================
  // VITAL SIGNS DATA TRANSFORMATION
  // ================================

  private static convertTimescaleToVitalHistory(timescaleData: any[]): vitalhistory[] {
    // Group data by timestamp to combine all vital types
    const groupedData: { [timestamp: string]: any } = {};

    timescaleData.forEach(item => {
      const timestamp = item.time || item.timestamp;
      if (!groupedData[timestamp]) {
        groupedData[timestamp] = {
          time: timestamp,
          heartRate: 0,
          bloodPressure: 0,
          bloodPressureDiastolic: 0,
          temperature: 0,
          oxygenSaturation: 0,
          respiratoryRate: 0,
          qualityScore: 0.9
        };
      }

      // Map TimescaleDB columns to frontend format
      if (item.heart_rate !== undefined) groupedData[timestamp].heartRate = item.heart_rate;
      if (item.blood_pressure !== undefined) groupedData[timestamp].bloodPressure = item.blood_pressure;
      if (item.blood_pressure_diastolic !== undefined) groupedData[timestamp].bloodPressureDiastolic = item.blood_pressure_diastolic;
      if (item.temperature !== undefined) groupedData[timestamp].temperature = item.temperature;
      if (item.oxygen_saturation !== undefined) groupedData[timestamp].oxygenSaturation = item.oxygen_saturation;
      if (item.respiratory_rate !== undefined) groupedData[timestamp].respiratoryRate = item.respiratory_rate;
      if (item.quality_score !== undefined) groupedData[timestamp].qualityScore = item.quality_score;

      // Handle camelCase variants
      if (item.heartRate !== undefined) groupedData[timestamp].heartRate = item.heartRate;
      if (item.bloodPressure !== undefined) groupedData[timestamp].bloodPressure = item.bloodPressure;
      if (item.bloodPressureDiastolic !== undefined) groupedData[timestamp].bloodPressureDiastolic = item.bloodPressureDiastolic;
      if (item.oxygenSaturation !== undefined) groupedData[timestamp].oxygenSaturation = item.oxygenSaturation;
      if (item.respiratoryRate !== undefined) groupedData[timestamp].respiratoryRate = item.respiratoryRate;
      if (item.qualityScore !== undefined) groupedData[timestamp].qualityScore = item.qualityScore;
    });

    // Convert grouped data to array and sort by timestamp
    return Object.values(groupedData).sort((a, b) =>
      new Date(a.time).getTime() - new Date(b.time).getTime()
    );
  }

  // ================================
  // VITAL SIGNS RETRIEVAL
  // ================================

  static async getVitalTimeSeries(
    patientId: string,
    timeRange: timerange,
    vitalType: 'heartRate' | 'bloodPressure' | 'temperature' | 'oxygenSaturation' | 'respiratoryRate' = 'heartRate',
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

      const convertedData = this.convertTimescaleToVitalHistory(response);
      console.log(`✅ Retrieved ${convertedData.length} vital data points`);

      return convertedData;
    } catch (error) {
      console.error(`❌ Error fetching vital time series for ${patientId}:`, error);
      return [];
    }
  }

  static async getVitalHistory(patientId: string, timeRange: string = '24h') {
    try {
      const response = await this.fetchFromBackend(`/patients/${patientId}/vitals/history?timeRange=${timeRange}`);
      return response || [];
    } catch (error) {
      console.error('Failed to get vital history:', error);
      return [];
    }
  }

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
        vitals: this.convertTimescaleToVitalHistory(response.vitals || [])
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