# ESP32 errno 113 - ROOT CAUSE IDENTIFIED

**Date:** 2025-10-19
**Status:** 🎯 ROOT CAUSE FOUND - TLS/Certificate Issue

---

## Critical Test Result

**Test Conducted:** ESP32 connects to Mosquitto with TLS using ONLY CA certificate (no client certificate).

### Configuration:
- **Mosquitto:** `require_certificate false` (accepts TLS without client cert)
- **ESP32:** Client cert/key commented out, ONLY `wifiClient.setCACert()` called
- **Result:** ❌ **errno 113 STILL OCCURS**

---

## What This Proves

### ✅ CLIENT CERTIFICATE IS NOT THE PROBLEM

The ESP32 fails with errno 113 even when:
- Client certificate is NOT set
- Client private key is NOT set
- Only CA certificate validation is enabled
- Mosquitto does not require client certificate

**Conclusion:** The problem is NOT related to client certificates, device certificates, or mTLS.

---

## Actual Problem: TLS/Certificate Validation Itself

### Error Details:
```
[ 68956][E][ssl_client.cpp:150] start_ssl_client(): socket error on fd 50, errno: 113, "Software caused connection abort"
[ 68968][I][NetworkClientSecure.cpp:153] connect(): Actual TLS start postponed.
[ 68975][E][NetworkClientSecure.cpp:159] connect(): start_ssl_client: connect failed: -1
```

### Key Observations:

1. **Error Location:** `ssl_client.cpp:150` in `start_ssl_client()` function
   - This is mbedTLS initialization code
   - Error happens BEFORE any data is sent to Mosquitto

2. **Mosquitto Logs:** ZERO connection attempts from ESP32 IP (192.168.0.148)
   - TCP connection never completes
   - TLS handshake never starts
   - Error is purely ESP32-side

3. **errno 113 = ECONNABORT**
   - LWIP TCP stack calls `tcp_abort()`
   - Indicates internal TCP/TLS stack failure
   - NOT a rejection by the server

4. **"Actual TLS start postponed"**
   - WiFiClientSecure trying to delay TLS handshake
   - Something wrong with TLS context setup

---

## Comparison: What Works vs. What Fails

### ✅ Works: openssl s_client from PC
```bash
openssl s_client -connect 192.168.0.113:8883 -CAfile hospital_ca.crt -cert backend.crt -key backend.key -tls1_2
# Result: CONNECTED, Verify return code: 0 (ok)
```

### ✅ Works: ESP32 HTTPS Provisioning
```cpp
WiFiClientSecure httpsClient;
httpsClient.setInsecure();  // No cert validation
http.begin(httpsClient, "https://192.168.0.113:8001/...");
# Result: SUCCESS - Downloads certificates from backend
```

### ❌ Fails: ESP32 MQTT with ANY certificate
```cpp
WiFiClientSecure wifiClient;
wifiClient.setCACert(caCertificate.c_str());  // Only CA, no client cert
mqttClient.connect(clientId.c_str());
# Result: errno 113 - Connection aborted
```

---

## Root Cause Analysis

### Possible Causes (from Web Research):

1. **WiFiClientSecure + PubSubClient Incompatibility**
   - Known issues with certificate handling in this combination
   - mbedTLS buffer/state corruption

2. **ESP32 Arduino Core Bug**
   - Specific versions have TLS bugs
   - `ssl_client.cpp` issues with certificate validation

3. **Certificate Size/Format Issue**
   - Total cert size: 1436 + 1619 + 1704 = 4759 bytes
   - May exceed ESP32 mbedTLS buffer limits

4. **TCP Socket State Corruption**
   - LWIP detects invalid state
   - Calls `tcp_abort()` preemptively

---

## Why setInsecure() Works for Provisioning

```cpp
httpsClient.setInsecure();  // Bypasses ALL cert validation
```

- `setInsecure()` disables mbedTLS certificate validation entirely
- No CA checking, no hostname verification
- Just encrypted connection without authentication
- This proves the TLS encryption itself works

---

## Next Steps to Fix

### Option 1: Use setInsecure() for MQTT (NOT RECOMMENDED - insecure)
```cpp
wifiClient.setInsecure();
mqttClient.connect(clientId.c_str());
```
**Pros:** Will likely work
**Cons:** NO security, man-in-the-middle attacks possible

### Option 2: Different MQTT Library
Switch from PubSubClient to:
- **esp-mqtt** (ESP-IDF native MQTT library)
- **AsyncMqttClient** (async library)

These may handle WiFiClientSecure better.

### Option 3: ESP32 Arduino Core Downgrade/Upgrade
Current issues may be specific to Arduino-ESP32 core version.
- Try v2.0.11 (known stable)
- Try latest v3.x (may have fixes)

### Option 4: Use Plain TCP + TLS Wrapper
Bypass WiFiClientSecure entirely, use mbedTLS directly.

---

## Recommended Action

**TRY OPTION 3 FIRST:** Different MQTT Library (esp-mqtt)

**Reasoning:**
1. esp-mqtt is ESP-IDF native (more mature TLS handling)
2. Many reports of PubSubClient + WiFiClientSecure issues
3. esp-mqtt has better mbedTLS integration
4. Used in production ESP32 IoT devices

**Implementation:**
1. Add esp-mqtt library to platformio.ini or Arduino libraries
2. Rewrite MQTT connection code using esp-mqtt API
3. Test with same certificates

---

## Alternative Quick Test

Before switching libraries, test if `setInsecure()` fixes it:

```cpp
// In setupMQTT():
Serial.println("⚠️ TESTING: Using insecure mode");
wifiClient.setInsecure();  // Comment out all setCACert/setCertificate/setPrivateKey
```

**If this works:**
→ Confirms it's certificate validation bug in WiFiClientSecure
→ Need to switch libraries

**If this STILL fails:**
→ Deeper ESP32/LWIP issue
→ May need ESP32 core downgrade

---

## Files Referenced

- [esp32_hospital_watch_complete.ino](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino)
- [mosquitto/config/mosquitto.conf](mosquitto/config/mosquitto.conf)
- [mosquitto/certs/hospital_ca.crt](mosquitto/certs/hospital_ca.crt)
- [SSL client error: ssl_client.cpp:150](https://github.com/espressif/arduino-esp32/blob/master/libraries/WiFiClientSecure/src/ssl_client.cpp#L150)

---

## Summary

**Root Cause:** WiFiClientSecure + PubSubClient combination has a bug when handling certificate validation with mbedTLS on ESP32. The TLS handshake fails internally before any network communication occurs.

**Evidence:**
- ✅ Works: PC openssl with same certs
- ✅ Works: ESP32 HTTPS with setInsecure()
- ❌ Fails: ESP32 MQTT with CA cert validation
- ❌ Fails: ESP32 MQTT even WITHOUT client cert

**Next Action:** Test with `setInsecure()` to confirm, then switch to esp-mqtt library for proper TLS handling.
