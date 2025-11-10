"""ADC value conversion to physical units."""

from typing import List
from .constants import ADC_MIDPOINT, SENSITIVITY_MV, SENSITIVITY_UV


def adc_to_millivolts(adc_values: List[int]) -> List[float]:
    """
    Convert 24-bit ADC values to millivolts for ECG display.

    ADC Format (from ESP32):
    - Midpoint: 8388608 (2^23, representing 0V)
    - Range: ±1.0V full scale
    - Sensitivity: ~10 μV per LSB

    Conversion formula:
        mV = (ADC_value - midpoint) * 0.01

    Args:
        adc_values: List of 24-bit ADC values

    Returns:
        List of voltages in millivolts

    Example:
        >>> adc_to_millivolts([8388608, 8410496, 8366720])
        [0.00, 218.88, -218.88]
    """
    return [(value - ADC_MIDPOINT) * SENSITIVITY_MV for value in adc_values]


def adc_to_microvolts(adc_values: List[int]) -> List[float]:
    """
    Convert 24-bit ADC values to microvolts for EEG display.

    ADC Format (from ESP32):
    - Midpoint: 8388608 (2^23, representing 0V)
    - Range: ±0.1V full scale for EEG
    - Sensitivity: ~1 μV per LSB

    Conversion formula:
        μV = (ADC_value - midpoint) * 0.001

    Args:
        adc_values: List of 24-bit ADC values

    Returns:
        List of voltages in microvolts

    Example:
        >>> adc_to_microvolts([8388608, 8389608, 8387608])
        [0.0, 1.0, -1.0]
    """
    return [(value - ADC_MIDPOINT) * SENSITIVITY_UV for value in adc_values]
