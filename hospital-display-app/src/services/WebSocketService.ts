/**
 * WebSocket service for real-time hospital data updates
 */

export interface WebSocketMessage {
  type: string;
  timestamp: string;
  patient_id?: string;
  [key: string]: any;
}

export interface VitalsUpdate {
  type: 'vitals_update';
  patient_id: string;
  device_id: string;
  timestamp: string;
  vitals: {
    heartRate?: number;
    bloodPressure?: { systolic: number; diastolic: number };
    temperature?: number;
    oxygenSaturation?: number;
    respiratoryRate?: number;
    ecg?: number;
    eeg?: number;
    bioimpedance?: number;
    tremor?: number;
  };
}

export interface MedicationUpdate {
  type: 'medication_update';
  patient_id: string;
  timestamp: string;
  medication: {
    medication_id: string;
    action: 'updated' | 'added' | 'deleted';
    updates?: any;
  };
}

export interface AlertMessage {
  type: 'alert';
  patient_id?: string;
  timestamp: string;
  alert: {
    severity: 'low' | 'medium' | 'high' | 'critical';
    message: string;
    source: string;
  };
}

type MessageHandler = (message: WebSocketMessage) => void;
type VitalsHandler = (update: VitalsUpdate) => void;
type MedicationHandler = (update: MedicationUpdate) => void;
type AlertHandler = (alert: AlertMessage) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private isManualDisconnect = false;
  private messageHandlers: Set<MessageHandler> = new Set();
  private vitalsHandlers: Set<VitalsHandler> = new Set();
  private medicationHandlers: Set<MedicationHandler> = new Set();
  private alertHandlers: Set<AlertHandler> = new Set();
  private subscribedPatients: Set<string> = new Set();
  
  private readonly baseUrl: string;
  private readonly maxReconnectAttempts = 10;
  private reconnectAttempts = 0;
  private reconnectDelay = 1000; // Start with 1 second
  
  constructor(baseUrl: string = 'ws://localhost:8001') {
    this.baseUrl = baseUrl;
  }
  
  /**
   * Connect to WebSocket server
   */
  async connect(userId: string, userRole: string): Promise<boolean> {
    return new Promise((resolve) => {
      try {
        this.isManualDisconnect = false;
        const wsUrl = `${this.baseUrl}/api/v1/ws/realtime?user_id=${userId}&user_role=${encodeURIComponent(userRole)}`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
          console.log('🔌 WebSocket connected to hospital system');
          this.reconnectAttempts = 0;
          this.reconnectDelay = 1000;
          
          // Re-subscribe to patients after reconnection
          this.resubscribeToPatients();
          
          resolve(true);
        };
        
        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (error) {
            console.error('❌ Failed to parse WebSocket message:', error);
          }
        };
        
        this.ws.onclose = (event) => {
          console.log('🔌 WebSocket disconnected:', event.code, event.reason);
          this.ws = null;
          
          if (!this.isManualDisconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect(userId, userRole);
          }
        };
        
        this.ws.onerror = (error) => {
          console.error('❌ WebSocket error:', error);
          resolve(false);
        };
        
        // Connection timeout
        setTimeout(() => {
          if (this.ws?.readyState !== WebSocket.OPEN) {
            console.error('❌ WebSocket connection timeout');
            this.ws?.close();
            resolve(false);
          }
        }, 5000);
        
      } catch (error) {
        console.error('❌ Failed to create WebSocket connection:', error);
        resolve(false);
      }
    });
  }
  
  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    this.isManualDisconnect = true;
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.ws) {
      this.ws.close(1000, 'Manual disconnect');
      this.ws = null;
    }
    
    this.subscribedPatients.clear();
    console.log('🔌 WebSocket manually disconnected');
  }
  
  /**
   * Check if WebSocket is connected
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
  
  /**
   * Send message to server
   */
  private sendMessage(message: any): boolean {
    if (!this.isConnected()) {
      console.warn('⚠️ Cannot send message: WebSocket not connected');
      return false;
    }
    
    try {
      this.ws!.send(JSON.stringify(message));
      return true;
    } catch (error) {
      console.error('❌ Failed to send WebSocket message:', error);
      return false;
    }
  }
  
  /**
   * Subscribe to patient-specific updates
   */
  subscribeToPatient(patientId: string): boolean {
    const success = this.sendMessage({
      type: 'subscribe_patient',
      patient_id: patientId
    });
    
    if (success) {
      this.subscribedPatients.add(patientId);
      console.log(`📡 Subscribed to patient updates: ${patientId}`);
    }
    
    return success;
  }
  
  /**
   * Unsubscribe from patient-specific updates
   */
  unsubscribeFromPatient(patientId: string): boolean {
    const success = this.sendMessage({
      type: 'unsubscribe_patient',
      patient_id: patientId
    });
    
    if (success) {
      this.subscribedPatients.delete(patientId);
      console.log(`📡 Unsubscribed from patient updates: ${patientId}`);
    }
    
    return success;
  }
  
  /**
   * Add message handler for all messages
   */
  addMessageHandler(handler: MessageHandler): void {
    this.messageHandlers.add(handler);
  }
  
  /**
   * Remove message handler
   */
  removeMessageHandler(handler: MessageHandler): void {
    this.messageHandlers.delete(handler);
  }
  
  /**
   * Add vitals update handler
   */
  addVitalsHandler(handler: VitalsHandler): void {
    this.vitalsHandlers.add(handler);
  }
  
  /**
   * Remove vitals update handler
   */
  removeVitalsHandler(handler: VitalsHandler): void {
    this.vitalsHandlers.delete(handler);
  }
  
  /**
   * Add medication update handler
   */
  addMedicationHandler(handler: MedicationHandler): void {
    this.medicationHandlers.add(handler);
  }
  
  /**
   * Remove medication update handler
   */
  removeMedicationHandler(handler: MedicationHandler): void {
    this.medicationHandlers.delete(handler);
  }
  
  /**
   * Add alert handler
   */
  addAlertHandler(handler: AlertHandler): void {
    this.alertHandlers.add(handler);
  }
  
  /**
   * Remove alert handler
   */
  removeAlertHandler(handler: AlertHandler): void {
    this.alertHandlers.delete(handler);
  }
  
  /**
   * Handle incoming WebSocket messages
   */
  private handleMessage(message: WebSocketMessage): void {
    // Call all general message handlers
    this.messageHandlers.forEach(handler => {
      try {
        handler(message);
      } catch (error) {
        console.error('❌ Message handler error:', error);
      }
    });
    
    // Handle specific message types
    switch (message.type) {
      case 'vitals_update':
        this.vitalsHandlers.forEach(handler => {
          try {
            handler(message as VitalsUpdate);
          } catch (error) {
            console.error('❌ Vitals handler error:', error);
          }
        });
        break;
        
      case 'medication_update':
        this.medicationHandlers.forEach(handler => {
          try {
            handler(message as MedicationUpdate);
          } catch (error) {
            console.error('❌ Medication handler error:', error);
          }
        });
        break;
        
      case 'alert':
        this.alertHandlers.forEach(handler => {
          try {
            handler(message as AlertMessage);
          } catch (error) {
            console.error('❌ Alert handler error:', error);
          }
        });
        break;
        
      case 'connection_established':
        console.log('✅ WebSocket connection confirmed:', message.message);
        break;
        
      case 'subscription_result':
        if (message.success) {
          console.log(`✅ ${message.action}: ${message.message}`);
        } else {
          console.warn(`⚠️ ${message.action} failed: ${message.message}`);
        }
        break;
        
      case 'ping':
        // Respond to keepalive ping
        this.sendMessage({ type: 'pong' });
        break;
        
      case 'error':
        console.error('❌ WebSocket error from server:', message.message);
        break;
        
      default:
        console.log('📨 Unhandled WebSocket message:', message);
    }
  }
  
  /**
   * Schedule reconnection attempt
   */
  private scheduleReconnect(userId: string, userRole: string): void {
    this.reconnectAttempts++;
    
    console.log(`🔄 Scheduling WebSocket reconnection attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${this.reconnectDelay}ms`);
    
    this.reconnectTimer = setTimeout(async () => {
      const success = await this.connect(userId, userRole);
      
      if (!success) {
        // Exponential backoff with jitter
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000) + Math.random() * 1000;
        
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect(userId, userRole);
        } else {
          console.error('❌ Max WebSocket reconnection attempts reached');
        }
      }
    }, this.reconnectDelay);
  }
  
  /**
   * Re-subscribe to all previously subscribed patients
   */
  private resubscribeToPatients(): void {
    this.subscribedPatients.forEach(patientId => {
      this.sendMessage({
        type: 'subscribe_patient',
        patient_id: patientId
      });
    });
  }
  
  /**
   * Get connection status
   */
  getStatus(): { connected: boolean; reconnectAttempts: number; subscribedPatients: string[] } {
    return {
      connected: this.isConnected(),
      reconnectAttempts: this.reconnectAttempts,
      subscribedPatients: Array.from(this.subscribedPatients)
    };
  }
}

// Export singleton instance
export const webSocketService = new WebSocketService();
export default webSocketService;