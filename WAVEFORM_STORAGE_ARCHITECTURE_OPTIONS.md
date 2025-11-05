# Waveform Storage Architecture - Trade-off Analysis
**Date:** 2025-11-02
**Question:** Why send waveforms twice? Can't `/stream` be stored directly?

---

## USER'S EXCELLENT QUESTION

**"Why does watch need to store and send twice? Can't the `/stream` thing do the same? Aggregate and store to tables?"**

**Answer:** You're absolutely correct! We CAN aggregate `/stream` messages on the backend and store them. This is a better solution.

---

## CURRENT DESIGN (Root Cause Analysis Recommendation)

### What Backend Expects:
- `/stream` topic → Real-time WebSocket broadcast (NOT stored)
- `/waveform` topic → Database storage (10-second snapshots)

### ESP32 Current Behavior:
- Sends to `/stream` every 100ms (10 msg/sec, 50 samples each)
- Does NOT send to `/waveform` → **This is the gap!**

### Proposed Solution (Option A from root cause analysis):
- ESP32 publishes BOTH `/stream` and `/waveform`
- `/stream` = 100ms packets for real-time display
- `/waveform` = 10-second snapshots for archival

**Problem with this approach:**
- ❌ Redundant data transmission
- ❌ ESP32 sends same data twice (once in small packets, once in large snapshots)
- ❌ Wasted bandwidth and processing
- ❌ Unnecessary ESP32 battery drain

---

## BETTER SOLUTION: Backend Aggregation (USER'S SUGGESTION)

### Concept:
**Backend aggregates 100 × 50-sample `/stream` messages into 10-second snapshots and stores them**

### Advantages:
- ✅ ESP32 sends data ONCE (to `/stream` only)
- ✅ Backend does aggregation (has more power and memory than ESP32)
- ✅ No redundant MQTT messages
- ✅ Better battery life for ESP32
- ✅ Simpler ESP32 firmware (no additional code needed!)

### Implementation:
**Backend changes only - NO ESP32 changes needed!**

```python
# In mqtt_service.py

class WaveformAggregator:
    """Aggregate 100ms stream packets into 10-second snapshots"""

    def __init__(self):
        self.buffers = {}  # deviceId → {samples: [], startTime: datetime}

    def addStreamPacket(self, deviceId: str, streamMsg: Dict[str, Any]):
        """Add 50-sample packet to aggregation buffer"""
        if deviceId not in self.buffers:
            self.buffers[deviceId] = {
                'samples': [],
                'startTime': datetime.now(),
                'mode': streamMsg['mode'],
                'patientId': streamMsg['patientId']
            }

        buffer = self.buffers[deviceId]
        buffer['samples'].extend(streamMsg['ecgWaveform'] or streamMsg['eegWaveform'])

        # Check if we have 10 seconds worth (100 packets × 50 samples = 5000 samples)
        if len(buffer['samples']) >= 5000:
            # Create WaveformSnapshotMessage from aggregated data
            await self._storeAggregatedSnapshot(deviceId, buffer)

            # Clear buffer for next 10-second window
            del self.buffers[deviceId]

async def _handleWaveformStream(self, deviceId: str, payload: Dict[str, Any]):
    """
    Handle real-time waveform streaming packets
    NOW: Also aggregate for storage
    """
    # ... existing code for WebSocket broadcast ...

    # ✅ NEW: Aggregate for 10-second snapshot storage
    await waveformAggregator.addStreamPacket(deviceId, payload)
```

---

## COMPARISON TABLE

| Aspect | Option A (ESP32 sends twice) | Option B (Backend aggregation) |
|--------|------------------------------|--------------------------------|
| **ESP32 Firmware** | Needs new code | No changes needed ✅ |
| **MQTT Messages** | 10 msg/sec + 0.1 msg/sec | 10 msg/sec only ✅ |
| **Battery Drain** | Higher (more TX) | Lower ✅ |
| **Bandwidth** | Higher | Lower ✅ |
| **Backend Complexity** | Simple (just store) | Moderate (aggregation logic) |
| **Backend RAM** | Low | ~20KB per device |
| **Data Alignment** | Exact 10s windows | Exact 10s windows |
| **Implementation Time** | 2-3 hours (ESP32) | 1-2 hours (Backend) |

---

## RECOMMENDATION: **Option B - Backend Aggregation**

### Rationale:
1. **User is correct** - Sending data twice is wasteful
2. **Backend has resources** - Server has more RAM/CPU than ESP32
3. **Simpler overall** - No ESP32 firmware changes needed
4. **Better efficiency** - Lower battery drain, less bandwidth
5. **Already working** - `/stream` is proven and stable

### Trade-offs:
- Backend needs to maintain 10-second buffers in RAM (~20KB per active device)
- For 100 devices: ~2MB RAM (negligible for modern servers)
- Need to handle buffer cleanup on device disconnection

---

## IMPLEMENTATION PLAN - BACKEND AGGREGATION

### Step 1: Create WaveformAggregator class

**File:** `hospital-backend/app/services/waveform_aggregator.py`

```python
from datetime import datetime
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class WaveformAggregator:
    """
    Aggregates 100ms waveform stream packets into 10-second snapshots for database storage

    Design:
    - Collects 100 packets (50 samples each) = 5000 samples total
    - Creates WaveformSnapshotMessage when buffer full
    - Stores to TimescaleDB waveform_snapshots table
    """

    def __init__(self):
        self.buffers: Dict[str, Dict[str, Any]] = {}

    async def addStreamPacket(self, deviceId: str, patientId: str, streamPayload: Dict[str, Any]):
        """Add 50-sample stream packet to aggregation buffer"""
        if deviceId not in self.buffers:
            self.buffers[deviceId] = {
                'packets': [],
                'startTime': datetime.now(),
                'mode': streamPayload['mode'],
                'patientId': patientId,
                'deviceId': deviceId
            }

        buffer = self.buffers[deviceId]
        buffer['packets'].append(streamPayload)

        # Check if we have 100 packets (10 seconds worth)
        if len(buffer['packets']) >= 100:
            await self._createSnapshotFromBuffer(deviceId, buffer)
            del self.buffers[deviceId]

    async def _createSnapshotFromBuffer(self, deviceId: str, buffer: Dict[str, Any]):
        """Create and store 10-second waveform snapshot from aggregated packets"""
        # Combine 100 packets into single snapshot message
        # ... implementation details ...
        pass

    def cleanup Device(self, deviceId: str):
        """Remove buffer when device disconnects"""
        if deviceId in self.buffers:
            del self.buffers[deviceId]
```

### Step 2: Integrate into mqtt_service.py

```python
# Add to imports
from .waveform_aggregator import WaveformAggregator

# Add to MQTTService.__init__()
self.waveformAggregator = WaveformAggregator()

# Modify _handleWaveformStream()
async def _handleWaveformStream(self, deviceId: str, payload: Dict[str, Any]):
    # ... existing WebSocket broadcast code ...

    # ✅ NEW: Aggregate for 10-second snapshot storage
    await self.waveformAggregator.addStreamPacket(
        deviceId=deviceId,
        patientId=payload['patientId'],
        streamPayload=payload
    )
```

### Step 3: Testing
1. ESP32 sends `/stream` messages (already working)
2. Backend aggregates 100 packets
3. After 10 seconds, creates snapshot and stores to database
4. Verify `waveform_snapshots` table has rows

---

## FINAL DECISION

**Proceed with Option B (Backend Aggregation)**

- No ESP32 changes needed
- More efficient overall
- User's suggestion is architecturally superior
- Faster to implement (backend only)

**Next Step:** Implement `WaveformAggregator` class in backend
