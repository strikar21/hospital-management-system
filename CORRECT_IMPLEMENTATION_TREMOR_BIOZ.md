# Tremor & Bioimpedance - CORRECT Implementation Plan

**Date:** 2025-11-06
**Architecture:** PhysiologicalSimulator → Sensor Simulators → ESP32 Firmware

---

## Architecture Correction ✅

### WRONG (Current ESP32 Firmware):
```
PhysiologicalSimulator
    ↓ ESP32 reads directly (BYPASSING SENSORS!)
ESP32 Firmware: heartRate = simulator.getHeartRate()
```

### CORRECT (What You Want):
```
PhysiologicalSimulator (human body)
    ↓ sensors measure body
Sensor Simulators (BMI323, MAX86178, STS40, ADS1298)
    ↓ sensor data to MCU
ESP32 Firmware: tremor = imu.getTremorIntensity()
```

**ESP32 should read from SENSORS, not bypass them!**

---

## Current ESP32 Code Analysis

**File:** `esp32_hospital_watch_complete.ino`

**Lines 1138-1144 (WRONG):**
```cpp
heartRate = simulator.getHeartRate();          // ❌ BYPASSING MAX86178!
temperature = simulator.getTemperature();      // ❌ BYPASSING STS40!
oxygenSat = simulator.getOxygenSaturation();   // ❌ BYPASSING MAX86178!
respiratoryRate = simulator.getRespiratoryRate(); // ❌ BYPASSING MAX86178!
quality = simulator.getSignalQuality();
bloodPressureSystolic = simulator.getBloodPressureSystolic();
bloodPressureDiastolic = simulator.getBloodPressureDiastolic();
```

**What's missing:**
- ❌ No BMI323Simulator instantiation
- ❌ No MAX86178Simulator instantiation
- ❌ No STS40Simulator instantiation
- ✅ ADS1298Simulator is used (for waveforms only)

---

## Correct Implementation Plan

### Step 1: Integrate Hardware Simulators

**Add to ESP32 firmware:**

```cpp
// At top of file (after line 100)
#include "BMI323Simulator.h"
#include "MAX86178Simulator.h"
#include "STS40Simulator.h"

// Create sensor instances (after line 227)
BMI323Simulator imu(&simulator);      // IMU sensor
MAX86178Simulator ppg(&simulator);    // PPG + BioZ sensor
STS40Simulator tempSensor(&simulator); // Temperature sensor

// In setup() (around line 1100)
void setup() {
  // ... existing code ...

  imu.begin();        // Initialize IMU
  ppg.begin();        // Initialize PPG
  tempSensor.begin(); // Initialize temp sensor
}

// In loop() - UPDATE SENSORS FIRST (before reading)
void loop() {
  // Update PhysiologicalSimulator (1 Hz)
  static unsigned long lastSimUpdate = 0;
  if (millis() - lastSimUpdate >= 1000) {
    simulator.update();
    lastSimUpdate = millis();
  }

  // Update IMU (1600 Hz)
  imu.update();

  // Update PPG (100 Hz)
  static unsigned long lastPPGUpdate = 0;
  if (millis() - lastPPGUpdate >= 10) {
    ppg.update();
    lastPPGUpdate = millis();
  }

  // Start temp measurement (as needed)
  static unsigned long lastTempStart = 0;
  if (millis() - lastTempStart >= 1000) {
    tempSensor.startMeasurement();
    lastTempStart = millis();
  }

  // NOW read from SENSORS (not PhysiologicalSimulator)
  heartRate = ppg.getHeartRate();              // ✅ From sensor
  oxygenSat = ppg.getSpO2();                   // ✅ From sensor
  respiratoryRate = ppg.getRespiratoryRate();  // ✅ From sensor

  if (tempSensor.isReady()) {
    temperature = tempSensor.readTemperature(); // ✅ From sensor
  }

  // NEW: Read tremor and bioimpedance from sensors
  tremor = imu.getTremorIntensity();           // ✅ From IMU sensor
  bioimpedance = ppg.getBioimpedance();        // ✅ From PPG sensor
  fallRisk = imu.getFallRisk();                // ✅ From IMU sensor
  perfusionIndex = ppg.getPerfusionIndex();    // ✅ From PPG sensor

  // ... rest of loop ...
}
```

---

### Step 2: Add New Vitals to MQTT Message

**In sendVitals() function (around line 1940):**

```cpp
// Existing vitals
doc["heartRate"] = (int)heartRate;
doc["respiratoryRate"] = (int)respiratoryRate;
doc["skinTemperature"] = tempCelsius;
doc["oxygenSaturation"] = (int)oxygenSat;
doc["bloodPressureSystolic"] = bloodPressureSystolic;
doc["bloodPressureDiastolic"] = bloodPressureDiastolic;
doc["signalQuality"] = quality / 100.0;
doc["batteryLevel"] = batteryLevel;

// NEW: Advanced vitals from sensors
doc["tremor"] = tremor;                        // From IMU
doc["bioimpedance"] = (int)bioimpedance;       // From PPG
doc["imuFallRisk"] = fallRisk;                 // From IMU
doc["perfusionIndex"] = perfusionIndex;        // From PPG
```

---

### Step 3: Add Global Variables

**After line 223:**

```cpp
float tremor = 0;              // From imu.getTremorIntensity()
float bioimpedance = 0;        // From ppg.getBioimpedance()
float fallRisk = 0;            // From imu.getFallRisk()
float perfusionIndex = 0;      // From ppg.getPerfusionIndex()
```

---

### Step 4: Database Schema

```sql
ALTER TABLE vitals_realtime
ADD COLUMN IF NOT EXISTS tremor NUMERIC(4,2),
ADD COLUMN IF NOT EXISTS bioimpedance NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS "imuFallRisk" NUMERIC(4,2),
ADD COLUMN IF NOT EXISTS "perfusionIndex" NUMERIC(5,2);

-- Constraints
ALTER TABLE vitals_realtime
ADD CONSTRAINT vitals_tremor_range CHECK (tremor BETWEEN 0.0 AND 10.0),
ADD CONSTRAINT vitals_bioimpedance_range CHECK (bioimpedance BETWEEN 20.0 AND 50.0),
ADD CONSTRAINT vitals_imu_fall_risk_range CHECK ("imuFallRisk" BETWEEN 0.0 AND 10.0),
ADD CONSTRAINT vitals_perfusion_index_range CHECK ("perfusionIndex" BETWEEN 0.0 AND 20.0);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_vitals_tremor
ON vitals_realtime ("patientId", tremor)
WHERE tremor > 5.0;

CREATE INDEX IF NOT EXISTS idx_vitals_fall_risk
ON vitals_realtime ("patientId", "imuFallRisk")
WHERE "imuFallRisk" > 7.0;

CREATE INDEX IF NOT EXISTS idx_vitals_perfusion
ON vitals_realtime ("patientId", "perfusionIndex")
WHERE "perfusionIndex" < 0.5;
```

**Note:** Bioimpedance range is 20-50 Ω (thoracic from MAX86178), NOT 200-1000 Ω

---

### Step 5: Backend UPDATE

**File:** `hospital-backend/app/models/neural_vitals.py`

**CRITICAL FIX (line 249):**
```python
# BEFORE:
bioimpedance: Optional[float] = Field(None, ge=200.0, le=1000.0, description="Bioelectrical impedance in Ohms")

# AFTER:
bioimpedance: Optional[float] = Field(None, ge=20.0, le=50.0, description="Thoracic bioimpedance in Ohms (MAX86178)")
```

**Add new field (line 253):**
```python
perfusionIndex: Optional[float] = Field(None, ge=0.0, le=20.0, description="Perfusion index percentage (MAX86178)")
```

**File:** `hospital-backend/app/services/mqtt_service.py`

**Update INSERT query (line 1167):**
```python
INSERT INTO vitals_realtime (
    ..., "systolicPressure", "diastolicPressure",
    tremor, bioimpedance, "imuFallRisk", "perfusionIndex",  # NEW
    "rrInterval", ...
) VALUES (
    ..., $11, $12, $13, $14, $15, $16, $17, ...  # Renumber params
)
```

**Parameter mapping:**
```python
vitalsMsg.systolicPressure, vitalsMsg.diastolicPressure,
vitalsMsg.tremor, vitalsMsg.bioimpedance, vitalsMsg.imuFallRisk, vitalsMsg.perfusionIndex,  # NEW
vitalsMsg.ecgAnalysis.rrInterval if vitalsMsg.ecgAnalysis else None,
```

---

## Timing Management

### Critical Timing Requirements:

1. **PhysiologicalSimulator:** 1 Hz (1000 ms)
   ```cpp
   if (millis() - lastSimUpdate >= 1000) {
     simulator.update();
   }
   ```

2. **BMI323 (IMU):** 1600 Hz (625 µs)
   ```cpp
   imu.update();  // Call every loop iteration (already fast enough)
   ```

3. **MAX86178 (PPG):** 100 Hz (10 ms)
   ```cpp
   if (millis() - lastPPGUpdate >= 10) {
     ppg.update();
   }
   ```

4. **STS40 (Temp):** On-demand (9 ms conversion)
   ```cpp
   tempSensor.startMeasurement();
   // Wait 9ms...
   if (tempSensor.isReady()) {
     temperature = tempSensor.readTemperature();
   }
   ```

5. **ADS1298 (ECG/EEG):** 500 Hz (2 ms) - already handled via PhysiologicalSimulator waveform generation

---

## What Each Sensor Provides

### BMI323 (IMU):
- **Tremor intensity:** 0-10 scale (FFT analysis of accelerometer data)
- **Fall risk:** 0-10 scale (state machine: NORMAL → FREEFALL → IMPACT → LYING)
- **Fall state:** Enum (NORMAL, FREEFALL, IMPACT, LYING)
- **Step count:** Pedometer (heel strike detection)
- **Last movement time:** For bedsore prevention alerts
- **Double-tap detection:** Watch interaction

### MAX86178 (PPG + BioZ):
- **Heart rate:** BPM from PPG peak detection
- **SpO2:** Percentage from red/IR ratio
- **Respiratory rate:** From bioimpedance modulation
- **Bioimpedance:** 28-32 Ω thoracic (respiratory monitoring)
- **Perfusion index:** 0-20% (< 0.5% = sepsis/shock detection)
- **Watch worn status:** Proximity detection

### STS40 (Temperature):
- **Temperature:** Celsius with ±0.1°C accuracy
- **Raw counts:** 16-bit ADC value
- **CRC checksum:** Data integrity

### ADS1298 (ECG/EEG ADC):
- **8-channel waveforms:** 24-bit ADC samples
- **Lead-off detection:** Per channel
- **Sample rate:** 500 Hz

---

## Version Update

**Update firmware version to v5.2.15:**

```cpp
* Version: 5.2.15
*
* - ✅ v5.2.15: FEATURE - Integrated BMI323 IMU sensor (tremor, fall detection)
* - ✅ v5.2.15: FEATURE - Integrated MAX86178 PPG sensor (bioimpedance, perfusion index)
* - ✅ v5.2.15: FEATURE - Integrated STS40 temperature sensor
* - ✅ v5.2.15: ARCHITECTURE FIX - ESP32 now reads from sensor simulators, not PhysiologicalSimulator directly
```

**Detailed changelog:**
```cpp
* ✅ v5.2.15: ARCHITECTURE FIX - Corrected data flow
* ✅ v5.2.15: PhysiologicalSimulator (body) → Sensors → ESP32 → MQTT
* ✅ v5.2.15: Added BMI323Simulator integration (tremor, fall risk, step count)
* ✅ v5.2.15: Added MAX86178Simulator integration (bioimpedance, perfusion index)
* ✅ v5.2.15: Added STS40Simulator integration (high-precision temperature)
* ✅ v5.2.15: ESP32 reads HR/SpO2/RR from MAX86178 (not PhysiologicalSimulator)
* ✅ v5.2.15: ESP32 reads temperature from STS40 (not PhysiologicalSimulator)
* ✅ v5.2.15: Result: Proper sensor simulation architecture, realistic hardware behavior
```

---

## Implementation Effort

**Estimated Time:** 2-3 hours

**Breakdown:**
- Add includes and instantiate sensors: 10 min
- Update timing in loop(): 30 min
- Change all reads from simulator to sensors: 20 min
- Add new vitals (tremor, bioz, fallRisk, perfusion): 10 min
- Database schema update: 10 min
- Backend Pydantic model update: 10 min
- Backend INSERT query update: 10 min
- Testing and debugging: 60 min

---

## Testing Plan

1. **Compile firmware** - Verify no errors
2. **Flash ESP32** - Upload new firmware
3. **Serial monitor:**
   - Verify sensor initialization messages
   - Check tremor values (should be 0-10, not 0.2-2.0)
   - Check bioimpedance (should be 28-32 Ω, not 450-590 Ω)
4. **MQTT broker:**
   - Verify new fields in JSON
   - Check field names (tremor, bioimpedance, imuFallRisk, perfusionIndex)
5. **Database:**
   - Query for tremor/bioz data
   - Verify values in correct ranges
6. **Backend logs:**
   - Check for validation errors
   - Verify INSERT query executes

---

## Rollback Plan

If integration fails:
1. Remove sensor includes
2. Revert to direct PhysiologicalSimulator reads
3. Flash previous firmware version (v5.2.14)
4. Revert database schema (DROP COLUMN)
5. Revert backend Pydantic model

---

## Summary

**You were absolutely correct:**
- ESP32 firmware is BYPASSING sensor simulators
- It's reading directly from PhysiologicalSimulator (wrong!)
- Sensors should be in the data path:
  - PhysiologicalSimulator (body)
  - → Sensor Simulators (measure body)
  - → ESP32 Firmware (read sensors)
  - → MQTT/Backend

**This implementation:**
- Fixes the architecture
- Integrates BMI323 (tremor, fall detection)
- Integrates MAX86178 (bioimpedance 28-32Ω, perfusion index)
- Integrates STS40 (high-precision temperature)
- ESP32 reads from sensors (not bypassing them)

**Ready to implement?** This is the correct architecture you described.
