/**
 * useRealtimeAlerts - React hook for real-time patient alerts via WebSocket
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data fields
 *
 * Subscribes to WebSocket alert messages and maintains real-time alert state
 * Alerts are prepended to the list (newest first) and de-duplicated by ID
 *
 * Usage:
 *   const { alerts, addAlert } = useRealtimeAlerts(patientId, initialAlerts);
 */

import { useState, useEffect, useCallback } from 'react';
import { useWebSocket } from './useWebSocket';
import { alert } from '../types/PatientTypes';
import { logger } from '../utils/logger';

interface UseRealtimeAlertsReturn {
  alerts: alert[];
  addAlert: (alert: alert) => void;
  clearAlerts: () => void;
}

export const useRealtimeAlerts = (
  patientId: string | undefined,
  initialAlerts?: alert[]
): UseRealtimeAlertsReturn => {
  const { subscribe, unsubscribe, isConnected } = useWebSocket();
  const [alerts, setAlerts] = useState<alert[]>(initialAlerts || []);

  // Add alert to list (de-duplicate by ID)
  const addAlert = useCallback((alert: alert) => {
    setAlerts(prevAlerts => {
      // Check if alert already exists
      const exists = prevAlerts.some(a => a.id === alert.id);
      if (exists) {
        logger.log('⚠️ Alert already exists, skipping:', alert.id);
        return prevAlerts;
      }

      // Add new alert to the beginning (newest first)
      logger.log('🚨 Adding new alert:', alert);
      return [alert, ...prevAlerts];
    });
  }, []);

  // Clear all alerts
  const clearAlerts = useCallback(() => {
    setAlerts([]);
  }, []);

  // Subscribe to WebSocket alert messages
  useEffect(() => {
    if (!patientId) {
      return;
    }

    logger.log(`📡 Subscribing to alerts for patient: ${patientId}`);

    // Subscribe to ALL messages for this patient
    const subscriberId = subscribe((message) => {
      // Handle alert messages
      if (message.type === 'alert' && message.patientId === patientId) {
        logger.log('🚨 WebSocket alert received:', message);

        if (message.alert) {
          // Transform backend alert to API alert type
          // Backend sends: { id, alertType, severity, message, source, alertTimestamp }
          // API expects: { id, message, type?, severity, timestamp, isAcknowledged }
          const transformedAlert: alert = {
            id: message.alert.id || crypto.randomUUID(),
            message: message.alert.message || 'Unknown alert',
            type: message.alert.alertType || 'unknown',
            severity: message.alert.severity || 'medium',
            timestamp: message.alert.alertTimestamp || message.timestamp || new Date().toISOString(),
            isAcknowledged: false
          };

          addAlert(transformedAlert);
        }
      }
    }, patientId);

    // Cleanup subscription on unmount or patientId change
    return () => {
      logger.log(`📡 Unsubscribing from alerts for patient: ${patientId}`);
      unsubscribe(subscriberId);
    };
  }, [patientId, subscribe, unsubscribe, addAlert]);

  // Update alerts when initialAlerts change (from API)
  useEffect(() => {
    if (initialAlerts && initialAlerts.length > 0) {
      setAlerts(initialAlerts);
    }
  }, [initialAlerts]);

  return {
    alerts,
    addAlert,
    clearAlerts
  };
};
