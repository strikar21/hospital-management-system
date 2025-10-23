# ESP32 mTLS Debugging Fixes - Applied

**Date:** 2025-10-19
**Version:** v5.0.1 (Diagnostic)
**File Modified:** `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`

---

## Problem Summary

**ESP32 fails to connect to Mosquitto MQTT broker with mTLS:**
```
[119131][E][ssl_client.cpp:150] start_ssl_client(): socket error on fd 50, errno: 113, "Software caused connection abort"
❌ MQTT Connection failed, rc=-2
```

**Root Cause:** TLS handshake fails on ESP32 side BEFORE reaching Mosquitto (Mosquitto logs show zero connection attempts from ESP32 IP `192.168.0.148`).

---

## Changes Applied

### Fix 1: Added Comprehensive Heap Monitoring ✅

**Purpose:** Identify if TLS failure is due to memory exhaustion

**Changes in `connectToMQTT()` function (lines 998-1077):**

```cpp
// BEFORE TLS setup
Serial.println("📊 Free heap BEFORE TLS setup: " + String(ESP.getFreeHeap()) + " bytes");
Serial.println("📊 Free PSRAM: " + String(ESP.getFreePsram()) + " bytes");

// BEFORE each certificate operation
Serial.println("📊 Free heap BEFORE setCACert: " + String(ESP.getFreeHeap()) + " bytes");
Serial.println("📊 Free heap AFTER setCACert: " + String(ESP.getFreeHeap()) + " bytes");

Serial.println("📊 Free heap BEFORE setCertificate: " + String(ESP.getFreeHeap()) + " bytes");
Serial.println("📊 Free heap AFTER setCertificate: " + String(ESP.getFreeHeap()) + " bytes");

Serial.println("📊 Free heap BEFORE setPrivateKey: " + String(ESP.getFreeHeap()) + " bytes");
Serial.println("📊 Free heap AFTER setPrivateKey: " + String(ESP.getFreeHeap()) + " bytes");

// BEFORE MQTT connection attempt
Serial.println("📊 Free heap BEFORE MQTT connect: " + String(ESP.getFreeHeap()) + " bytes");

// AFTER connection (success or failure)
Serial.println("📊 Free heap AFTER MQTT connect: " + String(ESP.getFreeHeap()) + " bytes");
```

**What This Reveals:**
- How much heap is consumed by each certificate operation
- If ESP32 is running out of memory during TLS handshake
- At which exact step memory exhaustion occurs (if that's the issue)

**Expected Heap Values:**
- **Normal:** >50KB free before TLS setup, ~30-40KB after certificates loaded
- **Problem:** <20KB free, suggests memory exhaustion

---

### Fix 2: Removed `wifiClient.stop()` Call ✅

**Problem:** Line 1002 previously called `wifiClient.stop()` which:
- Closes the underlying socket
- Corrupts TLS context
- Causes "Bad file number" (errno 9) errors

**Before:**
```cpp
void connectToMQTT() {
  if (!wifiConnected || !isProvisioned) return;

  // Clear any existing TLS connection state
  wifiClient.stop();  // ❌ THIS WAS THE PROBLEM

  // Load certs...
  wifiClient.setCACert(...);
}
```

**After:**
```cpp
void connectToMQTT() {
  if (!wifiConnected || !isProvisioned) return;

  // ====================================
  // STEP 3: CONFIGURE TLS (NO wifiClient.stop()!)
  // ====================================
  // ✅ FIX: DON'T call wifiClient.stop() - it corrupts TLS context
  // TLS context is already configured in setupMQTT()

  Serial.println("🔐 Setting TLS certificates...");
  // No stop() call - certificates set directly
  wifiClient.setCACert(...);
}
```

**Why This Fixes It:**
- `wifiClient.stop()` invalidates the socket file descriptor
- Subsequent `setCACert()`, `setCertificate()`, `setPrivateKey()` operations fail silently
- TLS handshake attempts to use invalid socket → errno 113 "Software caused connection abort"

---

### Fix 3: Added Detailed Diagnostic Logging ✅

**Purpose:** Provide step-by-step visibility into TLS handshake process

**New Diagnostic Output:**
```
🔍 === TLS HANDSHAKE DIAGNOSTICS ===
📊 Free heap BEFORE TLS setup: XXXXX bytes
📊 Free PSRAM: XXXXX bytes

🔍 Certificate sizes:
   CA: 1436 bytes
   Device cert: 1619 bytes
   Device key: 1704 bytes
   TOTAL: 4759 bytes

🔐 Setting TLS certificates...
📊 Free heap BEFORE setCACert: XXXXX bytes
   ✅ CA cert set
📊 Free heap AFTER setCACert: XXXXX bytes
   ✅ Device cert set
📊 Free heap AFTER setCertificate: XXXXX bytes
   ✅ Private key set
📊 Free heap AFTER setPrivateKey: XXXXX bytes

🔄 Connecting to MQTT with client certificate...
🔐 Device ID (from cert CN): ESP32-WATCH-A0:A3:B3:AA:13:B0
📡 MQTT Server: 192.168.0.113:8883
📊 Free heap BEFORE MQTT connect: XXXXX bytes

// SUCCESS or FAILURE with detailed troubleshooting

🔍 === END DIAGNOSTICS ===
```

**Troubleshooting Guide Added:**
```cpp
Serial.println("\n💡 Troubleshooting:");
Serial.println("   - Check heap memory (should be > 30KB before TLS)");
Serial.println("   - Verify certificate valid (not expired)");
Serial.println("   - Confirm Device ID matches cert CN");
Serial.println("   - Ensure Mosquitto configured for mTLS");
```

---

## Certificate Infrastructure Verification ✅

**Pre-fix verification using `verify-mtls-chain.sh`:**

```
✅ ALL CHECKS PASSED

Certificate chain is valid and ready for mTLS:
  • All certificate files exist
  • CA certificates match (Mosquitto ↔ ESP32)
  • Server and backend certs signed by Hospital CA
  • All private keys match their certificates
  • All certificates are valid (not expired)
```

**Device Certificate Verified:**
```sql
device_id: ESP32-WATCH-A0:A3:B3:AA:13:B0
issued_at: 2025-10-19 10:46:12
expires_at: 2026-10-19 10:46:12
revoked: false
```

**Mosquitto TLS Configuration:**
- TLS 1.2 supported: `ECDHE-RSA-AES256-GCM-SHA384` ✅
- mTLS requires client certificate ✅
- Backend connects successfully as `hospitalBackend` ✅
- Server certificate has correct SANs including `192.168.0.113` ✅

---

## Testing Instructions

### Step 1: Flash Updated Firmware

```bash
# Using Arduino IDE or PlatformIO
# Upload the modified esp32_hospital_watch_complete.ino
```

### Step 2: Monitor Serial Output

**Open Serial Monitor at 115200 baud**

Watch for the new diagnostic section:
```
🔍 === TLS HANDSHAKE DIAGNOSTICS ===
```

### Step 3: Analyze Heap Memory

**Look for these values:**

✅ **GOOD (Enough Memory):**
```
📊 Free heap BEFORE TLS setup: 65432 bytes  ← >50KB = Good
📊 Free heap BEFORE MQTT connect: 35120 bytes  ← >30KB = OK
```

❌ **BAD (Memory Exhaustion):**
```
📊 Free heap BEFORE TLS setup: 18234 bytes  ← <20KB = Problem!
📊 Free heap BEFORE MQTT connect: 8912 bytes  ← <10KB = Critical!
```

### Step 4: Check Mosquitto Logs

```bash
docker logs hospital_mosquitto --tail 50 -f
```

**Success looks like:**
```
New connection from 192.168.0.148:xxxxx on port 8883.
New client connected from 192.168.0.148:xxxxx as HospitalWatch_ESP32-WATCH-A0:A3:B3:AA:13:B0
    (p2, c1, k60, u'ESP32-WATCH-A0:A3:B3:AA:13:B0').
```

**Failure looks like:**
```
(No connection attempts from 192.168.0.148)
```

---

## Expected Results

### Scenario A: Fix Works (wifiClient.stop() was the issue)

**ESP32 Serial:**
```
🔐 Setting TLS certificates...
   ✅ CA cert set
   ✅ Device cert set
   ✅ Private key set
🔄 Connecting to MQTT with client certificate...
✅ MQTT Connected with client certificate (mTLS)!
📡 Subscribed to: hospital/devices/ESP32-WATCH-A0:A3:B3:AA:13:B0/assign
📡 Subscribed to: hospital/devices/ESP32-WATCH-A0:A3:B3:AA:13:B0/command
```

**Mosquitto Logs:**
```
1760872000: New connection from 192.168.0.148:52341 on port 8883.
1760872000: New client connected from 192.168.0.148:52341 as HospitalWatch_ESP32-WATCH-A0:A3:B3:AA:13:B0
    (p2, c1, k60, u'ESP32-WATCH-A0:A3:B3:AA:13:B0').
```

### Scenario B: Memory Exhaustion (needs further optimization)

**ESP32 Serial:**
```
📊 Free heap BEFORE TLS setup: 18432 bytes  ← Too low!
📊 Free heap BEFORE MQTT connect: 8234 bytes  ← Critical!
[E][ssl_client.cpp:150] start_ssl_client(): socket error on fd 50, errno: 113
❌ MQTT Connection failed, rc=-2
```

**Next Steps if Memory Exhaustion:**
1. Increase `CONFIG_ESP32_MAIN_TASK_STACK_SIZE` in sdkconfig
2. Reduce `mqttClient.setBufferSize()` from 4096 to 2048
3. Free up heap by reducing String usage
4. Use static buffers instead of dynamic allocation

### Scenario C: Cipher Suite Mismatch (needs Mosquitto config change)

**ESP32 Serial:**
```
[E][ssl_client.cpp:150] start_ssl_client(): mbedtls_ssl_handshake returned -0x7780
❌ MQTT Connection failed, rc=-2
```

**Mosquitto Logs:**
```
New connection from 192.168.0.148:xxxxx on port 8883.
OpenSSL Error[0]: error:0A0000C1:SSL routines::no shared cipher
Client <unknown> disconnected: Protocol error.
```

**Fix:** Add to `mosquitto/config/mosquitto.conf`:
```conf
ciphers TLS_RSA_WITH_AES_256_CBC_SHA256:TLS_RSA_WITH_AES_128_GCM_SHA256
```

---

## Files Modified

### 1. `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`

**Function:** `connectToMQTT()`
**Lines:** 998-1077

**Changes:**
- ✅ Removed `wifiClient.stop()` call (line 1002)
- ✅ Added heap monitoring (8 measurement points)
- ✅ Added step-by-step diagnostic logging
- ✅ Added troubleshooting guide on failure
- ✅ Added certificate size summary (TOTAL bytes)

**Unchanged:**
- Certificate loading logic
- MQTT connection logic
- Subscribe topics
- Error handling

---

## Success Criteria

✅ **Primary Goal:** ESP32 connects to Mosquitto with mTLS

**Indicators:**
1. Serial log shows: `✅ MQTT Connected with client certificate (mTLS)!`
2. Mosquitto log shows: `New client connected ... as HospitalWatch_ESP32-WATCH-A0:A3:B3:AA:13:B0`
3. No `errno: 113` or `Bad file number` errors
4. Heap memory remains >30KB before MQTT connect

✅ **Secondary Goal:** Detailed diagnostics for troubleshooting

**Indicators:**
1. Heap measurements show where memory is consumed
2. Certificate sizes logged (CA: 1436, Cert: 1619, Key: 1704 bytes)
3. Clear failure messages with actionable troubleshooting steps

---

## Rollback Plan

If new firmware causes issues, revert to previous version:

**Previous `connectToMQTT()` function:**
```cpp
void connectToMQTT() {
  if (!wifiConnected || !isProvisioned) return;
  wifiClient.stop();  // Problematic line
  // ... rest of function
}
```

**File backup location:** (if created before editing)
- `esp32_hospital_watch_complete.ino.backup`

---

## Next Steps

### After Flashing Firmware:

1. **Monitor Serial Output**
   - Look for diagnostic section
   - Note heap values
   - Check for errors

2. **Check Mosquitto Logs**
   - Watch for connection from `192.168.0.148`
   - Look for `HospitalWatch_ESP32-WATCH-A0:A3:B3:AA:13:B0`

3. **Share Results**
   - Copy full diagnostic output
   - Include heap measurements
   - Note any errors

4. **If Still Failing:**
   - Check heap values (>30KB required)
   - Look for new error codes
   - Verify certificates not corrupted
   - Test with mosquitto_pub using same certs

---

## Summary

**Changes Made:**
- ✅ Removed socket-corrupting `wifiClient.stop()` call
- ✅ Added 8-point heap memory monitoring
- ✅ Added detailed step-by-step diagnostics
- ✅ Added troubleshooting guidance

**Most Likely Fix:**
- Removing `wifiClient.stop()` should resolve errno 113 "Software caused connection abort"

**Diagnostic Value:**
- Heap monitoring will reveal if memory exhaustion is a factor
- Step-by-step logging will pinpoint exact failure point
- Troubleshooting guide provides clear next steps

**Ready for testing.** 🚀
