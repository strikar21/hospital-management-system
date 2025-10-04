/**
 * Universal Data Refresh Hook - Single Source of Truth Implementation
 *
 * This hook provides centralized data refreshing functionality for all medical operations.
 * After atomic operations, the frontend refetches fresh data from the backend instead of
 * manually updating state, ensuring the backend remains the single source of truth.
 *
 * Medical Safety: All medical record data comes from backend database, not frontend state.
 * Enhanced with BaseService architecture for proper security, authentication, and error handling.
 */

import { BaseService } from '../services/BaseService';

class DataRefreshService extends BaseService {
  /**
   * Refresh medications from backend after atomic operations
   * Used after: add, status change, administration
   */
  static async refreshMedications(patientId: string) {
    try {
      const response = await this.fetchFromBackend(`/patients/${patientId}/medications`);
      return response.medications || response;
    } catch (error) {
      // Failed to refresh medications
      throw error;
    }
  }

  /**
   * Refresh investigations from backend after atomic operations
   * Used after: add, complete, status updates
   */
  static async refreshInvestigations(patientId: string) {
    try {
      const response = await this.fetchFromBackend(`/patients/${patientId}/investigations`);
      return response.investigations || response;
    } catch (error) {
      // Failed to refresh investigations
      throw error;
    }
  }

  /**
   * Refresh therapies from backend after atomic operations
   * Used after: add, sessions, status updates
   */
  static async refreshTherapies(patientId: string) {
    try {
      const response = await this.fetchFromBackend(`/patients/${patientId}/therapies`);
      return response.therapies || response;
    } catch (error) {
      // Failed to refresh therapies
      throw error;
    }
  }

  /**
   * Refresh notes from backend after atomic operations
   * Used after: add regular notes, add handoff notes
   */
  static async refreshNotes(patientId: string) {
    try {
      const response = await this.fetchFromBackend(`/patients/${patientId}/notes`);
      return response.notes || response;
    } catch (error) {
      // Failed to refresh notes
      throw error;
    }
  }

  /**
   * Refresh alerts from backend after atomic operations
   * Used after: acknowledge alerts
   */
  static async refreshAlerts(patientId: string) {
    try {
      const response = await this.fetchFromBackend(`/patients/${patientId}/alerts`);
      return response.alerts || response;
    } catch (error) {
      // Failed to refresh alerts
      throw error;
    }
  }

  /**
   * Refresh case entries from backend after atomic operations
   * All atomic operations create case entries, so this is refreshed after every atomic operation
   */
  static async refreshCaseEntries(patientId: string) {
    try {
      const response = await this.fetchFromBackend(`/patients/${patientId}/case-entries`);
      return response.caseEntries || response;
    } catch (error) {
      // Failed to refresh case entries
      throw error;
    }
  }

  /**
   * Refresh all patient data (for complete refresh scenarios)
   */
  static async refreshPatientData(patientId: string) {
    try {
      const response = await this.fetchFromBackend(`/patients/${patientId}`);
      return response;
    } catch (error) {
      // Failed to refresh patient data
      throw error;
    }
  }

  /**
   * Refresh vital signs data from backend after atomic operations
   * Used after: vital monitoring changes, ECG mode toggles
   */
  static async refreshVitals(patientId: string) {
    try {
      const response = await this.fetchFromBackend(`/patients/${patientId}/vitals`);
      return response.vitals || response;
    } catch (error) {
      // Failed to refresh vitals
      throw error;
    }
  }

  /**
   * Refresh device assignments from backend after atomic operations
   * Used after: device assignment, unassignment, calibration
   */
  static async refreshDeviceAssignments(patientId: string) {
    try {
      const response = await this.fetchFromBackend(`/patients/${patientId}/devices`);
      return response.devices || response;
    } catch (error) {
      // Failed to refresh device assignments
      throw error;
    }
  }

  /**
   * Refresh staff information from backend after atomic operations
   * Used after: staff role changes, certification updates
   */
  static async refreshStaffData() {
    try {
      const response = await this.fetchFromBackend('/staff/');
      return response;
    } catch (error) {
      // Failed to refresh staff data
      throw error;
    }
  }
}

export const useDataRefresh = (patientId: string) => {
  /**
   * Refresh medications from backend after atomic operations
   * Used after: add, status change, administration
   */
  const refreshMedications = async () => {
    return DataRefreshService.refreshMedications(patientId);
  };

  /**
   * Refresh investigations from backend after atomic operations
   * Used after: add, complete, status updates
   */
  const refreshInvestigations = async () => {
    return DataRefreshService.refreshInvestigations(patientId);
  };

  /**
   * Refresh therapies from backend after atomic operations
   * Used after: add, sessions, status updates
   */
  const refreshTherapies = async () => {
    return DataRefreshService.refreshTherapies(patientId);
  };

  /**
   * Refresh notes from backend after atomic operations
   * Used after: add regular notes, add handoff notes
   */
  const refreshNotes = async () => {
    return DataRefreshService.refreshNotes(patientId);
  };

  /**
   * Refresh alerts from backend after atomic operations
   * Used after: acknowledge alerts
   */
  const refreshAlerts = async () => {
    return DataRefreshService.refreshAlerts(patientId);
  };

  /**
   * Refresh case entries from backend after atomic operations
   * All atomic operations create case entries, so this is refreshed after every atomic operation
   */
  const refreshCaseEntries = async () => {
    return DataRefreshService.refreshCaseEntries(patientId);
  };

  /**
   * Refresh all patient data (for complete refresh scenarios)
   */
  const refreshPatientData = async () => {
    return DataRefreshService.refreshPatientData(patientId);
  };

  /**
   * Refresh vital signs data from backend after atomic operations
   * Used after: vital monitoring changes, ECG mode toggles
   */
  const refreshVitals = async () => {
    return DataRefreshService.refreshVitals(patientId);
  };

  /**
   * Refresh device assignments from backend after atomic operations
   * Used after: device assignment, unassignment, calibration
   */
  const refreshDeviceAssignments = async () => {
    return DataRefreshService.refreshDeviceAssignments(patientId);
  };

  /**
   * Refresh staff information from backend after atomic operations
   * Used after: staff role changes, certification updates
   */
  const refreshStaffData = async () => {
    return DataRefreshService.refreshStaffData();
  };

  return {
    refreshMedications,
    refreshInvestigations,
    refreshTherapies,
    refreshNotes,
    refreshAlerts,
    refreshCaseEntries,
    refreshPatientData,
    refreshVitals,
    refreshDeviceAssignments,
    refreshStaffData
  };
};