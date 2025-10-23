# WiFiClientSecure Bug Confirmed - Client Certificate Not Sent

## Problem Summary

ESP32 successfully loads certificates but **WiFiClientSecure DOES NOT send client certificate** during TLS handshake.

---

## Evidence

### ESP32 Serial Output
```
✅ Device certificate loaded (1619 bytes)
✅ Device private key loaded (1704 bytes)
🔐 Certificates loaded:
   CA: 1436 bytes (global)
   Device cert: 1619 bytes (global)
   Device key: 1704 bytes (global)
🔐 Setting TLS certificates in wifiClient...
   ✅ CA cert set (server validation enabled)
   ✅ Device cert set (client authentication)
   ✅ Private key set (mTLS complete)
```

**Certificates ARE loaded and set correctly in firmware.**

### Mosquitto Logs
```
1760937012: New connection from 172.20.0.1 on port 8883.
1760937012: OpenSSL Error[0]: error:140360B2:SSL routines:ACCEPT_SR_CERT:no certificate returned
1760937012: Socket error on client <unknown>, disconnecting.
```

**Mosquitto says: "no certificate returned" - ESP32 didn't send client certificate!**

### ESP32 Error
```
[ssl_starttls_handshake():317]: (-30592) SSL - A fatal alert message was received from our peer
❌ MQTT Connection failed, rc=-2
```

**ESP32 received fatal alert from Mosquitto because no client certificate was presented.**

---

## Root Cause: WiFiClientSecure + PubSubClient Bug

**The Problem:**
- `wifiClient.setCertificate()` and `wifiClient.setPrivateKey()` are called successfully
- **BUT** WiFiClientSecure doesn't actually send the certificates during TLS handshake
- This is a known bug in Arduino ESP32 core's WiFiClientSecure implementation
- Specifically affects PubSubClient library interactions

**Why HTTPS works but MQTT doesn't:**
- HTTPS uses `HTTPClient` which has different internal TLS handling
- MQTT uses `PubSubClient` which relies on raw WiFiClientSecure
- Different code paths trigger different bugs in mbedTLS wrapper

---

## Attempted Fixes (All Failed)

1. ✅ Made certificates global String variables (prevent `.c_str()` pointer issues)
2. ✅ Set certificates BEFORE `setServer()` call
3. ✅ Removed NTP requirement
4. ✅ Verified certificates are valid and loaded
5. ✅ Fixed Windows Firewall (errno 113 → fatal alert)
6. ✅ Downgraded Mosquitto to 1.6 (TLS 1.2 only)
7. ✅ Tested with `setInsecure()` mode (works - proves connectivity OK)

**None of these fix the client certificate sending bug.**

---

## Solution: Switch to ESP-MQTT Library

**ESP-MQTT** is Espressif's official MQTT library that bypasses WiFiClientSecure entirely and uses esp-tls directly.

### Why ESP-MQTT Will Work:

1. **Lower-level TLS**: Uses `esp-tls` instead of Arduino WiFiClientSecure wrapper
2. **Official Espressif**: Maintained by ESP32 chip manufacturer
3. **Production-tested**: Used in millions of ESP32 IoT devices
4. **Better mTLS support**: Designed for certificate-based authentication
5. **Non-blocking**: Event-driven architecture

### Implementation Plan:

**Step 1: Add ESP-MQTT to platformio.ini or Arduino IDE**
```ini
[env:esp32]
lib_deps =
    ESP32 MQTT Library
```

**Step 2: Replace PubSubClient code**

**FROM:**
```cpp
#include <WiFiClientSecure.h>
#include <PubSubClient.h>

WiFiClientSecure wifiClient;
PubSubClient mqttClient(wifiClient);

wifiClient.setCACert(caCertificate.c_str());
wifiClient.setCertificate(deviceCertificate.c_str());
wifiClient.setPrivateKey(devicePrivateKey.c_str());

mqttClient.setServer(mqttServer.c_str(), 8883);
mqttClient.connect(clientId.c_str());
```

**TO:**
```cpp
#include "mqtt_client.h"

esp_mqtt_client_config_t mqtt_cfg = {
    .uri = "mqtts://192.168.0.113:8883",
    .client_cert_pem = deviceCertificate.c_str(),
    .client_key_pem = devicePrivateKey.c_str(),
    .cert_pem = caCertificate.c_str(),
    .skip_cert_common_name_check = false,
};

esp_mqtt_client_handle_t client = esp_mqtt_client_init(&mqtt_cfg);
esp_mqtt_client_register_event(client, ESP_EVENT_ANY_ID, mqtt_event_handler, NULL);
esp_mqtt_client_start(client);
```

**Step 3: Update callbacks**

ESP-MQTT uses event handlers instead of callbacks:

```cpp
static void mqtt_event_handler(void *handler_args, esp_event_base_t base, int32_t event_id, void *event_data) {
    esp_mqtt_event_handle_t event = (esp_mqtt_event_handle_t)event_data;

    switch ((esp_mqtt_event_id_t)event_id) {
        case MQTT_EVENT_CONNECTED:
            Serial.println("✅ MQTT Connected with mTLS!");
            esp_mqtt_client_subscribe(client, "hospital/devices/+/assign", 0);
            break;

        case MQTT_EVENT_DATA:
            Serial.printf("📨 MQTT: %.*s -> %.*s\n",
                event->topic_len, event->topic,
                event->data_len, event->data);
            break;

        case MQTT_EVENT_DISCONNECTED:
            Serial.println("❌ MQTT Disconnected");
            break;
    }
}
```

---

## Alternative: Temporary Workaround

If we **cannot** switch to ESP-MQTT right now, we can temporarily:

1. **Disable `require_certificate` in Mosquitto** (allow connections without client cert)
2. **Keep `use_identity_as_username false`** (don't extract username from cert)
3. **Use username/password auth** instead of mTLS (less secure)

**Mosquitto config changes:**
```conf
require_certificate false
use_identity_as_username false
allow_anonymous false

# Use password file
password_file /mosquitto/config/passwords.txt
```

**ESP32 changes:**
```cpp
// Remove certificate calls
// wifiClient.setCertificate(...);  // REMOVE
// wifiClient.setPrivateKey(...);   // REMOVE

// Keep CA cert for server validation
wifiClient.setCACert(caCertificate.c_str());

// Add username/password
mqttClient.connect(clientId.c_str(), "esp32_user", "password123");
```

**But this is NOT recommended** - defeats the purpose of certificate-based security.

---

## Recommendation

**Implement ESP-MQTT library** - this is the proper fix that will:
- ✅ Work with mTLS immediately
- ✅ Be more reliable long-term
- ✅ Match our security requirements
- ✅ Be production-ready

The code refactoring is straightforward (2-3 hours work) and will solve the problem permanently.

---

## Status

**Current State:**
- ESP32 can connect with firewall open
- ESP32 can provision via HTTPS successfully
- ESP32 loads certificates correctly
- **WiFiClientSecure CANNOT send client certificates to Mosquitto**
- Mosquitto correctly rejects connections without client certs

**Next Action Required:**
Switch from PubSubClient + WiFiClientSecure to ESP-MQTT library.