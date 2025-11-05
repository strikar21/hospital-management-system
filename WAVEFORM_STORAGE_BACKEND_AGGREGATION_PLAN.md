# Waveform Storage - Backend Aggregation Implementation Plan
**Date:** 2025-11-02
**Approach:** Backend aggregates `/stream` packets into 10-second snapshots (NO ESP32 changes)

---

## SENIOR TECH LEAD CHECKLIST

### 1. Do I have a detailed failproof plan for each of the fixes?
**YES** - This document provides step-by-step implementation plan with all components identified.

### 2. Have I thought of alternative plans or if something better exists?
**YES** - See [WAVEFORM_STORAGE_ARCHITECTURE_OPTIONS.md](WAVEFORM_STORAGE_ARCHITECTURE_OPTIONS.md)
- Option A: ESP32 sends twice → Wasteful, rejected
- Option B: Backend aggregation → Efficient, chosen ✅

### 3. Does the code I plan to fix conform to both project and memory guidelines?
**YES**:
- ✅ All camelCase naming (patientId, deviceId, sampleRate)
- ✅ Backend-only medical logic (aggregation happens on backend)
- ✅ Modular code (separate WaveformAggregator service)
- ✅ No frontend changes (backend storage only)

### 4. Have I thought about the fixes with logic and sense?
**YES**:
- ✅ Reuses existing `/stream` messages (already working)
- ✅ Backend has more resources than ESP32 for aggregation
- ✅ No redundant data transmission
- ✅ Better battery life for ESP32
- ✅ Handles edge cases (device disconnect, buffer cleanup)

### 5. Have I thought this out like a senior experienced tech lead?
**YES**:
- ✅ Root cause fix (enables waveform storage)
- ✅ Architecturally sound (server-side aggregation)
- ✅ Production-ready (error handling, logging, cleanup)
- ✅ Testable (can verify database rows after 10 seconds)
- ✅ Maintainable (clear separation of concerns)

---

## PROBLEM STATEMENT

**Current State:**
- ESP32 publishes to `/stream` topic (100ms intervals, 50 samples each)
- Backend broadcasts `/stream` to WebSocket (real-time display) ✅ WORKING
- Backend does NOT store waveforms to database ❌ NOT WORKING
- `waveform_snapshots` table has 0 rows

**Root Cause:**
- Backend expects `/waveform` topic for storage
- ESP32 never publishes to `/waveform` topic
- No aggregation logic exists to convert `/stream` → storage

**Goal:**
- Aggregate 100 × `/stream` packets (100ms × 100 = 10 seconds = 5000 samples)
- Store as 10-second snapshots in `waveform_snapshots` table
- Enable 7-year HIPAA retention for ECG/EEG data

---

## ARCHITECTURE OVERVIEW

```
┌─────────────┐
│   ESP32     │
│   Watch     │
└─────┬───────┘
      │ Publishes /stream every 100ms
      │ (50 samples per packet)
      ▼
┌─────────────────────────────────────────────────────┐
│              MQTT Broker (Mosquitto)                 │
└─────┬───────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────┐
│            Backend (mqtt_service.py)                 │
│                                                      │
│  _handleWaveformStream() ◄─── Receives /stream      │
│         │                                            │
│         ├─► WebSocket Broadcast (real-time) ✅      │
│         │                                            │
│         └─► WaveformAggregator.addStreamPacket()    │
│                     │                                │
│                     ▼                                │
│         ┌──────────────────────────┐                │
│         │  WaveformAggregator      │                │
│         │  ─────────────────────   │                │
│         │  • Buffer per device     │                │
│         │  • Collect 100 packets   │                │
│         │  • Aggregate 5000 samples│                │
│         │  • Store to DB           │                │
│         └──────────┬───────────────┘                │
│                    │                                 │
│                    ▼                                 │
│         _storeWaveformSnapshot()                     │
│                    │                                 │
└────────────────────┼─────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│   TimescaleDB (waveform_snapshots table)            │
│   • 10-second snapshots                             │
│   • Delta-encoded for compression                   │
│   • HIPAA 7-year retention                          │
└─────────────────────────────────────────────────────┘
```

---

## DETAILED IMPLEMENTATION PLAN

### Phase 1: Create WaveformAggregator Service

**File:** `hospital-backend/app/services/waveform_aggregator.py`

**Responsibilities:**
1. Maintain per-device aggregation buffers
2. Collect 100 packets (10 seconds worth)
3. Aggregate into single waveform snapshot
4. Store to TimescaleDB
5. Cleanup on device disconnect

**Key Methods:**
- `addStreamPacket()` - Add 50-sample packet to buffer
- `_createAndStoreSnapshot()` - Aggregate and store when buffer full
- `_aggregateECGWaveform()` - Combine ECG packets
- `_aggregateEEGWaveform()` - Combine EEG packets
- `_createChannelData()` - Delta encoding for compression
- `_storeWaveformSnapshot()` - Insert to TimescaleDB
- `cleanupDevice()` - Remove buffer on disconnect

**Buffer Structure:**
```python
self.buffers = {
    'WATCH_001': {
        'packets': [packet1, packet2, ..., packet100],  # 100 × 50-sample packets
        'startTime': datetime(2025, 11, 2, 10, 30, 0),
        'mode': 'ecg',
        'patientId': 'uuid-...',
        'deviceId': 'WATCH_001',
        'sampleRate': 500
    }
}
```

**Memory Usage:**
- Each packet ≈ 200 bytes (JSON)
- 100 packets × 200 bytes = 20KB per device
- 100 active devices = 2MB total (acceptable)

---

### Phase 2: Integrate into mqtt_service.py

**File:** `hospital-backend/app/services/mqtt_service.py`

**Changes Required:**

**1. Import WaveformAggregator (around line 10):**
```python
from .waveform_aggregator import waveformAggregator
```

**2. Initialize in MQTTService.__init__() (around line 80):**
```python
self.waveformAggregator = waveformAggregator
```

**3. Modify _handleWaveformStream() (around line 735):**
```python
async def _handleWaveformStream(self, deviceId: str, payload: Dict[str, Any]):
    """
    Handle real-time waveform streaming packets (100ms batches)
    NOW: Also aggregates for 10-second snapshot storage
    """
    # ... existing WebSocket broadcast code (lines 694-762) ...

    # ✅ NEW: Aggregate for 10-second snapshot storage
    patientId = payload.get('patientId')
    await self.waveformAggregator.addStreamPacket(
        deviceId=deviceId,
        patientId=patientId,
        streamPayload=payload
    )
    logger.debug(f"📊 Stream packet added to aggregation buffer for {deviceId}")
```

**4. Add cleanup on device disconnect (check existing disconnect handlers):**
```python
# Find disconnect handler and add:
self.waveformAggregator.cleanupDevice(deviceId)
```

---

### Phase 3: Data Format Verification

**Current /stream Message Format (from ESP32):**
```json
{
  "deviceId": "WATCH_001",
  "patientId": "uuid-...",
  "timestamp": "2025-11-02T10:30:00Z",
  "mode": "ecg",
  "sampleRate": 500,
  "sequence": 12345,
  "ecgWaveform": {
    "limb": {
      "lead1": [123, 125, 128, ..., 145],  // 50 samples
      "lead2": [234, 236, 239, ..., 256],
      "lead3": [111, 111, 111, ..., 111]
    },
    "precordial": {
      "v1": [...],  // 50 samples
      "v2": [...],
      "v3": [...],
      "v4": [...],
      "v5": [...]
    },
    "derived": {
      "avr": [...],  // 50 samples
      "avl": [...],
      "avf": [...],
      "v6": [...]
    }
  }
}
```

**Aggregated /waveform Format (for database):**
```json
{
  "deviceId": "WATCH_001",
  "patientId": "uuid-...",
  "timestamp": "2025-11-02T10:30:00Z",
  "mode": "ecg",
  "sampleRate": 500,
  "duration": 10,
  "compression": "delta",
  "ecgWaveform": {
    "limb": {
      "leadI": {
        "baseline": 123,
        "deltas": [2, 3, -1, ..., 17]  // 4999 deltas (5000 samples total)
      },
      "leadII": {...},
      "leadIII": {...}
    },
    "precordial": {...},
    "derived": {...}
  }
}
```

**Key Differences:**
- **Sample count:** 50 → 5000 samples per lead
- **Encoding:** Raw arrays → Delta encoding (baseline + deltas)
- **Lead naming:** `lead1/lead2/lead3` → `leadI/leadII/leadIII` (backend schema uses Roman numerals)

**⚠️ IMPORTANT NAMING MISMATCH FOUND:**
- ESP32 sends: `lead1`, `lead2`, `lead3`
- Backend schema expects: `leadI`, `leadII`, `leadIII`
- Aggregator must map these correctly!

---

### Phase 4: Handle Edge Cases

**Edge Case 1: Device disconnects mid-buffer**
- Buffer has 50 packets (5 seconds worth)
- Device disconnects
- **Solution:** Call `cleanupDevice()` to discard partial buffer

**Edge Case 2: Mode switch during aggregation**
- Buffer starts in ECG mode
- Device switches to EEG mode mid-buffer
- **Solution:** Detect mode change, store partial buffer, start new buffer

**Edge Case 3: Packet loss**
- MQTT packet lost
- Buffer has gaps
- **Solution:** For now, accept partial data. Future: add sequence number validation

**Edge Case 4: Backend restart**
- In-memory buffers lost
- **Solution:** Acceptable for now. Future: persist to Redis for recovery

---

## TESTING PLAN

### Test 1: Basic Aggregation Flow
**Steps:**
1. Ensure ESP32 is publishing to `/stream` (already working)
2. Deploy backend changes
3. Monitor logs for aggregation messages
4. Wait 10 seconds
5. Query database: `SELECT COUNT(*) FROM waveform_snapshots;`
6. **Expected:** Should show 1 row per 10 seconds

**SQL Verification:**
```sql
SELECT
    time,
    "patientId",
    "deviceId",
    mode,
    duration,
    "sampleRate",
    "ecgLimbLeads" IS NOT NULL as has_ecg_data
FROM waveform_snapshots
ORDER BY time DESC
LIMIT 10;
```

### Test 2: Data Integrity
**Steps:**
1. Extract one snapshot from database
2. Decompress delta encoding
3. Verify 5000 samples per lead
4. Spot-check sample values (should be in valid range)

**Sample Validation:**
- ECG: -2048 to +2047 (12-bit ADC)
- EEG: -2048 to +2047

### Test 3: Multiple Devices
**Steps:**
1. Connect 2-3 ESP32 watches
2. Verify each gets separate buffer
3. Verify each stores snapshots independently

### Test 4: Device Disconnect
**Steps:**
1. Start aggregation (50 packets buffered)
2. Disconnect ESP32
3. Verify buffer cleanup in logs
4. Verify no crash or memory leak

---

## ROLLBACK PLAN

**If aggregation fails:**
1. Comment out aggregation call in `_handleWaveformStream()`
2. Backend returns to WebSocket-only mode
3. No data loss (real-time streaming unaffected)

**Code to disable:**
```python
# In _handleWaveformStream():
# await self.waveformAggregator.addStreamPacket(...)  # DISABLED
```

---

## FILES TO MODIFY

### New Files (1):
1. `hospital-backend/app/services/waveform_aggregator.py` (NEW)

### Modified Files (1):
1. `hospital-backend/app/services/mqtt_service.py` (3 small changes)

### Database:
- No schema changes needed ✅
- Table `waveform_snapshots` already exists (migration 010)

---

## ESTIMATED EFFORT

- **Implementation:** 1-2 hours
- **Testing:** 30 minutes
- **Documentation:** 30 minutes
- **Total:** 2-3 hours

---

## SUCCESS CRITERIA

✅ Backend aggregates 100 `/stream` packets into 10-second snapshots
✅ `waveform_snapshots` table populates every 10 seconds
✅ Data integrity verified (5000 samples per lead)
✅ Delta encoding applied correctly
✅ No memory leaks or crashes
✅ Real-time streaming unaffected (WebSocket still works)
✅ Device disconnect handled gracefully

---

## RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| Memory leak from orphaned buffers | High | Implement `cleanupDevice()` on disconnect |
| Lead name mismatch (lead1 vs leadI) | High | Add mapping in aggregator |
| Backend restart loses buffers | Medium | Acceptable for MVP, add Redis later |
| Packet loss causes incomplete snapshots | Low | Accept partial data for now |
| Database write errors | Medium | Add error handling and retry logic |

---

## NEXT STEPS

1. **User Approval:** Get approval for this plan
2. **Implementation:** Create `waveform_aggregator.py`
3. **Integration:** Modify `mqtt_service.py`
4. **Testing:** Verify database storage
5. **Documentation:** Update system architecture docs

---

## QUESTIONS FOR USER

1. **Partial buffer handling:** If device disconnects with 50 packets buffered (5 seconds), should we:
   - A) Discard partial buffer (current plan)
   - B) Store 5-second snapshot anyway

2. **Buffer size:** Use 100 packets (10s) or make configurable (e.g., 50 packets = 5s snapshots)?

3. **Mode switch handling:** If device switches ECG↔EEG mid-buffer, should we:
   - A) Discard partial buffer and start fresh
   - B) Store partial buffer before mode switch

4. **Redis for buffer persistence:** Add now or later?

---

## APPROVAL CHECKLIST

Before proceeding with implementation, confirm:

- [ ] User approves backend aggregation approach
- [ ] User approves 10-second snapshot duration
- [ ] User approves discarding partial buffers on disconnect
- [ ] User approves no ESP32 firmware changes
- [ ] User ready to proceed with implementation
