/**
 * API Client - Unified HTTP client for all API requests.
 *
 * Usage:
 *   import { apiClient } from '@/lib/api';
 *
 *   const patients = await apiClient.get('/api/v1/patients');
 *   const patient = await apiClient.post('/api/v1/patients', { firstName: 'John' });
 */

export { apiClient } from './client';
export { ApiError, isApiError } from './errors';
export type { ApiResponse, ApiRequestConfig } from './client';
