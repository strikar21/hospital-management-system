# Bandwidth Calculation Correction

**Date:** 2025-10-21
**Issue:** Does sending frequency affect total bandwidth?

---

## THE MATH

### Total Waveform Data Generated (Same Either Way)

**Per Channel:**
- Sampling rate: 250 Hz (250 samples per second)
- 8 channels (ECG/EEG)
- **Total samples per second:** 250 × 8 = 2,000 samples/second

**Per Sample:**
- 24-bit ADC = 3 bytes per sample
- With delta encoding: ~0.5-1 byte per sample (depending on compression)

**Raw data rate:**
- 2,000 samples/sec × 3 bytes = **6,000 bytes/sec**
- With delta compression: 2,000 samples/sec × 0.75 bytes = **1,500 bytes/sec**

---

## OPTION A: Send 10-Second Batches

**Per Message (Every 10 seconds):**
- 2,000 samples/sec × 10 sec = 20,000 samples
- With delta encoding: 20,000 × 0.75 bytes = **15,000 bytes (15 KB)**
- Frequency: Every 10 seconds

**Bandwidth per second:**
- 15 KB / 10 seconds = **1,500 bytes/sec**

**MQTT overhead:**
- 1 message every 10 seconds
- MQTT header: ~20 bytes per message
- Overhead: 20 bytes / 10 sec = **2 bytes/sec**

**Total: 1,502 bytes/sec**

---

## OPTION B: Send 1-Second Batches

**Per Message (Every 1 second):**
- 2,000 samples/sec × 1 sec = 2,000 samples
- With delta encoding: 2,000 × 0.75 bytes = **1,500 bytes (1.5 KB)**
- Frequency: Every 1 second

**Bandwidth per second:**
- 1.5 KB / 1 second = **1,500 bytes/sec**

**MQTT overhead:**
- 1 message every 1 second
- MQTT header: ~20 bytes per message
- Overhead: 20 bytes / 1 sec = **20 bytes/sec**

**Total: 1,520 bytes/sec**

---

## ACTUAL DIFFERENCE

### Waveform Data: **IDENTICAL**
- Option A: 1,500 bytes/sec
- Option B: 1,500 bytes/sec
- **Difference: 0 bytes/sec**

### MQTT Overhead: **Slightly Higher for 1-Second**
- Option A: 2 bytes/sec (1 message per 10 sec)
- Option B: 20 bytes/sec (10 messages per 10 sec)
- **Difference: 18 bytes/sec** (1.2% overhead)

---

## I WAS WRONG - HERE'S THE CORRECTION

**YOU ARE CORRECT!** The total bandwidth for waveform data is essentially the **SAME** whether you send:
- 10-second batches every 10 seconds, OR
- 1-second batches every 1 second

The only difference is tiny MQTT overhead (~1.2%).

---

## REVISED COMPARISON

### Option 1: Vitals (1 sec) + Waveforms (10 sec batches)

**Per Second:**
- Vitals: 300 bytes/sec
- Waveforms: 1,500 bytes/sec
- MQTT overhead: 2 bytes/sec
- **Total: 1,802 bytes/sec**

**Per Day:**
- 1,802 bytes/sec × 86,400 sec = **155.7 MB/day**

---

### Option 2: Vitals (1 sec) + Waveforms (1 sec batches)

**Per Second:**
- Vitals: 300 bytes/sec
- Waveforms: 1,500 bytes/sec
- MQTT overhead: 20 bytes/sec
- **Total: 1,820 bytes/sec**

**Per Day:**
- 1,820 bytes/sec × 86,400 sec = **157.2 MB/day**

---

## THE REAL DIFFERENCE

**Bandwidth:** Almost identical (1% difference)
- Option 1: 155.7 MB/day
- Option 2: 157.2 MB/day

**The bandwidth argument I made was WRONG.**

---

## WHAT IS ACTUALLY DIFFERENT?

### 1. **MQTT Broker Load (Message Count)**

**Option 1:**
- Vitals: 86,400 messages/day (1 per second)
- Waveforms: 8,640 messages/day (1 per 10 seconds)
- **Total: 95,040 messages/day per device**
- For 100 devices: **9.5 million messages/day**

**Option 2:**
- Combined: 86,400 messages/day (1 per second)
- **Total: 86,400 messages/day per device**
- For 100 devices: **8.6 million messages/day**

**Option 2 actually has FEWER messages!** (I was wrong again)

---

### 2. **Message Size (MQTT Broker Limits)**

**Option 1:**
- Vitals: 300 bytes (tiny)
- Waveforms: 15 KB (medium)
- **Largest message: 15 KB**

**Option 2:**
- Combined: 1.8 KB (small)
- **Largest message: 1.8 KB**

**Option 2 has smaller individual messages** - better for MQTT broker memory

---

### 3. **ESP32 Processing**

**Option 1: Send 10-second batches**
```cpp
// Buffer 10 seconds of data (20,000 samples)
int buffer[8][2500];  // 8 channels × 2500 samples = 80 KB RAM

void loop() {
  if (millis() - lastWaveform >= 10000) {
    deltaEncode(buffer);     // Encode 20,000 samples
    publishMQTT(encoded);     // Send 15 KB message
    clearBuffer();
  }
}
```

**RAM required:** 80 KB for circular buffer
**CPU burst:** Every 10 seconds (delta encode 20,000 samples)

**Option 2: Send 1-second batches**
```cpp
// Buffer 1 second of data (2,000 samples)
int buffer[8][250];  // 8 channels × 250 samples = 8 KB RAM

void loop() {
  if (millis() - lastWaveform >= 1000) {
    deltaEncode(buffer);     // Encode 2,000 samples
    publishMQTT(encoded);     // Send 1.5 KB message
    clearBuffer();
  }
}
```

**RAM required:** 8 KB for circular buffer (10x less!)
**CPU load:** Every 1 second (smoother, smaller bursts)

**Option 2 uses 10x less RAM!** (Important for ESP32 with limited memory)

---

### 4. **Backend Analysis Latency**

**Option 1:**
- Backend receives waveform data every 10 seconds
- Arrhythmia detection delay: **Up to 10 seconds**
- Example: V-fib starts at 10:00:01, detected at 10:00:10 (9 second delay)

**Option 2:**
- Backend receives waveform data every 1 second
- Arrhythmia detection delay: **Up to 1 second**
- Example: V-fib starts at 10:00:01.5, detected at 10:00:02 (0.5 second delay)

**Option 2 detects critical arrhythmias 9 seconds faster!**

---

### 5. **Battery Life**

**I need to reconsider this...**

**Option 1:**
- WiFi transmits 15 KB every 10 seconds
- WiFi stays on continuously for MQTT (persistent connection)
- Radio power: ~150-200 mA when active

**Option 2:**
- WiFi transmits 1.5 KB every 1 second
- WiFi stays on continuously for MQTT (persistent connection)
- Radio power: ~150-200 mA when active

**MQTT uses persistent TCP connection**, so WiFi radio is ON continuously either way.

The difference is only in **transmission time**:
- Option 1: 15 KB @ ~1 Mbps = 120 ms of transmission every 10 sec
- Option 2: 1.5 KB @ ~1 Mbps = 12 ms of transmission every 1 sec

**Both average to 12 ms per second of transmission time.**

**Battery life: ESSENTIALLY THE SAME!** (I was wrong about this too)

---

## CORRECTED COMPARISON TABLE

| Factor | Option 1 (10 sec batch) | Option 2 (1 sec batch) | Winner |
|--------|-------------------------|------------------------|---------|
| **Bandwidth** | 155.7 MB/day | 157.2 MB/day | TIE (~1% diff) |
| **Cost** | ₹1,400/month | ₹1,420/month | TIE (~1% diff) |
| **MQTT messages/day** | 95,040 | 86,400 | **Option 2** ✅ |
| **Max message size** | 15 KB | 1.8 KB | **Option 2** ✅ |
| **ESP32 RAM usage** | 80 KB buffer | 8 KB buffer | **Option 2** ✅ |
| **CPU load pattern** | Burst every 10s | Smooth every 1s | **Option 2** ✅ |
| **Analysis latency** | Up to 10 sec | Up to 1 sec | **Option 2** ✅ |
| **Battery life** | ~Same | ~Same | TIE |
| **Backend complexity** | Already built ✅ | Needs refactor | **Option 1** ✅ |

---

## REVISED RECOMMENDATION

### **Option 2 is Actually BETTER** (I was wrong!)

**Reasons Option 2 wins:**

1. ✅ **Same bandwidth** (~1% difference is negligible)
2. ✅ **Same cost** (~1% difference)
3. ✅ **Fewer MQTT messages** (9% fewer total messages)
4. ✅ **Smaller message size** (1.8 KB vs 15 KB - better for MQTT broker)
5. ✅ **10x less RAM on ESP32** (8 KB vs 80 KB - critical for ESP32!)
6. ✅ **Smoother CPU load** (no big bursts)
7. ✅ **9 seconds faster critical event detection** (life-saving!)
8. ✅ **Same battery life**

**Only downside:**
- ❌ Backend needs refactoring (but not a huge change)

---

## TECHNICAL DEEP DIVE: Why I Was Wrong

### My Mistake #1: Assumed sending less frequently = less data
**Wrong:** Total data = sampling rate × time, regardless of batching

### My Mistake #2: Assumed WiFi turns off between transmissions
**Wrong:** MQTT uses persistent TCP connection, WiFi stays on

### My Mistake #3: Assumed more messages = more overhead
**Partially wrong:** MQTT overhead is tiny (20 bytes) compared to payload (1500 bytes)

### My Mistake #4: Didn't consider ESP32 RAM constraints
**Big miss:** ESP32 has limited RAM, 80 KB buffer is significant

---

## FINAL ANSWER TO YOUR QUESTION

**You were right to question my analysis!**

**Sending 10-second data at once vs 1-second data per second:**
- **Uses the SAME total bandwidth** (just different batching)
- **Option 2 (1-second batches) is actually BETTER** because:
  - 10x less RAM on ESP32
  - 9 seconds faster critical event detection
  - Smaller MQTT messages (better for broker)
  - Fewer total messages (combined vitals+waveform)

**New Recommendation: Option 2 (Combined 1-second messages)**

Unless backend refactoring is a blocker, go with 1-second combined messages.

---

## IMPLEMENTATION COMPARISON (CORRECTED)

### Option 2: Combined Message Every 1 Second (RECOMMENDED)

**ESP32 Code:**
```cpp
// Only 8 KB RAM needed!
int waveformBuffer[8][250];  // 8 channels × 250 samples = 8 KB

void loop() {
  // Collect samples continuously at 250 Hz
  collectSample();

  // Every 1 second, send combined message
  if (millis() - lastMessage >= 1000) {
    sendCombinedData();  // Vitals + 1-second waveform
    lastMessage = millis();
  }
}

void sendCombinedData() {
  JsonDocument doc;

  // Add vitals (300 bytes)
  doc["heartRate"] = heartRate;
  doc["oxygenSaturation"] = oxygenSat;
  // ... other vitals

  // Add waveform (1200 bytes with delta encoding)
  doc["waveform"] = deltaEncode(waveformBuffer);

  // Total message: ~1.5-1.8 KB
  mqttClient.publish(topic, doc);
}
```

**Backend Refactoring Needed:**
- Change MQTT topic subscription to single topic
- Modify Pydantic model to accept combined message
- Split data into two TimescaleDB tables (vitals_realtime, waveform_snapshots)
- Update WebSocket broadcasting

**Estimated refactoring time:** 2-4 hours of work

**Benefit:** Real-time clinical monitoring with 1-second latency!
