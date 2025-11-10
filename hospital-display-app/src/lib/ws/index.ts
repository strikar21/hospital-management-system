/**
 * WebSocket Client - Unified WebSocket client with reconnection and heartbeat.
 *
 * Usage:
 *   import { wsClient } from '@/lib/ws';
 *
 *   wsClient.connect();
 *   wsClient.on('vitalsUpdate', (data) => console.log(data));
 *   wsClient.send('subscribe', { patientId: '123' });
 */

export { wsClient } from './client';
export type { WSMessage, WSEventType } from './client';
