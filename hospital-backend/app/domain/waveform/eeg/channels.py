"""EEG channel name constants."""

from typing import Optional

# 8-channel EEG mapping (standard 10-20 system positions)
EEG_CHANNELS = {
    0: 'Fp1',
    1: 'Fp2',
    2: 'C3',
    3: 'C4',
    4: 'P3',
    5: 'P4',
    6: 'O1',
    7: 'O2'
}


def get_channel_name(channel_index: int) -> Optional[str]:
    """
    Get EEG channel name from channel index.

    Args:
        channel_index: Channel index (0-7)

    Returns:
        Channel name or None if invalid index

    Example:
        >>> get_channel_name(0)
        'Fp1'
        >>> get_channel_name(6)
        'O1'
    """
    return EEG_CHANNELS.get(channel_index)
