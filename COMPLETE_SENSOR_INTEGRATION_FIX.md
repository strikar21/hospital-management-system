# Complete Sensor Integration Fix - ALL Sensors

**Date:** 2025-11-06
**Issue:** ESP32 bypassing ALL sensor simulators, reading directly from PhysiologicalSimulator
**Fix:** Integrate ALL sensor simulators properly

---

## Current Architecture (WRONG ❌)

```
PhysiologicalSimulator
    ↓ ESP32 reads DIRECTLY (bypassing sensors!)
ESP32 Firmware
    heartRate = simulator.getHeartRate()          // WRONG!
    temperature = simulator.getTemperature()      // WRONG!
    oxygenSat = simulator.getOxygenSaturation()   // WRONG!
    respiratoryRate = simulator.getRespiratoryRate() // WRONG!
    bloodPressure = simulator.getBloodPressure()  // WRONG!
```

---

## Correct Architecture (What You Want ✅)

```
PhysiologicalSimulator (Human Body)
    ↓ sensors measure body
    ↓
BMI323Simulator (IMU)
    - Reads: Activity state, tremor from body
    - Measures: Accelerometer, gyroscope data
    - Provides: Tremor, fall risk, steps, orientation
    ↓
MAX86178Simulator (PPG + BioZ)
    - Reads: HR, SpO2, RR from body
    - Measures: PPG waveforms (green/red/IR), bioimpedance
    - Provides: HR, SpO2, RR, bioimpedance, perfusion index
    ↓
STS40Simulator (Temperature)
    - Reads: Temperature from body
    - Measures: Temperature with I2C protocol
    - Provides: Temperature with CRC, timing simulation
    ↓
ADS1298Simulator (ECG/EEG ADC)
    - Reads: ECG/EEG waveforms from body
    - Measures: 8-channel 24-bit ADC samples
    - Provides: Lead I/II/III/aVR/aVL/aVF/V1-V6 or Fp1/Fp2/F3/F4/C3/C4/O1/O2
    ↓
ESP32 Firmware (MCU reads from SENSORS, not body!)
    heartRate = ppg.getHeartRate()           // ✅ CORRECT
    temperature = tempSensor.readTemperature() // ✅ CORRECT
    tremor = imu.getTremorIntensity()        // ✅ CORRECT
```

---

## Current ESP32 Code Audit (Lines 1138-1144)

### What's Being Read Directly from PhysiologicalSimulator (WRONG):

| Vital | Current Code | Should Read From |
|-------|--------------|------------------|
| Heart Rate | `simulator.getHeartRate()` | ❌ `ppg.getHeartRate()` (MAX86178) |
| Temperature | `simulator.getTemperature()` | ❌ `tempSensor.readTemperature()` (STS40) |
| SpO2 | `simulator.getOxygenSaturation()` | ❌ `ppg.getSpO2()` (MAX86178) |
| Respiratory Rate | `simulator.getRespiratoryRate()` | ❌ `ppg.getRespiratoryRate()` (MAX86178) |
| Signal Quality | `simulator.getSignalQuality()` | ❌ Calculate from sensor quality metrics |
| Blood Pressure | `simulator.getBloodPressure*()` | ⚠️ No sensor for BP (keep PhysiologicalSimulator) |

### What's Missing Entirely:

| Vital | Sensor Source | Current Status |
|-------|---------------|----------------|
| **Tremor** | `imu.getTremorIntensity()` (BMI323) | ❌ Not read at all |
| **Bioimpedance** | `ppg.getBioimpedance()` (MAX86178) | ❌ Not read at all |
| **Fall Risk** | `imu.getFallRisk()` (BMI323) | ❌ Not read at all |
| **Fall State** | `imu.getFallState()` (BMI323) | ❌ Not read at all |
| **Perfusion Index** | `ppg.getPerfusionIndex()` (MAX86178) | ❌ Not read at all |
| **Step Count** | `imu.getStepCount()` (BMI323) | ❌ Not read at all |
| **Watch Worn** | `ppg.isWatchWorn()` (MAX86178) | ❌ Not read at all |
| **Last Movement** | `imu.getLastMovementTime()` (BMI323) | ❌ Not read at all |

---

## Complete Sensor Integration Plan

### Step 1: Add Includes

**File:** `esp32_hospital_watch_complete.ino`
**After line 100:**

```cpp
#include "PhysiologicalSimulator.h"  // ✅ Already included
#include "NFCManager.h"              // ✅ Already included
#include "BMI323Simulator.h"         // ✅ ADD THIS
#include "MAX86178Simulator.h"       // ✅ ADD THIS
#include "STS40Simulator.h"          // ✅ ADD THIS
#include "ADS1298Simulator.h"        // ✅ ADD THIS (if not already)
```

---

### Step 2: Instantiate Sensors

**After line 227 (after PhysiologicalSimulator declaration):**

```cpp
// ====================================
// SENSOR SIMULATORS (Hardware Layer)
// ====================================
PhysiologicalSimulator simulator;  // ✅ Already exists

// Hardware sensors that measure the simulated body
BMI323Simulator imu(&simulator);        // 6-axis IMU (accel + gyro)
MAX86178Simulator ppg(&simulator);      // 3-LED PPG + BioZ
STS40Simulator tempSensor(&simulator);  // High-precision temperature
ADS1298Simulator adc(&simulator);       // 8-channel ECG/EEG ADC
```

---

### Step 3: Initialize Sensors in setup()

**In setup() function (around line 1100):**

```cpp
void setup() {
  Serial.begin(115200);
  delay(1000);

  // ====================================
  // SENSOR INITIALIZATION
  // ====================================
  Serial.println("\n🔬 Initializing Sensor Simulators...");

  // Initialize body simulator
  simulator.begin();
  Serial.println("✅ PhysiologicalSimulator (body) initialized");

  // Initialize hardware sensors
  imu.begin();
  Serial.println("✅ BMI323 (IMU) initialized");

  ppg.begin();
  Serial.println("✅ MAX86178 (PPG + BioZ) initialized");

  tempSensor.begin();
  Serial.println("✅ STS40 (Temperature) initialized");

  adc.begin();
  Serial.println("✅ ADS1298 (ECG/EEG ADC) initialized");

  // ... rest of setup ...
}
```

---

### Step 4: Update Sensor Data in loop()

**Replace lines 1136-1144:**

```cpp
// OLD CODE (WRONG - bypassing sensors):
/*
simulator.update();
heartRate = simulator.getHeartRate();
temperature = simulator.getTemperature();
oxygenSat = simulator.getOxygenSaturation();
respiratoryRate = simulator.getRespiratoryRate();
quality = simulator.getSignalQuality();
bloodPressureSystolic = simulator.getBloodPressureSystolic();
bloodPressureDiastolic = simulator.getBloodPressureDiastolic();
*/

// NEW CODE (CORRECT - reading from sensors):

// 1. Update PhysiologicalSimulator (body state) - 1 Hz
static unsigned long lastPhysioUpdate = 0;
if (millis() - lastPhysioUpdate >= 1000) {
  simulator.update();
  lastPhysioUpdate = millis();
}

// 2. Update IMU sensor - 1600 Hz (call every loop iteration)
imu.update();

// 3. Update PPG sensor - 100 Hz (every 10ms)
static unsigned long lastPPGUpdate = 0;
if (millis() - lastPPGUpdate >= 10) {
  ppg.update();
  lastPPGUpdate = millis();
}

// 4. Update temperature sensor - on-demand (every 1 second)
static unsigned long lastTempStart = 0;
if (millis() - lastTempStart >= 1000) {
  tempSensor.startMeasurement();
  lastTempStart = millis();
}

// 5. Update ADC sensor - 500 Hz (already handled by waveform generation timing)
// adc.update() is called in waveform generation section

// ====================================
// READ FROM SENSORS (not PhysiologicalSimulator!)
// ====================================

// Cardiovascular vitals from PPG sensor
heartRate = ppg.getHeartRate();              // ✅ From MAX86178
oxygenSat = ppg.getSpO2();                   // ✅ From MAX86178
respiratoryRate = ppg.getRespiratoryRate();  // ✅ From MAX86178

// Temperature from temperature sensor
if (tempSensor.isReady()) {
  float tempF = tempSensor.readTemperature();
  // Convert Celsius to Fahrenheit (STS40 returns Celsius)
  temperature = tempF;  // Already in °F if we want, or keep as Celsius
}

// Blood pressure - NO SENSOR for this, keep from PhysiologicalSimulator
bloodPressureSystolic = simulator.getBloodPressureSystolic();
bloodPressureDiastolic = simulator.getBloodPressureDiastolic();

// Signal quality - aggregate from all sensors
float ppgQuality = ppg.getPerfusionIndex() * 5.0;  // 0-20% → 0-100%
float imuQuality = (imu.getFallRisk() < 7.0) ? 90.0 : 50.0;  // High fall risk = poor quality
quality = (ppgQuality + imuQuality) / 2.0;

// ====================================
// NEW: Advanced vitals from sensors
// ====================================

// IMU sensor data
tremor = imu.getTremorIntensity();           // 0-10 scale
fallRisk = imu.getFallRisk();                // 0-10 scale
String fallState = imu.getFallRiskCategory(); // "low", "medium", "high", "critical"
stepCount = imu.getStepCount();              // Pedometer
unsigned long lastMovement = imu.getLastMovementTime(); // ms since last movement

// PPG sensor data
bioimpedance = ppg.getBioimpedance();        // 28-32 Ω (thoracic)
perfusionIndex = ppg.getPerfusionIndex();    // 0-20% (sepsis detection)
watchWorn = ppg.isWatchWorn();               // true/false

// Battery level - no sensor, keep simulated
batteryLevel = 100;  // TODO: Add real battery ADC reading
```

---

### Step 5: Add New Global Variables

**After line 223:**

```cpp
// Existing vitals
float heartRate = 0;
float temperature = 0;
int oxygenSat = 0;
int batteryLevel = 100;
int respiratoryRate = 0;
float quality = 0;
int bloodPressureSystolic = 0;
int bloodPressureDiastolic = 0;

// NEW: Advanced vitals from sensors
float tremor = 0;              // BMI323
float bioimpedance = 0;        // MAX86178 (28-32 Ω thoracic)
float fallRisk = 0;            // BMI323 (0-10)
uint32_t stepCount = 0;        // BMI323
float perfusionIndex = 0;      // MAX86178 (0-20%)
bool watchWorn = true;         // MAX86178
unsigned long lastMovement = 0; // BMI323 (ms)
```

---

### Step 6: Update MQTT Transmission

**In sendVitals() function (around line 1940):**

```cpp
// Existing vitals
doc["deviceId"] = String(DEVICE_ID);
doc["patientId"] = String(patientId);
doc["timestamp"] = getISO8601Timestamp();
doc["mode"] = isECGMode ? "ecg" : "eeg";
doc["heartRate"] = (int)heartRate;
doc["respiratoryRate"] = (int)respiratoryRate;
doc["skinTemperature"] = tempCelsius;
doc["oxygenSaturation"] = (int)oxygenSat;
doc["bloodPressureSystolic"] = bloodPressureSystolic;
doc["bloodPressureDiastolic"] = bloodPressureDiastolic;
doc["signalQuality"] = quality / 100.0;
doc["batteryLevel"] = batteryLevel;
doc["sequence"] = vitalsSequenceCounter++;

// NEW: Advanced sensor data
doc["tremor"] = tremor;                        // BMI323
doc["bioimpedance"] = (int)bioimpedance;       // MAX86178
doc["imuFallRisk"] = fallRisk;                 // BMI323
doc["perfusionIndex"] = perfusionIndex;        // MAX86178
doc["stepCount"] = stepCount;                  // BMI323
doc["watchWorn"] = watchWorn;                  // MAX86178
doc["lastMovementTime"] = lastMovement;        // BMI323 (ms)
```

---

### Step 7: Database Schema Update

```sql
-- Add new columns from sensors
ALTER TABLE vitals_realtime
ADD COLUMN IF NOT EXISTS tremor NUMERIC(4,2),
ADD COLUMN IF NOT EXISTS bioimpedance NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS "imuFallRisk" NUMERIC(4,2),
ADD COLUMN IF NOT EXISTS "perfusionIndex" NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS "stepCount" INTEGER,
ADD COLUMN IF NOT EXISTS "watchWorn" BOOLEAN,
ADD COLUMN IF NOT EXISTS "lastMovementTime" INTEGER;

-- Add constraints
ALTER TABLE vitals_realtime
ADD CONSTRAINT vitals_tremor_range CHECK (tremor BETWEEN 0.0 AND 10.0),
ADD CONSTRAINT vitals_bioimpedance_range CHECK (bioimpedance BETWEEN 20.0 AND 50.0),
ADD CONSTRAINT vitals_imu_fall_risk_range CHECK ("imuFallRisk" BETWEEN 0.0 AND 10.0),
ADD CONSTRAINT vitals_perfusion_index_range CHECK ("perfusionIndex" BETWEEN 0.0 AND 20.0);

-- Add indexes for critical values
CREATE INDEX IF NOT EXISTS idx_vitals_tremor
ON vitals_realtime ("patientId", tremor)
WHERE tremor > 5.0;

CREATE INDEX IF NOT EXISTS idx_vitals_fall_risk
ON vitals_realtime ("patientId", "imuFallRisk")
WHERE "imuFallRisk" > 7.0;

CREATE INDEX IF NOT EXISTS idx_vitals_perfusion
ON vitals_realtime ("patientId", "perfusionIndex")
WHERE "perfusionIndex" < 0.5;

CREATE INDEX IF NOT EXISTS idx_vitals_watch_off
ON vitals_realtime ("patientId", "watchWorn", time)
WHERE "watchWorn" = false;

-- Verify columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'vitals_realtime'
  AND column_name IN ('tremor', 'bioimpedance', 'imuFallRisk', 'perfusionIndex', 'stepCount', 'watchWorn', 'lastMovementTime')
ORDER BY column_name;
```

---

### Step 8: Backend Pydantic Model Update

**File:** `hospital-backend/app/models/neural_vitals.py`

**Update line 249 (CRITICAL FIX):**
```python
# BEFORE:
bioimpedance: Optional[float] = Field(None, ge=200.0, le=1000.0, description="Bioelectrical impedance in Ohms")

# AFTER:
bioimpedance: Optional[float] = Field(None, ge=20.0, le=50.0, description="Thoracic bioimpedance in Ohms (MAX86178)")
```

**Add new fields (after line 253):**
```python
# Advanced vitals (from ESP32 sensors v5.2.15+)
bioimpedance: Optional[float] = Field(None, ge=20.0, le=50.0, description="Thoracic bioimpedance in Ohms (MAX86178)")
tremor: Optional[float] = Field(None, ge=0.0, le=10.0, description="Tremor intensity 0-10 (BMI323)")
imuFallRisk: Optional[float] = Field(None, ge=0.0, le=10.0, description="IMU fall risk 0-10 (BMI323)")
perfusionIndex: Optional[float] = Field(None, ge=0.0, le=20.0, description="Perfusion index percentage (MAX86178)")
stepCount: Optional[int] = Field(None, ge=0, description="Step counter (BMI323)")
watchWorn: Optional[bool] = Field(None, description="Watch worn status (MAX86178)")
lastMovementTime: Optional[int] = Field(None, ge=0, description="Milliseconds since last movement (BMI323)")
```

---

### Step 9: Backend MQTT Service Update

**File:** `hospital-backend/app/services/mqtt_service.py`

**Update INSERT query (line 1167):**

```python
INSERT INTO vitals_realtime (
    time, "patientId", "deviceId", mode,
    "heartRate", "respiratoryRate", "skinTemperature",
    "oxygenSaturation", "batteryLevel", "signalQuality",
    "systolicPressure", "diastolicPressure",
    tremor, bioimpedance, "imuFallRisk", "perfusionIndex",
    "stepCount", "watchWorn", "lastMovementTime",  -- NEW FIELDS
    "rrInterval", "qrsDuration", "qtInterval", axis, rhythm, "stSegment",
    "alphaPower", "betaPower", "thetaPower", "deltaPower", "gammaPower",
    "dominantFrequency", "seizureActivity",
    quality, sequence, metadata
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
    $13, $14, $15, $16, $17, $18, $19,  -- NEW PARAMS
    $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32, $33, $34, $35
)
```

**Update parameter mapping:**
```python
vitalsMsg.timestamp, vitalsMsg.patientId, vitalsMsg.deviceId, vitalsMsg.mode,
vitalsMsg.heartRate, vitalsMsg.respiratoryRate, vitalsMsg.skinTemperature,
vitalsMsg.oxygenSaturation, vitalsMsg.batteryLevel, vitalsMsg.signalQuality,
vitalsMsg.bloodPressureSystolic, vitalsMsg.bloodPressureDiastolic,
vitalsMsg.tremor, vitalsMsg.bioimpedance, vitalsMsg.imuFallRisk, vitalsMsg.perfusionIndex,
vitalsMsg.stepCount, vitalsMsg.watchWorn, vitalsMsg.lastMovementTime,  # NEW
vitalsMsg.ecgAnalysis.rrInterval if vitalsMsg.ecgAnalysis else None,
# ... rest of parameters
```

---

### Step 10: Version Update

**Update firmware version to v5.2.15:**

```cpp
/*
 * ESP32 Hospital Watch - Certificate-Based Authentication + Waveform Streaming
 * Version: 5.2.15
 *
 * ✅ v5.2.15: ARCHITECTURE FIX - Complete sensor integration
 * ✅ v5.2.15: Integrated BMI323 IMU sensor (tremor, fall detection, pedometer)
 * ✅ v5.2.15: Integrated MAX86178 PPG sensor (bioimpedance, perfusion index)
 * ✅ v5.2.15: Integrated STS40 temperature sensor (high-precision, CRC)
 * ✅ v5.2.15: Integrated ADS1298 ADC sensor (8-channel ECG/EEG)
 * ✅ v5.2.15: ESP32 now reads from SENSORS, not PhysiologicalSimulator directly
 * ✅ v5.2.15: Correct data flow: Body → Sensors → ESP32 → MQTT
 */
```

---

## Summary of Changes

### Sensors Now Properly Integrated:

| Sensor | Purpose | New Data Provided |
|--------|---------|-------------------|
| **BMI323** | 6-axis IMU | Tremor (0-10), fall risk (0-10), step count, last movement time |
| **MAX86178** | PPG + BioZ | Bioimpedance (28-32Ω), perfusion index (0-20%), watch worn status |
| **STS40** | Temperature | High-precision temp with CRC and timing simulation |
| **ADS1298** | ECG/EEG ADC | 8-channel 24-bit waveforms (already integrated for waveforms) |

### Vitals Source Correction:

| Vital | OLD (Wrong) | NEW (Correct) |
|-------|-------------|---------------|
| Heart Rate | `simulator.getHeartRate()` | `ppg.getHeartRate()` |
| SpO2 | `simulator.getOxygenSaturation()` | `ppg.getSpO2()` |
| Respiratory Rate | `simulator.getRespiratoryRate()` | `ppg.getRespiratoryRate()` |
| Temperature | `simulator.getTemperature()` | `tempSensor.readTemperature()` |
| Blood Pressure | `simulator.getBloodPressure*()` | ✅ Keep (no sensor for BP) |

---

## Implementation Effort

**Estimated Time:** 3-4 hours

**Breakdown:**
- Add sensor includes and instantiation: 15 min
- Update setup() to initialize sensors: 15 min
- Rewrite loop() sensor updates and reads: 60 min
- Add new vitals to MQTT message: 20 min
- Database schema update: 15 min
- Backend Pydantic model update: 20 min
- Backend INSERT query update: 20 min
- Testing and debugging: 90 min

---

## Testing Checklist

### ESP32 Firmware:
- [ ] Compile with no errors
- [ ] Flash to device
- [ ] Serial monitor shows sensor initialization messages
- [ ] Verify tremor values (0-10 range, not 0.2-2.0)
- [ ] Verify bioimpedance (28-32 Ω, not 450-590 Ω)
- [ ] Verify fall risk updates (state machine working)
- [ ] Verify perfusion index (< 0.5% alerts)

### MQTT:
- [ ] Verify new fields in JSON payload
- [ ] Check field names match backend model
- [ ] Verify values in correct ranges

### Database:
- [ ] Query for new columns
- [ ] Verify data insertion
- [ ] Check constraints working
- [ ] Test indexes created

### Backend:
- [ ] No Pydantic validation errors
- [ ] INSERT query executes successfully
- [ ] Data appears in vitals_realtime table
- [ ] API endpoints return new fields

---

## Ready to Implement?

This fixes the complete architecture to match what you described:
- PhysiologicalSimulator (body) → Sensors → ESP32 → MQTT
- ESP32 reads from sensors, not bypassing them
- All 4 hardware sensors properly integrated
- 7 new vitals transmitted (tremor, bioimpedance, fall risk, perfusion, steps, watch worn, last movement)

**Shall I proceed with implementation?**
