# Real-Time Waveform Streaming Architecture
**Continuous ECG/EEG Data Streaming - No Batching**

Generated: 2025-10-22
Based on: Existing WebSocket infrastructure + ESP32 hardware capabilities

---

## Current Architecture Analysis

### ✅ What We Already Have:

**1. Backend WebSocket Manager** ([websocket_manager.py](hospital-backend/app/services/websocket_manager.py))
- ✅ Real-time vitals streaming to frontend
- ✅ Patient-specific subscriptions
- ✅ Connection management
- ✅ Keepalive pings (30 sec)
- ✅ Alert broadcasting

**2. Frontend WebSocket Client**
- ✅ Subscribes to patient updates
- ✅ Receives vitals in real-time
- ✅ Displays on patient cards

### ❌ What's Missing for Waveform Streaming:

**1. Waveform-specific WebSocket channel**
- Current: Only vitals updates (HR, SpO2, temp every 1 sec)
- Needed: Continuous waveform samples (250-500 Hz)

**2. ESP32 → Backend transport**
- Current: MQTT with 1-sec vitals batches
- Needed: High-frequency waveform streaming

**3. Frontend waveform renderer**
- Current: Number displays (HR: 75)
- Needed: Real-time waveform canvas/chart

---

## Real-Time Streaming Architecture Options

### Option 1: ESP32 → MQTT → Backend → WebSocket → Frontend

```
┌─────────────┐
│  ESP32      │
│  (500 Hz)   │  MQTT: hospital/devices/{deviceId}/stream
└──────┬──────┘  (continuous small packets, 10-50 samples each)
       │
       │  50-100ms packets (25-50 samples)
       ▼
┌─────────────────┐
│  MQTT Broker    │
│  (Mosquitto)    │
└──────┬──────────┘
       │
       │  Subscribe to stream topic
       ▼
┌─────────────────────────┐
│  Backend MQTT Service   │
│  (mqtt_service.py)      │
└──────┬──────────────────┘
       │
       │  Parse waveform packet
       ▼
┌──────────────────────────┐
│  WebSocket Manager       │
│  (websocket_manager.py)  │
└──────┬───────────────────┘
       │
       │  Broadcast to subscribers
       ▼
┌─────────────────┐
│  Frontend       │
│  (Web/Display)  │
│  Canvas Render  │
└─────────────────┘
```

**Pros:**
- Uses existing MQTT infrastructure
- ESP32 → Backend proven (already working for vitals)
- Backend can store snapshots to TimescaleDB
- Multiple frontends can subscribe

**Cons:**
- Double network hop (MQTT → WebSocket)
- Slight latency (~50-100ms extra)
- MQTT broker handles high message rate

---

### Option 2: ESP32 → MQTT → Backend → WebSocket (Aggregated)

```
ESP32 sends: 50ms packets (25 samples @ 500 Hz)
Backend aggregates: Buffers 200ms (4 packets = 100 samples)
Backend broadcasts: Every 200ms via WebSocket
```

**Pros:**
- Reduces WebSocket message rate
- Smoother rendering (less jitter)
- Lower frontend CPU usage

**Cons:**
- 200ms latency added by buffering
- Not truly "real-time" (200ms delay)

---

### Option 3: ESP32 → WebSocket Direct (Bypass MQTT)

```
┌─────────────┐
│  ESP32      │
│  (500 Hz)   │  WebSocket: wss://server:8001/ws/stream/{deviceId}
└──────┬──────┘  (continuous small packets)
       │
       │  Direct WebSocket connection
       ▼
┌─────────────────────────┐
│  Backend WebSocket API  │
│  (FastAPI endpoint)     │
└──────┬──────────────────┘
       │
       │  Fan-out to multiple subscribers
       ▼
┌─────────────────┐
│  Frontend(s)    │
│  Display Tabs   │
└─────────────────┘
```

**Pros:**
- **Lowest latency** (~10-20ms)
- No MQTT overhead
- True real-time streaming
- Bidirectional (backend can request config changes)

**Cons:**
- ESP32 must maintain WebSocket connection (more battery drain)
- No MQTT benefits (message queuing, QoS)
- All-or-nothing (if WebSocket drops, data lost)

---

## Recommended Hybrid Architecture

### Best of Both Worlds:

```
┌─────────────┐
│  ESP32      │
│  ADS1298    │
│  500 Hz ADC │
└──────┬──────┘
       │
       ├─ MQTT: hospital/devices/{id}/vitals (1/sec)
       │  └─> Basic vitals + metadata (HR, temp, battery)
       │       Stored in TimescaleDB vitals_realtime
       │
       └─ MQTT: hospital/devices/{id}/stream (20/sec = 50ms packets)
          └─> Raw waveform samples (25 samples × 3-8 channels)
              NOT stored, just forwarded to WebSocket

┌─────────────────┐
│  MQTT Broker    │
└──────┬──────────┘
       │
       ▼
┌──────────────────────────────┐
│  Backend MQTT Service        │
│  ├─ /vitals → TimescaleDB    │
│  └─ /stream → WebSocket only │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────┐
│  WebSocket Manager       │
│  broadcastWaveformStream()│
└──────┬───────────────────┘
       │
       ▼
┌─────────────────┐
│  Frontend       │
│  Real-time Plot │
└─────────────────┘
```

**Advantages:**
- **MQTT for vitals** (reliable, stored, 1/sec)
- **MQTT for waveforms** (real-time, ephemeral, 20/sec)
- **WebSocket fan-out** (multiple displays subscribe to same patient)
- **Selective storage** (Store vitals + 1-minute waveform snapshots, not continuous stream)

---

## Message Format - Real-Time Streaming

### ESP32 Waveform Stream Message (50ms packet)

**MQTT Topic:** `hospital/devices/{deviceId}/stream`
**Frequency:** 20/sec (every 50ms)
**Payload Size:** 300-800 bytes (depending on channel count)

```json
{
  "deviceId": "fit-00001",
  "patientId": "PAT12345",
  "timestamp": "2025-10-22T14:32:15.050Z",
  "mode": "ecg",
  "sampleRate": 500,
  "sequence": 12345,
  "samples": {
    "leadI": [8388608, 8388610, 8388607, ...],     // 25 samples (50ms @ 500 Hz)
    "leadII": [8388610, 8388612, 8388609, ...],    // 25 samples
    "leadIII": [8388605, 8388607, 8388604, ...]    // 25 samples
  }
}
```

**Key Points:**
- **No delta encoding** for streaming (need absolute values for real-time rendering)
- **Small packets** (25 samples = 50ms worth of data)
- **High frequency** (20 messages/sec)
- **Sequence number** for lost packet detection

---

### WebSocket Waveform Stream to Frontend

**WebSocket Message Type:** `waveformStream`

```json
{
  "type": "waveformStream",
  "patientId": "PAT12345",
  "deviceId": "fit-00001",
  "timestamp": "2025-10-22T14:32:15.050Z",
  "mode": "ecg",
  "sampleRate": 500,
  "sequence": 12345,
  "samples": {
    "leadI": [8388608, 8388610, 8388607, ...],
    "leadII": [8388610, 8388612, 8388609, ...],
    "leadIII": [8388605, 8388607, 8388604, ...]
  }
}
```

---

## Bandwidth Analysis - Real-Time Streaming

### Message Size Calculation

**Per-sample storage:**
- Raw int32: 4 bytes
- JSON number: ~7 bytes (includes formatting overhead)

**50ms packet (25 samples per channel):**

| Config | Channels | Samples | JSON Size | Overhead | Total |
|--------|----------|---------|-----------|----------|-------|
| **1-lead** | 1 | 25 | 175 bytes | 150 bytes | **325 bytes** |
| **3-lead** | 3 | 75 | 525 bytes | 150 bytes | **675 bytes** |
| **5-lead** | 5 | 125 | 875 bytes | 150 bytes | **1,025 bytes** |
| **8-lead** | 8 | 200 | 1,400 bytes | 150 bytes | **1,550 bytes** |
| **12-lead** | 8 phys | 200 | 1,400 bytes | 150 bytes | **1,550 bytes** |

---

### Bandwidth Per Device

| Config | Message Size | Freq | Data Rate | MB/Day | MB/Month |
|--------|--------------|------|-----------|--------|----------|
| **1-lead** | 325 bytes | 20/sec | 52 Kbps | 562 MB | 16.86 GB |
| **3-lead** | 675 bytes | 20/sec | 108 Kbps | 1,166 MB | 34.98 GB |
| **5-lead** | 1,025 bytes | 20/sec | 164 Kbps | 1,771 MB | 53.13 GB |
| **8-lead** | 1,550 bytes | 20/sec | 248 Kbps | 2,678 MB | 80.34 GB |
| **12-lead** | 1,550 bytes | 20/sec | 248 Kbps | 2,678 MB | 80.34 GB |

**Worst-case: 80 GB/month per device** ❌ **TOO MUCH!**

---

### Comparison: Batched vs Streaming

| Approach | Packet Size | Freq | MB/Day | MB/Month |
|----------|-------------|------|--------|----------|
| **200ms batches** | 1,212 bytes | 5/sec | 532 MB | 15.96 GB |
| **Real-time stream (50ms)** | 1,550 bytes | 20/sec | 2,678 MB | 80.34 GB |
| **Increase:** | | **4×** | **5×** | **5×** |

**Problem:** Real-time streaming uses 5× more bandwidth than 200ms batches!

---

## Solution: Smart Streaming Strategy

### Hybrid: Stream + Snapshot Storage

```
ESP32 generates 500 Hz continuous stream
  ├─> MQTT stream (50ms packets, 20/sec) → WebSocket → Frontend display
  │   └─> NOT stored in database (ephemeral)
  │
  └─> MQTT snapshot (1-sec packets, 1/sec) → TimescaleDB
      └─> Stored for historical analysis, alerts, archival
```

**Benefits:**
- Frontend sees real-time waveform (50ms latency)
- Database stores only 1-sec snapshots (1/20th the data)
- Historical playback available (from snapshots)
- Alerts run on snapshots (backend analysis)

**Bandwidth:**
- **Stream:** 2,678 MB/day (ephemeral, not stored)
- **Snapshots:** 233 MB/day (stored in TimescaleDB)
- **Network:** Full bandwidth needed
- **Storage:** Only 233 MB/day

---

## ESP32 Hardware Feasibility - Real-Time Streaming

### Memory Requirements

**Streaming Buffer (50ms window):**

| Config | Channels | 50ms @ 500Hz | Buffer Size |
|--------|----------|--------------|-------------|
| **1-lead** | 1 | 25 samples | 100 bytes ✅ |
| **3-lead** | 3 | 75 samples | 300 bytes ✅ |
| **8-lead** | 8 | 200 samples | 800 bytes ✅ |

**No circular buffer needed** - just send samples immediately after ADC read!

---

### CPU Load

**Every 2ms (500 Hz sampling):**
1. ADS1298 interrupt fires
2. Read 8 channels via SPI (~100 μs)
3. Store in 50ms buffer (~10 μs)
4. Check if 50ms elapsed (25 samples collected)
5. If yes: Serialize JSON + MQTT publish (~20 ms)

**CPU time per second:**
- Sampling: 500 × 110 μs = 55 ms/sec (5.5%)
- JSON + MQTT: 20 × 20 ms = 400 ms/sec (40%)
- **Total: 45.5% CPU** ✅ Feasible

---

### Battery Life (Real-Time Streaming)

**500 mAh battery, 8-lead streaming (20 msg/sec):**

```
Active WiFi time: 20 × 20ms = 400 ms/sec
Sleep time: 600 ms/sec

Active power: 400 ms × 200 mA = 80 mA-ms
Sleep power: 600 ms × 22 mA = 13.2 mA-ms
Average: (80 + 13.2) / 1000 = 93.2 mA

Battery life: 500 mAh / 93.2 mA = 5.4 hours
```

❌ **Only 5.4 hours!** Need 4-5 charges per day or plug-in power

**Solution:** Critical patients on real-time streaming = plug-in power (standard in ICU/ER)

---

## Network Feasibility - 500 Devices

### WiFi Access Point Load

**500 devices, 8-lead streaming:**
```
Per device: 248 Kbps
500 devices: 124 Mbps
```

**802.11ac WiFi AP:** 600-1300 Mbps capacity
**Load:** 124 / 600 = **21% of WiFi capacity** ✅ Feasible

**Recommendation:** 5 APs (100 devices each) for redundancy = 4% per AP ✅

---

### MQTT Broker Load

**500 devices × 20 msg/sec = 10,000 msg/sec**

**Mosquitto capacity:** 100,000+ msg/sec
**Load:** 10% ✅ Feasible

---

### WebSocket Fan-Out

**Scenario:** 50 display tablets, each watching 10 patients

```
50 tablets × 10 patients × 1,550 bytes/50ms = 15.5 MB/sec = 124 Mbps
```

**Backend server (1 Gbps NIC):** 124 / 1000 = 12.4% ✅ Feasible

---

### Database Storage (Snapshots Only)

**500 devices, 1-sec snapshots (not stream):**
```
500 × 233 MB/day = 116.5 GB/day = 3.5 TB/month
```

**TimescaleDB with compression:** 3.5 TB → ~1 TB compressed ✅ Feasible

---

## Frontend Rendering Feasibility

### Canvas Rendering Performance

**JavaScript Canvas (HTML5):**
- Can handle 1000+ points/sec easily
- 500 Hz = 500 points/sec per channel
- 8 channels = 4,000 points/sec ✅ No problem

**Optimization:**
- Use requestAnimationFrame() for smooth 60 FPS
- Ring buffer (only render last 10 seconds = 5,000 points)
- WebGL for >10 channels (if needed)

---

## Implementation Plan - Real-Time Streaming

### Phase 1: ESP32 Streaming (2 weeks)

**Changes needed:**

```cpp
// New global variables
#define STREAM_INTERVAL_MS 50  // Send every 50ms
unsigned long lastStreamTime = 0;
int32_t streamBuffer[8][25];  // 25 samples × 8 channels
int streamBufferIndex = 0;

// In ADS1298 interrupt (every 2ms @ 500 Hz)
void onDataReady() {
  // Read all 8 channels
  for (int ch = 0; ch < 8; ch++) {
    streamBuffer[ch][streamBufferIndex] = ADS1298_readChannel(ch);
  }

  streamBufferIndex++;

  // Check if 50ms elapsed (25 samples collected)
  if (streamBufferIndex >= 25) {
    // Send stream packet
    sendWaveformStream();
    streamBufferIndex = 0;
  }
}

void sendWaveformStream() {
  String topic = "hospital/devices/" + deviceId + "/stream";

  JsonDocument doc;
  doc["deviceId"] = deviceId;
  doc["patientId"] = assignedPatientId;
  doc["timestamp"] = getISO8601Timestamp();
  doc["mode"] = digitalRead(MODE_SELECT_PIN) == HIGH ? "ecg" : "eeg";
  doc["sampleRate"] = 500;
  doc["sequence"] = streamSequence++;

  JsonObject samples = doc.createNestedObject("samples");

  bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;
  if (isECGMode) {
    // Add active leads based on config
    if (activeLeads >= 1) {
      JsonArray leadI = samples.createNestedArray("leadI");
      for (int i = 0; i < 25; i++) leadI.add(streamBuffer[0][i]);
    }
    if (activeLeads >= 2) {
      JsonArray leadII = samples.createNestedArray("leadII");
      for (int i = 0; i < 25; i++) leadII.add(streamBuffer[1][i]);
    }
    if (activeLeads >= 3) {
      JsonArray leadIII = samples.createNestedArray("leadIII");
      for (int i = 0; i < 25; i++) leadIII.add(streamBuffer[2][i]);
    }
    // ... additional leads based on activeLeads config
  }

  String payload;
  serializeJson(doc, payload);
  mqttClient.publish(topic.c_str(), payload.c_str());
}
```

---

### Phase 2: Backend MQTT → WebSocket Bridge (1 week)

**Add to `mqtt_service.py`:**

```python
async def onMqttMessage(self, topic: str, payload: dict):
    # Existing vitals handler
    if topic.endswith("/vitals"):
        await self._handleVitals(payload)

    # NEW: Stream handler
    elif topic.endswith("/stream"):
        await self._handleWaveformStream(payload)

async def _handleWaveformStream(self, payload: dict):
    """Forward waveform stream to WebSocket subscribers (NO DATABASE)"""
    from .websocket_manager import connectionManager

    patientId = payload.get('patientId')
    deviceId = payload.get('deviceId')

    # Validate device assignment (same as vitals)
    # ... check device is assigned to patient ...

    # Forward to WebSocket subscribers (ephemeral, not stored)
    await connectionManager.broadcastWaveformStream(patientId, payload)
```

**Add to `websocket_manager.py`:**

```python
async def broadcastWaveformStream(self, patientId: str, waveformData: Dict[str, Any]) -> int:
    """Broadcast real-time waveform stream to patient subscribers"""
    data = {
        'type': 'waveformStream',
        'patientId': patientId,
        'deviceId': waveformData.get('deviceId'),
        'timestamp': waveformData.get('timestamp'),
        'mode': waveformData.get('mode'),
        'sampleRate': waveformData.get('sampleRate'),
        'sequence': waveformData.get('sequence'),
        'samples': waveformData.get('samples')
    }

    sentCount = await self.broadcastToPatientSubscribers(patientId, data)
    # No logging here (too frequent - 20 msg/sec would spam logs)
    return sentCount
```

---

### Phase 3: Frontend Real-Time Renderer (2 weeks)

**Add WebSocket subscription for waveform stream:**

```typescript
// In patient detail view
useEffect(() => {
  const ws = new WebSocket(`ws://localhost:8001/ws/patient/${patientId}`);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === 'waveformStream') {
      updateWaveformCanvas(data.samples);
    }
  };

  return () => ws.close();
}, [patientId]);

// Canvas renderer
function updateWaveformCanvas(samples: any) {
  const canvas = canvasRef.current;
  const ctx = canvas.getContext('2d');

  // Shift existing waveform left
  const imageData = ctx.getImageData(25, 0, canvas.width - 25, canvas.height);
  ctx.putImageData(imageData, 0, 0);

  // Draw new samples on right edge
  ctx.clearRect(canvas.width - 25, 0, 25, canvas.height);

  // Draw 25 new samples
  samples.leadI.forEach((value, i) => {
    const x = canvas.width - 25 + i;
    const y = scaleValue(value);
    ctx.lineTo(x, y);
  });
  ctx.stroke();
}
```

---

## Selective Streaming Strategy (Recommended)

### Not All Patients Need Real-Time Streaming!

**Low-risk patients:** 1-sec batches (stored in DB)
**Medium-risk patients:** 1-sec batches (stored) + WebSocket forward
**High-risk patients:** 50ms real-time stream (ephemeral) + 1-sec snapshots (stored)

```
┌──────────────┐
│  ESP32 Watch │
└──────┬───────┘
       │
       │ Backend config determines mode:
       │
       ├─ Low-risk: /vitals only (1/sec)
       │
       ├─ Medium-risk: /vitals (1/sec) → WebSocket
       │
       └─ High-risk: /stream (20/sec) + /snapshot (1/sec)
                      └─ stream → WebSocket (ephemeral)
                      └─ snapshot → TimescaleDB (stored)
```

**Bandwidth savings:**
- 400 low-risk: 400 × 17 MB/day = 6.8 GB/day
- 80 medium-risk: 80 × 233 MB/day = 18.6 GB/day
- 20 high-risk streaming: 20 × 2,678 MB/day = 53.6 GB/day
- **Total: 79 GB/day** (vs 1,339 GB/day if all streaming)

**Cost savings:** 94% reduction by selective streaming ✅

---

## Summary - Real-Time Streaming Feasibility

### ✅ YES - Real-Time Streaming is Feasible!

**ESP32 Hardware:**
- ✅ Can send 20 msg/sec (50ms packets)
- ✅ CPU: 45% load (acceptable)
- ❌ Battery: Only 5.4 hours (need plug-in for streaming patients)

**Network (500 devices all streaming):**
- ✅ WiFi: 21% of AP capacity
- ✅ MQTT: 10% of broker capacity
- ✅ WebSocket: 12% of server bandwidth

**Storage:**
- ✅ Stream: Ephemeral (not stored)
- ✅ Snapshots: 1-sec snapshots stored (233 MB/day per device)

### 🎯 Recommended Approach:

**Selective Streaming:**
1. **Low-risk (80%):** 1-sec batches, database storage only
2. **Medium-risk (15%):** 1-sec batches + WebSocket forward
3. **High-risk (5%):** Real-time 50ms stream + 1-sec snapshots

**Result:**
- Real-time visualization for critical patients ✅
- Reasonable bandwidth (79 GB/day for 500 devices) ✅
- Historical data available (snapshots in DB) ✅
- Battery life acceptable (high-risk patients on plug-in power) ✅

**Doctor can enable real-time streaming per patient based on severity!**

---

**Ready to implement real-time streaming architecture?**
