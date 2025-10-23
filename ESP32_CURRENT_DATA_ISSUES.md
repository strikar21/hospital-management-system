# ESP32 Current Data Issues

## Summary of What Gets Sent

**ONLY these fields are sent to backend every 1 second:**

```json
{
  "timestamp": "2025-10-21T10:00:00.000Z",
  "mode": "ecg",
  "deviceId": "fit-00001",
  "patientId": "PAT0001",
  "heartRate": 0,
  "skinTemperature": -17.78,
  "oxygenSaturation": 0,
  "respiratoryRate": 0,
  "batteryLevel": 100,
  "signalQuality": 0.0
}
```

---

## Issues Identified

### Issue 1: Mode is Hardcoded ❌

**File:** [esp32_hospital_watch_complete.ino:1325](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1325)

```cpp
doc["mode"] = "ecg";  // ❌ HARDCODED
```

**Problem:** Mode should be read from a GPIO pin to detect if ADS1298 is configured for ECG or EEG.

**Expected Behavior:**
- GPIO pin HIGH → mode = "ecg"
- GPIO pin LOW → mode = "eeg"

**Fix Needed:**
```cpp
// Define mode detection pin
#define MODE_SELECT_PIN 4  // GPIO 4 for mode selection

void setup() {
  // ... existing setup ...
  pinMode(MODE_SELECT_PIN, INPUT_PULLUP);
}

void sendVitals() {
  // ... existing code ...

  // Read mode from GPIO pin
  bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;
  doc["mode"] = isECGMode ? "ecg" : "eeg";

  // ... rest of function ...
}
```

---

### Issue 2: All Sensor Values are Zero ❌

**Reason:** We removed the fake data

**Current Values:**
- heartRate = 0
- temperature = 0
- oxygenSat = 0
- respiratoryRate = 0
- quality = 0

**Problem:** These zeros trigger alerts and are not useful for testing.

**Options:**
1. **Add realistic random variations** (for testing)
2. **Integrate real sensors** (for production)
3. **Leave as zero** (not recommended)

---

### Issue 3: No Waveform Data ❌

**Missing:** `sendWaveform()` function doesn't exist

**Backend expects:**
- Topic: `hospital/devices/fit-00001/waveform`
- Frequency: Every 10 seconds
- Contains: 8-channel ECG or EEG raw data

**ESP32 doesn't send this** - only sends basic vitals.

---

### Issue 4: No ECG/EEG Analysis ❌

**Backend expects in vitals message:**
```json
{
  "ecgAnalysis": {
    "rrInterval": 800,
    "qrsDuration": 100,
    "qtInterval": 400,
    "rhythm": "sinus"
  },
  "ecgLeads": {
    "leadI": 0.5,
    "leadII": 0.8,
    "leadIII": 0.3,
    // ... all 12 leads
  }
}
```

**ESP32 doesn't send this** - only sends basic vitals.

---

## What Frontend Receives

**Frontend only gets these values every 1 second:**
- Device ID: fit-00001
- Patient ID: PAT0001
- Heart Rate: 0 bpm
- Temperature: -17.78°C (because 0°F converts to -17.78°C)
- SpO2: 0%
- Respiratory Rate: 0 bpm
- Battery: 100%
- Signal Quality: 0%
- Mode: "ecg" (always)

**Frontend does NOT receive:**
- ❌ ECG waveforms
- ❌ EEG waveforms
- ❌ ECG analysis (RR interval, QRS, rhythm)
- ❌ EEG analysis (band powers, seizure detection)
- ❌ Events (arrhythmias, seizures)

---

## Immediate Fixes Needed

### Fix 1: Add GPIO Mode Detection

**Priority:** HIGH
**Effort:** 5 minutes
**Files:** esp32_hospital_watch_complete.ino

```cpp
// Add after line 40
#define MODE_SELECT_PIN 4  // GPIO 4 - HIGH=ECG, LOW=EEG

// Add in setup() after line 530
pinMode(MODE_SELECT_PIN, INPUT_PULLUP);

// Change line 1325
bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;
doc["mode"] = isECGMode ? "ecg" : "eeg";
```

### Fix 2: Add Realistic Test Data

**Priority:** HIGH (for testing)
**Effort:** 10 minutes
**Files:** esp32_hospital_watch_complete.ino

```cpp
// Add after line 464
void generateTestVitals() {
  heartRate = 70 + random(0, 16);
  temperature = 97.5 + random(0, 20)/10.0;
  oxygenSat = 95 + random(0, 6);
  respiratoryRate = 14 + random(0, 7);
  quality = 90 + random(0, 11);
}

// Add in loop() before sendVitals() at line 627
generateTestVitals();
sendVitals();
```

### Fix 3: (Future) Add sendWaveform()

**Priority:** LOW (requires ADS1298 hardware)
**Effort:** 2-3 days
**Dependencies:** ADS1298 chip, libraries, testing

Not needed for current basic vitals monitoring.

---

## Current System Capabilities

### ✅ What Works:
- WiFi connection
- HTTPS provisioning
- Certificate-based mTLS MQTT
- Sequential device IDs (fit-00001)
- Patient assignment
- Heartbeat messages (every 30 seconds)
- Device alerts (battery, connectivity, sensor malfunction)

### ❌ What Doesn't Work:
- Sensor data (all zeros)
- Mode detection (hardcoded to "ecg")
- Waveform data (not implemented)
- ECG/EEG analysis (not implemented)

---

## Recommendations

**For immediate testing:**
1. Add GPIO mode detection (Fix 1)
2. Add realistic test data (Fix 2)

**For production:**
1. Integrate MAX30102 for HR/SpO2
2. Integrate MLX90614 for temperature
3. Calculate respiratory rate from PPG
4. Add battery voltage ADC reading

**For advanced monitoring (future):**
1. Add ADS1298 hardware
2. Implement sendWaveform()
3. Add ECG/EEG analysis
4. Implement event detection

---

## Mode Detection Details

**Hardware Setup:**
```
GPIO 4 (MODE_SELECT_PIN) ─── Physical Switch ─── GND
                         └─── 10kΩ Pull-up ───── 3.3V

Switch OPEN  → GPIO reads HIGH → ECG mode
Switch CLOSED → GPIO reads LOW  → EEG mode
```

**Software Logic:**
```cpp
pinMode(MODE_SELECT_PIN, INPUT_PULLUP);
bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;
String mode = isECGMode ? "ecg" : "eeg";
```

**Backend Impact:**
- Backend uses this mode field to determine which analysis to run
- ECG mode → ECGAnalysisService analyzes waveforms
- EEG mode → EEGAnalysisService analyzes waveforms

---

## Questions to Answer

1. **Do you want GPIO mode detection added now?** (5 min fix)
2. **Do you want realistic test data added now?** (10 min fix)
3. **Are you planning to add real sensors soon?** (affects testing strategy)
4. **Which GPIO pin should be used for mode selection?** (I suggested GPIO 4)

---

## Files That Need Changes

1. **esp32_hospital_watch_complete.ino**
   - Line 40: Add MODE_SELECT_PIN definition
   - Line 530: Add pinMode for mode pin
   - Line 1325: Change hardcoded "ecg" to GPIO-detected mode
   - Line 627: (Optional) Add generateTestVitals() call

No other files need changes.
