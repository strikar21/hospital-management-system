/**
 * AlertProcessor - Frontend domain logic for alert display and processing
 *
 * Single source of truth for:
 * - Alert formatting for UI display
 * - Severity-based styling (colors, icons)
 * - Alert grouping and sorting
 * - Alert priority calculation
 *
 * Matches backend AlertPipeline pattern for consistency.
 */

export interface AlertData {
  id: string;
  patientId: string;
  type: 'vital' | 'arrhythmia' | 'device' | 'system';
  severity: 'critical' | 'high' | 'medium' | 'low';
  status: 'active' | 'acknowledged' | 'resolved';
  message: string;
  timestamp: string;
  vitalType?: string;
  vitalValue?: number;
  thresholdValue?: number;
  source?: string;
  isAcknowledged?: boolean;
}

export interface DisplayAlert extends AlertData {
  severityClass: string;
  severityIcon: string;
  formattedTimestamp: string;
  priorityScore: number;
}

export class AlertProcessor {
  /**
   * Format alert for UI display with styling and icons
   */
  static formatAlertForDisplay(alert: AlertData): DisplayAlert {
    return {
      ...alert,
      severityClass: this.getSeverityClass(alert.severity),
      severityIcon: this.getSeverityIcon(alert.severity),
      formattedTimestamp: this.formatTimestamp(alert.timestamp),
      priorityScore: this.calculatePriority(alert)
    };
  }

  /**
   * Format multiple alerts for display
   */
  static formatAlertsForDisplay(alerts: AlertData[]): DisplayAlert[] {
    return alerts.map(alert => this.formatAlertForDisplay(alert));
  }

  /**
   * Get Tailwind CSS class for alert severity
   */
  static getSeverityClass(severity: string): string {
    const severityMap: Record<string, string> = {
      'critical': 'bg-red-500 text-white border-red-600',
      'high': 'bg-orange-500 text-white border-orange-600',
      'medium': 'bg-yellow-500 text-black border-yellow-600',
      'low': 'bg-blue-500 text-white border-blue-600'
    };
    return severityMap[severity] || 'bg-gray-500 text-white border-gray-600';
  }

  /**
   * Get icon name for alert severity
   */
  static getSeverityIcon(severity: string): string {
    const iconMap: Record<string, string> = {
      'critical': '🚨',
      'high': '⚠️',
      'medium': '⚡',
      'low': 'ℹ️'
    };
    return iconMap[severity] || '📌';
  }

  /**
   * Format timestamp for display (e.g., "2 minutes ago")
   */
  static formatTimestamp(timestamp: string): string {
    const now = Date.now();
    const alertTime = new Date(timestamp).getTime();
    const diffSeconds = Math.floor((now - alertTime) / 1000);

    if (diffSeconds < 60) {
      return 'Just now';
    } else if (diffSeconds < 3600) {
      const minutes = Math.floor(diffSeconds / 60);
      return `${minutes} min${minutes !== 1 ? 's' : ''} ago`;
    } else if (diffSeconds < 86400) {
      const hours = Math.floor(diffSeconds / 3600);
      return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
    } else {
      const days = Math.floor(diffSeconds / 86400);
      return `${days} day${days !== 1 ? 's' : ''} ago`;
    }
  }

  /**
   * Calculate priority score for sorting (higher = more urgent)
   * Critical = 4, High = 3, Medium = 2, Low = 1
   * Active status gets +0.5 bonus
   */
  static calculatePriority(alert: AlertData): number {
    const severityScores: Record<string, number> = {
      'critical': 4,
      'high': 3,
      'medium': 2,
      'low': 1
    };

    let score = severityScores[alert.severity] || 0;

    // Active alerts get priority boost
    if (alert.status === 'active') {
      score += 0.5;
    }

    return score;
  }

  /**
   * Group alerts by patient ID
   */
  static groupAlertsByPatient(alerts: AlertData[]): Map<string, AlertData[]> {
    const grouped = new Map<string, AlertData[]>();

    for (const alert of alerts) {
      const patientAlerts = grouped.get(alert.patientId) || [];
      patientAlerts.push(alert);
      grouped.set(alert.patientId, patientAlerts);
    }

    // Sort each patient's alerts by priority
    for (const [patientId, patientAlerts] of grouped.entries()) {
      grouped.set(
        patientId,
        this.sortAlertsByPriority(patientAlerts)
      );
    }

    return grouped;
  }

  /**
   * Sort alerts by priority (highest first), then by timestamp (newest first)
   */
  static sortAlertsByPriority(alerts: AlertData[]): AlertData[] {
    return [...alerts].sort((a, b) => {
      // First sort by priority score
      const priorityDiff = this.calculatePriority(b) - this.calculatePriority(a);
      if (priorityDiff !== 0) return priorityDiff;

      // If same priority, sort by timestamp (newest first)
      const timeA = new Date(a.timestamp).getTime();
      const timeB = new Date(b.timestamp).getTime();
      return timeB - timeA;
    });
  }

  /**
   * Filter alerts by status
   */
  static filterByStatus(
    alerts: AlertData[],
    status: 'active' | 'acknowledged' | 'resolved'
  ): AlertData[] {
    return alerts.filter(alert => alert.status === status);
  }

  /**
   * Filter alerts by severity
   */
  static filterBySeverity(
    alerts: AlertData[],
    minSeverity: 'critical' | 'high' | 'medium' | 'low'
  ): AlertData[] {
    const severityOrder = ['low', 'medium', 'high', 'critical'];
    const minIndex = severityOrder.indexOf(minSeverity);

    return alerts.filter(alert => {
      const alertIndex = severityOrder.indexOf(alert.severity);
      return alertIndex >= minIndex;
    });
  }

  /**
   * Get count of active alerts by severity
   */
  static getAlertCounts(alerts: AlertData[]): {
    critical: number;
    high: number;
    medium: number;
    low: number;
    total: number;
  } {
    const active = this.filterByStatus(alerts, 'active');

    return {
      critical: active.filter(a => a.severity === 'critical').length,
      high: active.filter(a => a.severity === 'high').length,
      medium: active.filter(a => a.severity === 'medium').length,
      low: active.filter(a => a.severity === 'low').length,
      total: active.length
    };
  }

  /**
   * Check if alert is stale (older than threshold)
   */
  static isStale(alert: AlertData, thresholdMinutes: number = 60): boolean {
    const now = Date.now();
    const alertTime = new Date(alert.timestamp).getTime();
    const ageMinutes = (now - alertTime) / (1000 * 60);
    return ageMinutes > thresholdMinutes;
  }

  /**
   * Get alert message with context
   */
  static getDetailedMessage(alert: AlertData): string {
    let message = alert.message;

    if (alert.vitalType && alert.vitalValue !== undefined) {
      message += ` (${alert.vitalType}: ${alert.vitalValue}`;
      if (alert.thresholdValue !== undefined) {
        message += `, threshold: ${alert.thresholdValue}`;
      }
      message += ')';
    }

    if (alert.source) {
      message += ` [Source: ${alert.source}]`;
    }

    return message;
  }
}
