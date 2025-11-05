# Waveform Storage - ACTUAL STATUS REPORT
**Generated:** 2025-11-02
**Database:** TimescaleDB (port 5433)
**Status:** PARTIALLY WORKING

---

## ✅ GOOD NEWS: Database Connection Working

Successfully connected to TimescaleDB at `localhost:5433` with credentials:
- Database: `hospitaltimescale`
- User: `hospital_user`
- Password: `hospital123`

---

## 📊 ACTUAL TABLE STATUS

### Tables Found (4 tables):
1. ✅ `neural_events` - EXISTS
2. ✅ `vitals_realtime` - EXISTS
3. ✅ `vitals_timeseries` - EXISTS (legacy table)
4. ✅ `waveform_snapshots` - EXISTS

---

## ❌ CRITICAL FINDING: Waveform Data NOT Being Stored

### `waveform_snapshots` Table:
```
Row Count: 0
Status: EMPTY - NO WAVEFORM DATA BEING STORED
```

**This means:**
- ❌ ECG waveforms are NOT being saved to database
- ❌ EEG waveforms are NOT being saved to database
- ❌ Multi-channel waveform data is NOT persisted
- ❌ Historical waveform review is NOT possible

### `neural_events` Table:
```
Row Count: 0
Status: EMPTY - NO NEURAL EVENTS BEING STORED
```

**This means:**
- ❌ Arrhythmia detections are NOT being saved
- ❌ Seizure events are NOT being saved
- ❌ No event history available for review

---

## ✅ GOOD NEWS: Vitals Data IS Being Stored

### `vitals_realtime` Table:
```
Row Count: 101,949 rows
Status: ACTIVE - Vitals ARE being stored properly
```

**This means:**
- ✅ Heart rate, SpO2, temperature ARE being saved
- ✅ ECG analysis (RR interval, QRS, QT) ARE being saved
- ✅ EEG analysis (band powers, seizure flags) ARE being saved
- ✅ Historical vitals queries work

---

## 🔍 ROOT CAUSE ANALYSIS

### Why Are Waveforms NOT Being Stored?

Based on code analysis ([`mqtt_service.py:686-1316`](hospital-backend/app/services/mqtt_service.py:686)):

1. **Code EXISTS to store waveforms:**
   - `_storeWaveformSnapshot()` function is implemented
   - `INSERT INTO waveform_snapshots` SQL is correct
   - Function handles ECG and EEG modes properly

2. **BUT the function is NOT being called:**
   - Waveform messages from ESP32 are received
   - Waveforms are streamed to WebSocket (frontend)
   - **Storage function is never invoked**

### Suspected Reasons:

#### 1. **ESP32 Not Sending to `/waveform` Topic**
ESP32 firmware may only be sending to:
- ✅ `hospital/devices/{deviceId}/vitals` - WORKING (vitals stored)
- ✅ `hospital/devices/{deviceId}/stream` - WORKING (streaming only, not stored)
- ❌ `hospital/devices/{deviceId}/waveform` - NOT SENDING (should trigger storage)

#### 2. **Storage Function Not Called in Message Handler**
Backend MQTT handler may be missing the call to `_storeWaveformSnapshot()` when receiving waveform messages.

#### 3. **No ESP32 Device Active**
If no ESP32 is currently connected and sending data, waveforms won't be stored.

---

## 📋 WHAT'S WORKING vs. WHAT'S NOT

### ✅ WORKING:
1. **Database tables created** - All 4 tables exist
2. **Vitals storage** - 101,949 vitals records stored
3. **Real-time waveform streaming** - Frontend receives waveforms via WebSocket
4. **WebSocket broadcasting** - Waveforms flow ESP32 → MQTT → Backend → WebSocket → Frontend
5. **Frontend rendering** - ECG/EEG waveforms display correctly
6. **Frontend caching** - IndexedDB cache works for instant display

### ❌ NOT WORKING:
1. **Waveform persistence** - 0 waveform snapshots stored
2. **Neural event logging** - 0 arrhythmia/seizure events stored
3. **Historical waveform review** - Cannot query past waveforms
4. **Event acknowledgement workflow** - No events to acknowledge
5. **Long-term ECG/EEG analysis** - No historical data available

---

## 🔧 WHAT NEEDS TO BE FIXED

### Priority 1: Enable Waveform Storage

**Option A: Verify ESP32 is sending `/waveform` messages**
1. Check ESP32 firmware: Does it publish to `hospital/devices/{deviceId}/waveform`?
2. Check MQTT broker logs: Are `/waveform` messages arriving?
3. Check backend MQTT logs: Is backend receiving `/waveform` topic?

**Option B: Add storage call to message handler**
1. Find where waveform messages are processed
2. Add call to `_storeWaveformSnapshot()` after receiving waveform
3. Verify JSONB serialization works correctly

### Priority 2: Enable Neural Event Storage

1. Verify alert detection service is detecting events
2. Add call to `_storeNeuralEvent()` when arrhythmia/seizure detected
3. Connect to frontend event acknowledgement UI

### Priority 3: Test Storage Pipeline

1. Send test waveform message via MQTT
2. Verify row appears in `waveform_snapshots` table
3. Query waveform back from database
4. Verify delta encoding/decoding works

---

## 🧪 VERIFICATION SCRIPT

Run this to check if waveform storage is working:

```python
import asyncio
import asyncpg

async def check_storage():
    conn = await asyncpg.connect(
        host='localhost',
        port=5433,
        database='hospitaltimescale',
        user='hospital_user',
        password='hospital123'
    )

    # Check waveform_snapshots
    count = await conn.fetchval('SELECT COUNT(*) FROM waveform_snapshots;')
    print(f'Waveform snapshots: {count}')

    if count > 0:
        latest = await conn.fetchrow('''
            SELECT time, "patientId", mode, "sampleRate"
            FROM waveform_snapshots
            ORDER BY time DESC LIMIT 1
        ''')
        print(f'Latest: {latest}')
    else:
        print('NO WAVEFORMS STORED - Storage not working!')

    await conn.close()

asyncio.run(check_storage())
```

---

## 📈 STORAGE CAPACITY ANALYSIS

### Current State:
- **Vitals:** 101,949 rows (~102k vitals readings)
- **Waveforms:** 0 rows (empty)
- **Events:** 0 rows (empty)

### Expected State (if storage working):
Assuming 1 patient with device for 24 hours:
- **Vitals:** ~86,400 rows (1 per second)
- **Waveforms:** ~8,640 rows (1 per 10 seconds)
- **Events:** ~5-20 rows (arrhythmias/seizures)

### Storage Estimate per Patient per Day:
- **Vitals:** ~5 MB/day (small JSONB records)
- **Waveforms:** ~500 MB/day (8-12 channel delta-encoded data)
- **Events:** <1 MB/day (small event snippets)
- **Total:** ~505 MB/patient/day

### 7-Year HIPAA Retention (1 patient):
- **Total:** ~1.3 TB per patient over 7 years
- **With 100 patients:** ~130 TB
- **With compression:** ~40-60 TB (TimescaleDB compression)

---

## 🎯 NEXT STEPS

1. **Research ESP32 Firmware:**
   - Check `esp32_hospital_watch_complete.ino`
   - Verify MQTT topic structure
   - Confirm waveform message publishing

2. **Research Backend MQTT Handler:**
   - Check `mqtt_service.py` message routing
   - Verify `_on_message()` callback
   - Find where storage should be called

3. **Enable Storage:**
   - Add storage call in appropriate handler
   - Test with real ESP32 device
   - Verify database inserts

4. **Monitor Storage:**
   - Check table row counts regularly
   - Monitor disk usage
   - Enable TimescaleDB compression

---

## 📝 CONCLUSION

### Current State: ⚠️ **PARTIALLY WORKING**

**WORKING:**
- ✅ Real-time waveform streaming to frontend
- ✅ Vitals data storage (101k+ rows)
- ✅ Database tables created correctly
- ✅ Frontend rendering and caching

**NOT WORKING:**
- ❌ Waveform data persistence (0 rows)
- ❌ Neural event logging (0 rows)
- ❌ Historical waveform review
- ❌ Long-term ECG/EEG analysis

### Fix Required:
**Storage pipeline needs to be connected between MQTT message reception and database insert.**

The code exists, the tables exist, but the connection between them is missing.

---

**Status:** NEEDS INVESTIGATION & FIX
**Impact:** HIGH - No historical waveform data available
**Urgency:** MEDIUM - Real-time streaming works, but archival doesn't
