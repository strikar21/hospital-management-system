/**
 * Delta decompression for waveform data.
 */

interface ChannelData {
  baseline: number;
  deltas: number[];
}

export function decompressDelta(channelData: ChannelData): number[] {
  /**
   * Decompress delta-encoded channel data.
   *
   * Format: {baseline: number, deltas: number[]}
   * Returns: Decompressed ADC values
   *
   * @param channelData - Channel data with baseline and deltas
   * @returns Array of reconstructed ADC values
   *
   * @example
   * decompressDelta({baseline: 8388608, deltas: [100, -50, 75]})
   * // [8388608, 8388708, 8388658, 8388733]
   */
  if (!channelData || !channelData.baseline || !channelData.deltas) {
    return [];
  }

  const { baseline, deltas } = channelData;

  // Reconstruct original values from delta encoding
  const values: number[] = [baseline];
  for (const delta of deltas) {
    values.push(values[values.length - 1] + delta);
  }

  return values;
}

export function decompressChannel(channel: ChannelData): number[] {
  /**
   * Decompress single channel with validation.
   *
   * Alias for decompressDelta with additional validation.
   *
   * @param channel - Channel data
   * @returns Array of ADC values
   * @throws Error if channel data is invalid
   */
  if (typeof channel !== 'object' || channel === null) {
    throw new Error('Channel data must be an object');
  }

  if (!('baseline' in channel)) {
    throw new Error("Channel data missing 'baseline'");
  }

  if (!('deltas' in channel)) {
    throw new Error("Channel data missing 'deltas'");
  }

  return decompressDelta(channel);
}
