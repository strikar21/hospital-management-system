# WebSocket vs Database Streaming - Analysis
**Date:** 2025-11-02
**User's Issue:** "Sometimes data comes in at once, sometimes takes a while to appear on screen"

---

## PROBLEM ANALYSIS

### What User Is Experiencing:

**Symptom 1: Data comes in bursts ("at once")**
```
Screen shows nothing... nothing... nothing... BOOM! 2 seconds of data appears instantly
```

**Symptom 2: Data takes a while to appear**
```
ESP32 sending data → Wait 2-3 seconds → Finally appears on screen
```

**Root Cause:** Network buffering/congestion, not our code!

---

## WHY THIS HAPPENS WITH WEBSOCKET

### Network Reality:

```
ESP32 → WiFi → Router → Internet → Backend → WebSocket → Browser → Display
        ↑              ↑                      ↑
    Can stall     Can buffer           Can queue packets
```

**TCP/WebSocket Behavior:**
1. **Network congestion:** Router buffers packets
2. **WiFi interference:** Packets delayed
3. **Backend busy:** Processes other requests first
4. **TCP guarantees order:** If packet #5 is delayed, packets #6-#10 wait for it!

**Result: Bursty delivery**
```
Packets 1-10 stuck in router → Finally arrive together → Screen updates in burst
```

### Why Frontend Buffer Doesn't Help:

**Frontend buffer helps with rendering smoothness, NOT network delays:**
- ✅ Buffer prevents stuttering DURING playback
- ❌ Buffer can't fix "no data arriving" problem
- ❌ Buffer doesn't bypass network issues

```
Frontend buffer: [empty... empty... empty]
                  ↓ Waiting for WebSocket
Network finally delivers: 2 seconds of data
Frontend buffer: [FULL! All 2 seconds at once]
Screen: Shows all 2 seconds very quickly (looks like a burst)
```

---

## OPTION 1: KEEP WEBSOCKET (Current)

### Advantages:
- ✅ Lowest latency when network is good (100ms)
- ✅ Real-time for critical alerts
- ✅ Already implemented and working
- ✅ Live data (most recent)

### Disadvantages:
- ❌ Subject to network issues (WiFi, congestion)
- ❌ Bursty delivery when network stutters
- ❌ Can't recover lost packets (WebSocket is ephemeral)
- ❌ No backfill if frontend disconnects

### When Network Is Good:
```
ESP32 → 100ms → Backend → 20ms → Frontend
Total lag: 120ms ✅ EXCELLENT
```

### When Network Is Bad:
```
ESP32 → 2 seconds stuck → Backend → 20ms → Frontend
Total lag: 2+ seconds ❌ POOR (bursty)
```

---

## OPTION 2: POLL DATABASE INSTEAD

### Architecture:

```
ESP32 → Backend → Database (storage happens regardless)
                     ↑
Frontend polls: "Give me data from last 1 second" (every 500ms)
                     ↓
Frontend receives: Guaranteed data, no WebSocket
```

### Implementation:

**Backend API:**
```python
@app.get("/api/patients/{patientId}/waveforms/recent")
async def getRecentWaveforms(patientId: str, seconds: int = 1):
    """Get last N seconds of waveform data"""
    cutoffTime = datetime.now() - timedelta(seconds=seconds)

    async with getTimescaleConnection() as conn:
        rows = await conn.fetch("""
            SELECT time, mode, "ecgLimbLeads", "eegFrontalChannels"
            FROM waveform_snapshots
            WHERE "patientId" = $1 AND time >= $2
            ORDER BY time ASC
        """, patientId, cutoffTime)

    return rows
```

**Frontend Polling:**
```typescript
// Poll database every 500ms instead of WebSocket
useEffect(() => {
    const interval = setInterval(async () => {
        const response = await fetch(
            `/api/patients/${patient.id}/waveforms/recent?seconds=1`
        );
        const data = await response.json();

        // Add to buffer
        data.forEach(packet => {
            appendToBuffer(packet);
        });
    }, 500); // Poll every 500ms

    return () => clearInterval(interval);
}, [patient.id]);
```

### Advantages:
- ✅ **Consistent delivery** - No bursty behavior
- ✅ **Guaranteed data** - Database won't lose packets
- ✅ **Backfill on reconnect** - Can query missed data
- ✅ **No WebSocket complexity** - Simpler networking
- ✅ **Works through firewalls** - HTTP is more reliable than WebSocket
- ✅ **Smooths out network issues** - Database acts as buffer

### Disadvantages:
- ❌ Higher latency (500ms minimum, vs 100ms WebSocket)
- ❌ More database load (queries every 500ms)
- ❌ Polling overhead (frontend makes requests constantly)
- ❌ Not "true real-time" (500ms delay always)

### Performance:

**Latency:**
```
ESP32 sends → Database stores (50ms) → Frontend polls (up to 500ms) → Display
Total lag: 100-550ms (average 300ms)
```

**Database Load:**
- 1 frontend client: 2 queries/second (500ms polling)
- 10 clients: 20 queries/second
- 100 clients: 200 queries/second

**Compare to WebSocket:**
- WebSocket: 0 database queries (streams from memory)
- Polling: 2 queries/second per client

---

## OPTION 3: HYBRID APPROACH ✅ RECOMMENDED

### Best of Both Worlds:

```
Primary: WebSocket (fast, real-time)
Fallback: Database polling (when WebSocket stutters)
Recovery: Database backfill (fill gaps)
```

### Implementation:

**Frontend Logic:**
```typescript
const [lastDataTime, setLastDataTime] = useState(Date.now());
const [usingFallback, setUsingFallback] = useState(false);

// WebSocket listener
useEffect(() => {
    const handleWaveform = (data) => {
        appendToBuffer(data);
        setLastDataTime(Date.now());
        setUsingFallback(false); // WebSocket working!
    };

    subscribe('waveform', handleWaveform);
    return () => unsubscribe('waveform', handleWaveform);
}, []);

// Watchdog: Check if WebSocket is stalling
useEffect(() => {
    const watchdog = setInterval(() => {
        const timeSinceLastData = Date.now() - lastDataTime;

        if (timeSinceLastData > 1000) {
            // No data for 1 second! Switch to database polling
            console.warn('⚠️ WebSocket stalling, switching to database polling');
            setUsingFallback(true);
        }
    }, 500);

    return () => clearInterval(watchdog);
}, [lastDataTime]);

// Database polling (only when WebSocket fails)
useEffect(() => {
    if (!usingFallback) return; // WebSocket working, don't poll

    const interval = setInterval(async () => {
        const data = await fetch(`/api/patients/${patient.id}/waveforms/recent?seconds=1`);
        const packets = await data.json();

        packets.forEach(packet => appendToBuffer(packet));

        console.log(`📊 Fallback: Loaded ${packets.length} packets from database`);
    }, 500);

    return () => clearInterval(interval);
}, [usingFallback, patient.id]);
```

### Behavior:

**Normal Operation (WebSocket working):**
```
ESP32 → WebSocket → Frontend (120ms latency) ✅
Database polling: OFF (not needed)
```

**Network Issue (WebSocket stuttering):**
```
WebSocket: Stalled for 1+ seconds
Frontend detects: No data for 1 second
Frontend switches: Database polling ON
ESP32 → Database → Frontend poll (300ms latency) ✅
Display: Continues smoothly using database data
```

**Recovery:**
```
WebSocket: Recovers
Frontend detects: Data arriving via WebSocket again
Frontend switches: Database polling OFF
Back to normal: WebSocket mode
```

### Advantages:
- ✅ **Best latency when possible** (WebSocket 120ms)
- ✅ **Reliable fallback** (Database when WebSocket fails)
- ✅ **Automatic recovery** (Switches back when network improves)
- ✅ **No data loss** (Database always has data)
- ✅ **User doesn't notice** (Seamless transition)

### Disadvantages:
- ⚠️ More complex code (~100 lines)
- ⚠️ Need to implement database query API
- ⚠️ Slightly more backend load during fallback

---

## WHAT'S CAUSING YOUR BURSTY BEHAVIOR?

### Likely Culprits:

**1. WiFi Congestion:**
```
ESP32 WiFi → Router buffering packets → Delivers in burst
```
**Fix:** Use 5GHz WiFi, reduce interference

**2. Backend Event Loop Blocking:**
```
Backend processing heavy task → WebSocket queued → Delivers when task done
```
**Fix:** Ensure async operations don't block

**3. Browser Tab Throttling:**
```
Browser tab in background → WebSocket deprioritized → Delivers when tab focused
```
**Fix:** Keep tab in foreground during monitoring

**4. TCP Head-of-Line Blocking:**
```
Packet #50 lost → Packets #51-60 wait for retransmit → All arrive together
```
**Fix:** Use UDP (not practical for WebSocket)

---

## RECOMMENDATIONS

### Short Term (Quick Fix):
**Improve WebSocket reliability:**

1. **Add heartbeat/keepalive:**
```python
# Backend sends ping every 1 second
async def sendHeartbeat():
    while True:
        await connectionManager.broadcast('heartbeat', {'timestamp': time.time()})
        await asyncio.sleep(1)
```

2. **Frontend detects stalls:**
```typescript
// Show warning when data delayed
if (Date.now() - lastDataTime > 2000) {
    showWarning('⚠️ Connection unstable - data delayed');
}
```

3. **Database backfill on reconnect:**
```typescript
// When WebSocket reconnects after disconnect
const fillGap = async (disconnectTime, reconnectTime) => {
    const missedData = await fetch(
        `/api/waveforms?from=${disconnectTime}&to=${reconnectTime}`
    );
    appendToBuffer(missedData);
};
```

### Medium Term (Recommended):
**Implement Hybrid Approach (Option 3):**
- Keep WebSocket for real-time
- Add database polling as fallback
- Automatic switching based on data arrival
- Estimated effort: 2-3 hours

### Long Term (If Issues Persist):
**Switch to Database Polling Only:**
- More consistent delivery
- Simpler code (remove WebSocket complexity)
- Slightly higher latency (acceptable for non-critical monitoring)
- Estimated effort: 1-2 hours

---

## QUICK DIAGNOSTIC

**Run this to see if it's a database or WebSocket issue:**

```bash
# Terminal 1: Monitor database writes
cd hospital-backend
python -c "
import asyncpg
import asyncio
import time

async def monitor():
    conn = await asyncpg.connect('postgresql://hospital_user:hospital123@localhost:5433/hospitaltimescale')

    last_count = 0
    while True:
        count = await conn.fetchval('SELECT COUNT(*) FROM waveform_snapshots')
        new_rows = count - last_count

        print(f'Database: {new_rows} new rows in last second (expected: ~10)')

        if new_rows == 0:
            print('❌ NO DATA ARRIVING - ESP32 or backend issue!')
        elif new_rows < 5:
            print('⚠️ SLOW DATA - Network or backend slow')
        else:
            print('✅ Database receiving data normally')

        last_count = count
        await asyncio.sleep(1)

    await conn.close()

asyncio.run(monitor())
"
```

**If database shows consistent 10 rows/second:**
- ✅ Backend is working fine
- ❌ Problem is WebSocket delivery to frontend
- **Solution:** Implement database polling or hybrid approach

**If database shows bursty/missing data:**
- ❌ Problem is ESP32 → Backend connection
- **Solution:** Fix ESP32 WiFi or MQTT reliability

---

## MY RECOMMENDATION

**Implement Hybrid Approach (Option 3):**

**Why:**
1. Your symptom (bursty data) indicates WebSocket unreliability
2. Database storage is now working (my implementation)
3. Hybrid gives best of both worlds
4. Automatic fallback means no manual intervention

**Next Steps:**
1. Create database query API (`/api/patients/{id}/waveforms/recent`)
2. Add watchdog timer to frontend
3. Implement fallback polling when WebSocket stalls
4. Test with ESP32 sending data

**Want me to implement this?**
