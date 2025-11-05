/**
 * WebSocketService Unit Tests
 * PRIORITY 1 - CRITICAL: Prevent cross-patient data leaks
 *
 * Tests subscriber management, message routing, and patient filtering
 * to ensure medical data goes to correct patient cards only.
 */

import WebSocketService from '../WebSocketService';
import WS from 'jest-websocket-mock';

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

describe('WebSocketService - Subscriber Management', () => {
  let server: WS;
  let service: WebSocketService;

  beforeEach(async () => {
    // Reset singleton before each test
    (WebSocketService as any).instance = null;
    service = WebSocketService.getInstance();

    // Create mock WebSocket server
    server = new WS('ws://localhost:8001/api/v1/ws/realtime?token=mock-jwt-token');
  });

  afterEach(() => {
    WS.clean();
    service.disconnect();
  });

  // ================================
  // SUBSCRIBER MANAGEMENT TESTS
  // ================================

  test('should handle duplicate subscriber IDs by replacing old one', async () => {
    const callback1 = jest.fn();
    const callback2 = jest.fn();
    const duplicateId = 'duplicate-id-123';

    // Subscribe with same ID twice
    service.subscribe(duplicateId, callback1, 'PAT001');
    service.subscribe(duplicateId, callback2, 'PAT001'); // Should replace first

    // Connect and send message
    await service.connect();
    await server.connected;

    server.send(JSON.stringify({
      type: 'vitalsUpdate',
      patientId: 'PAT001',
      vitals: { heartRate: 75 }
    }));

    // Wait for message processing
    await new Promise(resolve => setTimeout(resolve, 50));

    // Only second callback should be called (first was replaced)
    expect(callback1).not.toHaveBeenCalled();
    expect(callback2).toHaveBeenCalledTimes(1);
  });

  test('should allow multiple subscribers for same patient', async () => {
    const callback1 = jest.fn();
    const callback2 = jest.fn();

    service.subscribe('sub-1', callback1, 'PAT001');
    service.subscribe('sub-2', callback2, 'PAT001');

    await service.connect();
    await server.connected;

    server.send(JSON.stringify({
      type: 'vitalsUpdate',
      patientId: 'PAT001',
      vitals: { heartRate: 80 }
    }));

    await new Promise(resolve => setTimeout(resolve, 50));

    // Both callbacks should be called
    expect(callback1).toHaveBeenCalledTimes(1);
    expect(callback2).toHaveBeenCalledTimes(1);
  });

  test('should remove subscriber on unsubscribe', async () => {
    const callback = jest.fn();
    const subscriberId = 'test-sub-1';

    service.subscribe(subscriberId, callback, 'PAT001');
    service.unsubscribe(subscriberId);

    await service.connect();
    await server.connected;

    server.send(JSON.stringify({
      type: 'vitalsUpdate',
      patientId: 'PAT001',
      vitals: { heartRate: 85 }
    }));

    await new Promise(resolve => setTimeout(resolve, 50));

    // Callback should NOT be called (unsubscribed)
    expect(callback).not.toHaveBeenCalled();
  });

  test('should not affect other subscribers when one unsubscribes', async () => {
    const callback1 = jest.fn();
    const callback2 = jest.fn();

    service.subscribe('sub-1', callback1, 'PAT001');
    service.subscribe('sub-2', callback2, 'PAT001');

    // Unsubscribe first one
    service.unsubscribe('sub-1');

    await service.connect();
    await server.connected;

    server.send(JSON.stringify({
      type: 'vitalsUpdate',
      patientId: 'PAT001',
      vitals: { heartRate: 90 }
    }));

    await new Promise(resolve => setTimeout(resolve, 50));

    // Only second callback should be called
    expect(callback1).not.toHaveBeenCalled();
    expect(callback2).toHaveBeenCalledTimes(1);
  });

  // ================================
  // MESSAGE ROUTING TESTS
  // ================================

  test('should route message only to matching patientId', async () => {
    const callbackPAT001 = jest.fn();
    const callbackPAT002 = jest.fn();

    service.subscribe('sub-pat001', callbackPAT001, 'PAT001');
    service.subscribe('sub-pat002', callbackPAT002, 'PAT002');

    await service.connect();
    await server.connected;

    // Send message for PAT001
    server.send(JSON.stringify({
      type: 'vitalsUpdate',
      patientId: 'PAT001',
      vitals: { heartRate: 75 }
    }));

    await new Promise(resolve => setTimeout(resolve, 50));

    // Only PAT001 callback should be called
    expect(callbackPAT001).toHaveBeenCalledTimes(1);
    expect(callbackPAT002).not.toHaveBeenCalled();
  });

  test('should NOT route to wrong patient (critical safety test)', async () => {
    const callbackPAT001 = jest.fn();
    const callbackPAT002 = jest.fn();
    const callbackPAT003 = jest.fn();

    service.subscribe('sub-1', callbackPAT001, 'PAT001');
    service.subscribe('sub-2', callbackPAT002, 'PAT002');
    service.subscribe('sub-3', callbackPAT003, 'PAT003');

    await service.connect();
    await server.connected;

    // Send messages for all 3 patients
    server.send(JSON.stringify({
      type: 'vitalsUpdate',
      patientId: 'PAT001',
      vitals: { heartRate: 75 }
    }));

    server.send(JSON.stringify({
      type: 'vitalsUpdate',
      patientId: 'PAT002',
      vitals: { heartRate: 85 }
    }));

    server.send(JSON.stringify({
      type: 'vitalsUpdate',
      patientId: 'PAT003',
      vitals: { heartRate: 95 }
    }));

    await new Promise(resolve => setTimeout(resolve, 100));

    // Each callback should be called exactly once with correct data
    expect(callbackPAT001).toHaveBeenCalledTimes(1);
    expect(callbackPAT001).toHaveBeenCalledWith(
      expect.objectContaining({
        patientId: 'PAT001',
        vitals: { heartRate: 75 }
      })
    );

    expect(callbackPAT002).toHaveBeenCalledTimes(1);
    expect(callbackPAT002).toHaveBeenCalledWith(
      expect.objectContaining({
        patientId: 'PAT002',
        vitals: { heartRate: 85 }
      })
    );

    expect(callbackPAT003).toHaveBeenCalledTimes(1);
    expect(callbackPAT003).toHaveBeenCalledWith(
      expect.objectContaining({
        patientId: 'PAT003',
        vitals: { heartRate: 95 }
      })
    );
  });

  test('should route to all subscribers without patientId filter', async () => {
    const callbackNoFilter = jest.fn();
    const callbackPAT001 = jest.fn();

    // Subscribe without patientId (dashboard?)
    service.subscribe('sub-no-filter', callbackNoFilter);
    service.subscribe('sub-pat001', callbackPAT001, 'PAT001');

    await service.connect();
    await server.connected;

    server.send(JSON.stringify({
      type: 'vitalsUpdate',
      patientId: 'PAT001',
      vitals: { heartRate: 75 }
    }));

    await new Promise(resolve => setTimeout(resolve, 50));

    // Both should receive message
    expect(callbackNoFilter).toHaveBeenCalledTimes(1);
    expect(callbackPAT001).toHaveBeenCalledTimes(1);
  });

  test('should handle message with no patientId', async () => {
    const callback = jest.fn();

    service.subscribe('sub-1', callback, 'PAT001');

    await service.connect();
    await server.connected;

    // Send message without patientId
    server.send(JSON.stringify({
      type: 'connectionStatus',
      message: 'connected'
    }));

    await new Promise(resolve => setTimeout(resolve, 50));

    // Should NOT be routed (no patientId match)
    expect(callback).not.toHaveBeenCalled();
  });

  // ================================
  // BACKEND SUBSCRIPTION TESTS
  // ================================

  test('should send subscribePatient message to backend', async () => {
    await service.connect();
    await server.connected;

    // Subscribe to patient
    service.subscribe('sub-1', jest.fn(), 'PAT001');

    // Wait for backend message
    await expect(server).toReceiveMessage(
      JSON.stringify({
        type: 'subscribePatient',
        patientId: 'PAT001'
      })
    );
  });

  test('should not send duplicate subscribePatient for same patient', async () => {
    await service.connect();
    await server.connected;

    // Subscribe to same patient twice
    service.subscribe('sub-1', jest.fn(), 'PAT001');
    service.subscribe('sub-2', jest.fn(), 'PAT001');

    // Should only send subscribePatient once
    await expect(server).toReceiveMessage(
      JSON.stringify({
        type: 'subscribePatient',
        patientId: 'PAT001'
      })
    );

    // No more messages
    const messages = server.messages;
    const subscribeMessages = messages.filter(msg =>
      msg === JSON.stringify({ type: 'subscribePatient', patientId: 'PAT001' })
    );
    expect(subscribeMessages.length).toBe(1);
  });

  test('should send unsubscribePatient when last subscriber removed', async () => {
    await service.connect();
    await server.connected;

    const sub1 = 'sub-1';
    service.subscribe(sub1, jest.fn(), 'PAT001');

    // Wait for subscribe message
    await server.nextMessage;

    // Unsubscribe
    service.unsubscribe(sub1);

    // Should send unsubscribe message
    await expect(server).toReceiveMessage(
      JSON.stringify({
        type: 'unsubscribePatient',
        patientId: 'PAT001'
      })
    );
  });

  test('should NOT unsubscribe if other subscribers exist', async () => {
    await service.connect();
    await server.connected;

    service.subscribe('sub-1', jest.fn(), 'PAT001');
    service.subscribe('sub-2', jest.fn(), 'PAT001');

    await server.nextMessage; // subscribePatient

    // Unsubscribe first one
    service.unsubscribe('sub-1');

    await new Promise(resolve => setTimeout(resolve, 100));

    // Should NOT send unsubscribePatient (sub-2 still exists)
    const messages = server.messages;
    const unsubscribeMessages = messages.filter(msg =>
      msg.includes('unsubscribePatient')
    );
    expect(unsubscribeMessages.length).toBe(0);
  });

  // ================================
  // RECONNECTION TESTS
  // ================================

  test('should resubscribe to all patients after reconnect', async () => {
    // Initial connection
    await service.connect();
    await server.connected;

    // Subscribe to 2 patients
    service.subscribe('sub-1', jest.fn(), 'PAT001');
    service.subscribe('sub-2', jest.fn(), 'PAT002');

    await server.nextMessage; // PAT001
    await server.nextMessage; // PAT002

    // Simulate disconnect
    server.close();
    await new Promise(resolve => setTimeout(resolve, 100));

    // Create new server (simulate backend restart)
    server = new WS('ws://localhost:8001/api/v1/ws/realtime?token=mock-jwt-token');

    // Reconnect
    await service.connect();
    await server.connected;

    // Should resubscribe to both patients
    const resubscribeMessages = [];
    resubscribeMessages.push(await server.nextMessage);
    resubscribeMessages.push(await server.nextMessage);

    expect(resubscribeMessages).toContainEqual(
      JSON.stringify({ type: 'subscribePatient', patientId: 'PAT001' })
    );
    expect(resubscribeMessages).toContainEqual(
      JSON.stringify({ type: 'subscribePatient', patientId: 'PAT002' })
    );
  });
});
