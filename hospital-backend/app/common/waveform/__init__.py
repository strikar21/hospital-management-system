"""
Waveform utilities - Single source of truth for waveform processing.

Usage:
    from app.common.waveform import decompress_delta, adc_to_millivolts

    # Decompress delta-encoded channel
    values = decompress_delta({'baseline': 8388608, 'deltas': [100, -50, 75]})

    # Convert ADC to millivolts (ECG)
    mv_values = adc_to_millivolts(values)
"""

from .decoder import decompress_delta, decompress_channel
from .converter import adc_to_millivolts, adc_to_microvolts
from .validator import validate_waveform_data
from .constants import ADC_MIDPOINT, SENSITIVITY_MV, SENSITIVITY_UV

__all__ = [
    'decompress_delta',
    'decompress_channel',
    'adc_to_millivolts',
    'adc_to_microvolts',
    'validate_waveform_data',
    'ADC_MIDPOINT',
    'SENSITIVITY_MV',
    'SENSITIVITY_UV'
]
