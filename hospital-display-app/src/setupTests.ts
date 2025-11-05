/**
 * Jest Setup File - Test Environment Configuration
 * Polyfills for Node.js test environment compatibility
 */

import '@testing-library/jest-dom';
import { webcrypto } from 'crypto';

// ================================
// WEB CRYPTO API POLYFILL
// ================================
// MedicalErrorBoundary and secureStorage use Web Crypto API
// Need to polyfill for Node.js Jest environment

if (!global.crypto) {
  (global as any).crypto = webcrypto;
}

// Ensure crypto.getRandomValues is available
if (!global.crypto.getRandomValues) {
  (global.crypto as any).getRandomValues = webcrypto.getRandomValues.bind(webcrypto);
}

// Ensure crypto.subtle is available for encryption tests
if (!global.crypto.subtle) {
  (global.crypto as any).subtle = webcrypto.subtle;
}

// ================================
// LOCALSTORAGE MOCK
// ================================
// Mock localStorage for secureStorage tests with actual storage behavior

const localStorageData: { [key: string]: string } = {};

const localStorageMock = {
  getItem: jest.fn((key: string) => localStorageData[key] || null),
  setItem: jest.fn((key: string, value: string) => {
    localStorageData[key] = value;
  }),
  removeItem: jest.fn((key: string) => {
    delete localStorageData[key];
  }),
  clear: jest.fn(() => {
    for (const key in localStorageData) {
      delete localStorageData[key];
    }
  }),
  get length() {
    return Object.keys(localStorageData).length;
  },
  key: jest.fn((index: number) => {
    const keys = Object.keys(localStorageData);
    return keys[index] || null;
  })
};

global.localStorage = localStorageMock as any;

// ================================
// SESSIONSTORAGE MOCK
// ================================
// Mock sessionStorage for any session-based storage with actual storage behavior

const sessionStorageData: { [key: string]: string } = {};

const sessionStorageMock = {
  getItem: jest.fn((key: string) => sessionStorageData[key] || null),
  setItem: jest.fn((key: string, value: string) => {
    sessionStorageData[key] = value;
  }),
  removeItem: jest.fn((key: string) => {
    delete sessionStorageData[key];
  }),
  clear: jest.fn(() => {
    for (const key in sessionStorageData) {
      delete sessionStorageData[key];
    }
  }),
  get length() {
    return Object.keys(sessionStorageData).length;
  },
  key: jest.fn((index: number) => {
    const keys = Object.keys(sessionStorageData);
    return keys[index] || null;
  })
};

global.sessionStorage = sessionStorageMock as any;
