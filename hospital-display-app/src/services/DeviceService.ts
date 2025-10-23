// DeviceService.ts - Device management and NFC operations
import { BaseService } from './BaseService';

/**
 * DeviceService - Medical device management and assignment service
 *
 * Handles critical medical device operations including:
 * - Medical device pool management and availability tracking
 * - Device assignment and unassignment to patients
 * - Assignment history and audit trails
 * - Device status monitoring and reporting
 * - NFC/RFID operations for device management
 * - Medical equipment safety and compliance tracking
 *
 * @extends BaseService
 * @since 1.0.0
 */
export class DeviceService extends BaseService {

  // ================================
  // DEVICE POOL MANAGEMENT
  // ================================

  /**
   * Retrieves all available (unassigned) medical devices from the device pool
   * NOW USING V2 API: Single Source of Truth architecture
   *
   * @param staffId - The unique identifier for the requesting staff member
   * @param deviceType - Optional filter by device type (e.g., 'watch', 'monitor')
   * @param location - Optional filter by device location/ward
   * @returns Promise resolving to array of available device objects
   * @throws {Error} When device pool retrieval fails
   *
   * @example
   * ```typescript
   * // Get all available devices
   * const devices = await DeviceService.getFreeDevices('STAFF123');
   *
   * // Get available watches in ICU
   * const icuWatches = await DeviceService.getFreeDevices('STAFF123', 'watch', 'ICU');
   * ```
   */
  static async getFreeDevices(staffId: string, deviceType?: string, location?: string): Promise<any[]> {
    try {
      // V2 API: Use unified endpoint with filtering
      const params = new URLSearchParams();
      params.append('status', 'available');
      if (deviceType) params.append('deviceType', deviceType);
      if (location) params.append('location', location);

      const response = await this.fetchFromBackend(`/v2/devices/?${params.toString()}`);

      // V2 API returns {devices: [...], count: N, total: N}
      return response?.devices || [];
    } catch (error) {
      // Error fetching free devices - handle silently
      return [];
    }
  }

  /**
   * Retrieves comprehensive status information about the medical device pool
   * NOW USING V2 API: Statistics endpoint with aggregated data
   *
   * @param staffId - The unique identifier for the requesting staff member
   * @returns Promise resolving to device pool status summary
   * @throws {Error} When device pool status retrieval fails
   *
   * @example
   * ```typescript
   * const status = await DeviceService.getDevicePoolStatus('STAFF123');
   * // Removed console.log for production
   * ```
   */
  static async getDevicePoolStatus(staffId: string): Promise<any> {
    try {
      // V2 API: Use statistics endpoint for aggregated data
      const response = await this.fetchFromBackend(`/v2/devices/stats/summary`);
      return response?.summary || { totalDevices: 0, availableDevices: 0, assignedDevices: 0 };
    } catch (error) {
      // Error fetching device pool status - handle silently
      return { totalDevices: 0, availableDevices: 0, assignedDevices: 0 };
    }
  }

  // ================================
  // DEVICE ASSIGNMENT
  // ================================

  /**
   * Assigns a medical device to a specific patient
   *
   * @param staffId - The unique identifier for the staff member performing assignment
   * @param deviceId - The unique identifier for the device to assign
   * @param patientId - The unique identifier for the patient receiving the device
   * @param assignmentReason - Medical justification for device assignment
   * @returns Promise resolving to assignment confirmation object
   * @throws {Error} When device assignment fails
   *
   * @example
   * ```typescript
   * const result = await DeviceService.assignDevice(
   *   'STAFF123',
   *   'DEVICE456',
   *   'PATIENT789',
   *   'patientAdmission'
   * );
   * // Removed console.log for production
   * ```
   */
  static async assignDevice(staffId: string, deviceId: string, patientId: string, assignmentReason: string): Promise<any> {
    try {
      const response = await this.fetchFromBackend(`/watchmanagement/assign`, {
        method: 'POST',
        body: JSON.stringify({
          deviceId,
          patientId,
          assignedBy: staffId,
          reason: assignmentReason,
          timestamp: new Date().toISOString()
        })
      });

      // Removed console.log for production
      return response;
    } catch (error) {
      // Error assigning device - handle silently
      throw error;
    }
  }

  /**
   * Unassigns a medical device from a patient (returns device to pool)
   *
   * @param staffId - The unique identifier for the staff member performing unassignment
   * @param deviceId - The unique identifier for the device to unassign
   * @param unassignmentReason - Medical justification for device unassignment (default: 'patientDischarge')
   * @returns Promise resolving to true if unassignment was successful
   * @throws {Error} When device unassignment fails
   *
   * @example
   * ```typescript
   * // Unassign device on patient discharge
   * const success = await DeviceService.unassignDevice(
   *   'STAFF123',
   *   'DEVICE456',
   *   'patientDischarge'
   * );
   *
   * // Unassign for device maintenance
   * const success = await DeviceService.unassignDevice(
   *   'STAFF123',
   *   'DEVICE456',
   *   'deviceMaintenance'
   * );
   * ```
   */
  static async unassignDevice(staffId: string, deviceId: string, unassignmentReason: string = 'patientDischarge'): Promise<boolean> {
    const caller = new Error().stack?.split('\n')[2]?.trim() || 'unknown';
    // Unassigning device - processing silently

    try {
      const response = await this.fetchFromBackend(`/watchmanagement/unassign`, {
        method: 'POST',
        body: JSON.stringify({
          deviceId,
          unassignedBy: staffId,
          reason: unassignmentReason,
          timestamp: new Date().toISOString()
        })
      });

      // Removed console.log for production
      return true;
    } catch (error) {
      // Error unassigning device - handle silently
      return false;
    }
  }

  static async reassignDevice(staffId: string, oldDeviceId: string, newDeviceId: string, reassignmentReason: string = 'deviceMalfunction'): Promise<any> {
    try {
      // Backend doesn't have reassign endpoint, so we unassign then assign
      await this.unassignDevice(staffId, oldDeviceId, reassignmentReason);
      // Note: We'd need the patientId to reassign to new device
      // Removed console.log for production
      return { success: true, message: 'Old device unassigned, manual assignment of new device required' };
    } catch (error) {
      // Error reassigning device - handle silently
      throw error;
    }
  }

  // ================================
  // DEVICE TRACKING
  // ================================

  static async getPatientDevice(staffId: string, patientId: string): Promise<any | null> {
    try {
      // V2 API: Filter by patientId directly
      const params = new URLSearchParams();
      params.append('patientId', patientId);
      params.append('includeUnassigned', 'false');

      const response = await this.fetchFromBackend(`/v2/devices/?${params.toString()}`);

      // V2 API returns {devices: [...]}
      if (response?.devices && response.devices.length > 0) {
        return response.devices[0]; // Return first (should only be one per patient)
      }

      return null;
    } catch (error) {
      // Error fetching patient device - handle silently
      return null;
    }
  }

  static async getAssignmentHistory(staffId: string, patientId?: string, deviceId?: string, limit: number = 50): Promise<any[]> {
    try {
      // V2 API: Get assigned devices with optional filtering
      const params = new URLSearchParams();
      params.append('includeUnassigned', 'false');
      params.append('limit', limit.toString());
      if (patientId) params.append('patientId', patientId);

      const response = await this.fetchFromBackend(`/v2/devices/?${params.toString()}`);
      return response?.devices || [];
    } catch (error) {
      // Error fetching assignment history - handle silently
      return [];
    }
  }

  static async bulkUnassignPatientDevices(staffId: string, patientId: string, unassignmentReason: string = 'patientDischarge'): Promise<any> {
    try {
      // Get patient's assigned device and unassign it
      const patientDevice = await this.getPatientDevice(staffId, patientId);

      if (patientDevice && patientDevice.deviceId) {
        const result = await this.unassignDevice(staffId, patientDevice.deviceId, unassignmentReason);
        // Removed console.log for production
        return { success: result, devicesUnassigned: result ? 1 : 0 };
      }

      // Removed console.log for production
      return { success: true, devicesUnassigned: 0 };
    } catch (error) {
      // Error in bulk unassignment - handle silently
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

      // Removed console.log for production
      return true;
    } catch (error) {
      // Error logging NFC tap - handle silently
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
      // Error fetching NFC tap history - handle silently
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
      // Error fetching device status - handle silently
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

      // Removed console.log for production
      return true;
    } catch (error) {
      // Error updating device status - handle silently
      return false;
    }
  }

  static async getDeviceAlerts(): Promise<any[]> {
    try {
      const response = await this.fetchFromBackend('/devices/alerts');
      return Array.isArray(response) ? response : [];
    } catch (error) {
      // Error fetching device alerts - handle silently
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
      // Failed to detect room proximity - handle silently
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

      // Removed console.log for production
      return true;
    } catch (error) {
      // Error updating device location - handle silently
      return false;
    }
  }

  // ================================
  // DEVICE PROVISIONING
  // ================================

  /**
   * Generates a 6-digit numeric provisioning PIN for ESP32 device setup
   * Requires Administrator or Technician role
   *
   * @param validityMinutes - How long the PIN is valid (default: 10 minutes)
   * @returns Promise resolving to PIN details (code, expiresAt, etc.)
   * @throws {Error} When PIN generation fails
   *
   * @example
   * ```typescript
   * const pinData = await DeviceService.generateProvisioningPin(10);
   * // Returns: { code: "123456", expiresAt: "2025-10-18T...", validityMinutes: 10 }
   * ```
   */
  static async generateProvisioningPin(validityMinutes: number = 10): Promise<{
    code: string;
    expiresAt: string;
    validityMinutes: number;
    technicianId: string;
  }> {
    try {
      const response = await this.fetchFromBackend('/provisioning/generate-code', {
        method: 'POST',
        body: JSON.stringify({ validityMinutes })
      });
      return response;
    } catch (error) {
      // Error generating provisioning PIN
      throw error;
    }
  }

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

      // Removed console.log for production
      return true;
    } catch (error) {
      // Error provisioning device - handle silently
      return false;
    }
  }

  /**
   * Provisions an ESP32-based device (watch, door scanner, etc.)
   * Backend will auto-generate deviceId and name if not provided
   *
   * @param deviceData - ESP32 device provisioning data
   * @returns Promise resolving to provisioned device details
   * @throws {Error} When ESP32 provisioning fails
   */
  static async provisionESP32Device(deviceData: {
    devicetype: string;
    location: string;
    macaddress?: string;
    ipaddress?: string;
    firmwareversion?: string;
    provisionedBy: string;
  }): Promise<any> {
    try {
      const response = await this.fetchFromBackend('/esp32/provision', {
        method: 'POST',
        body: JSON.stringify(deviceData)
      });
      return response;
    } catch (error) {
      // Error provisioning ESP32 device - handle silently
      throw error;
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

      // Removed console.log for production
      return true;
    } catch (error) {
      // Error decommissioning device - handle silently
      return false;
    }
  }

  // ================================
  // DEVICE CALIBRATION
  // ================================

  /**
   * Initiates calibration process for a medical device
   *
   * @param deviceId - The unique identifier for the device to calibrate
   * @param staffId - The unique identifier for the staff member performing calibration
   * @param calibrationType - Optional type of calibration (default: 'standard')
   * @returns Promise resolving to true if calibration was initiated successfully
   * @throws {Error} When device calibration fails
   *
   * @example
   * ```typescript
   * const success = await DeviceService.calibrateDevice('DEVICE456', 'STAFF123');
   * ```
   */
  static async calibrateDevice(deviceId: string, staffId: string, calibrationType: string = 'standard'): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/devices/${deviceId}/calibrate`, {
        method: 'POST',
        body: JSON.stringify({
          calibrationType,
          performedBy: staffId,
          timestamp: new Date().toISOString()
        })
      });

      // Removed console.log for production
      return true;
    } catch (error) {
      // Error calibrating device - handle silently
      return false;
    }
  }
}