# ESP32 Firmware v5.2.8 - DC Offset Fix for Derived Leads

**Date:** 2025-11-04
**Firmware Version:** v5.2.8
**Critical Bugfix:** DC offset removal for derived ECG leads

---

## Problem Diagnosed

### Symptoms
- Lead III, aVR, aVL, and aVF displayed **flat lines** (no waveforms)
- Lead I, Lead II, and V1-V6 displayed proper waveforms
- Issue persisted despite v5.2.7 Goldberger formula corrections

### Root Cause
The derived lead calculations were operating on **absolute ADC values** (~8,388,608 ± 100,000) instead of relative values.

**Example calculation that failed:**
```cpp
// WRONG - operating on absolute ADC values
int32_t leadI = 8,388,608 + 100,000;  // ADC value for Lead I
int32_t leadII = 8,388,608 + 50,000;  // ADC value for Lead II

avrArray[i] = -(3 * (leadI + leadII)) / 4;
            = -(3 * (8,488,608 + 8,438,608)) / 4
            = -(3 * 16,927,216) / 4
            = -12,695,412  // WAY OFF SCALE! Should be near 8,388,608
```

**Why this caused flat lines:**
- ADC midpoint: 8,388,608 (represents 0mV)
- Normal ECG signal: ±1mV = ±100,000 ADC units
- When adding two large numbers (~16.7M) and multiplying by 3, then dividing by 4:
  - Result was ~-12.6M or similar massive offset
  - Frontend saw this as completely out of range
  - Displayed as flat line at bottom of canvas

---

## Solution Implemented

### Fix Strategy
**Subtract DC offset BEFORE calculations, then add it back:**

```cpp
// ✅ CORRECT - work in relative space
int32_t leadI_rel = leadI - 8388608;      // Convert to relative (-100k to +100k)
int32_t leadII_rel = leadII - 8388608;    // Convert to relative

// Calculate in relative space
int32_t avr_rel = -(3 * (leadI_rel + leadII_rel)) / 4;

// Convert back to absolute ADC value
avrArray[i] = avr_rel + 8388608;
```

### Changes Made

**File:** `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`

#### 1. Lead III Fix (Lines 1980-1988)
```cpp
// Calculate lead III array (Lead III = II - I)
// ✅ CRITICAL: Subtract DC offset before calculating derived lead
int32_t lead3Array[50];
for (int i = 0; i < 50; i++) {
  int32_t leadI_rel = waveformAccumulator[0][i] - 8388608;
  int32_t leadII_rel = waveformAccumulator[1][i] - 8388608;
  int32_t lead3_rel = leadII_rel - leadI_rel;
  lead3Array[i] = lead3_rel + 8388608;  // Convert back to absolute
}
```

#### 2. Augmented Leads Fix (Lines 2013-2027)
```cpp
for (int i = 0; i < 50; i++) {
  int32_t leadI = waveformAccumulator[0][i];
  int32_t leadII = waveformAccumulator[1][i];

  // ✅ CRITICAL: Subtract DC offset (ADC midpoint) before calculating derived leads
  // ADC values are ~8,388,608 ± 100,000, we need to work with relative values
  int32_t leadI_rel = leadI - 8388608;
  int32_t leadII_rel = leadII - 8388608;

  // Goldberger augmented lead formulas (1.5x amplified) in relative space:
  int32_t avr_rel = -(3 * (leadI_rel + leadII_rel)) / 4;        // aVR = -1.5*(I+II)/2
  int32_t avl_rel = (3 * (2 * leadI_rel - leadII_rel)) / 4;     // aVL = 1.5*(2I-II)/2
  int32_t avf_rel = (3 * (2 * leadII_rel - leadI_rel)) / 4;     // aVF = 1.5*(2II-I)/2

  // Convert back to absolute ADC values
  avrArray[i] = avr_rel + 8388608;
  avlArray[i] = avl_rel + 8388608;
  avfArray[i] = avf_rel + 8388608;
}
```

#### 3. Version and Documentation Updates
- Updated `FIRMWARE_VERSION` to "5.2.8"
- Added changelog entries explaining DC offset fix
- Updated Serial.println messages to mention v5.2.8 fix

---

## Technical Explanation

### ADC Value Structure
```
ADS1298 24-bit ADC:
- Range: 0 to 16,777,215
- Midpoint: 8,388,608 (represents 0 volts)
- Scale: 1mV = 100,000 ADC units (configured in PhysiologicalSimulator)

ECG Signal Example:
- Baseline: 8,388,608 ADC units = 0mV
- +1mV signal: 8,488,608 ADC units
- -1mV signal: 8,288,608 ADC units
```

### Why Relative Space is Required

**Mathematical Reason:**
- ECG formulas (Lead III = II - I, aVR = -1.5*(I+II)/2) assume 0V baseline
- ADC uses 8,388,608 as 0V baseline
- Must remove DC offset to apply formulas correctly

**Example with numbers:**
```
Lead I: +0.5mV = 8,438,608 ADC units
Lead II: +1.0mV = 8,488,608 ADC units

WRONG (absolute space):
aVR = -(3 * (8,438,608 + 8,488,608)) / 4
    = -(3 * 16,927,216) / 4
    = -12,695,412  ❌ Completely wrong!

CORRECT (relative space):
leadI_rel = 8,438,608 - 8,388,608 = 50,000 (= +0.5mV)
leadII_rel = 8,488,608 - 8,388,608 = 100,000 (= +1.0mV)
avr_rel = -(3 * (50,000 + 100,000)) / 4
        = -(3 * 150,000) / 4
        = -112,500 (= -1.125mV) ✅ Correct!
avrArray[i] = -112,500 + 8,388,608 = 8,276,108 ADC units ✅
```

---

## Expected Results After Fix

### All 12 ECG Leads Should Display Waveforms:
1. **Limb Leads:** I, II, III ✅
2. **Augmented Leads:** aVR, aVL, aVF ✅
3. **Precordial Leads:** V1, V2, V3, V4, V5, V6 ✅

### Waveform Characteristics:
- Lead III should show waveform (II - I difference)
- aVR should show inverted waveform (negative deflections)
- aVL should show proper QRS complexes
- aVF should show proper QRS complexes
- All amplitudes should be physiologically correct

---

## Testing Instructions

### 1. Flash Updated Firmware
```bash
# Flash ESP32 with v5.2.8 firmware
arduino-cli upload --fqbn esp32:esp32:esp32 -p COM_PORT esp32_hospital_watch_complete/
```

### 2. Open ECG Viewer
- Navigate to patient detail page
- Click "View ECG" button
- Fullscreen ECG viewer should open

### 3. Verify All Leads Display Waveforms
Check these specific leads that were previously flat:
- ✅ Lead III (bottom left in limb section)
- ✅ aVR (top right in augmented section)
- ✅ aVL (middle right in augmented section)
- ✅ aVF (bottom right in augmented section)

### 4. Check Console Logs
Look for ESP32 serial output:
```
✅ v5.2.8: DC offset FIXED | Lead III/aVR/aVL/aVF working | Goldberger 1.5x amplification
```

---

## Files Modified

| File | Lines Changed | Description |
|------|---------------|-------------|
| `esp32_hospital_watch_complete.ino` | 1980-1988 | Lead III DC offset fix |
| `esp32_hospital_watch_complete.ino` | 2013-2027 | aVR/aVL/aVF DC offset fix |
| `esp32_hospital_watch_complete.ino` | 28-29, 55-59, 81, 967, 972, 1065 | Version updates to v5.2.8 |

---

## Version History

| Version | Date | Fix |
|---------|------|-----|
| v5.2.5 | 2025-11-03 | Delta encoding implementation |
| v5.2.6 | 2025-11-03 | NFC + critical timing bugfix |
| v5.2.7 | 2025-11-04 | Goldberger formula corrections |
| **v5.2.8** | **2025-11-04** | **DC offset removal for derived leads** ✅ |

---

## Conclusion

This fix resolves the **root cause** of flat-line derived leads by ensuring all ECG calculations operate in relative voltage space (±mV) rather than absolute ADC space (~8.3M units).

**Status:** ✅ **READY TO FLASH AND TEST**

All 12 ECG leads should now display proper waveforms with correct amplitudes.
