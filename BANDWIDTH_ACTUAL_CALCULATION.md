# Bandwidth Actual Calculation - From First Principles

**Date:** 2025-10-21
**Starting from ZERO assumptions**

---

## GIVEN DATA

### Hardware Specifications
- **ADC:** ADS1298 (24-bit, 8 channels)
- **Sampling rate:** 250 Hz (250 samples per second)
- **Channels:** 8 (for ECG or EEG)
- **Bits per sample:** 24 bits = 3 bytes

### Basic Vitals (Separate from Waveform)
- Heart rate: 4 bytes (int)
- Respiratory rate: 4 bytes (int)
- Skin temperature: 4 bytes (float)
- Oxygen saturation: 4 bytes (int)
- Battery level: 4 bytes (int)
- Signal quality: 4 bytes (float)
- Device ID: ~20 bytes (string)
- Patient ID: ~36 bytes (UUID string)
- Timestamp: ~25 bytes (ISO 8601 string)
- Mode: ~5 bytes (string "ecg" or "eeg")
- JSON overhead: ~50 bytes (braces, quotes, commas, field names)

**Total vitals message size:** ~160 bytes (let's round to 200 bytes with full JSON formatting)

---

## RAW WAVEFORM DATA GENERATION

**Per second (continuous):**
- 8 channels × 250 samples/sec × 3 bytes/sample = **6,000 bytes/sec**

This is CONSTANT. The ESP32 is reading ADC samples at this rate continuously.

---

## SCENARIO 1: Send 10-Second Waveform Batches

### What ESP32 Does

**Vitals:**
- Send every 1 second
- Message size: 200 bytes
- **Vitals bandwidth: 200 bytes/sec**

**Waveform:**
- Collect samples for 10 seconds
- Buffer size: 8 channels × 250 Hz × 10 sec = 20,000 samples
- Raw size: 20,000 samples × 3 bytes = 60,000 bytes (60 KB)
- Delta compression: ~40% of original = 24,000 bytes (24 KB)
- JSON overhead: ~500 bytes
- Total message: 24,500 bytes
- Send every 10 seconds
- **Waveform bandwidth: 24,500 bytes / 10 sec = 2,450 bytes/sec**

**Total bandwidth per second:**
- Vitals: 200 bytes/sec
- Waveform: 2,450 bytes/sec
- **Total: 2,650 bytes/sec**

**Per day:**
- 2,650 bytes/sec × 86,400 sec/day = **229 MB/day**

**Per month (100 devices):**
- 229 MB × 30 days × 100 devices = **687 GB/month**

---

## SCENARIO 2: Send 1-Second Waveform Batches

### What ESP32 Does

**Combined message (vitals + waveform):**
- Send every 1 second

**Vitals portion:**
- Same as before: 200 bytes

**Waveform portion:**
- Collect samples for 1 second
- Buffer size: 8 channels × 250 Hz × 1 sec = 2,000 samples
- Raw size: 2,000 samples × 3 bytes = 6,000 bytes (6 KB)
- Delta compression: ~40% of original = 2,400 bytes (2.4 KB)
- JSON overhead: ~500 bytes

**Total message:**
- Vitals: 200 bytes
- Waveform: 2,400 bytes
- JSON overhead: 500 bytes
- **Total: 3,100 bytes**

**Total bandwidth per second:**
- **3,100 bytes/sec**

**Per day:**
- 3,100 bytes/sec × 86,400 sec/day = **268 MB/day**

**Per month (100 devices):**
- 268 MB × 30 days × 100 devices = **804 GB/month**

---

## WAIT... THESE ARE DIFFERENT!

**Scenario 1:** 229 MB/day
**Scenario 2:** 268 MB/day

**Difference:** 39 MB/day (17% more)

## WHY THE DIFFERENCE?

### Delta Encoding Efficiency Changes with Batch Size

**Delta encoding works better with MORE data:**

**10-second batch:**
- 20,000 samples to compress
- Baseline overhead: 24 bits (3 bytes) × 8 channels = 24 bytes
- Delta overhead per sample: ~0.96 bytes average
- Total: 24 + (20,000 × 0.96) = 19,224 bytes
- Compression ratio: 19,224 / 60,000 = 32% (better!)

**1-second batch:**
- 2,000 samples to compress
- Baseline overhead: 24 bits × 8 channels = 24 bytes
- Delta overhead per sample: ~0.96 bytes average
- Total: 24 + (2,000 × 0.96) = 1,944 bytes
- Compression ratio: 1,944 / 6,000 = 32% (same ratio)

Wait, that's the same ratio...

---

## LET ME RECALCULATE DELTA ENCODING PROPERLY

### How Delta Encoding Actually Works

**Original values (example channel):**
```
[8388608, 8388610, 8388609, 8388609, 8388612, ...]
```

**Delta encoded:**
```
{
  "baseline": 8388608,
  "deltas": [2, -1, 0, 3, ...]
}
```

**Baseline:** 24 bits = 3 bytes (ONE TIME per channel)
**Deltas:** Most deltas are small (-10 to +10), can be encoded in 1 byte each

### 10-Second Batch (per channel)

- Baseline: 3 bytes × 1 = 3 bytes
- Deltas: 2,500 deltas × 1 byte = 2,500 bytes
- **Total per channel: 2,503 bytes**
- **8 channels: 20,024 bytes**
- JSON overhead: ~500 bytes
- **Total message: 20,524 bytes**

### 1-Second Batch (per channel)

- Baseline: 3 bytes × 1 = 3 bytes
- Deltas: 250 deltas × 1 byte = 250 bytes
- **Total per channel: 253 bytes**
- **8 channels: 2,024 bytes**
- JSON overhead: ~500 bytes
- **Total message: 2,524 bytes**

---

## RECALCULATED WITH CORRECT DELTA ENCODING

### SCENARIO 1: 10-Second Batches

**Per second bandwidth:**
- Vitals: 200 bytes/sec
- Waveform: 20,524 bytes / 10 sec = 2,052 bytes/sec
- **Total: 2,252 bytes/sec**

**Per day:**
- 2,252 × 86,400 = **195 MB/day**

**Per month (100 devices):**
- 195 × 30 × 100 = **585 GB/month**

---

### SCENARIO 2: 1-Second Batches

**Per second bandwidth:**
- Combined message: 200 (vitals) + 2,024 (waveform) + 500 (JSON) = 2,724 bytes
- **Total: 2,724 bytes/sec**

**Per day:**
- 2,724 × 86,400 = **235 MB/day**

**Per month (100 devices):**
- 235 × 30 × 100 = **705 GB/month**

---

## ACTUAL DIFFERENCE

| Metric | 10-Sec Batches | 1-Sec Batches | Difference |
|--------|----------------|---------------|------------|
| **Bytes/sec** | 2,252 | 2,724 | +21% |
| **MB/day** | 195 | 235 | +21% |
| **GB/month (100)** | 585 | 705 | +21% |

**1-second batches use 21% MORE bandwidth**

---

## WHY THE 21% DIFFERENCE?

### JSON Overhead

**10-second batches:**
- Vitals message: 200 bytes (every 1 sec) → 200 bytes/sec
- Waveform message: 500 bytes overhead (every 10 sec) → 50 bytes/sec
- **Total JSON overhead: 250 bytes/sec**

**1-second batches:**
- Combined message: 500 bytes overhead (every 1 sec) → 500 bytes/sec
- **Total JSON overhead: 500 bytes/sec**

**Difference: 250 bytes/sec = 21.6 MB/day**

That's exactly the 21% difference!

---

## CORRECTED COMPARISON

| Factor | 10-Sec Batches | 1-Sec Batches | Winner |
|--------|----------------|---------------|---------|
| **Bandwidth** | 195 MB/day | 235 MB/day | **10-Sec** ✅ |
| **Cost (100 patients/month)** | ₹1,755 | ₹2,115 | **10-Sec** ✅ |
| **ESP32 RAM** | 80 KB buffer | 8 KB buffer | **1-Sec** ✅ |
| **CPU pattern** | Burst every 10s | Smooth every 1s | **1-Sec** ✅ |
| **Analysis latency** | Up to 10 sec | Up to 1 sec | **1-Sec** ✅ |
| **MQTT messages** | 95,040/day | 86,400/day | **1-Sec** ✅ |
| **Max message size** | 20.5 KB | 2.7 KB | **1-Sec** ✅ |
| **Backend work** | Already done ✅ | Needs refactor | **10-Sec** ✅ |

---

## FINAL ACTUAL ANSWER

**10-second batches:**
- 21% less bandwidth
- 21% cheaper
- Backend already built for it
- BUT: 10x more RAM, slower detection, larger messages

**1-second batches:**
- 21% more bandwidth (20 MB/day more per device)
- 21% more cost (₹360/month more for 100 devices)
- BUT: 10x less RAM, 9 sec faster detection, smoother CPU

---

## WHICH IS BETTER?

**For 100 patients:**
- Extra cost for 1-second: ₹360/month (~₹3.60 per patient/month)
- Benefit: Detect V-fib 9 seconds faster
- Benefit: Use 10x less RAM on ESP32

**Is ₹3.60/patient/month worth 9 seconds faster critical event detection?**

For a hospital system: **YES**

**Recommendation: 1-second batches**

The 21% extra bandwidth is a reasonable tradeoff for:
- Real-time monitoring
- ESP32 RAM constraints (8 KB vs 80 KB is critical)
- Faster critical event detection

But if budget is tight: 10-second batches are acceptable clinically.
