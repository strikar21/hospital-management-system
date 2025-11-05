# ADS1298 8-Channel ECG/EEG and Simulator - Complete Analysis

**Date:** 2025-11-03
**Your Questions Answered**

---

## Question 1: What leads is the ADS1298 reading?

### ✅ ADS1298 Hardware Capability

**The ADS1298 is an 8-channel simultaneous sampling ADC:**
- **8 differential input channels** (CH1-CH8)
- **Sample rate:** 500 Hz for ECG/EEG
- **Resolution:** 24-bit (±8.4 million counts)
- **Can read 8 leads/channels simultaneously**

### ✅ What We're Actually Reading (Based on Code)

#### ECG Mode (8 channels → 12-lead ECG):

**Direct Hardware Channels (8):**
- CH1 = **Lead I** (Lateral)
- CH2 = **Lead II** (Inferior - reference)
- CH3 = **V1** (Right precordial)
- CH4 = **V2** (Transitional)
- CH5 = **V3** (Transition zone)
- CH6 = **V4** (Left precordial - tallest)
- CH7 = **V5** (Lateral)
- CH8 = **V6** (Lateral)

**Derived/Calculated Leads (4):**
- **Lead III** = Lead II - Lead I (calculated in firmware)
- **aVR** = -(Lead I + Lead II) / 2
- **aVL** = Lead I - Lead II / 2
- **aVF** = Lead II - Lead I / 2

**Total: 12-lead ECG** from 8 hardware channels.

See: [esp32_hospital_watch_complete.ino:1938-1966](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1938-L1966)

```cpp
// Calculate lead III array (Lead III = II - I)
int32_t lead3Array[50];
for (int i = 0; i < 50; i++) {
  lead3Array[i] = waveformAccumulator[1][i] - waveformAccumulator[0][i];
}

// Calculate derived lead arrays
int32_t avrArray[50], avlArray[50], avfArray[50];
for (int i = 0; i < 50; i++) {
  int32_t ch0 = waveformAccumulator[0][i];
  int32_t ch1 = waveformAccumulator[1][i];
  avrArray[i] = -(ch0 + ch1) / 2;
  avlArray[i] = ch0 - ch1 / 2;
  avfArray[i] = ch1 - ch0 / 2;
}
```

#### EEG Mode (8 channels → 8 EEG electrodes):

**Direct Hardware Channels (8):**
- CH1 = **Fp1** (Frontal pole left)
- CH2 = **Fp2** (Frontal pole right)
- CH3 = **F3** (Frontal left)
- CH4 = **F4** (Frontal right)
- CH5 = **C3** (Central left)
- CH6 = **C4** (Central right)
- CH7 = **O1** (Occipital left)
- CH8 = **O2** (Occipital right)

**Total: 8-channel EEG** (standard 10-20 system placement).

See: [esp32_hospital_watch_complete.ino:1972-1992](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1972-L1992)

---

## Question 2: What is the watch inferring/calculating?

### Vitals (from PhysiologicalSimulator):
See: [esp32_hospital_watch_complete.ino:1884-1889](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1884-L1889)

```cpp
simulator.update();
heartRate = simulator.getHeartRate();           // BPM
temperature = simulator.getTemperature();       // Fahrenheit → converted to Celsius
oxygenSat = simulator.getOxygenSaturation();    // %
respiratoryRate = simulator.getRespiratoryRate(); // breaths/min
quality = simulator.getSignalQuality();         // 0.0-100.0
```

### Derived ECG Leads (calculated from hardware channels):
- Lead III = Lead II - Lead I
- aVR, aVL, aVF (calculated from limb leads)

### Device-Level Metrics:
- Battery health percentage
- Battery drain rate per hour
- Signal strength (WiFi RSSI)
- Connection stability (disconnect count)
- Sensor validity checks

---

## Question 3: What's being sent to backend/stream?

### 1. **Vitals Message** (every 1 second)
**Topic:** `hospital/devices/{deviceId}/vitals`

See: [esp32_hospital_watch_complete.ino:1828-1850](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1828-L1850)

```json
{
  "timestamp": "2025-11-03T10:30:45.123Z",
  "mode": "ecg",  // or "eeg"
  "deviceId": "ESP32-WATCH-001",
  "patientId": "PAT123",
  "heartRate": 75,
  "skinTemperature": 36.5,  // Celsius
  "oxygenSaturation": 98,
  "signalQuality": 0.92,
  "respiratoryRate": 14,
  "batteryLevel": 85
}
```

### 2. **Waveform Stream** (every 100ms - 10 packets/second)
**Topic:** `hospital/devices/{deviceId}/stream`

See: [esp32_hospital_watch_complete.ino:1916-1996](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1916-L1996)

#### ECG Mode:
```json
{
  "deviceId": "ESP32-WATCH-001",
  "patientId": "PAT123",
  "timestamp": "2025-11-03T10:30:45.123Z",
  "mode": "ecg",
  "sequence": 12345,
  "duration": 0.1,  // 100ms packet
  "sampleRate": 500,
  "ecgWaveform": {
    "limb": {
      "leadI": { "baseline": 8388608, "deltas": [120, -45, 200, ...] },
      "leadII": { "baseline": 8390000, "deltas": [150, -50, 250, ...] },
      "leadIII": { "baseline": 8387500, "deltas": [30, -5, 50, ...] }
    },
    "precordial": {
      "v1": { "baseline": 8388608, "deltas": [...] },
      "v2": { "baseline": 8388608, "deltas": [...] },
      "v3": { "baseline": 8388608, "deltas": [...] },
      "v4": { "baseline": 8388608, "deltas": [...] },
      "v5": { "baseline": 8388608, "deltas": [...] }
    },
    "derived": {
      "avr": { "baseline": 8388608, "deltas": [...] },
      "avl": { "baseline": 8388608, "deltas": [...] },
      "avf": { "baseline": 8388608, "deltas": [...] },
      "v6": { "baseline": 8388608, "deltas": [...] }
    }
  }
}
```

**Each packet contains:**
- **50 samples per lead** (100ms at 500 Hz)
- **12 leads total** (8 hardware + 4 derived)
- **Delta encoding:** baseline + deltas (51% bandwidth reduction)

#### EEG Mode:
```json
{
  "mode": "eeg",
  "eegWaveform": {
    "frontal": {
      "Fp1": { "baseline": 8388608, "deltas": [...] },
      "Fp2": { "baseline": 8388608, "deltas": [...] },
      "F3": { "baseline": 8388608, "deltas": [...] },
      "F4": { "baseline": 8388608, "deltas": [...] }
    },
    "central": {
      "C3": { "baseline": 8388608, "deltas": [...] },
      "C4": { "baseline": 8388608, "deltas": [...] }
    },
    "occipital": {
      "O1": { "baseline": 8388608, "deltas": [...] },
      "O2": { "baseline": 8388608, "deltas": [...] }
    }
  }
}
```

**Each packet contains:**
- **50 samples per channel** (100ms at 500 Hz)
- **8 channels total**
- **Delta encoding:** baseline + deltas

### 3. **Alerts** (as needed)
**Topic:** `hospital/devices/{deviceId}/alerts`

```json
{
  "alertType": "lowBatteryWarning",
  "severity": "medium",
  "message": "LOW BATTERY - 15%",
  "source": "Watch",
  "confidence": 0.95,
  "timestamp": "2025-11-03T10:30:45.123Z",
  "deviceId": "ESP32-WATCH-001",
  "patientId": "PAT123",
  "category": "device"
}
```

### 4. **Heartbeat** (every 30 seconds)
**Topic:** `hospital/devices/{deviceId}/heartbeat`

```json
{
  "deviceId": "ESP32-WATCH-001",
  "timestamp": "2025-11-03T10:30:45.123Z",
  "batteryLevel": 85,
  "signalStrength": -45,
  "firmwareVersion": "5.2.5"
}
```

---

## Question 4: We can read only 8 leads right?

### ✅ **Correct - But We Get 12 ECG Leads from 8 Hardware Channels**

**Hardware limitation: 8 simultaneous channels (ADS1298)**

**What we achieve:**
- **ECG mode:** 12-lead ECG (8 direct + 4 calculated)
- **EEG mode:** 8-channel EEG

**How it works:**
1. ADS1298 reads 8 physical channels simultaneously at 500 Hz
2. ESP32 calculates 4 derived leads using Einthoven's and Goldberger's equations:
   - Lead III = Lead II - Lead I
   - aVR = -(Lead I + Lead II) / 2
   - aVL = Lead I - Lead II / 2
   - aVF = Lead II - Lead I / 2
3. Result: Full 12-lead ECG from 8-channel hardware

**This is standard practice in ECG systems** - you don't need 12 physical ADC channels to get 12-lead ECG.

---

## Question 5: Why is the simulator wrong? Sending same data with minor changes instead of mimicking real body leads?

### 🚨 **YOU'RE ABSOLUTELY RIGHT - THE SIMULATOR IS WRONG!**

Let me analyze what's happening vs. what SHOULD happen:

### Current Simulator Behavior (WRONG):

See: [PhysiologicalSimulator.cpp:419-451](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L419-L451)

```cpp
void PhysiologicalSimulator::fillSampleBuffer(int32_t buffer[8][10]) {
  for (int i = 0; i < 10; i++) {
    if (currentMode == MODE_ECG) {
      // ✅ FIX: Calculate cardiac cycle phase for this sample
      float cycleDuration = 60000.0 / currentHeartRate;
      float phase = ecgCycleTime / cycleDuration;

      // Generate all 8 leads with same phase
      for (int lead = 0; lead < 8; lead++) {
        generateECGSampleWithPhase(lead, phase, buffer[lead][i]);
      }
```

**Problem 1: All leads use the SAME phase**
- Real ECG: Each lead shows a DIFFERENT view of the same electrical activity
- Current simulator: All leads show the same PQRST wave, just scaled by a multiplier

**Problem 2: Lead-specific morphology is ONLY amplitude scaling**

See: [PhysiologicalSimulator.cpp:382-417](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L382-L417)

```cpp
// Apply lead-specific morphology for 12-lead ECG (8 channels)
float leadMultiplier = 1.0;
switch (lead) {
    case 0:  // Lead I (LA-RA) - Lateral
        leadMultiplier = 0.75;  // ❌ WRONG - just amplitude scaling
        break;
    case 1:  // Lead II (LL-RA) - Inferior (reference, tallest)
        leadMultiplier = 1.0;   // ❌ WRONG - just amplitude scaling
        break;
    case 2:  // V1 - Right precordial (small R, deep S)
        leadMultiplier = 0.50;  // ❌ WRONG - should have NEGATIVE QRS!
        break;
    // ... etc
}
return amplitude * leadMultiplier;
```

### What SHOULD Happen (Real Human Body Physics):

#### **1. Lead I (LA-RA):**
- Horizontal vector
- Positive P, positive QRS, positive T
- Moderate amplitude
- **Current:** ✅ Correct overall, just scaled
- **Should be:** More specific morphology

#### **2. Lead II (LL-RA):**
- Inferior vector
- Tallest P and T waves
- Tallest R wave
- **Current:** ✅ Used as reference (1.0x)
- **Should be:** ✅ Mostly correct

#### **3. V1 (Right precordial):**
- Should show **rS pattern** (small r, DEEP S)
- QRS should be PREDOMINANTLY NEGATIVE
- **Current:** ❌ Just scaled positive waveform (0.5x)
- **Should be:** INVERTED QRS with small positive initial deflection

#### **4. V2 (Transitional):**
- Should show **RS pattern** (R starting to dominate S)
- Still somewhat negative overall
- **Current:** ❌ Just scaled positive waveform (0.65x)
- **Should be:** Transitional with balanced R and S

#### **5. V3 (Transition zone):**
- R wave = S wave
- **Current:** ❌ Just scaled positive waveform (0.85x)
- **Should be:** ✅ Actually close - balanced

#### **6. V4 (Left precordial):**
- Tallest R wave of all precordial leads
- Small S wave
- **Current:** ✅ Correct (1.25x)
- **Should be:** ✅ Correct

#### **7. V5 (Lateral):**
- Tall R, small S
- **Current:** ✅ Correct (1.15x)
- **Should be:** ✅ Mostly correct

#### **8. V6 (Lateral):**
- Similar to V5, slightly shorter
- **Current:** ✅ Correct (1.05x)
- **Should be:** ✅ Correct

### The Core Problem:

**The simulator doesn't simulate LEAD VECTORS properly:**

Real ECG leads measure voltage from different anatomical perspectives:
- **Limb leads:** Measure frontal plane electrical activity
- **Precordial leads V1-V6:** Measure horizontal plane, moving from right to left ventricle

**Each lead should show:**
1. Different PQRST wave SHAPES (not just amplitudes)
2. Some leads should have INVERTED complexes (V1, V2, aVR)
3. Different P-wave morphologies
4. Different T-wave polarities

**What the simulator does:**
- Generates ONE reference PQRST wave
- Multiplies it by a scalar for each lead
- **This produces anatomically IMPOSSIBLE ECGs**

---

## What Should Be Fixed:

### Option 1: Realistic Lead-Specific Waveform Generation (Proper Fix)

```cpp
float PhysiologicalSimulator::generatePQRST(float phase, int lead) {
    float amplitude = 0.0;

    // Generate base PQRST components
    float P = 0.0, Q = 0.0, R = 0.0, S = 0.0, T = 0.0;

    // ... calculate P, Q, R, S, T based on phase ...

    // Apply VECTOR-BASED lead morphology
    switch (lead) {
        case 0:  // Lead I
            amplitude = 0.75 * P + 0.8 * Q + 0.9 * R + 0.7 * S + 0.75 * T;
            break;
        case 1:  // Lead II (reference)
            amplitude = 1.0 * P + 1.0 * Q + 1.0 * R + 1.0 * S + 1.0 * T;
            break;
        case 2:  // V1 (rS pattern - predominantly negative)
            amplitude = 0.5 * P + 0.3 * R - 1.5 * S + 0.4 * T;  // Negative QRS
            break;
        case 3:  // V2 (RS pattern)
            amplitude = 0.6 * P + 0.6 * R - 0.8 * S + 0.5 * T;
            break;
        case 4:  // V3 (balanced)
            amplitude = 0.75 * P + 0.85 * R - 0.4 * S + 0.7 * T;
            break;
        case 5:  // V4 (tallest R)
            amplitude = 0.85 * P + 1.25 * R - 0.2 * S + 0.9 * T;
            break;
        case 6:  // V5
            amplitude = 0.8 * P + 1.15 * R - 0.15 * S + 0.85 * T;
            break;
        case 7:  // V6
            amplitude = 0.75 * P + 1.05 * R - 0.1 * S + 0.8 * T;
            break;
    }

    return amplitude;
}
```

### Option 2: Use Real ECG Libraries (Best Solution)

Use established ECG simulation libraries like:
- **ECGSYN** (McSharry et al., 2003)
- **MIT-BIH simulator**
- Proper multi-lead ECG synthesis with anatomically accurate vectors

---

## Summary:

| Question | Answer |
|----------|--------|
| **What leads?** | 8 hardware channels → 12 ECG leads (8 direct + 4 calculated) OR 8 EEG channels |
| **What's inferred?** | Derived leads (III, aVR, aVL, aVF), vitals, battery metrics |
| **What's sent?** | Vitals (1/sec), Waveforms (10/sec), Alerts (as needed), Heartbeat (30sec) |
| **Only 8 leads?** | Yes hardware, but we get 12 ECG leads through calculation |
| **Simulator wrong?** | **YES** - All leads show same waveform scaled, not anatomically correct vectors |

---

## Recommendation:

**Fix the simulator to generate lead-specific morphologies:**
1. V1-V2 should have PREDOMINANTLY NEGATIVE QRS (rS pattern)
2. V3 should be transitional (balanced R/S)
3. V4-V6 should have TALL R waves with small S
4. aVR should be COMPLETELY INVERTED
5. Each lead should have different P and T wave morphologies

**Would you like me to implement a proper multi-lead ECG simulator with anatomically correct vectors?**
