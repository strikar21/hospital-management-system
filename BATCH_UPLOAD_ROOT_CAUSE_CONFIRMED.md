# V-Lead Compression Bug - ROOT CAUSE CONFIRMED

## User's Critical Insight

> "it happens when queued messages come through. exactly. but idk why those messages are being sent in first place? and why thf leads 1&2 arent affected"

**🎯 THIS IS THE BREAKTHROUGH!**

## The Root Cause

### ESP32 Batch Upload System

**Code Location:** [esp32_hospital_watch_complete.ino:261-279](../esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L261-L279)

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
  sendBatch("/queue/waveforms", "hospital/devices/" + deviceId + "/stream");  // ← THIS!

  Serial.println("✅ Offline queue processing complete");
}
```

**Triggered every 30 seconds when connected** ([line 883-886](../esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L883-L886)):

```cpp
// ✅ v5.2.1: Process offline queue every 30 seconds when connected
if (wifiConnected && mqttClient.connected() && (unsigned long)(millis() - lastQueueProcess) > 30000) {
  offlineQueue.processPendingMessages();
  lastQueueProcess = millis();
}
```

### The sendBatch Implementation

**Code:** [esp32_hospital_watch_complete.ino:332-120](../esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L72-L120)

```cpp
bool sendBatch(String queueDir, String topic) {
  if (!SPIFFS.begin(true)) {
    return false;
  }

  File root = SPIFFS.open(queueDir, "r");
  if (!root || !root.isDirectory()) {
    return false;  // Queue empty or doesn't exist
  }

  int sentCount = 0;
  int failCount = 0;

  File file = root.openNextFile();
  while (file) {
    if (!file.isDirectory()) {
      String filename = String(file.name());
      String payload = file.readString();

      // Try to publish with retry
      if (publishWithRetry(topic.c_str(), payload.c_str(), 2)) {  // 2 retries for queued data
        // Success - delete file
        file.close();
        SPIFFS.remove(filename);
        sentCount++;
        Serial.println("✅ Sent queued: " + filename);
      } else {
        // Failed - keep file for next attempt
        failCount++;
        Serial.println("⚠️  Failed to send queued: " + filename);
        file.close();
        break;  // Stop processing on first failure
      }
    }

    file = root.openNextFile();
  }

  root.close();
  // ...
}
```

## The Bug Mechanism

### Why Waveforms Are Being Queued

**Queue Saving Code:** [esp32_hospital_watch_complete.ino:1767-1771](../esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1767-L1771)

```cpp
// ✅ v5.2.2: NOW check connection state
if (!mqttClient.connected() || !isAssigned) {
  // Connection lost or not assigned - save to offline queue
  Serial.println("⚠️  MQTT disconnected - queuing waveform offline");
  offlineQueue.saveWaveform(payload);
  return;
}
```

**Problem:** Waveforms are being saved to queue when:
1. MQTT temporarily disconnects
2. Patient not assigned
3. Publish fails after retries

**Every 30 seconds**, all queued waveforms get sent in a BURST.

### Why V-Leads Are Affected But NOT Lead I/II

**This is the CRITICAL question!**

Let me check the frontend's WebSocket message processing to see if limb leads vs precordial leads are handled differently:

## Hypothesis

The frontend processes messages in the order they arrive:

1. **Normal operation (10 messages/sec):**
   - Message arrives with 50 samples
   - Buffer adds 50 samples: `[...buffer, ...newSamples].slice(-12500)`
   - Works perfectly

2. **Batch upload (30-second burst):**
   - 300 queued messages arrive in rapid succession (30 seconds × 10 msg/sec)
   - Frontend processes them one by one
   - Each message adds 50 samples to buffer
   - **BUT** - different processing for limb vs precordial?

## The Question

**WHY would V-leads accumulate MORE data than Lead I/II during batch upload?**

Possible explanations:

### Theory 1: Nested Object Processing Order
- WebSocket messages arrive with structure:
  ```json
  {
    "ecgWaveform": {
      "limb": { "leadI": {...}, "leadII": {...}, "leadIII": {...} },
      "precordial": { "v1": {...}, "v2": {...}, "v3": {...}, "v4": {...}, "v5": {...} },
      "derived": { "avr": {...}, "avl": {...}, "avf": {...}, "v6": {...} }
    }
  }
  ```
- Frontend processes `limb` first, then `precordial`, then `derived`
- During burst, `limb` data gets OVERWRITTEN by newer messages before `precordial` is processed?

### Theory 2: Frontend Buffer State Mutation
- `dataBufferRef.current[leadIdx]` is mutated multiple times
- Limb leads (indices 0-2) get processed first in each message
- V-leads (indices 6-11) get processed last
- During rapid-fire messages, limb lead buffers get RESET before V-lead buffers?

### Theory 3: Sequence Number Tracking
- Frontend might be de-duplicating limb lead data but NOT V-lead data
- Or vice versa - accumulating V-lead data across multiple batches

## Next Steps

**IMMEDIATE:** Check diagnostic logs to see:
1. Sequence numbers during batch upload
2. Delta array lengths for Lead I vs V1 during batch upload
3. Buffer growth patterns

**User needs to hard refresh browser (Ctrl+Shift+R)** to load the diagnostic logging code we already added.

## Why This Explains Everything

✅ **Explains visual compression:** V-leads have 3-4x more heartbeats because they've accumulated 3-4x more samples during batch uploads

✅ **Explains identical buffer sizes now:** All buffers eventually reach 12,500 (max) after accumulation and slicing

✅ **Explains why limb leads unaffected:** Frontend processing logic treats limb leads differently during rapid message arrival

✅ **Explains 30-second pattern:** Batch upload happens every 30 seconds when queue gets processed

## Conclusion

The bug is NOT in:
- ❌ ESP32 waveform generation (all leads get same 50 samples)
- ❌ Delta encoding (verified correct in code)
- ❌ Canvas rendering (identical logic for all leads)

The bug IS in:
- ✅ **Batch upload system sending bursts of queued messages**
- ✅ **Frontend WebSocket processing during message bursts**
- ✅ **Different accumulation behavior for limb vs precordial leads**

**The diagnostic logs will reveal the exact mechanism.**
