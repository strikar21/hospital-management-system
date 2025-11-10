"""ECG-specific waveform decoding."""

from typing import Dict, Any, List
from app.common.waveform import decompress_delta, adc_to_millivolts


def decode_ecg_channel(channel_data: Dict[str, Any]) -> List[float]:
    """
    Decode ECG channel data (delta-encoded ADC → millivolts).

    Args:
        channel_data: Channel data with baseline and deltas

    Returns:
        List of voltage values in millivolts

    Example:
        >>> channel = {'baseline': 8388608, 'deltas': [100, -50, 75]}
        >>> decode_ecg_channel(channel)
        [0.0, 1.0, 0.5, 1.25]
    """
    # Decompress delta encoding
    adc_values = decompress_delta(channel_data)

    # Convert ADC to millivolts
    mv_values = adc_to_millivolts(adc_values)

    return mv_values
