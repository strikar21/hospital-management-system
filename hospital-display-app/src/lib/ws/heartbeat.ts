/**
 * Heartbeat mechanism to keep connection alive.
 */

const HEARTBEAT_INTERVAL = 30000; // 30 seconds

export function setupHeartbeat(client: any) {
  const timer = window.setInterval(() => {
    const ws = client.getWS();

    if (ws?.readyState === WebSocket.OPEN) {
      // Send ping message
      ws.send(JSON.stringify({ type: 'ping', payload: {} }));
    } else {
      // Connection lost, clear heartbeat
      clearInterval(timer);
    }
  }, HEARTBEAT_INTERVAL);

  client.setHeartbeatTimer(timer);
}
