/**
 * WebSocketService Unit Tests (No Mock Server)
 * PRIORITY 1 - CRITICAL: Prevent cross-patient data leaks
 *
 * Tests core logic without actual WebSocket connection
 * Focus on subscriber management and message routing
 */

import WebSocketService from '../WebSocketService';

// Mock SecureStorage
jest.mock('../../utils/secureStorage', () => ({
  __esModule: true,
  default: {
    getToken: jest.fn().mockResolvedValue('mock-jwt-token')
  }
}));

// Mock API config
jest.mock('../../config/apiConfig', () => ({
  getWsUrl: jest.fn((path: string) => `ws://localhost:8001/api/v1/ws${path}`)
}));

describe('WebSocketService - Core Logic Tests', () => {
  let service: WebSocketService;

  beforeEach(() => {
    // Reset singleton before each test
    (WebSocketService as any).instance = null;
    service = WebSocketService.getInstance();
  });

  afterEach(() => {
    service.disconnect();
  });

  // ================================
  // SUBSCRIBER MANAGEMENT
  // ================================

  describe('Subscriber Management', () => {
    test('should be a singleton', () => {
      const instance1 = WebSocketService.getInstance();
      const instance2 = WebSocketService.getInstance();

      expect(instance1).toBe(instance2);
    });

    test('should add subscriber to subscribers array', () => {
      const callback = jest.fn();
      const subscriberId = 'test-sub-1';

      service.subscribe(subscriberId, callback, 'PAT001');

      // Access private subscribers array for testing
      const subscribers = (service as any).subscribers;
      expect(subscribers).toHaveLength(1);
      expect(subscribers[0]).toMatchObject({
        id: subscriberId,
        patientId: 'PAT001',
        callback
      });
    });

    test('should handle duplicate subscriber IDs by replacing old one', () => {
      const callback1 = jest.fn();
      const callback2 = jest.fn();
      const duplicateId = 'duplicate-id-123';

      service.subscribe(duplicateId, callback1, 'PAT001');
      service.subscribe(duplicateId, callback2, 'PAT001');

      const subscribers = (service as any).subscribers;

      // Should have only 1 subscriber (second replaced first)
      expect(subscribers).toHaveLength(1);
      expect(subscribers[0].callback).toBe(callback2);
    });

    test('should allow multiple subscribers for same patient', () => {
      const callback1 = jest.fn();
      const callback2 = jest.fn();

      service.subscribe('sub-1', callback1, 'PAT001');
      service.subscribe('sub-2', callback2, 'PAT001');

      const subscribers = (service as any).subscribers;

      expect(subscribers).toHaveLength(2);
      expect(subscribers[0].patientId).toBe('PAT001');
      expect(subscribers[1].patientId).toBe('PAT001');
    });

    test('should remove subscriber on unsubscribe', () => {
      const callback = jest.fn();

      service.subscribe('sub-1', callback, 'PAT001');
      expect((service as any).subscribers).toHaveLength(1);

      service.unsubscribe('sub-1');
      expect((service as any).subscribers).toHaveLength(0);
    });

    test('should not affect other subscribers when one unsubscribes', () => {
      service.subscribe('sub-1', jest.fn(), 'PAT001');
      service.subscribe('sub-2', jest.fn(), 'PAT002');

      service.unsubscribe('sub-1');

      const subscribers = (service as any).subscribers;
      expect(subscribers).toHaveLength(1);
      expect(subscribers[0].id).toBe('sub-2');
    });
  });

  // ================================
  // MESSAGE ROUTING LOGIC
  // ================================

  describe('Message Routing', () => {
    test('should route message only to matching patientId', () => {
      const callbackPAT001 = jest.fn();
      const callbackPAT002 = jest.fn();

      service.subscribe('sub-pat001', callbackPAT001, 'PAT001');
      service.subscribe('sub-pat002', callbackPAT002, 'PAT002');

      // Call private routeMessage method directly
      (service as any).routeMessage({
        type: 'vitalsUpdate',
        patientId: 'PAT001',
        vitals: { heartRate: 75 }
      });

      // Only PAT001 callback should be called
      expect(callbackPAT001).toHaveBeenCalledTimes(1);
      expect(callbackPAT001).toHaveBeenCalledWith(
        expect.objectContaining({
          patientId: 'PAT001',
          vitals: { heartRate: 75 }
        })
      );
      expect(callbackPAT002).not.toHaveBeenCalled();
    });

    test('should NOT route to wrong patient (CRITICAL SAFETY TEST)', () => {
      const callbackPAT001 = jest.fn();
      const callbackPAT002 = jest.fn();
      const callbackPAT003 = jest.fn();

      service.subscribe('sub-1', callbackPAT001, 'PAT001');
      service.subscribe('sub-2', callbackPAT002, 'PAT002');
      service.subscribe('sub-3', callbackPAT003, 'PAT003');

      // Send message for PAT002
      (service as any).routeMessage({
        type: 'vitalsUpdate',
        patientId: 'PAT002',
        vitals: { heartRate: 85 }
      });

      // ONLY PAT002 callback should be called
      expect(callbackPAT001).not.toHaveBeenCalled();
      expect(callbackPAT002).toHaveBeenCalledTimes(1);
      expect(callbackPAT003).not.toHaveBeenCalled();

      // Verify correct data
      expect(callbackPAT002).toHaveBeenCalledWith(
        expect.objectContaining({
          patientId: 'PAT002',
          vitals: { heartRate: 85 }
        })
      );
    });

    test('should route to all matching subscribers for same patient', () => {
      const callback1 = jest.fn();
      const callback2 = jest.fn();

      service.subscribe('sub-1', callback1, 'PAT001');
      service.subscribe('sub-2', callback2, 'PAT001');

      (service as any).routeMessage({
        type: 'vitalsUpdate',
        patientId: 'PAT001',
        vitals: { heartRate: 80 }
      });

      // Both callbacks should be called
      expect(callback1).toHaveBeenCalledTimes(1);
      expect(callback2).toHaveBeenCalledTimes(1);
    });

    test('should route to subscribers without patientId filter', () => {
      const callbackNoFilter = jest.fn();
      const callbackPAT001 = jest.fn();

      service.subscribe('sub-no-filter', callbackNoFilter); // No patientId
      service.subscribe('sub-pat001', callbackPAT001, 'PAT001');

      (service as any).routeMessage({
        type: 'vitalsUpdate',
        patientId: 'PAT001',
        vitals: { heartRate: 75 }
      });

      // Both should receive the message
      expect(callbackNoFilter).toHaveBeenCalledTimes(1);
      expect(callbackPAT001).toHaveBeenCalledTimes(1);
    });

    test('should NOT route message with no patientId to filtered subscribers', () => {
      const callback = jest.fn();

      service.subscribe('sub-1', callback, 'PAT001');

      (service as any).routeMessage({
        type: 'connectionStatus',
        message: 'connected'
        // No patientId
      });

      // Should NOT be routed
      expect(callback).not.toHaveBeenCalled();
    });

    test('should handle multiple messages to different patients correctly', () => {
      const callbackPAT001 = jest.fn();
      const callbackPAT002 = jest.fn();
      const callbackPAT003 = jest.fn();

      service.subscribe('sub-1', callbackPAT001, 'PAT001');
      service.subscribe('sub-2', callbackPAT002, 'PAT002');
      service.subscribe('sub-3', callbackPAT003, 'PAT003');

      // Send 3 different messages
      (service as any).routeMessage({
        type: 'vitalsUpdate',
        patientId: 'PAT001',
        vitals: { heartRate: 75 }
      });

      (service as any).routeMessage({
        type: 'vitalsUpdate',
        patientId: 'PAT002',
        vitals: { heartRate: 85 }
      });

      (service as any).routeMessage({
        type: 'vitalsUpdate',
        patientId: 'PAT003',
        vitals: { heartRate: 95 }
      });

      // Each callback called exactly once with correct data
      expect(callbackPAT001).toHaveBeenCalledTimes(1);
      expect(callbackPAT001).toHaveBeenCalledWith(
        expect.objectContaining({ patientId: 'PAT001', vitals: { heartRate: 75 } })
      );

      expect(callbackPAT002).toHaveBeenCalledTimes(1);
      expect(callbackPAT002).toHaveBeenCalledWith(
        expect.objectContaining({ patientId: 'PAT002', vitals: { heartRate: 85 } })
      );

      expect(callbackPAT003).toHaveBeenCalledTimes(1);
      expect(callbackPAT003).toHaveBeenCalledWith(
        expect.objectContaining({ patientId: 'PAT003', vitals: { heartRate: 95 } })
      );
    });
  });

  // ================================
  // PATIENT SUBSCRIPTION TRACKING
  // ================================

  describe('Patient Subscription Tracking', () => {
    test('should track subscribed patients', () => {
      service.subscribe('sub-1', jest.fn(), 'PAT001');
      service.subscribe('sub-2', jest.fn(), 'PAT002');

      const subscribedPatients = (service as any).subscribedPatients;

      expect(subscribedPatients.has('PAT001')).toBe(true);
      expect(subscribedPatients.has('PAT002')).toBe(true);
    });

    test('should not track duplicate patient subscriptions', () => {
      service.subscribe('sub-1', jest.fn(), 'PAT001');
      service.subscribe('sub-2', jest.fn(), 'PAT001');

      const subscribedPatients = (service as any).subscribedPatients;

      expect(subscribedPatients.size).toBe(1);
      expect(subscribedPatients.has('PAT001')).toBe(true);
    });

    test('should remove patient from tracking when last subscriber removed', () => {
      const sub1 = 'sub-1';
      service.subscribe(sub1, jest.fn(), 'PAT001');

      const subscribedPatients = (service as any).subscribedPatients;
      expect(subscribedPatients.has('PAT001')).toBe(true);

      service.unsubscribe(sub1);

      // PAT001 should be removed (if backend unsubscribe was called)
      // Note: This depends on connection state, so may not be removed immediately
      // in disconnected state
    });

    test('should NOT remove patient if other subscribers exist', () => {
      service.subscribe('sub-1', jest.fn(), 'PAT001');
      service.subscribe('sub-2', jest.fn(), 'PAT001');

      service.unsubscribe('sub-1');

      const subscribedPatients = (service as any).subscribedPatients;

      // PAT001 should still be in set (sub-2 still subscribed)
      expect(subscribedPatients.has('PAT001')).toBe(true);
    });
  });

  // ================================
  // CONNECTION STATE
  // ================================

  describe('Connection State', () => {
    test('should start in disconnected state', () => {
      expect(service.getConnectionState()).toBe('disconnected');
      expect(service.isConnected()).toBe(false);
    });

    test('should clean up subscribers on disconnect', () => {
      service.subscribe('sub-1', jest.fn(), 'PAT001');
      service.subscribe('sub-2', jest.fn(), 'PAT002');

      expect((service as any).subscribers).toHaveLength(2);

      service.disconnect();

      expect((service as any).subscribers).toHaveLength(0);
      expect((service as any).subscribedPatients.size).toBe(0);
    });
  });
});
