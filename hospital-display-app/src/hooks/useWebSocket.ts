/**
 * useWebSocket - React hook for WebSocket integration
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data fields
 *
 * Provides React components with WebSocket messaging capabilities
 * Handles connection lifecycle, message subscription, and cleanup
 *
 * Usage:
 *   const { subscribe, unsubscribe, connectionState, isConnected } = useWebSocket();
 *   useEffect(() => {
 *     const id = subscribe((message) => { ... }, patientId);
 *     return () => unsubscribe(id);
 *   }, [patientId]);
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import WebSocketService from '../services/WebSocketService';
import { logger } from '../utils/logger';

interface WebSocketMessage {
  type: 'vitalsUpdate' | 'alert' | 'waveformStream' | 'connectionStatus' | 'error';
  patientId?: string;
  deviceId?: string;
  timestamp?: string;
  vitals?: any;
  alert?: any;
  waveform?: any;
  data?: any;
  message?: string;
}

type ConnectionState = 'connecting' | 'connected' | 'disconnected';

interface UseWebSocketReturn {
  subscribe: (callback: (message: WebSocketMessage) => void, patientId?: string, triggerCalibration?: boolean) => string;
  unsubscribe: (subscriberId: string) => void;
  connectionState: ConnectionState;
  isConnected: boolean;
}

export const useWebSocket = (): UseWebSocketReturn => {
  const wsService = useRef(WebSocketService.getInstance());
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');

  // Monitor connection state
  useEffect(() => {
    const checkConnection = setInterval(() => {
      const state = wsService.current.getConnectionState();
      setConnectionState(state);
    }, 1000);

    return () => clearInterval(checkConnection);
  }, []);

  /**
   * Subscribe to WebSocket messages
   * Returns subscriber ID for later unsubscription
   *
   * FIXED: Use crypto.randomUUID() for guaranteed unique IDs
   * Previous bug: counter + timestamp could collide if multiple components mounted simultaneously
   */
  const subscribe = useCallback((
    callback: (message: WebSocketMessage) => void,
    patientId?: string,
    triggerCalibration?: boolean
  ): string => {
    const subscriberId = crypto.randomUUID();
    logger.log('🔵 [DEBUG] useWebSocket subscribe() called:', { subscriberId, patientId, triggerCalibration });
    wsService.current.subscribe(subscriberId, callback, patientId, triggerCalibration);
    logger.log('🔵 [DEBUG] useWebSocket subscribe() completed for:', subscriberId);
    return subscriberId;
  }, []);

  /**
   * Unsubscribe from WebSocket messages
   */
  const unsubscribe = useCallback((subscriberId: string): void => {
    logger.log('🔵 [DEBUG] useWebSocket unsubscribe() called for:', subscriberId);
    wsService.current.unsubscribe(subscriberId);
    logger.log('🔵 [DEBUG] useWebSocket unsubscribe() completed for:', subscriberId);
  }, []);

  const isConnected = connectionState === 'connected';

  return {
    subscribe,
    unsubscribe,
    connectionState,
    isConnected
  };
};
