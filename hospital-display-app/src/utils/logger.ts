/**
 * Logger Utility - HIPAA Compliant Logging
 *
 * Production builds should NOT log PHI to browser console.
 * This utility gates all logging behind development mode check.
 *
 * HIPAA Compliance:
 * - NO patient data in production console
 * - NO vitals in production console
 * - NO medical data in production console
 *
 * Usage:
 *   import { logger } from '@/utils/logger';
 *   logger.log('Debug message'); // Only in dev
 *   logger.error('Error message'); // Always logged
 */

const isDevelopment = process.env.NODE_ENV === 'development';

/**
 * Medical-safe logger that respects environment
 */
export const logger = {
  /**
   * Development-only logging
   * Use for debugging, vitals display, waveform processing
   */
  log: (...args: any[]) => {
    if (isDevelopment) {
      console.log(...args);
    }
  },

  /**
   * Development-only info logging
   * Use for informational messages
   */
  info: (...args: any[]) => {
    if (isDevelopment) {
      console.info(...args);
    }
  },

  /**
   * Development-only warning logging
   * Use for non-critical warnings
   */
  warn: (...args: any[]) => {
    if (isDevelopment) {
      console.warn(...args);
    }
  },

  /**
   * Always-on error logging
   * Use for actual errors that need tracking
   * IMPORTANT: Sanitize any patient data before logging errors
   */
  error: (...args: any[]) => {
    console.error(...args);
  },

  /**
   * Development-only debug logging
   * Use for verbose debugging
   */
  debug: (...args: any[]) => {
    if (isDevelopment) {
      console.debug(...args);
    }
  },

  /**
   * Development-only table logging
   * Use for structured data display
   */
  table: (data: any) => {
    if (isDevelopment) {
      console.table(data);
    }
  },

  /**
   * Development-only group logging
   * Use for collapsible log groups
   */
  group: (label: string) => {
    if (isDevelopment) {
      console.group(label);
    }
  },

  /**
   * Development-only group end
   */
  groupEnd: () => {
    if (isDevelopment) {
      console.groupEnd();
    }
  }
};

/**
 * Helper to sanitize patient data for logging
 * Replaces sensitive fields with [REDACTED]
 */
export const sanitizeForLog = (obj: any): any => {
  if (!obj) return obj;

  const sensitive = ['ssn', 'phoneNumber', 'email', 'address', 'dateOfBirth', 'firstName', 'lastName'];
  const sanitized = { ...obj };

  sensitive.forEach(key => {
    if (key in sanitized) {
      sanitized[key] = '[REDACTED]';
    }
  });

  return sanitized;
};
