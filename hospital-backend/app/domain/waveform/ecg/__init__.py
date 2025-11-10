"""ECG-specific waveform processing."""

from .leads import ECG_LEADS, get_lead_name
from .decoder import decode_ecg_channel

__all__ = ['ECG_LEADS', 'get_lead_name', 'decode_ecg_channel']
