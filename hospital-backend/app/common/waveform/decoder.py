"""Delta decompression for waveform data."""

from typing import List, Dict, Any


def decompress_delta(channel_data: Dict[str, Any]) -> List[int]:
    """
    Decompress delta-encoded channel data.

    Format: {baseline: int, deltas: List[int]}
    Returns: List of decompressed ADC values

    Args:
        channel_data: Dict with 'baseline' and 'deltas' keys

    Returns:
        List of reconstructed ADC values

    Example:
        >>> decompress_delta({'baseline': 8388608, 'deltas': [100, -50, 75]})
        [8388608, 8388708, 8388658, 8388733]
    """
    if not channel_data or 'baseline' not in channel_data or 'deltas' not in channel_data:
        return []

    baseline = channel_data['baseline']
    deltas = channel_data['deltas']

    # Reconstruct original values from delta encoding
    values = [baseline]
    for delta in deltas:
        values.append(values[-1] + delta)

    return values


def decompress_channel(channel: Dict[str, Any]) -> List[int]:
    """
    Decompress single channel with validation.

    Alias for decompress_delta with additional validation.

    Args:
        channel: Channel data dict

    Returns:
        List of ADC values

    Raises:
        ValueError: If channel data is invalid
    """
    if not isinstance(channel, dict):
        raise ValueError("Channel data must be a dictionary")

    if 'baseline' not in channel:
        raise ValueError("Channel data missing 'baseline'")

    if 'deltas' not in channel:
        raise ValueError("Channel data missing 'deltas'")

    return decompress_delta(channel)
