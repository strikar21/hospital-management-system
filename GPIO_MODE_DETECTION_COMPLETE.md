# GPIO Mode Detection Implementation Complete

**Date:** 2025-10-21
**Firmware Version:** 5.0.0
**Status:** ✅ COMPLETE - Ready to Flash

---

## WHAT WAS FIXED

### Issue
Line 1325 had hardcoded mode:
```cpp
doc["mode"] = "ecg";  // ❌ HARDCODED
```

User correctly identified:
> "mode ecg or eeg depends on a gpio pin being high or low. its not hardcoded as ecg imo."

### Solution Implemented
**GPIO 4** now controls ECG/EEG mode dynamically:
- **GPIO 4 HIGH** (or floating with pullup) → ECG mode
- **GPIO 4 LOW** (grounded) → EEG mode

---

## CHANGES MADE

### 1. GPIO Pin Definition (Lines 42-45)
```cpp
// ====================================
// GPIO PIN CONFIGURATION
// ====================================
#define MODE_SELECT_PIN 4  // GPIO 4 for ECG/EEG mode selection (HIGH=ECG, LOW=EEG)
```

### 2. Pin Configuration in setup() (Lines 538-542)
```cpp
// Configure mode selection GPIO pin
pinMode(MODE_SELECT_PIN, INPUT_PULLUP);
bool initialMode = digitalRead(MODE_SELECT_PIN) == HIGH;
Serial.println("🔌 GPIO " + String(MODE_SELECT_PIN) + " configured for mode selection");
Serial.println("   Current mode: " + String(initialMode ? "ECG" : "EEG") + " (HIGH=ECG, LOW=EEG)");
```

### 3. Dynamic Mode Reading in sendVitals() (Lines 1337-1339)
```cpp
// Read GPIO pin to determine mode (HIGH = ECG, LOW = EEG)
bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;
doc["mode"] = isECGMode ? "ecg" : "eeg";
```

### 4. Enhanced Serial Output (Lines 1357-1361)
```cpp
Serial.println("📊 Vitals: Mode=" + String(isECGMode ? "ECG" : "EEG") +
               ", HR=" + String((int)heartRate) +
               ", Temp=" + String(tempCelsius, 1) + "°C" +
               ", SpO2=" + String(oxygenSat) + "%" +
               ", RR=" + String(respiratoryRate));
```

---

## HOW IT WORKS

### Hardware Setup

**GPIO 4 Pin Modes:**

1. **ECG Mode (Default):**
   - GPIO 4 left **floating** (not connected)
   - Internal pullup resistor pulls pin HIGH
   - Mode = "ecg"

2. **EEG Mode:**
   - GPIO 4 connected to **GND**
   - Pin reads LOW
   - Mode = "eeg"

**Mode Switch Example:**
```
ESP32 Board:
┌─────────────────┐
│                 │
│  GPIO 4  ○──────┼──── Switch ──── GND
│                 │
│  (Pullup)       │
│                 │
└─────────────────┘

Switch Open  → HIGH → ECG mode
Switch Closed → LOW  → EEG mode
```

### Software Flow

1. **On Startup:**
   - GPIO 4 configured as INPUT_PULLUP
   - Initial mode printed to Serial console
   - Mode can change dynamically during runtime

2. **Every Second (sendVitals):**
   - Read GPIO 4 state
   - Determine mode: `HIGH = "ecg"`, `LOW = "eeg"`
   - Include mode in MQTT vitals message
   - Print current mode to Serial console

3. **Backend Receives:**
   - Vitals message with dynamic mode
   - Backend stores mode in TimescaleDB
   - Backend uses mode for ECG/EEG-specific analysis

---

## SERIAL OUTPUT EXAMPLE

### ECG Mode (GPIO 4 HIGH)
```
🔌 GPIO 4 configured for mode selection
   Current mode: ECG (HIGH=ECG, LOW=EEG)
📊 Vitals: Mode=ECG, HR=0, Temp=-17.8°C, SpO2=0%, RR=0
```

### EEG Mode (GPIO 4 LOW)
```
🔌 GPIO 4 configured for mode selection
   Current mode: EEG (HIGH=ECG, LOW=EEG)
📊 Vitals: Mode=EEG, HR=0, Temp=-17.8°C, SpO2=0%, RR=0
```

---

## MQTT MESSAGE EXAMPLE

### ECG Mode
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

### EEG Mode
```json
{
  "timestamp": "2025-10-21T10:00:00.000Z",
  "mode": "eeg",
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

## BACKEND COMPATIBILITY

### Backend Already Supports Mode Field

**TimescaleDB vitals_realtime table:**
```sql
CREATE TABLE vitals_realtime (
    time TIMESTAMPTZ NOT NULL,
    "patientId" TEXT NOT NULL,
    "deviceId" TEXT NOT NULL,
    mode TEXT,  -- ✅ "ecg" or "eeg"
    ...
);
```

**Backend Analysis:**
- ECG mode → Triggers ECG-specific alert rules
- EEG mode → Triggers EEG-specific alert rules
- Mode stored for trend analysis and reporting

---

## TESTING INSTRUCTIONS

### 1. Flash Firmware
```bash
# Upload esp32_hospital_watch_complete.ino to ESP32
# Using Arduino IDE or PlatformIO
```

### 2. Test ECG Mode (Default)
- Leave GPIO 4 disconnected (floating)
- Watch Serial Monitor for: `Current mode: ECG`
- Verify MQTT messages show `"mode": "ecg"`

### 3. Test EEG Mode
- Connect GPIO 4 to GND
- Watch Serial Monitor for mode change
- Verify MQTT messages show `"mode": "eeg"`

### 4. Test Dynamic Switching
- Start in ECG mode (GPIO 4 floating)
- Ground GPIO 4 while running
- Observe Serial output change from ECG to EEG
- Disconnect GPIO 4 from GND
- Observe Serial output change back to ECG

---

## GPIO PIN SELECTION

### Why GPIO 4?
- ✅ Safe GPIO (not used for boot/flash/strapping)
- ✅ No conflicts with I2C, SPI, or UART
- ✅ Available on most ESP32 dev boards
- ✅ Internal pullup resistor available

### Alternative GPIOs (If GPIO 4 Conflicts)
User can change `MODE_SELECT_PIN` to any of these:
- GPIO 5 (safe)
- GPIO 12 (safe, but affects flash voltage on some boards)
- GPIO 13 (safe)
- GPIO 14 (safe)
- GPIO 15 (safe, but has pullup - must override)
- GPIO 16 (safe)
- GPIO 17 (safe)
- GPIO 18 (safe)
- GPIO 19 (safe)
- GPIO 21 (safe)
- GPIO 22 (safe)
- GPIO 23 (safe)

**Avoid:** GPIO 0, 2, 6-11 (boot/flash), GPIO 34-39 (input-only, no pullup)

---

## NEXT STEPS

### Immediate
1. ✅ GPIO mode detection implemented
2. ⏳ Flash firmware to ESP32
3. ⏳ Test with GPIO 4 switch (high/low)

### Future (When Sensors Available)
1. ⏳ Implement `sendWaveform()` function
2. ⏳ Integrate ADS1298 8-channel ADC
3. ⏳ Add ECG/EEG waveform data collection
4. ⏳ Send waveform snapshots every 10 seconds

### Backend
- ✅ Backend already supports dynamic mode
- ✅ Backend ready for ECG/EEG waveform data
- ✅ Backend analysis services ready

---

## FILE CHANGES

**Modified Files:**
- `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`
  - Lines 42-45: GPIO pin definition
  - Lines 538-542: Pin configuration in setup()
  - Lines 1337-1339: Dynamic mode reading
  - Lines 1357-1361: Enhanced serial output

**No Backend Changes Required** - Backend already handles mode field.

---

## SUMMARY

✅ **GPIO 4 now controls ECG/EEG mode dynamically**
✅ **HIGH = ECG, LOW = EEG**
✅ **Internal pullup enabled (default ECG when floating)**
✅ **Serial console shows current mode**
✅ **MQTT messages include dynamic mode**
✅ **Backend fully compatible**
✅ **Ready to flash and test**

**User requested fix: COMPLETE**

---

## WAVEFORM STATUS

User asked: "do you know how waveforms are being sent?"

**Answer:** ESP32 does NOT send waveform data currently.

**Why?** User stated: "i dont have any sensors just yet."

**Backend Status:**
- ✅ Backend subscribes to `hospital/devices/+/waveform` topic
- ✅ Backend has `_handleWaveformMessage()` handler ready
- ✅ Backend will automatically analyze ECG/EEG waveforms when received
- ❌ ESP32 has no `sendWaveform()` function yet

**Waveform implementation deferred until ADS1298 hardware is available.**
