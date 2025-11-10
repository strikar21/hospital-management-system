"""ECG lead name constants."""

from typing import Optional

# 8-channel ECG lead mapping (standard limb + precordial leads)
ECG_LEADS = {
    0: 'Lead I',
    1: 'Lead II',
    2: 'Lead III',
    3: 'aVR',
    4: 'aVL',
    5: 'aVF',
    6: 'V1',
    7: 'V2'
}


def get_lead_name(channel_index: int) -> Optional[str]:
    """
    Get ECG lead name from channel index.

    Args:
        channel_index: Channel index (0-7)

    Returns:
        Lead name or None if invalid index

    Example:
        >>> get_lead_name(0)
        'Lead I'
        >>> get_lead_name(6)
        'V1'
    """
    return ECG_LEADS.get(channel_index)
