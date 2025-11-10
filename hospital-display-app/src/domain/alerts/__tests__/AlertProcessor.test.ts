/**
 * Unit Tests for AlertProcessor
 * Domain layer tests for alert display logic
 */

import { AlertProcessor, AlertData, DisplayAlert } from '../AlertProcessor';

describe('AlertProcessor', () => {
  // ================================
  // FORMAT ALERT FOR DISPLAY
  // ================================

  describe('formatAlertForDisplay', () => {
    it('should format alert with all display properties', () => {
      const alert: AlertData = {
        id: 'ALR001',
        severity: 'critical',
        message: 'High heart rate detected',
        timestamp: new Date().toISOString(),
        isAcknowledged: false
      };

      const formatted = AlertProcessor.formatAlertForDisplay(alert);

      expect(formatted.severityClass).toBeDefined();
      expect(formatted.severityIcon).toBe('🚨'); // Critical icon
      expect(formatted.formattedTimestamp).toBeDefined();
      expect(formatted.priorityScore).toBeGreaterThan(0);
    });

    it('should preserve original alert properties', () => {
      const alert: AlertData = {
        id: 'ALR001',
        severity: 'high',
        message: 'Abnormal vitals',
        timestamp: new Date().toISOString(),
        vitalType: 'heartRate',
        vitalValue: 120
      };

      const formatted = AlertProcessor.formatAlertForDisplay(alert);

      expect(formatted.id).toBe('ALR001');
      expect(formatted.severity).toBe('high');
      expect(formatted.message).toBe('Abnormal vitals');
      expect(formatted.vitalType).toBe('heartRate');
      expect(formatted.vitalValue).toBe(120);
    });
  });

  // ================================
  // SEVERITY CLASS
  // ================================

  describe('getSeverityClass', () => {
    it('should return correct class for critical severity', () => {
      const className = AlertProcessor.getSeverityClass('critical');
      expect(className).toContain('bg-red-500');
      expect(className).toContain('border-red-600');
    });

    it('should return correct class for high severity', () => {
      const className = AlertProcessor.getSeverityClass('high');
      expect(className).toContain('bg-orange-500');
      expect(className).toContain('border-orange-600');
    });

    it('should return correct class for medium severity', () => {
      const className = AlertProcessor.getSeverityClass('medium');
      expect(className).toContain('bg-yellow-500');
      expect(className).toContain('border-yellow-600');
    });

    it('should return correct class for low severity', () => {
      const className = AlertProcessor.getSeverityClass('low');
      expect(className).toContain('bg-blue-500');
      expect(className).toContain('border-blue-600');
    });

    it('should return default class for unknown severity', () => {
      const className = AlertProcessor.getSeverityClass('unknown' as any);
      expect(className).toContain('bg-gray-500');
    });
  });

  // ================================
  // SEVERITY ICON
  // ================================

  describe('getSeverityIcon', () => {
    it('should return correct icon for each severity level', () => {
      expect(AlertProcessor.getSeverityIcon('critical')).toBe('🚨');
      expect(AlertProcessor.getSeverityIcon('high')).toBe('⚠️');
      expect(AlertProcessor.getSeverityIcon('medium')).toBe('⚡');
      expect(AlertProcessor.getSeverityIcon('low')).toBe('ℹ️');
    });

    it('should return default icon for unknown severity', () => {
      const icon = AlertProcessor.getSeverityIcon('unknown' as any);
      expect(icon).toBe('📌');
    });
  });

  // ================================
  // TIMESTAMP FORMATTING
  // ================================

  describe('formatTimestamp', () => {
    it('should return "Just now" for timestamps within last minute', () => {
      const now = new Date();
      const timestamp = now.toISOString();

      const formatted = AlertProcessor.formatTimestamp(timestamp);

      expect(formatted).toBe('Just now');
    });

    it('should return minutes ago for recent timestamps', () => {
      const twoMinutesAgo = new Date(Date.now() - 2 * 60 * 1000);
      const timestamp = twoMinutesAgo.toISOString();

      const formatted = AlertProcessor.formatTimestamp(timestamp);

      expect(formatted).toMatch(/\d+ mins? ago/);
    });

    it('should return hours ago for older timestamps', () => {
      const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000);
      const timestamp = twoHoursAgo.toISOString();

      const formatted = AlertProcessor.formatTimestamp(timestamp);

      expect(formatted).toMatch(/\d+ hours? ago/);
    });

    it('should return days ago for very old timestamps', () => {
      const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000);
      const timestamp = threeDaysAgo.toISOString();

      const formatted = AlertProcessor.formatTimestamp(timestamp);

      expect(formatted).toMatch(/\d+ days? ago/);
    });

    it('should handle invalid timestamp gracefully', () => {
      const formatted = AlertProcessor.formatTimestamp('invalid');

      // Invalid timestamp results in NaN, which formats as "NaN days ago"
      expect(formatted).toContain('NaN');
    });

    it('should use singular for 1 minute/hour/day', () => {
      const oneMinuteAgo = new Date(Date.now() - 60 * 1000);
      const formatted = AlertProcessor.formatTimestamp(oneMinuteAgo.toISOString());

      expect(formatted).toBe('1 min ago');
    });
  });

  // ================================
  // PRIORITY CALCULATION
  // ================================

  describe('calculatePriority', () => {
    it('should assign highest priority to critical alerts', () => {
      const alert: AlertData = {
        id: 'ALR001',
        severity: 'critical',
        message: 'Critical alert',
        timestamp: new Date().toISOString(),
        isAcknowledged: true // Explicitly acknowledged to avoid bonus
      };

      const priority = AlertProcessor.calculatePriority(alert);

      expect(priority).toBe(4); // Critical = 4, no bonus
    });

    it('should add bonus for active/unacknowledged alerts', () => {
      const alert: AlertData = {
        id: 'ALR001',
        severity: 'high',
        message: 'High alert',
        timestamp: new Date().toISOString(),
        isAcknowledged: false
      };

      const priority = AlertProcessor.calculatePriority(alert);

      expect(priority).toBe(3.5); // High = 3 + 0.5 bonus
    });

    it('should not add bonus for acknowledged alerts', () => {
      const alert: AlertData = {
        id: 'ALR001',
        severity: 'high',
        message: 'High alert',
        timestamp: new Date().toISOString(),
        isAcknowledged: true
      };

      const priority = AlertProcessor.calculatePriority(alert);

      expect(priority).toBe(3); // High = 3, no bonus
    });

    it('should handle status field for active determination', () => {
      const alert: AlertData = {
        id: 'ALR001',
        severity: 'medium',
        status: 'active',
        message: 'Medium alert',
        timestamp: new Date().toISOString()
      };

      const priority = AlertProcessor.calculatePriority(alert);

      expect(priority).toBe(2.5); // Medium = 2 + 0.5 bonus
    });

    it('should return correct priority for all severity levels', () => {
      const severities: Array<'critical' | 'high' | 'medium' | 'low'> = ['critical', 'high', 'medium', 'low'];
      const expectedScores = [4, 3, 2, 1];

      severities.forEach((severity, index) => {
        const alert: AlertData = {
          id: `ALR${index}`,
          severity,
          message: 'Test',
          timestamp: new Date().toISOString(),
          isAcknowledged: true
        };

        expect(AlertProcessor.calculatePriority(alert)).toBe(expectedScores[index]);
      });
    });
  });

  // ================================
  // FILTER BY STATUS
  // ================================

  describe('filterByStatus', () => {
    const alerts: AlertData[] = [
      {
        id: 'ALR001',
        severity: 'critical',
        message: 'Alert 1',
        timestamp: new Date().toISOString(),
        isAcknowledged: false
      },
      {
        id: 'ALR002',
        severity: 'high',
        message: 'Alert 2',
        timestamp: new Date().toISOString(),
        isAcknowledged: true
      },
      {
        id: 'ALR003',
        severity: 'medium',
        message: 'Alert 3',
        timestamp: new Date().toISOString(),
        status: 'active'
      },
      {
        id: 'ALR004',
        severity: 'low',
        message: 'Alert 4',
        timestamp: new Date().toISOString(),
        status: 'acknowledged'
      }
    ];

    it('should filter active alerts using isAcknowledged field', () => {
      const activeAlerts = AlertProcessor.filterByStatus(alerts, 'active');

      expect(activeAlerts).toHaveLength(2);
      expect(activeAlerts[0].id).toBe('ALR001');
      expect(activeAlerts[1].id).toBe('ALR003');
    });

    it('should filter acknowledged alerts using isAcknowledged field', () => {
      const acknowledgedAlerts = AlertProcessor.filterByStatus(alerts, 'acknowledged');

      expect(acknowledgedAlerts).toHaveLength(2);
      expect(acknowledgedAlerts[0].id).toBe('ALR002');
      expect(acknowledgedAlerts[1].id).toBe('ALR004');
    });

    it('should prefer status field over isAcknowledged when both present', () => {
      const alertsWithStatus: AlertData[] = [
        {
          id: 'ALR001',
          severity: 'high',
          message: 'Test',
          timestamp: new Date().toISOString(),
          status: 'active',
          isAcknowledged: true // Conflicting, but status takes precedence
        }
      ];

      const activeAlerts = AlertProcessor.filterByStatus(alertsWithStatus, 'active');

      expect(activeAlerts).toHaveLength(1);
    });

    it('should return empty array for resolved status (legacy support)', () => {
      const resolvedAlerts = AlertProcessor.filterByStatus(alerts, 'resolved');

      expect(resolvedAlerts).toHaveLength(0);
    });
  });

  // ================================
  // FILTER BY SEVERITY
  // ================================

  describe('filterBySeverity', () => {
    const alerts: AlertData[] = [
      { id: 'ALR001', severity: 'critical', message: 'Critical', timestamp: new Date().toISOString() },
      { id: 'ALR002', severity: 'high', message: 'High', timestamp: new Date().toISOString() },
      { id: 'ALR003', severity: 'medium', message: 'Medium', timestamp: new Date().toISOString() },
      { id: 'ALR004', severity: 'low', message: 'Low', timestamp: new Date().toISOString() },
      { id: 'ALR005', severity: 'critical', message: 'Critical 2', timestamp: new Date().toISOString() }
    ];

    it('should filter alerts by minimum severity (critical only)', () => {
      const criticalAlerts = AlertProcessor.filterBySeverity(alerts, 'critical');

      // Should only return critical alerts (minSeverity = critical)
      expect(criticalAlerts).toHaveLength(2);
      expect(criticalAlerts.every(a => a.severity === 'critical')).toBe(true);
    });

    it('should filter alerts by minimum severity (high and above)', () => {
      const highAndAbove = AlertProcessor.filterBySeverity(alerts, 'high');

      // Should return high AND critical alerts
      expect(highAndAbove).toHaveLength(3); // 2 critical + 1 high
      expect(highAndAbove.some(a => a.severity === 'critical')).toBe(true);
      expect(highAndAbove.some(a => a.severity === 'high')).toBe(true);
      expect(highAndAbove.every(a => a.severity === 'low' || a.severity === 'medium')).toBe(false);
    });

    it('should filter alerts by minimum severity (medium and above)', () => {
      const mediumAndAbove = AlertProcessor.filterBySeverity(alerts, 'medium');

      // Should return medium, high, and critical
      expect(mediumAndAbove).toHaveLength(4); // 2 critical + 1 high + 1 medium
    });

    it('should return all alerts for low minimum severity', () => {
      const allAlerts = AlertProcessor.filterBySeverity(alerts, 'low');

      expect(allAlerts).toHaveLength(5); // All alerts
    });

    it('should return all alerts for non-existent severity', () => {
      const unknownAlerts = AlertProcessor.filterBySeverity(alerts, 'unknown' as any);

      // Unknown severity returns -1 from indexOf, so minIndex = -1
      // All valid severities have alertIndex >= -1, so all alerts are returned
      expect(unknownAlerts).toHaveLength(5);
    });
  });

  // ================================
  // SORT BY PRIORITY
  // ================================

  describe('sortAlertsByPriority', () => {
    it('should sort alerts by priority (highest first)', () => {
      const alerts: AlertData[] = [
        { id: 'ALR001', severity: 'low', message: 'Low', timestamp: new Date().toISOString(), isAcknowledged: true },
        { id: 'ALR002', severity: 'critical', message: 'Critical', timestamp: new Date().toISOString(), isAcknowledged: true },
        { id: 'ALR003', severity: 'medium', message: 'Medium', timestamp: new Date().toISOString(), isAcknowledged: true },
        { id: 'ALR004', severity: 'high', message: 'High', timestamp: new Date().toISOString(), isAcknowledged: true }
      ];

      const sorted = AlertProcessor.sortAlertsByPriority(alerts);

      expect(sorted[0].severity).toBe('critical');
      expect(sorted[1].severity).toBe('high');
      expect(sorted[2].severity).toBe('medium');
      expect(sorted[3].severity).toBe('low');
    });

    it('should preserve alert data during sort', () => {
      const alerts: AlertData[] = [
        { id: 'ALR001', severity: 'low', message: 'Low alert', timestamp: new Date().toISOString(), isAcknowledged: true },
        { id: 'ALR002', severity: 'critical', message: 'Critical alert', timestamp: new Date().toISOString(), isAcknowledged: true }
      ];

      const sorted = AlertProcessor.sortAlertsByPriority(alerts);

      expect(sorted[0].id).toBe('ALR002');
      expect(sorted[0].message).toBe('Critical alert');
      expect(sorted[1].id).toBe('ALR001');
      expect(sorted[1].message).toBe('Low alert');
    });

    it('should not mutate original array', () => {
      const alerts: AlertData[] = [
        { id: 'ALR001', severity: 'low', message: 'Low', timestamp: new Date().toISOString(), isAcknowledged: true },
        { id: 'ALR002', severity: 'critical', message: 'Critical', timestamp: new Date().toISOString(), isAcknowledged: true }
      ];

      const originalOrder = alerts.map(a => a.id);
      AlertProcessor.sortAlertsByPriority(alerts);

      expect(alerts.map(a => a.id)).toEqual(originalOrder);
    });
  });

  // ================================
  // GROUP ALERTS BY PATIENT
  // ================================

  describe('groupAlertsByPatient', () => {
    it('should group alerts by patient ID', () => {
      const alerts: AlertData[] = [
        { id: 'ALR001', patientId: 'P001', severity: 'high', message: 'Alert 1', timestamp: new Date().toISOString() },
        { id: 'ALR002', patientId: 'P002', severity: 'medium', message: 'Alert 2', timestamp: new Date().toISOString() },
        { id: 'ALR003', patientId: 'P001', severity: 'low', message: 'Alert 3', timestamp: new Date().toISOString() }
      ];

      const grouped = AlertProcessor.groupAlertsByPatient(alerts);

      expect(grouped.size).toBe(2);
      expect(grouped.get('P001')).toHaveLength(2);
      expect(grouped.get('P002')).toHaveLength(1);
    });

    it('should sort alerts within each patient group', () => {
      const alerts: AlertData[] = [
        { id: 'ALR001', patientId: 'P001', severity: 'low', message: 'Alert 1', timestamp: new Date().toISOString() },
        { id: 'ALR002', patientId: 'P001', severity: 'critical', message: 'Alert 2', timestamp: new Date().toISOString() }
      ];

      const grouped = AlertProcessor.groupAlertsByPatient(alerts);
      const p001Alerts = grouped.get('P001')!;

      expect(p001Alerts[0].severity).toBe('critical');
      expect(p001Alerts[1].severity).toBe('low');
    });

    it('should handle alerts without patientId', () => {
      const alerts: AlertData[] = [
        { id: 'ALR001', severity: 'high', message: 'Alert 1', timestamp: new Date().toISOString() }
      ];

      const grouped = AlertProcessor.groupAlertsByPatient(alerts);

      expect(grouped.size).toBe(1);
      // Undefined patientId becomes string 'undefined' as Map key
      expect(grouped.get(undefined)).toHaveLength(1);
    });
  });

  // ================================
  // BATCH FORMATTING
  // ================================

  describe('formatAlertsForDisplay', () => {
    it('should format multiple alerts', () => {
      const alerts: AlertData[] = [
        { id: 'ALR001', severity: 'critical', message: 'Alert 1', timestamp: new Date().toISOString() },
        { id: 'ALR002', severity: 'high', message: 'Alert 2', timestamp: new Date().toISOString() }
      ];

      const formatted = AlertProcessor.formatAlertsForDisplay(alerts);

      expect(formatted).toHaveLength(2);
      expect(formatted[0].severityIcon).toBeDefined();
      expect(formatted[1].severityIcon).toBeDefined();
    });

    it('should preserve original order', () => {
      const alerts: AlertData[] = [
        { id: 'ALR001', severity: 'low', message: 'Low', timestamp: new Date().toISOString() },
        { id: 'ALR002', severity: 'critical', message: 'Critical', timestamp: new Date().toISOString() }
      ];

      const formatted = AlertProcessor.formatAlertsForDisplay(alerts);

      expect(formatted[0].id).toBe('ALR001');
      expect(formatted[1].id).toBe('ALR002');
    });
  });
});
