# Mode Switching Bug - Diagnosis and Fix Plan

**Date:** 2025-11-04
**Status:** 🔴 **BUG CONFIRMED** - Old data persists when swapping ECG/EEG cables

---

## User Report

> "if i swap between ecg/eeg by changing cable, it shows mode change on frontend, but the data isnt correct?"

**User observation:**
1. Frontend detects mode change ✅
2. Mode label switches (ECG ↔ EEG) ✅
3. **BUT data displayed is wrong** ❌

---

## Root Cause Analysis

### Buffer Architecture

**File:** [useECGViewer.ts:36-37](hospital-display-app/src/hooks/useECGViewer.ts#L36-L37)

```typescript
// ✅ FIX: Always allocate 22 buffers (ECG: 0-11, EEG: 12-21) regardless of mode
const dataBufferRef = useRef<number[][]>(Array(22).fill(null).map(() => []));
```

**Buffer allocation:**
- ECG uses buffers **0-11** (12 leads: I, II, III, aVR, aVL, aVF, V1-V6)
- EEG uses buffers **12-21** (8 channels: Fp1, Fp2, F3, F4, C3, C4, O1, O2)

### The Bug

**File:** [useECGViewer.ts:73-86](hospital-display-app/src/hooks/useECGViewer.ts#L73-L86)

```typescript
// ✅ FIXED: Only clear buffers when PATIENT changes, not when MODE changes
// When mode changes, we keep the data - ECG data stays in 0-11, EEG data stays in 12-21
useEffect(() => {
  // Clear any existing cache
  waveformCacheService.invalidateCache(patient.id, isECGMode ? 'ecg' : 'eeg').catch(err => {
    logger.warn(`⚠️ Failed to invalidate cache: ${err}`);
  });

  // Clear existing data in all 22 buffers
  for (let i = 0; i < 22; i++) {
    dataBufferRef.current[i] = [];
  }
  logger.log(`🆕 Blank canvas initialized - 22 empty buffers ready for fresh data (ECG: 0-11, EEG: 12-21)`);
}, [patient.id]); // ❌ BUG: Only clears on patient change, not mode change!
```

**What happens:**

### Scenario 1: ECG → EEG swap

1. **Initial state (ECG mode):**
   - GPIO 4 HIGH
   - ESP32 sends ECG waveforms
   - Buffers 0-11 fill with ECG data
   - Buffers 12-21 are empty

2. **User swaps cable (EEG mode):**
   - GPIO 4 LOW
   - ESP32 detects mode change
   - ESP32 sends `waveformData.mode = 'eeg'`

3. **Frontend auto-switches:**
   ```typescript
   if (waveformData.mode === 'eeg' && isECGMode) {
     logger.log('🔄 Auto-switching to EEG mode (detected from device)');
     setIsECGMode(false);  // ✅ Mode switches
   }
   ```

4. **Display updates:**
   - `leads` changes from `['I', 'II', ...]` to `['Fp1', 'Fp2', ...]`
   - `getBufferIndex()` now maps to buffers 12-21
   - **BUT buffers 12-21 are empty!**
   - Canvas tries to render empty buffers → blank screen

5. **New EEG data arrives:**
   - Buffers 12-21 start filling with EEG data
   - **BUT buffers 0-11 still contain old ECG data**
   - If user switches back to ECG, they see OLD ECG data + NEW ECG data mixed

### Scenario 2: EEG → ECG swap

Same problem in reverse:
- Buffers 12-21 contain old EEG data
- Buffers 0-11 are empty when switching to ECG
- Blank screen until new ECG data arrives
- Old EEG data persists in buffers 12-21

---

## Why The Comment Is Misleading

**Line 73-74:**
```typescript
// ✅ FIXED: Only clear buffers when PATIENT changes, not when MODE changes
// When mode changes, we keep the data - ECG data stays in 0-11, EEG data stays in 12-21
```

**This comment implies:**
- "It's good to keep old data when mode changes"
- "ECG and EEG data coexist in separate buffers"

**Why this is WRONG:**
1. **Same physical device** - When you swap cable, old data is from WRONG mode
2. **Not multi-modal** - You can't view ECG and EEG simultaneously
3. **Stale data** - Old ECG data doesn't belong in new EEG session
4. **Confusing display** - Empty buffers → blank screen until new data flows

**The original intent was probably:**
- Support rapid mode toggling for testing
- Avoid clearing buffers unnecessarily

**But in practice:**
- Physical cable swap = completely different sensor configuration
- Old data is invalid and should be discarded

---

## The Fix

### Option 1: Clear Buffers on Mode Change (Recommended)

**Add `isECGMode` to useEffect dependency:**

```typescript
// ✅ FIX: Clear buffers when PATIENT or MODE changes
useEffect(() => {
  // Clear any existing cache
  waveformCacheService.invalidateCache(patient.id, isECGMode ? 'ecg' : 'eeg').catch(err => {
    logger.warn(`⚠️ Failed to invalidate cache: ${err}`);
  });

  // Clear existing data in all 22 buffers
  for (let i = 0; i < 22; i++) {
    dataBufferRef.current[i] = [];
  }
  logger.log(`🆕 Blank canvas initialized - 22 empty buffers ready for fresh data (${isECGMode ? 'ECG: 0-11' : 'EEG: 12-21'})`);
}, [patient.id, isECGMode]); // ✅ Added isECGMode dependency
```

**Why this works:**
1. User swaps cable → ESP32 detects mode change
2. ESP32 sends `waveformData.mode = 'eeg'`
3. Frontend calls `setIsECGMode(false)`
4. useEffect sees `isECGMode` changed → **clears all buffers**
5. New EEG data arrives → fills clean buffers 12-21
6. No stale ECG data from previous mode

### Option 2: Clear Only Relevant Buffers (More Efficient)

```typescript
// ✅ FIX: Clear only the buffers for current mode
useEffect(() => {
  // Clear any existing cache
  waveformCacheService.invalidateCache(patient.id, isECGMode ? 'ecg' : 'eeg').catch(err => {
    logger.warn(`⚠️ Failed to invalidate cache: ${err}`);
  });

  // Clear buffers for current mode only
  if (isECGMode) {
    // Clear ECG buffers 0-11
    for (let i = 0; i < 12; i++) {
      dataBufferRef.current[i] = [];
    }
    logger.log(`🆕 ECG buffers cleared (0-11) - ready for fresh ECG data`);
  } else {
    // Clear EEG buffers 12-21
    for (let i = 12; i < 22; i++) {
      dataBufferRef.current[i] = [];
    }
    logger.log(`🆕 EEG buffers cleared (12-21) - ready for fresh EEG data`);
  }
}, [patient.id, isECGMode]); // ✅ Added isECGMode dependency
```

**Why this is better:**
- Only clears relevant buffers (ECG: 0-11 or EEG: 12-21)
- Preserves data if you want to keep both modes' history
- More efficient (clears 10-12 buffers instead of 22)

**Why this might not matter:**
- In practice, you can only view ONE mode at a time
- Both modes use same physical device (not simultaneous)
- Clearing all 22 buffers is simpler and safer

---

## Recommendation

**Use Option 1** (clear all buffers on mode change):
- **Simpler code** - less conditional logic
- **Safer** - guarantees no stale data
- **More intuitive** - mode change = fresh start
- **Performance impact negligible** - clearing 22 arrays is instant

**Update the comment** to reflect new behavior:
```typescript
// ✅ Clear buffers when PATIENT or MODE changes to prevent stale/wrong data
// Physical cable swap (ECG ↔ EEG) requires fresh buffers for new sensor configuration
```

---

## Testing Plan

### Test 1: ECG → EEG Swap
1. Start with ECG mode (GPIO 4 HIGH)
2. Wait for ECG waveforms to appear (buffers 0-11 filled)
3. Swap cable to EEG (GPIO 4 LOW)
4. **Expected:**
   - Mode switches to EEG ✅
   - Screen shows blank/baseline until new EEG data arrives ✅
   - No ECG waveforms in EEG view ✅
   - New EEG waveforms appear within 100-200ms ✅

### Test 2: EEG → ECG Swap
1. Start with EEG mode (GPIO 4 LOW)
2. Wait for EEG waveforms to appear (buffers 12-21 filled)
3. Swap cable to ECG (GPIO 4 HIGH)
4. **Expected:**
   - Mode switches to ECG ✅
   - Screen shows blank/baseline until new ECG data arrives ✅
   - No EEG waveforms in ECG view ✅
   - New ECG waveforms appear within 100-200ms ✅

### Test 3: Rapid Mode Toggling
1. Start in ECG mode
2. Quickly toggle ECG → EEG → ECG → EEG (manual button clicks)
3. **Expected:**
   - Buffers clear on each toggle
   - No mixing of ECG and EEG data
   - Display shows correct waveforms for current mode

---

## Files to Modify

1. **hospital-display-app/src/hooks/useECGViewer.ts**
   - Line 86: Add `isECGMode` to useEffect dependency array
   - Lines 73-74: Update comment to explain why we clear on mode change

---

## Impact Analysis

### Before Fix:
- ❌ Mode switch shows blank screen (empty buffers)
- ❌ Old data from previous mode persists
- ❌ Confusing user experience
- ❌ Potential for wrong data display

### After Fix:
- ✅ Mode switch immediately clears buffers
- ✅ Fresh data appears within 100-200ms
- ✅ No stale data from previous mode
- ✅ Clear visual feedback (blank → waveforms)

---

## Summary

**Bug:** Old waveform data persists when swapping ECG/EEG cables
**Cause:** Buffers only cleared on patient change, not mode change
**Fix:** Add `isECGMode` to useEffect dependency to clear buffers on mode switch
**Impact:** Prevents stale/wrong data, improves user experience

**Status:** ✅ **FIX READY** - Awaiting approval to implement

---

**END OF DIAGNOSIS**
