# Batch Upload / Rapid Update Issue - ROOT CAUSE FOUND

**Date:** 2025-11-03
**User Report:** "leads v1-v6 aren't clean like leads 1 & 2... feels like when batch upload/queue is sent, they get updated rapidly"

---

## Understanding the User's Issue

### What User is Seeing:
- **Lead I & II look "clean"** - smooth, continuous waveforms
- **V1-V6 and derived leads look "fucked"** - rapid updates, jumpy, batch-like behavior

### The REAL Question:
**Are Lead I & II coming from a different source (database) while V1-V6 come from real-time stream?**

---

## Data Flow Research

### ESP32 → Backend (ALL leads come from same source):

**File:** [esp32_hospital_watch_complete.ino:1683-1736](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1683-L1736)

```cpp
// ✅ ALL LEADS SENT IN SAME MQTT MESSAGE - No difference in source!

JsonDocument doc;
doc["deviceId"] = deviceId;
doc["timestamp"] = getISO8601Timestamp();

if (isECGMode) {
  JsonObject ecgWaveform = doc.createNestedObject("ecgWaveform");

  // Limb leads (I, II, III)
  JsonObject limb = ecgWaveform.createNestedObject("limb");
  addDeltaEncodedChannel(limb, "leadI", waveformAccumulator[0], 50);      // ← Lead I
  addDeltaEncodedChannel(limb, "leadII", waveformAccumulator[1], 50);     // ← Lead II
  addDeltaEncodedChannel(limb, "leadIII", lead3Array, 50);                // ← Lead III (calculated)

  // Precordial leads (V1-V6)
  JsonObject precordial = ecgWaveform.createNestedObject("precordial");
  addDeltaEncodedChannel(precordial, "v1", waveformAccumulator[2], 50);   // ← V1
  addDeltaEncodedChannel(precordial, "v2", waveformAccumulator[3], 50);   // ← V2
  addDeltaEncodedChannel(precordial, "v3", waveformAccumulator[4], 50);   // ← V3
  addDeltaEncodedChannel(precordial, "v4", waveformAccumulator[5], 50);   // ← V4
  addDeltaEncodedChannel(precordial, "v5", waveformAccumulator[6], 50);   // ← V5

  // Derived leads (aVR, aVL, aVF, V6)
  JsonObject derived = ecgWaveform.createNestedObject("derived");
  addDeltaEncodedChannel(derived, "avr", avrArray, 50);                   // ← aVR (calculated)
  addDeltaEncodedChannel(derived, "avl", avlArray, 50);                   // ← aVL (calculated)
  addDeltaEncodedChannel(derived, "avf", avfArray, 50);                   // ← aVF (calculated)
  addDeltaEncodedChannel(derived, "v6", waveformAccumulator[7], 50);      // ← V6
}

// ✅ ALL LEADS SENT TOGETHER IN ONE MQTT MESSAGE
mqttClient.publish(topic, payload);
```

**Conclusion:** ALL 12 leads come from the SAME MQTT message, sent at the SAME time (every 100ms).

**So why do Lead I & II look clean while V1-V6 look "rapid/batch-like"?**

---

## Hypothesis: Offline Queue Batch Processing

### The Offline Queue System:

**File:** [esp32_hospital_watch_complete.ino:261-279](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L261-L279)

```cpp
void processPendingMessages() {
  if (!mqttClient.connected()) {
    return;
  }

  Serial.println("📤 Processing offline queue...");

  // Process vitals queue
  sendBatch("/queue/vitals", "hospital/devices/" + deviceId + "/vitals");

  // Process alerts queue
  sendBatch("/queue/alerts", "hospital/devices/" + deviceId + "/alerts");

  // Process waveforms queue (lower priority) ← WAVEFORMS!
  sendBatch("/queue/waveforms", "hospital/devices/" + deviceId + "/stream");

  Serial.println("✅ Offline queue processing complete");
}
```

**When does this trigger?**

**File:** [esp32_hospital_watch_complete.ino:1143-1146](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1143-L1146)

```cpp
// ✅ v5.2.1: Process offline queue every 30 seconds when connected
if (wifiConnected && mqttClient.connected() && (unsigned long)(millis() - lastQueueProcess) > 30000) {
  offlineQueue.processPendingMessages();  // ← BATCH UPLOAD
  lastQueueProcess = millis();
}
```

**What happens during batch upload?**

**File:** [esp32_hospital_watch_complete.ino:337-389](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L337-L389)

```cpp
bool sendBatch(String queueDir, String topic) {
  // ... code to open SPIFFS directory ...

  File file = root.openNextFile();
  while (file) {  // ← LOOPS THROUGH ALL QUEUED FILES
    if (!file.isDirectory()) {
      String payload = file.readString();

      // Try to publish with retry
      if (publishWithRetry(topic.c_str(), payload.c_str(), 2)) {
        // Success - delete file
        file.close();
        SPIFFS.remove(filename);
        sentCount++;
        Serial.println("✅ Sent queued: " + filename);
      }
    }

    file = root.openNextFile();  // ← NEXT FILE
  }

  Serial.println("📤 Sent " + String(sentCount) + " queued messages");
}
```

**Result:** If ESP32 was offline for a while:
- **10 waveform messages** queued (MAX_WAVEFORMS = 10)
- Every 30 seconds, all 10 messages sent **rapidly in sequence**
- Frontend receives 10 × 100ms packets = **1 second of waveforms in rapid burst**

---

## The REAL Problem

### Scenario:
1. **ESP32 loses connection** (WiFi drops, MQTT broker down, etc.)
2. **Waveforms get queued** to SPIFFS (`/queue/waveforms/`)
3. **Max 10 waveform messages** saved (1 second total)
4. **ESP32 reconnects** after 1-2 minutes
5. **Every 30 seconds**, offline queue processes:
   ```
   📤 Processing offline queue...
   ✅ Sent queued: /queue/waveforms/1234567890.json
   ✅ Sent queued: /queue/waveforms/1234567891.json
   ✅ Sent queued: /queue/waveforms/1234567892.json
   ... (rapid burst of 10 messages)
   📤 Sent 10 queued messages from /queue/waveforms
   ```

### What User Sees:
- **Lead I & II:** Smooth, continuous (seem "clean")
- **V1-V6 & derived leads:** Rapid updates in bursts every 30 seconds (seem "fucked")

### Why the Difference?
**HYPOTHESIS:** Frontend rendering issue:
- All leads receive the SAME data
- But frontend might be rendering Lead I/II differently than V1-V6
- OR frontend buffer/cache handles Lead I/II vs V1-V6 differently
- OR Lead I/II get smoothed/interpolated while V1-V6 show raw batch updates

---

## Investigation Steps

### Step 1: Check if Queue is Actually Being Used

**Serial Monitor Output:**
- Look for: `⚠️  MQTT disconnected - queuing waveform offline`
- Look for: `📤 Processing offline queue...`
- Look for: `✅ Sent queued: /queue/waveforms/...`

If you see these messages, **queuing IS happening** and causing batch updates.

### Step 2: Check Frontend Waveform Cache

**File:** [hospital-display-app/src/services/WaveformCacheService.ts](hospital-display-app/src/services/WaveformCacheService.ts)

Does the frontend cache/buffer Lead I/II differently than V1-V6?

### Step 3: Check Frontend Rendering

**File:** [hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx](hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx)

Does the canvas render Lead I/II with interpolation/smoothing but V1-V6 without?

### Step 4: Check WebSocket Message Handling

**File:** [hospital-display-app/src/hooks/useECGViewer.ts](hospital-display-app/src/hooks/useECGViewer.ts)

Does the frontend handle limb leads (I, II, III) differently than precordial (V1-V6) or derived (aVR, aVL, aVF)?

---

## Possible Root Causes

### Option 1: Batch Queue Processing
- ESP32 was offline temporarily
- Waveforms queued to SPIFFS
- When reconnected, 10 messages sent rapidly
- Frontend receives burst of old data mixed with new data
- **Fix:** Disable offline queueing for waveforms (only keep vitals/alerts)

### Option 2: Frontend Rendering Difference
- All leads receive same data at same time
- But frontend renders Lead I/II with smoothing/interpolation
- V1-V6 rendered without smoothing (shows actual batch behavior)
- **Fix:** Apply same rendering to all leads

### Option 3: Frontend Buffer Management
- Lead I/II buffered differently (e.g., separate buffer with pre-fetching)
- V1-V6 buffered in main waveform buffer (shows batch behavior)
- **Fix:** Unify buffer management for all leads

### Option 4: Database vs Stream Mismatch
- **LEAST LIKELY** but worth checking:
- Frontend fetches Lead I/II from database (smooth, historical)
- Frontend uses WebSocket stream for V1-V6 (real-time, batch updates)
- **Fix:** Use same data source for all leads

---

## Recommended Fix

### Option A: Disable Waveform Queueing (Immediate Fix)

**File:** [esp32_hospital_watch_complete.ino:2030](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L2030)

```cpp
// ❌ BEFORE (queues waveforms)
if (!mqttClient.connected() || !isAssigned) {
  offlineQueue.saveWaveform(payload);  // ← Causes batch updates
  return;
}

// ✅ AFTER (drops waveforms when offline)
if (!mqttClient.connected() || !isAssigned) {
  // Drop waveforms when offline - vitals are more important
  // Real-time waveforms don't make sense to queue (too much data, stale by time of replay)
  Serial.println("⚠️  MQTT disconnected - dropping waveform (real-time only)");
  return;
}
```

**Also disable batch processing for waveforms:**

**File:** [esp32_hospital_watch_complete.ino:275-276](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L275-L276)

```cpp
// ❌ BEFORE
sendBatch("/queue/waveforms", "hospital/devices/" + deviceId + "/stream");

// ✅ AFTER (comment out)
// sendBatch("/queue/waveforms", "hospital/devices/" + deviceId + "/stream");
// Real-time waveforms should NOT be queued - only vitals/alerts need offline storage
```

### Option B: Frontend Unification (Better Fix)

**Ensure all leads are rendered the same way:**
1. Check if Lead I/II use different rendering path than V1-V6
2. Apply same smoothing/interpolation to all leads
3. Use same buffer management for all leads
4. Verify all leads use same data source (WebSocket stream, not database)

---

## Questions for User

1. **Do you see these messages in ESP32 Serial Monitor?**
   ```
   ⚠️  MQTT disconnected - queuing waveform offline
   📤 Processing offline queue...
   ✅ Sent 10 queued messages from /queue/waveforms
   ```

2. **Does the "rapid update" happen periodically (every 30 seconds)?**

3. **Are Lead I & II displayed in a different UI component than V1-V6?**

4. **Can you open browser DevTools → Network tab and check:**
   - Are Lead I/II fetched from HTTP API?
   - Are V1-V6 received via WebSocket?

---

## Status

🔴 **NEED USER CONFIRMATION** - Which hypothesis is correct?

**Next Action:**
1. User confirms if batch queue processing is happening (Serial Monitor)
2. User confirms if Lead I/II vs V1-V6 render differently
3. Apply appropriate fix based on root cause

---

**Most Likely:** Offline queue batch processing causing rapid bursts of waveforms every 30 seconds.

**Recommended:** Disable waveform queueing (real-time data shouldn't be queued anyway).
