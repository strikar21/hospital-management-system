/**
 * Core HTTP client with interceptors and retry logic.
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { setupInterceptors } from './interceptors';
import { setupRetry } from './retry';

export interface ApiRequestConfig extends AxiosRequestConfig {
  skipAuth?: boolean;
  skipRetry?: boolean;
}

export interface ApiResponse<T = any> {
  data: T;
  status: number;
  statusText: string;
}

class APIClient {
  private client: AxiosInstance;

  constructor(baseURL: string = 'http://localhost:8001') {
    this.client = axios.create({
      baseURL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json'
      }
    });

    // Setup interceptors (auth, error handling)
    setupInterceptors(this.client);

    // Setup retry logic
    setupRetry(this.client);
  }

  async get<T = any>(url: string, config?: ApiRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config);
    return response.data;
  }

  async post<T = any>(url: string, data?: any, config?: ApiRequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, config);
    return response.data;
  }

  async put<T = any>(url: string, data?: any, config?: ApiRequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, config);
    return response.data;
  }

  async patch<T = any>(url: string, data?: any, config?: ApiRequestConfig): Promise<T> {
    const response = await this.client.patch<T>(url, data, config);
    return response.data;
  }

  async delete<T = any>(url: string, config?: ApiRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config);
    return response.data;
  }

  /**
   * Set authorization token for all requests.
   */
  setAuthToken(token: string | null) {
    if (token) {
      this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete this.client.defaults.headers.common['Authorization'];
    }
  }

  /**
   * Get the underlying axios instance for advanced usage.
   */
  getInstance(): AxiosInstance {
    return this.client;
  }
}

// Export singleton instance
export const apiClient = new APIClient();
