# Comprehensive TLS Cipher Configuration Audit

## Executive Summary

**CRITICAL FINDING:** The ESP32 firmware does **NOT** configure any specific cipher suites. It relies entirely on the ESP32 Arduino Core's default mbedTLS cipher configuration, which is determined at compile time.

**Current Status:**
- ❓ ESP32 cipher support: **UNKNOWN** (depends on mbedTLS compile-time config)
- ✅ Backend cipher config: Uses Python OpenSSL defaults (`ciphers=None`)
- ✅ Mosquitto cipher config: Custom list (recently modified)

## File-by-File Analysis

### 1. ESP32 Firmware: `esp32_hospital_watch_complete.ino`

**TLS Configuration Code:**

```cpp
// Line 30
#include <WiFiClientSecure.h>

// Line 60
WiFiClientSecure wifiClient;

// Lines 980-987 (setupMQTT function)
if (caCertificate.length() > 0) {
  wifiClient.setCACert(caCertificate.c_str());
  Serial.println("🔐 TLS configured with Hospital CA certificate");
} else {
  Serial.println("⚠️ WARNING: No CA certificate - using insecure mode");
  wifiClient.setInsecure();
}

// Lines 1002-1027 (connectToMQTT function)
wifiClient.stop();
wifiClient.setHandshakeTimeout(30000);  // 30 seconds
wifiClient.setCACert(caCertificate.c_str());
wifiClient.setCertificate(deviceCert.c_str());
wifiClient.setPrivateKey(deviceKey.c_str());
```

**CRITICAL OBSERVATION:**
- ✅ Sets CA certificate
- ✅ Sets client certificate (mTLS)
- ✅ Sets private key
- ✅ Sets handshake timeout
- ❌ **DOES NOT SET CIPHER SUITES** - No `.setCiphers()` or similar call

**What This Means:**
The ESP32 will use whatever ciphers are **compiled into mbedTLS** in the ESP32 Arduino Core. This is determined at the Arduino Core build time, NOT at runtime.

**ESP32 Arduino Core 3.x mbedTLS Default Ciphers** (typical configuration):
Based on standard ESP-IDF mbedTLS config, likely includes:
- `TLS-ECDHE-RSA-WITH-AES-128-GCM-SHA256` ✅
- `TLS-ECDHE-RSA-WITH-AES-256-GCM-SHA384` ✅
- `TLS-DHE-RSA-WITH-AES-128-GCM-SHA256` ❓
- `TLS-DHE-RSA-WITH-AES-256-GCM-SHA384` ❓
- `TLS-RSA-WITH-AES-128-GCM-SHA256` ✅
- `TLS-RSA-WITH-AES-256-GCM-SHA384` ✅
- `TLS-RSA-WITH-AES-128-CBC-SHA256` ✅
- `TLS-RSA-WITH-AES-256-CBC-SHA256` ✅
- `TLS-RSA-WITH-AES-128-CBC-SHA` ✅ (for TLS 1.2 backwards compat)
- `TLS-RSA-WITH-AES-256-CBC-SHA` ✅

**Important Notes:**
- ESP32 mbedTLS likely **DOES support** `AES128-GCM-SHA256`
- ESP32 mbedTLS likely **DOES support** `ECDHE-RSA-AES128-GCM-SHA256`
- ESP32 mbedTLS **MAY OR MAY NOT support** `AES128-SHA256` specifically

**OpenSSL vs mbedTLS Cipher Naming:**
- OpenSSL: `AES128-SHA256`
- mbedTLS: `TLS-RSA-WITH-AES-128-CBC-SHA256`

These might be the **SAME** cipher, just different naming conventions!

### 2. Backend MQTT Service: `hospital-backend/app/services/mqtt_service.py`

**TLS Configuration Code (Lines 92-100):**

```python
# Configure TLS with client certificate (mTLS)
if self.config.get('use_tls'):
    self.client.tls_set(
        ca_certs=self.config.get('ca_certs'),
        certfile=self.config.get('certfile'),  # Backend client certificate
        keyfile=self.config.get('keyfile'),    # Backend client private key
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLSv1_2,
        ciphers=None  # ← CRITICAL: Uses Python OpenSSL DEFAULT cipher list
    )
```

**CRITICAL OBSERVATION:**
- `ciphers=None` means Python OpenSSL chooses from its compiled cipher list
- Python OpenSSL DEFAULT_CIPHERS (typical list):
  ```
  ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:ECDHE+AES:DHE+AES:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!3DES:!MD5:!PSK
  ```

**Python OpenSSL DEFAULT Cipher Preferences (Priority Order):**
1. `ECDHE-RSA-AES128-GCM-SHA256` ✅ (highest priority)
2. `ECDHE-RSA-AES256-GCM-SHA384` ✅
3. `DHE-RSA-AES128-GCM-SHA256` ✅
4. `DHE-RSA-AES256-GCM-SHA384` ✅
5. `ECDHE-RSA-AES128-SHA256` ✅
6. `ECDHE-RSA-AES256-SHA384` ✅
7. `AES128-GCM-SHA256` ✅
8. `AES256-GCM-SHA384` ✅
9. `AES128-SHA256` ✅ (lower priority)
10. `AES256-SHA256` ✅

**What Backend Will Actually Use:**
Whichever cipher is **HIGHEST PRIORITY** in the Mosquitto cipher list that the backend also supports.

### 3. Mosquitto Configuration: `mosquitto/config/mosquitto.conf`

**Current Configuration (Line 48):**

```conf
ciphers AES128-SHA256:AES256-SHA256:ECDHE-RSA-AES128-GCM-SHA256
```

**Cipher Negotiation Process:**

**Step 1: Client Hello (Backend or ESP32)**
- Client sends list of supported ciphers to Mosquitto
- Client's cipher list is in PRIORITY order (preferred first)

**Step 2: Server Hello (Mosquitto)**
- Mosquitto looks at its configured cipher list: `AES128-SHA256:AES256-SHA256:ECDHE-RSA-AES128-GCM-SHA256`
- Mosquitto **selects the FIRST cipher in its list** that the client also supports
- Mosquitto sends selected cipher back to client

**Backend Connection Negotiation:**
1. Backend sends Python OpenSSL default list (ECDHE-RSA-AES128-GCM-SHA256 is highest)
2. Mosquitto looks at its list: `AES128-SHA256`, `AES256-SHA256`, `ECDHE-RSA-AES128-GCM-SHA256`
3. Backend supports all three, but Mosquitto tries them in ORDER
4. **PROBLEM:** Mosquitto will try `AES128-SHA256` first!
5. **QUESTION:** Does Python OpenSSL support `AES128-SHA256`? **YES** (it's in the default list)
6. **RESULT:** Backend SHOULD connect with `AES128-SHA256`

**ESP32 Connection Negotiation:**
1. ESP32 sends mbedTLS compiled cipher list (unknown, but likely includes ECDHE-RSA-AES128-GCM-SHA256)
2. Mosquitto looks at its list: `AES128-SHA256`, `AES256-SHA256`, `ECDHE-RSA-AES128-GCM-SHA256`
3. **QUESTION:** Does ESP32 mbedTLS support `AES128-SHA256`?
   - **UNKNOWN** - depends on mbedTLS compile config
   - If NO → tries `AES256-SHA256`
   - If still NO → tries `ECDHE-RSA-AES128-GCM-SHA256`
   - If still NO → **CONNECTION FAILS** with "no shared cipher"

## Root Cause Analysis

### Why Backend Connected After Restart

**Timeline:**
1. Mosquitto restarted at 1760849976 (from logs)
2. Backend attempted connection at 1760849977 (failed with "unexpected eof")
3. Backend attempted connection at 1760850000 (SUCCESS)

**Why First Attempt Failed:**
- `OpenSSL Error[0]: error:0A000126:SSL routines::unexpected eof while reading`
- This is NOT a cipher error - it's a TLS handshake interruption
- Likely cause: Backend's MQTT client was reconnecting too fast, before Mosquitto fully initialized

**Why Second Attempt Succeeded:**
- Mosquitto fully initialized
- Backend and Mosquitto negotiated `AES128-SHA256` or `ECDHE-RSA-AES128-GCM-SHA256`
- Connection established successfully

### Why ESP32 Likely Will STILL Fail

**Hypothesis 1: ESP32 mbedTLS Does NOT Support AES128-SHA256**

**Evidence:**
- AES128-SHA256 is NOT a standard mbedTLS cipher name
- mbedTLS uses: `TLS-RSA-WITH-AES-128-CBC-SHA256`
- OpenSSL uses: `AES128-SHA256`
- These might be DIFFERENT ciphers!

**OpenSSL `AES128-SHA256` Details:**
- Full name: `TLS_RSA_WITH_AES_128_CBC_SHA256`
- Key exchange: RSA
- Encryption: AES-128-CBC
- MAC: SHA-256

**mbedTLS Equivalent:**
- mbedTLS name: `TLS-RSA-WITH-AES-128-CBC-SHA256`
- Same cipher, different naming

**CRITICAL QUESTION:** Does mbedTLS recognize OpenSSL cipher names?
- **NO** - mbedTLS and OpenSSL use different naming conventions
- **BUT:** Mosquitto translates between them automatically
- **SO:** If mbedTLS supports the cipher (regardless of name), it should work

**Hypothesis 2: ESP32 mbedTLS ONLY Supports GCM Modes**

Modern ESP-IDF mbedTLS configs often DISABLE CBC mode ciphers for security and disable AES-256 to save flash space.

**Typical ESP32 mbedTLS Enabled Ciphers:**
- `TLS-ECDHE-RSA-WITH-AES-128-GCM-SHA256` ✅
- `TLS-ECDHE-ECDSA-WITH-AES-128-GCM-SHA256` ✅
- `TLS-RSA-WITH-AES-128-GCM-SHA256` ✅

**Typical ESP32 mbedTLS DISABLED Ciphers:**
- `TLS-RSA-WITH-AES-128-CBC-SHA256` ❌ (CBC mode disabled)
- `TLS-RSA-WITH-AES-128-CBC-SHA` ❌ (CBC mode disabled)
- `TLS-RSA-WITH-AES-256-*` ❌ (AES-256 disabled to save space)

**If This is True:**
- ESP32 cannot use `AES128-SHA256` (it's a CBC cipher)
- ESP32 cannot use `AES256-SHA256` (it's AES-256)
- ESP32 CAN use `ECDHE-RSA-AES128-GCM-SHA256` ✅

**Mosquitto Cipher Order:**
```
AES128-SHA256:AES256-SHA256:ECDHE-RSA-AES128-GCM-SHA256
     ❌              ❌                     ✅
   (CBC)         (AES-256)            (ECDHE+GCM)
```

**Result:** ESP32 will negotiate `ECDHE-RSA-AES128-GCM-SHA256` (the 3rd cipher in Mosquitto's list)

**BUT WHY DID IT FAIL BEFORE?**

The ORIGINAL Mosquitto config was:
```
ECDHE-RSA-AES128-GCM-SHA256:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256
```

This STARTS with `ECDHE-RSA-AES128-GCM-SHA256` which ESP32 supports!

**Answer:** The original failure was NOT due to cipher mismatch - it was due to RSA-4096 certificates being too large/slow for ESP32.

## Current Cipher Configuration Assessment

### Mosquitto Current Config: `AES128-SHA256:AES256-SHA256:ECDHE-RSA-AES128-GCM-SHA256`

**Backend (Python OpenSSL):**
- Supported: ✅ All three ciphers
- Will negotiate: `AES128-SHA256` (first in Mosquitto list)
- Security: GOOD (128-bit AES, SHA-256 HMAC, RSA-2048 key exchange)
- Performance: EXCELLENT

**ESP32 (mbedTLS):**
- Supported: ❓ `AES128-SHA256` (if CBC mode enabled)
- Supported: ❓ `AES256-SHA256` (if AES-256 enabled)
- Supported: ✅ `ECDHE-RSA-AES128-GCM-SHA256` (very likely)
- Will negotiate: Depends on mbedTLS config
  - **Best case:** `AES128-SHA256` (if supported)
  - **Likely case:** `ECDHE-RSA-AES128-GCM-SHA256` (if AES128-SHA256 not supported)
  - **Worst case:** Connection fails (if none supported)

## Recommended Mosquitto Cipher Configuration

### Option 1: Prioritize ECDHE-GCM (Modern, Secure)

```conf
ciphers ECDHE-RSA-AES128-GCM-SHA256:AES128-GCM-SHA256:AES128-SHA256
```

**Why:**
- `ECDHE-RSA-AES128-GCM-SHA256` is universally supported (ESP32, Python, modern clients)
- Provides Perfect Forward Secrecy (ECDHE key exchange)
- GCM mode provides authenticated encryption (no need for separate HMAC)
- Falls back to simpler ciphers if ECDHE not available

**Negotiation:**
- Backend: Will use `ECDHE-RSA-AES128-GCM-SHA256` ✅
- ESP32: Will use `ECDHE-RSA-AES128-GCM-SHA256` ✅

### Option 2: Simplified for Maximum Compatibility

```conf
ciphers AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256
```

**Why:**
- `AES128-GCM-SHA256` is simple RSA key exchange with GCM mode
- Supported by both Python OpenSSL and ESP32 mbedTLS
- ECDHE as fallback for clients that prefer it

**Negotiation:**
- Backend: Will use `AES128-GCM-SHA256` or `ECDHE-RSA-AES128-GCM-SHA256` ✅
- ESP32: Will use `AES128-GCM-SHA256` ✅

### Option 3: ORIGINAL Configuration (REVERT)

```conf
ciphers ECDHE-RSA-AES128-GCM-SHA256:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256
```

**Why:**
- This was the ORIGINAL configuration
- It worked for backend (we know this)
- ESP32 failed NOT because of ciphers, but because of RSA-4096 certificates
- Now that we have RSA-2048, this should work

**Negotiation:**
- Backend: Will use `ECDHE-RSA-AES128-GCM-SHA256` ✅
- ESP32: Will use `ECDHE-RSA-AES128-GCM-SHA256` or `AES128-GCM-SHA256` ✅

## Security Analysis

### Cipher Strength Comparison

| Cipher | Key Exchange | Encryption | MAC | PFS | Performance | Security |
|--------|-------------|-----------|-----|-----|-------------|----------|
| `ECDHE-RSA-AES128-GCM-SHA256` | ECDHE (ephemeral) | AES-128-GCM | Built-in | ✅ Yes | Good | ⭐⭐⭐⭐⭐ |
| `AES128-GCM-SHA256` | RSA-2048 | AES-128-GCM | Built-in | ❌ No | Excellent | ⭐⭐⭐⭐ |
| `AES128-SHA256` | RSA-2048 | AES-128-CBC | SHA-256 | ❌ No | Excellent | ⭐⭐⭐⭐ |
| `AES256-SHA256` | RSA-2048 | AES-256-CBC | SHA-256 | ❌ No | Good | ⭐⭐⭐⭐ |

**All ciphers are HIPAA compliant and suitable for medical data.**

## Testing Plan

### Test 1: ESP32 with Current Config (AES128-SHA256 first)

**Current Mosquitto Config:**
```
ciphers AES128-SHA256:AES256-SHA256:ECDHE-RSA-AES128-GCM-SHA256
```

**Test Steps:**
1. Power on ESP32
2. Provision with new PIN
3. Observe serial output

**Expected Results:**
- **If ESP32 supports AES128-SHA256:** ✅ Connection succeeds
- **If ESP32 only supports ECDHE-GCM:** ✅ Connection succeeds (falls back to 3rd cipher)
- **If ESP32 supports neither:** ❌ Connection fails

### Test 2: ESP32 with ECDHE First (Option 1)

**Change Mosquitto Config to:**
```
ciphers ECDHE-RSA-AES128-GCM-SHA256:AES128-GCM-SHA256:AES128-SHA256
```

**Test Steps:**
1. Restart Mosquitto: `docker-compose restart mosquitto`
2. Power on ESP32
3. Provision with new PIN
4. Observe serial output

**Expected Results:**
- **ESP32:** ✅ Connection succeeds (ECDHE-RSA-AES128-GCM-SHA256)
- **Backend:** ✅ Still connected (ECDHE-RSA-AES128-GCM-SHA256)

### Test 3: ESP32 with ORIGINAL Config (Option 3)

**Change Mosquitto Config to:**
```
ciphers ECDHE-RSA-AES128-GCM-SHA256:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256
```

**Test Steps:**
1. Restart Mosquitto: `docker-compose restart mosquitto`
2. Verify backend still connected
3. Power on ESP32
4. Provision with new PIN
5. Observe serial output

**Expected Results:**
- **ESP32:** ✅ Connection succeeds (certificates now RSA-2048)
- **Backend:** ✅ Still connected

## Recommendations

### Immediate Action: Test with Current Config

**DO NOT CHANGE** Mosquitto config yet. Test ESP32 with current config first.

**Reason:**
- We don't know for certain which ciphers ESP32 supports
- Current config might work
- Changing blindly could break backend

### If ESP32 Fails: Enable Mosquitto Debug Logging

**Add to `mosquitto.conf`:**
```conf
log_type debug
```

**Restart Mosquitto:**
```bash
docker-compose restart mosquitto
```

**Check logs:**
```bash
docker logs -f hospital_mosquitto | grep -i "cipher\|tls\|ssl"
```

**Look for:**
```
New connection from 192.168.x.x
OpenSSL: Cipher: ECDHE-RSA-AES128-GCM-SHA256  ← This tells us which cipher was negotiated
Client connected: ESP32-WATCH-xxx
```

OR:
```
OpenSSL Error: no shared cipher  ← This confirms cipher mismatch
```

### If ESP32 Still Fails: Try ECDHE-First Config

**Change Mosquitto to Option 1:**
```conf
ciphers ECDHE-RSA-AES128-GCM-SHA256:AES128-GCM-SHA256:AES128-SHA256
```

**This should work because:**
- ECDHE-RSA-AES128-GCM-SHA256 is standard in ESP32 mbedTLS
- It's also preferred by Python OpenSSL
- Both clients get their preferred cipher

## Conclusion

**Current Status: UNCERTAIN**

We've made good progress:
- ✅ RSA-2048 certificates working
- ✅ Backend connecting to MQTT successfully
- ❓ ESP32 cipher compatibility UNKNOWN

**Next Step:**
**TEST ESP32 WITH CURRENT CONFIG BEFORE MAKING MORE CHANGES**

**Likely Outcome:**
- ESP32 will either connect with `ECDHE-RSA-AES128-GCM-SHA256` (3rd cipher) ✅
- OR fail if mbedTLS doesn't support any of the three ciphers ❌

**If Fails:**
- Enable Mosquitto debug logging
- Review TLS handshake logs
- Adjust cipher list based on actual ESP32 capabilities

**Files to Watch:**
- `mosquitto/config/mosquitto.conf` (line 48 - cipher list)
- ESP32 serial output (look for "MQTT Connected" or rc=-2 error)
- Mosquitto logs (`docker logs hospital_mosquitto`)
