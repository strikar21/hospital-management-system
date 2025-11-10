# Hospital Management System - Modular Refactor Plan

**Generated:** 2025-11-10
**Branch:** `refactor/clean-slate-phase1-shared-modules`
**Backup Tag:** `backup-before-refactor-20251110-145117`
**Approach:** Small, focused modules (30-60 LOC each)

---

## 🎯 GOALS

1. **Eliminate 40-50% code duplication** by extracting to shared modules
2. **Improve maintainability** - small files, single responsibility
3. **Enable parallel development** - clear module boundaries
4. **Reduce cognitive load** - each file does ONE thing
5. **Make testing trivial** - pure functions, no side effects

---

## 📐 DESIGN PRINCIPLES

### **Module Size Rules:**
- ✅ **30-60 lines** per file (max 80 for complex logic)
- ✅ **Single responsibility** - one job only
- ✅ **Pure functions** where possible (no side effects)
- ✅ **Clear dependencies** - explicit imports, no circular deps
- ✅ **Self-documenting** - good naming, minimal comments needed

### **Folder Structure:**
- ✅ **Group by feature** (alerts/, vitals/, waveform/)
- ✅ **Separate by layer** (common/, domain/, data/, repos/)
- ✅ **Index files** for clean imports

---

## 📦 PHASE 1: CORE SHARED UTILITIES (Week 1)

**Goal:** Extract duplicated utility code into small, testable modules

### **Day 1-2: Datetime Utilities**

#### **Backend: `app/common/datetime/`**

```
app/common/datetime/
├── __init__.py              # Export public API
├── parser.py                # Parse ISO8601, handle timezones (40 LOC)
├── formatter.py             # Format to ISO8601, relative time (40 LOC)
├── utils.py                 # now_utc(), seconds_since() (30 LOC)
└── constants.py             # Timezone constants (20 LOC)
```

**What gets deleted after migration:**
- ❌ 5 different timestamp patterns across `mqtt_service.py`, `websocket_manager.py`, `pipeline.py`

**Files to create:**

##### **`app/common/datetime/__init__.py`**
```python
"""
Datetime utilities - Single source of truth for all timestamp operations.

Usage:
    from app.common.datetime import now_utc, parse_iso8601, to_iso8601

    # Get current UTC time (timezone-aware)
    current = now_utc()

    # Parse ISO8601 string
    dt = parse_iso8601("2025-11-10T14:30:00Z")

    # Format to ISO8601
    iso_str = to_iso8601(dt)
"""

from .parser import parse_iso8601, parse_timestamp
from .formatter import to_iso8601, format_relative, format_medical
from .utils import now_utc, seconds_since, is_recent

__all__ = [
    'parse_iso8601',
    'parse_timestamp',
    'to_iso8601',
    'format_relative',
    'format_medical',
    'now_utc',
    'seconds_since',
    'is_recent'
]
```

##### **`app/common/datetime/parser.py`** (40 LOC)
```python
"""Parse timestamp strings to datetime objects."""

from datetime import datetime, timezone
from typing import Union


def parse_iso8601(timestamp_str: str) -> datetime:
    """
    Parse ISO8601 string to UTC datetime (timezone-aware).

    Handles both 'Z' suffix and explicit timezone offsets.

    Args:
        timestamp_str: ISO8601 formatted string (e.g., "2025-11-10T14:30:00Z")

    Returns:
        Timezone-aware datetime in UTC

    Example:
        >>> parse_iso8601("2025-11-10T14:30:00Z")
        datetime(2025, 11, 10, 14, 30, 0, tzinfo=timezone.utc)
    """
    # Handle 'Z' suffix (Zulu time = UTC)
    if timestamp_str.endswith('Z'):
        timestamp_str = timestamp_str.replace('Z', '+00:00')

    dt = datetime.fromisoformat(timestamp_str)

    # Ensure timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


def parse_timestamp(value: Union[str, datetime, int, float]) -> datetime:
    """
    Parse various timestamp formats to datetime.

    Args:
        value: ISO8601 string, datetime object, or Unix epoch (int/float)

    Returns:
        Timezone-aware datetime in UTC

    Example:
        >>> parse_timestamp("2025-11-10T14:30:00Z")
        >>> parse_timestamp(1699627800)
        >>> parse_timestamp(datetime.now())
    """
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    if isinstance(value, str):
        return parse_iso8601(value)

    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)

    raise ValueError(f"Cannot parse timestamp from type {type(value)}")
```

##### **`app/common/datetime/formatter.py`** (40 LOC)
```python
"""Format datetime objects to strings."""

from datetime import datetime, timezone


def to_iso8601(dt: datetime) -> str:
    """
    Format datetime to ISO8601 string with 'Z' suffix.

    Args:
        dt: Datetime object (timezone-aware or naive)

    Returns:
        ISO8601 string with 'Z' suffix (e.g., "2025-11-10T14:30:00Z")

    Example:
        >>> to_iso8601(datetime(2025, 11, 10, 14, 30, 0, tzinfo=timezone.utc))
        "2025-11-10T14:30:00Z"
    """
    # Ensure timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # Convert to UTC and format
    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.isoformat().replace('+00:00', 'Z')


def format_relative(dt: datetime) -> str:
    """
    Format datetime as relative time string ("2m ago", "5h ago").

    Args:
        dt: Datetime object

    Returns:
        Human-readable relative time string

    Example:
        >>> format_relative(datetime.now() - timedelta(minutes=5))
        "5m ago"
    """
    from .utils import seconds_since

    elapsed = seconds_since(dt)

    if elapsed < 60:
        return "Just now"
    elif elapsed < 3600:
        mins = int(elapsed / 60)
        return f"{mins}m ago"
    elif elapsed < 86400:
        hours = int(elapsed / 3600)
        return f"{hours}h ago"
    else:
        days = int(elapsed / 86400)
        return f"{days}d ago"


def format_medical(dt: datetime) -> str:
    """
    Format datetime for medical records (24-hour format, ISO date).

    Args:
        dt: Datetime object

    Returns:
        Medical record format: "2025-11-10 14:30:00 UTC"

    Example:
        >>> format_medical(datetime(2025, 11, 10, 14, 30, 0, tzinfo=timezone.utc))
        "2025-11-10 14:30:00 UTC"
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
```

##### **`app/common/datetime/utils.py`** (30 LOC)
```python
"""Datetime utility functions."""

from datetime import datetime, timezone


def now_utc() -> datetime:
    """
    Get current UTC time (timezone-aware).

    Returns:
        Current datetime in UTC with timezone info

    Example:
        >>> now_utc()
        datetime(2025, 11, 10, 14, 30, 0, tzinfo=timezone.utc)
    """
    return datetime.now(timezone.utc)


def seconds_since(dt: datetime) -> float:
    """
    Get seconds elapsed since given datetime.

    Args:
        dt: Past datetime

    Returns:
        Seconds elapsed (float)

    Example:
        >>> dt = now_utc() - timedelta(minutes=5)
        >>> seconds_since(dt)
        300.0
    """
    return (now_utc() - dt).total_seconds()


def is_recent(dt: datetime, max_age_seconds: float) -> bool:
    """
    Check if datetime is within max age.

    Args:
        dt: Datetime to check
        max_age_seconds: Maximum age in seconds

    Returns:
        True if dt is within max_age_seconds of now

    Example:
        >>> dt = now_utc() - timedelta(minutes=2)
        >>> is_recent(dt, max_age_seconds=300)  # 5 minutes
        True
    """
    return seconds_since(dt) < max_age_seconds
```

#### **Frontend: `src/utils/datetime/`**

```
src/utils/datetime/
├── index.ts                 # Export public API
├── parser.ts                # Parse ISO8601 (25 LOC)
├── formatter.ts             # Format timestamps (35 LOC)
└── relative.ts              # Relative time formatting (30 LOC)
```

**Files to create:**

##### **`src/utils/datetime/index.ts`**
```typescript
/**
 * Datetime utilities - Single source of truth for timestamp operations.
 *
 * Usage:
 *   import { parseISO, formatISO, formatRelative } from '@/utils/datetime';
 */

export { parseISO, parseTimestamp } from './parser';
export { formatISO, formatMedical } from './formatter';
export { formatRelative, isRecent } from './relative';
```

##### **`src/utils/datetime/parser.ts`** (25 LOC)
```typescript
/**
 * Parse timestamp strings to Date objects.
 */

export function parseISO(isoString: string): Date {
  /**
   * Parse ISO8601 string to Date object.
   *
   * @param isoString - ISO8601 formatted string
   * @returns Date object
   *
   * @example
   * parseISO("2025-11-10T14:30:00Z")
   */
  return new Date(isoString);
}

export function parseTimestamp(value: string | number | Date): Date {
  /**
   * Parse various timestamp formats to Date.
   *
   * @param value - ISO string, Unix epoch, or Date object
   * @returns Date object
   */
  if (value instanceof Date) {
    return value;
  }

  if (typeof value === 'string') {
    return parseISO(value);
  }

  if (typeof value === 'number') {
    return new Date(value * 1000); // Assume Unix epoch in seconds
  }

  throw new Error(`Cannot parse timestamp from type ${typeof value}`);
}
```

##### **`src/utils/datetime/formatter.ts`** (35 LOC)
```typescript
/**
 * Format Date objects to strings.
 */

export function formatISO(date: Date): string {
  /**
   * Format Date to ISO8601 string.
   *
   * @param date - Date object
   * @returns ISO8601 string
   *
   * @example
   * formatISO(new Date()) // "2025-11-10T14:30:00.000Z"
   */
  return date.toISOString();
}

export function formatMedical(date: Date): string {
  /**
   * Format Date for medical records (24-hour format).
   *
   * @param date - Date object
   * @returns Medical format: "2025-11-10 14:30:00 UTC"
   *
   * @example
   * formatMedical(new Date()) // "2025-11-10 14:30:00 UTC"
   */
  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, '0');
  const day = String(date.getUTCDate()).padStart(2, '0');
  const hours = String(date.getUTCHours()).padStart(2, '0');
  const minutes = String(date.getUTCMinutes()).padStart(2, '0');
  const seconds = String(date.getUTCSeconds()).padStart(2, '0');

  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds} UTC`;
}
```

##### **`src/utils/datetime/relative.ts`** (30 LOC)
```typescript
/**
 * Relative time formatting.
 */

export function formatRelative(date: Date): string {
  /**
   * Format Date as relative time ("2m ago", "5h ago").
   *
   * @param date - Date object
   * @returns Relative time string
   *
   * @example
   * formatRelative(new Date(Date.now() - 300000)) // "5m ago"
   */
  const now = Date.now();
  const then = date.getTime();
  const diffMs = now - then;
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;

  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

export function isRecent(date: Date, maxAgeMs: number): boolean {
  /**
   * Check if date is within max age.
   *
   * @param date - Date to check
   * @param maxAgeMs - Maximum age in milliseconds
   * @returns True if date is recent
   */
  return (Date.now() - date.getTime()) < maxAgeMs;
}
```

---

### **Day 3-4: Waveform Utilities**

#### **Backend: `app/common/waveform/`**

```
app/common/waveform/
├── __init__.py              # Export public API
├── decoder.py               # Delta decompression (40 LOC)
├── converter.py             # ADC → mV/μV conversion (50 LOC)
├── validator.py             # Validate waveform data (40 LOC)
└── constants.py             # ADC constants (20 LOC)
```

**What gets deleted after migration:**
- ❌ Duplicate functions in `mqtt_service.py` lines 315-464
- ❌ Duplicate functions in `websocket_manager.py` lines 315-464

**Files to create:**

##### **`app/common/waveform/__init__.py`**
```python
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
```

##### **`app/common/waveform/constants.py`** (20 LOC)
```python
"""ADC and conversion constants."""

# 24-bit ADC midpoint (2^23)
ADC_MIDPOINT = 8388608

# ECG sensitivity (10 μV per LSB = 0.01 mV per LSB)
SENSITIVITY_MV = 0.01

# EEG sensitivity (1 μV per LSB)
SENSITIVITY_UV = 0.001

# Valid ADC range
ADC_MIN = 0
ADC_MAX = 16777215  # 2^24 - 1

# Maximum delta value (compression limit)
MAX_DELTA = 32767  # int16 max
```

##### **`app/common/waveform/decoder.py`** (40 LOC)
```python
"""Delta decompression for waveform data."""

from typing import List, Dict, Any


def decompress_delta(channel_data: Dict[str, Any]) -> List[int]:
    """
    Decompress delta-encoded channel data.

    Format: {baseline: int, deltas: List[int]}
    Returns: List of decompressed ADC values

    Args:
        channel_data: Dict with 'baseline' and 'deltas' keys

    Returns:
        List of reconstructed ADC values

    Example:
        >>> decompress_delta({'baseline': 8388608, 'deltas': [100, -50, 75]})
        [8388608, 8388708, 8388658, 8388733]
    """
    if not channel_data or 'baseline' not in channel_data or 'deltas' not in channel_data:
        return []

    baseline = channel_data['baseline']
    deltas = channel_data['deltas']

    # Reconstruct original values from delta encoding
    values = [baseline]
    for delta in deltas:
        values.append(values[-1] + delta)

    return values


def decompress_channel(channel: Dict[str, Any]) -> List[int]:
    """
    Decompress single channel with validation.

    Alias for decompress_delta with additional validation.

    Args:
        channel: Channel data dict

    Returns:
        List of ADC values

    Raises:
        ValueError: If channel data is invalid
    """
    if not isinstance(channel, dict):
        raise ValueError("Channel data must be a dictionary")

    if 'baseline' not in channel:
        raise ValueError("Channel data missing 'baseline'")

    if 'deltas' not in channel:
        raise ValueError("Channel data missing 'deltas'")

    return decompress_delta(channel)
```

##### **`app/common/waveform/converter.py`** (50 LOC)
```python
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
```

##### **`app/common/waveform/validator.py`** (40 LOC)
```python
"""Waveform data validation."""

from typing import Dict, Any, List
from .constants import ADC_MIN, ADC_MAX, MAX_DELTA


def validate_waveform_data(waveform: Dict[str, Any]) -> tuple[bool, str]:
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
```

#### **Frontend: `src/utils/waveform/`**

```
src/utils/waveform/
├── index.ts                 # Export public API
├── decoder.ts               # Delta decompression (30 LOC)
├── converter.ts             # ADC conversion (40 LOC)
└── constants.ts             # ADC constants (15 LOC)
```

---

### **Day 5: Alert Rules (Backend Only)**

#### **Backend: `app/domain/alerts/rules/`**

```
app/domain/alerts/rules/
├── __init__.py              # Export public API
├── thresholds.py            # Vital thresholds (SSOT) (60 LOC)
├── checker.py               # Check threshold breaches (50 LOC)
└── constants.py             # Alert severity levels (20 LOC)
```

**What gets deleted after migration:**
- ❌ Inline threshold checks in `mqtt_service.py` lines 646-776
- ❌ Duplicate thresholds in `pipeline.py`

**Files to create:**

##### **`app/domain/alerts/rules/__init__.py`**
```python
"""
Alert rules - Single source of truth for alert thresholds and checking.

Usage:
    from app.domain.alerts.rules import VITAL_THRESHOLDS, check_vital_threshold

    # Check if heart rate breaches threshold
    result = check_vital_threshold('heartrate', 125)
    if result:
        severity, threshold_value = result
        print(f"Alert! HR {125} exceeds threshold {threshold_value} (severity: {severity})")
"""

from .thresholds import VITAL_THRESHOLDS
from .checker import check_vital_threshold, check_all_vitals
from .constants import AlertSeverity, AlertType

__all__ = [
    'VITAL_THRESHOLDS',
    'check_vital_threshold',
    'check_all_vitals',
    'AlertSeverity',
    'AlertType'
]
```

##### **`app/domain/alerts/rules/constants.py`** (20 LOC)
```python
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
```

##### **`app/domain/alerts/rules/thresholds.py`** (60 LOC)
```python
"""
Vital sign thresholds - Single source of truth.

IMPORTANT: These thresholds are for ALERTING purposes.
Clinical normal ranges may differ. Consult medical staff before changing.

Indian Medical Guidelines Compliance:
- Heart Rate: Based on Indian Council of Medical Research (ICMR) guidelines
- SpO2: COVID-19 management guidelines (AIIMS/ICMR)
- Temperature: Standard Celsius ranges per Indian medical practice
"""

from typing import Dict, Any, Optional

# SINGLE SOURCE OF TRUTH for all vital thresholds
VITAL_THRESHOLDS: Dict[str, Dict[str, Any]] = {
    'heartrate': {
        'unit': 'bpm',
        'criticalLow': 40,      # Severe bradycardia
        'warningLow': 50,       # Bradycardia
        'warningHigh': 120,     # Tachycardia
        'criticalHigh': 150,    # Severe tachycardia
        'normalRange': (60, 100)
    },

    'oxygen': {
        'unit': '%',
        'criticalLow': 85,      # Severe hypoxia (per ICMR COVID guidelines)
        'warningLow': 90,       # Hypoxia
        'warningHigh': None,    # No upper limit for SpO2
        'criticalHigh': None,
        'normalRange': (95, 100)
    },

    'temperature': {
        'unit': '°C',
        'criticalLow': 35.0,    # Hypothermia
        'warningLow': 36.0,     # Low-grade hypothermia
        'warningHigh': 38.0,    # Fever
        'criticalHigh': 39.5,   # High fever
        'normalRange': (36.5, 37.5)
    },

    'respiratory': {
        'unit': '/min',
        'criticalLow': 8,       # Respiratory depression
        'warningLow': 10,       # Bradypnea
        'warningHigh': 24,      # Tachypnea
        'criticalHigh': 30,     # Severe tachypnea
        'normalRange': (12, 20)
    },

    'systolic': {
        'unit': 'mmHg',
        'criticalLow': 90,      # Hypotension
        'warningLow': 100,      # Low BP
        'warningHigh': 140,     # Hypertension
        'criticalHigh': 180,    # Severe hypertension
        'normalRange': (110, 130)
    },

    'diastolic': {
        'unit': 'mmHg',
        'criticalLow': 60,      # Hypotension
        'warningLow': 65,       # Low BP
        'warningHigh': 90,      # Hypertension
        'criticalHigh': 110,    # Severe hypertension
        'normalRange': (70, 85)
    }
}


def get_threshold(vital_type: str) -> Optional[Dict[str, Any]]:
    """Get threshold configuration for vital type."""
    return VITAL_THRESHOLDS.get(vital_type)
```

##### **`app/domain/alerts/rules/checker.py`** (50 LOC)
```python
"""Check vital values against thresholds."""

from typing import Optional, Tuple, Dict, List
from .thresholds import VITAL_THRESHOLDS
from .constants import AlertSeverity


def check_vital_threshold(
    vital_type: str,
    value: float
) -> Optional[Tuple[AlertSeverity, float, str]]:
    """
    Check if vital value breaches threshold.

    Args:
        vital_type: Type of vital (heartrate, oxygen, temperature, etc.)
        value: Current vital value

    Returns:
        Tuple of (severity, threshold_value, message_prefix) if breach detected
        None if value is within normal range

    Example:
        >>> check_vital_threshold('heartrate', 125)
        ('high', 120, 'High')

        >>> check_vital_threshold('heartrate', 75)
        None  # Normal range
    """
    # Check if vital type has thresholds
    if vital_type not in VITAL_THRESHOLDS:
        return None

    threshold = VITAL_THRESHOLDS[vital_type]

    # Check critical low
    if threshold.get('criticalLow') is not None and value <= threshold['criticalLow']:
        return ('critical', threshold['criticalLow'], 'Critical Low')

    # Check critical high
    if threshold.get('criticalHigh') is not None and value >= threshold['criticalHigh']:
        return ('critical', threshold['criticalHigh'], 'Critical High')

    # Check warning low
    if threshold.get('warningLow') is not None and value <= threshold['warningLow']:
        return ('high', threshold['warningLow'], 'Low')

    # Check warning high
    if threshold.get('warningHigh') is not None and value >= threshold['warningHigh']:
        return ('high', threshold['warningHigh'], 'High')

    # Value is within normal range
    return None


def check_all_vitals(vitals: Dict[str, float]) -> List[Tuple[str, AlertSeverity, float, str]]:
    """
    Check all vitals and return list of alerts.

    Args:
        vitals: Dict of vital_type -> value

    Returns:
        List of tuples: (vital_type, severity, threshold_value, message_prefix)

    Example:
        >>> check_all_vitals({'heartrate': 125, 'oxygen': 88})
        [('heartrate', 'high', 120, 'High'), ('oxygen', 'critical', 85, 'Critical Low')]
    """
    alerts = []

    for vital_type, value in vitals.items():
        result = check_vital_threshold(vital_type, value)
        if result:
            severity, threshold_value, message_prefix = result
            alerts.append((vital_type, severity, threshold_value, message_prefix))

    return alerts
```

---

## 📦 PHASE 2: API & DATA LAYER (Week 2)

**Goal:** Unified API clients and data mapping

### **Day 6-7: Backend Query Layer**

#### **`app/common/queries/`**

```
app/common/queries/
├── __init__.py              # Export public API
├── cache.py                 # Prepared statement cache (50 LOC)
├── patient.py               # Patient queries (50 LOC)
├── device.py                # Device queries (50 LOC)
└── vitals.py                # Vitals queries (50 LOC)
```

**What gets deleted:**
- ❌ 15+ inline queries across `mqtt_service.py`, `websocket_manager.py`

---

### **Day 8-9: Frontend API Client**

#### **`src/lib/api/`**

```
src/lib/api/
├── index.ts                 # Export public API
├── client.ts                # Core HTTP client (50 LOC)
├── interceptors.ts          # Request/response interceptors (40 LOC)
├── retry.ts                 # Retry logic (30 LOC)
└── errors.ts                # Error handling (40 LOC)
```

**What gets deleted:**
- ❌ 8 different service classes in `src/services/`

---

### **Day 10: Frontend WebSocket Client**

#### **`src/lib/ws/`**

```
src/lib/ws/
├── index.ts                 # Export public API
├── client.ts                # WebSocket connection (60 LOC)
├── reconnect.ts             # Reconnection logic (40 LOC)
├── heartbeat.ts             # Heartbeat mechanism (30 LOC)
├── queue.ts                 # Offline message queue (40 LOC)
└── router.ts                # Message routing (30 LOC)
```

**What gets deleted:**
- ❌ `src/services/WebSocketService.ts` (200+ LOC)

---

## 📦 PHASE 3: DOMAIN LAYER REFACTOR (Week 3)

**Goal:** Clean up domain logic, extract to small modules

### **Day 11-12: Alert Pipeline Cleanup**

#### **`app/domain/alerts/`**

```
app/domain/alerts/
├── __init__.py
├── pipeline.py              # Main alert pipeline (80 LOC) - REFACTORED
├── deduplicator.py          # Deduplication (60 LOC) - KEEP AS IS
├── formatter.py             # Alert message formatting (40 LOC) - NEW
├── rules/                   # (Already created in Phase 1)
│   ├── thresholds.py
│   ├── checker.py
│   └── constants.py
└── generators/              # NEW: Split alert generation logic
    ├── __init__.py
    ├── vital.py             # Generate vital alerts (40 LOC)
    ├── arrhythmia.py        # Generate arrhythmia alerts (40 LOC)
    └── device.py            # Generate device alerts (30 LOC)
```

**What gets deleted:**
- ❌ Inline alert generation in `mqtt_service.py` lines 646-776 (130 LOC deleted!)

---

### **Day 13-14: Vitals & Waveform Domain**

#### **`app/domain/vitals/`**

```
app/domain/vitals/
├── __init__.py
├── normalizer.py            # Normalize vitals (50 LOC) - KEEP, REFACTOR
├── validator.py             # Validate vitals (50 LOC) - KEEP, REFACTOR
├── ranges.py                # Valid ranges (30 LOC) - NEW
└── units.py                 # Unit conversions (40 LOC) - NEW
```

#### **`app/domain/waveform/`**

```
app/domain/waveform/
├── __init__.py
├── ecg/
│   ├── __init__.py
│   ├── decoder.py           # ECG-specific decoding (40 LOC)
│   ├── leads.py             # Lead name constants (20 LOC)
│   └── validator.py         # Validate ECG data (40 LOC)
└── eeg/
    ├── __init__.py
    ├── decoder.py           # EEG-specific decoding (40 LOC)
    ├── channels.py          # Channel name constants (20 LOC)
    └── validator.py         # Validate EEG data (40 LOC)
```

---

### **Day 15: Frontend Data Mappers**

#### **`src/data/mappers/`**

```
src/data/mappers/
├── patient/
│   ├── index.ts
│   ├── fromAPI.ts           # API → domain (30 LOC)
│   └── toAPI.ts             # Domain → API (30 LOC)
├── vitals/
│   ├── index.ts
│   ├── fromAPI.ts           # Map vitals from API (40 LOC)
│   └── normalize.ts         # Normalize vitals (30 LOC)
└── alerts/
    ├── index.ts
    ├── fromAPI.ts           # Map alerts from API (30 LOC)
    └── format.ts            # Format alert messages (25 LOC)
```

---

## 📦 PHASE 4: INTEGRATION & MIGRATION (Week 4)

**Goal:** Replace old code with new shared modules

### **Day 16-17: Backend Migration**

**Tasks:**
1. Replace timestamp code in `mqtt_service.py` with `app.common.datetime`
2. Replace waveform code in `mqtt_service.py` with `app.common.waveform`
3. Replace waveform code in `websocket_manager.py` with `app.common.waveform`
4. Replace alert generation in `mqtt_service.py` with `app.domain.alerts.pipeline`

**Expected Deletions:**
- ❌ ~300 lines of duplicate code deleted
- ✅ Imports changed to use shared modules

---

### **Day 18-19: Frontend Migration**

**Tasks:**
1. Replace all timestamp code with `src/utils/datetime`
2. Replace WebSocket service with `src/lib/ws`
3. Replace individual API services with `src/lib/api`
4. Update components to use data mappers

**Expected Deletions:**
- ❌ ~400 lines of duplicate code deleted
- ✅ 8 service files consolidated into 2 client modules

---

### **Day 20: Testing & Validation**

**Tasks:**
1. Write unit tests for all shared modules (>90% coverage)
2. Integration tests for alert pipeline
3. E2E test for vitals flow (ESP32 → DB → WebSocket → Frontend)
4. Load test (100 devices, 1000 msg/sec)

---

## 📏 SUCCESS METRICS

### **Code Quality Metrics:**

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Code duplication | 40-50% | <10% | ✅ |
| Avg file size | 200 LOC | 40-60 LOC | ✅ |
| Cyclomatic complexity | 18 | <8 | ✅ |
| Functions > 50 LOC | 30+ | <5 | ✅ |

### **Performance Metrics:**

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Alert E2E latency (p95) | 1.2s | <300ms | ✅ |
| WS broadcast (10 clients) | 800ms | <100ms | ✅ |
| Query time (patient lookup) | 15ms | <5ms | ✅ |

### **Developer Experience:**

| Metric | Before | After |
|--------|--------|-------|
| Time to fix alert bug | 3 files, 30 min | 1 file, 5 min |
| Time to add new vital threshold | 3 files, 20 min | 1 file, 2 min |
| Lines changed for timestamp fix | 50+ | 1 import |

---

## 🚀 ROLLOUT STRATEGY

### **Week 1: Shared Utilities (Phase 1)**
- Create all utility modules
- NO deletions yet
- New code uses new modules
- Old code still works

### **Week 2: API/Data Layer (Phase 2)**
- Create API clients
- NO deletions yet
- Run side-by-side with old code

### **Week 3: Domain Refactor (Phase 3)**
- Extract domain logic
- Feature flag: `USE_NEW_ALERT_PIPELINE`
- Test with 10% traffic

### **Week 4: Migration (Phase 4)**
- Replace old code with new
- Delete duplicate code
- 100% traffic to new code

---

## 📋 DELIVERABLES BY WEEK

### **End of Week 1:**
- ✅ 12 backend utility modules (~480 LOC)
- ✅ 10 frontend utility modules (~350 LOC)
- ✅ Unit tests for all utilities (>90% coverage)
- ✅ Migration guide document

### **End of Week 2:**
- ✅ Unified API client (backend + frontend)
- ✅ WebSocket client with reconnection
- ✅ Query layer with prepared statements
- ✅ Integration tests

### **End of Week 3:**
- ✅ Refactored alert pipeline
- ✅ Refactored vitals/waveform domain
- ✅ Data mappers
- ✅ Feature flags in place

### **End of Week 4:**
- ✅ All old code replaced
- ✅ ~700 lines of duplicate code deleted
- ✅ Performance benchmarks met
- ✅ E2E tests passing

---

## 🔄 ROLLBACK PLAN

**If anything breaks:**

1. **Revert to backup tag:**
   ```bash
   git checkout backup-before-refactor-20251110-145117
   ```

2. **Feature flag rollback:**
   ```python
   # .env
   USE_NEW_ALERT_PIPELINE=false
   USE_NEW_WS_CLIENT=false
   ```

3. **Partial rollback:**
   - Revert specific module: `git revert <commit-hash>`
   - Keep utilities, rollback domain layer

---

## ❓ QUESTIONS FOR YOU

Before I start generating files:

1. **Do you want me to start with Phase 1 (Week 1) utilities?**
   - I'll create all 22 utility modules (~830 LOC total)
   - Small, focused files (30-60 LOC each)
   - Complete with tests

2. **Should I create a migration checklist?**
   - Exact steps to replace old code with new
   - File-by-file instructions
   - Before/after examples

3. **Do you want CI/CD pipeline now or later?**
   - GitHub Actions workflows
   - Coverage gates, lint checks
   - Or wait until Week 4?

---

**Ready to start?** Tell me which phase to begin with!
