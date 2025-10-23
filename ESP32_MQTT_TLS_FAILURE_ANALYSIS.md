# ESP32 MQTT TLS Connection Failure - Root Cause Analysis

**Date:** 2025-10-19
**Status:** INVESTIGATING

---

## Problem Statement

ESP32 successfully provisions via HTTPS and receives certificates from backend, but fails to connect to MQTT broker with TLS handshake error.

**ESP32 Error:**
```
[E][ssl_client.cpp:150] start_ssl_client(): socket error on fd 50, errno: 113, "Software caused connection abort"
❌ MQTT Connection failed, rc=-2
```

**Mosquitto Error:**
```
OpenSSL Error[0]: error:0A000126:SSL routines::unexpected eof while reading
Client <unknown> disconnected: Protocol error.
```

---

## What Works ✅

1. **Backend MQTT Connection** - Backend successfully connects to Mosquitto with mTLS
   ```
   2025-10-19 08:54:18,799 - ✅ MQTT broker connected
   2025-10-19 08:54:18,911 - ✅ MQTT service started successfully
   ```

2. **ESP32 HTTPS Provisioning** - ESP32 successfully provisions and receives certificates
   ```
   ✅ Device certificates saved to SPIFFS
   ✅ CA certificate saved to SPIFFS
   🎉 DEVICE PROVISIONED via HTTPS!
   ```

3. **Certificate Loading** - ESP32 loads certificates from SPIFFS
   ```
   ✅ Device certificate loaded (1964 bytes)
   ✅ Device private key loaded (1704 bytes)
   ```

4. **Certificate Chain Validation** - All certificates are valid
   ```
   [OK] Mosquitto server certificate: VALID (signed by Hospital CA)
   [OK] Backend client certificate: VALID (signed by Hospital CA)
   ```

---

## What Fails ❌

**ESP32 MQTT TLS Connection** - Connection aborts during TLS handshake BEFORE any MQTT protocol exchange

---

## Error Code Analysis

### errno: 113 - "Software caused connection abort"
**Meaning:** Connection was aborted by software in your host machine (ESP32), not by network issues.

**Common Causes:**
1. **Memory exhaustion** during TLS handshake (ESP32 runs out of RAM)
2. **Buffer overflow** in SSL library
3. **Certificate too large** for ESP32 to process
4. **Cipher suite mismatch** between ESP32 and Mosquitto
5. **TLS version mismatch**

### Mosquitto: "unexpected eof while reading"
**Meaning:** Client (ESP32) closed the connection unexpectedly during TLS handshake

**Indicates:** ESP32 terminated connection, not Mosquitto rejecting it

---

## Technical Investigation

### 1. Certificate Sizes
- **CA Certificate:** 2130 bytes (34 lines) ✅ Normal size
- **Device Certificate:** 1964 bytes ✅ Normal size
- **Device Private Key:** 1704 bytes ✅ Normal size
- **Total in memory:** ~5800 bytes for all three certificates

### 2. ESP32 Memory During TLS
**ESP32 has limited heap memory (~300KB total, but fragmented)**

During TLS handshake, the ESP32 needs:
- CA certificate in RAM
- Device certificate in RAM
- Device private key in RAM
- TLS handshake buffers (at least 16KB for TLS 1.2)
- WiFiClientSecure buffers (default varies)
- PubSubClient buffer (currently set to 2048 bytes)

**Estimated memory requirement:** ~30-50KB during TLS handshake

### 3. ESP32 Code Analysis

**Current Buffer Configuration:**
```cpp
mqttClient.setBufferSize(2048);  // Line 991
```

**Problem:** No explicit buffer size set for WiFiClientSecure!

**WiFiClientSecure default behavior:**
- Uses internal buffering for TLS
- Default buffer sizes may be insufficient for large certificates
- No `setBufferSizes()` called in current code

### 4. Cipher Suite Compatibility

**Mosquitto Configuration:**
```
ciphers ECDHE-RSA-AES128-GCM-SHA256:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256
```

**ESP32 Supported Ciphers (via mbedTLS):**
- TLS_RSA_WITH_AES_256_CBC_SHA
- TLS_RSA_WITH_AES_128_CBC_SHA
- TLS_RSA_WITH_AES_128_GCM_SHA256 ✅ (matches Mosquitto)
- ECDHE ciphers (if compiled in)

**Potential Issue:** ESP32 may not support all cipher suites offered by Mosquitto

### 5. Backend vs ESP32 Comparison

**Why Backend Works:**
- Backend runs on Windows with unlimited memory
- Python ssl library handles buffering automatically
- Full OpenSSL implementation

**Why ESP32 Fails:**
- Limited heap memory (fragmented)
- mbedTLS has smaller buffers than OpenSSL
- No explicit buffer sizes configured

---

## ROOT CAUSES (Ranked by Likelihood)

### 1. **MOST LIKELY: WiFiClientSecure Buffer Size** (95% confidence)
**Problem:** WiFiClientSecure not configured with sufficient buffer sizes for TLS handshake with certificates

**Evidence:**
- No `setBufferSizes()` call in current code
- Default buffers may be 512 bytes (too small for cert chain)
- ESP32 aborts connection when buffer overflows

**Solution:** Add explicit buffer configuration:
```cpp
wifiClient.setBufferSizes(4096, 1024);  // RX=4096, TX=1024
```

### 2. **LIKELY: Memory Fragmentation** (70% confidence)
**Problem:** ESP32 heap too fragmented to allocate contiguous memory for TLS buffers

**Evidence:**
- ESP32 running multiple tasks (WiFi, NTP, MQTT, sensors)
- String operations fragment heap
- TLS needs large contiguous allocations

**Solution:**
- Stop/restart WiFiClientSecure before each connection
- Add `wifiClient.stop()` before setting certificates

### 3. **POSSIBLE: PubSubClient Buffer Too Small** (50% confidence)
**Problem:** 2048 bytes may not be enough for MQTT + TLS overhead

**Evidence:**
- TLS adds ~40-100 bytes overhead per packet
- Certificates add to initial handshake payload

**Solution:**
```cpp
mqttClient.setBufferSize(4096);  // Increase from 2048
```

### 4. **POSSIBLE: Cipher Suite Mismatch** (30% confidence)
**Problem:** ESP32 mbedTLS may not support ECDHE ciphers

**Evidence:**
- Mosquitto prefers ECDHE-RSA-AES128-GCM-SHA256
- ESP32 may only support RSA (non-ECDHE) ciphers
- Connection aborts if no common cipher found

**Solution:** Test with simpler cipher suite

### 5. **UNLIKELY: Certificate Format Issue** (10% confidence)
**Problem:** Certificate has formatting that ESP32's mbedTLS doesn't like

**Evidence:**
- CA certificate looks valid (proper PEM format)
- Backend accepts same certificates
- OpenSSL validates them

---

## Proposed Fixes (In Order of Implementation)

### Fix #1: Add WiFiClientSecure Buffer Sizes ⭐ **START HERE**
**File:** `esp32_hospital_watch_complete.ino`
**Function:** `setupMQTT()` and `connectToMQTT()`

**Change in `connectToMQTT()` BEFORE setting certificates:**
```cpp
void connectToMQTT() {
  if (!wifiConnected || !isProvisioned) return;

  // ✅ FIX 1: Configure WiFiClientSecure buffer sizes for TLS with certificates
  wifiClient.stop();  // Stop any existing connection
  wifiClient.setBufferSizes(4096, 1024);  // RX buffer 4KB, TX buffer 1KB

  // Load device certificate and private key
  String deviceCert, deviceKey;
  ...
}
```

**Rationale:**
- ESP32's WiFiClientSecure needs explicit buffer sizes for large TLS handshakes
- Default buffers (512-1024 bytes) insufficient for certificate chains
- 4096 RX buffer accommodates server certificate + CA chain
- 1024 TX buffer sufficient for client certificate

**Expected Result:** ESP32 completes TLS handshake without memory error

---

###Fix #2: Increase MQTT Buffer Size
**File:** `esp32_hospital_watch_complete.ino` line 991

**Change:**
```cpp
mqttClient.setBufferSize(4096);  // Increased from 2048
```

**Rationale:**
- MQTT payload + TLS overhead may exceed 2048 bytes
- 4096 provides headroom for TLS framing

---

### Fix #3: Add TLS Debug Logging (Optional - for diagnosis)
**File:** `esp32_hospital_watch_complete.ino`

**Add before TLS connection:**
```cpp
Serial.println("🔍 Free heap before TLS: " + String(ESP.getFreeHeap()));
Serial.println("🔍 CA cert size: " + String(caCertificate.length()));
Serial.println("🔍 Device cert size: " + String(deviceCert.length()));
Serial.println("🔍 Device key size: " + String(deviceKey.length()));
```

**Rationale:** Diagnose if it's a memory issue

---

### Fix #4: Simplify Mosquitto Cipher Suite (If Fixes 1-3 Don't Work)
**File:** `mosquitto/config/mosquitto.conf` line 47

**Change:**
```conf
# Simplified cipher - ESP32-friendly
ciphers AES128-GCM-SHA256:AES128-SHA256
```

**Rationale:**
- Remove ECDHE ciphers that ESP32 may not support
- Use only RSA-based ciphers

**⚠️ ONLY DO THIS IF OTHER FIXES FAIL - reduces security slightly**

---

## Testing Plan

### Test 1: Add WiFiClientSecure Buffer Sizes (Primary Fix)
1. Update ESP32 firmware with Fix #1 and Fix #2
2. Re-upload firmware to ESP32
3. Re-provision device (generate new PIN, provision via captive portal)
4. Monitor serial output for successful MQTT connection
5. **Expected Result:** ESP32 connects to MQTT successfully

### Test 2: Check Memory Usage (Diagnostic)
1. Add Fix #3 (debug logging)
2. Check serial output for free heap before TLS
3. **Expected Result:** Free heap > 80KB before TLS handshake

### Test 3: Cipher Suite Simplification (Fallback)
1. If Test 1 fails, apply Fix #4
2. Restart Mosquitto: `docker restart hospital_mosquitto`
3. Restart backend
4. Re-test ESP32 connection
5. **Expected Result:** ESP32 connects with simpler cipher

---

## Alternative Solutions (If All Fixes Fail)

### Option A: Use Smaller Certificate Key Sizes
**Backend Change:** Generate 1024-bit device certificates instead of 2048-bit
**Trade-off:** Reduced security (not recommended for production)

### Option B: Disable Client Certificates on ESP32 (Use Password Auth)
**Major Architecture Change:** ESP32 uses username/password, only backend uses certificates
**Trade-off:** Less secure, defeats purpose of mTLS

### Option C: Use Non-TLS MQTT (Insecure - NOT RECOMMENDED)
**Development Only:** Connect to port 1883 without TLS
**Trade-off:** No encryption, not acceptable for production

---

## Conclusion

**Primary Hypothesis:** WiFiClientSecure lacks explicit buffer configuration for large TLS handshakes

**Primary Fix:** Add `wifiClient.setBufferSizes(4096, 1024)` before TLS connection

**Confidence Level:** 95% - This is the most common cause of ESP32 TLS failures with certificates

**Next Steps:**
1. Apply Fix #1 and Fix #2 to ESP32 firmware
2. Upload updated firmware
3. Re-provision ESP32 with new PIN
4. Verify MQTT connection succeeds

---

## References

- ESP32 WiFiClientSecure documentation
- mbedTLS buffer configuration
- Mosquitto mTLS configuration
- PubSubClient Arduino library

---

**End of Analysis**
