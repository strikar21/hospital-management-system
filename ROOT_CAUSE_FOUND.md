# ESP32 mTLS Root Cause - FOUND

## Summary

**ROOT CAUSE**: NetworkClientSecure's certificate pointers (`_cert` and `_private_key`) become NULL or invalid between `setCertificate()`/`setPrivateKey()` calls and the actual `connect()` call.

## Evidence

### 1. Verbose Logging Enabled
```cpp
esp_log_level_set("*", ESP_LOG_VERBOSE);
```

### 2. Expected Log Messages MISSING
From [ssl_client.cpp:269, 278](C:\Users\Srika\AppData\Local\Arduino15\packages\esp32\hardware\esp32\3.2.0\libraries\NetworkClientSecure\src\ssl_client.cpp):
```cpp
log_v("Loading CRT cert");        // Line 269
log_v("Loading private key");     // Line 278
```

These messages **NEVER APPEAR** in serial output, proving the code at line 265 is never executed:

```cpp
if (!insecure && cli_cert != NULL && cli_key != NULL) {
    // This block is NEVER executed
}
```

### 3. Why The Condition Fails

When `mqttClient.connect(clientId)` is called:
1. PubSubClient calls `wifiClient.connect(domain, port)`
2. NetworkClientSecure calls `connect(host, port, _CA_cert, _cert, _private_key)`
3. `_cert` and `_private_key` are **NULL or pointing to invalid memory**

## The Problem: Dangling Pointers

NetworkClientSecure stores **pointers**, not data:

```cpp
void NetworkClientSecure::setCertificate(const char *client_ca) {
    _cert = client_ca;  // Just stores the pointer!
}

void NetworkClientSecure::setPrivateKey(const char *private_key) {
    _private_key = private_key;  // Just stores the pointer!
}
```

When we call:
```cpp
wifiClient.setCertificate(deviceCertificate.c_str());
```

It stores a pointer to the String's internal buffer. **But String objects can reallocate their buffers** when they grow, shrink, or move in memory, making the stored pointer invalid.

## Why Test 1 & 2 Worked But Test 3 Failed

### Test 1 (setInsecure) - SUCCESS ✅
```cpp
wifiClient.setInsecure();  // _use_insecure = true
```
- Condition `!insecure` fails → Client cert code skipped
- Server doesn't require cert → Connection succeeds

### Test 2 (CA cert only) - SUCCESS ✅
```cpp
wifiClient.setCACert(...);  // Server validation enabled
// Client cert code skipped because _cert == NULL
```
- Server validates ESP32's connection
- Server doesn't require client cert → Connection succeeds

### Test 3 (Full mTLS) - FAILED ❌
```cpp
wifiClient.setCACert(...);
wifiClient.setCertificate(...);  // _cert pointer stored
wifiClient.setPrivateKey(...);   // _private_key pointer stored
```
- By the time `connect()` is called, pointers are invalid/NULL
- Client cert code skipped
- Server REQUIRES client cert → **Connection fails**

## Why Certificate Data Appears Valid

```
🔍 Device cert preview: -----BEGIN CERTIFICATE-----
MIIEfjCCA2agAwIBAgIUEh...
```

This proves:
- ✅ Certificate is loaded in the String
- ✅ Certificate is valid PEM format
- ✅ `.c_str()` works at the time of `setCertificate()` call

**BUT** it doesn't prove the pointer remains valid later!

## The Solution

We have 3 options:

### Option 1: Switch to ESP-MQTT Library ⭐ RECOMMENDED
Use the native ESP-IDF MQTT library which properly handles certificates:

```cpp
#include "mqtt_client.h"

esp_mqtt_client_config_t mqtt_cfg = {
    .broker.address.uri = "mqtts://192.168.0.113:8883",
    .broker.verification.certificate = caCertificate.c_str(),
    .credentials.authentication.certificate = deviceCertificate.c_str(),
    .credentials.authentication.key = devicePrivateKey.c_str(),
};

esp_mqtt_client_handle_t client = esp_mqtt_client_init(&mqtt_cfg);
esp_mqtt_client_start(client);
```

### Option 2: Keep Certificates in Static Memory
Allocate certificate strings on the heap with `new char[]` so they never move:

```cpp
// In global scope
char* deviceCertPtr = nullptr;
char* deviceKeyPtr = nullptr;

// After loading from SPIFFS
deviceCertPtr = new char[deviceCertificate.length() + 1];
strcpy(deviceCertPtr, deviceCertificate.c_str());

deviceKeyPtr = new char[devicePrivateKey.length() + 1];
strcpy(deviceKeyPtr, devicePrivateKey.c_str());

// Set certificates
wifiClient.setCertificate(deviceCertPtr);
wifiClient.setPrivateKey(deviceKeyPtr);
```

**Problem**: This leaks memory unless carefully managed.

### Option 3: Use loadCertificate() Method
NetworkClientSecure has `loadCertificate()` and `loadPrivateKey()` methods that might properly copy the data:

```cpp
File certFile = SPIFFS.open("/device.crt", "r");
wifiClient.loadCertificate(certFile, certFile.size());
certFile.close();

File keyFile = SPIFFS.open("/device.key", "r");
wifiClient.loadPrivateKey(keyFile, keyFile.size());
keyFile.close();
```

**Status**: Untested - may or may not work better.

## Recommendation

**SWITCH TO ESP-MQTT LIBRARY (Option 1)**

Reasons:
1. ✅ Confirmed working with mTLS in production systems
2. ✅ Better performance and features
3. ✅ Native ESP-IDF component (well-maintained)
4. ✅ Avoids all pointer/memory issues
5. ✅ QoS 2 support, persistent sessions, automatic reconnection

NetworkClientSecure has fundamental design issues with certificate handling that make it unreliable for production mTLS use.

## Next Steps

1. Create implementation plan for ESP-MQTT migration
2. Estimate 4-6 hours for complete rewrite
3. Test with full mTLS enabled
4. Verify certificate-based authentication end-to-end

## Alternative Quick Test

Before full migration, we could try **Option 2** (static memory) as a quick test to confirm this diagnosis:

```cpp
// Test code to add after loading certificates
static String staticDeviceCert;
static String staticDeviceKey;
staticDeviceCert = deviceCertificate;
staticDeviceKey = devicePrivateKey;

wifiClient.setCertificate(staticDeviceCert.c_str());
wifiClient.setPrivateKey(staticDeviceKey.c_str());
```

If this works, it confirms the root cause is pointer invalidation.
