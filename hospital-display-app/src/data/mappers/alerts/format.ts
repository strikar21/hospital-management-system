/**
 * Format alert messages for display.
 */

import { AlertDomain } from './fromAPI';

const SEVERITY_ICONS = {
  low: 'ℹ️',
  medium: '⚠️',
  high: '🔴',
  critical: '🚨'
};

const SEVERITY_COLORS = {
  low: '#0EA5E9',      // blue-500
  medium: '#F59E0B',   // amber-500
  high: '#EF4444',     // red-500
  critical: '#DC2626'  // red-600
};

export function formatAlertMessage(alert: AlertDomain): string {
  /**
   * Format alert message with icon.
   *
   * @param alert - Alert domain model
   * @returns Formatted message
   *
   * @example
   * formatAlertMessage(alert) // "🔴 High Heart Rate: 125bpm"
   */
  const icon = SEVERITY_ICONS[alert.severity] || '⚠️';
  return `${icon} ${alert.message}`;
}

export function getAlertColor(severity: AlertDomain['severity']): string {
  /**
   * Get color code for alert severity.
   *
   * @param severity - Alert severity
   * @returns Hex color code
   */
  return SEVERITY_COLORS[severity] || SEVERITY_COLORS.medium;
}

export function getAlertIcon(severity: AlertDomain['severity']): string {
  /**
   * Get icon for alert severity.
   *
   * @param severity - Alert severity
   * @returns Icon emoji
   */
  return SEVERITY_ICONS[severity] || '⚠️';
}
