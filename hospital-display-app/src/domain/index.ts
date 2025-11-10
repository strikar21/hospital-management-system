/**
 * Frontend Domain Layer
 *
 * Single source of truth for business logic and data processing.
 * Matches backend domain-driven architecture for consistency.
 *
 * Usage:
 *   import { AlertProcessor, VitalsFormatter } from '@/domain';
 *
 * DO NOT put API calls or component logic here.
 * This layer is pure business logic only.
 */

// Alert domain
export * from './alerts';

// Vitals domain
export * from './vitals';
