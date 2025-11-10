/**
 * API error handling utilities.
 */

import { AxiosError } from 'axios';

export class ApiError extends Error {
  public statusCode: number;
  public originalError?: AxiosError;

  constructor(message: string, statusCode: number, originalError?: AxiosError) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.originalError = originalError;

    // Maintains proper stack trace for where error was thrown
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, ApiError);
    }
  }

  /**
   * Check if error is a network error (no response from server).
   */
  isNetworkError(): boolean {
    return !this.originalError?.response;
  }

  /**
   * Check if error is a timeout error.
   */
  isTimeoutError(): boolean {
    return this.originalError?.code === 'ECONNABORTED';
  }

  /**
   * Get user-friendly error message.
   */
  getUserMessage(): string {
    if (this.isNetworkError()) {
      return 'Unable to connect to server. Please check your internet connection.';
    }

    if (this.isTimeoutError()) {
      return 'Request timed out. Please try again.';
    }

    switch (this.statusCode) {
      case 400:
        return 'Invalid request. Please check your input.';
      case 401:
        return 'You are not authorized. Please log in again.';
      case 403:
        return 'You do not have permission to perform this action.';
      case 404:
        return 'The requested resource was not found.';
      case 500:
        return 'Server error. Please try again later.';
      default:
        return this.message || 'An unexpected error occurred.';
    }
  }
}

/**
 * Type guard to check if error is an ApiError.
 */
export function isApiError(error: any): error is ApiError {
  return error instanceof ApiError;
}
