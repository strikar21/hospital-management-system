# Research-Based WebSocket Issue Analysis
**Date:** 2025-11-02
**User's Issue:** "Data comes in bursts, sometimes takes a while to appear"

---

## ACTUAL RESEARCH CONDUCTED ✅

### 1. Backend API Endpoints (VERIFIED)

**No waveform query API exists:**
```bash
grep -r "waveform" hospital-backend/app/api/
# Result: NO MATCHES
```

**Existing APIs found:**
- `/api/v2/patients/{id}` - Patient data (NO waveforms)
- `/api/v1/ws/realtime` - WebSocket (realtime only)
- `/api/v1/nursing` - Has `recentVitals` query (vitals_realtime table)

**Conclusion:** We would need to CREATE waveform query API from scratch

---

### 2. Frontend WebSocket Implementation (VERIFIED)

**File:** `hospital-display-app/src/services/WebSocketService.ts`

**What I found:**
```typescript
// Line 44-49: Reconnection logic
private reconnectAttempts = 0;
private maxReconnectAttempts = 10;
private reconnectDelay = 1000; // Start at 1 second
private reconnectTimer: NodeJS.Timeout | null = null;
private heartbeatTimer: NodeJS.Timeout | null = null;

// Line 92-96: Auto-reconnect on connection loss
this.startHeartbeat();
this.resubscribePatients();  // Resubscribes after reconnect

// Line 124-126: Reconnect with exponential backoff
if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
    this.scheduleReconnect();
}

// Line 352-356: Heartbeat every 30 seconds
this.heartbeatTimer = setInterval(() => {
    if (this.isConnected()) {
        this.ws?.send(JSON.stringify({ type: 'ping' }));
    }
}, 30000);
```

**Features ALREADY implemented:**
- ✅ Auto-reconnect with exponential backoff
- ✅ Heartbeat (ping every 30s)
- ✅ Resubscribe patients on reconnect
- ✅ Connection state tracking

**What's missing:**
- ❌ No "data not arriving" detection
- ❌ No fallback when WebSocket stalls
- ❌ No data gap filling on reconnect

---

### 3. Frontend Buffer Implementation (VERIFIED)

**File:** `hospital-display-app/src/hooks/useECGViewer.ts`

```typescript
// Line 29: 10-second circular buffer
const dataBufferRef = useRef<number[][]>([]);

// Line 44: Reset buffer on mode change
dataBufferRef.current = Array(leads.length).fill(null).map(() => []);
```

**File:** `hospital-display-app/src/components/ECGViewer/ECGViewerContainer.tsx`

```typescript
// Line 80-82: Buffer overflow management
dataBufferRef.current.forEach((buffer, index) => {
    if (buffer.length > BUFFER_MAX_SAMPLES) {
        dataBufferRef.current[index] = buffer.slice(-BUFFER_MAX_SAMPLES);
```

**Buffer capacity:** 10 seconds of data (5000 samples @ 500Hz)

---

### 4. Database Storage Status (VERIFIED)

```bash
python -c "SELECT COUNT(*) FROM waveform_snapshots"
# Result: 0 rows
```

**Status:**
- ✅ Table exists
- ✅ Storage code added (my implementation)
- ❌ No data yet (ESP32 not sending, or backend not running)
- ❌ Cannot test query performance without data

---

## ACTUAL PROBLEM DIAGNOSIS

### User's Symptoms (Evidence):
1. "Data comes in at once" = Bursty delivery
2. "Data takes a while to appear" = Delayed arrival

### Possible Causes (Based on Research):

**1. WebSocket Reconnection Delay**
```typescript
// Line 337: Exponential backoff up to 30 seconds!
const delay = Math.min(
    this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
    30000  // Max 30 seconds
);
```

**If WebSocket disconnects:**
- Attempt 1: Reconnect after 1 second
- Attempt 2: Reconnect after 2 seconds
- Attempt 3: Reconnect after 4 seconds
- Attempt 4: Reconnect after 8 seconds
- Attempt 5: Reconnect after 16 seconds
- Attempt 6: Reconnect after 30 seconds

**During this time: NO DATA ARRIVES → Then reconnects → ALL buffered data arrives at once = BURST!**

**2. Browser Tab Throttling**
- When tab is in background, WebSocket deprioritized
- Data queued, then delivered when tab focused
- Appears as burst

**3. WiFi/Network Issues**
- ESP32 WiFi packet loss
- Router buffering
- Network congestion

---

## WHAT WOULD FIXING WITH DATABASE POLLING REQUIRE?

### Step 1: Create Query API (NEW CODE NEEDED)

**File:** `hospital-backend/app/api/v1/waveforms.py` (DOESN'T EXIST)

```python
@router.get("/patients/{patientId}/waveforms/recent")
async def getRecentWaveforms(
    patientId: str,
    seconds: int = Query(1, description="Seconds of data to retrieve")
):
    """Get recent waveform data for database polling"""
    async with getTimescaleConnection() as conn:
        cutoff = datetime.now() - timedelta(seconds=seconds)

        rows = await conn.fetch("""
            SELECT
                time, mode, "sampleRate", duration,
                "ecgLimbLeads", "ecgPrecordialLeads", "ecgDerivedLeads",
                "eegFrontalChannels", "eegCentralChannels", "eegOccipitalChannels"
            FROM waveform_snapshots
            WHERE "patientId" = $1 AND time >= $2
            ORDER BY time ASC
        """, patientId, cutoff)

        return [dict(row) for row in rows]
```

**Effort:** ~30 lines, 30 minutes

---

### Step 2: Modify Frontend to Poll (REPLACE WebSocket)

**File:** `hospital-display-app/src/hooks/useECGViewer.ts`

**Current (WebSocket):**
```typescript
// Line 92-134: Subscribe to WebSocket
useEffect(() => {
    const handleWaveform = (message) => {
        // Append to buffer
    };

    subscribe('waveform', handleWaveform);
    return () => unsubscribe('waveform', handleWaveform);
}, []);
```

**New (Database Polling):**
```typescript
useEffect(() => {
    const interval = setInterval(async () => {
        const response = await fetch(
            `/api/v1/waveforms/patients/${patient.id}/recent?seconds=1`
        );
        const packets = await response.json();

        packets.forEach(packet => {
            // Append to buffer (same logic as WebSocket)
            appendPacketToBuffer(packet);
        });
    }, 500); // Poll every 500ms

    return () => clearInterval(interval);
}, [patient.id]);
```

**Effort:** ~50 lines, 1 hour

---

## BETTER SOLUTION: FIX WEBSOCKET STALLING DETECTION

### Problem: WebSocket reconnects but frontend doesn't detect stalls

**Current:** Frontend only knows WebSocket is disconnected when browser fires `onclose` event

**Issue:** WebSocket can be "connected" but data not flowing (backend busy, MQTT stalled, ESP32 not sending)

### Solution: Add Watchdog Timer (SIMPLE FIX)

**File:** `hospital-display-app/src/hooks/useECGViewer.ts`

```typescript
// NEW: Track last data arrival time
const lastDataTime = useRef(Date.now());
const [stalledWarning, setStalledWarning] = useState(false);

// NEW: Detect stalls
useEffect(() => {
    const watchdog = setInterval(() => {
        const timeSince = Date.now() - lastDataTime.current;

        if (timeSince > 2000) {  // No data for 2 seconds
            setStalledWarning(true);
            console.warn('⚠️ WebSocket stalled - no data for 2 seconds');
        } else {
            setStalledWarning(false);
        }
    }, 1000);

    return () => clearInterval(watchdog);
}, []);

// Update last data time when data arrives
const handleWaveform = (message) => {
    lastDataTime.current = Date.now();  // ✅ NEW
    setStalledWarning(false);  // ✅ NEW
    // ... existing append logic
};
```

**Result:** Shows warning "Connection unstable" when data stalls

**Effort:** ~20 lines, 15 minutes

---

## RECOMMENDATION

### Option 1: Add Stall Detection (RECOMMENDED) ✅

**Why:**
- ✅ Simple (20 lines of code)
- ✅ Fast (15 minutes)
- ✅ Helps diagnose problem
- ✅ Shows user when connection is bad
- ✅ No backend changes needed

**What it does:**
- Detects when WebSocket data stops flowing
- Shows warning to user
- Helps identify if problem is network vs backend vs ESP32

**Doesn't fix root cause, but makes problem visible**

---

### Option 2: Create Database Polling API

**Why:**
- ❌ Complex (~80 lines of code)
- ❌ Slower (1-2 hours implementation)
- ❌ Requires backend API creation
- ❌ Requires frontend rewrite
- ❌ Higher database load
- ❌ **Cannot test yet (database empty)**

**Would fix bursty behavior BUT:**
- Need to wait for ESP32 data to test
- Need to implement and test API first
- Need to verify query performance

---

## WHAT TO DO NEXT

### Immediate (Diagnostic):

**Add watchdog timer to detect stalls:**
1. Add `lastDataTime` ref to track data arrival
2. Add `setInterval` to check if data stopped
3. Show warning when stalled > 2 seconds
4. Helps identify WHERE problem is

**Effort:** 15 minutes

**Result:** "Connection stalled" warning shows when data stops

---

### After Diagnostic (If Needed):

**IF watchdog shows frequent stalls:**
- Check ESP32 WiFi signal strength
- Check MQTT broker status
- Check backend event loop blocking
- Consider database polling

**IF watchdog shows no stalls:**
- Problem is browser/display rendering
- Not a data delivery issue
- Check canvas rendering performance

---

## SUMMARY OF RESEARCH

**What EXISTS:**
- ✅ WebSocket with reconnection
- ✅ Frontend 10-second buffer
- ✅ Database storage (my implementation)
- ✅ Heartbeat (30-second ping)

**What's MISSING:**
- ❌ Stall detection (WebSocket connected but no data)
- ❌ Database query API for waveforms
- ❌ Fallback mechanism when WebSocket fails

**What WOULD FIX bursty behavior:**
- Option A: Database polling (complex, 1-2 hours, requires API)
- Option B: Stall detection (simple, 15 minutes, diagnostic only)

**RECOMMENDATION:** Start with Option B (stall detection) to diagnose, then decide if Option A is needed.

---

## FILES TO MODIFY (IF IMPLEMENTING STALL DETECTION)

### Modified (1 file):
1. `hospital-display-app/src/hooks/useECGViewer.ts`
   - Add `lastDataTime` ref (1 line)
   - Add `stalledWarning` state (1 line)
   - Add watchdog timer (10 lines)
   - Update `handleWaveform` to track time (2 lines)
   - Show warning in UI (5 lines)
   - **Total: ~20 lines**

### New Files (0):
- None

### Backend Changes (0):
- None needed

---

## APPROVAL NEEDED

**Before proceeding, user should decide:**

1. **Option A:** Add simple stall detection (15 min, shows problem)
2. **Option B:** Create full database polling (1-2 hrs, fixes problem)
3. **Option C:** Wait for ESP32 data, then reassess

**Which would you prefer?**
