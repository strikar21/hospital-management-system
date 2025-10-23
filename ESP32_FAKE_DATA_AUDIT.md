# ESP32 Watch Fake/Mock Data Audit

## Current State - Lines 105-113

**File:** [esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino:105-113](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L105-L113)

```cpp
// ====================================
// MOCK SENSOR DATA
// ====================================
float heartRate = 75;
float temperature = 98.6;
int oxygenSat = 98;
int batteryLevel = 85;
int respiratoryRate = 16;
float quality = 95.0;
```

---

## Issue

The ESP32 watch is using **hardcoded static values** for all vital signs:
- Heart Rate: **75 bpm** (never changes)
- Temperature: **98.6°F** (never changes)
- Oxygen Saturation: **98%** (never changes)
- Respiratory Rate: **16 bpm** (never changes)
- Battery Level: **85%** (starts at 85, may change via fake battery drain)
- Signal Quality: **95%** (never changes)

---

## Where This Data Is Used

### sendVitals() Function - Lines 1311-1345

```cpp
void sendVitals() {
  if (!mqttClient.connected() || !isAssigned) {
    if (!mqttClient.connected()) {
      connectToMQTT();
    }
    return;
  }

  String topic = "hospital/devices/" + deviceId + "/vitals";

  JsonDocument doc;
  doc["timestamp"] = getISO8601Timestamp();
  doc["mode"] = "ecg";
  doc["deviceId"] = deviceId;
  doc["patientId"] = assignedPatientId;
  doc["heartRate"] = (int)heartRate;  // ← FAKE DATA (always 75)

  float tempCelsius = (temperature - 32.0) * 5.0 / 9.0;
  doc["skinTemperature"] = tempCelsius;  // ← FAKE DATA (always 37°C)

  doc["oxygenSaturation"] = (int)oxygenSat;  // ← FAKE DATA (always 98)
  doc["signalQuality"] = quality / 100.0;  // ← FAKE DATA (always 0.95)
  doc["respiratoryRate"] = (int)respiratoryRate;  // ← FAKE DATA (always 16)
  doc["batteryLevel"] = batteryLevel;  // ← FAKE DATA (starts 85)

  String payload;
  serializeJson(doc, payload);

  if (mqttClient.publish(topic.c_str(), payload.c_str())) {
    Serial.println("📊 Vitals: HR=" + String((int)heartRate) +
                   ", Temp=" + String(tempCelsius, 1) + "°C" +
                   ", SpO2=" + String(oxygenSat) + "%" +
                   ", RR=" + String(respiratoryRate));
  }
}
```

**Result:** Every vitals message sent to MQTT contains the same static values.

---

## What Should Happen (Real Hardware)

For a real hospital watch with MAX30102 (HR/SpO2) and MLX90614 (temperature) sensors:

```cpp
// Real sensor data
float heartRate = max30102.getHeartRate();  // Read from MAX30102
int oxygenSat = max30102.getSpO2();  // Read from MAX30102
float temperature = mlx90614.readObjectTempF();  // Read from MLX90614
int respiratoryRate = calculateRR();  // Derived from PPG waveform
float quality = max30102.getSignalQuality();  // Signal quality from sensor
```

---

## Options to Fix

### Option 1: Add Realistic Variation (Still Fake, But Better for Testing)

Add small random variations to simulate real sensors:

```cpp
// In loop() or sendVitals():
heartRate = 75 + random(-5, 6);  // 70-80 bpm
temperature = 98.6 + (random(-10, 11) / 10.0);  // 97.6-99.6°F
oxygenSat = 98 + random(-2, 3);  // 96-100%
respiratoryRate = 16 + random(-2, 3);  // 14-18 bpm
quality = 95.0 + (random(-5, 6) / 1.0);  // 90-100%
batteryLevel = max(0, batteryLevel - 1);  // Slow drain
```

**Pros:**
- Better for testing alert systems
- Simulates real patient variations
- Shows that system handles changing data

**Cons:**
- Still fake data
- Not from real sensors

---

### Option 2: Integrate Real Sensors (Production)

**Required Hardware:**
- **MAX30102**: Heart rate + SpO2 sensor (I2C)
- **MLX90614**: Infrared temperature sensor (I2C)
- **Battery monitoring**: Read actual ESP32 battery voltage

**Code Changes:**

```cpp
#include <Wire.h>
#include <MAX30105.h>  // Sparkfun library
#include <Adafruit_MLX90614.h>

MAX30105 max30102;
Adafruit_MLX90614 mlx90614 = Adafruit_MLX90614();

void setup() {
  // ... existing code ...

  // Initialize I2C sensors
  Wire.begin();

  if (!max30102.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println("❌ MAX30102 not found");
  } else {
    Serial.println("✅ MAX30102 initialized");
    max30102.setup();  // Configure LED brightness, sample rate, etc.
  }

  if (!mlx90614.begin()) {
    Serial.println("❌ MLX90614 not found");
  } else {
    Serial.println("✅ MLX90614 initialized");
  }
}

void readSensors() {
  // Read heart rate and SpO2
  if (max30102.check()) {  // Check if new data available
    heartRate = max30102.getHeartRate();
    oxygenSat = max30102.getSpO2();
    quality = max30102.getSignalQuality();
  }

  // Read temperature
  temperature = mlx90614.readObjectTempF();

  // Calculate respiratory rate from PPG waveform
  respiratoryRate = calculateRespiratoryRate();

  // Read battery level
  batteryLevel = readBatteryLevel();
}

void loop() {
  // ... existing code ...

  if (millis() - lastSensorRead > 1000) {
    readSensors();  // Read real sensor data every second
    lastSensorRead = millis();
  }

  // ... rest of loop ...
}
```

**Pros:**
- Real patient data
- Production-ready
- Accurate medical monitoring

**Cons:**
- Requires hardware sensors
- More complex code
- Sensor calibration needed

---

### Option 3: Remove Section Marker (Keep Code Same)

Just change the comment from "MOCK SENSOR DATA" to "SENSOR DATA" since the code will work the same way whether it's reading from sensors or using static values.

**Pros:**
- No functional change
- Clears up confusion

**Cons:**
- Still using fake data
- Misleading comment

---

## Recommendation

**For Development/Testing:** Use **Option 1** (Add Realistic Variation)
- Makes testing more realistic
- Helps test alert detection systems
- Shows UI updates properly
- Easy to implement

**For Production:** Use **Option 2** (Real Sensors)
- Required for actual hospital deployment
- Provides real patient monitoring
- Meets medical device standards

---

## Current Impact

**Does this affect functionality?**
- ✅ MQTT connection works fine
- ✅ Certificate auth works fine
- ✅ Sequential device IDs work fine
- ✅ Backend receives vitals
- ❌ **BUT: All vitals data is static/fake**

**Frontend Impact:**
- Frontend displays the fake static values
- No variation in vitals graphs
- Alert detection sees constant "normal" values
- Cannot test abnormal vital sign alerts

---

## Code Locations

1. **Variable Declaration:** [Lines 105-113](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L105-L113)
2. **sendVitals() Uses Fake Data:** [Lines 1311-1345](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1311-L1345)
3. **Battery Health Updates:** [Lines 378-391](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L378-L391) (has some variation)
4. **Sensor History:** [Lines 458-463](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L458-L463) (stores same value 5 times)

---

## Quick Fix for Testing (Option 1 Implementation)

Add this function and call it in `loop()` before `sendVitals()`:

```cpp
// Add after line 463 (after updateSensorHistory function)

void generateRealisticVitals() {
  // Simulate realistic vital sign variations

  // Heart rate: 70-85 bpm with occasional spikes
  heartRate = 75 + random(-5, 11);
  if (random(100) < 5) {  // 5% chance of spike
    heartRate += random(10, 30);
  }

  // Temperature: 97.0-99.5°F
  temperature = 98.6 + (random(-16, 9) / 10.0);

  // SpO2: 95-100%
  oxygenSat = 98 + random(-3, 3);
  oxygenSat = constrain(oxygenSat, 95, 100);

  // Respiratory rate: 12-20 breaths/min
  respiratoryRate = 16 + random(-4, 5);
  respiratoryRate = constrain(respiratoryRate, 12, 20);

  // Signal quality: 85-100%
  quality = 95.0 + (random(-10, 6) / 1.0);
  quality = constrain(quality, 85.0, 100.0);

  // Battery slowly drains (1% every ~5 minutes)
  if (millis() % 300000 == 0 && batteryLevel > 0) {
    batteryLevel--;
  }
}
```

Then in `loop()`, add before line 624:

```cpp
if (wifiConnected && isProvisioned && isAssigned && millis() - lastVitals > 1000) {
  generateRealisticVitals();  // ← ADD THIS LINE
  sendVitals();
  lastVitals = millis();
}
```

This will make vitals data vary realistically for testing purposes.

---

## Summary

**Current State:** ESP32 uses hardcoded static vital signs (HR=75, SpO2=98, Temp=98.6°F)

**Impact:** System works functionally, but all vitals data is fake and unchanging

**Quick Fix:** Add realistic variation for testing (Option 1)

**Production Fix:** Integrate real MAX30102 and MLX90614 sensors (Option 2)
