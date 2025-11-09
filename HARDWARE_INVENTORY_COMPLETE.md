# Hospital Watch - Complete Hardware Inventory

**Date:** 2025-11-06
**Architecture:** PhysiologicalSimulator (body) → Hardware Simulators (sensors) → ESP32 Firmware → MQTT

---

## Correct Architecture Understanding ✅

**You were absolutely right:**

```
PhysiologicalSimulator (simulates human body vitals)
    ↓ reads from
Hardware Simulators (simulate medical sensors)
    ↓ provide data to
ESP32 Firmware (watch software)
    ↓ transmits via
MQTT → Backend → Database
```

**Real Watch Would Work Exactly the Same:**
- Replace PhysiologicalSimulator → Real human body
- Replace Hardware Simulators → Real sensor chips (ADS1298, BMI323, etc.)
- ESP32 Firmware stays the same!

---

## All Hardware Simulators

### 1. ADS1298Simulator ✅ CURRENTLY USED
**Real Chip:** Texas Instruments ADS1298 (8-Channel 24-Bit ECG/EEG AFE)
**Purpose:** ECG and EEG waveform acquisition
**Integration:** Actively used in main firmware

**Capabilities:**
- 8 differential input channels
- 24-bit ADC resolution
- Sample rate: 500 Hz (2ms per sample)
- I2C Address: 0x40
- Lead-off detection
- Built-in right-leg drive (RLD)

**What it reads from PhysiologicalSimulator:**
- ECG waveform generation (PQRST morphology)
- EEG waveform generation (alpha/beta/theta/delta bands)
- Signal quality

**What it provides to firmware:**
- 8-channel raw waveform data (delta-encoded)
- Lead-off detection flags
- Impedance measurements per channel

---

### 2. BMI323Simulator ❌ NOT CURRENTLY USED
**Real Chip:** Bosch Sensortec BMI323 (6-Axis IMU)
**Purpose:** Motion tracking, fall detection, tremor analysis
**Integration:** Code exists but NOT included in main firmware

**Capabilities:**
- 3-axis accelerometer (±2g/±4g/±8g/±16g)
- 3-axis gyroscope (±125 to ±2000 dps)
- Sample rate: Up to 1600 Hz
- I2C Address: 0x68
- Built-in step counter (pedometer)
- Tap/double-tap detection
- No-motion detection

**What it reads from PhysiologicalSimulator:**
- Activity state (RESTING, LIGHT_ACTIVITY, EXERCISE, SLEEP)
- Tremor intensity (for overlay on motion)
- Heart rate (for cardiac vibration simulation)

**What it provides to firmware:**
- Raw accelerometer data (X, Y, Z)
- Raw gyroscope data (X, Y, Z)
- **Tremor intensity (0-10)** - FFT analysis of 4-12 Hz band ← USER ASKED ABOUT THIS
- **Fall risk score (0-10)** - State machine (NORMAL → FREEFALL → IMPACT → LYING)
- Step count
- Double-tap events
- Last movement time (bedsore prevention)

**Clinical Applications:**
- Parkinson's tremor monitoring
- Fall detection for elderly
- Activity tracking (steps, movement)
- Bedsore prevention (no-motion alerts)
- Gait analysis

---

### 3. MAX86178Simulator ❌ NOT CURRENTLY USED
**Real Chip:** Maxim Integrated MAX86178 (3-LED PPG + BioZ AFE)
**Purpose:** Heart rate, SpO2, perfusion index, bioimpedance
**Integration:** Code exists but NOT included in main firmware

**Capabilities:**
- 3 LEDs: Red (660nm), Green (537nm), IR (880nm)
- 20-bit ADC resolution
- Sample rate: 100 Hz (10ms period)
- I2C Address: 0x57
- Green LED optimized for equitable healthcare (works on all skin tones)
- Proximity detection (watch worn status)

**What it reads from PhysiologicalSimulator:**
- Heart rate (for PPG waveform timing)
- SpO2 (for red/IR ratio simulation)
- Respiratory rate (for bioimpedance modulation)

**What it provides to firmware:**
- Raw PPG samples (green, red, IR) - 20-bit
- Heart rate (from peak detection)
- SpO2 (from red/IR ratio)
- **Bioimpedance (Ω)** - **RESPIRATORY MONITORING** ← USER ASKED ABOUT THIS
- Perfusion index (shock/sepsis detection)
- Respiratory rate (from bioz modulation)
- Watch worn status (proximity detection)

**Bioimpedance Details:**
- **Purpose:** Respiratory monitoring (NOT sweat analysis)
- **Method:** Thoracic impedance measurement
- **Mechanism:** Lung volume changes → Chest impedance changes
- **Range:** 20-50 Ω (baseline ~30 Ω, ±2 Ω with breathing)
- **Modulation:** Sinusoidal with respiratory rate
- **Clinical Use:** Respiratory rate calculation, lung volume estimation, fluid retention detection

**User's Question:** "isn't it sweat analysis bioz?"
**Answer:** No - bioimpedance in MAX86178 is for **respiratory monitoring** (thoracic impedance), not sweat/hydration analysis. Whole-body bioimpedance scales (like InBody) measure 200-1000 Ω for hydration/body composition.

---

### 4. STS40Simulator ❌ NOT CURRENTLY USED
**Real Chip:** Sensirion STS40 (High-Accuracy Temperature Sensor)
**Purpose:** Precise skin temperature measurement
**Integration:** Code exists but NOT included in main firmware

**Capabilities:**
- Accuracy: ±0.1°C (0-65°C range)
- Resolution: 0.01°C
- I2C Address: 0x44
- Conversion time: 9ms (high precision mode)
- CRC-8 checksum (polynomial 0x31)

**What it reads from PhysiologicalSimulator:**
- Temperature (Fahrenheit, converts to Celsius)

**What it provides to firmware:**
- High-precision temperature in °C
- Raw 16-bit temperature counts
- CRC checksum for data integrity
- Conversion ready flag

**Why separate from PhysiologicalSimulator?**
- Simulates realistic I2C timing (9ms conversion delay)
- Simulates CRC checksum verification
- Adds realistic sensor noise (±0.05°C)
- Matches real STS40 hardware behavior

---

### 5. PhysiologicalSimulator ✅ CURRENTLY USED
**Purpose:** Simulates the human body (patient state)
**Integration:** Actively used in main firmware

**What it simulates:**
- **Core Vitals:**
  - Heart rate (40-200 BPM)
  - Temperature (95-105°F, converts to Celsius)
  - SpO2 (70-100%)
  - Respiratory rate (8-30 breaths/min)
  - Blood pressure systolic (100-180 mmHg) ✅ v5.2.14
  - Blood pressure diastolic (60-110 mmHg) ✅ v5.2.14

- **Advanced Vitals:**
  - **Bioimpedance (200-1000 Ω)** - Whole-body (hydration status)
  - **Tremor intensity (0-10)** - Simple state-based (0.2-2.0 range)
  - IMU fall risk (0-10) - Simple state-based (0.5-4.0 range)
  - ECG reading (representative mV)
  - EEG reading (representative μV)

- **Physiological States:**
  - RESTING (default)
  - LIGHT_ACTIVITY (walking)
  - EXERCISE (elevated vitals)
  - SLEEP (reduced vitals)

- **ECG/EEG Waveforms:**
  - 8-channel ECG (Lead I, II, III, aVR, aVL, aVF, V1-V6)
  - 8-channel EEG (Fp1, Fp2, F3, F4, C3, C4, O1, O2)
  - Calibration pulse support (1mV ECG, 100μV EEG)

**What it provides:**
- Getter methods for all vitals
- Waveform generation (500 Hz sampling)
- Natural variation (Perlin noise)
- Smooth transitions between states
- Realistic PQRST morphology (ECG)
- Frequency band mixing (EEG)

---

## Current Firmware Integration Status

### ✅ ACTIVELY USED:
1. **PhysiologicalSimulator** - Body state simulation
2. **ADS1298Simulator** - Via PhysiologicalSimulator waveform generation
3. **NFCManager** - NFC badge/wristband reading

### ❌ NOT INTEGRATED (Code exists but unused):
1. **BMI323Simulator** - IMU (accelerometer + gyroscope)
2. **MAX86178Simulator** - PPG + BioZ
3. **STS40Simulator** - High-precision temperature

---

## What Gets Transmitted Currently (v5.2.14)

### Via MQTT `hospital/devices/{deviceId}/vitals`:
✅ Heart rate
✅ Respiratory rate
✅ Skin temperature
✅ Oxygen saturation
✅ Battery level
✅ Signal quality
✅ Blood pressure systolic (**NEW v5.2.14**)
✅ Blood pressure diastolic (**NEW v5.2.14**)
❌ Tremor intensity
❌ Bioimpedance
❌ IMU fall risk
❌ Perfusion index
❌ Watch worn status
❌ Step count

### Via MQTT `hospital/devices/{deviceId}/stream`:
✅ 8-channel ECG waveforms (delta-encoded, 500 Hz)
✅ 8-channel EEG waveforms (delta-encoded, 500 Hz)
✅ Calibration pulses (1mV ECG, 100μV EEG)

---

## What Could Be Added (Already Implemented in Simulators)

### From BMI323Simulator:
- **Tremor intensity (0-10)** - FFT-based, realistic 4-12 Hz detection
- **Fall risk (0-10)** - State machine with FREEFALL/IMPACT/LYING detection
- **Step count** - Pedometer algorithm
- **Activity state** - STILL, WALKING, RUNNING, FALL_DETECTED
- **Last movement time** - For bedsore prevention alerts
- **Double-tap detection** - Watch interaction
- **Raw accelerometer** - X, Y, Z (±8g)
- **Raw gyroscope** - X, Y, Z (±2000 dps)

### From MAX86178Simulator:
- **Bioimpedance (20-50 Ω)** - Thoracic impedance for respiratory monitoring
- **Perfusion index (0-20%)** - Shock/sepsis detection (< 0.5% = CRITICAL)
- **Watch worn status** - Proximity detection
- **Raw PPG samples** - Green/Red/IR (20-bit, 100 Hz)
- **Heart rate** - From PPG peak detection (redundant with physio sim)
- **SpO2** - From red/IR ratio (redundant with physio sim)
- **Respiratory rate** - From bioimpedance modulation (redundant with physio sim)

### From STS40Simulator:
- **High-precision temperature** - ±0.1°C accuracy (better than current)
- **CRC checksum** - Data integrity verification
- **Temperature as Celsius** - No Fahrenheit→Celsius conversion

---

## User Questions Answered

### Q: "tremor and bioz?"
**A:** Yes, both exist!

**Tremor:**
- **Simple version:** PhysiologicalSimulator.getTremorIntensity() (0.2-2.0, state-based)
- **Advanced version:** BMI323Simulator.getTremorIntensity() (0-10, FFT-based 4-12 Hz)
- **Currently transmitted:** ❌ NO
- **Database ready:** ✅ Backend Pydantic model supports it
- **Implementation:** Need to add to ESP32 firmware MQTT transmission

**Bioimpedance:**
- **Purpose:** Respiratory monitoring (thoracic impedance), NOT sweat analysis
- **Simple version:** PhysiologicalSimulator.getBioimpedance() (450-590 Ω, whole-body)
- **Advanced version:** MAX86178Simulator.getBioimpedance() (20-50 Ω, thoracic)
- **Currently transmitted:** ❌ NO
- **Database ready:** ✅ Backend Pydantic model supports it
- **Implementation:** Need to add to ESP32 firmware MQTT transmission

### Q: "isn't this how watch would work?"
**A:** ✅ YES, EXACTLY!

**Simulator Architecture:**
```
PhysiologicalSimulator (human body)
    ↓
BMI323Simulator (reads body state, simulates IMU sensor)
MAX86178Simulator (reads body state, simulates PPG sensor)
STS40Simulator (reads body state, simulates temp sensor)
ADS1298Simulator (reads body state, simulates ECG/EEG AFE)
    ↓
ESP32 Firmware (watch software - reads from sensors)
    ↓
MQTT transmission to backend
```

**Real Watch Architecture:**
```
Real Human Body
    ↓
Real BMI323 chip (IMU sensor)
Real MAX86178 chip (PPG sensor)
Real STS40 chip (temp sensor)
Real ADS1298 chip (ECG/EEG AFE)
    ↓
ESP32 Firmware (SAME CODE! Just reads from real I2C instead of simulators)
    ↓
MQTT transmission to backend
```

**ESP32 firmware code would be nearly identical for real hardware!**

---

## Implementation Options

### Option 1: Use PhysiologicalSimulator (Quick - 15 min)
**Pros:**
- Already generating tremor (0.2-2.0) and bioz (450-590 Ω)
- Just add transmission via MQTT
- Minimal code changes

**Cons:**
- Less realistic (state-based, not sensor-based)
- Tremor range too narrow (0.2-2.0 instead of 0-10)
- Bioimpedance is whole-body (450-590 Ω), not thoracic (20-50 Ω)

**Changes:**
1. ESP32: Add `tremor` and `bioimpedance` to MQTT vitals message
2. Database: Add tremor (0-10) and bioimpedance (200-1000 Ω) columns
3. Backend: Update INSERT query

---

### Option 2: Integrate Hardware Simulators (Proper - 1-2 hours)
**Pros:**
- Realistic tremor from FFT analysis
- Correct thoracic bioimpedance (20-50 Ω)
- Advanced fall detection
- Perfusion index (sepsis detection)
- Step counting, activity tracking
- Future-ready for real hardware

**Cons:**
- More complex integration
- Need to manage multiple update() calls at different frequencies
- Longer implementation time

**Changes:**
1. ESP32: Include BMI323Simulator.h and MAX86178Simulator.h
2. ESP32: Instantiate simulators, pass PhysiologicalSimulator pointer
3. ESP32: Call update() at correct rates (BMI323: 1600Hz, MAX86178: 100Hz)
4. ESP32: Read tremor from BMI323, bioz from MAX86178
5. ESP32: Add to MQTT vitals message
6. Database: Add tremor (0-10), bioimpedance (20-50 Ω), imuFallRisk (0-10), perfusionIndex columns
7. Backend: Update INSERT query

---

## Recommended Path Forward

### Phase 1: Quick Win (PhysiologicalSimulator)
- Add tremor and bioimpedance transmission (15 min)
- Verify data pipeline works end-to-end
- Users can start seeing tremor/bioz charts

### Phase 2: Hardware Integration (Future)
- Integrate BMI323 for realistic tremor + fall detection
- Integrate MAX86178 for thoracic bioz + perfusion index
- Integrate STS40 for high-precision temperature
- Full sensor simulation matching real watch hardware

### Phase 3: Clinical Alerts (Backend)
- Tremor > 5.0 → Fall risk alert
- Tremor > 7.0 → Seizure detection
- Perfusion index < 0.5% → Sepsis/shock alert
- Bioimpedance trends → Fluid retention monitoring
- Combined fall risk scoring (IMU + meds + demographics)

---

## Decision Required

**User, please confirm:**
1. Start with Phase 1 (PhysiologicalSimulator - quick 15 min)?
2. Or go straight to Phase 2 (proper hardware integration - 1-2 hours)?
3. Any specific hardware capabilities you want to prioritize?

**My recommendation:** Start with Phase 1 to get data flowing, then plan Phase 2 for realistic sensor simulation.
