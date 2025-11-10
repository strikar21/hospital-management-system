/**
 * Waveform utilities - Single source of truth for waveform processing.
 *
 * Usage:
 *   import { decompressDelta, adcToMillivolts } from '@/utils/waveform';
 */

export { decompressDelta, decompressChannel } from './decoder';
export { adcToMillivolts, adcToMicrovolts } from './converter';
export { ADC_MIDPOINT, SENSITIVITY_MV, SENSITIVITY_UV } from './constants';
