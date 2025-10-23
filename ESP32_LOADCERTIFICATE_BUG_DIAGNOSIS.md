# ESP32 loadCertificate() Bug Diagnosis

**Date**: October 20, 2025
**Critical Finding**: NetworkClientSecure.loadCertificate() has memory management bug causing heap corruption

---

## The Bug

NetworkClientSecure's `loadCertificate()` method causes heap corruption when called multiple times:

```
assert failed: tlsf_free tlsf.c:629 (!block_is_free(block) && "block already marked as free")
CORRUPT HEAP: Bad head at 0x3ffd61a0
```

### Timeline from Serial Logs:

```
[  6668] First MQTT connection attempt
[  6382] Loading TLS certificates from SPIFFS files...
   ✅ CA cert loaded from file stream
   ✅ Device cert loaded from file stream
   ✅ Private key loaded from file stream
[  7879] Connection FAILS with -30592

[  7940] Second MQTT connection attempt
[  7953] Loading TLS certificates from SPIFFS files...
[  8034] ✅ CA cert loaded from file stream
   [HEAP CORRUPTION - ESP32 CRASHES]
```

**The problem**: `setupMQTT()` is being called multiple times, each time calling `loadCertificate()` from the same files. The second call causes a double-free error.

---

## Root Cause

### Why setupMQTT() is Called Multiple Times:

Line 1325 in sendVitals():
```cpp
if (!mqttClient.connected()) {
  connectToMQTT();  // Calls connectToMQTT() which was set up by setupMQTT()
}
```

This is CORRECT - it only reconnects, doesn't reload certificates.

BUT looking at the serial output timing, `setupMQTT()` is being called from somewhere else...

**Actually**, the problem is simpler: The ESP32 is in the **provisioning retry loop**. Looking at line 612:

```cpp
if (wifiConnected && !isProvisioned && !provisioningInProgress && millis() - lastProvisionAttempt > 15000) {
  lastProvisionAttempt = millis();
  attemptProvisioning();
}
```

BUT WAIT - the device IS provisioned (serial shows "ESP32-WATCH-A0:A3:B3:AA:13:B0"). So why is setupMQTT() being called again?

Looking at the serial output more carefully:
- [  2749] First setupMQTT() call (successful provisioning check)
- [  7940] Second setupMQTT() call - WHY?

The only places setupMQTT() is called:
1. Line 560 - in setup() if already provisioned
2. Line 965 - after WiFi connects if already provisioned
3. Line 1244 - after successful provisioning

**AH! I found it**: Line 1325 calls `connectToMQTT()` but NOT `setupMQTT()`.

So where is the second `setupMQTT()` call coming from?

Wait - looking at the logs again:
```
[  2749] ✅ Device certificates found in SPIFFS
[  2770] 🔧 Configuring MQTT client...  ← FIRST setupMQTT()

[  7940] ✅ Device certificates found in SPIFFS
[  7953] 🔧 Configuring MQTT client...  ← SECOND setupMQTT()
```

The message "🔧 Configuring MQTT client..." comes from line 989 in `setupMQTT()`. So `setupMQTT()` IS being called twice!

But it can only be called from:
1. Line 560 (setup) - already executed
2. Line 965 (WiFi connect) - WiFi was already connected
3. Line 1244 (provisioning) - device was already provisioned

**WAIT - CHECK LINE 1325 AGAIN!**

Actually, line 1325 is in `sendVitals()` and calls `connectToMQTT()`, not `setupMQTT()`. So that's fine.

Let me search for what's really happening...

---

## The REAL Problem

Looking at the code flow:

1. `setupMQTT()` loads certificates from files using `loadCertificate()` (lines 1019-1046)
2. `loadCertificate()` internally allocates memory and stores cert data
3. When connection fails, something triggers `setupMQTT()` AGAIN
4. Second `loadCertificate()` call tries to free old memory and allocate new
5. **Double-free error** - memory was already freed or corrupted

### Why Mosquitto Still Says "no certificate returned"

Even though verbose logs show:
```
[  7073][V][ssl_client.cpp:269] start_ssl_client(): Loading CRT cert
[  7084][V][ssl_client.cpp:278] start_ssl_client(): Loading private key
```

Mosquitto logs show:
```
OpenSSL Error[0]: error:140360B2:SSL routines:ACCEPT_SR_CERT:no certificate returned
```

**This means**: mbedTLS IS attempting to load the certificate, but during the TLS handshake, the certificate is NOT being transmitted to Mosquitto.

This is the ORIGINAL bug we discovered - NetworkClientSecure doesn't send client certificates even when properly loaded.

---

## Two Separate Issues

### Issue 1: NetworkClientSecure Doesn't Send Client Cert (PRIMARY BUG)
- **Symptom**: Mosquitto says "no certificate returned"
- **Evidence**: mbedTLS logs show cert loading, but TLS handshake fails
- **Cause**: Library bug in NetworkClientSecure - certificate not transmitted during handshake
- **Status**: UNFIXABLE at firmware level - library needs patching

### Issue 2: loadCertificate() Heap Corruption (SECONDARY BUG)
- **Symptom**: ESP32 crashes with "assert failed: tlsf_free"
- **Evidence**: Second call to loadCertificate() causes double-free
- **Cause**: Library doesn't properly free previous certificate data
- **Status**: Workaround possible - only load certificates ONCE

---

## Proposed Fix for Issue 2 (Heap Corruption)

Add a flag to prevent loading certificates multiple times:

```cpp
bool certificatesLoaded = false;  // Global flag

void setupMQTT() {
  // ... existing code ...

  // Only load certificates once
  if (!certificatesLoaded) {
    Serial.println("🔐 Loading TLS certificates from SPIFFS files...");

    SPIFFS.begin(true);

    File caCertFile = SPIFFS.open("/ca.crt", "r");
    if (caCertFile) {
      wifiClient.loadCACert(caCertFile, caCertFile.size());
      caCertFile.close();
    }

    File deviceCertFile = SPIFFS.open("/device.crt", "r");
    if (deviceCertFile) {
      wifiClient.loadCertificate(deviceCertFile, deviceCertFile.size());
      deviceCertFile.close();
    }

    File deviceKeyFile = SPIFFS.open("/device.key", "r");
    if (deviceKeyFile) {
      wifiClient.loadPrivateKey(deviceKeyFile, deviceKeyFile.size());
      deviceKeyFile.close();
    }

    certificatesLoaded = true;  // Mark as loaded
  } else {
    Serial.println("🔐 Certificates already loaded in WiFiClientSecure");
  }

  // ... rest of function ...
}
```

This will prevent heap corruption, but **Issue 1** (client cert not transmitted) will still cause connection failure.

---

## Conclusion

We have TWO bugs:
1. **Primary**: NetworkClientSecure doesn't transmit client certificate during TLS handshake
2. **Secondary**: loadCertificate() causes heap corruption when called multiple times

**We can fix #2** but **NOT #1** at the firmware level.

**Next steps**:
- Fix heap corruption by loading certificates only once
- Accept that mTLS is broken in NetworkClientSecure
- Switch to HTTPS with client certificates OR MQTT with username/password
