/**
 * AlertService - Patient alert management service
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data
 *
 * Purpose: Centralized alert operations (previously misplaced in PatientCaseService)
 * Handles alert acknowledgment, resolution, and retrieval
 *
 * @module AlertService
 * @since Phase 6
 */

import { BaseService } from './BaseService';
import { alert } from '../types/PatientTypes';

/**
 * AlertService - Manages patient alerts
 *
 * Provides alert-specific operations that were previously mixed with case entry operations.
 * This service ensures proper separation of concerns.
 *
 * Key Features:
 * - Alert acknowledgment by medical staff
 * - Alert retrieval for patient monitoring
 * - Alert resolution and escalation (future)
 * - Medical compliance with audit trail
 *
 * @example
 * ```typescript
 * // Acknowledge an alert
 * const success = await AlertService.acknowledgeAlert('P123', 'ALR456', 'DOC001');
 *
 * // Get patient alerts
 * const alerts = await AlertService.getPatientAlerts('P123');
 * ```
 */
export class AlertService extends BaseService {

  // ================================
  // ALERT OPERATIONS
  // ================================

  /**
   * Acknowledge a patient alert
   *
   * Records that a medical staff member has seen and acknowledged the alert.
   * This creates an audit trail entry for medical compliance.
   *
   * @param patientId - Patient ID
   * @param alertId - Alert ID to acknowledge
   * @param userId - User ID of the staff member acknowledging the alert
   * @returns Promise resolving to true if acknowledged successfully
   *
   * @example
   * ```typescript
   * const success = await AlertService.acknowledgeAlert(
   *   'P123',
   *   'ALR456',
   *   'DOC001'
   * );
   *
   * if (success) {
   *   console.log('Alert acknowledged');
   * }
   * ```
   */
  static async acknowledgeAlert(
    patientId: string,
    alertId: string,
    userId: string
  ): Promise<boolean> {
    try {
      await this.fetchFromBackend(
        `/atomic/patients/${patientId}/alerts/${alertId}/acknowledge`,
        {
          method: 'POST',
          body: JSON.stringify({
            acknowledgedBy: userId,
            alertId: alertId
            // Let backend handle acknowledgedAt timestamp to avoid datetime format issues
          })
        }
      );

      return true;
    } catch (error) {
      console.error('Error acknowledging alert:', error);
      return false;
    }
  }

  /**
   * Get all alerts for a patient
   *
   * Retrieves active and historical alerts for patient monitoring.
   *
   * @param patientId - Patient ID
   * @param includeAcknowledged - Include acknowledged alerts (default: true)
   * @returns Promise resolving to array of alerts
   *
   * @example
   * ```typescript
   * // Get all alerts
   * const allAlerts = await AlertService.getPatientAlerts('P123');
   *
   * // Get only unacknowledged alerts
   * const activeAlerts = await AlertService.getPatientAlerts('P123', false);
   * ```
   */
  static async getPatientAlerts(
    patientId: string,
    includeAcknowledged: boolean = true
  ): Promise<alert[]> {
    try {
      const endpoint = includeAcknowledged
        ? `/patients/${patientId}/alerts`
        : `/patients/${patientId}/alerts?acknowledged=false`;

      const response = await this.fetchFromBackend(endpoint);

      // Handle different response formats
      if (response?.alerts) {
        return response.alerts;
      }

      if (Array.isArray(response)) {
        return response;
      }

      return [];
    } catch (error) {
      console.error('Error fetching patient alerts:', error);
      return [];
    }
  }

  /**
   * Get unacknowledged alerts for a patient
   *
   * Convenience method for retrieving active/pending alerts only.
   *
   * @param patientId - Patient ID
   * @returns Promise resolving to array of unacknowledged alerts
   *
   * @example
   * ```typescript
   * const activeAlerts = await AlertService.getUnacknowledgedAlerts('P123');
   * ```
   */
  static async getUnacknowledgedAlerts(patientId: string): Promise<alert[]> {
    return this.getPatientAlerts(patientId, false);
  }

  /**
   * Resolve an alert
   *
   * Marks an alert as resolved after corrective action has been taken.
   * Future implementation for alert workflow.
   *
   * @param patientId - Patient ID
   * @param alertId - Alert ID to resolve
   * @param userId - User ID resolving the alert
   * @param resolution - Resolution notes/action taken
   * @returns Promise resolving to true if resolved successfully
   *
   * @example
   * ```typescript
   * const success = await AlertService.resolveAlert(
   *   'P123',
   *   'ALR456',
   *   'DOC001',
   *   'BP normalized after medication adjustment'
   * );
   * ```
   */
  static async resolveAlert(
    patientId: string,
    alertId: string,
    userId: string,
    resolution?: string
  ): Promise<boolean> {
    try {
      await this.fetchFromBackend(
        `/atomic/patients/${patientId}/alerts/${alertId}/resolve`,
        {
          method: 'POST',
          body: JSON.stringify({
            resolvedBy: userId,
            resolution: resolution || '',
            alertId: alertId
            // Let backend handle resolvedAt timestamp
          })
        }
      );

      return true;
    } catch (error) {
      console.error('Error resolving alert:', error);
      return false;
    }
  }

  /**
   * Escalate an alert
   *
   * Escalates an alert to higher priority or different staff.
   * Future implementation for alert workflow.
   *
   * @param patientId - Patient ID
   * @param alertId - Alert ID to escalate
   * @param userId - User ID escalating the alert
   * @param escalationReason - Reason for escalation
   * @returns Promise resolving to true if escalated successfully
   *
   * @example
   * ```typescript
   * const success = await AlertService.escalateAlert(
   *   'P123',
   *   'ALR456',
   *   'NUR001',
   *   'Patient condition deteriorating'
   * );
   * ```
   */
  static async escalateAlert(
    patientId: string,
    alertId: string,
    userId: string,
    escalationReason: string
  ): Promise<boolean> {
    try {
      await this.fetchFromBackend(
        `/atomic/patients/${patientId}/alerts/${alertId}/escalate`,
        {
          method: 'POST',
          body: JSON.stringify({
            escalatedBy: userId,
            reason: escalationReason,
            alertId: alertId
            // Let backend handle escalatedAt timestamp
          })
        }
      );

      return true;
    } catch (error) {
      console.error('Error escalating alert:', error);
      return false;
    }
  }

  /**
   * Get alert statistics for a patient
   *
   * Retrieves alert counts and statistics for monitoring dashboard.
   * Future implementation for analytics.
   *
   * @param patientId - Patient ID
   * @param timeRange - Time range in hours (default: 24)
   * @returns Promise resolving to alert statistics
   *
   * @example
   * ```typescript
   * const stats = await AlertService.getAlertStatistics('P123', 24);
   * // Returns: { total, acknowledged, unacknowledged, bySeverity: {...} }
   * ```
   */
  static async getAlertStatistics(
    patientId: string,
    timeRange: number = 24
  ): Promise<any> {
    try {
      const response = await this.fetchFromBackend(
        `/patients/${patientId}/alerts/statistics?hours=${timeRange}`
      );

      return response || {
        total: 0,
        acknowledged: 0,
        unacknowledged: 0,
        bySeverity: { low: 0, medium: 0, high: 0, critical: 0 }
      };
    } catch (error) {
      console.error('Error fetching alert statistics:', error);
      return {
        total: 0,
        acknowledged: 0,
        unacknowledged: 0,
        bySeverity: { low: 0, medium: 0, high: 0, critical: 0 }
      };
    }
  }
}
