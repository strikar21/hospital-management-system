# Batch Sending and Message ID Analysis

**Date:** 2025-11-03
**Questions:**
1. Do waveform/vitals messages have any ID for tracking?
2. What if batch send is sending data even when NOT offline right now?

---

## Answer 1: Do Messages Have IDs?

### Waveforms: ✅ YES - `sequence` Counter
**File:** `esp32_hospital_watch_complete.ino` Line 1951

```cpp
doc["sequence"] = waveformSequenceCounter++;
```

**Properties:**
- **Global counter**: `waveformSequenceCounter` starts at 0, increments forever
- **Never resets**: Counter persists for entire watch uptime
- **Tracks order**: Frontend can detect missed/duplicate messages
- **Logged every 10th message**: `if (waveformData.sequence && waveformData.sequence % 10 === 0)`

**Example:**
```json
{
  "sequence": 150,
  "duration": 0.1,
  "sampleRate": 500,
  "ecgWaveform": { ... }
}
```

---

### Vitals: ❌ NO - Only Timestamp
**File:** `esp32_hospital_watch_complete.ino` Line 1831

```cpp
doc["timestamp"] = getISO8601Timestamp();
```

**No sequence counter for vitals** - only ISO 8601 timestamp

---

## Answer 2: Batch Sending DOES Happen When Online!

### 🚨 **CRITICAL FINDING: Batch Processing Runs Every 30 Seconds REGARDLESS of Connection Status**

**File:** `esp32_hospital_watch_complete.ino` Lines 1142-1146

```cpp
// ✅ v5.2.1: Process offline queue every 30 seconds when connected
if (wifiConnected && mqttClient.connected() && (unsigned long)(millis() - lastQueueProcess) > 30000) {
  offlineQueue.processPendingMessages();
  lastQueueProcess = millis();
}
```

**What This Means:**
- Every 30 seconds, even when watch is **ONLINE and connected**
- Calls `offlineQueue.processPendingMessages()`
- This processes ALL queued messages from SPIFFS

---

## The Batch Upload System - How It Works

### When Messages Get Queued

**During Real-Time Streaming:**

1. **ESP32 generates waveform** every 100ms (line 1924: `sendWaveformStream()`)
2. **Checks MQTT connection** (line 2027):
   ```cpp
   if (!mqttClient.connected() || !isAssigned) {
     Serial.println("⚠️  MQTT disconnected - queuing waveform offline");
     offlineQueue.saveWaveform(payload);
     return;
   }
   ```
3. **If MQTT publish fails after 3 retries** (line 2035-2041):
   ```cpp
   bool publishResult = publishWithRetry(topic.c_str(), payload.c_str());
   if (publishResult) {
     // Success
   } else {
     Serial.println("⚠️  MQTT publish failed - queuing waveform offline");
     offlineQueue.saveWaveform(payload);
   }
   ```

**So messages get queued when:**
- ❌ MQTT disconnected (`mqttClient.connected()` = false)
- ❌ Device not assigned to patient (`isAssigned` = false)
- ❌ MQTT publish fails after 3 retry attempts

---

### When Queued Messages Get Sent (THE BATCH UPLOAD)

**File:** `esp32_hospital_watch_complete.ino` Lines 260-278

```cpp
void processPendingMessages() {
  if (!mqttClient.connected()) {
    Serial.println("⚠️  Cannot process queue - MQTT disconnected");
    return;
  }

  Serial.println("📤 Processing offline queue...");

  // Process vitals queue
  sendBatch("/queue/vitals", "hospital/devices/" + deviceId + "/vitals");

  // Process alerts queue
  sendBatch("/queue/alerts", "hospital/devices/" + deviceId + "/alerts");

  // Process waveforms queue (lower priority)
  sendBatch("/queue/waveforms", "hospital/devices/" + deviceId + "/stream");

  Serial.println("✅ Offline queue processing complete");
}
```

**Called from main loop** (line 1143):
```cpp
if (wifiConnected && mqttClient.connected() && (unsigned long)(millis() - lastQueueProcess) > 30000) {
  offlineQueue.processPendingMessages();
  lastQueueProcess = millis();
}
```

---

## 🔍 Root Cause Hypothesis: Batch Upload During Normal Operation

### Scenario 1: Normal Operation - No Batch Expected
```
Time 0s: Watch boots, connects to MQTT
Time 0-30s: Sends 300 waveform messages (100ms each)
Time 30s: Timer triggers → offlineQueue.processPendingMessages()
           Queue is empty → No batch upload
```

**Expected Console:**
```
📤 Processing offline queue...
✅ Offline queue processing complete
```

---

### Scenario 2: Transient Network Failure - Batch Occurs
```
Time 0s: Watch boots, connects to MQTT
Time 0-15s: Sends 150 waveform messages normally
Time 15s: Network hiccup → 2 messages fail to publish
          → Those 2 messages saved to /queue/waveforms/
Time 15-30s: Network recovers, sends 150 more messages normally
Time 30s: Timer triggers → offlineQueue.processPendingMessages()
          → Sends the 2 queued messages from 15s ago
          → THESE MESSAGES HAVE OLD SEQUENCE NUMBERS!
```

**Console at 30s:**
```
📤 Processing offline queue...
✅ Sent queued: /queue/waveforms/15123.json  (sequence: 75)
✅ Sent queued: /queue/waveforms/15223.json  (sequence: 76)
📤 Sent 2 queued messages from /queue/waveforms
✅ Offline queue processing complete
```

**Frontend receives:**
```
Sequence 298 → 50 samples  (real-time)
Sequence 299 → 50 samples  (real-time)
Sequence 75 → 50 samples   (BATCH - 15 seconds old!)
Sequence 76 → 50 samples   (BATCH - 15 seconds old!)
Sequence 300 → 50 samples  (real-time)
```

---

## 🚨 THE BUG: Out-of-Order Sequence Numbers Cause Buffer Corruption

**If frontend doesn't check sequence numbers:**
1. Frontend processes sequence 298-299 normally
2. **Batch upload** arrives with sequences 75-76 (old data)
3. Frontend **appends** this old data to current buffer
4. Some leads might process old data, others skip it
5. **Result: Some leads accumulate more samples than others**

---

## How This Could Cause V-Lead Compression

### Hypothesis: V-Leads Process Old Batch Data, Lead I/II Skip It

**Possible causes:**
1. **Conditional processing bug**: Maybe Lead I/II check `if (sequence > lastProcessed)` but V-leads don't?
2. **Different message arrival timing**: Maybe limb leads process before batch arrives, V-leads process after?
3. **Frontend buffer state differences**: Lead I/II buffers full, V-leads have room for more data?

---

## How to Verify This Hypothesis

### Check Frontend Console During Batch Upload

**Look for:**
1. **Sequence number jumps**:
   ```
   Sequence 298 → Sequence 75 → Sequence 76 → Sequence 300
   ```

2. **Out-of-order logs** (if we add sequence logging):
   ```
   🔍 Lead I: 49 deltas → 50 samples (seq: 298)
   🔍 V1: 49 deltas → 50 samples (seq: 75)   ← OLD DATA!
   🔍 V1: 49 deltas → 50 samples (seq: 76)   ← OLD DATA!
   🔍 Lead I: 49 deltas → 50 samples (seq: 300)
   ```

3. **Buffer length discrepancies**:
   ```
   📊 Buffer lengths at sequence 300: {
     'Lead I': 1000,
     'Lead II': 1000,
     'V1': 1100,  ← 100 MORE SAMPLES FROM BATCH!
   }
   ```

---

## Diagnostic Plan Update

### Add Sequence Number Logging

**File:** `hospital-display-app/src/hooks/useECGViewer.ts`

**After line 89** (inside WebSocket message handler):
```typescript
const waveformData = message.waveform;
if (!waveformData) {
  logger.warn('⚠️ Received waveform message without data');
  return;
}

// 🔍 DIAGNOSTIC: Log sequence number
if (waveformData.sequence && waveformData.sequence % 10 === 0) {
  console.log(`🔢 Waveform sequence: ${waveformData.sequence}`);
}
```

**Inside `getData()` helper** (line 119):
```typescript
if (waveformData.sequence && waveformData.sequence % 10 === 0 && leadName) {
  console.log(`  🔍 ${leadName}: ${leadData.deltas.length} deltas → ${decoded.length} samples (SEQ: ${waveformData.sequence})`);
}
```

---

## Expected Diagnostic Output

### Normal Operation (No Batch)
```
🔢 Waveform sequence: 290
  🔍 Lead I: 49 deltas → 50 samples (SEQ: 290)
  🔍 Lead II: 49 deltas → 50 samples (SEQ: 290)
  🔍 V1: 49 deltas → 50 samples (SEQ: 290)
📊 Buffer lengths at sequence 290: { 'Lead I': 1000, 'V1': 1000 }

🔢 Waveform sequence: 300
  🔍 Lead I: 49 deltas → 50 samples (SEQ: 300)
  🔍 Lead II: 49 deltas → 50 samples (SEQ: 300)
  🔍 V1: 49 deltas → 50 samples (SEQ: 300)
📊 Buffer lengths at sequence 300: { 'Lead I': 1000, 'V1': 1000 }
```

---

### During Batch Upload (BUG PRESENT)
```
🔢 Waveform sequence: 290
  🔍 Lead I: 49 deltas → 50 samples (SEQ: 290)
  🔍 Lead II: 49 deltas → 50 samples (SEQ: 290)
  🔍 V1: 49 deltas → 50 samples (SEQ: 290)
📊 Buffer lengths at sequence 290: { 'Lead I': 1000, 'V1': 1000 }

🔢 Waveform sequence: 75  ← BATCH UPLOAD (OLD DATA!)
  🔍 Lead I: 49 deltas → 50 samples (SEQ: 75)
  🔍 Lead II: 49 deltas → 50 samples (SEQ: 75)
  🔍 V1: 49 deltas → 50 samples (SEQ: 75)
📊 Buffer lengths at sequence 75: { 'Lead I': 1050, 'V1': 1050 }  ← BOTH GREW!

🔢 Waveform sequence: 76  ← BATCH UPLOAD (OLD DATA!)
  🔍 Lead I: 49 deltas → 50 samples (SEQ: 76)
  🔍 Lead II: 49 deltas → 50 samples (SEQ: 76)
  🔍 V1: 49 deltas → 50 samples (SEQ: 76)
📊 Buffer lengths at sequence 76: { 'Lead I': 1100, 'V1': 1100 }  ← BOTH GREW AGAIN!

🔢 Waveform sequence: 300
  🔍 Lead I: 49 deltas → 50 samples (SEQ: 300)
  🔍 Lead II: 49 deltas → 50 samples (SEQ: 300)
  🔍 V1: 49 deltas → 50 samples (SEQ: 300)
📊 Buffer lengths at sequence 300: { 'Lead I': 1000, 'V1': 1000 }  ← Back to normal after slice()
```

**BUT**: The canvas has already rendered the compressed waveforms from sequences 75-76 mixed with current data!

---

## Next Steps

1. **Add sequence logging** to diagnostic code (already implemented)
2. **Watch for sequence number jumps** in console
3. **Check ESP32 serial monitor** for batch upload messages:
   ```
   📤 Processing offline queue...
   ✅ Sent 2 queued messages from /queue/waveforms
   ```
4. **Correlate** ESP32 batch uploads with frontend sequence jumps

---

## Summary

### ✅ **YES - Waveforms Have IDs**
- `sequence` counter tracks waveform order
- Increments from 0 forever (no reset)
- Logged every 10th message

### 🚨 **YES - Batch Sending Happens Online**
- Every 30 seconds, `processPendingMessages()` runs
- Sends any queued messages from previous failures
- **These messages have OLD sequence numbers**
- **Could cause horizontal compression if frontend doesn't handle out-of-order data**

### 🎯 **Root Cause Hypothesis**
**Batch uploads during normal operation send old messages with low sequence numbers mixed into current high-sequence stream, causing some leads to accumulate extra samples and appear horizontally compressed.**

---

## Status

🟡 **HYPOTHESIS REQUIRES TESTING**

Need to observe console logs during batch upload (30-second mark) to confirm sequence number jumps.
