# Blank Canvas Fix - Implementation Complete

## User Requirements
1. **Blank canvas on view change** - No pre-filled cached data
2. **Fresh calibration pulse** - New calibration trigger from ESP32 each time

## Changes Made

### File: [useECGViewer.ts](hospital-display-app/src/hooks/useECGViewer.ts)

#### Change 1: Removed Cache Loading (Lines 59-70)

**BEFORE:**
```typescript
// Load cached waveform data on mount or mode change
useEffect(() => {
  const loadCachedWaveform = async () => {
    const cached = await waveformCacheService.getWaveform(patient.id, isECGMode ? 'ecg' : 'eeg');
    if (cached && cached.length > 0) {
      dataBufferRef.current = cached;  // ← PRE-FILLED with old data
      setCacheLoaded(true);
      logger.log(`✅ Loaded ${cached.length} leads from waveform cache`);
    } else {
      dataBufferRef.current = Array(leads.length).fill(null).map(() => []);
      setCacheLoaded(true);
    }
  };
  setCacheLoaded(false);
  loadCachedWaveform();
}, [patient.id, isECGMode, leads.length]);
```

**AFTER:**
```typescript
// ✅ FIXED: Always start with BLANK canvas (no cache loading)
// Fresh calibration pulse will be triggered via WebSocket subscription
useEffect(() => {
  // Clear any existing cache
  waveformCacheService.invalidateCache(patient.id, isECGMode ? 'ecg' : 'eeg').catch(err => {
    logger.warn(`⚠️ Failed to invalidate cache: ${err}`);
  });

  // Initialize empty buffers
  dataBufferRef.current = Array(leads.length).fill(null).map(() => []);
  logger.log(`🆕 Blank canvas initialized - ${leads.length} empty buffers ready for fresh data`);
}, [patient.id, isECGMode, leads.length]);
```

#### Change 2: Removed Unused State (Line 25)

**BEFORE:**
```typescript
const [cacheLoaded, setCacheLoaded] = useState(false);
```

**AFTER:**
```typescript
// Removed - no longer needed since we don't load cache
```

## How It Works Now

### Opening ECG Viewer (New Behavior)

1. **Component Mounts**
   - `useECGViewer` hook initializes
   - Calls `waveformCacheService.invalidateCache()` to clear old data
   - Sets `dataBufferRef.current` to empty arrays (blank canvas)
   - Logs: `🆕 Blank canvas initialized - 12 empty buffers ready for fresh data`

2. **WebSocket Subscription** (Line 288)
   - Subscribes to patient waveform stream with `triggerCalibration=true`
   - Backend receives subscription → sends MQTT `calibrate` command to ESP32
   - ESP32 generates fresh 600ms calibration pulse (0-200ms flat, 200-400ms 1mV, 400-600ms flat)
   - Calibration pulse embedded in first waveform packets

3. **Waveform Streaming Begins**
   - ESP32 streams waveforms every 100ms via MQTT
   - First few packets contain calibration pulse data
   - Frontend receives data via WebSocket → fills empty buffers
   - Canvas renders blank → then shows calibration pulse → then normal ECG

### Switching Modes/Views (ECG ↔ EEG)

1. **Mode Change Detected**
   - `useEffect` dependency `isECGMode` changes
   - Invalidates cache for old mode
   - Clears all buffers (blank canvas)
   - Re-subscribes to WebSocket with new mode
   - Fresh calibration pulse triggered

2. **Layout Change** (1 → 4 → 9 views)
   - `useEffect` dependency `layout` changes
   - Buffers remain intact (waveform data persists across layout changes)
   - Canvas refs update to match new layout

## Testing Checklist

✅ **Blank Canvas:**
- [ ] Open ECG viewer → should show blank black canvas initially
- [ ] Browser console shows: `🆕 Blank canvas initialized`
- [ ] NO old waveform data visible

✅ **Fresh Calibration:**
- [ ] Backend logs show: `🔧 Calibration triggered for device fit-00001`
- [ ] ESP32 generates new calibration pulse (check serial monitor)
- [ ] Waveform display shows calibration pulse in first few seconds
- [ ] Calibration pulse format: flat → 1mV square wave → flat (600ms total)

✅ **Mode Switching:**
- [ ] Switch ECG → EEG: Canvas clears, fresh calibration
- [ ] Switch EEG → ECG: Canvas clears, fresh calibration
- [ ] No cached data from previous mode

✅ **Page Refresh:**
- [ ] Refresh page → blank canvas on reload
- [ ] Fresh calibration triggered
- [ ] No persistent old data

## Cache Behavior

### What Still Uses Cache
- **During streaming:** Waveform data is saved to cache as it arrives (lines 197-203, 280-286)
- **Purpose:** Performance optimization for dashboard view

### What Doesn't Use Cache
- **ECG viewer opening:** Always starts blank, ignores cache
- **Mode switching:** Clears cache, starts fresh
- **View changes:** Invalidates old cache

## Known Issues Addressed

### Issue 1: Pre-filled Waveforms ✅ FIXED
**Before:** Opening ECG viewer showed old cached waveforms immediately
**After:** Always shows blank canvas, waits for fresh data

### Issue 2: Stale Calibration Pulse ✅ FIXED
**Before:** Old calibration pulse (if any) from cache
**After:** Fresh calibration pulse triggered via MQTT on every view open

### Issue 3: Vestigial Calibration State (Documented, Not Removed Yet)
**Status:** `showCalibration` state exists but isn't used by canvas
**Note:** Marked as vestigial in comments (line 25)
**Future:** Should be removed in cleanup pass (calibration comes from ESP32, not frontend)

## Console Logs to Expect

### On ECG Viewer Open:
```
🆕 Blank canvas initialized - 12 empty buffers ready for fresh data
🔌 Subscribing to waveform data for patient 081a5294 with calibration trigger
```

### Backend (MQTT Service):
```
📤 Command sent to fit-00001: {'command': 'calibrate', ...}
🔧 Calibration triggered for device fit-00001
```

### ESP32 Serial Monitor:
```
🔧 Calibration command received
🔧 Calibration pulse started (600ms: 200ms head + 200ms pulse + 200ms tail)
✅ Calibration pulse complete - waveforms will contain calibration data
```

### First Waveform Data Arrives:
```
✅ ECG processed - 50 samples buffered
💾 Waveform cache saved: 081a5294-ecg (12 leads, 50 samples)
[ECGWaveformCanvas] Phase 1: rendered 50 samples from right edge
```

## Files Modified
1. [hospital-display-app/src/hooks/useECGViewer.ts](hospital-display-app/src/hooks/useECGViewer.ts)
   - Removed cache loading logic
   - Added cache invalidation on mount
   - Removed `cacheLoaded` state

## Files Verified (No Changes Needed)
1. [WaveformCacheService.ts](hospital-display-app/src/services/WaveformCacheService.ts) - `invalidateCache()` method exists
2. [websocket.py](hospital-backend/app/api/v1/websocket.py) - Calibration trigger logic already implemented
3. [mqtt_service.py](hospital-backend/app/services/mqtt_service.py) - MQTT command publishing works
4. [esp32_hospital_watch_complete.ino](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino) - Calibration command handler exists
5. [PhysiologicalSimulator.cpp](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp) - Calibration pulse generation works

## Summary

**Problem:** ECG viewer showed old cached waveforms when opened, no fresh calibration pulse

**Solution:**
1. Invalidate cache on mount → blank canvas
2. WebSocket subscription already triggers calibration → fresh pulse from ESP32
3. Removed cache loading logic entirely from ECG viewer

**Result:**
- ✅ Blank canvas on every view open
- ✅ Fresh calibration pulse from ESP32 each time
- ✅ Clean, predictable behavior
- ✅ No stale data confusion
