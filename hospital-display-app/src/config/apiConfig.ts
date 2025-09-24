/**
 * Centralized API configuration for easy maintenance
 */

export const API_CONFIG = {
  // Backend URL configuration
  BACKEND_BASE_URL: process.env.NODE_ENV === 'development'
    ? 'http://localhost:8001'
    : (process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001'),

  // API versions - v2 for modern services, v1 for legacy
  API_V1: '/api/v1',
  API_V2: '/api/v2',

  // WebSocket URL
  WS_BASE_URL: process.env.NODE_ENV === 'development'
    ? 'ws://localhost:8001'
    : (process.env.REACT_APP_WS_URL || 'ws://localhost:8001'),
};

// Service-to-version mapping
const SERVICE_VERSIONS: Record<string, 'v1' | 'v2'> = {
  // v2 services (fully migrated)
  '/patients': 'v2',
  '/medications': 'v2',
  '/investigations': 'v2',
  '/therapy': 'v2',

  // v1 services (not yet migrated)
  '/auth': 'v1',
  '/staff': 'v1',
  '/admission': 'v1',
  '/audit': 'v1',
  '/ws': 'v1',
  '/esp32': 'v1',
  '/provisioning': 'v1'
};

// Convenience functions
export const getApiUrl = (endpoint: string, forceVersion?: 'v1' | 'v2'): string => {
  // If version is forced, use it
  if (forceVersion) {
    const apiVersion = forceVersion === 'v2' ? API_CONFIG.API_V2 : API_CONFIG.API_V1;
    return `${API_CONFIG.BACKEND_BASE_URL}${apiVersion}${endpoint}`;
  }

  // Handle endpoints that already specify version (e.g., '/v2/patients/list')
  if (endpoint.startsWith('/v1/') || endpoint.startsWith('/v2/')) {
    return `${API_CONFIG.BACKEND_BASE_URL}/api${endpoint}`;
  }

  // Auto-detect version based on service for relative endpoints (e.g., '/patients/list')
  const service = '/' + endpoint.split('/')[1];
  const version = (SERVICE_VERSIONS as Record<string, 'v1' | 'v2'>)[service] || 'v1'; // Default to v1 for unknown services
  const apiVersion = version === 'v2' ? API_CONFIG.API_V2 : API_CONFIG.API_V1;

  return `${API_CONFIG.BACKEND_BASE_URL}${apiVersion}${endpoint}`;
};

export const getWsUrl = (endpoint: string): string => {
  return `${API_CONFIG.WS_BASE_URL}${API_CONFIG.API_V1}/ws${endpoint}`;
};

export default API_CONFIG;