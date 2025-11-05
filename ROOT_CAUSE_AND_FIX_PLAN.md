# V-Lead Compression Bug - ROOT CAUSE FOUND + FIX PLAN

## User's Insight - THE BREAKTHROUGH 🎯

> "but why is it uploading queue messages in the first place when its able to stream nicely?"

**This question exposed the root cause!**

## Root Cause Analysis

### The Bug Flow:

1. **ESP32 Streams Normally** - 10 waveforms/sec, 50 samples each
2. **Momentary MQTT Glitch** - Connection drops for 1-2 seconds (network hiccup, Mosquitto restart, broker reconnect)
3. **Queueing Triggers** - [esp32_hospital_watch_complete.ino:2027-2030](../esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L2027-L2030):
   ```cpp
   if (!mqttClient.connected() || !isAssigned) {
       Serial.println("⚠️  MQTT disconnected - queuing waveform offline");
       offlineQueue.saveWaveform(payload);
       return;
   }
   ```
4. **Queue Accumulates** - 10-20 waveforms get saved to SPIFFS during the glitch
5. **Reconnection** - MQTT connection restores
6. **BATCH UPLOAD BURST** - Every 30 seconds [line 1143-1146](../esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1143-L1146):
   ```cpp
   if (wifiConnected && mqttClient.connected() && (unsigned long)(millis() - lastQueueProcess) > 30000) {
       offlineQueue.processPendingMessages();  // ← SENDS ALL QUEUED WAVEFORMS AT ONCE
       lastQueueProcess = millis();
   }
   ```
7. **Frontend Receives Burst** - 20 messages arrive in rapid succession (queued + live)
8. **V-Leads Accumulate More Data** - Due to processing order or React state mutation bug

## Why This Causes V-Lead Compression

### Hypothesis 1: Message Processing Order
```typescript
// useECGViewer.ts processes messages in order:
1. Limb leads (Lead I, II, III) → indices 0-2
2. Derived leads (aVR, aVL, aVF) → indices 3-5
3. V-leads (V1-V6) → indices 6-11
```

During burst:
- **Limb leads** processed first, React state updated
- **New message arrives** before V-leads processed
- **Limb lead buffers overwritten** with newer data
- **V-leads still processing OLD data** from first message
- **Result:** V-leads accumulate data from BOTH messages

### Hypothesis 2: React State Race Condition
```typescript
dataBufferRef.current[0] = [...dataBufferRef.current[0], ...samples].slice(-maxBufferSize);
```

During rapid-fire messages:
- Ref mutation happens faster than React can process
- Limb leads (processed first) get overwritten by next message
- V-leads (processed last) accumulate from multiple messages

## The Evidence

**User confirmed:** "it happens when queued messages come through"
**Console logs show:** All leads have 12,500 samples (eventually settle)
**Screenshot shows:** V-leads compressed 3-4x (accumulated burst data)

## Fix Options

### Option 1: Disable Waveform Queueing (RECOMMENDED)
**Rationale:** Waveforms are **ephemeral streaming data**, not critical diagnostic data

```cpp
// esp32_hospital_watch_complete.ino:2027-2031
if (!mqttClient.connected() || !isAssigned) {
    // ❌ OLD: Save to offline queue
    // offlineQueue.saveWaveform(payload);

    // ✅ NEW: Just drop waveforms when disconnected (ephemeral data)
    if (DEBUG_WAVEFORMS) {
        Serial.println("⚠️  MQTT disconnected - dropping waveform (ephemeral data)");
    }
    return;
}

// Lines 2047-2051
} else {
    // ❌ OLD: Queue failed waveforms
    // offlineQueue.saveWaveform(payload);

    // ✅ NEW: Drop failed waveforms
    if (DEBUG_WAVEFORMS) {
        Serial.println("⚠️  MQTT publish failed - dropping waveform (ephemeral data)");
    }
}
```

**Pros:**
- ✅ Fixes bug immediately
- ✅ Reduces SPIFFS wear
- ✅ Reduces burst traffic
- ✅ Waveforms are real-time - no value in old data
- ✅ Vitals + Alerts still queued (critical data preserved)

**Cons:**
- ⚠️ Lose waveforms during disconnection (but this is acceptable - they're ephemeral)

### Option 2: Reduce Queue Size
```cpp
// Line 284
const int MAX_WAVEFORMS = 1;   // Only keep 1 waveform (0.1 seconds)
```

**Pros:**
- ✅ Minimal burst (only 1 extra message)

**Cons:**
- ❌ Still causes small compression artifacts
- ❌ Doesn't address root issue

### Option 3: Frontend Rate Limiting
Add message throttling in WebSocket handler:

```typescript
// WebSocketService.ts
private lastWaveformTime: number = 0;

this.ws.onmessage = (event) => {
    const message = JSON.parse(event.data);

    if (message.type === 'waveformStream') {
        const now = Date.now();
        if (now - this.lastWaveformTime < 90) {  // Enforce minimum 90ms between waveforms
            console.warn('⚠️ Dropping waveform - too fast');
            return;
        }
        this.lastWaveformTime = now;
    }

    this.routeMessage(message);
};
```

**Pros:**
- ✅ Prevents burst processing
- ✅ Protects frontend from overload

**Cons:**
- ❌ Drops legitimate data during bursts
- ❌ Doesn't fix ESP32 queuing behavior

## RECOMMENDED FIX: Option 1 (Disable Waveform Queueing)

### Why This Is The Right Fix:

1. **Waveforms are ephemeral** - Real-time streaming data has no value when delayed
2. **Vitals + Alerts remain queued** - Critical diagnostic data is preserved
3. **Reduces system load** - No SPIFFS writes for waveforms
4. **Fixes bug completely** - No burst messages = no compression

### What Gets Queued vs Dropped:

**Queued (Critical):**
- ✅ Vitals (HR, SpO2, temp, RR)
- ✅ Alerts (battery, sensor malfunction, etc.)
- ✅ Heartbeats (device status)

**Dropped (Ephemeral):**
- ❌ Waveforms (ECG/EEG streaming data)
- **Rationale:** If network is down, real-time waveforms are useless anyway. Vitals provide sufficient diagnostic info.

### Implementation Steps:

1. Modify `sendWaveformStream()` to drop (not queue) when disconnected
2. Remove waveform queue processing from `processPendingMessages()`
3. Test: Disconnect MQTT, verify waveforms drop gracefully
4. Test: Reconnect, verify no burst messages
5. Test: Verify V-leads no longer compressed

## Alternative: Keep Minimal Queue

If you want to keep SOME waveform history:

```cpp
const int MAX_WAVEFORMS = 1;  // Only last 0.1 seconds
```

This limits burst to 1 extra message (negligible impact).

## Conclusion

**Root Cause:** Waveform queueing during MQTT glitches causes 30-second burst uploads
**Impact:** Frontend processes burst, V-leads accumulate extra data, causing compression
**Fix:** Disable waveform queueing (waveforms are ephemeral, not diagnostic)
**Result:** No bursts → No compression → Clean streaming

**Do you want me to implement Option 1 (disable waveform queueing)?**
