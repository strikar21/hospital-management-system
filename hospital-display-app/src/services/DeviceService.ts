// DeviceService.ts - Device management and NFC operations
import { BaseService } from './BaseService';

export class DeviceService extends BaseService {

  // ================================
  // DEVICE POOL MANAGEMENT
  // ================================

  static async getFreeDevices(staffId: string, deviceType?: string, location?: string): Promise<any[]> {
    try {
      const response = await this.fetchFromBackend(`/watch-management/available`);
      return Array.isArray(response) ? response : [];
    } catch (error) {
      console.error('❌ Error fetching free devices:', error);
      return [];
    }
  }

  static async getDevicePoolStatus(staffId: string): Promise<any> {
    try {
      const response = await this.fetchFromBackend(`/watch-management/available`);
      return response || { totalDevices: 0, availableDevices: 0, assignedDevices: 0 };
    } catch (error) {
      console.error('❌ Error fetching device pool status:', error);
      return { totalDevices: 0, availableDevices: 0, assignedDevices: 0 };
    }
  }

  // ================================
  // DEVICE ASSIGNMENT
  // ================================

  static async assignDevice(staffId: string, deviceId: string, patientId: string, assignmentReason: string): Promise<any> {
    try {
      const response = await this.fetchFromBackend(`/watch-management/assign`, {
        method: 'POST',
        body: JSON.stringify({
          deviceId,
          patientId,
          assignedBy: staffId,
          reason: assignmentReason,
          timestamp: new Date().toISOString()
        })
      });

      console.log('✅ Device assigned successfully:', response);
      return response;
    } catch (error) {
      console.error('❌ Error assigning device:', error);
      throw error;
    }
  }

  static async unassignDevice(staffId: string, deviceId: string, unassignmentReason: string = 'patientDischarge'): Promise<boolean> {
    const caller = new Error().stack?.split('\n')[2]?.trim() || 'unknown';
    console.log('🌐 API.unassignDevice called:', { staffId, deviceId, unassignmentReason, caller });

    try {
      const response = await this.fetchFromBackend(`/watch-management/unassign`, {
        method: 'POST',
        body: JSON.stringify({
          deviceId,
          unassignedBy: staffId,
          reason: unassignmentReason,
          timestamp: new Date().toISOString()
        })
      });

      console.log('✅ Device unassigned successfully:', response);
      return true;
    } catch (error) {
      console.error('❌ Error unassigning device:', error);
      return false;
    }
  }

  static async reassignDevice(staffId: string, oldDeviceId: string, newDeviceId: string, reassignmentReason: string = 'deviceMalfunction'): Promise<any> {
    try {
      // Backend doesn't have reassign endpoint, so we unassign then assign
      await this.unassignDevice(staffId, oldDeviceId, reassignmentReason);
      // Note: We'd need the patientId to reassign to new device
      console.log('⚠️ Reassignment requires patient ID - partial operation completed');
      return { success: true, message: 'Old device unassigned, manual assignment of new device required' };
    } catch (error) {
      console.error('❌ Error reassigning device:', error);
      throw error;
    }
  }

  // ================================
  // DEVICE TRACKING
  // ================================

  static async getPatientDevice(staffId: string, patientId: string): Promise<any | null> {
    try {
      const response = await this.fetchFromBackend(`/watch-management/assigned`);

      if (Array.isArray(response)) {
        const patientDevice = response.find(assignment => assignment.patientId === patientId);
        return patientDevice || null;
      }

      return null;
    } catch (error) {
      console.error('❌ Error fetching patient device:', error);
      return null;
    }
  }

  static async getAssignmentHistory(staffId: string, patientId?: string, deviceId?: string, limit: number = 50): Promise<any[]> {
    try {
      const response = await this.fetchFromBackend(`/watch-management/assigned`);
      return Array.isArray(response) ? response.slice(0, limit) : [];
    } catch (error) {
      console.error('❌ Error fetching assignment history:', error);
      return [];
    }
  }

  static async bulkUnassignPatientDevices(staffId: string, patientId: string, unassignmentReason: string = 'patientDischarge'): Promise<any> {
    try {
      // Get patient's assigned device and unassign it
      const patientDevice = await this.getPatientDevice(staffId, patientId);

      if (patientDevice && patientDevice.deviceId) {
        const result = await this.unassignDevice(staffId, patientDevice.deviceId, unassignmentReason);
        console.log('✅ Bulk unassignment completed for patient:', patientId);
        return { success: result, devicesUnassigned: result ? 1 : 0 };
      }

      console.log('ℹ️ No devices found for patient:', patientId);
      return { success: true, devicesUnassigned: 0 };
    } catch (error) {
      console.error('❌ Error in bulk unassignment:', error);
      return { success: false, devicesUnassigned: 0 };
    }
  }

  // ================================
  // NFC OPERATIONS
  // ================================

  static async logNfcTap(patientWatchId: string, staffNfcId: string, location?: string): Promise<boolean> {
    try {
      // Send to backend for storage
      await this.fetchFromBackend('/nfc/tap-log', {
        method: 'POST',
        body: JSON.stringify({
          patientWatchId,
          staffNfcId,
          location: location || 'unknown',
          timestamp: new Date().toISOString(),
          tapType: 'staff_patient_interaction'
        })
      });

      console.log('✅ NFC tap logged successfully');
      return true;
    } catch (error) {
      console.error('❌ Error logging NFC tap:', error);
      return false;
    }
  }

  static async getNfcTapHistory(patientWatchId?: string, staffNfcId?: string, limit: number = 100): Promise<any[]> {
    try {
      const params = new URLSearchParams();
      if (patientWatchId) params.append('patientWatchId', patientWatchId);
      if (staffNfcId) params.append('staffNfcId', staffNfcId);
      params.append('limit', limit.toString());

      const response = await this.fetchFromBackend(`/nfc/tap-history?${params.toString()}`);
      return Array.isArray(response) ? response : [];
    } catch (error) {
      console.error('❌ Error fetching NFC tap history:', error);
      return [];
    }
  }

  // ================================
  // DEVICE STATUS AND MONITORING
  // ================================

  static async getDeviceStatus(deviceId: string): Promise<any> {
    try {
      const response = await this.fetchFromBackend(`/devices/${deviceId}/status`);
      return response || { status: 'unknown', batteryLevel: 0, lastSeen: null };
    } catch (error) {
      console.error('❌ Error fetching device status:', error);
      return { status: 'unknown', batteryLevel: 0, lastSeen: null };
    }
  }

  static async updateDeviceStatus(deviceId: string, status: any): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/devices/${deviceId}/status`, {
        method: 'PUT',
        body: JSON.stringify({
          ...status,
          updatedAt: new Date().toISOString()
        })
      });

      console.log('✅ Device status updated successfully');
      return true;
    } catch (error) {
      console.error('❌ Error updating device status:', error);
      return false;
    }
  }

  static async getDeviceAlerts(): Promise<any[]> {
    try {
      const response = await this.fetchFromBackend('/devices/alerts');
      return Array.isArray(response) ? response : [];
    } catch (error) {
      console.error('❌ Error fetching device alerts:', error);
      return [];
    }
  }

  // ================================
  // ROOM PROXIMITY AND LOCATION
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

  static async updateDeviceLocation(deviceId: string, location: { roomId?: string; coordinates?: { x: number; y: number } }): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/devices/${deviceId}/location`, {
        method: 'PUT',
        body: JSON.stringify({
          ...location,
          updatedAt: new Date().toISOString()
        })
      });

      console.log('✅ Device location updated successfully');
      return true;
    } catch (error) {
      console.error('❌ Error updating device location:', error);
      return false;
    }
  }

  // ================================
  // DEVICE PROVISIONING
  // ================================

  static async provisionDevice(deviceData: {
    deviceId: string;
    deviceType: string;
    model?: string;
    manufacturer?: string;
    firmwareVersion?: string;
  }): Promise<boolean> {
    try {
      await this.fetchFromBackend('/devices/provision', {
        method: 'POST',
        body: JSON.stringify({
          ...deviceData,
          provisionedAt: new Date().toISOString(),
          status: 'available'
        })
      });

      console.log('✅ Device provisioned successfully');
      return true;
    } catch (error) {
      console.error('❌ Error provisioning device:', error);
      return false;
    }
  }

  static async decommissionDevice(deviceId: string, reason: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/devices/${deviceId}/decommission`, {
        method: 'POST',
        body: JSON.stringify({
          reason,
          decommissionedAt: new Date().toISOString()
        })
      });

      console.log('✅ Device decommissioned successfully');
      return true;
    } catch (error) {
      console.error('❌ Error decommissioning device:', error);
      return false;
    }
  }
}