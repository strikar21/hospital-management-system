# ESP32 errno 113 Isolation Test - READY

**Date:** 2025-10-19
**Test Status:** ⏳ Ready to Flash ESP32

---

## Test Purpose

Determine if errno 113 is caused by **client certificate** or something else.

---

## Changes Applied

### 1. Mosquitto Config ✅
**File:** [mosquitto/config/mosquitto.conf](mosquitto/config/mosquitto.conf#L37)

**Line 37:**
```conf
require_certificate false  # Was: true
```

**Effect:** Mosquitto now accepts TLS connections WITHOUT client certificates.

### 2. ESP32 Code ✅
**File:** [esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1011-L1019)

**Lines 1011-1019:**
```cpp
// ⚠️ TEMPORARILY DISABLED FOR TESTING (errno 113 debug)
// Testing TLS without client certificate to isolate the problem
// wifiClient.setCertificate(deviceCertificate.c_str());
// wifiClient.setPrivateKey(devicePrivateKey.c_str());

Serial.println("   ⚠️  CLIENT CERT DISABLED (testing TLS only)");
```

**Effect:** ESP32 will use TLS with CA validation ONLY (no client cert).

### 3. ESP32 Code - NTP Requirement Removed ✅
**File:** [esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L602-L606)

**Lines 602-606:**
```cpp
// ⚠️ TEMPORARILY REMOVED NTP REQUIREMENT FOR TESTING
if (wifiConnected && !isProvisioned && !provisioningInProgress && millis() - lastProvisionAttempt > 15000) {
  lastProvisionAttempt = millis();
  attemptProvisioning();
}
```

**Effect:** Provisioning will proceed even if NTP sync fails. **THIS WAS THE BLOCKER** preventing the device from even attempting to provision and connect to MQTT.

### 4. Mosquitto Restart ✅
```bash
docker restart hospital_mosquitto
```

Mosquitto restarted successfully with new config.

---

## Expected Serial Output

### If Test SUCCEEDS (No errno 113):
```
🔐 Certificates loaded:
   CA: 1436 bytes (global)
   Device cert: 1619 bytes (global)
   Device key: 1704 bytes (global)
🔐 Setting TLS certificates in wifiClient...
   ✅ CA cert set
   ⚠️  CLIENT CERT DISABLED (testing TLS only)
✅ MQTT client configured with certificates

🔍 === TLS HANDSHAKE DIAGNOSTICS ===
📊 Free heap BEFORE MQTT connect: 142556 bytes
...
🔄 Connecting to MQTT with client certificate...
✅ MQTT Connected with client certificate (mTLS)!  <- (Actually TLS only now)
📡 Subscribed to: hospital/devices/ESP32-WATCH-A0:A3:B3:AA:13:B0/assign
```

**Conclusion if SUCCESS:** Client certificate is causing errno 113.

**Next Steps:**
1. Examine device certificate format/content
2. Check if ESP32 mbedTLS has issues with specific cert fields
3. Try regenerating device cert with different parameters

---

### If Test FAILS (Still errno 113):
```
🔐 Certificates loaded:
   CA: 1436 bytes (global)
   Device cert: 1619 bytes (global)
   Device key: 1704 bytes (global)
🔐 Setting TLS certificates in wifiClient...
   ✅ CA cert set
   ⚠️  CLIENT CERT DISABLED (testing TLS only)
✅ MQTT client configured with certificates

🔍 === TLS HANDSHAKE DIAGNOSTICS ===
📊 Free heap BEFORE MQTT connect: 142556 bytes
...
🔄 Connecting to MQTT with client certificate...
[ 75931][E][ssl_client.cpp:150] start_ssl_client(): socket error on fd 50, errno: 113
❌ MQTT Connection failed, rc=-2
```

**Conclusion if FAILS:** NOT a client cert issue.

**Next Steps:**
1. Try different MQTT library (AsyncMqttClient or esp-mqtt)
2. Check ESP32 Arduino core version (try downgrade/upgrade)
3. Test with setInsecure() (no cert validation at all)
4. Check for WiFiClientSecure library bug

---

## Mosquitto Logs to Check

After flashing ESP32, check:

```bash
docker logs hospital_mosquitto --since 1m -f
```

**If SUCCESS:**
```
New connection from 192.168.0.148:xxxxx on port 8883.
New client connected from 192.168.0.148 as HospitalWatch_ESP32-WATCH-A0:A3:B3:AA:13:B0 (p2, c1, k60).
```

**If FAILS:**
Still zero connection attempts from 192.168.0.148.

---

## Backend Impact

**Backend WILL FAIL** to connect because:
- Backend still sends client certificate
- Mosquitto `require_certificate false` but backend presents cert anyway
- Mosquitto will reject it with "not authorised"

**This is expected and temporary.** We're only testing ESP32.

To fix backend temporarily (if needed):
```python
# In mqtt_service.py, comment out client cert:
# cert_reqs=ssl.CERT_REQUIRED,
# certfile=self.backend_cert_path,
# keyfile=self.backend_key_path,
```

But we don't need backend working for this test - only ESP32.

---

## Revert Plan

After test completes:

### 1. Revert Mosquitto Config
`mosquitto/config/mosquitto.conf` line 37:
```conf
require_certificate true  # Restore
```

### 2. Revert ESP32 Code
`esp32_hospital_watch_complete.ino` lines 1011-1019:
```cpp
wifiClient.setCertificate(deviceCertificate.c_str());
Serial.println("   ✅ Device cert set");

wifiClient.setPrivateKey(devicePrivateKey.c_str());
Serial.println("   ✅ Private key set");
```

### 3. Restart Mosquitto
```bash
docker restart hospital_mosquitto
```

---

## Ready to Test

**USER ACTION REQUIRED:**

1. Open Arduino IDE
2. Upload `esp32_hospital_watch_complete.ino` to ESP32
3. Open Serial Monitor
4. Power cycle ESP32 or reset
5. Watch for serial output
6. Report back whether errno 113 still occurs

---

**CRITICAL:**
This test will definitively answer: **Is the client certificate causing errno 113?**

After we know the answer, we can proceed with targeted debugging.
