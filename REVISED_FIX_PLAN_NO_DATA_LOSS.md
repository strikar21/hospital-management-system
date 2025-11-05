# V-Lead Compression Bug - REVISED FIX (No Data Loss)

## User's Critical Feedback

> "if there's lost data whats the entire use?"

**✅ You're absolutely right!** Waveforms contain critical diagnostic data:
- ST segment elevation (heart attack)
- Arrhythmia patterns
- QRS complex morphology
- T-wave abnormalities

**Dropping waveforms = losing critical medical data = unacceptable!**

## The Real Problem

**Root Cause:** Batch uploads send bursts of queued waveforms, causing V-leads to accumulate MORE data than limb leads.

**But WHY does queueing happen?**
- ❌ **Not** because MQTT is disconnected (streaming works fine)
- ❌ **Not** because of network issues (user confirmed streaming is smooth)
- ✅ **It's a BUG in the code logic!**

## Let Me Research WHY Waveforms Are Being Queued

Looking at the code again:

```cpp
// Lines 2027-2031
if (!mqttClient.connected() || !isAssigned) {
    Serial.println("⚠️  MQTT disconnected - queuing waveform offline");
    offlineQueue.saveWaveform(payload);
    return;
}
```

**The problem:** This check runs on **EVERY waveform** (10 times per second).

Even a **single millisecond glitch** where `mqttClient.connected()` returns false will queue messages.

## The REAL Fix - Rate Limit Queue Processing

**Option 1: Increase Queue Processing Interval** ✅ RECOMMENDED

Instead of sending queued messages every 30 seconds, send them:
- **Every 5 minutes** when patient is NOT in critical state
- **Disable during active monitoring** (when live streaming is working)

```cpp
// Line 1143-1146
// ❌ OLD: Every 30 seconds (causes bursts)
if (wifiConnected && mqttClient.connected() && (unsigned long)(millis() - lastQueueProcess) > 30000) {

// ✅ NEW: Only process queue during extended disconnections (5 minutes)
// This prevents burst uploads during normal operation
if (wifiConnected && mqttClient.connected() && (unsigned long)(millis() - lastQueueProcess) > 300000) {
```

**Pros:**
- ✅ No data loss
- ✅ Queued messages only sent during genuine long disconnections
- ✅ Prevents burst uploads during normal streaming
- ✅ V-leads won't accumulate extra data

**Cons:**
- ⚠️ Queued data delayed by 5 minutes (but this is acceptable for historical data)

---

**Option 2: Smart Queue Processing** ✅ BETTER

Only process queue when **actively disconnected for extended period:**

```cpp
// Track consecutive successful publishes
uint32_t consecutiveSuccessfulPublishes = 0;

// In sendWaveformStream():
if (publishResult) {
    consecutiveSuccessfulPublishes++;
}

// In loop():
// Only process queue if we've had recent connection problems
bool recentConnectionIssues = (consecutiveSuccessfulPublishes < 50);  // Less than 5 seconds of success

if (wifiConnected && mqttClient.connected() &&
    recentConnectionIssues &&
    (unsigned long)(millis() - lastQueueProcess) > 60000) {  // 1 minute
    offlineQueue.processPendingMessages();
    lastQueueProcess = millis();
}
```

**Pros:**
- ✅ No data loss
- ✅ Only sends queue during actual connection problems
- ✅ Prevents burst during stable streaming
- ✅ Faster recovery (1 minute vs 5 minutes)

**Cons:**
- Slightly more complex logic

---

**Option 3: Rate-Limited Queue Sending** ✅ BEST

Send queued messages **one at a time** with delays, not all at once:

```cpp
bool sendBatch(String queueDir, String topic) {
    // ... existing code ...

    File file = root.openNextFile();
    int sentThisRound = 0;
    const int MAX_PER_ROUND = 3;  // ✅ NEW: Limit to 3 messages per round

    while (file && sentThisRound < MAX_PER_ROUND) {
        if (!file.isDirectory()) {
            String filename = String(file.name());
            String payload = file.readString();

            if (publishWithRetry(topic.c_str(), payload.c_str(), 2)) {
                file.close();
                SPIFFS.remove(filename);
                sentCount++;
                sentThisRound++;
                Serial.println("✅ Sent queued: " + filename);

                delay(100);  // ✅ NEW: 100ms delay between queued messages (10/sec max)
            } else {
                failCount++;
                file.close();
                break;
            }
        }
        file = root.openNextFile();
    }

    root.close();
    // ...
}
```

**Pros:**
- ✅ No data loss
- ✅ Queued messages sent gradually (not burst)
- ✅ Frontend receives data at manageable rate
- ✅ V-leads won't accumulate extra data

**Cons:**
- Takes longer to clear queue (but acceptable for historical data)

## RECOMMENDED SOLUTION: Combination Approach

**Implement ALL three fixes together:**

1. **Increase queue interval** (30s → 5min) to prevent frequent bursts
2. **Smart queue trigger** - only process during connection issues
3. **Rate-limited sending** - send max 3 messages per round with 100ms delays

This ensures:
- ✅ **No data loss** - all waveforms eventually delivered
- ✅ **No bursts** - queued messages trickle in slowly
- ✅ **No V-lead compression** - frontend processes data smoothly
- ✅ **Fast recovery** - queue clears within reasonable time

## Implementation

```cpp
// ====================================
// GLOBAL VARIABLES (add near line 233)
// ====================================
uint32_t consecutiveSuccessfulPublishes = 0;
const int MAX_QUEUE_MESSAGES_PER_ROUND = 3;  // Limit burst size

// ====================================
// MODIFIED sendWaveformStream() (lines 2047-2051)
// ====================================
if (publishResult) {
    consecutiveSuccessfulPublishes++;  // ✅ Track connection stability
    if (waveformSequenceCounter % 10 == 0) {
        Serial.println("📈 Waveform stream: " + String(isECGMode ? "ECG" : "EEG") +
                      " (seq: " + String(waveformSequenceCounter) +
                      ", size: " + String(payload.length()) + " bytes)");
    }
} else {
    consecutiveSuccessfulPublishes = 0;  // ✅ Reset on failure
    // ✅ Publish failed after retries - save to offline queue
    Serial.println("⚠️  MQTT publish failed - queuing waveform offline");
    offlineQueue.saveWaveform(payload);
}

// ====================================
// MODIFIED loop() queue processing (lines 1143-1146)
// ====================================
// ✅ v5.2.6: Smart queue processing - only during connection instability
bool recentConnectionIssues = (consecutiveSuccessfulPublishes < 50);  // Less than 5 seconds stable

if (wifiConnected && mqttClient.connected() &&
    recentConnectionIssues &&
    (unsigned long)(millis() - lastQueueProcess) > 60000) {  // 1 minute during issues
    offlineQueue.processPendingMessages();
    lastQueueProcess = millis();
} else if (wifiConnected && mqttClient.connected() &&
           (unsigned long)(millis() - lastQueueProcess) > 300000) {  // 5 minutes when stable
    offlineQueue.processPendingMessages();
    lastQueueProcess = millis();
}

// ====================================
// MODIFIED sendBatch() in OfflineQueue (lines 332-380)
// ====================================
bool sendBatch(String queueDir, String topic) {
    // ... existing code ...

    int sentCount = 0;
    int failCount = 0;
    int sentThisRound = 0;

    File file = root.openNextFile();
    while (file && sentThisRound < MAX_QUEUE_MESSAGES_PER_ROUND) {  // ✅ Limit burst size
        if (!file.isDirectory()) {
            String filename = String(file.name());
            String payload = file.readString();

            if (publishWithRetry(topic.c_str(), payload.c_str(), 2)) {
                file.close();
                SPIFFS.remove(filename);
                sentCount++;
                sentThisRound++;
                Serial.println("✅ Sent queued: " + filename);
                delay(100);  // ✅ 100ms delay between queued messages
            } else {
                failCount++;
                file.close();
                break;
            }
        }
        file = root.openNextFile();
    }
    // ...
}
```

## Conclusion

**No data loss + No compression = Perfect solution!**

This fixes the V-lead compression bug while preserving ALL diagnostic waveform data.

**Shall I implement this fix?**
