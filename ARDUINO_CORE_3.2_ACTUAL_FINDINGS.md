# Arduino ESP32 Core 3.2.0 - Actual Investigation Results

## Verified Installation

**Location**: `C:\Users\Srika\AppData\Local\Arduino15\packages\esp32\hardware\esp32\3.2.0\`

**Confirmation**: Arduino ESP32 Core **3.2.0 IS installed** ✅

## Critical Discovery: setBufferSizes() and setDebugLevel() DO NOT EXIST

### Investigation Path

1. Searched for WiFiClientSecure class location
2. Found it at: `NetworkClientSecure/src/WiFiClientSecure.h`
3. Discovered WiFiClientSecure is a **typedef** for NetworkClientSecure
4. Read the actual class header: [NetworkClientSecure.h](C:\Users\Srika\AppData\Local\Arduino15\packages\esp32\hardware\esp32\3.2.0\libraries\NetworkClientSecure\src\NetworkClientSecure.h)

### Available Methods in NetworkClientSecure (Core 3.2.0)

```cpp
class NetworkClientSecure : public NetworkClient {
public:
  // Certificate management
  void setCACert(const char *rootCA);                              // ✅ EXISTS
  void setCertificate(const char *client_ca);                      // ✅ EXISTS
  void setPrivateKey(const char *private_key);                     // ✅ EXISTS

  // Security configuration
  void setInsecure();                                              // ✅ EXISTS
  void setPreSharedKey(const char *pskIdent, const char *psKey);   // ✅ EXISTS
  void setHandshakeTimeout(unsigned long handshake_timeout);       // ✅ EXISTS
  void setAlpnProtocols(const char **alpn_protos);                 // ✅ EXISTS

  // Certificate loading from streams
  bool loadCACert(Stream &stream, size_t size);                    // ✅ EXISTS
  bool loadCertificate(Stream &stream, size_t size);               // ✅ EXISTS
  bool loadPrivateKey(Stream &stream, size_t size);                // ✅ EXISTS

  // Certificate validation
  bool verify(const char *fingerprint, const char *domain_name);   // ✅ EXISTS
  const mbedtls_x509_crt *getPeerCertificate();                    // ✅ EXISTS

  // Connection methods with certificates
  int connect(IPAddress ip, uint16_t port, const char *rootCABuff,
              const char *cli_cert, const char *cli_key);          // ✅ EXISTS
};
```

### Methods That DO NOT EXIST

```cpp
wifiClient.setBufferSizes(4096, 4096);  // ❌ DOES NOT EXIST in Core 3.2.0
wifiClient.setDebugLevel(1);            // ❌ DOES NOT EXIST in Core 3.2.0
```

**Why the confusion?** The "Arduino Core 3.2 compatible code" provided earlier was **incorrect** or from a different library/fork.

## Current ESP32 Firmware Status

### Lines that cause compile errors ([esp32_hospital_watch_complete.ino:1006-1007, 1021-1022](../esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1006))

```cpp
//  wifiClient.setBufferSizes(4096, 4096);  // COMMENTED - causes compile errors
//  wifiClient.setDebugLevel(1);            // COMMENTED - causes compile errors
```

**Reason**: These methods don't exist in Arduino ESP32 Core 3.2.0's NetworkClientSecure class.

## Root Problem: WiFiClientSecure Not Sending Client Certificate

### The Issue
ESP32 shows:
```
✅ Device cert set (client authentication)
```

But Mosquitto receives:
```
❌ OpenSSL Error: no certificate returned
```

### Why Is This Happening?

After reviewing the NetworkClientSecure header, I see that the class has **multiple connect() methods** with different signatures:

```cpp
// Method 1: Basic connect (what we're using now)
int connect(const char *host, uint16_t port);  // <-- CURRENT

// Method 2: Connect with certificates as parameters
int connect(const char *host, uint16_t port,
            const char *rootCABuff, const char *cli_cert, const char *cli_key);
```

**Hypothesis**: When using Method 1 (basic connect), the pre-set certificates via `setCACert()`, `setCertificate()`, `setPrivateKey()` might not be properly attached to the TLS handshake.

**Possible Fix**: Use Method 2 and pass certificates directly to `connect()`.

## Proposed Fix Strategy

### Option A: Pass Certificates Directly to connect() (Recommended)

Instead of:
```cpp
wifiClient.setCACert(caCertificate.c_str());
wifiClient.setCertificate(deviceCertificate.c_str());
wifiClient.setPrivateKey(devicePrivateKey.c_str());

mqttClient.connect(clientId.c_str());  // PubSubClient calls wifiClient.connect(host, port)
```

Use NetworkClientSecure's special connect method:
```cpp
// Connect with certificates passed as parameters
wifiClient.connect(mqttServer.c_str(), mqttPort.toInt(),
                   caCertificate.c_str(),
                   deviceCertificate.c_str(),
                   devicePrivateKey.c_str());
```

**Problem**: PubSubClient library doesn't expose this method - it only uses the basic `connect(host, port)`.

### Option B: Switch to ESP-MQTT Library

The ESP-MQTT library (native ESP-IDF component) has better certificate handling:
```cpp
#include "mqtt_client.h"

esp_mqtt_client_config_t mqtt_cfg = {
    .uri = "mqtts://192.168.0.113:8883",
    .cert_pem = caCertificate.c_str(),
    .client_cert_pem = deviceCertificate.c_str(),
    .client_key_pem = devicePrivateKey.c_str(),
};
```

### Option C: Debug with setHandshakeTimeout()

Try increasing the handshake timeout to see if it's a timing issue:
```cpp
wifiClient.setHandshakeTimeout(15000);  // 15 seconds (default is usually 3-5 seconds)
```

### Option D: Test with setInsecure() First

Temporarily disable server verification to isolate the problem:
```cpp
wifiClient.setInsecure();  // Skip server certificate verification
wifiClient.setCertificate(deviceCertificate.c_str());  // Client cert still sent
wifiClient.setPrivateKey(devicePrivateKey.c_str());
```

If this works, it confirms the client certificate IS being sent, but there's a CA validation issue.

## Recommended Next Steps

1. **Immediate Test**: Try Option D (setInsecure + client cert) to verify certificate is actually being sent
2. **If Option D works**: Problem is CA cert validation, not client cert sending
3. **If Option D fails**: Switch to Option B (ESP-MQTT library) for better certificate control

## Code Changes to Test

### Test 1: setInsecure() + Client Certificate

Modify [esp32_hospital_watch_complete.ino:1009-1018](../esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1009):

```cpp
// TEST: Disable server verification to isolate client cert issue
wifiClient.setInsecure();  // ⚠️ TEMPORARY - bypasses server cert check
Serial.println("   ⚠️  Server verification DISABLED (testing mode)");

// ✅ Client certificate and private key (mTLS)
wifiClient.setCertificate(deviceCertificate.c_str());
Serial.println("   ✅ Device cert set (client authentication)");

wifiClient.setPrivateKey(devicePrivateKey.c_str());
Serial.println("   ✅ Private key set (mTLS complete)");
```

**Expected outcome**:
- If Mosquitto connection succeeds → Client certificate IS being sent properly
- If still fails with "no certificate returned" → NetworkClientSecure bug or API misuse

### Test 2: Increase Handshake Timeout

Add after line 1018:

```cpp
wifiClient.setHandshakeTimeout(15000);  // 15 seconds
Serial.println("   ⏱️  Handshake timeout: 15 seconds");
```

## Conclusion

- ✅ Arduino ESP32 Core 3.2.0 is installed
- ❌ `setBufferSizes()` and `setDebugLevel()` do NOT exist in Core 3.2.0
- ❓ Client certificate not being sent - root cause still unknown
- 🧪 Need to test with setInsecure() to isolate the problem

**The "Arduino Core 3.2 compatible code" you were given was WRONG.**
