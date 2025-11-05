# Diagnostic Logging Implemented - V-Leads Horizontal Compression

**Date:** 2025-11-03
**Purpose:** Gather runtime data to identify why V-leads appear horizontally compressed
**Hypothesis:** Batch updates may cause V-leads to accumulate more samples than Lead I/II

---

## Changes Made

### File: `hospital-display-app/src/hooks/useECGViewer.ts`

#### 1. Sequence Number Logging (Lines 95-98)
**Added after waveform data validation**

```typescript
// 🔍 DIAGNOSTIC: Log sequence number to detect batch uploads
if (waveformData.sequence && waveformData.sequence % 10 === 0) {
  console.log(`🔢 Waveform sequence: ${waveformData.sequence}`);
}
```

**What This Shows:**
- **CRITICAL**: Detects batch uploads from offline queue
- Shows if sequence numbers jump backwards (e.g., 290 → 75 → 76 → 300)
- Identifies old messages being replayed

---

#### 2. Enhanced `getData()` Helper Function (Lines 118-133)
**Added optional `leadName` parameter and delta decoding diagnostic logging with sequence numbers**

```typescript
const getData = (leadData: any, leadName?: string) => {
  if (!leadData) return [];
  // Delta-encoded: {baseline: number, deltas: number[]}
  if (leadData.baseline !== undefined && leadData.deltas !== undefined) {
    const decoded = decodeDeltaChannel(leadData);
    // 🔍 DIAGNOSTIC: Log delta array length every 10th message (with sequence number)
    if (waveformData.sequence && waveformData.sequence % 10 === 0 && leadName) {
      console.log(`  🔍 ${leadName}: ${leadData.deltas.length} deltas → ${decoded.length} samples (SEQ: ${waveformData.sequence})`);
    }
    return decoded;
  }
  // Raw array (legacy v5.2.4 and earlier)
  if (Array.isArray(leadData)) {
    return leadData;
  }
  return [];
};
```

**What This Shows:**
- Number of deltas in the incoming delta-encoded array
- Number of samples after decoding (should be deltas.length + 1)
- **Sequence number** - correlates with batch upload timing
- Per-lead breakdown to compare Lead I/II vs V1-V6

---

#### 3. Added Lead Names to All `getData()` Calls (Lines 139-188)

**Examples:**
```typescript
// Lead I
const samples = getData(limb.leadI, 'Lead I');

// Lead II
const samples = getData(limb.leadII, 'Lead II');

// V1-V6
const samples = getData(precordial.v1, 'V1');
const samples = getData(precordial.v2, 'V2');
// ... etc
```

**What This Shows:**
- Which lead each delta array belongs to
- Enables per-lead delta count comparison

---

#### 4. Buffer Length Logging (Lines 191-202)

**Added after all leads are processed:**
```typescript
// 🔍 DIAGNOSTIC: Log buffer lengths every 10th message
if (waveformData.sequence && waveformData.sequence % 10 === 0) {
  console.log(`📊 Buffer lengths at sequence ${waveformData.sequence}:`, {
    'Lead I': dataBufferRef.current[0]?.length || 0,
    'Lead II': dataBufferRef.current[1]?.length || 0,
    'V1': dataBufferRef.current[6]?.length || 0,
    'V2': dataBufferRef.current[7]?.length || 0,
    'V3': dataBufferRef.current[8]?.length || 0,
    'V4': dataBufferRef.current[9]?.length || 0,
  });
  logger.log(`✅ ECG processed - ${dataBufferRef.current[1].length} samples buffered`);
}
```

**What This Shows:**
- Total samples accumulated in each lead's buffer
- Comparison across Lead I, Lead II, and V1-V6
- Shows if V-leads are accumulating more samples than Lead I/II

---

## Expected Console Output

### Normal Operation (All Leads Identical, Sequential Sequence Numbers)
```
🔢 Waveform sequence: 290
  🔍 Lead I: 49 deltas → 50 samples (SEQ: 290)
  🔍 Lead II: 49 deltas → 50 samples (SEQ: 290)
  🔍 V1: 49 deltas → 50 samples (SEQ: 290)
  🔍 V2: 49 deltas → 50 samples (SEQ: 290)
  🔍 V3: 49 deltas → 50 samples (SEQ: 290)
  🔍 V4: 49 deltas → 50 samples (SEQ: 290)
📊 Buffer lengths at sequence 290: {
  'Lead I': 1000,
  'Lead II': 1000,
  'V1': 1000,
  'V2': 1000,
  'V3': 1000,
  'V4': 1000
}

🔢 Waveform sequence: 300
  🔍 Lead I: 49 deltas → 50 samples (SEQ: 300)
  🔍 Lead II: 49 deltas → 50 samples (SEQ: 300)
  🔍 V1: 49 deltas → 50 samples (SEQ: 300)
📊 Buffer lengths at sequence 300: { ... }
```

### During Batch Upload (If Bug Occurs - SEQUENCE JUMPS BACKWARDS!)
```
🔢 Waveform sequence: 290
  🔍 Lead I: 49 deltas → 50 samples (SEQ: 290)
  🔍 Lead II: 49 deltas → 50 samples (SEQ: 290)
  🔍 V1: 49 deltas → 50 samples (SEQ: 290)
📊 Buffer lengths at sequence 290: { 'Lead I': 1000, 'V1': 1000 }

🔢 Waveform sequence: 75  ← BATCH UPLOAD! Old data from 15 seconds ago!
  🔍 Lead I: 49 deltas → 50 samples (SEQ: 75)
  🔍 Lead II: 49 deltas → 50 samples (SEQ: 75)
  🔍 V1: 49 deltas → 50 samples (SEQ: 75)
📊 Buffer lengths at sequence 75: { 'Lead I': 1050, 'V1': 1050 }  ← GREW!

🔢 Waveform sequence: 76  ← BATCH UPLOAD! Old data!
  🔍 Lead I: 49 deltas → 50 samples (SEQ: 76)
  🔍 Lead II: 49 deltas → 50 samples (SEQ: 76)
  🔍 V1: 49 deltas → 50 samples (SEQ: 76)
📊 Buffer lengths at sequence 76: { 'Lead I': 1100, 'V1': 1100 }  ← GREW AGAIN!

🔢 Waveform sequence: 300  ← Back to current stream
  🔍 Lead I: 49 deltas → 50 samples (SEQ: 300)
  🔍 Lead II: 49 deltas → 50 samples (SEQ: 300)
  🔍 V1: 49 deltas → 50 samples (SEQ: 300)
📊 Buffer lengths at sequence 300: { 'Lead I': 1000, 'V1': 1000 }  ← Back to normal after slice()
```

**🚨 THE SMOKING GUN**: If you see sequence numbers jump backwards (290 → 75 → 76 → 300), that's the batch upload causing compression!

---

## How to Test

1. **Reload frontend** to pick up changes:
   - Hard refresh browser (Ctrl+Shift+R)
   - Or restart frontend dev server

2. **Watch console** during normal streaming:
   - Every 10th message will show delta counts and buffer lengths

3. **Trigger batch upload** (if possible):
   - Disconnect ESP32 from WiFi
   - Let it accumulate data in SPIFFS
   - Reconnect and watch for batch upload

4. **Look for anomalies**:
   - Do V-leads have more deltas than Lead I/II?
   - Do V-lead buffers grow faster than Lead I/II buffers?

---

## Diagnostic Questions This Answers

### Q1: Do V-leads receive more deltas in their delta arrays?
**Answer:** Check `🔍` logs - compare delta counts across leads

### Q2: Do V-leads accumulate more samples in their buffers?
**Answer:** Check `📊` logs - compare buffer lengths across leads

### Q3: Does this happen during batch uploads specifically? **← CRITICAL QUESTION**
**Answer:** Check `🔢` logs - watch for sequence number jumps (e.g., 290 → 75 → 76 → 300)
- **Normal**: Sequence increments sequentially (290 → 300 → 310)
- **Batch Upload**: Sequence jumps backwards (290 → 75 → 76 → 300)
- **ESP32 logs**: Look for "📤 Processing offline queue..." every 30 seconds

### Q4: Are all leads receiving the same data from ESP32?
**Answer:** If deltas differ, bug is in ESP32 firmware. If deltas same but buffers differ, bug is in frontend.

### Q5: **NEW** - Are batch uploads causing out-of-order data processing?
**Answer:** If sequence numbers jump backwards and buffers temporarily grow larger, then batch uploads are the root cause!

---

## Next Steps After Gathering Data

**If V-leads have MORE deltas:**
→ Bug is in ESP32 firmware's delta encoding (lines 1912-1978 in .ino)

**If all leads have SAME deltas but V-lead buffers grow faster:**
→ Bug is in frontend data accumulation (lines 128-179 in useECGViewer.ts)

**If all data is identical but rendering looks compressed:**
→ Bug is in canvas rendering (ECGWaveformCanvas.tsx)

---

## Files Changed

- ✅ `hospital-display-app/src/hooks/useECGViewer.ts` (4 edits)

## Critical Discovery - Batch Upload System

### ESP32 Batch Processing Runs Every 30 Seconds

**File:** `esp32_hospital_watch_complete.ino` Line 1143

```cpp
// Process offline queue every 30 seconds when connected
if (wifiConnected && mqttClient.connected() && (unsigned long)(millis() - lastQueueProcess) > 30000) {
  offlineQueue.processPendingMessages();
  lastQueueProcess = millis();
}
```

**What This Means:**
- Every 30 seconds, even when watch is **ONLINE and fully connected**
- Processes any queued messages from previous network failures
- **These messages have OLD sequence numbers**
- Could cause horizontal compression if frontend processes them

### Watch For This In Console

**At 30-second mark, ESP32 serial monitor shows:**
```
📤 Processing offline queue...
✅ Sent 2 queued messages from /queue/waveforms
```

**Frontend console should show:**
```
🔢 Waveform sequence: 290  (current)
🔢 Waveform sequence: 75   (BATCH - 15 seconds old!)
🔢 Waveform sequence: 76   (BATCH - 15 seconds old!)
🔢 Waveform sequence: 300  (current)
```

**If you see this sequence jump backwards, that's the root cause!**

---

## Status

🟢 **READY FOR TESTING**

Diagnostic logging is now active with sequence number tracking. Run frontend and watch for:
1. **Sequence number jumps** (e.g., 290 → 75 → 76 → 300)
2. **Buffer length spikes** during batch upload
3. **ESP32 "Processing offline queue" messages** every 30 seconds

See [BATCH_SENDING_AND_ID_ANALYSIS.md](BATCH_SENDING_AND_ID_ANALYSIS.md) for detailed analysis of the batch upload system.
