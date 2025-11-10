# Phase 1 Migration Guide - Shared Utilities

**Created:** 2025-11-10
**Branch:** `refactor/clean-slate-phase1-shared-modules`
**Status:** ✅ All 21 utility modules created

---

## ✅ WHAT WAS CREATED

### **Backend (13 files)**

#### `app/common/datetime/` (4 files)
- ✅ `__init__.py` - Public API exports
- ✅ `parser.py` - Parse ISO8601, handle timezones (40 LOC)
- ✅ `formatter.py` - Format to ISO8601, relative time (40 LOC)
- ✅ `utils.py` - now_utc(), seconds_since(), is_recent() (30 LOC)

#### `app/common/waveform/` (5 files)
- ✅ `__init__.py` - Public API exports
- ✅ `constants.py` - ADC constants (20 LOC)
- ✅ `decoder.py` - Delta decompression (40 LOC)
- ✅ `converter.py` - ADC → mV/μV conversion (50 LOC)
- ✅ `validator.py` - Validate waveform data (40 LOC)

#### `app/domain/alerts/rules/` (4 files)
- ✅ `__init__.py` - Public API exports
- ✅ `constants.py` - Alert severity levels (20 LOC)
- ✅ `thresholds.py` - Vital thresholds SSOT (60 LOC)
- ✅ `checker.py` - Check threshold breaches (50 LOC)

### **Frontend (8 files)**

#### `src/utils/datetime/` (4 files)
- ✅ `index.ts` - Public API exports
- ✅ `parser.ts` - Parse ISO8601 (25 LOC)
- ✅ `formatter.ts` - Format timestamps (35 LOC)
- ✅ `relative.ts` - Relative time formatting (30 LOC)

#### `src/utils/waveform/` (4 files)
- ✅ `index.ts` - Public API exports
- ✅ `constants.ts` - ADC constants (15 LOC)
- ✅ `decoder.ts` - Delta decompression (30 LOC)
- ✅ `converter.ts` - ADC conversion (40 LOC)

**Total:** 21 files, ~630 lines of code

---

## 📖 HOW TO USE THE NEW MODULES

### **Backend Usage Examples**

#### **1. Datetime Utilities**

**OLD CODE (scattered patterns):**
```python
# Pattern 1 (mqtt_service.py)
timestamp = datetime.now()

# Pattern 2 (websocket_manager.py)
timestamp = datetime.utcnow().isoformat()

# Pattern 3 (pipeline.py)
from app.common import to_utc_now
timestamp = to_utc_now()

# Pattern 4 (mqtt_service.py)
messageTimestamp = datetime.fromisoformat(messageTimestamp.replace('Z', '+00:00'))
```

**NEW CODE (single source of truth):**
```python
from app.common.datetime import now_utc, parse_iso8601, to_iso8601, format_relative

# Get current UTC time (timezone-aware)
timestamp = now_utc()

# Parse ISO8601 string
dt = parse_iso8601("2025-11-10T14:30:00Z")

# Format datetime to ISO8601
iso_string = to_iso8601(timestamp)

# Format as relative time ("5m ago")
relative = format_relative(timestamp)
```

---

#### **2. Waveform Utilities**

**OLD CODE (duplicated in mqtt_service.py and websocket_manager.py):**
```python
# Duplicate function in mqtt_service.py:315-375
def decompressChannelData(channelData):
    if not channelData or 'baseline' not in channelData:
        return []
    baseline = channelData['baseline']
    deltas = channelData['deltas']
    values = [baseline]
    for delta in deltas:
        values.append(values[-1] + delta)
    return values

# Duplicate function in mqtt_service.py:377-390
def convertADCToMillivolts(adcValues):
    ADC_MIDPOINT = 8388608
    SENSITIVITY = 0.01
    return [(value - ADC_MIDPOINT) * SENSITIVITY for value in adcValues]

# SAME FUNCTIONS duplicated in websocket_manager.py:315-464
```

**NEW CODE (single source of truth):**
```python
from app.common.waveform import decompress_delta, adc_to_millivolts, adc_to_microvolts

# Decompress delta-encoded channel
channel_data = {'baseline': 8388608, 'deltas': [100, -50, 75]}
adc_values = decompress_delta(channel_data)

# Convert to millivolts (ECG)
mv_values = adc_to_millivolts(adc_values)

# Convert to microvolts (EEG)
uv_values = adc_to_microvolts(adc_values)
```

---

#### **3. Alert Rules**

**OLD CODE (duplicated threshold checks):**
```python
# In mqtt_service.py:646-776 (inline threshold checks)
if heartRate > 120:
    severity = 'high'
    message = f'High Heart Rate: {heartRate}bpm'
elif heartRate < 50:
    severity = 'high'
    message = f'Low Heart Rate: {heartRate}bpm'
elif heartRate > 150:
    severity = 'critical'
    message = f'Critical High Heart Rate: {heartRate}bpm'

# In pipeline.py (duplicate threshold logic)
if vital_value <= threshold.get('criticalLow', float('-inf')):
    severity = 'critical'
# ... same logic repeated
```

**NEW CODE (single source of truth):**
```python
from app.domain.alerts.rules import check_vital_threshold, VITAL_THRESHOLDS

# Check if heart rate breaches threshold
result = check_vital_threshold('heartrate', 125)
if result:
    severity, threshold_value, message_prefix = result
    message = f"{message_prefix} Heart Rate: {125}bpm"
    # severity = 'high', threshold_value = 120, message_prefix = 'High'

# Check all vitals at once
from app.domain.alerts.rules import check_all_vitals

vitals = {'heartrate': 125, 'oxygen': 88, 'temperature': 39.0}
alerts = check_all_vitals(vitals)
for vital_type, severity, threshold_value, message_prefix in alerts:
    print(f"Alert: {message_prefix} {vital_type} = {vitals[vital_type]}")
```

---

### **Frontend Usage Examples**

#### **1. Datetime Utilities**

**OLD CODE:**
```typescript
// Scattered timestamp parsing
const date1 = new Date(timestamp);
const date2 = new Date(timestamp.replace('Z', '+00:00'));
const date3 = parseISO(timestamp); // from date-fns

// Scattered formatting
const formatted1 = date.toISOString();
const formatted2 = formatDistanceToNow(date); // from date-fns
```

**NEW CODE:**
```typescript
import { parseISO, formatISO, formatRelative, isRecent } from '@/utils/datetime';

// Parse timestamp
const date = parseISO("2025-11-10T14:30:00Z");

// Format timestamp
const isoString = formatISO(date);

// Format as relative time
const relative = formatRelative(date); // "5m ago"

// Check if recent
const recent = isRecent(date, 300000); // Within 5 minutes?
```

---

#### **2. Waveform Utilities**

**OLD CODE:**
```typescript
// Inline decompression logic
function decompressDelta(channelData: any) {
  const values = [channelData.baseline];
  for (const delta of channelData.deltas) {
    values.push(values[values.length - 1] + delta);
  }
  return values;
}

// Inline ADC conversion
const ADC_MIDPOINT = 8388608;
const mv = adcValues.map(v => (v - ADC_MIDPOINT) * 0.01);
```

**NEW CODE:**
```typescript
import { decompressDelta, adcToMillivolts, ADC_MIDPOINT } from '@/utils/waveform';

// Decompress channel data
const channelData = { baseline: 8388608, deltas: [100, -50, 75] };
const adcValues = decompressDelta(channelData);

// Convert to millivolts
const mvValues = adcToMillivolts(adcValues);
```

---

## 🔄 MIGRATION STEPS (OPTIONAL - NOT REQUIRED YET)

**IMPORTANT:** You can start using the new modules immediately in NEW code. Old code can be migrated incrementally.

### **When to Migrate:**

**Option 1: Gradual (Recommended)**
- Use new modules in all NEW code
- Migrate old code file-by-file as you touch it
- No urgency, no risk

**Option 2: Aggressive (Week 4 of plan)**
- Replace all old code systematically
- Delete duplicate functions
- Requires testing

---

## 📊 IMPACT ANALYSIS

### **What can be deleted AFTER migration:**

#### **Backend:**
1. **Datetime duplicates (~150 LOC):**
   - `mqtt_service.py`: Various timestamp patterns
   - `websocket_manager.py`: `datetime.now()` calls
   - `pipeline.py`: Manual timezone handling

2. **Waveform duplicates (~240 LOC):**
   - `mqtt_service.py` lines 315-464
   - `websocket_manager.py` lines 315-464

3. **Alert threshold duplicates (~130 LOC):**
   - `mqtt_service.py` lines 646-776 (inline threshold checks)

**Total deletable: ~520 LOC**

#### **Frontend:**
1. **Datetime duplicates (~80 LOC):**
   - Various components with inline date parsing
   - Multiple relative time formatters

2. **Waveform duplicates (~60 LOC):**
   - Inline decompression logic in waveform components

**Total deletable: ~140 LOC**

### **Net Result:**
- **Before:** ~660 LOC of duplicated code
- **After:** 630 LOC of modular, reusable code
- **Savings:** ~30 LOC + massive maintainability gain

---

## ✅ NEXT STEPS

### **Immediate (Today):**
1. ✅ Review the generated modules (DONE)
2. ✅ Test importing the new modules
3. ✅ Use new modules in any NEW code you write

### **Short-term (This Week):**
1. Update one file to use new datetime utilities (proof of concept)
2. Measure impact (lines changed, bugs found, developer experience)
3. Decide on migration pace

### **Long-term (Week 4):**
1. Systematically replace old code with new modules
2. Delete duplicate functions
3. Run full test suite

---

## 🧪 TESTING THE NEW MODULES

### **Backend Tests (Python)**

```python
# Test datetime utilities
from app.common.datetime import now_utc, parse_iso8601, to_iso8601

def test_datetime_utils():
    # Test now_utc
    now = now_utc()
    assert now.tzinfo is not None

    # Test parse_iso8601
    dt = parse_iso8601("2025-11-10T14:30:00Z")
    assert dt.year == 2025
    assert dt.month == 11

    # Test to_iso8601
    iso = to_iso8601(dt)
    assert iso.endswith('Z')

# Test waveform utilities
from app.common.waveform import decompress_delta, adc_to_millivolts

def test_waveform_utils():
    # Test decompress_delta
    channel = {'baseline': 8388608, 'deltas': [100, -50, 75]}
    values = decompress_delta(channel)
    assert len(values) == 4
    assert values[0] == 8388608
    assert values[1] == 8388708

    # Test adc_to_millivolts
    mv = adc_to_millivolts([8388608])
    assert mv[0] == 0.0

# Test alert rules
from app.domain.alerts.rules import check_vital_threshold

def test_alert_rules():
    # Test normal heart rate (no alert)
    result = check_vital_threshold('heartrate', 75)
    assert result is None

    # Test high heart rate
    result = check_vital_threshold('heartrate', 125)
    assert result is not None
    severity, threshold, prefix = result
    assert severity == 'high'
    assert threshold == 120
    assert prefix == 'High'
```

### **Frontend Tests (TypeScript/Jest)**

```typescript
import { parseISO, formatRelative } from '@/utils/datetime';
import { decompressDelta, adcToMillivolts } from '@/utils/waveform';

describe('Datetime utilities', () => {
  test('parseISO', () => {
    const date = parseISO("2025-11-10T14:30:00Z");
    expect(date.getFullYear()).toBe(2025);
  });

  test('formatRelative', () => {
    const fiveMinutesAgo = new Date(Date.now() - 300000);
    const relative = formatRelative(fiveMinutesAgo);
    expect(relative).toBe('5m ago');
  });
});

describe('Waveform utilities', () => {
  test('decompressDelta', () => {
    const channel = { baseline: 8388608, deltas: [100, -50, 75] };
    const values = decompressDelta(channel);
    expect(values).toHaveLength(4);
    expect(values[0]).toBe(8388608);
  });

  test('adcToMillivolts', () => {
    const mv = adcToMillivolts([8388608]);
    expect(mv[0]).toBe(0.0);
  });
});
```

---

## 🚨 TROUBLESHOOTING

### **Import Error: "Cannot find module 'app.common.datetime'"**

**Solution:** Make sure `app/common/datetime/__init__.py` exists and exports the functions.

---

### **Type Error: "Argument of type 'datetime' is not assignable..."**

**Solution:** The new utilities return timezone-aware datetimes. Update type hints if needed.

**Before:**
```python
def process_timestamp(dt: datetime) -> None:
    ...
```

**After:**
```python
from datetime import datetime

def process_timestamp(dt: datetime) -> None:
    # dt is now timezone-aware
    if dt.tzinfo is None:
        raise ValueError("Expected timezone-aware datetime")
```

---

### **Frontend: Path alias not working**

**Solution:** Ensure `tsconfig.json` has the `@/` alias configured:

```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

---

## 📞 SUPPORT

**Questions or issues?**
- Check the inline documentation in each module
- Review the examples in this guide
- Ask the team in Slack #refactor-phase1

---

## 🎉 SUCCESS!

**You now have:**
- ✅ 21 small, focused utility modules
- ✅ Single source of truth for datetime, waveform, alert rules
- ✅ No breaking changes (old code still works)
- ✅ Ready to start using in new code

**Next:** Start using these modules in your next feature!
