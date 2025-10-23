# ESP32 mTLS Fix Applied - Ready for Testing

**Date:** 2025-10-19
**Fix:** Removed duplicate `setCACert()` call
**Status:** ✅ Code changed, ready to flash and test

---

## What Was Changed

**File:** `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`
**Function:** `setupMQTT()`
**Lines:** 980-988

### BEFORE (Duplicate setCACert):
```cpp
// ✅ v5.0: Configure TLS with CA certificate (client cert added in connectToMQTT)
if (caCertificate.length() > 0) {
  wifiClient.setCACert(caCertificate.c_str());  // ← REMOVED THIS
  Serial.println("🔐 TLS configured with Hospital CA certificate");
} else {
  Serial.println("⚠️ WARNING: No CA certificate - using insecure mode");
  wifiClient.setInsecure();
}
```

### AFTER (Single Certificate Configuration):
```cpp
// ✅ v5.0.1: TLS certificates (CA + device cert + key) set together in connectToMQTT()
// Removed setCACert() from here to avoid duplicate calls causing errno 113
if (caCertificate.length() > 0) {
  Serial.println("🔐 CA certificate loaded (" + String(caCertificate.length()) + " bytes)");
  Serial.println("   TLS will be configured with all certificates on MQTT connect");
} else {
  Serial.println("⚠️ WARNING: No CA certificate - TLS will fail!");
  wifiClient.setInsecure();
}
```

### What Happens Now

**All certificates set in ONE place (`connectToMQTT()` lines 1032-1040):**
1. `wifiClient.setCACert(caCertificate.c_str());`
2. `wifiClient.setCertificate(deviceCert.c_str());`
3. `wifiClient.setPrivateKey(deviceKey.c_str());`

**No more duplicate `setCACert()` calls = No more errno 113 (hopefully!)**

---

## How to Test

### Step 1: Flash Firmware

**Arduino IDE:**
1. Open the `.ino` file in Arduino IDE
2. Select ESP32 board and COM port
3. Click Upload (→)
4. Wait for "Done uploading"

**OR PlatformIO:**
```bash
cd esp32_hospital_watch_complete
pio run --target upload
```

### Step 2: Open Serial Monitor

**Baud Rate:** 115200

### Step 3: Provision the Device

1. Connect to `HospitalWatch` WiFi network
2. Captive portal should open automatically
3. Select `NETGEAR05` network
4. Enter WiFi password
5. Server IP: `192.168.0.113`
6. HTTP Port: `8001`
7. MQTT Port: `8883`
8. Enter 6-digit provisioning code
9. Click "Configure & Connect"

### Step 4: Watch Serial Output

**Look for NEW output:**
```
🔧 Configuring MQTT client...
📡 MQTT Server: 192.168.0.113:8883
🔐 CA certificate loaded (1436 bytes)
   TLS will be configured with all certificates on MQTT connect  ← NEW!
✅ MQTT client configured

🔍 === TLS HANDSHAKE DIAGNOSTICS ===
📊 Free heap BEFORE TLS setup: XXXXX bytes
...
🔐 Setting TLS certificates...
   ✅ CA cert set
   ✅ Device cert set
   ✅ Private key set
🔄 Connecting to MQTT with client certificate...
```

**SUCCESS looks like:**
```
✅ MQTT Connected with client certificate (mTLS)!  ← THIS IS WHAT WE WANT!
📡 Subscribed to: hospital/devices/ESP32-WATCH-A0:A3:B3:AA:13:B0/assign
📡 Subscribed to: hospital/devices/ESP32-WATCH-A0:A3:B3:AA:13:B0/command
```

**FAILURE still shows:**
```
[E][ssl_client.cpp:150] start_ssl_client(): socket error on fd 50, errno: 113
❌ MQTT Connection failed, rc=-2
```

### Step 5: Check Mosquitto Logs (In Another Terminal)

```bash
docker logs hospital_mosquitto --tail 50 -f
```

**SUCCESS looks like:**
```
New connection from 192.168.0.148:xxxxx on port 8883.
New client connected from 192.168.0.148:xxxxx as HospitalWatch_ESP32-WATCH-A0:A3:B3:AA:13:B0
    (p2, c1, k60, u'ESP32-WATCH-A0:A3:B3:AA:13:B0').
```

**FAILURE shows:**
```
(No connection attempts from 192.168.0.148)
```

---

## Expected Results

### Scenario A: Fix Worked ✅

**ESP32 Serial:**
```
🔐 CA certificate loaded (1436 bytes)
   TLS will be configured with all certificates on MQTT connect
...
🔐 Setting TLS certificates...
   ✅ CA cert set
   ✅ Device cert set
   ✅ Private key set
✅ MQTT Connected with client certificate (mTLS)!
📊 Free heap AFTER MQTT connect: 140000+ bytes
```

**Mosquitto Logs:**
```
New connection from 192.168.0.148
New client connected ... as HospitalWatch_ESP32-WATCH-A0:A3:B3:AA:13:B0
```

**What This Means:**
- ✅ The duplicate `setCACert()` was causing errno 113
- ✅ ESP32 now successfully connects to Mosquitto with mTLS
- ✅ Problem solved!

---

### Scenario B: Still Fails (errno 113) ❌

**ESP32 Serial:**
```
🔐 CA certificate loaded (1436 bytes)
   TLS will be configured with all certificates on MQTT connect
...
🔐 Setting TLS certificates...
   ✅ CA cert set
   ✅ Device cert set
   ✅ Private key set
[E][ssl_client.cpp:150] start_ssl_client(): socket error on fd 50, errno: 113
❌ MQTT Connection failed, rc=-2
```

**Mosquitto Logs:**
```
(No connection from 192.168.0.148)
```

**What This Means:**
- ❌ Duplicate `setCACert()` was NOT the root cause
- ❌ Issue is something else (library bug, cipher mismatch, etc.)
- ⚠️ Need to try alternate solutions

**Next Steps if This Happens:**
1. Try disabling mTLS requirement in Mosquitto temporarily (test without client cert)
2. Try different MQTT library (AsyncMqttClient instead of PubSubClient)
3. Check for ESP32 Arduino core bugs

---

### Scenario C: Different Error ⚠️

If you see a DIFFERENT error (not errno 113), share the full serial output.

---

## What to Share After Testing

**Please share:**

1. **Full serial output** from provisioning through connection attempt
2. **Mosquitto logs** during connection attempt
3. **Whether it worked or not**

**I need to see:**
- The new log line: `TLS will be configured with all certificates on MQTT connect`
- Whether errno 113 still appears
- What Mosquitto sees (if anything)

---

## Rollback (If Needed)

If this breaks something, revert lines 980-988 to:

```cpp
if (caCertificate.length() > 0) {
  wifiClient.setCACert(caCertificate.c_str());
  Serial.println("🔐 TLS configured with Hospital CA certificate");
} else {
  Serial.println("⚠️ WARNING: No CA certificate - using insecure mode");
  wifiClient.setInsecure();
}
```

---

## Summary

**Change Made:** Removed `wifiClient.setCACert()` call from `setupMQTT()` (line 982)
**Why:** Duplicate certificate setting corrupts LWIP socket, causes errno 113
**Confidence:** 60% this fixes it
**Risk:** Very low (easy to revert)

**Now:** Flash the firmware and test!

**Ready to proceed with testing.** 🚀
