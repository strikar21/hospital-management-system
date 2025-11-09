/**
 * PatientCacheService - Smart IndexedDB cache with device connection awareness
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade caching: Fresh data for connected watches, cached for offline
 */

interface PatientCache {
  id: string;
  userId: string;
  ward: string;
  patients: any[];
  timestamp: number;
  expiresAt: number;
  hasConnectedDevices: boolean; // Track if any devices were connected when cached
}

interface CacheResult {
  patients: any[] | null;
  shouldFetchFresh: boolean;
  reason: string;
}

class PatientCacheService {
  private dbName = 'HospitalAppCache';
  private storeName = 'patientCache';
  private version = 1;
  private db: IDBDatabase | null = null;
  private TTL = 5 * 60 * 1000; // 5 minutes

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
   * Check if any patient has a connected device
   * Connected = lastSeen within 5 minutes (from backend logic)
   */
  private hasConnectedDevices(patients: any[]): boolean {
    return patients.some(p => p.deviceStatus === 'connected');
  }

  /**
   * Save patient data to cache
   */
  async saveToCache(userId: string, ward: string, patients: any[]): Promise<void> {
    if (!this.db) await this.init();

    const cache: PatientCache = {
      id: this.getCacheKey(userId, ward),
      userId,
      ward,
      patients,
      timestamp: Date.now(),
      expiresAt: Date.now() + this.TTL,
      hasConnectedDevices: this.hasConnectedDevices(patients)
    };

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const request = store.put(cache);

      request.onsuccess = () => {
        resolve();
      };
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Smart cache retrieval with device connection awareness
   *
   * Decision logic:
   * - If cache doesn't exist → Fetch fresh
   * - If cache expired → Fetch fresh
   * - If ANY device is connected → Show cache + Fetch fresh (medical accuracy)
   * - If ALL devices offline → Show cache only (no new data available)
   *
   * @returns {patients, shouldFetchFresh, reason}
   * - patients: Cached data if available
   * - shouldFetchFresh: true if API call is required
   * - reason: Explanation for decision (for logging/debugging)
   */
  async getFromCacheSmart(userId: string, ward: string): Promise<CacheResult> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readonly');
      const store = transaction.objectStore(this.storeName);
      const request = store.get(this.getCacheKey(userId, ward));

      request.onsuccess = () => {
        const cache = request.result as PatientCache | undefined;

        // No cache found
        if (!cache) {
          resolve({
            patients: null,
            shouldFetchFresh: true,
            reason: 'cache_miss'
          });
          return;
        }

        // Cache expired
        if (Date.now() > cache.expiresAt) {
          this.invalidateCache(userId, ward);
          resolve({
            patients: null,
            shouldFetchFresh: true,
            reason: 'cache_expired'
          });
          return;
        }

        // Cache exists and valid - check for connected devices
        const currentlyConnectedDevices = this.hasConnectedDevices(cache.patients);

        if (currentlyConnectedDevices) {
          resolve({
            patients: cache.patients, // Return cache for instant display
            shouldFetchFresh: true,   // But also fetch fresh data
            reason: 'connected_devices_need_fresh'
          });
          return;
        }

        // All devices offline - safe to use cache
        const offlineCount = cache.patients.filter(p =>
          p.deviceStatus === 'offline' || p.deviceStatus === 'recentlySeen' || !p.deviceStatus
        ).length;
        resolve({
          patients: cache.patients,
          shouldFetchFresh: false, // No need to fetch immediately (can fetch in background)
          reason: 'all_devices_offline'
        });
      };

      request.onerror = () => {
        console.error('📦 Cache read error:', request.error);
        resolve({
          patients: null,
          shouldFetchFresh: true,
          reason: 'cache_error'
        }); // Graceful fallback
      };
    });
  }

  /**
   * Invalidate cache for specific user/ward
   */
  async invalidateCache(userId: string, ward: string): Promise<void> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const request = store.delete(this.getCacheKey(userId, ward));

      request.onsuccess = () => {
        resolve();
      };
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Clear all cached data (useful for logout or debugging)
   */
  async clearAllCache(): Promise<void> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const request = store.clear();

      request.onsuccess = () => {
        resolve();
      };
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Get cache statistics (for debugging/monitoring)
   */
  async getCacheStats(): Promise<{
    totalEntries: number;
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
          totalEntries: keys.length,
          cacheKeys: keys
        });
      };
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Generate cache key from user ID and ward
   */
  private getCacheKey(userId: string, ward: string): string {
    return `${userId}-${ward}`;
  }
}

// Singleton instance
export const patientCacheService = new PatientCacheService();
export default patientCacheService;
