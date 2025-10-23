# ESP32 Waveform and GPIO Mode Analysis

**Date:** 2025-10-21
**Status:** Research Complete - Ready for Implementation

---

## CURRENT STATE

### What ESP32 Currently Sends

**1. Vitals (Every 1 second)** - Line 1313-1347
```cpp
topic: "hospital/devices/{deviceId}/vitals"
{
  "timestamp": "2025-10-21T10:00:00.000Z",
  "mode": "ecg",  // ❌ HARDCODED
  "deviceId": "fit-00001",
  "patientId": "PAT0001",
  "heartRate": 0,
  "skinTemperature": -17.78,  // Converted to Celsius
  "oxygenSaturation": 0,
  "respiratoryRate": 0,
  "batteryLevel": 100,
  "signalQuality": 0.0
}
```

**2. Heartbeat (Every 30 seconds)** - Line 1290-1308
```cpp
topic: "hospital/devices/{deviceId}/heartbeat"
{
  "deviceId": "fit-00001",
  "timestamp": "2025-10-21T10:00:00.000Z",
  "batteryLevel": 100,
  "signalStrength": -45,
  "firmwareVersion": "5.0.0"
}
```

**3. NO WAVEFORM DATA** - Function does not exist
- Backend expects waveform every 10 seconds
- Backend topic subscribed: `hospital/devices/+/waveform`
- ESP32 has NO `sendWaveform()` function

---

## ISSUE 1: Hardcoded Mode (Line 1325)

### Current Code
```cpp
doc["mode"] = "ecg";  // ❌ HARDCODED
```

### User Requirement
> "mode ecg or eeg depends on a gpio pin being high or low. its not hardcoded as ecg imo."

### Root Cause
Mode should be dynamically determined by reading a GPIO pin state.

### Proposed Fix
```cpp
// At top of file - GPIO Pin Definition
#define MODE_SELECT_PIN 4  // GPIO 4 for ECG/EEG mode selection

// In setup() function
pinMode(MODE_SELECT_PIN, INPUT_PULLUP);

// In sendVitals() function (line 1325)
bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;
doc["mode"] = isECGMode ? "ecg" : "eeg";
```

### GPIO Pin Convention
- **HIGH (pulled up)** = ECG mode
- **LOW (grounded)** = EEG mode
- **INPUT_PULLUP** = Internal pullup resistor (default HIGH if not connected)

**QUESTION FOR USER:** Which GPIO pin should we use? (Suggested: GPIO 4, but user may have hardware preference)

---

## ISSUE 2: No Waveform Data

### Backend Expectations
From `hospital-backend/app/services/mqtt_service.py:241-316`:

**Backend subscribes to:**
```python
"hospital/devices/+/waveform"   # Waveform snapshots (10 sec updates)
```

**Backend handler: `_handleWaveformMessage()`**
- Expects `WaveformSnapshotMessage` Pydantic model
- Contains ECG/EEG waveform arrays
- Should include 8-channel data from ADS1298
- Backend performs automatic ECG/EEG analysis on waveform data

### ESP32 Reality
**NO waveform sending function exists.**

### Waveform Data Structure Expected by Backend

**ECG Mode Waveform:**
```json
{
  "timestamp": "2025-10-21T10:00:00.000Z",
  "patientId": "PAT0001",
  "deviceId": "fit-00001",
  "mode": "ecg",
  "sampleRate": 250,
  "duration": 10.0,
  "ecgWaveform": {
    "limb": {
      "lead_I": [array of 2500 samples],
      "lead_II": [array of 2500 samples],
      "lead_III": [array of 2500 samples],
      "aVR": [array of 2500 samples],
      "aVL": [array of 2500 samples],
      "aVF": [array of 2500 samples]
    },
    "precordial": {
      "V1": [array of 2500 samples],
      "V2": [array of 2500 samples]
    }
  },
  "quality": {
    "leadOff": [false, false, false, false, false, false, false, false],
    "impedance": [1.2, 1.5, 1.8, 2.1, 1.9, 1.6, 2.3, 2.0]
  }
}
```

**EEG Mode Waveform:**
```json
{
  "timestamp": "2025-10-21T10:00:00.000Z",
  "patientId": "PAT0001",
  "deviceId": "fit-00001",
  "mode": "eeg",
  "sampleRate": 250,
  "duration": 10.0,
  "eegWaveform": {
    "frontal": {
      "Fp1": [array of 2500 samples],
      "Fp2": [array of 2500 samples],
      "F3": [array of 2500 samples],
      "F4": [array of 2500 samples]
    },
    "central": {
      "C3": [array of 2500 samples],
      "C4": [array of 2500 samples]
    },
    "occipital": {
      "O1": [array of 2500 samples],
      "O2": [array of 2500 samples]
    }
  },
  "quality": {
    "leadOff": [false, false, false, false, false, false, false, false],
    "impedance": [1.2, 1.5, 1.8, 2.1, 1.9, 1.6, 2.3, 2.0]
  }
}
```

### Why No Waveform Function?
**User confirmed:** "i dont have any sensors just yet."

- No ADS1298 hardware connected
- No MAX30102 sensor
- No ECG/EEG electrodes
- Cannot send real waveform data without sensors

### Backend Behavior Without Waveform
Backend will:
- ✅ Process vitals data (currently all zeros)
- ✅ Trigger sensor malfunction alerts (because all values are zero)
- ❌ NOT receive waveform snapshots
- ❌ NOT perform ECG/EEG analysis
- ❌ NOT detect arrhythmias or seizures

**This is EXPECTED until sensors are integrated.**

---

## WHAT NEEDS TO BE DONE NOW

### Priority 1: GPIO Mode Detection (User Requested)
✅ **Fix line 1325 to read GPIO pin instead of hardcoded "ecg"**

**Implementation:**
1. Define GPIO pin for mode selection
2. Configure pin as INPUT_PULLUP in setup()
3. Read pin state in sendVitals()
4. Set mode based on pin state

**User Confirmation Needed:**
- Which GPIO pin should be used? (Suggest GPIO 4)

### Priority 2: Waveform Sending (Future - When Sensors Available)
⏳ **Cannot implement without hardware**

**Will require:**
1. ADS1298 8-channel ADC integration
2. Circular buffer for waveform samples
3. `sendWaveform()` function to publish every 10 seconds
4. Delta encoding for compression (optional)
5. Lead-off detection
6. Impedance measurement

**NOT URGENT** - Backend handles vitals-only mode gracefully.

---

## CURRENT SENSOR VALUES

All sensor values are **zero** (fake data removed):

```cpp
float heartRate = 0;         // TODO: Read from MAX30102
float temperature = 0;       // TODO: Read from MLX90614
int oxygenSat = 0;           // TODO: Read from MAX30102
int batteryLevel = 100;      // TODO: Read from battery voltage ADC
int respiratoryRate = 0;     // TODO: Calculate from PPG waveform
float quality = 0;           // TODO: Read from sensor signal quality
```

**Side Effect:** Backend triggers sensor malfunction alerts because:
- `heartRate = 0` (invalid - should be 20-300)
- `oxygenSat = 0` (invalid - should be 50-100)
- `temperature = 0°C` (invalid - should be 30-45°C)

**Options:**
1. Keep zeros (triggers alerts, but honest about sensor state)
2. Add realistic random variations (for testing without real sensors)

**User has NOT requested realistic test data yet.**

---

## NEXT STEPS

1. **Implement GPIO mode detection** (user requested: "fix the gpio thing")
2. **Confirm GPIO pin number** with user
3. **Waveform implementation** deferred until user has ADS1298 hardware

---

## BACKEND READINESS

Backend is **FULLY READY** for 8-channel ECG/EEG waveform data:

✅ **MQTT Topics Subscribed:**
- `hospital/devices/+/vitals` (receiving)
- `hospital/devices/+/waveform` (ready but not receiving)
- `hospital/devices/+/event` (ready for arrhythmia/seizure events)

✅ **Data Models Defined:**
- `VitalsRealtimeMessage` (Pydantic)
- `WaveformSnapshotMessage` (Pydantic)
- `NeuralEventMessage` (Pydantic)

✅ **TimescaleDB Tables:**
- `vitals_realtime` (receiving data)
- `waveform_snapshots` (ready)
- `neural_events` (ready)

✅ **Analysis Services:**
- `ecgAnalysisService` (ready for ECG waveform)
- `eegAnalysisService` (ready for EEG waveform)
- `alertDetectionService` (active on vitals)

**Backend will automatically analyze waveforms when ESP32 starts sending them.**

---

## IMPLEMENTATION PLAN - GPIO MODE FIX

```cpp
// ====================================
// STEP 1: ADD GPIO PIN DEFINITION (after line 40)
// ====================================
#define MODE_SELECT_PIN 4  // GPIO 4 for ECG/EEG mode selection

// ====================================
// STEP 2: CONFIGURE PIN IN setup() (after line 531)
// ====================================
pinMode(MODE_SELECT_PIN, INPUT_PULLUP);
Serial.println("🔌 GPIO " + String(MODE_SELECT_PIN) + " configured for mode selection (HIGH=ECG, LOW=EEG)");

// ====================================
// STEP 3: READ MODE IN sendVitals() (replace line 1325)
// ====================================
// Read GPIO pin to determine mode (HIGH = ECG, LOW = EEG)
bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;
doc["mode"] = isECGMode ? "ecg" : "eeg";

Serial.println("📊 Vitals: Mode=" + String(isECGMode ? "ECG" : "EEG") +
               ", HR=" + String((int)heartRate) +
               ", Temp=" + String(tempCelsius, 1) + "°C" +
               ", SpO2=" + String(oxygenSat) + "%" +
               ", RR=" + String(respiratoryRate));
```

**Ready to implement upon user confirmation of GPIO pin number.**
