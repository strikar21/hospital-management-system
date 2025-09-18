/**
 * Centralized API configuration for easy maintenance
 */

export const API_CONFIG = {
  // Backend URL configuration
  BACKEND_BASE_URL: process.env.NODE_ENV === 'development' 
    ? 'http://localhost:8001' 
    : (process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001'),
    
  // API version
  API_VERSION: '/api/v1',
  
  // WebSocket URL
  WS_BASE_URL: process.env.NODE_ENV === 'development'
    ? 'ws://localhost:8001'
    : (process.env.REACT_APP_WS_URL || 'ws://localhost:8001'),
};

// Convenience functions
export const getApiUrl = (endpoint: string): string => {
  return `${API_CONFIG.BACKEND_BASE_URL}${API_CONFIG.API_VERSION}${endpoint}`;
};

export const getWsUrl = (endpoint: string): string => {
  return `${API_CONFIG.WS_BASE_URL}${API_CONFIG.API_VERSION}/ws${endpoint}`;
};

export default API_CONFIG;