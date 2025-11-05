/**
 * WaveformCacheService - Waveform data caching with IndexedDB persistence
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade caching: Instant waveform display with persistence
 */

import { logger } from '../utils/logger';

interface WaveformCacheData {
  patientId: string;
  mode: 'ecg' | 'eeg';
  sampleRate: number;
  timestamp: number;
  expiresAt: number;
  leadBuffers: number[][];  // Array of arrays for each lead
}

class WaveformCacheService {
  private dbName = 'HospitalWaveformCache';
  private storeName = 'waveforms';
  private version = 1;
  private db: IDBDatabase | null = null;
  private TTL = 10 * 60 * 1000; // 10 minutes
  private memoryCache = new Map<string, WaveformCacheData>();

  /**
   * Initialize IndexedDB connection
   */
  async init(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.version);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve();
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;
        if (!db.objectStoreNames.contains(this.storeName)) {
          db.createObjectStore(this.storeName, { keyPath: 'id' });
        }
      };
    });
  }

  /**
   * Generate cache key from patient ID and mode
   */
  private getCacheKey(patientId: string, mode: 'ecg' | 'eeg'): string {
    return `${patientId}-${mode}`;
  }

  /**
   * Save waveform data to both memory and IndexedDB cache
   */
  async saveWaveform(
    patientId: string,
    mode: 'ecg' | 'eeg',
    leadBuffers: number[][],
    sampleRate: number
  ): Promise<void> {
    const cacheKey = this.getCacheKey(patientId, mode);
    const cacheData: WaveformCacheData = {
      patientId,
      mode,
      sampleRate,
      timestamp: Date.now(),
      expiresAt: Date.now() + this.TTL,
      leadBuffers: this.trimBuffers(leadBuffers, sampleRate)
    };

    // Save to memory cache (fast access)
    this.memoryCache.set(cacheKey, cacheData);

    // Save to IndexedDB (persistence)
    try {
      await this.saveToIndexedDB(cacheKey, cacheData);
      logger.log(`💾 Waveform cache saved: ${cacheKey} (${leadBuffers.length} leads, ${leadBuffers[0]?.length || 0} samples)`);
    } catch (error) {
      logger.error('Failed to save waveform to IndexedDB:', error);
      // Continue with memory cache only
    }
  }

  /**
   * Get waveform data from cache
   * Checks memory cache first, then IndexedDB
   * Returns null if not found or expired
   */
  async getWaveform(patientId: string, mode: 'ecg' | 'eeg'): Promise<number[][] | null> {
    const cacheKey = this.getCacheKey(patientId, mode);

    // Check memory cache first (fastest - no async)
    const memoryData = this.memoryCache.get(cacheKey);
    if (memoryData && Date.now() < memoryData.expiresAt) {
      logger.log(`⚡ Waveform cache HIT (memory): ${cacheKey}`);
      return memoryData.leadBuffers;
    }

    // Check IndexedDB (slower but persists across page reloads)
    try {
      const indexedData = await this.getFromIndexedDB(cacheKey);
      if (indexedData && Date.now() < indexedData.expiresAt) {
        logger.log(`📦 Waveform cache HIT (IndexedDB): ${cacheKey}`);
        // Restore to memory cache for faster subsequent access
        this.memoryCache.set(cacheKey, indexedData);
        return indexedData.leadBuffers;
      }
    } catch (error) {
      logger.error('Failed to read waveform from IndexedDB:', error);
      // Continue with cache miss
    }

    logger.log(`❌ Waveform cache MISS: ${cacheKey}`);
    return null;
  }

  /**
   * Trim buffers to keep only last 10 minutes of data
   * Prevents unlimited memory growth
   */
  private trimBuffers(leadBuffers: number[][], sampleRate: number): number[][] {
    const maxSamples = sampleRate * 10 * 60; // 10 minutes worth of samples
    return leadBuffers.map(buffer => {
      if (buffer.length > maxSamples) {
        return buffer.slice(-maxSamples);
      }
      return buffer;
    });
  }

  /**
   * Save waveform data to IndexedDB
   */
  private async saveToIndexedDB(cacheKey: string, cacheData: WaveformCacheData): Promise<void> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const request = store.put({ id: cacheKey, ...cacheData });

      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Get waveform data from IndexedDB
   */
  private async getFromIndexedDB(cacheKey: string): Promise<WaveformCacheData | null> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readonly');
      const store = transaction.objectStore(this.storeName);
      const request = store.get(cacheKey);

      request.onsuccess = () => {
        const result = request.result;
        if (result) {
          // Remove 'id' field added by IndexedDB
          const { id, ...cacheData } = result;
          resolve(cacheData as WaveformCacheData);
        } else {
          resolve(null);
        }
      };
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Invalidate waveform cache for specific patient/mode
   */
  async invalidateCache(patientId: string, mode: 'ecg' | 'eeg'): Promise<void> {
    const cacheKey = this.getCacheKey(patientId, mode);

    // Remove from memory cache
    this.memoryCache.delete(cacheKey);

    // Remove from IndexedDB
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const request = store.delete(cacheKey);

      request.onsuccess = () => {
        logger.log(`🗑️ Waveform cache invalidated: ${cacheKey}`);
        resolve();
      };
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Clear all waveform cache data
   */
  async clearAllCache(): Promise<void> {
    // Clear memory cache
    this.memoryCache.clear();

    // Clear IndexedDB
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const request = store.clear();

      request.onsuccess = () => {
        logger.log('🗑️ All waveform cache cleared');
        resolve();
      };
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Get cache statistics (for debugging/monitoring)
   */
  async getCacheStats(): Promise<{
    memoryEntries: number;
    indexedDBEntries: number;
    cacheKeys: string[];
  }> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readonly');
      const store = transaction.objectStore(this.storeName);
      const request = store.getAllKeys();

      request.onsuccess = () => {
        const keys = request.result as string[];
        resolve({
          memoryEntries: this.memoryCache.size,
          indexedDBEntries: keys.length,
          cacheKeys: keys
        });
      };
      request.onerror = () => reject(request.error);
    });
  }
}

// Singleton instance
export const waveformCacheService = new WaveformCacheService();
export default waveformCacheService;
