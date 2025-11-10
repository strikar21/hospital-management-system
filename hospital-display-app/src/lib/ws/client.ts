/**
 * WebSocket client with reconnection, heartbeat, and offline queue.
 */

import { EventEmitter } from 'events';
import { setupReconnect } from './reconnect';
import { setupHeartbeat } from './heartbeat';
import { MessageQueue } from './queue';

export type WSEventType =
  | 'vitalsUpdate'
  | 'waveformStream'
  | 'alert'
  | 'deviceStatus'
  | 'connect'
  | 'disconnect'
  | 'error';

export interface WSMessage {
  type: string;
  payload: any;
}

class WebSocketClient extends EventEmitter {
  private ws: WebSocket | null = null;
  private url: string;
  private queue: MessageQueue;
  private reconnectTimer: number | null = null;
  private heartbeatTimer: number | null = null;
  private reconnectAttempts: number = 0;
  private isManualDisconnect: boolean = false;

  constructor(url: string = 'ws://localhost:8001/api/v1/ws') {
    super();
    this.url = url;
    this.queue = new MessageQueue();
  }

  /**
   * Connect to WebSocket server.
   */
  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.warn('[WS] Already connected');
      return;
    }

    this.isManualDisconnect = false;
    this.createConnection();
  }

  /**
   * Disconnect from WebSocket server.
   */
  disconnect() {
    this.isManualDisconnect = true;
    this.cleanup();
  }

  /**
   * Send message to server.
   */
  send(type: string, payload: any) {
    const message: WSMessage = { type, payload };

    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      // Queue message for later
      this.queue.enqueue(message);
    }
  }

  /**
   * Subscribe to patient updates.
   */
  subscribeToPatient(patientId: string) {
    this.send('subscribe', { patientId });
  }

  /**
   * Unsubscribe from patient updates.
   */
  unsubscribeFromPatient(patientId: string) {
    this.send('unsubscribe', { patientId });
  }

  private createConnection() {
    try {
      // Add auth token to URL if available
      const token = localStorage.getItem('authToken');
      const wsUrl = token ? `${this.url}?token=${token}` : this.url;

      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
      this.ws.onerror = this.handleError.bind(this);
    } catch (error) {
      console.error('[WS] Connection failed:', error);
      this.scheduleReconnect();
    }
  }

  private handleOpen() {
    console.log('[WS] Connected');
    this.reconnectAttempts = 0;

    // Start heartbeat
    setupHeartbeat(this);

    // Flush queued messages
    this.flushQueue();

    // Emit connect event
    this.emit('connect');
  }

  private handleMessage(event: MessageEvent) {
    try {
      const message: WSMessage = JSON.parse(event.data);

      // Handle pong response (heartbeat)
      if (message.type === 'pong') {
        return;
      }

      // Emit message to listeners
      this.emit(message.type, message.payload);
    } catch (error) {
      console.error('[WS] Message parse error:', error);
    }
  }

  private handleClose() {
    console.log('[WS] Disconnected');

    this.cleanup();

    // Emit disconnect event
    this.emit('disconnect');

    // Reconnect if not manually disconnected
    if (!this.isManualDisconnect) {
      this.scheduleReconnect();
    }
  }

  private handleError(error: Event) {
    console.error('[WS] Error:', error);
    this.emit('error', error);
  }

  private scheduleReconnect() {
    setupReconnect(this);
  }

  private cleanup() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  private flushQueue() {
    while (!this.queue.isEmpty()) {
      const message = this.queue.dequeue();
      if (message) {
        this.ws?.send(JSON.stringify(message));
      }
    }
  }

  // Public getters for reconnect/heartbeat modules
  getWS(): WebSocket | null {
    return this.ws;
  }

  getReconnectAttempts(): number {
    return this.reconnectAttempts;
  }

  incrementReconnectAttempts() {
    this.reconnectAttempts++;
  }

  setReconnectTimer(timer: number) {
    this.reconnectTimer = timer;
  }

  setHeartbeatTimer(timer: number) {
    this.heartbeatTimer = timer;
  }
}

// Export singleton instance
export const wsClient = new WebSocketClient();
