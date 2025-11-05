# Frontend Pre-Buffering for Smooth Playback
**Date:** 2025-11-02
**User's Question:** "We should have 1-2 sec buffer in DB, so it feels smooth instead of waiting for data?"

---

## UNDERSTANDING THE REQUIREMENT

### What User Wants:
**Smooth playback experience when viewing historical ECG/EEG data**

Like YouTube:
- Click "Play" on a video
- Video starts immediately (not waiting 10 seconds to buffer)
- Plays smoothly without stuttering

### Two Different Scenarios:

#### Scenario 1: Real-Time Display (Live Monitoring)
```
Doctor opens patient monitor → Sees LIVE ECG immediately

Current: WebSocket pushes data continuously
Result: Already smooth! ✅ No buffering needed
```

#### Scenario 2: Historical Playback (Review Past Data)
```
Doctor clicks "Review last night's ECG at 2:30 AM"
Frontend requests: /api/waveforms?time=2025-11-01T02:30:00

Option A (No Pre-buffering):
- Request sent
- Wait for database query...
- Wait for network transfer...
- Display starts 2 seconds later ❌ FEELS SLOW

Option B (With Pre-buffering):
- Request sent
- Frontend receives 1-2 seconds of data
- Display starts IMMEDIATELY ✅ FEELS SMOOTH
- While playing, load more in background
```

**User is talking about Scenario 2!**

---

## WHERE SHOULD PRE-BUFFERING HAPPEN?

### Option A: Database Buffer (What User Suggested)
**"1-2 sec buffer in DB"**

**Interpretation:** Not sure what this means exactly. Let me explore:

**Possibility 1:** Database caches recent data in RAM
- TimescaleDB already does this automatically
- Recent data stays in memory (hot cache)
- Older data on disk (cold storage)
- **Already happening! No code needed.**

**Possibility 2:** Store data with 1-2 second delay
- ESP32 sends data
- Backend waits 1-2 seconds before storing
- **This doesn't help - makes queries slower!**

**Possibility 3:** Database pre-loads next chunks
- Not really a database feature
- This is application-level logic (frontend/backend)

---

### Option B: Frontend Buffer (Better Interpretation)
**"Frontend loads 1-2 seconds ahead while playing historical data"**

```
Doctor requests: "Show ECG from 10:00:00 to 10:10:00" (10 minutes)

Without Pre-buffering:
1. Frontend requests all 10 minutes
2. Wait for 6,000 packets (10 min × 10 packets/sec × 60 sec)
3. Wait for ~10 MB download
4. Display starts after 5 seconds ❌ SLOW

With Pre-buffering:
1. Frontend requests FIRST 2 seconds only
2. Get 20 packets (~36 KB)
3. Display starts IMMEDIATELY ✅ SMOOTH
4. While playing, request next 2 seconds in background
5. Seamless playback (like YouTube buffering)
```

---

## REAL-TIME VS HISTORICAL - DIFFERENT BUFFERING NEEDS

### Real-Time (WebSocket) - NO BUFFERING NEEDED
```
ESP32 → MQTT → Backend → WebSocket → Frontend

Data flow:
- Packet 1 arrives → Display immediately
- Packet 2 arrives (100ms later) → Display immediately
- Packet 3 arrives (100ms later) → Display immediately

Result: Smooth real-time rendering
Buffer: Frontend keeps ~1 second in canvas for sweep line
```

**Current Status: Already smooth! ✅**

---

### Historical Playback (HTTP API) - NEEDS BUFFERING

```
Frontend → Backend API → Database Query → Return Data → Display

Without Smart Loading:
- Request 10 minutes of data
- Wait for database query (2-3 seconds)
- Wait for JSON serialization (1-2 seconds)
- Wait for network transfer (2-3 seconds)
- Total: 5-8 seconds before anything displays ❌

With Smart Loading (Chunked + Pre-buffer):
- Request first 5 seconds of data
- Get data in 0.5 seconds
- Start displaying IMMEDIATELY ✅
- While displaying first 5 seconds, request next 10 seconds in background
- When playback reaches 5 seconds, next chunk already loaded
- Seamless playback
```

---

## IMPLEMENTATION OPTIONS

### Option 1: Backend Pagination (Simple)
**Backend returns data in chunks**

```python
# API endpoint
@app.get("/api/waveforms")
async def getWaveforms(
    patientId: str,
    startTime: datetime,
    limit: int = 50,  # Default: 5 seconds of data (50 packets)
    offset: int = 0
):
    """
    Returns paginated waveform data

    Example:
    - Request 1: /api/waveforms?startTime=10:00:00&limit=50&offset=0
      Returns: 10:00:00 - 10:00:05 (5 seconds)

    - Request 2: /api/waveforms?startTime=10:00:00&limit=50&offset=50
      Returns: 10:00:05 - 10:00:10 (next 5 seconds)
    """
    async with getTimescaleConnection() as conn:
        rows = await conn.fetch("""
            SELECT * FROM waveform_snapshots
            WHERE "patientId" = $1
              AND time >= $2
            ORDER BY time
            LIMIT $3 OFFSET $4
        """, patientId, startTime, limit, offset)

    return rows
```

**Frontend:**
```typescript
// Historical ECG viewer
async function playHistoricalECG(startTime: Date, duration: number) {
    let offset = 0;
    const chunkSize = 50; // 5 seconds

    // Load first chunk and start displaying IMMEDIATELY
    const firstChunk = await fetchWaveforms(startTime, chunkSize, offset);
    startPlayback(firstChunk);

    // While playing, pre-load next chunks
    offset += chunkSize;
    while (isPlaying) {
        const nextChunk = await fetchWaveforms(startTime, chunkSize, offset);
        bufferNextChunk(nextChunk); // Add to playback buffer
        offset += chunkSize;
        await sleep(4000); // Wait 4 seconds, load next chunk before current finishes
    }
}
```

**Result:**
- First chunk loads in 0.5 seconds
- Display starts immediately
- Next chunks load in background
- Smooth playback ✅

---

### Option 2: Backend Streaming (Advanced)
**Backend streams data chunk-by-chunk**

```python
@app.get("/api/waveforms/stream")
async def streamWaveforms(patientId: str, startTime: datetime):
    """
    Streams waveform data in real-time chunks
    Uses Server-Sent Events (SSE) or chunked transfer
    """
    async def generate():
        async with getTimescaleConnection() as conn:
            # Stream from database using cursor
            async with conn.transaction():
                async for row in conn.cursor("""
                    SELECT * FROM waveform_snapshots
                    WHERE "patientId" = $1 AND time >= $2
                    ORDER BY time
                """, patientId, startTime):
                    yield json.dumps(row) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")
```

**Frontend:**
```typescript
// Receive data as it arrives
const response = await fetch('/api/waveforms/stream?patientId=...');
const reader = response.body.getReader();

while (true) {
    const {done, value} = await reader.read();
    if (done) break;

    // Display chunk immediately as it arrives
    displayWaveformChunk(value);
}
```

**Result:**
- Data flows continuously from backend
- Frontend displays as it receives
- Very smooth, like YouTube adaptive streaming ✅

---

### Option 3: Frontend Circular Buffer (Like Real-Time Display)
**Reuse existing real-time buffering logic for historical data**

```typescript
// ECG Viewer already has circular buffer for real-time
class ECGWaveformCanvas {
    private buffer: number[][] = []; // 1-2 second circular buffer

    // Currently used for WebSocket data
    addRealtimeData(samples: number[]) {
        this.buffer.push(samples);
        if (this.buffer.length > 20) { // Keep 2 seconds (20 × 100ms)
            this.buffer.shift();
        }
        this.render();
    }

    // NEW: Also use for historical data
    async playHistoricalData(startTime: Date, endTime: Date) {
        // Load first 2 seconds
        const initialData = await fetchWaveforms(startTime, 20);

        // Fill buffer
        initialData.forEach(packet => this.addRealtimeData(packet.samples));

        // Start playback immediately (buffer has 2 seconds)
        this.startPlayback();

        // Load more in background
        let currentTime = startTime + 2 seconds;
        while (currentTime < endTime) {
            const nextChunk = await fetchWaveforms(currentTime, 20);
            nextChunk.forEach(packet => this.addRealtimeData(packet.samples));
            currentTime += 2 seconds;
        }
    }
}
```

**Result:**
- Reuses existing rendering code
- Smooth playback (same as real-time)
- 2-second buffer prevents stuttering ✅

---

## WHAT DOES "1-2 SEC BUFFER IN DB" MEAN?

### Interpretation 1: Database Query Strategy
**Query only what you need, when you need it**

```sql
-- Bad: Query 10 minutes at once (slow)
SELECT * FROM waveform_snapshots
WHERE time BETWEEN '10:00:00' AND '10:10:00';
-- Returns: 6,000 rows, takes 3 seconds

-- Good: Query 2 seconds at a time (fast)
SELECT * FROM waveform_snapshots
WHERE time BETWEEN '10:00:00' AND '10:00:02';
-- Returns: 20 rows, takes 0.1 seconds ✅
```

**This is backend pagination (Option 1 above)**

---

### Interpretation 2: TimescaleDB Memory Buffer
**Database keeps recent data in RAM**

TimescaleDB already does this:
- Recent data (last few minutes): In memory cache
- Older data: On disk (SSD)
- Query recent data: Fast (0.1 seconds)
- Query old data: Slower (1-2 seconds)

**No code needed - TimescaleDB handles automatically ✅**

---

### Interpretation 3: Frontend Pre-loads Ahead
**Like video buffering**

```
User viewing: 10:00:00 - 10:00:02 (currently visible on screen)
Frontend has: 10:00:00 - 10:00:04 (pre-loaded in memory)
                        ↑
                    2-second buffer ahead

When user scrolls to 10:00:03:
- Already in buffer! Displays immediately ✅
- Frontend requests next chunk: 10:00:04 - 10:00:06
```

**This is frontend buffering (Option 3 above)**

---

## RECOMMENDATION

### For Real-Time Display (Already Working)
**No changes needed!**
- WebSocket pushes data continuously
- Frontend circular buffer keeps 1-2 seconds
- Already smooth ✅

### For Historical Playback (What We're Adding Storage For)
**Implement chunked loading with frontend pre-buffer:**

**Backend (Simple Pagination):**
```python
@app.get("/api/waveforms")
async def getWaveforms(
    patientId: str,
    startTime: datetime,
    limit: int = 20  # 2 seconds of data
):
    # Return only 2 seconds at a time
    # Fast queries (0.1-0.2 seconds)
```

**Frontend (Pre-buffer 2 Seconds):**
```typescript
async function loadHistoricalECG(startTime: Date) {
    // Load first 2 seconds
    const firstChunk = await api.getWaveforms(startTime, 20);

    // Start displaying IMMEDIATELY
    displayECG(firstChunk);

    // Pre-load next 2 seconds while displaying
    const nextChunk = await api.getWaveforms(startTime + 2sec, 20);

    // Continue loading ahead as needed
}
```

**Result:**
- Click "View historical ECG" → Starts in 0.2 seconds ✅
- Smooth playback (pre-buffered) ✅
- Efficient (only load what's needed) ✅

---

## DOES THIS AFFECT OUR CURRENT IMPLEMENTATION PLAN?

**NO! Our plan remains the same:**

1. **Store every `/stream` packet to database** (what we're implementing now)
2. **Backend provides query API** (already exists)
3. **Frontend implements smart loading** (future enhancement)

**The "1-2 second buffer" is a FRONTEND feature, not database feature!**

---

## IMPLEMENTATION PHASES

### Phase 1: Enable Database Storage (NOW)
**File:** `mqtt_service.py`
```python
async def _handleWaveformStream(self, payload):
    await broadcastToWebSocket(payload)  # Real-time ✅
    await saveToDatabase(payload)        # Storage ✅ NEW
```

**Result:** Database starts collecting data

---

### Phase 2: Backend Pagination API (LATER - Maybe Already Exists?)
**Check if this exists:**
```python
@app.get("/api/waveforms")
async def getWaveforms(patientId, startTime, limit, offset):
    # Does this endpoint exist already?
```

**If not, add it (simple, ~20 lines)**

---

### Phase 3: Frontend Smart Loading (LATER)
**File:** `hospital-display-app/src/components/ECGViewer/`

Add chunked loading with 2-second pre-buffer

**Complexity:** Medium (50-100 lines)
**Benefit:** Smooth historical playback

---

## CONCLUSION

**User's request for "1-2 sec buffer" is a FRONTEND feature for smooth historical playback.**

**Does NOT change our current plan:**
- We still store every packet in real-time ✅
- Backend still provides query API ✅
- Frontend later adds smart buffering for smooth playback ✅

**Should we proceed with Phase 1 (database storage) now?**

The buffering logic can be added to frontend later as enhancement.
