/**
 * usePatientVitals - React hook for real-time patient vitals via WebSocket
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data fields
 *
 * Wrapper around useWebSocket specifically for vitals updates
 * Automatically subscribes to patient vitals and updates state in real-time
 *
 * Usage:
 *   const { vitals, lastUpdate, isConnected } = usePatientVitals(patientId);
 */

import { useState, useEffect, useCallback } from 'react';
import { useWebSocket } from './useWebSocket';

interface VitalsData {
  heartRate?: number;
  oxygenSaturation?: number;
  temperature?: number;
  respiratoryRate?: number;
  bloodPressureSystolic?: number;
  bloodPressureDiastolic?: number;
  ecgReading?: number;
  eegReading?: number;
}

interface UsePatientVitalsReturn {
  vitals: VitalsData | null;
  lastUpdate: string | null;
  isConnected: boolean;
}

export const usePatientVitals = (
  patientId: string | undefined,
  initialVitals?: VitalsData | null
): UsePatientVitalsReturn => {
  const { subscribe, unsubscribe, isConnected } = useWebSocket();
  // Lazy initializer - only runs ONCE on mount, prevents resetting to null on re-renders
  const [vitals, setVitals] = useState<VitalsData | null>(() => initialVitals || null);
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);

  useEffect(() => {
    if (!patientId) {
      setVitals(null);
      setLastUpdate(null);
      return;
    }

    // Subscribe to vitals updates for this patient
    const subscriberId = subscribe((message) => {
      if (message.type === 'vitalsUpdate' && message.patientId === patientId) {
        if (message.vitals) {
          setVitals(message.vitals);
          setLastUpdate(message.timestamp || new Date().toISOString());
        }
      }
    }, patientId);

    // Cleanup subscription on unmount or patientId change
    return () => {
      unsubscribe(subscriberId);
    };
  }, [patientId, subscribe, unsubscribe]);

  return {
    vitals,
    lastUpdate,
    isConnected
  };
};
