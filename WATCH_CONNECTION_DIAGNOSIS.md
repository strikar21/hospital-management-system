# Watch Connection Diagnosis

## ESP32 Watch Status
- **Device ID**: fit-00001
- **MAC Address**: A0:A3:B3:AA:13:B0
- **Assigned Patient**: 081a5294-da91-4c74-bb8a-e5062f5851dd (Thomas Brown)
- **MQTT Connection**: ✅ CONNECTED (TLS 1.2 with mTLS)
- **WiFi**: ✅ CONNECTED (192.168.0.149, -62 dBm)
- **Firmware**: v5.2.8

## Database Status
- **Device ID**: fit-00001
- **Device Type**: watch
- **Device Status**: assigned
- **Battery Level**: 100%
- **Last Seen**: 2025-11-08 19:51:58 (OLD - not updating!)
- **Patient ID**: 081a5294-da91-4c74-bb8a-e5062f5851dd
- **Patient Name**: Thomas Brown
- **Patient Status**: active
- **Assignment Status**: active
- **Assigned At**: 2025-10-27 01:06:45
- **Assigned By**: NUR0001

## Problem Identified
❌ **`lastSeen` timestamp is NOT updating!**

The ESP32 watch shows:
```
20:31:02.190 -> ✅ MQTT Connected with client certificate (mTLS)!
20:31:02.237 -> ✅ Physiological Simulator initialized
```

But the database `lastSeen` is from **2025-11-08 19:51:58** (OLD).

This means:
1. **Either**: Backend MQTT service is NOT running
2. **Or**: Backend is NOT processing MQTT messages from ESP32
3. **Or**: Backend is NOT updating the `lastSeen` timestamp

## Root Cause Analysis

### Possible Causes:

1. **Backend Not Running**
   - Check if `uvicorn` is running on port 8001
   - Check backend logs for MQTT connection

2. **MQTT Broker Not Running**
   - ESP32 shows MQTT connected, so broker IS running
   - Broker is at 192.168.0.113:8883

3. **Backend Not Subscribed to MQTT Topics**
   - Backend should subscribe to: `hospital/devices/+/vitals`
   - Check backend MQTT service initialization

4. **Backend MQTT Service Crashed**
   - Check backend logs for errors
   - MQTT service may have failed to start

5. **Backend Receiving Messages But Not Processing**
   - Backend receives MQTT messages but handler crashes
   - Check for Python exceptions in backend logs

## Next Steps to Diagnose

### Step 1: Check if backend is running
```bash
# Check if port 8001 is listening
netstat -an | findstr "8001"
```

### Step 2: Check backend logs
```bash
cd hospital-backend
# Look for MQTT-related logs
tail -f logs/backend.log | findstr "MQTT"
```

### Step 3: Check MQTT broker logs
```bash
# Check mosquitto logs for backend connection
# Look for "fit-00001" device messages
```

### Step 4: Verify backend MQTT initialization
Check backend logs for:
- "✅ MQTT service started successfully"
- "📡 Subscribed to: hospital/devices/+/vitals"
- "✅ AlertPipeline initialized with database pool"

## Expected Behavior

When ESP32 sends vitals via MQTT, backend should:
1. Receive MQTT message on topic `hospital/devices/fit-00001/vitals`
2. Validate device assignment
3. Process vitals data
4. Update `devices.lastSeen` to current timestamp
5. Store vitals in TimescaleDB
6. Generate alerts via AlertPipeline
7. Broadcast to frontend via WebSocket

## Frontend "Watch Not Connected" Logic

Frontend likely checks:
- `devices.lastSeen` < 30 seconds ago = Connected
- `devices.lastSeen` > 30 seconds ago = Disconnected

Since `lastSeen` is old (from yesterday), frontend shows "watch not connected".

## Solution

**Primary action**: Start/restart the backend to ensure MQTT service is running.

```bash
cd hospital-backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Watch for these log messages:
- "✅ MQTT service started successfully"
- "✅ AlertPipeline initialized with database pool"
- "📨 MQTT message: hospital/devices/fit-00001/vitals"
