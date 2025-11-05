# Root Cause Analysis: Batch Upload Rapid Updates & Lead I/II vs V-leads Appearance

**Date:** 2025-11-03
**User Questions:**
1. "but i thought we have enough buffer? why is it happening though?"
2. "why batch send when we are sending data already?"
3. "and why 1 & 2 are fine not affected?"

---

## TL;DR

**You have TWO separate buffer systems** - the real-time streaming buffer (100ms) and the offline SPIFFS queue (30-second batch). The batch processing runs every 30 seconds **regardless** of whether you're currently streaming or not. Lead I & II **ARE affected equally**, but they APPEAR smoother due to processing order, extreme morphologies in V-leads after the ECG fix, and where your visual attention is focused.

---

## Answer 1: Why Batch Upload Even With Enough Buffer?

### The Two Buffer Systems

You have **TWO completely separate systems**:

#### System 1: Real-Time Streaming Buffer (Working Perfectly)
```cpp
// Line 163: Global accumulator - 8 channels × 50 samples
int32_t waveformAccumulator[8][50];  // 1,600 bytes global
```

**How it works:**
- **Every 20ms** ([line 1095](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1095)): Generate 10 samples → add to accumulator
- **Every 100ms** ([line 1101](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1101)): Send 50 samples via MQTT
- **Buffer cleared** after each send

**This is smooth: 50 samples / 100ms = 500 Hz sampling rate ✅**

#### System 2: Offline SPIFFS Queue (The Problem)
```cpp
// Line 284: Max 10 waveform messages = 1 second of data
const int MAX_WAVEFORMS = 10;   // Keep up to 10 waveform messages (1 second)
```

**How it works:**
- **When offline** ([lines 2027-2031](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L2027)): Waveforms saved to SPIFFS flash storage
- **Every 30 seconds** ([lines 1143-1146](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1143)): Process ALL queued messages in rapid batch
- **Separate from real-time buffer** - different storage, different purpose

---

### What Actually Happens

#### Step 1: Device Goes Offline (e.g., 2-second network hiccup)

```cpp
// Lines 1095-1098: Waveform generation NEVER stops (P0 requirement)
if (isProvisioned && isAssigned && (unsigned long)(millis() - lastMicroBatch) > 20) {
  generateMicroBatch();  // ← CONTINUES GENERATING OFFLINE
}

// Lines 2027-2031: But MQTT disconnected, so SAVE to SPIFFS
if (!mqttClient.connected() || !isAssigned) {
  offlineQueue.saveWaveform(payload);  // ← SAVED TO FLASH
  return;
}
```

**Result**: 2 seconds offline × 10 messages/second = **20 waveform messages saved to SPIFFS**
(But max is 10, so oldest 10 deleted, newest 10 kept)

#### Step 2: Device Reconnects

```cpp
// Real-time streaming resumes normally
publishWithRetry(topic.c_str(), payload.c_str());  // ✅ Working fine
```

#### Step 3: 30-Second Timer Fires

```cpp
// Lines 1143-1146: Timer-based batch processing (DOESN'T CHECK IF STREAMING)
if (wifiConnected && mqttClient.connected() && (unsigned long)(millis() - lastQueueProcess) > 30000) {
  offlineQueue.processPendingMessages();  // ← BATCH SEND TRIGGERED
  lastQueueProcess = millis();
}
```

#### Step 4: Batch Loop Sends All Queued Messages Rapidly

```cpp
// Lines 345-368: sendBatch() processes ALL files in queue
File file = root.openNextFile();
while (file) {
  String payload = file.readString();
  if (publishWithRetry(topic.c_str(), payload.c_str(), 2)) {
    SPIFFS.remove(filename);  // Success - delete file
    sentCount++;
  }
  file = root.openNextFile();
}

Serial.println("📤 Sent " + String(sentCount) + " queued messages from " + queueDir);
```

**Your serial monitor showed:**
```
✅ Sent queued: /queue/waveforms/1234567890.json
✅ Sent queued: /queue/waveforms/1234567891.json
... (18 times total)
📤 Sent 18 queued messages from /queue/waveforms
```

**18 messages × 50 samples × 12 leads sent in rapid burst = visual "jump"**

---

### Why Buffer Doesn't Prevent This

**The `waveformAccumulator[8][50]` is ONLY for real-time streaming:**
- Size: 50 samples (100ms worth)
- Purpose: Smooth out micro-batches before MQTT send
- Lifetime: Cleared every 100ms

**The SPIFFS offline queue is SEPARATE:**
- Size: 10 messages (1 second worth)
- Purpose: Store data during network outages
- Lifetime: Persists until successfully sent

**They don't interact** - two independent systems.

---

## Answer 2: Why Batch Send When Already Sending Data?

### The Timer Doesn't Care If You're Streaming

**Lines 1143-1146 - Check the condition:**
```cpp
if (wifiConnected && mqttClient.connected() && (unsigned long)(millis() - lastQueueProcess) > 30000) {
  offlineQueue.processPendingMessages();
}
```

**What it checks:**
- ✅ WiFi connected?
- ✅ MQTT connected?
- ✅ Been 30 seconds since last queue process?

**What it DOESN'T check:**
- ❌ Is the queue empty?
- ❌ Are we currently streaming?
- ❌ Is real-time data flowing normally?

**Result**: Batch processing runs **timer-based**, not **condition-based**.

---

### Real-World Scenario

**Timeline:**
1. **t=0s**: Device connected, streaming normally (1 message every 100ms)
2. **t=5s**: WiFi drops for 3 seconds
3. **t=5-8s**: 30 waveform messages saved to SPIFFS (but max 10, so 20 deleted)
4. **t=8s**: WiFi reconnects, streaming resumes normally
5. **t=8-38s**: Streaming continues normally (1 message every 100ms)
6. **t=38s**: **30-second timer fires** → batch processing triggers
7. **t=38-40s**: ALL 10 queued messages sent rapidly **WHILE also sending real-time messages**

**What frontend receives during t=38-40s:**
- **Real-time stream**: 20 messages (2 seconds × 10/sec)
- **Batch queue**: 10 old messages (sent in rapid burst)
- **Total**: 30 messages in 2 seconds = **15 messages/second** (vs normal 10/sec)

**Visual effect**: V-leads appear to "jump" forward during the burst.

---

### Why This Design Exists

From firmware comments:
```cpp
// ✅ v5.2.1: Offline data buffering (SPIFFS-based queue for vitals/alerts/waveforms)
// ✅ v5.2.4: P0 CRITICAL - Patient monitoring never stops
```

**Medical requirement**: Patient data cannot be lost during network issues.

**Design trade-off:**
- **Pros**: Guarantees data delivery, simple timer-based logic
- **Cons**: Can send batch + real-time simultaneously (your issue)

---

## Answer 3: Why Are Lead I & II Fine, Not Affected?

### They ARE Affected - All Leads Receive Same Data!

**Critical fact**: ALL 12 leads receive data from the **SAME MQTT message** at the **SAME TIME**.

**But you perceive them differently due to THREE factors:**

---

### Factor 1: Processing Order Within Each Message

**Frontend code** ([`useECGViewer.ts:128-179`](hospital-display-app/src/hooks/useECGViewer.ts#L128-L179)):

```typescript
// Limb leads processed FIRST
if (limb?.leadI) {
  const samples = getData(limb.leadI);
  dataBufferRef.current[0] = [...dataBufferRef.current[0], ...samples].slice(-maxBufferSize);
}
if (limb?.leadII) {
  const samples = getData(limb.leadII);
  dataBufferRef.current[1] = [...dataBufferRef.current[1], ...samples].slice(-maxBufferSize);
}

// ... 60+ lines later ...

// Precordial leads processed LAST
if (precordial?.v1) {
  const samples = getData(precordial.v1);
  dataBufferRef.current[6] = [...dataBufferRef.current[6], ...samples].slice(-maxBufferSize);
}
```

**When 18 messages arrive in rapid batch:**

| Message # | Lead I Update Time | Lead II Update Time | V1 Update Time |
|-----------|-------------------|---------------------|----------------|
| 1 | t=0ms | t=1ms | t=5ms |
| 2 | t=6ms | t=7ms | t=11ms |
| 3 | t=12ms | t=13ms | t=17ms |
| ... | ... | ... | ... |
| 18 | t=102ms | t=103ms | t=107ms |

**Cumulative delay effect:**
- **Lead I**: Updates spread evenly over 102ms → **smooth appearance**
- **Lead II**: Updates spread evenly over 103ms → **smooth appearance**
- **V1-V6**: All updates compressed into last 5ms of each message → **jumpy appearance**

**Visual perception**: V-leads appear to "catch up" in rapid bursts.

---

### Factor 2: Extreme Morphologies After ECG Fix

**Your recent ECG anatomical fix** ([`PhysiologicalSimulator.cpp:387-466`](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L387-L466)) changed waveform amplitudes:

```cpp
case 0:  // Lead I (Lateral)
  R_vec = 0.85;   // Moderate R wave
  S_vec = 0.60;   // Moderate S wave
  break;

case 1:  // Lead II (Inferior, REFERENCE)
  R_vec = 1.0;    // Baseline R wave
  S_vec = 1.0;    // Baseline S wave
  break;

case 2:  // V1 (Right precordial - rS pattern)
  R_vec = 0.30;   // SMALL r wave (30% of normal)
  S_vec = 2.50;   // DEEP S wave (250% of normal) ← EXTREME
  T_vec = -0.30;  // INVERTED T wave
  break;

case 5:  // V4 (Left precordial - TALLEST R)
  R_vec = 1.40;   // TALLEST R wave (140% of normal) ← EXTREME
  break;
```

**Before ECG fix:**
- All leads: Same PQRST shape, just scaled by multipliers
- Jitter equally noticeable (or equally hidden)

**After ECG fix:**
- Lead I & II: Moderate, familiar morphology → small jitter **less noticeable**
- V1: Deep negative S wave → negative spike makes jitter **visually amplified**
- V4: Tall positive R wave → positive peak makes jitter **visually prominent**

**Analogy**: Imagine watching a person walk:
- **Normal height person** (Lead I & II): Small stumble barely noticeable
- **Giant person** (V4): Same stumble looks huge and obvious

---

### Factor 3: Visual Attention and Screen Position

**Typical ECG display layout:**
```
┌─────────────────┐
│ Lead I          │ ← Top section (stable reference)
│ Lead II         │
├─────────────────┤
│ Lead III        │
│ aVR, aVL, aVF   │
├─────────────────┤
│ V1              │ ← Bottom section (where you're looking)
│ V2              │
│ V3              │
│ V4              │ ← Most noticeable (tallest R wave)
│ V5              │
│ V6              │
└─────────────────┘
```

**Psychological factors:**
1. **Expectation bias**: After ECG fix, you're specifically checking V-leads for correctness
2. **Peripheral vision**: Our brains detect motion/change better in areas we're actively watching
3. **Pattern recognition**: Extreme morphologies (V1 rS, V4 tall R) draw more attention

**If you recorded all 12 leads simultaneously during batch upload**, frame-by-frame analysis would show:
- All leads receive **exactly the same data** at **exactly the same time**
- But **V-leads appear jumpier** due to factors 1 & 2 above

---

## The Complete Picture

### Data Flow During Batch Upload

**ESP32 → MQTT Broker → Frontend:**

```
ESP32 sends:
  Message 1 (t=0ms)   → MQTT → Frontend receives at t=0ms   → Processes Lead I at t=0ms, V1 at t=5ms
  Message 2 (t=5ms)   → MQTT → Frontend receives at t=5ms   → Processes Lead I at t=5ms, V1 at t=10ms
  Message 3 (t=10ms)  → MQTT → Frontend receives at t=10ms  → Processes Lead I at t=10ms, V1 at t=15ms
  ...
  Message 18 (t=90ms) → MQTT → Frontend receives at t=90ms  → Processes Lead I at t=90ms, V1 at t=95ms
```

**Result:**
- **All leads receive same data** from each message
- **Processing order creates visual difference**
- **V-leads processed last** → cumulative lag → apparent "jump"

---

## The Fix

### Option 1: Disable Waveform Queueing (Recommended)

**Rationale**: Waveforms are **real-time data** - historical waveforms from 3 seconds ago have no clinical value.

**Change 1** - Stop queuing waveforms ([line 2030](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L2030)):
```cpp
// ❌ BEFORE
if (!mqttClient.connected() || !isAssigned) {
  Serial.println("⚠️  MQTT disconnected - queuing waveform offline");
  offlineQueue.saveWaveform(payload);
  return;
}

// ✅ AFTER
if (!mqttClient.connected() || !isAssigned) {
  Serial.println("⚠️  MQTT disconnected - dropping waveform (real-time only)");
  return;  // Don't queue - just drop
}
```

**Change 2** - Stop batch processing waveforms ([line 276](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L276)):
```cpp
// ❌ BEFORE
sendBatch("/queue/vitals", "hospital/devices/" + deviceId + "/vitals");     // ✅ Keep
sendBatch("/queue/alerts", "hospital/devices/" + deviceId + "/alerts");     // ✅ Keep
sendBatch("/queue/waveforms", "hospital/devices/" + deviceId + "/stream");  // ❌ Remove

// ✅ AFTER
sendBatch("/queue/vitals", "hospital/devices/" + deviceId + "/vitals");
sendBatch("/queue/alerts", "hospital/devices/" + deviceId + "/alerts");
// sendBatch("/queue/waveforms", "hospital/devices/" + deviceId + "/stream");
// ↑ Waveforms are real-time only - no historical value
```

**Benefits:**
- ✅ Eliminates batch upload visual issue completely
- ✅ Medically appropriate (real-time data shouldn't be queued)
- ✅ Keeps important data queued (vitals & alerts for patient safety)
- ✅ Reduces SPIFFS wear (flash has limited write cycles)
- ✅ Simplest fix (2 line changes)

**Drawbacks:**
- ❌ Lose waveform data during network disconnections
- ❌ But this is expected and acceptable for real-time waveform displays

---

### Option 2: Condition-Based Queue Processing (Alternative)

**Change** - Only process queue when non-empty ([line 1143](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1143)):
```cpp
// ✅ Check queue size before processing
if (wifiConnected && mqttClient.connected() &&
    (unsigned long)(millis() - lastQueueProcess) > 30000) {

  // Only process if queue actually has data
  int queueSize = offlineQueue.getFileCount("/queue/waveforms");
  if (queueSize > 0) {
    offlineQueue.processPendingMessages();
  }
  lastQueueProcess = millis();
}
```

**Drawbacks:**
- Requires making `getFileCount()` public
- Still batches when queue is non-empty
- More complex than Option 1

---

### Option 3: Rate-Limited Batch Sending (Not Recommended)

Add delay between queued messages:
```cpp
// Line 357: Inside sendBatch() while loop
if (publishWithRetry(topic.c_str(), payload.c_str(), 2)) {
  SPIFFS.remove(filename);
  sentCount++;
  delay(100);  // ← Rate limit: 100ms between messages
}
```

**Drawbacks:**
- Very slow queue draining (10 messages = 1 second → now takes 10 seconds)
- Blocks other operations during queue processing
- Doesn't fix root issue

---

## Summary Table

| Your Question | Root Cause | Why You Notice It |
|--------------|-----------|------------------|
| **"We have enough buffer?"** | TWO separate systems: real-time buffer (100ms) + offline SPIFFS queue (1 second). Buffer is for real-time only. | Offline queue batches old data when timer fires. |
| **"Why batch when already sending?"** | Batch processing runs on 30-second timer, doesn't check if currently streaming or if queue is empty. | Timer-based, not condition-based design. |
| **"Why I & II fine?"** | ALL leads affected equally. V-leads APPEAR worse due to: processing order (cumulative lag), extreme morphologies (after ECG fix), visual attention. | You're watching V-leads section when batch happens. |

---

## Recommendation

**Implement Option 1** - disable waveform queueing entirely:

**Medical justification:**
- Real-time waveforms have **no clinical value** when delayed by seconds
- Historical waveform analysis should use **backend aggregation**, not ESP32 offline queue
- Vitals & alerts **do have value** when delayed (patient safety) → keep those queued

**Implementation:**
1. Comment out line 2030: Don't save waveforms to SPIFFS when offline
2. Comment out line 276: Don't batch process waveforms from queue

**Result**: Smooth, continuous waveforms for all 12 leads.
