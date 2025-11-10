/**
 * Retry logic for failed requests.
 */

import { AxiosInstance, AxiosError } from 'axios';

const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // 1 second

export function setupRetry(client: AxiosInstance) {
  client.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const config = error.config as any;

      // Skip retry if explicitly disabled
      if (config?.skipRetry) {
        return Promise.reject(error);
      }

      // Don't retry on 4xx errors (client errors)
      if (error.response && error.response.status >= 400 && error.response.status < 500) {
        return Promise.reject(error);
      }

      // Initialize retry count
      config.retryCount = config.retryCount || 0;

      // Check if we've exceeded max retries
      if (config.retryCount >= MAX_RETRIES) {
        return Promise.reject(error);
      }

      // Increment retry count
      config.retryCount += 1;

      // Calculate delay with exponential backoff
      const delay = RETRY_DELAY * Math.pow(2, config.retryCount - 1);

      // Wait before retrying
      await new Promise((resolve) => setTimeout(resolve, delay));

      // Retry the request
      return client(config);
    }
  );
}
