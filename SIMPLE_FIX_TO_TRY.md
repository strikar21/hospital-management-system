# Simple Fix To Try - Use loadCertificate() Instead

## The Problem
NetworkClientSecure has two ways to load certificates:

1. **setCertificate(const char*)** - Stores pointer (what we're using)
2. **loadCertificate(Stream, size)** - Loads from file stream (NOT tried yet)

## The Solution

NetworkClientSecure has `loadCertificate()` and `loadPrivateKey()` methods that load directly from SPIFFS File streams. This might internally copy the data instead of just storing pointers.

## Code Change

Replace this in `setupMQTT()`:

```cpp
// OLD - using setCertificate() with String.c_str()
wifiClient.setCACert(caCertificate.c_str());
wifiClient.setCertificate(deviceCertificate.c_str());
wifiClient.setPrivateKey(devicePrivateKey.c_str());
```

With this:

```cpp
// NEW - using loadCertificate() from File streams
SPIFFS.begin(true);

// Load CA cert
File caCertFile = SPIFFS.open("/ca.crt", "r");
if (caCertFile) {
  wifiClient.loadCACert(caCertFile, caCertFile.size());
  caCertFile.close();
  Serial.println("   ✅ CA cert loaded from file stream");
}

// Load device certificate
File deviceCertFile = SPIFFS.open("/device.crt", "r");
if (deviceCertFile) {
  wifiClient.loadCertificate(deviceCertFile, deviceCertFile.size());
  deviceCertFile.close();
  Serial.println("   ✅ Device cert loaded from file stream");
}

// Load device private key
File deviceKeyFile = SPIFFS.open("/device.key", "r");
if (deviceKeyFile) {
  wifiClient.loadPrivateKey(deviceKeyFile, deviceKeyFile.size());
  deviceKeyFile.close();
  Serial.println("   ✅ Private key loaded from file stream");
}
```

## Why This Might Work

The `loadCertificate()` method might internally allocate memory and copy the certificate data, avoiding the pointer invalidation issue.

From NetworkClientSecure.cpp:
```cpp
bool NetworkClientSecure::loadCertificate(Stream& stream, size_t size) {
  char *dest = _streamLoad(stream, size);
  bool ret = false;
  if (dest) {
    setCertificate(dest);  // Internally calls setCertificate
    ret = true;
  }
  return ret;
}
```

It uses `_streamLoad()` which might malloc() memory, keeping it valid.

## Test This First

This is a 5-minute change that might fix the issue without needing to switch libraries.

If this works → Problem was pointer management
If this fails → Deeper library issue, need ESP-MQTT

## Implementation Location

File: `esp32_hospital_watch_complete.ino`
Function: `setupMQTT()`
Lines: ~1014-1025 (where certificates are currently set)
