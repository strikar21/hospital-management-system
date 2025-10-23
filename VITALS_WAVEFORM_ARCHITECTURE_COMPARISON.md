# Vitals + Waveform Architecture Comparison

**Date:** 2025-10-21
**Decision Required:** How should ESP32 send vitals and waveform data?

---

## OPTION 1: Separate Messages (Current Backend Design)

### Architecture
```
ESP32 sends TWO separate MQTT messages:

1. hospital/devices/{deviceId}/vitals
   - Frequency: Every 1 second
   - Size: ~300 bytes
   - Contains: HR, SpO2, temp, battery, etc.

2. hospital/devices/{deviceId}/waveform
   - Frequency: Every 10 seconds
   - Size: ~15-60 KB (with delta compression)
   - Contains: 8-channel ECG/EEG waveform (2500 samples per channel)
```

### Message Structure

**Vitals (1 second):**
```json
{
  "timestamp": "2025-10-21T10:00:00.000Z",
  "deviceId": "fit-00001",
  "patientId": "PAT0001",
  "mode": "ecg",
  "heartRate": 75,
  "oxygenSaturation": 98,
  "skinTemperature": 36.5,
  "respiratoryRate": 16,
  "batteryLevel": 85,
  "signalQuality": 0.95
}
```

**Waveform (10 seconds):**
```json
{
  "timestamp": "2025-10-21T10:00:00.000Z",
  "deviceId": "fit-00001",
  "patientId": "PAT0001",
  "mode": "ecg",
  "sampleRate": 250,
  "duration": 10,
  "ecgWaveform": {
    "limb": {
      "leadI": {"baseline": 512, "deltas": [/* 2500 samples */]},
      "leadII": {"baseline": 518, "deltas": [/* 2500 samples */]},
      "leadIII": {"baseline": 506, "deltas": [/* 2500 samples */]}
    },
    "precordial": {
      "v1": {"baseline": 520, "deltas": [/* 2500 samples */]},
      // ... 4 more channels
    }
  }
}
```

### Bandwidth Analysis (Per Device)

**Per Second:**
- Vitals: 300 bytes/sec
- Waveforms: 15 KB / 10 sec = 1.5 KB/sec
- **Total: 1.8 KB/sec**

**Per Day:**
- Vitals: 25.92 MB
- Waveforms: 129.6 MB
- **Total: 155.52 MB/day**

**100 Patients/Month:**
- **467 GB/month**

### Pros ✅

1. **Lower bandwidth** - Waveforms only every 10 seconds saves 83% bandwidth
2. **Better ESP32 performance** - Less CPU time spent on MQTT publish
3. **Battery efficient** - Fewer transmissions = longer battery life
4. **Less MQTT broker load** - 10x fewer large messages
5. **Standard medical practice** - Most ECG monitors send waveforms at lower frequency than vitals
6. **Backend already designed for this** - No code changes needed
7. **Easier to scale** - 100 patients = manageable load

### Cons ❌

1. **Delayed waveform analysis** - Backend sees full waveform every 10 sec, not every second
2. **Arrhythmia detection latency** - Up to 10 second delay to detect critical events
3. **Data synchronization** - Vitals and waveforms arrive separately (but timestamped)

---

## OPTION 2: Combined Message Every Second

### Architecture
```
ESP32 sends ONE combined MQTT message:

hospital/devices/{deviceId}/data
   - Frequency: Every 1 second
   - Size: ~4-8 KB per message
   - Contains: Vitals + 1-second waveform snapshot (250 samples per channel)
```

### Message Structure

**Combined Data (1 second):**
```json
{
  "timestamp": "2025-10-21T10:00:00.000Z",
  "deviceId": "fit-00001",
  "patientId": "PAT0001",
  "mode": "ecg",

  // VITALS (same as before)
  "heartRate": 75,
  "oxygenSaturation": 98,
  "skinTemperature": 36.5,
  "respiratoryRate": 16,
  "batteryLevel": 85,
  "signalQuality": 0.95,

  // WAVEFORM (1 second snapshot - 250 samples)
  "sampleRate": 250,
  "duration": 1,
  "ecgWaveform": {
    "limb": {
      "leadI": {"baseline": 512, "deltas": [/* 250 samples */]},
      "leadII": {"baseline": 518, "deltas": [/* 250 samples */]},
      "leadIII": {"baseline": 506, "deltas": [/* 250 samples */]}
    },
    "precordial": {
      "v1": {"baseline": 520, "deltas": [/* 250 samples */]},
      // ... 4 more channels
    }
  }
}
```

### Bandwidth Analysis (Per Device)

**Per Second:**
- Combined message: ~6 KB/sec (vitals + 1-second waveform)

**Per Day:**
- **518.4 MB/day**

**100 Patients/Month:**
- **1,555 GB/month** (1.5 TB)

### Pros ✅

1. **Real-time waveform analysis** - Backend sees every heartbeat immediately
2. **Faster arrhythmia detection** - 1 second latency instead of 10 seconds
3. **Perfect time synchronization** - Vitals and waveforms always aligned
4. **Simpler data model** - Only one message type to handle
5. **Better for critical care** - ICU patients need real-time monitoring
6. **No missed events** - Backend sees all waveform data, not 10% sampling

### Cons ❌

1. **3.3x higher bandwidth** - 518 MB/day vs 155 MB/day
2. **Higher MQTT broker load** - 10x more messages with 4x size = 40x load
3. **More ESP32 CPU usage** - Constant MQTT publishing
4. **Worse battery life** - 10x more transmissions drains battery faster
5. **Harder to scale** - 100 patients = 1.5 TB/month bandwidth
6. **Backend storage costs** - 3.3x more data to store in TimescaleDB
7. **MQTT message size limits** - Some brokers limit message size to 256 KB

---

## OPTION 3: Hybrid Approach (Best of Both?)

### Architecture
```
ESP32 sends TWO message types with intelligent frequency:

1. hospital/devices/{deviceId}/vitals
   - Frequency: Every 1 second
   - Size: ~300 bytes
   - Contains: Basic vitals only

2. hospital/devices/{deviceId}/waveform
   - Frequency: ADAPTIVE
     - Normal: Every 10 seconds
     - Abnormal detected: Every 1 second (for 30 seconds)
   - Size: Variable (1-10 second snapshots)
   - Contains: ECG/EEG waveform
```

### Adaptive Logic on ESP32

```cpp
void loop() {
  // Always send vitals every second
  if (millis() - lastVitals >= 1000) {
    sendVitals();
    lastVitals = millis();
  }

  // Adaptive waveform frequency
  int waveformInterval = 10000;  // Default: 10 seconds

  // If vitals are abnormal, increase waveform frequency
  if (heartRate < 50 || heartRate > 120 ||
      oxygenSaturation < 92 ||
      signalQuality < 0.7) {
    waveformInterval = 1000;  // Switch to 1 second
  }

  if (millis() - lastWaveform >= waveformInterval) {
    sendWaveform(waveformInterval / 1000);  // Send 1 or 10 second snapshot
    lastWaveform = millis();
  }
}
```

### Bandwidth Analysis (Per Device)

**Normal Conditions (95% of time):**
- Same as Option 1: 155 MB/day

**Abnormal Conditions (5% of time):**
- Switches to high-frequency: 518 MB/day during events

**Average:**
- **~173 MB/day** (11% increase over Option 1)

### Pros ✅

1. **Best battery life** - Low bandwidth 95% of time
2. **Fast critical response** - 1 second latency when needed
3. **Scalable** - Normal load same as Option 1
4. **Intelligent** - More data when it matters
5. **Backend-triggered** - Backend can request high-frequency mode via MQTT command

### Cons ❌

1. **More complex logic** - ESP32 needs abnormality detection (contradicts "no analysis on watch")
2. **Variable latency** - Sometimes 1 sec, sometimes 10 sec
3. **Requires backend commands** - Backend must tell ESP32 to switch modes

---

## RECOMMENDATION ANALYSIS

### For Your Hospital System:

**Key Requirements:**
- All clinical analysis on backend (not ESP32)
- ESP32 sends raw data only
- Device alerts only (battery, sensor disconnect)
- Real-time monitoring for critical patients

### Recommended: **OPTION 1 (Separate Messages, 10-Second Waveforms)**

**Why?**

1. **Scalability** - You mentioned this is for Indian hospitals with potentially 100+ patients
   - Option 1: 467 GB/month for 100 patients ✅ Manageable
   - Option 2: 1,555 GB/month for 100 patients ❌ Expensive

2. **Battery Life** - Watches need to run 24+ hours
   - Option 1: 10x fewer large transmissions ✅ Better battery
   - Option 2: Constant high-bandwidth ❌ Battery drain

3. **10 Seconds is Clinically Acceptable**
   - Most arrhythmias are not instant-death (V-fib exception)
   - Bradycardia, tachycardia, A-fib: 10 seconds detection is fine
   - Critical alerts (asystole) can be detected from vitals (HR=0)

4. **Backend Already Built for This**
   - Your TimescaleDB schema expects separate messages
   - MQTT service subscribes to both topics
   - No code changes needed ✅

5. **ESP32 Simplicity**
   - Two simple functions: `sendVitals()`, `sendWaveform()`
   - No complex logic needed
   - Aligns with "no analysis on watch" principle

### When Option 2 Would Be Better:

- **ICU/Emergency setting** - Every second matters
- **Single patient monitoring** - Bandwidth not an issue
- **Research application** - Need complete waveform data
- **Unlimited bandwidth/storage** - Cost not a concern

---

## IMPLEMENTATION COMPARISON

### Option 1 Implementation (Recommended)

**ESP32 Code:**
```cpp
void loop() {
  // Send vitals every 1 second
  if (millis() - lastVitals >= 1000) {
    sendVitals();  // ~300 bytes
    lastVitals = millis();
  }

  // Send waveform every 10 seconds
  if (millis() - lastWaveform >= 10000) {
    sendWaveform();  // ~15 KB (10 sec of data)
    lastWaveform = millis();
  }
}

void sendVitals() {
  // Read sensors
  // Publish to: hospital/devices/{deviceId}/vitals
}

void sendWaveform() {
  // Collect 2500 samples per channel (250 Hz * 10 sec)
  // Delta encode
  // Publish to: hospital/devices/{deviceId}/waveform
}
```

**Backend:** ✅ Already implemented, no changes needed

---

### Option 2 Implementation

**ESP32 Code:**
```cpp
void loop() {
  // Send combined data every 1 second
  if (millis() - lastData >= 1000) {
    sendCombinedData();  // ~6 KB
    lastData = millis();
  }
}

void sendCombinedData() {
  // Read sensors
  // Collect 250 samples per channel (250 Hz * 1 sec)
  // Delta encode
  // Combine vitals + waveform in one message
  // Publish to: hospital/devices/{deviceId}/data
}
```

**Backend:** ❌ Needs refactoring
- Change MQTT topic subscriptions
- Modify data models to combine vitals + waveform
- Update TimescaleDB insertion logic
- Update WebSocket broadcasting

---

## COST ANALYSIS (100 Patients, Indian Context)

### Network Bandwidth Costs

**Option 1:**
- 467 GB/month for 100 patients
- Indian cloud egress: ~₹2-3 per GB
- **Monthly cost: ₹934 - ₹1,401**

**Option 2:**
- 1,555 GB/month for 100 patients
- **Monthly cost: ₹3,110 - ₹4,665**
- **3.3x more expensive**

### TimescaleDB Storage Costs

**Option 1:**
- 467 GB/month (90-day retention)
- With compression: ~150 GB
- **Storage cost: ₹450 - ₹750/month**

**Option 2:**
- 1,555 GB/month (90-day retention)
- With compression: ~500 GB
- **Storage cost: ₹1,500 - ₹2,500/month**

### Total Monthly Cost (100 Patients)

| Cost | Option 1 | Option 2 |
|------|----------|----------|
| Bandwidth | ₹934 - ₹1,401 | ₹3,110 - ₹4,665 |
| Storage | ₹450 - ₹750 | ₹1,500 - ₹2,500 |
| **Total** | **₹1,384 - ₹2,151** | **₹4,610 - ₹7,165** |

**Option 1 is 3.3x cheaper to operate.**

---

## FINAL RECOMMENDATION

### **Choose OPTION 1: Separate Messages (Vitals 1 sec, Waveforms 10 sec)**

**Reasons:**
1. ✅ **3.3x lower cost** (₹1,400 vs ₹4,600/month)
2. ✅ **Better battery life** (10x fewer large transmissions)
3. ✅ **More scalable** (100+ patients)
4. ✅ **Backend already built for this**
5. ✅ **Clinically acceptable** (10 sec latency is fine for most arrhythmias)
6. ✅ **Standard practice** (most medical monitors use this approach)
7. ✅ **Simpler ESP32 code**

**Critical Events Still Fast:**
- Asystole: Detected from vitals (HR=0) within 1 second ✅
- Severe bradycardia: Detected from vitals (HR<40) within 1 second ✅
- Hypoxia: Detected from vitals (SpO2<90) within 1 second ✅
- V-fib: Detected from waveform within 10 seconds ⚠️ (acceptable for most cases)

**When you need real-time:** You can always add a backend MQTT command to temporarily request 1-second waveforms for specific patients (like Option 3 hybrid).

---

## ANSWER TO YOUR QUESTION

**"Which is better?"**

**For your hospital system: OPTION 1 (Separate messages)**

- Vitals every 1 second
- Waveforms every 10 seconds
- All analysis on backend
- Device alerts only on ESP32

This gives you the best balance of:
- Clinical efficacy ✅
- Cost efficiency ✅
- Battery life ✅
- Scalability ✅
- Simplicity ✅

You can always upgrade to 1-second waveforms later if you find you need it for ICU patients.
