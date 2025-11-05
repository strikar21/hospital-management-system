/**
 * SecureStorage Encryption Tests
 * PRIORITY 1 - CRITICAL: PHI Data Protection
 *
 * Tests AES-GCM encryption/decryption for medical data
 * Ensures HIPAA-compliant data protection
 */

import SecureStorage from '../secureStorage';
import { webcrypto } from 'crypto';

// Polyfill Web Crypto API for Node.js test environment
if (!global.crypto) {
  (global as any).crypto = webcrypto;
}

// Mock localStorage and sessionStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; },
    get length() { return Object.keys(store).length; },
    key: (index: number) => Object.keys(store)[index] || null
  };
})();

const sessionStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; }
  };
})();

// Apply mocks
Object.defineProperty(global, 'localStorage', { value: localStorageMock });
Object.defineProperty(global, 'sessionStorage', { value: sessionStorageMock });

describe('SecureStorage - Encryption Tests', () => {
  beforeEach(() => {
    localStorageMock.clear();
    sessionStorageMock.clear();
  });

  // ================================
  // ENCRYPTION/DECRYPTION CORRECTNESS
  // ================================

  describe('Encryption and Decryption', () => {
    test('should encrypt and decrypt token correctly', async () => {
      const originalToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token';

      await SecureStorage.setToken(originalToken);
      const retrieved = await SecureStorage.getToken();

      expect(retrieved).toBe(originalToken);
    });

    test('should encrypt and decrypt user data correctly', async () => {
      const originalUser = {
        id: 'USER001',
        name: 'Dr. John Doe',
        role: 'doctor',
        department: 'Cardiology'
      };

      await SecureStorage.setUser(originalUser);
      const retrieved = await SecureStorage.getUser();

      expect(retrieved).toEqual(originalUser);
    });

    test('should encrypt and decrypt generic data correctly', async () => {
      const phi = JSON.stringify({
        patientId: 'P123',
        diagnosis: 'Hypertension',
        medications: ['Lisinopril', 'Amlodipine']
      });

      await SecureStorage.set('patient_data', phi);
      const retrieved = await SecureStorage.get('patient_data');

      expect(retrieved).toBe(phi);
    });

    test('should produce different ciphertext for same plaintext (IV randomness)', async () => {
      const token = 'same-token-123';

      await SecureStorage.setToken(token);
      const encrypted1 = localStorage.getItem('hospitalAccessToken');

      localStorageMock.clear();
      sessionStorageMock.clear();

      await SecureStorage.setToken(token);
      const encrypted2 = localStorage.getItem('hospitalAccessToken');

      // Ciphertexts should be different (due to random IV)
      expect(encrypted1).not.toBe(encrypted2);

      // But both should decrypt to same value
      localStorageMock.setItem('hospitalAccessToken', encrypted1!);
      const decrypted1 = await SecureStorage.getToken();

      localStorageMock.setItem('hospitalAccessToken', encrypted2!);
      const decrypted2 = await SecureStorage.getToken();

      expect(decrypted1).toBe(token);
      expect(decrypted2).toBe(token);
    });
  });

  // ================================
  // DATA NOT STORED IN PLAINTEXT
  // ================================

  describe('PHI Protection - No Plaintext Storage', () => {
    test('should NOT store token in plaintext', async () => {
      const sensitiveToken = 'secret-jwt-token-with-patient-data';

      await SecureStorage.setToken(sensitiveToken);
      const stored = localStorage.getItem('hospitalAccessToken');

      // Stored value should not contain the plaintext
      expect(stored).not.toContain('secret');
      expect(stored).not.toContain('jwt');
      expect(stored).not.toContain('patient');
    });

    test('should NOT store user PHI in plaintext', async () => {
      const user = {
        id: 'DOC001',
        name: 'Dr. Jane Smith',
        ssn: '123-45-6789', // Sensitive PHI
        email: 'jane.smith@hospital.com'
      };

      await SecureStorage.setUser(user);
      const stored = localStorage.getItem('hospital_user');

      // Should not contain any user data in plaintext
      expect(stored).not.toContain('Jane');
      expect(stored).not.toContain('Smith');
      expect(stored).not.toContain('123-45-6789');
      expect(stored).not.toContain('jane.smith');
    });

    test('should NOT store patient data in plaintext', async () => {
      const patientData = JSON.stringify({
        name: 'John Patient',
        mrn: 'MRN12345',
        diagnosis: 'Diabetes Type 2'
      });

      await SecureStorage.set('patient_P123', patientData);
      const stored = localStorage.getItem('patient_P123');

      expect(stored).not.toContain('John');
      expect(stored).not.toContain('Patient');
      expect(stored).not.toContain('MRN12345');
      expect(stored).not.toContain('Diabetes');
    });
  });

  // ================================
  // TOKEN EXPIRATION
  // ================================

  describe('Token Expiration (Security)', () => {
    test('should return null for expired token', async () => {
      const token = 'valid-token';

      await SecureStorage.setToken(token);

      // Manually set expiration to past
      localStorage.setItem('hospitalAccessToken_exp', (Date.now() - 1000).toString());

      const retrieved = await SecureStorage.getToken();

      expect(retrieved).toBeNull();
    });

    test('should remove expired token from storage', async () => {
      await SecureStorage.setToken('expired-token');
      localStorage.setItem('hospitalAccessToken_exp', (Date.now() - 1000).toString());

      await SecureStorage.getToken();

      // Token should be removed
      expect(localStorage.getItem('hospitalAccessToken')).toBeNull();
      expect(localStorage.getItem('hospitalAccessToken_exp')).toBeNull();
    });

    test('should set 8-hour expiration on token storage', async () => {
      const beforeTime = Date.now();
      await SecureStorage.setToken('test-token');
      const afterTime = Date.now();

      const expiration = localStorage.getItem('hospitalAccessToken_exp');
      const expirationTime = parseInt(expiration!);

      const expectedExpiration = beforeTime + (8 * 60 * 60 * 1000);
      const maxExpectedExpiration = afterTime + (8 * 60 * 60 * 1000);

      expect(expirationTime).toBeGreaterThanOrEqual(expectedExpiration);
      expect(expirationTime).toBeLessThanOrEqual(maxExpectedExpiration);
    });

    test('should refresh token expiration', async () => {
      await SecureStorage.setToken('test-token');

      const originalExpiration = localStorage.getItem('hospitalAccessToken_exp');

      // Wait 10ms and refresh
      await new Promise(resolve => setTimeout(resolve, 10));
      await SecureStorage.refreshTokenExpiration();

      const newExpiration = localStorage.getItem('hospitalAccessToken_exp');

      expect(parseInt(newExpiration!)).toBeGreaterThan(parseInt(originalExpiration!));
    });
  });

  // ================================
  // ERROR HANDLING
  // ================================

  describe('Error Handling', () => {
    test('should return null for missing token', async () => {
      const token = await SecureStorage.getToken();
      expect(token).toBeNull();
    });

    test('should return null for missing user', async () => {
      const user = await SecureStorage.getUser();
      expect(user).toBeNull();
    });

    test('should return null for corrupted encrypted data', async () => {
      // Store invalid base64
      localStorage.setItem('hospitalAccessToken', 'invalid-not-encrypted!!!');

      const token = await SecureStorage.getToken();

      expect(token).toBeNull();
      // Should also remove corrupted data
      expect(localStorage.getItem('hospitalAccessToken')).toBeNull();
    });

    test('should handle empty string gracefully', async () => {
      await SecureStorage.setToken('');
      const retrieved = await SecureStorage.getToken();

      // Empty token should not be stored
      expect(retrieved).toBeNull();
    });

    test('should handle null/undefined user gracefully', async () => {
      await SecureStorage.setUser(null as any);
      await SecureStorage.setUser(undefined as any);

      const retrieved = await SecureStorage.getUser();
      expect(retrieved).toBeNull();
    });
  });

  // ================================
  // DATA CLEANUP (HIPAA)
  // ================================

  describe('Data Cleanup - HIPAA Compliance', () => {
    test('should remove token', () => {
      localStorage.setItem('hospitalAccessToken', 'encrypted-token');
      localStorage.setItem('hospitalAccessToken_exp', '12345');

      SecureStorage.removeToken();

      expect(localStorage.getItem('hospitalAccessToken')).toBeNull();
      expect(localStorage.getItem('hospitalAccessToken_exp')).toBeNull();
    });

    test('should remove user', () => {
      localStorage.setItem('hospital_user', 'encrypted-user');

      SecureStorage.removeUser();

      expect(localStorage.getItem('hospital_user')).toBeNull();
    });

    test('should clear all PHI data on clearAll()', async () => {
      // Store various PHI data
      await SecureStorage.setToken('token');
      await SecureStorage.setUser({ id: 'USER001' });
      await SecureStorage.set('hospital_data', 'phi');
      await SecureStorage.set('patient_P123', 'patient-phi');
      await SecureStorage.set('medical_records', 'records');
      localStorage.setItem('unrelated_data', 'should-remain');

      SecureStorage.clearAll();

      // PHI data should be removed
      expect(localStorage.getItem('hospitalAccessToken')).toBeNull();
      expect(localStorage.getItem('hospital_user')).toBeNull();
      expect(localStorage.getItem('hospital_data')).toBeNull();
      expect(localStorage.getItem('patient_P123')).toBeNull();
      expect(localStorage.getItem('medical_records')).toBeNull();

      // Encryption key should be removed from session
      expect(sessionStorage.getItem('medical_encryption_key')).toBeNull();

      // Unrelated data should remain
      expect(localStorage.getItem('unrelated_data')).toBe('should-remain');
    });
  });

  // ================================
  // SECURITY PROPERTIES
  // ================================

  describe('Security Properties', () => {
    test('should use same encryption key within session', async () => {
      await SecureStorage.setToken('token1');
      const key1 = sessionStorage.getItem('medical_encryption_key');

      await SecureStorage.setToken('token2');
      const key2 = sessionStorage.getItem('medical_encryption_key');

      // Key should be reused within session
      expect(key1).toBe(key2);
      expect(key1).not.toBeNull();
    });

    test('should store encryption key in sessionStorage (KNOWN ISSUE)', () => {
      // This test documents the current behavior
      // SECURITY ISSUE: Encryption key stored in sessionStorage is vulnerable to XSS
      // TODO: Move to memory-only storage

      localStorage.setItem('test', 'data');
      const key = sessionStorage.getItem('medical_encryption_key');

      // Key exists in sessionStorage (this is the bug we documented)
      expect(key).not.toBeNull();
    });

    test('should have valid hasValidToken check', async () => {
      expect(await SecureStorage.hasValidToken()).toBe(false);

      await SecureStorage.setToken('valid-token');
      expect(await SecureStorage.hasValidToken()).toBe(true);

      // Set expired token
      localStorage.setItem('hospitalAccessToken_exp', (Date.now() - 1000).toString());
      expect(await SecureStorage.hasValidToken()).toBe(false);
    });

    test('should provide token expiration time', async () => {
      expect(SecureStorage.getTokenExpiration()).toBeNull();

      const beforeTime = Date.now();
      await SecureStorage.setToken('test-token');
      const expiration = SecureStorage.getTokenExpiration();

      expect(expiration).toBeInstanceOf(Date);
      expect(expiration!.getTime()).toBeGreaterThan(beforeTime);
    });
  });
});
