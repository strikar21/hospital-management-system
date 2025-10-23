# ESP32 MQTT Connection Diagnosis

## Current Situation

### Device Information
- **MAC Address**: A0:A3:B3:AA:13:B0
- **Database Status**: ALREADY EXISTS as ESP32_WATCH_003
- **Serial Number**: SN_W003
- **Firmware on ESP32**: v4.2.0 (MQTT-only provisioning)
- **Database Firmware**: v2.1.0 (old)
- **Device Status**: assigned

### Connection Attempt
```
ESP32 Serial Output:
🔄 Attempting MQTT provisioning...
🔧 Configuring MQTT client...
📡 MQTT Server: 192.168.0.113:8883
🔐 TLS configured with CA certificate from SPIFFS
✅ MQTT client configured
🔄 Connecting to MQTT as: HospitalWatch_UNPROVISIONED_A0A3B3AA13B0
🔐 Using credentials: hospitalEsp32
❌ MQTT connection failed for provisioning, rc=-2
```

### Mosquitto Logs
```
OpenSSL Error[0]: error:0A000126:SSL routines::unexpected eof while reading
Client <unknown> disconnected: Protocol error.
```

## Root Cause Analysis

### Issue #1: Device Already Provisioned in Database
The ESP32 is trying to **provision as new device**, but it's already registered as `ESP32_WATCH_003`.

**Expected Behavior:**
- Device should connect with existing credentials: `ESP32_WATCH_003_mqtt` / [generated password]
- Device should NOT request provisioning again

**Actual Behavior:**
- Device has `isProvisioned = false` in its Preferences
- Device is attempting MQTT provisioning
- Device is using shared credentials (`hospitalEsp32`)

### Issue #2: TLS "Unexpected EOF" Error
The ESP32 TLS connection is closing prematurely before completing the handshake.

**Possible Causes:**
1. **Certificate mismatch** - ❌ RULED OUT (CA certs match, server cert has correct IP)
2. **Client not sending proper TLS ClientHello** - ⚠️ POSSIBLE
3. **MQTT credentials issue causing immediate disconnect** - ⚠️ POSSIBLE
4. **Arduino WiFiClientSecure TLS version mismatch** - ⚠️ POSSIBLE
5. **ESP32 not waiting for TLS handshake completion** - ⚠️ POSSIBLE

### Issue #3: Firmware Mismatch
- **ESP32 Running**: v4.2.0 (MQTT-only, per-device credentials)
- **Database Shows**: v2.1.0 (HTTP + MQTT, HMAC auth)

This indicates the device was previously flashed with v2.1.0 firmware, then updated to v4.2.0, but **Preferences were not cleared**.

## Diagnostic Evidence

### ✅ Working Components:
- Mosquitto running on port 8883 ✅
- TLS configured correctly ✅
- Backend connected to Mosquitto ✅
- CA certificate valid and matches ✅
- Server certificate includes IP 192.168.0.113 ✅
- ESP32 WiFi connected ✅
- ESP32 NTP synced ✅

### ❌ Failing Components:
- ESP32 TLS handshake fails ❌
- ESP32 Preferences show `isProvisioned = false` but device exists in DB ❌
- ESP32 doesn't have per-device MQTT credentials ❌

## Solution Options

### Option A: Clear ESP32 Preferences and Re-Provision (RECOMMENDED)
**Pros:**
- Clean slate
- Tests complete provisioning flow
- Validates MQTT provisioning works end-to-end

**Cons:**
- Will create NEW device ID (ESP32_WATCH_004 or higher)
- Old device record (ESP32_WATCH_003) becomes orphaned

**Steps:**
1. Add erase function to ESP32 firmware or use `esptool.py --erase-flash`
2. Flash firmware again
3. Configure via captive portal
4. Watch MQTT provisioning happen

### Option B: Manually Configure ESP32 with Existing Credentials
**Pros:**
- Preserves existing device ID (ESP32_WATCH_003)
- No orphaned records

**Cons:**
- Requires knowing the exact MQTT password for ESP32_WATCH_003
- Need to understand backend's password generation algorithm
- Won't test provisioning flow

**Steps:**
1. Find or regenerate MQTT password for ESP32_WATCH_003
2. Manually save to ESP32 Preferences:
   - `device_id`: ESP32_WATCH_003
   - `serial_num`: SN_W003
   - `mqtt_user`: ESP32_WATCH_003_mqtt
   - `mqtt_pass`: [generated password]
   - `provisioned`: true
3. Reset ESP32

### Option C: Delete Database Record and Provision Fresh (CLEANEST)
**Pros:**
- Clean slate
- Tests provisioning flow
- Same device ID can be reused

**Cons:**
- Loses device history (battery health, disconnects, etc.)

**Steps:**
1. Delete device record from database: `DELETE FROM devices WHERE id = 'ESP32_WATCH_003'`
2. ESP32 provisions via MQTT
3. Gets assigned ESP32_WATCH_003 (next available number)

## Recommended Action

**Use Option C**: Delete existing device record and provision fresh.

**Reasoning:**
1. ESP32 firmware v4.2.0 expects MQTT-only provisioning
2. Device record is stale (firmware v2.1.0)
3. No critical data to preserve (battery health can rebuild)
4. Tests complete provisioning flow as intended

## Implementation

### Step 1: Delete Existing Device Record
```sql
DELETE FROM devices WHERE "macAddress" = 'A0:A3:B3:AA:13:B0';
-- Or
DELETE FROM devices WHERE id = 'ESP32_WATCH_003';
```

### Step 2: Check Device Assignments
```sql
SELECT * FROM "deviceAssignments" WHERE "deviceId" = 'ESP32_WATCH_003';
-- If any exist:
DELETE FROM "deviceAssignments" WHERE "deviceId" = 'ESP32_WATCH_003';
```

### Step 3: Reset ESP32
Press the physical RESET button on the ESP32.

### Step 4: Watch Provisioning Happen
Monitor serial output for:
```
🔄 Attempting MQTT provisioning...
✅ MQTT connected (unprovisioned)
📡 Subscribed to: hospital/provisioning/response/A0:A3:B3:AA:13:B0
📤 Provisioning request sent via MQTT
📨 MQTT Message: hospital/provisioning/response/A0:A3:B3:AA:13:B0
🎉 DEVICE PROVISIONED via MQTT!
   Device ID: ESP32_WATCH_003 (or 004)
   Serial Number: SN_W003 (or SN_W004)
   MQTT Username: ESP32_WATCH_003_mqtt
💾 Credentials saved to Preferences
```

### Step 5: Verify in Mosquitto Logs
```bash
docker logs hospital-mosquitto -f
```

Expected:
```
New connection from 192.168.0.148:XXXXX on port 8883.
New client connected from 192.168.0.148 as HospitalWatch_UNPROVISIONED_A0A3B3AA13B0 (p2, c1, k60, u'hospitalEsp32').
[... provisioning happens ...]
Client HospitalWatch_UNPROVISIONED_A0A3B3AA13B0 disconnected.
New connection from 192.168.0.148:XXXXX on port 8883.
New client connected from 192.168.0.148 as HospitalWatch_ESP32_WATCH_003 (p2, c1, k60, u'ESP32_WATCH_003_mqtt').
```

## TLS "Unexpected EOF" Investigation

If TLS error persists after Option C, investigate:

### Test 1: Verify ESP32 TLS Library
Check ArduinoJson and WiFiClientSecure versions:
- WiFiClientSecure should support TLS 1.2
- Verify `wifiClient.setCACert()` is called BEFORE `mqttClient.connect()`

### Test 2: Add Debug Logging
In firmware, add before `mqttClient.connect()`:
```cpp
Serial.println("DEBUG: About to connect to MQTT...");
Serial.println("DEBUG: CA cert length: " + String(caCertificate.length()));
Serial.println("DEBUG: WiFi client ready: " + String(wifiClient.connected()));
```

### Test 3: Try Insecure Mode (Temporarily)
Replace `configureTLS()` with:
```cpp
wifiClient.setInsecure();  // TEMPORARY - for debugging only
```

If this works, it confirms certificate issue. If it still fails, it's MQTT credentials or protocol issue.

### Test 4: Check MQTT Protocol Version
ESP32 uses MQTT 3.1.1. Mosquitto supports this. But verify in `mqttClient.connect()` that the correct protocol is negotiated.

## Next Steps

1. User decides: Option A, B, or C?
2. If Option C (recommended), execute database cleanup
3. Reset ESP32 and monitor provisioning
4. Report results
