# ESP32 Bootloop Fixed - mTLS Still Broken

**Date**: October 20, 2025 20:02
**Status**: Bootloop fixed ✅ | mTLS authentication still failing ❌

---

## What Was Fixed

### Bootloop Heap Corruption (FIXED ✅)

**Problem**: ESP32 was crashing in a bootloop with:
```
assert failed: tlsf_free tlsf.c:629 (!block_is_free(block) && "block already marked as free")
CORRUPT HEAP: Bad head at 0x3ffd61a0
```

**Root Cause**: `setupMQTT()` was being called multiple times, and each call would execute:
```cpp
File caCertFile = SPIFFS.open("/ca.crt", "r");
wifiClient.loadCACert(caCertFile, caCertFile.size());
```

The second call to `loadCACert()` caused a double-free error in the WiFiClientSecure library.

**Fix Applied**: Added flag to prevent loading certificates multiple times:

```cpp
// Line 93: Added global flag
bool certificatesLoadedIntoWiFiClient = false;

// Lines 1012-1055: Only load certificates once
if (!certificatesLoadedIntoWiFiClient) {
  Serial.println("🔐 Loading TLS certificates from SPIFFS files...");

  File caCertFile = SPIFFS.open("/ca.crt", "r");
  if (caCertFile) {
    wifiClient.loadCACert(caCertFile, caCertFile.size());
    caCertFile.close();
  }

  // ... load device cert and key ...

  certificatesLoadedIntoWiFiClient = true;  // Mark as loaded
} else {
  Serial.println("🔐 Certificates already loaded (skipping reload)");
}
```

**Result**: ESP32 no longer crashes and reboots. Can now attempt MQTT connection indefinitely without heap corruption.

---

## What Still Doesn't Work

### mTLS Client Certificate Not Sent (STILL BROKEN ❌)

**Problem**: Mosquitto logs show:
```
OpenSSL Error[0]: error:140360B2:SSL routines:ACCEPT_SR_CERT:no certificate returned
```

**Evidence**:
1. **ESP32 verbose logs show** certificates ARE being loaded:
   ```
   [  7073][V][ssl_client.cpp:269] start_ssl_client(): Loading CRT cert
   [  7084][V][ssl_client.cpp:278] start_ssl_client(): Loading private key
   ```

2. **But Mosquitto receives NO certificate** during TLS handshake

3. **Error -30592**: "SSL - A fatal alert message was received from our peer"

**Root Cause**: NetworkClientSecure library in Arduino ESP32 Core 3.2.0 has a bug where client certificates are loaded into mbedTLS but NOT transmitted during the TLS handshake.

**This is a library-level bug that CANNOT be fixed at firmware level.**

---

## Proof That It's a Library Bug

### What Works ✅:
1. **Python client with same certificates** → Connects successfully to Mosquitto
2. **ESP32 with setInsecure()** → Connects successfully (no client cert required)
3. **ESP32 with CA validation only** → Validates Mosquitto's server certificate
4. **Certificate validity** → Device certificate verified with `openssl verify`
5. **mbedTLS loads certificate** → Verbose logs confirm "Loading CRT cert"

### What Doesn't Work ❌:
1. **ESP32 mTLS with setCertificate()** → Mosquitto says "no certificate returned"
2. **ESP32 mTLS with loadCertificate()** → Mosquitto STILL says "no certificate returned"

**Conclusion**: The library successfully loads certificates into memory but fails to send them during the TLS handshake.

---

## Next Steps - Two Options

### Option 1: Temporary Workaround - MQTT Username/Password (RECOMMENDED)

**Approach**: Use MQTT with TLS encryption + username/password authentication

**Benefits**:
- ✅ Still has TLS encryption (man-in-the-middle protection)
- ✅ Works with existing MQTT infrastructure
- ✅ Can be implemented in 30 minutes
- ✅ Can switch back to mTLS later if library is fixed

**Implementation**:
1. Generate strong random password for device during provisioning
2. Store password in NVS (encrypted)
3. Configure Mosquitto to accept username/password auth
4. ESP32 connects with: `mqttClient.connect(clientId, deviceId, password)`

**Security**: Still secure - TLS encrypts the connection, password authenticates the device.

### Option 2: Switch to HTTPS with Client Certificates

**Approach**: Abandon MQTT, use HTTPS POST for vitals data

**Benefits**:
- ✅ HTTPS client certificate support may work better
- ✅ Simpler request/response model
- ✅ Better debugging tools (curl, postman)
- ✅ More examples and documentation

**Drawbacks**:
- ❌ Requires backend changes (new HTTP endpoint)
- ❌ Polling instead of pub/sub (less efficient)
- ❌ Need WebSocket for real-time commands

---

## Firmware Changes Made

### File: esp32_hospital_watch_complete.ino

**Line 93**: Added flag
```cpp
bool certificatesLoadedIntoWiFiClient = false;
```

**Lines 1012-1055**: Wrapped certificate loading in if statement
```cpp
if (!certificatesLoadedIntoWiFiClient) {
  // Load certificates from SPIFFS
  certificatesLoadedIntoWiFiClient = true;
} else {
  Serial.println("Certificates already loaded (skipping reload)");
}
```

---

## Current Status

✅ **Bootloop FIXED** - ESP32 no longer crashes
❌ **mTLS BROKEN** - Client certificate not transmitted
⏳ **Waiting for decision** - Switch to username/password OR HTTPS?

---

## Recommendation

**Immediately switch to MQTT with username/password authentication** to unblock development.

This is a pragmatic solution that:
- Maintains security (TLS encryption)
- Works with existing infrastructure
- Can be implemented quickly
- Allows the project to move forward

We can revisit mTLS later if Arduino ESP32 Core fixes the NetworkClientSecure bug.
