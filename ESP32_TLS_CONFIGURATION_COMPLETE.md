# ESP32 MQTT TLS Configuration - COMPLETE GUIDE

## ✅ MQTT TLS SETUP - **COMPLETED**

### Backend & Mosquitto Status:
- **✅ TLS Certificate Fixed** - Added SANs for localhost, 127.0.0.1, 192.168.0.113
- **✅ Mosquitto Running** - Port 8883 with TLS 1.2
- **✅ Backend Connected** - MQTT service successfully connected to broker

### Certificate Details:
- **Location:** `C:/Users/Srika/OneDrive/Desktop/hospital-management-system/mosquitto/certs/`
- **CA Certificate:** `ca.crt` (valid for 10 years)
- **Server Certificate:** `server.crt` (with SANs: localhost, hospital-mosquitto, 127.0.0.1, 192.168.0.113)
- **Server Key:** `server.key`

---

## 🔧 ESP32 FIRMWARE - REQUIRED CHANGES

### Current ESP32 Configuration (v4.0.0):
```cpp
String mqttPort = "1883";  // ❌ WRONG - needs to be 8883
WiFiClient wifiClient;      // ❌ WRONG - needs WiFiClientSecure
PubSubClient mqttClient(wifiClient);  // Using non-secure client
```

### Required Changes for TLS Support:

#### 1. Change Include (Line 32):
```cpp
// BEFORE:
#include <time.h>

// AFTER:
#include <time.h>
#include <WiFiClientSecure.h>
```

#### 2. Add CA Certificate (After line 47):
```cpp
// ====================================
// TLS CERTIFICATE
// ====================================
const char* CA_CERT = \
"-----BEGIN CERTIFICATE-----\n" \
"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\n" \
"LSQs\n" \
"-----END CERTIFICATE-----\n";
```

#### 3. Change WiFi Client (Lines 53-55):
```cpp
// BEFORE:
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

// AFTER:
WiFiClientSecure wifiClient;
PubSubClient mqttClient(wifiClient);
```

#### 4. Change Default Port (Line 73):
```cpp
// BEFORE:
String mqttPort = "1883";

// AFTER:
String mqttPort = "8883";
```

#### 5. Update Form Default (Line 652):
```cpp
// BEFORE:
html += "<input type='text' name='mqtt_port' value='1883' required>";

// AFTER:
html += "<input type='text' name='mqtt_port' value='8883' required>";
```

#### 6. Update setupMQTT() Function (After line 853):
```cpp
void setupMQTT() {
  if (mqttServer.length() == 0) {
    mqttServer = serverIP;
  }

  Serial.println("🔧 Setting up MQTT connection...");
  Serial.println("📡 MQTT Server: " + mqttServer + ":" + mqttPort);

  // ✅ NEW: Configure TLS
  wifiClient.setCACert(CA_CERT);
  wifiClient.setInsecure();  // For development - accepts any certificate

  mqttClient.setServer(mqttServer.c_str(), mqttPort.toInt());
  mqttClient.setCallback(onMqttMessage);

  connectToMQTT();
}
```

#### 7. Update loadConfiguration() Default (Line 1092):
```cpp
// BEFORE:
mqttPort = prefs.getString("mqttport", "1883");

// AFTER:
mqttPort = prefs.getString("mqttport", "8883");
```

---

## 📋 PROVISIONING CONFIGURATION

### When Filling the ESP32 Provisioning Form:

1. **WiFi Network:** [Select from dropdown]
2. **WiFi Password:** [Your WiFi password]
3. **Server IP:** `192.168.0.113`
4. **HTTP Port:** `8001`
5. **MQTT Port:** `8883` ✅ (TLS encrypted)
6. **Provisioner ID:** `TEC0001` ✅
7. **Provisioner Password:** `tech123` ✅

### Authentication Details:
- **Provisioner:** David Kumar (Technician)
- **Database:** PostgreSQL on localhost:5432
- **MQTT Broker:** Mosquitto on localhost:8883 (TLS)
- **Backend:** FastAPI on localhost:8001

---

## 🔒 SECURITY CONFIGURATION

### Mosquitto MQTT Broker:
- **Port:** 8883
- **Protocol:** MQTT over TLS 1.2
- **Authentication:** Username/Password (`hospitalEsp32` / stored hash)
- **Certificate:** X.509 with Subject Alternative Names
- **ACLs:** Topic-level permissions configured

### Backend MQTT Service:
- **Connection:** Established ✅
- **TLS Verification:** Enabled
- **CA Certificate:** Loaded from filesystem
- **Topics Subscribed:**
  - `hospital/devices/+/vitals`
  - `hospital/devices/+/alerts`
  - `hospital/devices/+/heartbeat`

---

## ✅ TODO: ESP32 Firmware Updates

The current ESP32 firmware (`esp32_hospital_watch_complete.ino`) needs the changes listed above to support TLS on port 8883.

**Option 1:** Manually edit the `.ino` file with the changes above
**Option 2:** Use Arduino IDE to add `WiFiClientSecure` and configure TLS

Once updated:
1. Flash the firmware to ESP32
2. Connect to "HospitalWatch" WiFi hotspot
3. Fill provisioning form with TEC0001/tech123
4. ESP32 will connect to MQTT on port 8883 with TLS

---

## 📊 SUMMARY

✅ **Certificate Issue Fixed** - SANs added for 127.0.0.1
✅ **Mosquitto Running** - Port 8883 with TLS
✅ **Backend Connected** - MQTT service operational
⏳ **ESP32 Firmware** - Needs TLS support added (changes documented above)
⏳ **Testing** - Pending ESP32 firmware update and flash

**Next Step:** Apply the documented changes to ESP32 firmware and flash to device.
