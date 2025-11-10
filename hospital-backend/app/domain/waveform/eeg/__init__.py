"""EEG-specific waveform processing."""

from .channels import EEG_CHANNELS, get_channel_name
from .decoder import decode_eeg_channel

__all__ = ['EEG_CHANNELS', 'get_channel_name', 'decode_eeg_channel']
