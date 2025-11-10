/**
 * Offline message queue for messages sent while disconnected.
 */

import { WSMessage } from './client';

const MAX_QUEUE_SIZE = 100;

export class MessageQueue {
  private queue: WSMessage[] = [];

  enqueue(message: WSMessage) {
    // Prevent queue from growing too large
    if (this.queue.length >= MAX_QUEUE_SIZE) {
      this.queue.shift(); // Remove oldest message
    }

    this.queue.push(message);
  }

  dequeue(): WSMessage | undefined {
    return this.queue.shift();
  }

  isEmpty(): boolean {
    return this.queue.length === 0;
  }

  clear() {
    this.queue = [];
  }

  size(): number {
    return this.queue.length;
  }
}
