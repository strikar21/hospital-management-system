# MQTT Setup - Minimal Required Steps

## What We Actually Need to Do (Excluding .env stuff)

### ✅ REQUIRED - Cannot Work Without These

#### 1. Install paho-mqtt Python Library
**Why**: Backend MQTT service won't start without it

**Command**:
```bash
cd hospital-backend
pip install paho-mqtt
```

**Check if already installed**:
```bash
pip show paho-mqtt
```

---

#### 2. Run Mosquitto MQTT Broker
**Why**: Backend needs a broker to connect to

**Option A - Simple (No Auth for Testing)**:
```bash
docker run -d \
  --name hospital-mosquitto \
  -p 1883:1883 \
  eclipse-mosquitto:2.0 \
  mosquitto -c /mosquitto-no-auth.conf
```

**Option B - With Auth (Recommended)**:
```bash
# Step 1: Create config directory
mkdir -p mosquitto/config

# Step 2: Create mosquitto.conf
cat > mosquitto/config/mosquitto.conf << 'EOF'
listener 1883
allow_anonymous false
password_file /mosquitto/config/passwords.txt
persistence true
persistence_location /mosquitto/data/
log_dest stdout
EOF

# Step 3: Create password file
docker run -it --rm \
  -v ${PWD}/mosquitto/config:/mosquitto/config \
  eclipse-mosquitto:2.0 \
  mosquitto_passwd -c /mosquitto/config/passwords.txt hospitalEsp32
# Enter password: esp32Secure

# Step 4: Run Mosquitto
docker run -d \
  --name hospital-mosquitto \
  -p 1883:1883 \
  -v ${PWD}/mosquitto/config:/mosquitto/config:ro \
  --restart unless-stopped \
  eclipse-mosquitto:2.0
```

---

#### 3. Restart Backend
**Why**: Backend needs to detect MQTT broker and initialize service

**Command**:
```bash
# Stop current backend (Ctrl+C or kill process)
# Then restart:
cd hospital-backend
python main.py
```

**Expected Output**:
```
✅ MQTT broker connected
📡 Subscribed to: hospital/devices/+/vitals
📡 Subscribed to: hospital/devices/+/alerts
✅ MQTT service started successfully
```

**Instead of**:
```
⚠️ MQTT service not available
```

---

### That's It! ✅

**Those 3 steps are ALL you need to get MQTT working.**

---

## Optional (But Recommended for Production)

### 4. Enable TLS/SSL
**Why**: Encrypt MQTT traffic

**When**: Before production deployment

**Complexity**: Medium (requires certificate generation)

---

### 5. Implement ACLs
**Why**: Topic-level access control

**When**: If multiple devices need different permissions

**Complexity**: Low (just add acl.conf file)

---

### 6. Per-Device Credentials
**Why**: Revoke individual devices

**When**: If you have many devices in production

**Complexity**: Medium (need to provision each device)

---

## Testing After Setup

### Test 1: Check Mosquitto is Running
```bash
docker ps | grep mosquitto
```

**Expected**:
```
abc123  eclipse-mosquitto:2.0  Up 10 seconds  0.0.0.0:1883->1883/tcp
```

---

### Test 2: Check Backend Connected
```bash
# Look at backend startup logs
```

**Expected**:
```
📡 Connecting to MQTT broker: 127.0.0.1:1883
✅ MQTT broker connected
📡 Subscribed to: hospital/devices/+/vitals
```

---

### Test 3: Subscribe to Topics (Optional)
```bash
# Install mosquitto clients
choco install mosquitto  # Windows

# Subscribe to all hospital topics
mosquitto_sub -h localhost -p 1883 -u hospitalEsp32 -P esp32Secure -t "hospital/#" -v
```

**Expected**: Should connect without errors

---

### Test 4: Check ESP32 Watch
**Serial Monitor Output**:
```
✅ MQTT Connected!
📡 Subscribed to: hospital/devices/ESP32_WATCH_003/assign
📡 Subscribed to: hospital/devices/ESP32_WATCH_003/command
```

**If you see**:
```
❌ MQTT Connection failed, rc=-2
```
Then broker is not accessible from watch's network.

---

## Current Architecture (Your System)

```
┌──────────────┐
│ ESP32 Watch  │
│  v3.3.0      │
└───────┬──────┘
        │
        │ HTTP (HMAC)     ✅ Already Secure
        │ Heartbeats
        │
        ▼
┌───────────────┐
│   Backend     │ ◄────┐
│   Port 8001   │      │ MQTT    ⚠️ Needs Setup
└───────┬───────┘      │
        │              │
        │ Forwards     │
        │ to MQTT      │
        │              │
        ▼              │
┌───────────────┐      │
│  Mosquitto    │──────┘
│  Port 1883    │
└───────────────┘
        │
        │ Publishes
        │
        ▼
┌───────────────┐
│  TimescaleDB  │
│  (Vitals)     │
└───────────────┘
```

**Key Point**: ESP32 → Backend uses HTTP (already secure with HMAC).
Backend → MQTT is internal (needs setup but lower security risk).

---

## Summary: 3 Required Steps

| Step | Action | Time | Status |
|------|--------|------|--------|
| 1 | Install paho-mqtt | 1 min | ⏳ Pending |
| 2 | Run Mosquitto Docker | 2 min | ⏳ Pending |
| 3 | Restart Backend | 1 min | ⏳ Pending |

**Total Time**: ~5 minutes

---

## After Setup Works

Once MQTT is running, you should see:
- ✅ Backend logs: "MQTT broker connected"
- ✅ Watch logs: "MQTT Connected" (if watch uses MQTT)
- ✅ Vitals flowing to TimescaleDB
- ✅ Real-time updates on frontend

---

## For Your Current ESP32 Firmware (v3.3.0)

**Important**: Your current watch firmware sends:
- ✅ Heartbeats via HTTP (working)
- ❓ Vitals via MQTT (needs broker setup)
- ❓ Alerts via MQTT (needs broker setup)

**After MQTT setup**, the watch will be able to:
1. Connect to MQTT broker (line 959-980 in firmware)
2. Subscribe to commands (line 973-975)
3. Publish vitals every 5 seconds (line 1177-1203)
4. Publish alerts every 2 seconds when triggered (line 249-272)

---

## Want Me to Do It Now?

I can execute all 3 steps for you right now:
1. Check/install paho-mqtt
2. Run Mosquitto in Docker
3. Check backend logs

Just say **"yes, set it up"** and I'll do it! 🚀
