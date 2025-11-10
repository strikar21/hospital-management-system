/**
 * Vitals domain layer - Single source of truth for vitals processing
 */

export { VitalsValidator } from './VitalsValidator';
export { VitalsFormatter } from './VitalsFormatter';
export type { VitalsData, ValidationResult } from './VitalsValidator';
export type { FormattedVital, TemperatureUnit } from './VitalsFormatter';
