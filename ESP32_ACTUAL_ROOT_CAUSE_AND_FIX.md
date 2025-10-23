# ESP32 MQTT Connection - Actual Root Cause and Fix

## Executive Summary

**ESP32 NEVER connected to MQTT because of a firmware bug introduced when we added `setHandshakeTimeout()`.**

The error `errno: 9, "Bad file number"` reveals that we're calling `setHandshakeTimeout()` on a **closed socket** before the connection is established.

## Evidence-Based Diagnosis

### User's Answers:
1. ✅ SPIFFS uploaded with RSA-2048 CA (1436 bytes confirmed)
2. ❌ ESP32 **NEVER worked** with MQTT (not a regression, always broken)
3. ❓ Cipher configuration unknown (may not matter - problem is earlier)

### ESP32 Serial Output Analysis:

```
✅ CA certificate loaded from SPIFFS (1436 bytes)  ← RSA-2048 working
✅ WiFi Connected!
✅ NTP synced
✅ Device certificates found in SPIFFS
🔐 TLS configured with Hospital CA certificate
🔍 Free heap: 215344 bytes  ← Plenty of memory
✅ Device certificate loaded (1619 bytes)
✅ Device private key loaded (1704 bytes)
🔐 Device ID (from cert CN): ESP32-WATCH-A0:A3:B3:AA:13:B0

[  4920][E][NetworkClient.cpp:327] setSocketOption(): fail on 0, errno: 9, "Bad file number"  ← THE PROBLEM
```

**Key Observation:** Error happens BEFORE TLS handshake even starts!

### Root Cause: Socket Operation Order Bug

**File:** `esp32_hospital_watch_complete.ino`
**Function:** `connectToMQTT()` (lines 998-1051)

**Problematic Code:**
```cpp
void connectToMQTT() {
  if (!wifiConnected || !isProvisioned) return;

  // ✅ FIX: Clear any existing TLS connection state
  wifiClient.stop();  // ← Line 1002: Closes socket (fd becomes invalid)

  // ✅ FIX: Configure handshake timeout for large certificate chains
  // ESP32 mbedTLS needs more time to process 2KB+ certificates
  // Default timeout (10-15s) is too short, increase to 30 seconds
  wifiClient.setHandshakeTimeout(30000);  // ← Line 1007: ERROR! Socket doesn't exist yet

  // ... certificate loading ...

  wifiClient.setCACert(caCertificate.c_str());  // ← Line 1024
  wifiClient.setCertificate(deviceCert.c_str());  // ← Line 1025
  wifiClient.setPrivateKey(deviceKey.c_str());  // ← Line 1026

  // ... MQTT connection attempt ...

  if (mqttClient.connect(clientId.c_str())) {  // ← Line 1033: Socket created HERE
    // ... success ...
  }
}
```

**Problem Flow:**
1. Line 1002: `wifiClient.stop()` - Closes existing socket, fd becomes invalid (0 or -1)
2. Line 1007: `setHandshakeTimeout(30000)` - Tries to call `setSocketOption()` on invalid fd
3. Result: `NetworkClient.cpp:327 setSocketOption(): fail on 0, errno: 9`
4. Socket is in broken state, connection fails

### Why This Happens (Technical Details)

**From ESP32 Arduino Core 3.x:**

`WiFiClientSecure::setHandshakeTimeout()` internally calls `setSocketOption()` which requires a **valid socket file descriptor**.

**Socket Lifecycle:**
```
1. new WiFiClientSecure() → fd = -1 (no socket)
2. .stop() → fd = 0 (closed socket)
3. .connect() → fd = 50 (valid socket created)
```

**Our Bug:**
We call `setHandshakeTimeout()` at stage 2 (fd = 0), but it requires stage 3 (valid socket).

**Web Research Confirms:**
From GitHub issue espressif/arduino-esp32#7244:
> "setSocketOption doesn't respect inheritance" and "You can't call setTimeout before client.connect"

### Why We Added This Code

**Original Intent:** Fix RSA-4096 certificate timeout issue

**What We Did:**
1. Changed certificates from RSA-4096 → RSA-2048 ✅ CORRECT
2. Added `setHandshakeTimeout(30000)` ❌ WRONG LOCATION

**Result:** Fixed one problem, introduced new bug

## The Actual Fix

### Option A: Remove setHandshakeTimeout() Entirely (RECOMMENDED)

**Reasoning:**
- RSA-2048 certificates are fast enough with hardware acceleration
- Default timeout (10-15s) should be sufficient for RSA-2048
- Backend connects instantly with same setup
- Adding complexity without proven need

**Fix:**
```cpp
void connectToMQTT() {
  if (!wifiConnected || !isProvisioned) return;

  // Clear any existing TLS connection state
  wifiClient.stop();

  // Load device certificate and private key
  String deviceCert, deviceKey;
  if (!loadDeviceCertificate(deviceCert, deviceKey)) {
    Serial.println("❌ Cannot connect to MQTT - certificates not found");
    return;
  }

  Serial.println("🔍 Certificate sizes:");
  Serial.println("   CA: " + String(caCertificate.length()) + " bytes");
  Serial.println("   Device cert: " + String(deviceCert.length()) + " bytes");
  Serial.println("   Device key: " + String(deviceKey.length()) + " bytes");

  // Configure TLS with client certificate (mTLS)
  wifiClient.setCACert(caCertificate.c_str());
  wifiClient.setCertificate(deviceCert.c_str());
  wifiClient.setPrivateKey(deviceKey.c_str());

  String clientId = "HospitalWatch_" + deviceId;
  Serial.println("🔄 Connecting to MQTT with client certificate...");
  Serial.println("🔐 Device ID (from cert CN): " + deviceId);

  // Connect WITHOUT username/password (certificate auth only)
  if (mqttClient.connect(clientId.c_str())) {
    Serial.println("✅ MQTT Connected with client certificate (mTLS)!");
    // ... rest of connection logic ...
  } else {
    Serial.println("❌ MQTT Connection failed, rc=" + String(mqttClient.state()));
  }
}
```

**Changes:**
- ❌ Removed: `wifiClient.setHandshakeTimeout(30000);` (line 1007)
- ❌ Removed: Free heap logging (unnecessary)
- ✅ Kept: Everything else

### Option B: Move setHandshakeTimeout() to setupMQTT() (Alternative)

**If** you insist on custom timeout, set it ONCE during setup:

```cpp
void setupMQTT() {
  // ... existing code ...

  Serial.println("🔧 Configuring MQTT client...");

  if (caCertificate.length() > 0) {
    wifiClient.setCACert(caCertificate.c_str());
    wifiClient.setHandshakeTimeout(30000);  // Set AFTER setCACert, BEFORE connect
    Serial.println("🔐 TLS configured with Hospital CA certificate");
  } else {
    Serial.println("⚠️ WARNING: No CA certificate - using insecure mode");
    wifiClient.setInsecure();
  }

  mqttClient.setServer(mqttServer.c_str(), mqttPort.toInt());
  mqttClient.setCallback(onMqttMessage);
  mqttClient.setBufferSize(4096);

  Serial.println("✅ MQTT client configured");
  connectToMQTT();
}
```

**BUT:** This may still cause issues because socket isn't created yet. **Option A is safer.**

### Option C: Set Timeout After connect() Succeeds (Complex, Not Recommended)

This would require modifying PubSubClient internals. Not worth the complexity.

## Testing Plan

### Step 1: Apply Fix (Option A - Remove Timeout)

1. Edit `esp32_hospital_watch_complete.ino`
2. Remove line 1007: `wifiClient.setHandshakeTimeout(30000);`
3. Remove lines 1009 (free heap logging)
4. Upload firmware to ESP32

### Step 2: Test ESP32 Connection

1. Power on ESP32
2. Observe serial output
3. Look for: `✅ MQTT Connected with client certificate (mTLS)!`

**Expected Result:**
```
✅ CA certificate loaded from SPIFFS (1436 bytes)
✅ WiFi Connected!
✅ NTP synced
✅ Device certificates found in SPIFFS
🔐 TLS configured with Hospital CA certificate
✅ Device certificate loaded (1619 bytes)
✅ Device private key loaded (1704 bytes)
🔍 Certificate sizes:
   CA: 1436 bytes
   Device cert: 1619 bytes
   Device key: 1704 bytes
🔄 Connecting to MQTT with client certificate...
🔐 Device ID (from cert CN): ESP32-WATCH-A0:A3:B3:AA:13:B0
✅ MQTT Connected with client certificate (mTLS)!  ← SUCCESS!
📡 Subscribed to: hospital/devices/ESP32-WATCH-A0:A3:B3:AA:13:B0/assign
📡 Subscribed to: hospital/devices/ESP32-WATCH-A0:A3:B3:AA:13:B0/command
```

### Step 3: Verify Mosquitto Logs

```bash
docker logs --tail 50 hospital_mosquitto
```

**Expected:**
```
New connection from 192.168.0.148:xxxxx on port 8883.
New client connected from 192.168.0.148:xxxxx as HospitalWatch_ESP32-WATCH-A0:A3:B3:AA:13:B0 (p2, c1, k60, u='ESP32-WATCH-A0:A3:B3:AA:13:B0').
```

### Step 4: Verify Backend Logs

Check that backend receives ESP32 connection:
```bash
# Look for MQTT message from ESP32
# Should see vitals/heartbeat messages
```

## Mosquitto Cipher Configuration

### Current Status:
```conf
ciphers AES128-SHA256:AES256-SHA256:ECDHE-RSA-AES128-GCM-SHA256
```

### Recommendation: REVERT to Defaults

**Why:**
- We don't know which ciphers ESP32 mbedTLS supports
- Original config had NO cipher directive (used OpenSSL defaults ~30+ ciphers)
- I restricted from 30+ to 3 ciphers WITHOUT evidence
- Backend works, but only because it supports one of the 3
- ESP32 may not support any of the 3

**Fix for mosquitto.conf:**

**Option 1: Remove cipher directive entirely** (RECOMMENDED)
```conf
# TLS version (1.2 minimum - ESP32 compatible)
tls_version tlsv1.2

# NO cipher directive - use OpenSSL defaults for maximum compatibility
```

**Option 2: Use broad compatibility list**
```conf
ciphers HIGH:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!3DES:!MD5:!PSK
```

**Option 3: ESP32-focused list** (based on research)
```conf
ciphers ECDHE-RSA-AES128-GCM-SHA256:AES128-GCM-SHA256:AES256-GCM-SHA384
```

### My Recommendation:
**Option 1** - Remove cipher directive, let OpenSSL provide defaults. Maximum compatibility, proven to work (original config).

## Complete Fix Implementation

### File 1: `esp32_hospital_watch_complete.ino`

**Remove lines 1007-1009:**
```cpp
  wifiClient.setHandshakeTimeout(30000);  // ❌ DELETE THIS

  Serial.println("🔍 Free heap: " + String(ESP.getFreeHeap()) + " bytes");  // ❌ DELETE THIS
```

**Result:** Function goes directly from `wifiClient.stop()` to loading certificates.

### File 2: `mosquitto/config/mosquitto.conf`

**Option A - Remove cipher directive (line 45-48):**
```conf
# TLS version (1.2 minimum - ESP32 compatible)
tls_version tlsv1.2

# Cipher suites: Using OpenSSL defaults for maximum compatibility
# (No cipher directive = defaults)
```

**OR Option B - Use broader list:**
```conf
# TLS version (1.2 minimum - ESP32 compatible)
tls_version tlsv1.2

# Cipher suites (broad compatibility for ESP32 and Python OpenSSL)
ciphers HIGH:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!3DES:!MD5:!PSK
```

### File 3: Enable Mosquitto Debug Logging (Temporary)

Add to `mosquitto.conf` (after line 112):
```conf
log_type error
log_type warning
log_type notice
log_type information
log_type debug  # ← ADD THIS
```

## Why This Should Work

1. **Socket Creation Order:** Removing `setHandshakeTimeout()` eliminates the errno:9 error
2. **RSA-2048 Speed:** With hardware-accelerated RSA-2048, default timeout is sufficient
3. **Cipher Compatibility:** Reverting to OpenSSL defaults maximizes ESP32 compatibility
4. **Proven Config:** Original mosquitto.conf (no cipher directive) worked for backend
5. **Certificates Valid:** ESP32 has valid RSA-2048 CA, device cert, and private key

## What We Learned (Senior Tech Lead Lessons)

### Mistakes Made:
1. ❌ Added `setHandshakeTimeout()` without understanding socket lifecycle
2. ❌ Changed mosquitto cipher config without knowing ESP32's actual support
3. ❌ Didn't test MQTT connection before claiming "fixed"
4. ❌ Made multiple changes simultaneously (certs + timeout + ciphers)
5. ❌ Assumed ESP32 needed special configuration without evidence

### Correct Approach:
1. ✅ Research ESP32 Arduino Core socket lifecycle
2. ✅ Test ONE change at a time
3. ✅ Keep configuration simple unless proven necessary
4. ✅ Use proven defaults when uncertain
5. ✅ Enable debug logging to see actual negotiation
6. ✅ Verify with user before claiming success

## Next Steps

**User Approval Required:**

1. **Apply ESP32 firmware fix** (remove setHandshakeTimeout line)?
2. **Revert mosquitto.conf cipher config** to defaults or broader list?
3. **Enable Mosquitto debug logging** temporarily?

**Once approved:**
1. I'll make the changes
2. You upload firmware to ESP32
3. Restart Mosquitto container
4. Test ESP32 connection
5. Review Mosquitto debug logs
6. Verify backend still connects
7. Document actual cipher used (from logs)

**No more assumptions. Evidence-based fixes only.**
