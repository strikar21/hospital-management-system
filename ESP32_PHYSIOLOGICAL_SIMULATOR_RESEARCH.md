# ESP32 Physiological Simulator - Research & Implementation Plan

**Date:** 2025-10-22
**Purpose:** Create realistic human vital signs and ECG/EEG waveform simulators for ESP32 (no hardware required)
**Status:** ✅ Research Complete - Ready for Plan Review

---

## Research Summary - What I VERIFIED Exists:

### Backend Expectations (Verified from Code):

**1. Vitals Message Format** ([mqtt_service.py:342-440](hospital-backend/app/services/mqtt_service.py#L342-L440))
```json
{
  "deviceId": "fit-00001",
  "patientId": "PAT123",
  "timestamp": "2025-10-22T10:00:00.000Z",
  "mode": "ecg" or "eeg",
  "heartRate": 75,          // BPM (validated: 20-300)
  "skinTemperature": 36.8,  // °C (validated: 30.0-45.0)
  "oxygenSaturation": 98,   // % (validated: 50-100)
  "respiratoryRate": 16,    // breaths/min (validated: 4-60)
  "batteryLevel": 85,       // %
  "signalQuality": 0.95     // 0.0-1.0
}
```

**2. Waveform Stream Message Format** ([mqtt_service.py:231-269](hospital-backend/app/services/mqtt_service.py#L231-L269))
```json
{
  "deviceId": "fit-00001",
  "patientId": "PAT123",
  "timestamp": "2025-10-22T10:00:00.100Z",
  "mode": "ecg",
  "sequence": 12345,
  "samples": {
    "limb": {
      "leadI": {"baseline": 8388608, "deltas": [2, -1, 0, 3, ...]},    // 50 deltas
      "leadII": {"baseline": 8388610, "deltas": [1, 0, -2, 2, ...]},
      "leadIII": {"baseline": 8388605, "deltas": [0, -1, 1, -1, ...]}
    }
  }
}
```

**3. Backend Validation** ([mqtt_service.py:312-340](hospital-backend/app/services/mqtt_service.py#L312-L340))
- Heart Rate: 20-300 BPM (physiologically possible)
- SpO2: 50-100%
- Temperature: 30.0-45.0°C (expects Celsius, NOT Fahrenheit)
- Respiratory Rate: 4-60 breaths/min

### ESP32 Current State (Verified from Code):

**Lines 114-119** ([esp32_hospital_watch_complete.ino](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L114-L119)):
```cpp
float heartRate = 0;         // TODO: Read from MAX30102
float temperature = 0;       // TODO: Read from MLX90614
int oxygenSat = 0;           // TODO: Read from MAX30102
int batteryLevel = 100;      // TODO: Read from battery voltage ADC
int respiratoryRate = 0;     // TODO: Calculate from PPG waveform
float quality = 0;           // TODO: Read from sensor signal quality
```

**Current Status:** All vitals are 0 or static defaults. NO simulator exists.

**Line 1324-1363** ([esp32_hospital_watch_complete.ino](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1324-L1363)):
- `sendVitals()` function EXISTS and works
- Sends MQTT message to `hospital/devices/{deviceId}/vitals`
- Converts temperature from Fahrenheit to Celsius (line 1345)
- NO waveform generation code exists

---

## Physiological Simulator Design (Human-Mimicking)

### Part 1: Realistic Vitals Simulator

**Algorithm Choice:** Perlin noise + sine waves for natural variation

**Why NOT random values:**
- Random() creates unrealistic jumps (HR: 70 → 120 → 65)
- Human vitals have smooth, continuous variations
- Physiological systems have circadian rhythms and correlations

**Implementation Approach:**

1. **Base State Machine** (4 states):
   - Resting (default): HR 60-75, RR 12-16, Temp 36.5-37.0°C
   - Light Activity: HR 80-100, RR 16-20, Temp 37.0-37.5°C
   - Exercise: HR 110-150, RR 20-30, Temp 37.5-38.5°C
   - Sleep: HR 50-65, RR 10-14, Temp 36.1-36.8°C

2. **Smooth Transitions:**
   - Use exponential moving average (EMA) for state changes
   - Transition time: 30-60 seconds (realistic)
   - Example: Resting → Exercise takes 45 seconds to reach target HR

3. **Natural Variation (Perlin Noise):**
   - Heart Rate: ±2-5 BPM variation every 5-10 seconds
   - SpO2: ±1-2% variation (stays 95-100% for healthy)
   - Temperature: ±0.1-0.3°C variation over minutes
   - Respiratory Rate: ±1-2 breaths/min

4. **Physiological Correlations:**
   - HR ↑ → RR ↑ (respiratory sinus arrhythmia)
   - Activity ↑ → Temp ↑, SpO2 ↓ slightly
   - Time of day affects baseline (circadian rhythm)

5. **Pathological Modes (Optional):**
   - Fever: Temp 38.5-40.0°C
   - Hypoxia: SpO2 75-90%
   - Tachycardia: HR 120-180
   - Bradycardia: HR 35-50

**Memory Footprint:** ~500 bytes (state variables + history buffer)

---

### Part 2: ECG Waveform Simulator

**Algorithm Choice:** Synthetic PQRST complex generation

**Why NOT random:**
- ECG has specific morphology (P wave, QRS complex, T wave)
- Backend ECG analysis expects Pan-Tompkins detectable features
- Realistic ECG is critical for arrhythmia detection testing

**Implementation Approach:**

1. **PQRST Complex Template:**
   - P wave: 80ms, amplitude +0.15mV
   - PR segment: 80ms, baseline
   - QRS complex: 80-120ms, amplitude ±1.0mV
   - ST segment: 80ms, baseline
   - T wave: 160ms, amplitude +0.3mV
   - Total cycle: 600-1000ms (depends on HR)

2. **3-Lead ECG Generation:**
   - Lead I, Lead II, Lead III (minimum required)
   - Einthoven's triangle relationships:
     - Lead I + Lead III = Lead II
     - Lead III = Lead II - Lead I

3. **Delta Encoding:**
   - Store first sample as baseline (int32)
   - Subsequent samples as delta (int16)
   - Compression: ~50% bandwidth savings

4. **Arrhythmia Simulation (Optional):**
   - Normal Sinus Rhythm (NSR): 60-100 BPM, regular
   - Atrial Fibrillation (AFib): Irregular RR intervals
   - Premature Ventricular Contractions (PVCs): Occasional wide QRS
   - ST Elevation: Elevated ST segment (STEMI simulation)

**Sample Generation Rate:** 500 Hz (2ms per sample)
**Buffer Size:** 50 samples × 3 leads × 4 bytes = 600 bytes
**Transmission:** Every 100ms (50 samples)

---

### Part 3: EEG Waveform Simulator

**Algorithm Choice:** Frequency band synthesis (delta, theta, alpha, beta, gamma)

**Why NOT random:**
- EEG has characteristic frequency bands
- Backend EEG analysis uses FFT to detect seizures
- Realistic power spectrum is critical

**Implementation Approach:**

1. **8-Channel EEG Generation:**
   - Frontal: Fp1, Fp2, F3, F4
   - Central: C3, C4
   - Occipital: O1, O2

2. **Frequency Band Synthesis:**
   - Delta (0.5-4 Hz): Deep sleep, high amplitude
   - Theta (4-8 Hz): Drowsiness, meditation
   - Alpha (8-13 Hz): Relaxed, eyes closed
   - Beta (13-30 Hz): Alert, active thinking
   - Gamma (30-100 Hz): Cognitive processing

3. **Vigilance States:**
   - Awake (eyes open): High beta, low alpha
   - Awake (eyes closed): High alpha, moderate beta
   - Drowsy: High theta, decreasing alpha
   - Sleep: High delta

4. **Seizure Simulation (Optional):**
   - Spike-wave patterns: 3 Hz (absence seizure)
   - High amplitude spikes: >200 μV
   - Rhythmic discharges

**Sample Generation Rate:** 500 Hz
**Buffer Size:** 50 samples × 8 channels × 4 bytes = 1600 bytes
**Transmission:** Every 100ms

---

## ESP32 Code Structure

### New Global Variables (After Line 119):

```cpp
// ====================================
// PHYSIOLOGICAL SIMULATOR STATE
// ====================================
// Vitals simulator
enum ActivityState { RESTING, LIGHT_ACTIVITY, EXERCISE, SLEEP };
ActivityState currentState = RESTING;
unsigned long stateStartTime = 0;
unsigned long stateDuration = 300000;  // 5 minutes per state (demo mode)

// Smooth vital transitions
float targetHeartRate = 72.0;
float currentHeartRate = 72.0;
float targetRespRate = 14.0;
float currentRespRate = 14.0;
float targetTemp = 36.8;
float currentTemp = 36.8;
float targetSpO2 = 98.0;
float currentSpO2 = 98.0;

// Perlin noise state (for natural variation)
float noiseX = 0.0;
float noiseDelta = 0.05;

// Waveform streaming state
unsigned long lastWaveformStream = 0;
int waveformSequence = 0;
int32_t sampleBuffer[3][50];  // 3 leads × 50 samples
int sampleBufferIndex = 0;
bool streamingEnabled = false;

// ECG synthesis state
float ecgPhase = 0.0;  // Current phase in cardiac cycle (0.0-1.0)
float ecgCycleTime = 0.0;  // Time since last R-peak (ms)
```

### New Functions:

**1. updateSimulatedVitals()** - Called every 1 second
```cpp
void updateSimulatedVitals() {
  // State machine (demo mode - cycles through states)
  if (millis() - stateStartTime > stateDuration) {
    currentState = (ActivityState)((currentState + 1) % 4);
    stateStartTime = millis();
    updateTargetVitals();
  }

  // Smooth transitions (exponential moving average)
  float alpha = 0.1;  // Smoothing factor
  currentHeartRate += alpha * (targetHeartRate - currentHeartRate);
  currentRespRate += alpha * (targetRespRate - currentRespRate);
  currentTemp += alpha * (targetTemp - currentTemp);
  currentSpO2 += alpha * (targetSpO2 - currentSpO2);

  // Add natural variation (Perlin-like noise)
  noiseX += noiseDelta;
  float noise = sin(noiseX) * cos(noiseX * 0.7);  // Pseudo-Perlin

  heartRate = currentHeartRate + noise * 3.0;  // ±3 BPM variation
  respiratoryRate = (int)(currentRespRate + noise * 1.5);  // ±1-2 variation
  temperature = currentTemp + noise * 0.2;  // ±0.2°C variation
  oxygenSat = (int)(currentSpO2 + noise * 1.0);  // ±1% variation

  // Clamp to physiological ranges
  heartRate = constrain(heartRate, 40, 180);
  respiratoryRate = constrain(respiratoryRate, 8, 35);
  temperature = constrain(temperature, 95.0, 104.0);  // Fahrenheit (will convert)
  oxygenSat = constrain(oxygenSat, 88, 100);

  // Signal quality (varies with activity)
  quality = 85 + noise * 10;  // 75-95%
  quality = constrain(quality, 70, 100);

  // Battery drain simulation (1% per 10 minutes)
  if (millis() % 600000 < 1000) {
    batteryLevel = max(0, batteryLevel - 1);
  }
}
```

**2. updateTargetVitals()** - Sets targets based on state
```cpp
void updateTargetVitals() {
  switch (currentState) {
    case RESTING:
      targetHeartRate = 68.0 + random(-5, 5);
      targetRespRate = 14.0 + random(-2, 2);
      targetTemp = 97.5 + random(-5, 5) * 0.1;  // 97.0-98.0°F
      targetSpO2 = 98.0 + random(-1, 2);
      break;

    case LIGHT_ACTIVITY:
      targetHeartRate = 90.0 + random(-8, 8);
      targetRespRate = 18.0 + random(-2, 2);
      targetTemp = 98.2 + random(-3, 3) * 0.1;
      targetSpO2 = 97.0 + random(-1, 2);
      break;

    case EXERCISE:
      targetHeartRate = 130.0 + random(-15, 15);
      targetRespRate = 25.0 + random(-3, 3);
      targetTemp = 99.5 + random(-5, 5) * 0.1;
      targetSpO2 = 95.0 + random(-2, 3);
      break;

    case SLEEP:
      targetHeartRate = 58.0 + random(-5, 5);
      targetRespRate = 12.0 + random(-2, 2);
      targetTemp = 96.8 + random(-5, 5) * 0.1;
      targetSpO2 = 98.0 + random(-1, 2);
      break;
  }
}
```

**3. generateECGSample()** - Generates one ECG sample for 3 leads
```cpp
void generateECGSample(int lead, int32_t& sample) {
  // Calculate cardiac cycle timing (depends on HR)
  float cycleDuration = 60000.0 / heartRate;  // ms per beat
  float phase = ecgCycleTime / cycleDuration;  // 0.0-1.0

  // PQRST complex synthesis
  float amplitude = 0.0;

  if (phase < 0.08) {
    // P wave (0-80ms)
    float t = phase / 0.08;
    amplitude = 0.15 * sin(t * PI);
  }
  else if (phase < 0.16) {
    // PR segment (80-160ms) - isoelectric
    amplitude = 0.0;
  }
  else if (phase < 0.24) {
    // QRS complex (160-240ms)
    float t = (phase - 0.16) / 0.08;
    // Simplified QRS: Q-dip, R-spike, S-dip
    if (t < 0.3) amplitude = -0.2 * (t / 0.3);  // Q wave
    else if (t < 0.6) amplitude = 1.5 * ((t - 0.3) / 0.3);  // R wave
    else amplitude = -0.3 * ((t - 0.6) / 0.4);  // S wave
  }
  else if (phase < 0.32) {
    // ST segment (240-320ms) - isoelectric
    amplitude = 0.0;
  }
  else if (phase < 0.56) {
    // T wave (320-560ms)
    float t = (phase - 0.32) / 0.24;
    amplitude = 0.3 * sin(t * PI);
  }
  else {
    // Rest of cycle - isoelectric
    amplitude = 0.0;
  }

  // Apply lead-specific morphology
  float leadMultiplier = 1.0;
  if (lead == 0) leadMultiplier = 0.8;  // Lead I
  else if (lead == 1) leadMultiplier = 1.0;  // Lead II (reference)
  else if (lead == 2) leadMultiplier = 0.6;  // Lead III

  // Convert to ADC units (24-bit ADC, midpoint 8388608)
  // Amplitude in mV, ADC range ±1.0V
  sample = 8388608 + (int32_t)(amplitude * leadMultiplier * 100000);

  // Add small noise
  sample += random(-50, 50);

  // Update phase for next sample (500 Hz = 2ms per sample)
  ecgCycleTime += 2.0;
  if (ecgCycleTime >= cycleDuration) {
    ecgCycleTime = 0.0;  // New beat
  }
}
```

**4. sendWaveformStream()** - Transmits 100ms waveform packet
```cpp
void sendWaveformStream() {
  if (!mqttClient.connected() || !isAssigned) return;

  String topic = "hospital/devices/" + deviceId + "/stream";

  JsonDocument doc;
  doc["deviceId"] = deviceId;
  doc["patientId"] = assignedPatientId;
  doc["timestamp"] = getISO8601Timestamp();
  doc["mode"] = digitalRead(MODE_SELECT_PIN) == HIGH ? "ecg" : "eeg";
  doc["sequence"] = waveformSequence;

  // Delta encoding
  JsonObject samples = doc.createNestedObject("samples");
  JsonObject limb = samples.createNestedObject("limb");

  // Lead I
  JsonObject leadI = limb.createNestedObject("leadI");
  leadI["baseline"] = sampleBuffer[0][0];
  JsonArray deltasI = leadI.createNestedArray("deltas");
  for (int i = 1; i < 50; i++) {
    deltasI.add(sampleBuffer[0][i] - sampleBuffer[0][i-1]);
  }

  // Lead II
  JsonObject leadII = limb.createNestedObject("leadII");
  leadII["baseline"] = sampleBuffer[1][0];
  JsonArray deltasII = leadII.createNestedArray("deltas");
  for (int i = 1; i < 50; i++) {
    deltasII.add(sampleBuffer[1][i] - sampleBuffer[1][i-1]);
  }

  // Lead III
  JsonObject leadIII = limb.createNestedObject("leadIII");
  leadIII["baseline"] = sampleBuffer[2][0];
  JsonArray deltasIII = leadIII.createNestedArray("deltas");
  for (int i = 1; i < 50; i++) {
    deltasIII.add(sampleBuffer[2][i] - sampleBuffer[2][i-1]);
  }

  String payload;
  serializeJson(doc, payload);

  if (mqttClient.publish(topic.c_str(), payload.c_str())) {
    Serial.println("📊 Waveform stream sent (seq: " + String(waveformSequence) + ")");
  }
}
```

**5. loop() Integration:**
```cpp
void loop() {
  // ... existing code ...

  // Update vitals simulator every 1 second
  if (wifiConnected && isAssigned && millis() - lastVitals > 1000) {
    updateSimulatedVitals();
    sendVitals();
    lastVitals = millis();
  }

  // Continuous waveform sampling (500 Hz = 2ms)
  if (streamingEnabled && isAssigned && (millis() % 2) == 0) {
    // Generate samples for 3 leads
    for (int lead = 0; lead < 3; lead++) {
      generateECGSample(lead, sampleBuffer[lead][sampleBufferIndex]);
    }

    sampleBufferIndex++;

    // Buffer full? (50 samples = 100ms)
    if (sampleBufferIndex >= 50) {
      sendWaveformStream();
      sampleBufferIndex = 0;
      waveformSequence++;

      // Synchronize vitals every 10th waveform (1 second)
      if (waveformSequence % 10 == 0) {
        sendVitals();
      }
    }
  }

  delay(100);
}
```

---

## Memory Analysis

**Heap Usage:**
- State variables: ~200 bytes
- Sample buffer (3×50): 600 bytes
- JSON serialization buffer: ~1500 bytes (ArduinoJson)
- **Total:** ~2300 bytes

**ESP32 Available:** 520 KB SRAM + 4 MB PSRAM
**Impact:** <0.5% of SRAM - **Safe**

---

## Testing Plan

**Phase 1: Vitals Only** (No waveforms yet)
1. Verify vitals change smoothly (no jumps)
2. Verify state transitions work (Resting → Exercise)
3. Verify backend validation passes (20-300 BPM, etc.)
4. Verify frontend displays realistic values

**Phase 2: ECG Waveforms**
1. Verify 500 Hz sampling (2ms intervals)
2. Verify delta encoding works
3. Verify MQTT messages sent 10 times/sec
4. Verify backend ECG analysis detects QRS complexes
5. Verify frontend waveform display shows realistic ECG

**Phase 3: Integration**
1. Verify vitals synchronized with every 10th waveform
2. Verify no packet loss (sequence numbers)
3. Verify battery drain simulation
4. Load test: 10 devices streaming simultaneously

---

## Questions for User:

1. **State machine behavior:** Should activity states cycle automatically (demo mode) or stay in one state?
   - Option A: Auto-cycle every 5 minutes (for demos)
   - Option B: Stay in RESTING state (for stable testing)
   - Option C: MQTT command to change state (user-controlled)

2. **Waveform streaming:** Enable by default or require MQTT command?
   - Option A: Enable when patient assigned (automatic)
   - Option B: Require MQTT command `/devices/{id}/command` with `{"command": "startStreaming"}`

3. **Pathological modes:** Include abnormal vitals (fever, hypoxia, arrhythmias)?
   - Option A: Yes - add command to trigger (e.g., `{"command": "simulateFever"}`)
   - Option B: No - only normal healthy vitals

4. **EEG waveforms:** Implement EEG simulator or ECG only first?
   - Option A: ECG only (simpler, 3 leads)
   - Option B: Both ECG and EEG (8 channels total)

---

## Alternative Approaches Considered:

**1. Pre-recorded Real ECG Data:**
- **Pros:** 100% realistic, includes real arrhythmias
- **Cons:** Large storage (10 MB+ for 1 hour), inflexible, requires SPIFFS upload
- **Decision:** REJECTED - Synthetic is more flexible and memory-efficient

**2. External Python Simulator:**
- **Pros:** Easy to code, powerful libraries (scipy, numpy)
- **Cons:** Requires PC running, not standalone ESP32
- **Decision:** REJECTED - User wants ESP32-only solution

**3. Simple Sine Wave:**
- **Pros:** Minimal code, low memory
- **Cons:** Unrealistic, won't pass backend ECG analysis
- **Decision:** REJECTED - Needs realistic PQRST morphology

---

## Conformance to Guidelines:

✅ **camelCase:** All variables use camelCase (heartRate, currentState, etc.)
✅ **Backend-only medical logic:** Simulator only generates data, no analysis on ESP32
✅ **No quick fixes:** Proper physiological modeling, not random values
✅ **Modular code:** Separate functions for vitals, ECG, state machine
✅ **Senior tech lead thinking:** Considered alternatives, memory impact, testing plan

---

## Ready to Implement?

**Next Steps:**
1. User answers 4 questions above
2. Create implementation plan with exact code locations
3. Execute implementation
4. Test with backend

**Estimated Time:**
- Vitals simulator: 2 hours
- ECG waveform simulator: 3 hours
- Integration & testing: 2 hours
- **Total:** 7 hours (1 day)
