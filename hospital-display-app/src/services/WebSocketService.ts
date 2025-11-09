/**
 * WebSocketService - Singleton WebSocket connection manager
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data fields
 *
 * Manages single WebSocket connection to backend for real-time vitals, alerts, and waveforms
 * Backend endpoint: wss://localhost:8001/api/v1/ws/realtime?token={jwt}
 *
 * Features:
 * - Singleton pattern (one connection per app)
 * - Auto-reconnect with exponential backoff
 * - Message routing to subscribed components
 * - Patient subscription management
 * - Connection state tracking
 */

import SecureStorage from '../utils/secureStorage';
import { getWsUrl } from '../config/apiConfig';

type ConnectionState = 'connecting' | 'connected' | 'disconnected';

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

interface MessageSubscriber {
  id: string;
  patientId?: string;
  callback: (message: WebSocketMessage) => void;
}

class WebSocketService {
  private static instance: WebSocketService | null = null;
  private ws: WebSocket | null = null;
  private connectionState: ConnectionState = 'disconnected';
  private subscribers: MessageSubscriber[] = [];
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectDelay = 1000; // Start at 1 second
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private subscribedPatients: Set<string> = new Set();
  private pendingCalibrationRequests: Set<string> = new Set();

  private constructor() {
    // Singleton - private constructor
  }

  /**
   * Get singleton instance
   */
  public static getInstance(): WebSocketService {
    if (!WebSocketService.instance) {
      WebSocketService.instance = new WebSocketService();
    }
    return WebSocketService.instance;
  }

  /**
   * Connect to WebSocket server
   */
  public async connect(): Promise<boolean> {
    if (this.connectionState === 'connected' || this.connectionState === 'connecting') {
      return true;
    }

    try {
      this.connectionState = 'connecting';
      const token = await SecureStorage.getToken();

      if (!token) {
        console.error('Cannot connect WebSocket: No auth token available');
        this.connectionState = 'disconnected';
        return false;
      }

      const wsUrl = `${getWsUrl('/realtime')}?token=${encodeURIComponent(token)}`;
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.connectionState = 'connected';
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        this.startHeartbeat();

        // Resubscribe to all patients after reconnect
        this.resubscribePatients();
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          // console.log('🔵 [DEBUG] WebSocket message received:', {
          //   type: message.type,
          //   patientId: message.patientId,
          //   deviceId: message.deviceId,
          //   hasVitals: !!message.vitals,
          //   vitalsData: message.vitals
          // });
          this.routeMessage(message);
        } catch (error) {
          console.error('❌ Failed to parse WebSocket message:', error);
          console.error('Raw message data:', event.data?.substring(0, 500));
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      this.ws.onclose = (event) => {
        this.connectionState = 'disconnected';
        this.stopHeartbeat();

        // Auto-reconnect if not a clean close
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect();
        }
      };

      return true;
    } catch (error) {
      console.error('WebSocket connection failed:', error);
      this.connectionState = 'disconnected';
      return false;
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  public disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    this.stopHeartbeat();

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }

    this.connectionState = 'disconnected';
    this.subscribers = [];
    this.subscribedPatients.clear();
    this.pendingCalibrationRequests.clear();
  }

  /**
   * Subscribe to WebSocket messages
   */
  public subscribe(subscriberId: string, callback: (message: WebSocketMessage) => void, patientId?: string, triggerWaveformCalibration?: boolean): void {
    // Remove existing subscription with same ID
    this.subscribers = this.subscribers.filter(sub => sub.id !== subscriberId);

    // Add new subscription
    this.subscribers.push({
      id: subscriberId,
      patientId,
      callback
    });

    // Subscribe to patient updates on backend
    if (patientId && !this.subscribedPatients.has(patientId)) {
      this.subscribeToPatient(patientId, triggerWaveformCalibration);
    } else if (patientId && triggerWaveformCalibration) {
      // Already subscribed, but still send waveform calibration trigger
      this.requestWaveformCalibration(patientId);
    }
  }

  /**
   * Unsubscribe from WebSocket messages
   */
  public unsubscribe(subscriberId: string): void {
    const subscriber = this.subscribers.find(sub => sub.id === subscriberId);

    // Check if this was the last subscriber for a patient
    if (subscriber?.patientId) {
      const otherSubs = this.subscribers.filter(
        sub => sub.id !== subscriberId && sub.patientId === subscriber.patientId
      );

      // If no other subscribers for this patient, unsubscribe from backend
      if (otherSubs.length === 0) {
        this.unsubscribeFromPatient(subscriber.patientId);
      }
    }

    this.subscribers = this.subscribers.filter(sub => sub.id !== subscriberId);
  }

  /**
   * Get current connection state
   */
  public getConnectionState(): ConnectionState {
    return this.connectionState;
  }

  /**
   * Check if connected
   */
  public isConnected(): boolean {
    return this.connectionState === 'connected' && this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Subscribe to patient updates on backend
   * Queues subscription if not connected - will be sent when connection establishes
   */
  private subscribeToPatient(patientId: string, triggerWaveformCalibration?: boolean): void {
    // Always add to subscribed set (queue for when connected)
    this.subscribedPatients.add(patientId);

    // If not connected, subscription will be processed by resubscribePatients() on connect
    if (!this.isConnected()) {
      return;
    }

    // Connected - send subscription message immediately
    const message = {
      type: 'subscribePatient',
      patientId,
      ...(triggerWaveformCalibration && { triggerWaveformCalibration: true })
    };

    this.ws?.send(JSON.stringify(message));
  }

  /**
   * Request waveform calibration for a patient
   * Queues the request if not connected - will be sent when connection establishes
   */
  private requestWaveformCalibration(patientId: string): void {
    if (!this.isConnected()) {
      this.pendingCalibrationRequests.add(patientId);
      return;
    }

    const message = {
      type: 'subscribePatient',
      patientId,
      triggerWaveformCalibration: true
    };

    const messageStr = JSON.stringify(message);
    this.ws?.send(messageStr);
    this.pendingCalibrationRequests.delete(patientId);
  }

  /**
   * Unsubscribe from patient updates on backend
   */
  private unsubscribeFromPatient(patientId: string): void {
    if (!this.isConnected()) {
      return;
    }

    const message = {
      type: 'unsubscribePatient',
      patientId
    };

    this.ws?.send(JSON.stringify(message));
    this.subscribedPatients.delete(patientId);
  }

  /**
   * Resubscribe to all patients after reconnect
   */
  private resubscribePatients(): void {
    this.subscribedPatients.forEach(patientId => {
      const message = {
        type: 'subscribePatient',
        patientId
      };
      this.ws?.send(JSON.stringify(message));
    });

    if (this.subscribedPatients.size > 0) {
    }

    // Send all pending calibration requests
    if (this.pendingCalibrationRequests.size > 0) {
      const count = this.pendingCalibrationRequests.size;
      this.pendingCalibrationRequests.forEach(patientId => {
        this.requestWaveformCalibration(patientId);
      });
    }
  }

  /**
   * Route incoming message to subscribers
   */
  private routeMessage(message: WebSocketMessage): void {
    // console.log('🟢 [DEBUG] Routing message to subscribers:', {
    //   totalSubscribers: this.subscribers.length,
    //   messageType: message.type,
    //   messagePatientId: message.patientId,
    //   subscribers: this.subscribers.map(s => ({ id: s.id, patientId: s.patientId }))
    // });

    let routed = 0;
    // Route to all subscribers
    this.subscribers.forEach(subscriber => {
      // If subscriber has patientId filter, only send matching messages
      if (subscriber.patientId) {
        if (message.patientId === subscriber.patientId) {
          // console.log(`🟢 [DEBUG] Routing to subscriber ${subscriber.id} (patient match: ${subscriber.patientId})`);
          subscriber.callback(message);
          routed++;
        }
      } else {
        // No filter - send all messages
        // console.log(`🟢 [DEBUG] Routing to subscriber ${subscriber.id} (no filter)`);
        subscriber.callback(message);
        routed++;
      }
    });

    // console.log(`🟢 [DEBUG] Message routed to ${routed} subscribers`);
  }

  /**
   * Schedule reconnect with exponential backoff
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    this.reconnectAttempts++;
    const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000);


    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * Start heartbeat to keep connection alive
   */
  private startHeartbeat(): void {
    this.stopHeartbeat();

    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected()) {
        this.ws?.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000); // Ping every 30 seconds
  }

  /**
   * Stop heartbeat
   */
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }
}

export default WebSocketService;
