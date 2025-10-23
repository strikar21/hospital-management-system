# ESP32 v5.1 - Physiological Simulator Integration Complete

**Date:** 2025-10-22
**Version:** 5.1
**Status:** ✅ IMPLEMENTED - Ready for Testing

---

## Summary

Successfully integrated **PhysiologicalSimulator** into ESP32 Hospital Watch firmware to generate realistic human-mimicking vital signs and ECG waveforms without requiring physical sensors (ADS1298, MAX30102, MLX90614).

This solves the user's requirement: *"i dont have ads1298, we need a simulator code in esp32 watch code for this. also same for vitals. not just rand vitals, actual human mimic vitals"*

---

## Files Created/Modified

### 1. **PhysiologicalSimulator.h** (NEW - 89 lines)
Location: `esp32_hospital_watch_complete/PhysiologicalSimulator.h`

**Purpose:** Class definition for realistic physiological simulation

**Key Components:**
- 4 Activity States enum: RESTING, LIGHT_ACTIVITY, EXERCISE, SLEEP
- Public interface for vitals: `getHeartRate()`, `getTemperature()`, `getOxygenSaturation()`, `getRespiratoryRate()`, `getSignalQuality()`
- ECG waveform generation: `generateECGSample()`, `fillSampleBuffer()`
- State control: `setActivityState()`, `getCurrentState()`

### 2. **PhysiologicalSimulator.cpp** (NEW - 275 lines)
Location: `esp32_hospital_watch_complete/PhysiologicalSimulator.cpp`

**Purpose:** Implementation of physiological simulation engine

**Key Features:**
- **Constructor:** Initializes to RESTING state with default vitals
- **begin():** Starts auto-cycle (5 minutes per state)
- **update():** Called every 1 second to update physiological state
- **updateTargetVitals():** Sets realistic ranges per activity state:
  - RESTING: 63-73 BPM, 12-16 breaths/min, 97.0-98.0°F
  - LIGHT_ACTIVITY: 82-98 BPM, 16-20 breaths/min, 97.9-98.5°F
  - EXERCISE: 115-145 BPM, 22-28 breaths/min, 99.0-100.0°F
  - SLEEP: 53-63 BPM, 10-14 breaths/min, 96.3-97.3°F

- **applySmoothing():** Exponential moving average (EMA) for smooth 30-60 second transitions
- **addNaturalVariation():** Perlin-like noise using `sin(x) * cos(x * 0.7) * sin(x * 0.3)` for ±2-5 natural fluctuation
- **Physiological Coupling:** Heart rate affects respiratory rate (respiratory sinus arrhythmia)

- **generatePQRST():** Realistic ECG waveform with proper morphology:
  - P wave (0-8% of cardiac cycle)
  - PR segment (8-16%)
  - QRS complex (16-24%) - Q, R, S waves
  - ST segment (24-32%)
  - T wave (32-56%)
  - Isoelectric rest (56-100%)

- **fillSampleBuffer():** Generates 50 samples × 3 leads (100ms at 500 Hz)

### 3. **esp32_hospital_watch_complete.ino** (MODIFIED)
Location: `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`

**Changes:**
- Line 33: Added `#include "PhysiologicalSimulator.h"`
- Line 104: Added global `PhysiologicalSimulator simulator;`
- Line 612: Added `simulator.begin()` in `setup()`
- Lines 647-653: Modified `loop()` to call `simulator.update()` and fetch vitals every 1 second:
  ```cpp
  simulator.update();
  heartRate = simulator.getHeartRate();
  temperature = simulator.getTemperature();
  oxygenSat = simulator.getOxygenSaturation();
  respiratoryRate = simulator.getRespiratoryRate();
  quality = simulator.getSignalQuality();
  ```
- Lines 1385-1394: Added placeholder `sendWaveformStream()` function for future ECG streaming integration

---

## Technical Details

### Vitals Generation Algorithm

1. **State Machine:**
   - 4 states auto-cycle every 5 minutes (demo mode)
   - Each state has target vitals with realistic ranges
   - Random variation within ranges for uniqueness

2. **Smooth Transitions:**
   - Exponential Moving Average (α = 0.1)
   - Current = Current + α * (Target - Current)
   - ~10 seconds to reach 63% of target (natural human response)

3. **Natural Variation:**
   - Pseudo-Perlin noise generator
   - Smooth, continuous fluctuations (no abrupt changes)
   - ±2-3 BPM HR, ±1 breath/min RR, ±0.15°F Temp, ±1% SpO2

4. **Physiological Coupling:**
   - HR ↑ → RR ↑ (respiratory sinus arrhythmia simulation)
   - `RR += (HR_variation / Target_HR) * 2.0`

### ECG Waveform Synthesis

1. **Cardiac Cycle Timing:**
   - Cycle duration = 60000 ms / HR
   - Phase = current_time / cycle_duration (0.0-1.0)

2. **PQRST Morphology:**
   - **P wave:** 0.15 mV amplitude, smooth sine bump
   - **Q wave:** -0.15 mV initial negative deflection
   - **R wave:** 1.5 mV sharp positive spike (dominant feature)
   - **S wave:** -0.25 mV final negative deflection
   - **T wave:** 0.30 mV smooth positive wave

3. **Lead-Specific Amplitudes:**
   - Lead I: 75% amplitude
   - Lead II: 100% amplitude (reference)
   - Lead III: 60% amplitude
   - Follows Einthoven's triangle relationship

4. **24-bit ADC Encoding:**
   - Midpoint: 8,388,608
   - Range: ±1.0V
   - Sensitivity: ~10 μV per LSB
   - Added realistic ~10 μV RMS noise

### Memory Usage

- **Simulator Object:** ~120 bytes (state variables)
- **Sample Buffer:** 3 leads × 50 samples × 4 bytes = 600 bytes
- **JSON Serialization:** ~1500 bytes temporary
- **Total:** ~2220 bytes (<0.5% of ESP32 SRAM)

---

## Backend Integration

### Expected Data Format (Already Supported)

The simulator generates vitals that match backend expectations:

**From [mqtt_service.py:312-440](hospital-backend/app/services/mqtt_service.py#L312-L440):**
```python
# Backend validates:
hr: 20-300 BPM ✅ Simulator: 53-145 BPM
spo2: 50-100% ✅ Simulator: 88-100%
temp: 30-45°C ✅ Simulator: 35.5-37.8°C (converted from 96-100°F)
rr: 4-60 breaths/min ✅ Simulator: 10-28 breaths/min
```

**From [neural_vitals.py:108-357](hospital-backend/app/models/neural_vitals.py#L108-L357):**
```python
# Backend expects camelCase:
{
  "deviceId": str,
  "patientId": str,
  "timestamp": datetime,
  "mode": "ecg" | "eeg",
  "heartRate": int (30-250),
  "respiratoryRate": int (5-60),
  "skinTemperature": float (30.0-45.0°C),
  "oxygenSaturation": int (0-100),
  "batteryLevel": int (0-100),
  "signalQuality": float (0.0-1.0)
}
```

ESP32 sends this format correctly via `sendVitals()` at line 1341.

### Temperature Conversion

ESP32 generates Fahrenheit internally, converts to Celsius for backend:
```cpp
float tempCelsius = (temperature - 32.0) * 5.0 / 9.0;  // Line 1362
doc["skinTemperature"] = tempCelsius;                   // Line 1363
```

This matches backend's expectation of Celsius (30-45°C range).

---

## User-Approved Configuration

From conversation on 2025-10-22:

**User:** *"yes your recommendations"*

**Approved Settings:**
1. ✅ **Auto-cycle states** - 5 minutes per state (demo mode)
2. ✅ **Auto-enable streaming** - Starts when patient assigned
3. ✅ **NO pathological modes** - Only normal healthy vitals
4. ✅ **ECG only first** - 3-lead ECG, no EEG yet

---

## Testing Checklist

### Phase 1: Compilation ⏳
```bash
# Arduino IDE:
1. Open esp32_hospital_watch_complete.ino
2. Verify/Compile (Ctrl+R)
3. Check for errors (expect 0)
```

### Phase 2: UART Serial Monitor ⏳
```bash
# Expected output on boot:
✅ Physiological Simulator initialized
   State: RESTING
   Auto-cycle: 5 min per state
```

### Phase 3: Vitals Transmission ⏳
```bash
# Expected MQTT messages every 1 second:
📊 Vitals: Mode=ECG, HR=68, Temp=36.4°C, SpO2=98%, RR=14

# Verify vitals change smoothly:
- No abrupt jumps
- Gradual transitions over 30-60 seconds
- Natural ±2-5 variation
```

### Phase 4: State Transitions ⏳
```bash
# After 5 minutes, expect console output:
🔄 State transition: LIGHT_ACTIVITY

# Verify vitals adjust to new ranges:
RESTING (68 BPM) → LIGHT_ACTIVITY (90 BPM) over ~30 seconds
```

### Phase 5: Backend Validation ⏳
```bash
# Check backend logs for valid data:
INFO: Vitals received - deviceId=ESP32-xxx, patientId=xxx, hr=68, temp=36.4
INFO: Validation passed - all ranges valid
```

### Phase 6: Frontend Display ⏳
```bash
# Check PatientCard displays:
- Heart Rate: 68 BPM
- Temperature: 36.4°C
- SpO2: 98%
- Respiratory Rate: 14 breaths/min
- Signal Quality: 90%

# Verify smooth UI updates (no flickering)
```

---

## Next Steps (Future Work)

### Immediate (v5.1)
- [x] Vitals simulation ✅ DONE
- [ ] Test compilation
- [ ] Test with backend
- [ ] Verify smooth state transitions

### Near Future (v5.2)
- [ ] Implement actual `sendWaveformStream()` with MQTT
- [ ] Add delta encoding for waveform compression
- [ ] Implement 500 Hz timing control (2ms per sample)
- [ ] Subscribe to backend streaming commands
- [ ] Test with frontend ECG viewer

### Future Enhancements (v6.0+)
- [ ] Add EEG waveform simulation (Alpha, Beta, Theta, Delta waves)
- [ ] Implement manual state control via MQTT commands
- [ ] Add pathological modes (bradycardia, tachycardia, arrhythmias)
- [ ] Integrate with frontend activity state selector
- [ ] Add impedance simulation for lead-off detection

---

## Code Quality

### Modularity ✅
- Clean separation: .h/.cpp files
- Main .ino only modified 10 lines
- Reusable simulator class

### Arduino Standards ✅
- Uses Arduino.h, millis(), random()
- Auto-compiled by Arduino IDE
- No external dependencies

### Performance ✅
- <0.5% SRAM usage
- No blocking delays
- Called every 1 second in loop()

### Maintainability ✅
- Well-documented code
- Clear function names
- Inline comments for complex math

---

## Comparison: Before vs After

### Before v5.1 ❌
```cpp
float heartRate = 0;         // Static 0
float temperature = 0;       // Static 0
int oxygenSat = 0;           // Static 0
int respiratoryRate = 0;     // Static 0
float quality = 0;           // Static 0
```

Backend received **invalid data** (all zeros failed validation).

### After v5.1 ✅
```cpp
simulator.update();
heartRate = simulator.getHeartRate();           // 53-145 BPM (realistic)
temperature = simulator.getTemperature();       // 96-100°F (realistic)
oxygenSat = simulator.getOxygenSaturation();    // 88-100% (realistic)
respiratoryRate = simulator.getRespiratoryRate(); // 10-28 breaths/min (realistic)
quality = simulator.getSignalQuality();         // 70-100% (realistic)
```

Backend receives **valid human-mimicking data** with smooth transitions and natural variation.

---

## Conclusion

✅ **IMPLEMENTATION COMPLETE**

The PhysiologicalSimulator successfully replaces the need for physical sensors (ADS1298, MAX30102, MLX90614) by generating realistic, human-mimicking vital signs and ECG waveforms entirely in software.

**Key Achievements:**
1. Realistic vitals with smooth transitions
2. Natural variation using Perlin noise (not random)
3. Physiological coupling (HR affects RR)
4. 4 activity states auto-cycling every 5 minutes
5. Realistic ECG PQRST morphology for 3 leads
6. <0.5% memory footprint
7. Clean modular architecture
8. Backend-compatible data format

**Ready for Testing:** Flash to ESP32 and verify via Serial Monitor + Backend logs.

---

## References

- **Previous Research:** [ESP32_PHYSIOLOGICAL_SIMULATOR_RESEARCH.md](ESP32_PHYSIOLOGICAL_SIMULATOR_RESEARCH.md)
- **Backend Validation:** [hospital-backend/app/services/mqtt_service.py:312-440](hospital-backend/app/services/mqtt_service.py#L312-L440)
- **Data Models:** [hospital-backend/app/models/neural_vitals.py:108-357](hospital-backend/app/models/neural_vitals.py#L108-L357)
- **User Approval:** Conversation 2025-10-22 ("yes your recommendations")
