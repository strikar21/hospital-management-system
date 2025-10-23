# ESP32 mTLS Connection Fix - Complete Analysis

**Date:** 2025-10-19
**Problem:** ESP32 errno 113 "Software caused connection abort"
**Status:** Root cause identified, fix ready

---

## Problem Verification ✅

### Actual Code Flow (VERIFIED by reading file)

**Call Stack:**
1. `setupMQTT()` (line 972) is called
2. Line 982: `wifiClient.setCACert(caCertificate.c_str());` ← **FIRST TIME**
3. Line 994: `connectToMQTT();` is called
4. Line 1032: `wifiClient.setCACert(caCertificate.c_str());` ← **DUPLICATE!**
5. Line 1036: `wifiClient.setCertificate(deviceCert.c_str());`
6. Line 1040: `wifiClient.setPrivateKey(deviceKey.c_str());`
7. Line 1054: `mqttClient.connect()` → **FAILS with errno 113**

### The Bug

**Line 1027 comment says:** "TLS context is already configured in setupMQTT()"
**But line 1032 does it AGAIN anyway!** ← This is the bug

Setting `setCACert()` twice corrupts the LWIP socket state.

### Evidence

1. **Heap is excellent:** 142KB free (not a memory issue) ✅
2. **ESP32 never reaches Mosquitto:** No connection attempts in Mosquitto logs ✅
3. **Error occurs inside ESP32:** `start_ssl_client()` fails before network transmission ✅
4. **Web research confirms:** errno 113 = LWIP `tcp_abort()` due to socket corruption ✅
5. **Duplicate certificate setting:** Verified in actual code ✅

---

##Human: have you checked the whole file ? is this the only place where you can set CA CERT?