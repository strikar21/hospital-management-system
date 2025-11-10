/**
 * Request/response interceptors for authentication and error handling.
 */

import { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { ApiError } from './errors';

export function setupInterceptors(client: AxiosInstance) {
  // Request interceptor: Add auth token
  client.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      // Add auth token from localStorage if available
      const token = localStorage.getItem('authToken');
      if (token && !config.headers?.skipAuth) {
        config.headers.Authorization = `Bearer ${token}`;
      }

      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // Response interceptor: Handle errors globally
  client.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      // Handle 401 Unauthorized - token expired
      if (error.response?.status === 401) {
        // Clear auth state
        localStorage.removeItem('authToken');

        // Redirect to login (or trigger refresh token flow)
        window.location.href = '/login';

        return Promise.reject(new ApiError('Unauthorized', 401, error));
      }

      // Wrap error in ApiError for consistent handling
      const apiError = new ApiError(
        error.message || 'An error occurred',
        error.response?.status || 500,
        error
      );

      return Promise.reject(apiError);
    }
  );
}
