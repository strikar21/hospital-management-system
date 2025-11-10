"""Alert constants and enums."""

from typing import Literal

# Alert severity levels (matches database enum)
AlertSeverity = Literal['low', 'medium', 'high', 'critical']

# Alert types (matches database enum)
AlertType = Literal['vital', 'arrhythmia', 'device', 'system']

# Severity ordering (for comparison)
SEVERITY_ORDER = {
    'low': 1,
    'medium': 2,
    'high': 3,
    'critical': 4
}
