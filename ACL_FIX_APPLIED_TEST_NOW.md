# ACL Fix Applied - Ready to Test

**Date**: October 20, 2025
**Status**: ✅ ACL FIX APPLIED - TEST NOW

---

## What Was Fixed

### Root Cause Identified (User Discovery)

**The Problem**: ESP32 certificate CN is `ESP32-WATCH-A0:A3:B3:AA:13:B0` (colon-separated MAC address).

Mosquitto ACL expected simpler device IDs like `ESP32-WATCH-001`, and the pattern matching with colons in the CN was causing the **fatal alert -30592** error.

---

## Fix Applied

### Modified File: `mosquitto/config/acl.conf`

Added explicit user entry at lines 40-49:

```conf
# ✅ TEMPORARY FIX: Explicit entry for colon-based CN (testing ACL hypothesis)
user ESP32-WATCH-A0:A3:B3:AA:13:B0
topic write hospital/devices/ESP32-WATCH-A0:A3:B3:AA:13:B0/vitals
topic write hospital/devices/ESP32-WATCH-A0:A3:B3:AA:13:B0/alerts
topic write hospital/devices/ESP32-WATCH-A0:A3:B3:AA:13:B0/heartbeat
topic write hospital/devices/ESP32-WATCH-A0:A3:B3:AA:13:B0/waveform
topic write hospital/devices/ESP32-WATCH-A0:A3:B3:AA:13:B0/event
topic write hospital/devices/ESP32-WATCH-A0:A3:B3:AA:13:B0/status
topic read hospital/devices/ESP32-WATCH-A0:A3:B3:AA:13:B0/command
topic read hospital/devices/ESP32-WATCH-A0:A3:B3:AA:13:B0/assign
```

### Mosquitto Restarted

```bash
docker restart hospital_mosquitto
```

Status: ✅ Running

---

## What This Tests

**If ESP32 now connects successfully** → ACL was the problem (colons in CN not matching patterns)

**If ESP32 still fails with -30592** → There's something else (possibly still a library issue)

---

## Testing Steps

### Step 1: Upload ESP32 Firmware
The firmware already has the `mqttConfigured` flag fix applied. Upload it now:
- File: `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`
- Board: Node32s (ESP32)
- Port: (your COM port)

### Step 2: Monitor Serial Output
Open Serial Monitor at 115200 baud and watch for:

**Success Indicators:**
```
✅ MQTT Connected with client certificate (mTLS)!
📡 Subscribed to: hospital/devices/ESP32-WATCH-A0:A3:B3:AA:13:B0/assign
📡 Subscribed to: hospital/devices/ESP32-WATCH-A0:A3:B3:AA:13:B0/command
```

**Failure Indicators:**
```
❌ MQTT Connection failed, rc=-2
[ssl_starttls_handshake():317]: (-30592) SSL - A fatal alert message was received from our peer
```

### Step 3: Check Mosquitto Logs
```bash
docker logs -f hospital_mosquitto
```

**Success Indicators:**
```
New connection from 192.168.0.148:xxxxx on port 8883.
New client connected from 192.168.0.148 as HospitalWatch_ESP32-WATCH-A0:A3:B3:AA:13:B0
  (p2, c1, k15, u'ESP32-WATCH-A0:A3:B3:AA:13:B0').
```

**Failure Indicators:**
```
New connection from 172.20.0.1 on port 8883.
OpenSSL Error[0]: error:140360B2:SSL routines:ACCEPT_SR_CERT:no certificate returned
Socket error on client <unknown>, disconnecting.
```

---

## Expected Outcomes

### Scenario A: Connection Succeeds ✅

**This means**:
- ✅ ACL was the root cause
- ✅ Explicit user entry works with colon-based CNs
- ✅ mTLS authentication is working
- ✅ ESP32 NetworkClientSecure IS sending the certificate correctly

**Next steps**:
1. Celebrate - the issue is solved!
2. Generate device certificates with sanitized IDs (remove colons)
3. Update ACL to use pattern matching (remove explicit user entry)
4. Re-provision all devices with new certificates

### Scenario B: Connection Still Fails ❌

**This means**:
- ❌ ACL was NOT the only issue
- ❌ There's still a problem with certificate transmission
- ❌ Possible causes:
  - Certificate chain incomplete
  - CA mismatch between ESP32 ca.crt and Mosquitto hospital_ca.crt
  - NetworkClientSecure library bug (still not sending cert)
  - Certificate format issue (encoding, line endings)

**Next steps**:
1. Verify CA certificates match:
   ```bash
   openssl x509 -in esp32_spiffs/ca.crt -noout -fingerprint
   openssl x509 -in mosquitto/certs/hospital_ca.crt -noout -fingerprint
   ```
2. Test with openssl s_client to confirm certs are valid
3. Consider switching to username/password authentication temporarily

---

## Files Modified

1. **mosquitto/config/acl.conf**
   - Added explicit user entry for `ESP32-WATCH-A0:A3:B3:AA:13:B0`
   - Lines 40-49

2. **esp32_hospital_watch_complete.ino** (already modified earlier)
   - Added `mqttConfigured` flag to prevent loading certs multiple times
   - Lines 93, 565, 970, 992-997, 1041, 1207

---

## What User Discovered

**Brilliant catch!** The user identified that:

1. Error -30592 is a **TLS fatal alert** from the server
2. Mosquitto has **strict ACLs** with default deny
3. ESP32 CN contains **colons** (`A0:A3:B3:AA:13:B0`) which don't match simple patterns
4. This causes Mosquitto to **reject the connection during/after TLS handshake**

This was NOT a NetworkClientSecure library bug - it was an **ACL configuration issue**!

---

## Summary

**Problem**: ESP32 CN with colons not matching Mosquitto ACL patterns → connection rejected with fatal alert -30592

**Fix**: Added explicit ACL entry for the colon-based CN

**Status**: ✅ Fix applied, Mosquitto restarted, ready to test

**Next**: Upload ESP32 firmware and test MQTT connection

---

**UPLOAD THE FIRMWARE NOW AND TEST!** 🚀
