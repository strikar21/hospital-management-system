# Calibration Pulse & 2ms Timing - Explanation

## Question 1: Why 2ms?

**Answer**: Because the sampling rate is **500Hz** (500 samples per second)

### The Math:
```
Sample rate: 500 Hz = 500 samples/second

Time per sample = 1 second / 500 samples
                = 1000ms / 500
                = 2ms per sample
```

### In the Code:

**ESP32** - `PhysiologicalSimulator.cpp:437`:
```cpp
// ✅ Increment time ONCE per sample (not per lead)
ecgCycleTime += 2.0;  // 500 Hz = 2ms per sample
```

This means:
- Every sample advances the cardiac cycle time by **2 milliseconds**
- At 500Hz, we generate **500 samples per second**
- Each sample represents **2ms** of real ECG time

### Example Timeline:

```
Sample 0:   Time = 0ms    (P wave start)
Sample 1:   Time = 2ms
Sample 2:   Time = 4ms
Sample 3:   Time = 6ms
...
Sample 50:  Time = 100ms  (middle of QRS)
...
Sample 337: Time = 674ms  (T wave end at 89 BPM)
Sample 338: Time = 676ms  ← Reset to 0ms (new beat starts)
```

---

## Question 2: Why No Calibration Pulse on Screen?

### The Problem

You're not seeing the calibration pulse because **there's no physical ESP32 device running** to receive the calibration command!

### The Full Calibration Flow:

1. **Frontend**: User opens ECG viewer
   - ✅ `useECGViewer.ts` sends `triggerCalibration: true`

2. **Backend**: Receives WebSocket message
   - ✅ `websocket.py:113` checks `triggerCalibration` flag
   - ✅ `websocket.py:117` calls `_triggerDeviceCalibration()`
   - ✅ `websocket.py:275` publishes MQTT command to `hospital/devices/{deviceId}/commands`

3. **MQTT Broker** (Mosquitto):
   - ✅ Receives message on topic
   - ✅ Waits for device to subscribe and receive

4. **ESP32 Watch** (PHYSICAL DEVICE):
   - ❌ **NO DEVICE IS CONNECTED!**
   - The ESP32 firmware exists as code on your computer
   - But no physical ESP32 is flashed and connected to MQTT

5. **Result**:
   - Calibration command published to MQTT ✅
   - But nobody is listening ❌
   - No calibration pulse generated ❌
   - Frontend receives only simulated ECG data (no calibration) ❌

---

## How to Test Calibration Pulse

### Option A: Flash Real ESP32 Hardware

1. Connect ESP32 board to your computer via USB
2. Upload firmware:
   - `esp32_hospital_watch_complete.ino`
   - `PhysiologicalSimulator.cpp` (with timing fix)
   - `PhysiologicalSimulator.h`

3. ESP32 connects to WiFi → MQTT broker
4. ESP32 subscribes to `hospital/devices/{deviceId}/commands`
5. Backend sends calibration command
6. ESP32 receives command → generates calibration pulse
7. Frontend displays calibration pulse

**Expected result**:
- 1 second flat baseline (0mV)
- 1 second square wave (1mV)
- 1 second flat baseline (0mV)
- Then normal ECG waveforms

### Option B: Mock Calibration in Frontend (Testing Only)

For testing without ESP32 hardware, you could temporarily add fake calibration data in frontend:

**File**: `useECGViewer.ts` (around line 70)

```typescript
useEffect(() => {
  // Clear cache
  waveformCacheService.invalidateCache(patient.id, isECGMode ? 'ecg' : 'eeg');

  // ✅ TESTING: Add fake calibration pulse
  const calibrationSamples = [
    // 500 samples of baseline (1 second)
    ...Array(500).fill(8388608),
    // 500 samples of 1mV pulse (1 second)
    ...Array(500).fill(8488608),
    // 500 samples of baseline (1 second)
    ...Array(500).fill(8388608)
  ];

  // Add to all lead buffers
  leads.forEach((_, index) => {
    dataBufferRef.current[index] = [...calibrationSamples];
  });

  logger.log(`🔧 Mock calibration pulse added (1500 samples, 3 seconds)`);
}, [patient.id, isECGMode]);
```

**This is ONLY for testing** - it's fake data, not from ESP32.

---

## Current System Architecture

```
┌─────────────────┐
│  ESP32 Firmware │  ← Code exists on computer
│  (Not Running)  │  ← Not flashed to hardware
└─────────────────┘  ← Not connected to MQTT
        ↓ (MISSING!)
┌─────────────────┐
│ MQTT Broker     │  ← Running (Mosquitto)
│ (Mosquitto)     │  ← Receives calibration command
└─────────────────┘  ← But no ESP32 to send to!
        ↓
┌─────────────────┐
│ Backend         │  ← Publishes calibration command
│ (Python/FastAPI)│  ← Command goes to MQTT but nobody receives
└─────────────────┘
        ↓
┌─────────────────┐
│ Frontend        │  ← Waiting for calibration pulse
│ (React)         │  ← Never receives it (ESP32 not running)
└─────────────────┘
```

---

## Why You're Seeing ECG Data Without ESP32

You mentioned seeing ECG waveforms on screen - this must be from:

1. **Cached data** from previous test
2. **Mock/test data** in frontend
3. **Different data source** (not ESP32)

The actual ESP32 physiological simulator with the timing fix is NOT running because no physical ESP32 is flashed and connected.

---

## Summary

### 2ms Timing:
- ✅ **Correct**: 500Hz = 2ms per sample
- ✅ **Fixed**: ecgCycleTime now advances 2ms per sample (not 16ms)
- ✅ **Result**: Waveforms display at correct speed after ESP32 flashing

### Calibration Pulse:
- ✅ **Frontend**: Sends calibration trigger
- ✅ **Backend**: Publishes MQTT command
- ✅ **ESP32 Code**: Has calibration handler
- ❌ **ESP32 Hardware**: Not running/connected
- ❌ **Result**: No calibration pulse received

**To see calibration pulse**: You need to flash the ESP32 firmware to actual hardware and connect it to your WiFi/MQTT broker.

**Alternative**: Add mock calibration data in frontend for testing (see Option B above).
