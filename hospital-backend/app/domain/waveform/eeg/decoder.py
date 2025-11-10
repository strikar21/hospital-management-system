"""EEG-specific waveform decoding."""

from typing import Dict, Any, List
from app.common.waveform import decompress_delta, adc_to_microvolts


def decode_eeg_channel(channel_data: Dict[str, Any]) -> List[float]:
    """
    Decode EEG channel data (delta-encoded ADC → microvolts).

    Args:
        channel_data: Channel data with baseline and deltas

    Returns:
        List of voltage values in microvolts

    Example:
        >>> channel = {'baseline': 8388608, 'deltas': [100, -50, 75]}
        >>> decode_eeg_channel(channel)
        [0.0, 0.1, 0.05, 0.125]
    """
    # Decompress delta encoding
    adc_values = decompress_delta(channel_data)

    # Convert ADC to microvolts
    uv_values = adc_to_microvolts(adc_values)

    return uv_values
