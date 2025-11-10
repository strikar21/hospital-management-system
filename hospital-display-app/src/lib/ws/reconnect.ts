/**
 * Reconnection logic with exponential backoff.
 */

const MAX_RECONNECT_DELAY = 30000; // 30 seconds
const INITIAL_DELAY = 1000; // 1 second

export function setupReconnect(client: any) {
  const attempts = client.getReconnectAttempts();

  // Calculate delay with exponential backoff + jitter
  const baseDelay = Math.min(INITIAL_DELAY * Math.pow(2, attempts), MAX_RECONNECT_DELAY);
  const jitter = Math.random() * 1000; // 0-1 second jitter
  const delay = baseDelay + jitter;

  console.log(`[WS] Reconnecting in ${Math.round(delay / 1000)}s (attempt ${attempts + 1})`);

  const timer = window.setTimeout(() => {
    client.incrementReconnectAttempts();
    client.connect();
  }, delay);

  client.setReconnectTimer(timer);
}
