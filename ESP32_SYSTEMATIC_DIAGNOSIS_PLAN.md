# ESP32 MQTT Connection - Systematic Diagnosis Plan

## Current Status

**ESP32 Error:** `errno: 113, "Software caused connection abort"` during TLS handshake
**Python Test:** Connection SUCCEEDED with correct password from host machine
**Mosquitto:** Running and accessible

## The Mystery

- ✅ Python client on Windows → Mosquitto: **WORKS**
- ❌ ESP32 on same network → Mosquitto: **FAILS**

Both use:
- Same IP: 192.168.0.113:8883
- Same credentials: hospitalEsp32 / ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF/Q=
- Same CA certificate
- Same TLS 1.2

**Why does Python work but ESP32 fails?**

## Systematic Test Plan

### Test 1: Verify Password Actually Changed in Firmware
**Goal:** Confirm the firmware was actually updated with the correct password

**Method:**
```cpp
// Add debug output in attemptProvisioning()
Serial.println("DEBUG: MQTT Password = " + mqttPassword);
```

**Expected:** Should show `/Q=` not `+Q=`

---

### Test 2: Check Certificate Format
**Goal:** Verify ESP32 CA certificate is valid

**Method:**
```bash
# Compare certificates byte-by-byte
diff esp32_hospital_watch_complete/data/ca.crt mosquitto/certs/ca.crt
```

**Expected:** Files should be identical

---

### Test 3: Test Without TLS (Temporarily)
**Goal:** Isolate if issue is TLS-specific or MQTT-specific

**Method:** Add temporary test mode in firmware:
```cpp
void configureTLS() {
  // TEMPORARY: Skip TLS validation to test
  wifiClient.setInsecure();
  Serial.println("WARNING: TLS validation DISABLED for testing");
}
```

**If this works:** Issue is certificate/TLS configuration
**If this fails:** Issue is MQTT protocol or credentials

---

### Test 4: Connect to Non-TLS Port (Temporarily)
**Goal:** Test if MQTT works at all

**Method:**
1. Add listener to Mosquitto on port 1883 (no TLS)
2. Change ESP32 to connect to 1883
3. Remove TLS setup

**If this works:** Issue is definitely TLS
**If this fails:** Issue is MQTT or credentials

---

### Test 5: Verify Mosquitto Sees Connection Attempt
**Goal:** Check if ESP32 packets even reach Mosquitto

**Method:**
```bash
# Watch Mosquitto logs in real-time during ESP32 connection
docker logs hospital-mosquitto -f
```

**Expected:** Should see connection attempts from 192.168.0.148
**If NOT seen:** Network routing issue between ESP32 and Mosquitto

---

### Test 6: Check ESP32 Can Reach Broker
**Goal:** Verify basic network connectivity

**Method:** Add in firmware before MQTT connect:
```cpp
Serial.println("Testing TCP connection to broker...");
WiFiClient testClient;
if (testClient.connect(mqttServer.c_str(), mqttPort.toInt())) {
  Serial.println("TCP connection successful!");
  testClient.stop();
} else {
  Serial.println("TCP connection FAILED!");
}
```

**Expected:** TCP should succeed even if TLS fails

---

## Most Likely Root Causes (Ranked)

### 1. Certificate Mismatch Between ESP32 and Mosquitto (80% likely)
**Symptoms:** TLS handshake fails immediately
**Fix:** Ensure ESP32 SPIFFS ca.crt is EXACT copy of mosquitto/certs/ca.crt

### 2. ESP32 TLS Library Not Compatible with Mosquitto TLS (15% likely)
**Symptoms:** Socket error during TLS negotiation
**Fix:** Try `wifiClient.setInsecure()` to skip validation

### 3. Mosquitto Server Certificate Doesn't Match IP (3% likely)
**Symptoms:** TLS verification fails
**Fix:** Regenerate server certificate with correct IP in SAN

### 4. ESP32 WiFiClientSecure Buffer Size Issue (2% likely)
**Symptoms:** Connection abort during handshake
**Fix:** Increase buffer size or reduce certificate size

## Recommended Action Sequence

### Step 1: Add Debug Output (5 minutes)
Add this to `attemptProvisioning()` before connect:
```cpp
Serial.println("=== MQTT CONNECTION DEBUG ===");
Serial.println("Server: " + mqttServer + ":" + mqttPort);
Serial.println("Username: " + mqttUsername);
Serial.println("Password: " + mqttPassword.substring(0, 20) + "..." + mqttPassword.substring(mqttPassword.length()-4));
Serial.println("CA Cert Length: " + String(caCertificate.length()));
Serial.println("============================");
```

Upload and check output confirms correct values.

### Step 2: Try Insecure Mode (10 minutes)
Change `configureTLS()` to:
```cpp
void configureTLS() {
  wifiClient.setInsecure();  // SKIP CERTIFICATE VALIDATION
  Serial.println("TLS: Insecure mode (NO certificate validation)");
}
```

**If this works:** Certificate is the problem
**If this fails:** Credentials or protocol is the problem

### Step 3: Based on Step 2 Result

**IF INSECURE WORKS:**
- Compare certificates byte-by-byte
- Re-upload ca.crt to SPIFFS
- Verify server certificate has correct IP in SAN

**IF INSECURE FAILS:**
- Check password is actually changed in firmware
- Try non-TLS connection (port 1883)
- Check Mosquitto ACL configuration

## Emergency Fallback Options

### Option A: Use HTTP Provisioning Instead
Revert to v3.3.0 firmware that used HTTP provisioning (worked before)

### Option B: Use Non-TLS MQTT
Configure Mosquitto for port 1883 without TLS
- Less secure but will work
- Can add TLS later once basic MQTT works

### Option C: Use Different MQTT Library
Try different ESP32 MQTT library (e.g., AsyncMQTT)

## Decision Tree

```
ESP32 MQTT Connection Fails
    |
    ├─ Add debug output → Verify password changed?
    │   ├─ NO → Re-upload firmware
    │   └─ YES → Continue
    |
    ├─ Try setInsecure() → Does it work?
    │   ├─ YES → Certificate problem
    │   │   └─ Fix: Compare & replace certificates
    │   └─ NO → Not certificate
    │       |
    │       ├─ Try port 1883 (no TLS) → Does it work?
    │       │   ├─ YES → TLS protocol problem
    │       │   └─ NO → MQTT or credentials problem
    │       |
    │       └─ Check Mosquitto logs → See connection?
    │           ├─ YES → Mosquitto rejecting
    │           └─ NO → Network routing problem
```

## Next Immediate Action

**I recommend Step 2: Try Insecure Mode**

This will tell us if the issue is:
- Certificate validation (if insecure works)
- OR something else (if insecure also fails)

Shall I create a test firmware with insecure mode enabled for diagnosis?
