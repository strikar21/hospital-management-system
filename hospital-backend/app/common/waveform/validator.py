"""Waveform data validation."""

from typing import Dict, Any, Tuple
from .constants import ADC_MIN, ADC_MAX, MAX_DELTA


def validate_waveform_data(waveform: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate waveform data structure and values.

    Checks:
    - Required fields present
    - ADC values in valid range
    - Delta values in valid range

    Args:
        waveform: Waveform data dict

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> validate_waveform_data({'baseline': 8388608, 'deltas': [100, -50]})
        (True, "")
    """
    # Check required fields
    if 'baseline' not in waveform:
        return (False, "Missing 'baseline' field")

    if 'deltas' not in waveform:
        return (False, "Missing 'deltas' field")

    baseline = waveform['baseline']
    deltas = waveform['deltas']

    # Validate baseline
    if not isinstance(baseline, int):
        return (False, f"Baseline must be int, got {type(baseline)}")

    if not (ADC_MIN <= baseline <= ADC_MAX):
        return (False, f"Baseline {baseline} out of range [{ADC_MIN}, {ADC_MAX}]")

    # Validate deltas
    if not isinstance(deltas, list):
        return (False, f"Deltas must be list, got {type(deltas)}")

    for i, delta in enumerate(deltas):
        if not isinstance(delta, int):
            return (False, f"Delta[{i}] must be int, got {type(delta)}")

        if abs(delta) > MAX_DELTA:
            return (False, f"Delta[{i}] = {delta} exceeds max {MAX_DELTA}")

    return (True, "")
