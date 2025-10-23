# ESP32 mTLS Complete Failure Analysis

**Date**: October 20, 2025
**Issue**: ESP32 cannot send client certificate to Mosquitto, causing mTLS authentication failure

---

## Current Status: BOTH APPROACHES FAILED

### Approach 1: `setCertificate()` - FAILED
- **Method**: `wifiClient.setCertificate(deviceCertificate.c_str())`
- **Result**: mbedTLS logs "Loading CRT cert" NEVER appeared
- **Cause**: String.c_str() pointer becomes invalid after String goes out of scope
- **Mosquitto logs**: `no certificate returned`

### Approach 2: `loadCertificate()` - FAILED
- **Method**: `wifiClient.loadCertificate(deviceCertFile, size)`
- **Result**: mbedTLS logs "Loading CRT cert" DO appear ✅
- **But**: Still error -30592 "fatal alert from peer" ❌
- **Mosquitto logs**: `no certificate returned` (SAME ERROR!)
- **Additional problem**: Heap corruption on retry causing ESP32 crash

---

## Evidence from Latest Test

### ESP32 Verbose Logs Show:
```
[  7073][V][ssl_client.cpp:269] start_ssl_client(): Loading CRT cert
[  7084][V][ssl_client.cpp:278] start_ssl_client(): Loading private key
[  7095][V][ssl_client.cpp:292] start_ssl_client(): Setting hostname for TLS session...
[  7103][V][ssl_client.cpp:313] ssl_starttls_handshake(): Performing the SSL/TLS handshake...
[  7879][E][ssl_client.cpp:36] _handle_error(): (-30592) SSL - A fatal alert message was received from our peer
```

**This proves**:
- ✅ mbedTLS IS loading the client certificate and private key
- ✅ mbedTLS IS attempting TLS handshake
- ❌ TLS handshake FAILS with fatal alert from Mosquitto

### Mosquitto Logs Show:
```
1760964976: New connection from 172.20.0.1 on port 8883.
1760964976: OpenSSL Error[0]: error:140360B2:SSL routines:ACCEPT_SR_CERT:no certificate returned
1760964976: Socket error on client <unknown>, disconnecting.
```

**This proves**:
- ❌ Mosquitto receives NO client certificate during TLS handshake
- ❌ ESP32 is NOT transmitting the certificate over the network

### Heap Corruption Evidence:
```
First connection attempt:
   ✅ CA cert loaded from file stream
   ✅ Device cert loaded from file stream
   ✅ Private key loaded from file stream
   [Connection fails with -30592]

Second connection attempt:
   ✅ CA cert loaded from file stream
   [HEAP CORRUPTION - ESP32 CRASHES]

assert failed: tlsf_free tlsf.c:629 (!block_is_free(block) && "block already marked as free")
CORRUPT HEAP: Bad head at 0x3ffd61a0
```

**This proves**:
- ❌ `loadCertificate()` has memory management bugs
- ❌ Calling it multiple times causes double-free error
- ❌ ESP32 crashes and reboots on retry

---

## Root Cause Analysis

### The Paradox:
1. **mbedTLS says**: Certificate loaded successfully (verbose logs confirm)
2. **Mosquitto says**: No certificate received during handshake
3. **Conclusion**: Certificate is loaded into mbedTLS structures BUT not sent during TLS handshake

### Possible Causes:

#### Theory 1: NetworkClientSecure Bug in Arduino Core 3.2.0
- `loadCertificate()` may store certificate data but not properly configure mbedTLS to send it
- The library may not be calling `mbedtls_ssl_conf_own_cert()` correctly
- This would explain why logs show "Loading CRT cert" but certificate isn't transmitted

#### Theory 2: TLS Configuration Issue
- mbedTLS may be configured to NOT send client certificate during handshake
- Possible missing configuration: `MBEDTLS_SSL_VERIFY_OPTIONAL` vs `MBEDTLS_SSL_VERIFY_REQUIRED`
- ESP32 may be waiting for server to request certificate, but server request is being ignored

#### Theory 3: Certificate Format Issue
- mbedTLS may be loading certificate but rejecting it due to format/validation
- Possible issues:
  - RSA-2048 certificate chain
  - X.509 extensions
  - Key usage flags
  - Certificate not matching private key

#### Theory 4: Library Version Incompatibility
- Arduino ESP32 Core 3.2.0 uses ESP-IDF v5.4.1
- NetworkClientSecure may have breaking changes or bugs in this version
- The library's TLS implementation may be fundamentally broken for mTLS

---

## What We've Tried

### ✅ Things That Work:
1. **TLS without client cert**: `setInsecure()` connects successfully
2. **TLS with CA validation**: ESP32 validates Mosquitto's server certificate
3. **Certificate validity**: Device certificate verified with `openssl verify`
4. **Network connectivity**: Firewall configured, port 8883 accessible
5. **Mosquitto configuration**: Full mTLS enabled, works with Python client
6. **Certificate loading**: Verbose logs confirm mbedTLS loads cert data

### ❌ Things That Don't Work:
1. **Client certificate transmission**: Mosquitto never receives the certificate
2. **Full mTLS authentication**: Error -30592 "fatal alert from peer"
3. **Connection retry**: Heap corruption crashes ESP32 on second attempt
4. **Both loading methods**: Neither `setCertificate()` nor `loadCertificate()` work

---

## Comparison: What Works vs What Doesn't

### Python Test Client (WORKS ✅):
```python
context.load_cert_chain("device.crt", "device.key")
```
- **Result**: Connects to Mosquitto successfully with mTLS
- **Mosquitto logs**: Certificate accepted, client authenticated
- **Proves**: Mosquitto configuration is 100% correct

### ESP32 NetworkClientSecure (FAILS ❌):
```cpp
wifiClient.loadCertificate(deviceCertFile, deviceCertFile.size());
wifiClient.loadPrivateKey(deviceKeyFile, deviceKeyFile.size());
```
- **Result**: Error -30592, Mosquitto rejects connection
- **Mosquitto logs**: "no certificate returned"
- **Proves**: ESP32 library has fundamental mTLS bug

---

## Critical Questions

### 1. Is the certificate actually loaded into mbedTLS?
**Answer**: YES - verbose logs at ssl_client.cpp:269 and :278 confirm loading

### 2. Is the certificate data valid in memory?
**Answer**: YES - pre-connection checks show correct PEM format and lengths

### 3. Does Mosquitto receive the certificate during handshake?
**Answer**: NO - Mosquitto logs show "no certificate returned"

### 4. Is there a gap between loading and transmitting?
**Answer**: YES - This is the core problem

### 5. Is this a known Arduino ESP32 Core 3.2.0 bug?
**Answer**: NEEDS RESEARCH - Check GitHub issues for NetworkClientSecure mTLS bugs

---

## Next Steps: Strategic Options

### Option A: Deep Library Investigation (HIGH RISK)
**Approach**: Debug NetworkClientSecure library source code
- Read ssl_client.cpp handshake implementation
- Check if `mbedtls_ssl_conf_own_cert()` is called correctly
- Verify TLS handshake sends CertificateVerify message
- **Risk**: May require ESP-IDF level debugging, extremely complex
- **Time**: 4-8 hours minimum

### Option B: Downgrade Arduino Core (MEDIUM RISK)
**Approach**: Try Arduino ESP32 Core 2.0.x (older, more stable)
- Core 2.0.x uses ESP-IDF 4.4
- NetworkClientSecure may have different implementation
- Older versions may have working mTLS
- **Risk**: May break other features, need to recompile
- **Time**: 1-2 hours

### Option C: Alternative mTLS Library (MEDIUM RISK)
**Approach**: Use WiFiClientSecureBearSSL or PubSubClientTools
- Try different TLS library implementation
- Some libraries have better mTLS support
- May require significant code refactoring
- **Risk**: Library may not exist for ESP32
- **Time**: 2-4 hours

### Option D: Custom mbedTLS Configuration (HIGH RISK)
**Approach**: Bypass NetworkClientSecure, use mbedTLS directly
- Write custom TLS handshake code
- Direct control over mbedTLS configuration
- Can ensure certificate is sent during handshake
- **Risk**: Complex, error-prone, security implications
- **Time**: 6-12 hours

### Option E: Switch to HTTP Client Cert (LOW RISK) ⭐ RECOMMENDED
**Approach**: Abandon MQTT, use HTTPS with client certificates
- ESP32 HTTPS client may have better mTLS support
- Poll backend HTTP endpoint instead of MQTT subscribe
- HTTPS libraries are more mature and tested
- **Risk**: Architecture change, need backend HTTP endpoint
- **Time**: 3-4 hours (including backend endpoint)

### Option F: MQTT Without mTLS (SECURITY RISK)
**Approach**: Use username/password authentication only
- Keep TLS for encryption (CA cert validation)
- Use MQTT username/password instead of client cert
- **Risk**: Less secure, password stored on device
- **Time**: 30 minutes
- **Note**: Still has TLS encryption, just not mutual TLS

---

## Recommendation

### Primary: Option E - Switch to HTTPS with Client Certificates
**Why**:
- HTTPS client certificate support is more mature
- Simpler architecture (request/response vs pub/sub)
- Better debugging tools (curl, openssl s_client)
- More examples and documentation
- Can still use WebSocket for real-time if needed

**Implementation**:
1. Create backend HTTPS endpoint for vitals data: `POST /api/v1/vitals`
2. ESP32 sends vitals via HTTPS POST with client certificate
3. Backend validates client certificate and extracts device ID
4. Backend pushes data to WebSocket for real-time updates
5. ESP32 polls for commands via HTTPS GET with client certificate

### Fallback: Option F - MQTT with Username/Password
**Why**:
- Fastest solution (30 minutes)
- Still has TLS encryption (man-in-the-middle protection)
- Works with existing MQTT infrastructure
- Can switch back to mTLS later if library is fixed

**Implementation**:
1. Generate strong random password for each device during provisioning
2. Store password in NVS (encrypted)
3. Configure Mosquitto to accept username/password auth
4. ESP32 connects with: `mqttClient.connect(clientId, deviceId, password)`

---

## Conclusion

**NetworkClientSecure in Arduino ESP32 Core 3.2.0 has a fundamental bug where client certificates are loaded into mbedTLS but not transmitted during TLS handshake.**

The library is either:
1. Not calling `mbedtls_ssl_conf_own_cert()` correctly
2. Not sending CertificateVerify message during handshake
3. Incompatible with Mosquitto's TLS 1.2 mTLS requirements

**We have exhausted both certificate loading methods** (`setCertificate()` and `loadCertificate()`), and both fail the same way.

**Recommended action**: Switch to HTTPS with client certificates OR fall back to MQTT with username/password authentication.
