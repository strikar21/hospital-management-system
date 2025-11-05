# Port Status Check

**Date:** 2025-11-01 13:50
**Command:** `netstat -ano | findstr ":PORT"`

---

## Port Status Summary

| Port | Service | Status | PID | Details |
|------|---------|--------|-----|---------|
| **3000** | Frontend (React) | ❌ **FREE** | - | Not running |
| **8001** | Backend (Python) | ✅ **IN USE** | 71752 | Running with active connections |
| **1883** | MQTT (Non-SSL) | ❌ **FREE** | - | Not running |
| **8883** | MQTT (SSL/TLS) | ✅ **IN USE** | 5264, 25524 | Running with multiple connections |
| **5432** | PostgreSQL | 🔍 Checking... | - | - |

---

## Detailed Port Analysis

### Port 3000 (Frontend - React)
```
Status: FREE ❌
No process listening
```
**Action Needed:** Start frontend with `npm start` in hospital-display-app/

---

### Port 8001 (Backend - Python FastAPI)
```
Status: RUNNING ✅
PID: 71752

Connections:
  TCP    0.0.0.0:8001           0.0.0.0:0              LISTENING       71752
  TCP    127.0.0.1:8001         127.0.0.1:51069        ESTABLISHED     71752
  TCP    127.0.0.1:51069        127.0.0.1:8001         ESTABLISHED     24128
  TCP    127.0.0.1:55201        127.0.0.1:8001         TIME_WAIT       0
  TCP    127.0.0.1:55486        127.0.0.1:8001         TIME_WAIT       0
  TCP    127.0.0.1:58459        127.0.0.1:8001         TIME_WAIT       0
  TCP    127.0.0.1:60304        127.0.0.1:8001         TIME_WAIT       0
  TCP    127.0.0.1:65363        127.0.0.1:8001         TIME_WAIT       0
```

**Analysis:**
- Backend is running
- Has 1 active connection (127.0.0.1:51069 - likely browser or tool)
- Multiple TIME_WAIT connections (recent closed connections, normal)

**Status:** ✅ HEALTHY

---

### Port 1883 (MQTT Non-SSL)
```
Status: FREE ❌
No process listening
```
**Note:** System uses port 8883 (SSL) instead, this is correct.

---

### Port 8883 (MQTT SSL/TLS - Mosquitto)
```
Status: RUNNING ✅
PIDs: 5264 (main), 25524, 27504 (listeners)

Connections:
  TCP    0.0.0.0:8883           0.0.0.0:0              LISTENING       5264
  TCP    0.0.0.0:8883           0.0.0.0:0              LISTENING       25524
  TCP    127.0.0.1:8883         127.0.0.1:56890        ESTABLISHED     5264
  TCP    127.0.0.1:56890        127.0.0.1:8883         ESTABLISHED     71752
  TCP    172.24.96.1:56891      172.24.109.4:8883      ESTABLISHED     5264
  TCP    172.24.96.1:58720      172.24.109.4:8883      ESTABLISHED     5264
  TCP    192.168.0.113:8883     192.168.0.148:54815    ESTABLISHED     5264
  TCP    192.168.0.113:58777    23.98.86.4:8883        ESTABLISHED     20336
  TCP    [::]:8883              [::]:0                 LISTENING       25524
  TCP    [::1]:8883             [::]:0                 LISTENING       27504
```

**Analysis:**
- Mosquitto MQTT broker is running
- **Local connection:** 127.0.0.1:56890 ↔ Backend (PID 71752) ✅
- **WSL connection:** 172.24.96.1 ↔ 172.24.109.4 (Docker/WSL)
- **LAN device:** 192.168.0.113:8883 ↔ 192.168.0.148:54815 (ESP32 watch?) ✅
- **External:** 192.168.0.113:58777 ↔ 23.98.86.4:8883 (unknown)
- IPv6 listeners active

**Status:** ✅ HEALTHY - Has device connected!

---

## Summary

### Services Running:
- ✅ **Backend** (port 8001) - Running
- ✅ **MQTT Broker** (port 8883) - Running with device connections
- ❌ **Frontend** (port 3000) - NOT running

### To Start Frontend:
```bash
cd hospital-display-app
npm start
```

Frontend should start on http://localhost:3000

---

## Next Steps

**To test ECG auto-sizing:**
1. Start frontend: `npm start` in hospital-display-app/
2. Login to application
3. Navigate to patient with assigned device
4. Click "Full View" to open ECG viewer
5. Test 12-lead, 9-lead, 4-lead layouts
6. Verify all leads visible without scrolling

**Backend and MQTT are already running** ✅
