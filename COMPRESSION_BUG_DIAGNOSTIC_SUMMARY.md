# V-Leads Horizontal Compression - Diagnostic Summary

**Date:** 2025-11-03
**Status:** 🟡 Diagnostic logging implemented, awaiting test results

---

## Your Questions Answered

### Q1: Do messages from watches have any ID for waveforms and vitals?

**Waveforms: ✅ YES**
- `sequence` counter (global, never resets)
- Starts at 0, increments forever
- Line 1951 in ESP32 firmware: `doc["sequence"] = waveformSequenceCounter++;`

**Vitals: ❌ NO**
- Only ISO 8601 timestamp
- No sequence counter

---

### Q2: What if batch send is sending data even when not offline right now?

**🚨 YOU'RE ABSOLUTELY RIGHT!**

**ESP32 processes offline queue EVERY 30 SECONDS, even when fully connected:**

```cpp
// Line 1143: esp32_hospital_watch_complete.ino
if (wifiConnected && mqttClient.connected() && (unsigned long)(millis() - lastQueueProcess) > 30000) {
  offlineQueue.processPendingMessages();
  lastQueueProcess = millis();
}
```

**This means:**
- Even when watch is online and streaming normally
- Every 30 seconds, it checks SPIFFS queue for old messages
- If any messages failed to publish earlier (network glitch), they get sent now
- **These old messages have LOW sequence numbers mixed into current HIGH sequence stream!**

---

## Root Cause Hypothesis

### The Batch Upload Problem

**Example Timeline:**
```
Time 0-15s: Watch streams normally (sequence 0-150)
Time 15s: Brief network hiccup → 2 messages (seq 75, 76) fail to publish
          → Saved to /queue/waveforms/ in SPIFFS
Time 15-30s: Network recovers, streaming continues (seq 150-300)
Time 30s: Timer triggers → processPendingMessages()
          → Sends old messages (seq 75, 76) from SPIFFS
          → Frontend receives: 298, 299, 75, 76, 300, 301...
```

**Frontend receives out-of-order messages:**
```
SEQ 298 (current) → 50 samples
SEQ 299 (current) → 50 samples
SEQ 75 (OLD!)     → 50 samples  ← Batch upload
SEQ 76 (OLD!)     → 50 samples  ← Batch upload
SEQ 300 (current) → 50 samples
```

**If frontend doesn't check sequence numbers:**
- Blindly appends seq 75 and 76 to current buffers
- Canvas has already rendered seq 0-299
- Now rendering seq 75-76 again as new data
- Some leads might process differently
- **Result: Horizontal compression**

---

## Diagnostic Logging Implemented

### Changes Made

**File:** `hospital-display-app/src/hooks/useECGViewer.ts`

1. **Sequence number logging** (line 96):
   ```typescript
   console.log(`🔢 Waveform sequence: ${waveformData.sequence}`);
   ```

2. **Delta decoding with sequence** (line 125):
   ```typescript
   console.log(`  🔍 ${leadName}: ${leadData.deltas.length} deltas → ${decoded.length} samples (SEQ: ${waveformData.sequence})`);
   ```

3. **Buffer length tracking** (line 193):
   ```typescript
   console.log(`📊 Buffer lengths at sequence ${waveformData.sequence}:`, { ... });
   ```

---

## What To Watch For

### Normal Operation (No Bug)
```
🔢 Waveform sequence: 290
  🔍 Lead I: 49 deltas → 50 samples (SEQ: 290)
  🔍 V1: 49 deltas → 50 samples (SEQ: 290)
📊 Buffer lengths: { 'Lead I': 1000, 'V1': 1000 }

🔢 Waveform sequence: 300
  🔍 Lead I: 49 deltas → 50 samples (SEQ: 300)
  🔍 V1: 49 deltas → 50 samples (SEQ: 300)
📊 Buffer lengths: { 'Lead I': 1000, 'V1': 1000 }
```

**Sequences increment sequentially: 290 → 300 → 310**

---

### Bug Present (Batch Upload)
```
🔢 Waveform sequence: 290
  🔍 Lead I: 49 deltas → 50 samples (SEQ: 290)
  🔍 V1: 49 deltas → 50 samples (SEQ: 290)
📊 Buffer lengths: { 'Lead I': 1000, 'V1': 1000 }

🔢 Waveform sequence: 75  ← JUMPS BACKWARDS!
  🔍 Lead I: 49 deltas → 50 samples (SEQ: 75)
  🔍 V1: 49 deltas → 50 samples (SEQ: 75)
📊 Buffer lengths: { 'Lead I': 1050, 'V1': 1050 }  ← GREW!

🔢 Waveform sequence: 76  ← OLD DATA CONTINUES
  🔍 Lead I: 49 deltas → 50 samples (SEQ: 76)
  🔍 V1: 49 deltas → 50 samples (SEQ: 76)
📊 Buffer lengths: { 'Lead I': 1100, 'V1': 1100 }  ← GREW AGAIN!

🔢 Waveform sequence: 300  ← Back to current
  🔍 Lead I: 49 deltas → 50 samples (SEQ: 300)
  🔍 V1: 49 deltas → 50 samples (SEQ: 300)
📊 Buffer lengths: { 'Lead I': 1000, 'V1': 1000 }  ← Normalized by slice()
```

**🚨 SMOKING GUN: Sequence jumps backwards (290 → 75 → 76 → 300)**

---

## How To Test

1. **Reload frontend** (hard refresh: Ctrl+Shift+R)
2. **Open browser console**
3. **Watch for:**
   - Sequence numbers every 10 messages
   - Any backwards jumps (e.g., 290 → 75)
4. **Check ESP32 serial monitor** for:
   ```
   📤 Processing offline queue...
   ✅ Sent 2 queued messages from /queue/waveforms
   ```
5. **Correlate** ESP32 batch uploads with frontend sequence jumps

---

## Testing Scenarios

### Scenario 1: Clean Boot (No Queued Messages)
**Expected:**
- Sequences increment normally (0 → 10 → 20 → 30)
- No compression visible
- No batch uploads

**Conclusion:** Bug not present, queue is empty

---

### Scenario 2: After Network Glitch
**Steps:**
1. Let watch run for 10 seconds
2. Briefly disconnect WiFi (5 seconds)
3. Reconnect WiFi
4. Wait 30 seconds for batch upload timer

**Expected if bug present:**
- Sequence jumps backwards at 30-second mark
- Buffers temporarily grow larger
- Horizontal compression appears briefly

**Conclusion:** Out-of-order messages cause compression

---

### Scenario 3: Force Queue Messages
**Steps:**
1. Flash ESP32
2. Let it boot and provision
3. **Before assigning patient**, let it generate waveforms (they get queued because `isAssigned = false`)
4. Assign patient
5. Watch for immediate batch upload

**Expected:**
- Massive sequence jump (current stream at seq 300, queued messages from seq 0-50)
- Severe compression visible

---

## Files Referenced

### Documentation
- [V_LEADS_COMPRESSION_ACTUAL_ROOT_CAUSE.md](V_LEADS_COMPRESSION_ACTUAL_ROOT_CAUSE.md) - Initial research
- [WHY_BATCH_HAPPENS_ROOT_CAUSE.md](WHY_BATCH_HAPPENS_ROOT_CAUSE.md) - Batch upload explanation
- [BATCH_SENDING_AND_ID_ANALYSIS.md](BATCH_SENDING_AND_ID_ANALYSIS.md) - Detailed ID and batch analysis
- [DIAGNOSTIC_LOGGING_IMPLEMENTED.md](DIAGNOSTIC_LOGGING_IMPLEMENTED.md) - Implementation details

### Code Files
- `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino` (lines 1143, 1951, 260-278)
- `hospital-display-app/src/hooks/useECGViewer.ts` (lines 95-202)

---

## Next Steps

### If Sequence Jumps Detected
1. ✅ Confirms batch uploads are the root cause
2. Implement sequence number validation in frontend:
   ```typescript
   const lastSequence = useRef(0);

   if (waveformData.sequence <= lastSequence.current) {
     console.warn(`⚠️ Ignoring out-of-order message: seq ${waveformData.sequence} (last: ${lastSequence.current})`);
     return; // Skip processing
   }

   lastSequence.current = waveformData.sequence;
   ```

### If No Sequence Jumps
1. Bug is NOT caused by batch uploads
2. Continue investigating other hypotheses:
   - Frontend buffer management
   - Canvas rendering differences
   - WebSocket message delivery order

---

## Summary

**Your intuition was correct!** The batch upload system runs every 30 seconds even when online, and could be sending old messages with low sequence numbers mixed into the current stream. This would cause horizontal compression if the frontend doesn't validate sequence numbers before processing.

**Diagnostic logging is now active** - we'll know within 30 seconds of testing whether this is the root cause by watching for backwards sequence jumps.

---

## Status

🟢 **READY FOR TESTING**

Run frontend, watch console for 30+ seconds, look for `🔢 Waveform sequence:` logs that jump backwards.
