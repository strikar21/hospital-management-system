# ESP32 Firmware Certificate Conversion Plan
## Days 5-6 Combined Implementation

**Status:** Ready to implement (awaiting user confirmation)
**Backup:** esp32_hospital_watch_complete.ino.backup-before-cert-auth created ✅

---

## Current State (v4.2.0 - MQTT Provisioning)

The firmware currently uses:
- **Provisioning Method:** MQTT-based with shared credentials
- **Authentication:** Username/password (`hospitalEsp32` / `ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF/Q=`)
- **Provisioning Flow:**
  1. ESP32 connects to MQTT with shared credentials
  2. Publishes provisioning request to `hospital/provisioning/request`
  3. Receives unique credentials via `hospital/provisioning/response/{mac}`
  4. Saves credentials and reconnects with unique credentials

**Security Issue:** All unprovisioned devices share the same hardcoded credentials (lines 79-80, 1233-1234)

---

## Target State (v5.0.0 - Certificate Provisioning)

The firmware will use:
- **Provisioning Method:** HTTPS-based with one-time codes
- **Authentication:** X.509 client certificates (mTLS)
- **Provisioning Flow:**
  1. Technician generates one-time code via backend API (`POST /api/v1/provisioning/generate-code`)
  2. Technician enters code on ESP32 captive portal
  3. ESP32 makes HTTPS request to `POST /api/v1/provisioning/provision-with-certificate`
  4. Backend validates code and issues X.509 certificate
  5. ESP32 saves certificate and private key to SPIFFS
  6. ESP32 connects to MQTT using client certificate (no password)

---

## Required Changes

### Day 5 Changes (Remove Hardcoded Credentials)

#### 1. Add HTTPClient Library (Line 31)
```cpp
#include <WiFi.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <PubSubClient.h>
#include <time.h>
#include <WiFiClientSecure.h>
#include <SPIFFS.h>
#include <HTTPClient.h>  // ✅ ADDED for HTTPS provisioning
```

#### 2. Remove Hardcoded MQTT Credentials (Lines 79-80)
**BEFORE:**
```cpp
String mqttUsername = "hospitalEsp32";
String mqttPassword = "ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF/Q=";
```

**AFTER:**
```cpp
// ✅ DAY 5: Removed hardcoded shared credentials - now using certificates
// Certificates will be loaded from SPIFFS after provisioning
```

#### 3. Add Certificate Storage Functions (After Line 169)
```cpp
// ====================================
// CERTIFICATE MANAGEMENT (v5.0.0)
// ====================================

/**
 * Check if device has provisioned certificates
 * @return true if both device certificate and private key exist in SPIFFS
 */
bool hasCertificates() {
  if (!SPIFFS.begin(true)) {
    Serial.println("❌ SPIFFS mount failed");
    return false;
  }

  bool certExists = SPIFFS.exists("/device.crt");
  bool keyExists = SPIFFS.exists("/device.key");

  if (certExists && keyExists) {
    Serial.println("✅ Device certificates found in SPIFFS");
    return true;
  }

  Serial.println("⚠️  Device certificates NOT found - provisioning required");
  return false;
}

/**
 * Load device certificate and private key from SPIFFS
 * @param cert Reference to string to store certificate PEM
 * @param key Reference to string to store private key PEM
 * @return true if both files loaded successfully
 */
bool loadDeviceCertificate(String& cert, String& key) {
  if (!SPIFFS.begin(true)) {
    Serial.println("❌ SPIFFS mount failed");
    return false;
  }

  // Load device certificate
  File certFile = SPIFFS.open("/device.crt", "r");
  if (!certFile) {
    Serial.println("❌ Device certificate file not found");
    return false;
  }
  cert = certFile.readString();
  certFile.close();

  // Load device private key
  File keyFile = SPIFFS.open("/device.key", "r");
  if (!keyFile) {
    Serial.println("❌ Device private key file not found");
    return false;
  }
  key = keyFile.readString();
  keyFile.close();

  if (cert.length() == 0 || key.length() == 0) {
    Serial.println("❌ Device certificate or key is empty");
    return false;
  }

  Serial.println("✅ Device certificate loaded (" + String(cert.length()) + " bytes)");
  Serial.println("✅ Device private key loaded (" + String(key.length()) + " bytes)");
  return true;
}

/**
 * Save device certificate and private key to SPIFFS
 * @param cert Certificate PEM string
 * @param key Private key PEM string
 * @return true if both files saved successfully
 */
bool saveCertificates(String cert, String key) {
  if (!SPIFFS.begin(true)) {
    Serial.println("❌ SPIFFS mount failed");
    return false;
  }

  // Save device certificate
  File certFile = SPIFFS.open("/device.crt", "w");
  if (!certFile) {
    Serial.println("❌ Failed to open device certificate file for writing");
    return false;
  }
  certFile.print(cert);
  certFile.close();

  // Save device private key
  File keyFile = SPIFFS.open("/device.key", "w");
  if (!keyFile) {
    Serial.println("❌ Failed to open device private key file for writing");
    return false;
  }
  keyFile.print(key);
  keyFile.close();

  Serial.println("✅ Device certificates saved to SPIFFS");
  return true;
}
```

---

### Day 6 Changes (Add Certificate Support)

#### 1. Replace attemptProvisioning() Function (Line 1071)
**Complete replacement - 60 lines**

Changes from MQTT provisioning to HTTPS provisioning:
- Accept one-time provisioning code from captive portal
- Make HTTPS POST to `/api/v1/provisioning/provision-with-certificate`
- Receive certificate, private key, and CA certificate
- Save all three to SPIFFS
- Mark device as provisioned

```cpp
void attemptProvisioning() {
  String provCode = prefs.getString("prov_code", "");

  if (provCode.length() == 0 || serverIP.length() == 0) {
    Serial.println("❌ Missing provisioning code or server IP");
    return;
  }

  if (provisioningInProgress) {
    Serial.println("⏳ Provisioning already in progress...");
    return;
  }

  Serial.println("🔄 Attempting HTTPS certificate provisioning...");
  provisioningInProgress = true;

  HTTPClient http;
  WiFiClientSecure httpsClient;
  httpsClient.setInsecure();  // Accept self-signed cert for provisioning

  String url = "https://" + serverIP + ":" + serverPort + "/api/v1/provisioning/provision-with-certificate";

  http.begin(httpsClient, url);
  http.addHeader("Content-Type", "application/json");

  JsonDocument doc;
  doc["code"] = provCode;
  doc["deviceId"] = deviceId.length() > 0 ? deviceId : ("ESP32-WATCH-" + macAddress);
  doc["macAddress"] = macAddress;
  doc["serialNumber"] = "SN-" + macAddress;

  String requestBody;
  serializeJson(doc, requestBody);

  int httpCode = http.POST(requestBody);

  if (httpCode == 200) {
    String response = http.getString();
    JsonDocument responseDoc;

    if (deserializeJson(responseDoc, response) == DeserializationError::Ok) {
      deviceId = responseDoc["deviceId"].as<String>();
      String certPem = responseDoc["certificatePem"].as<String>();
      String keyPem = responseDoc["privateKeyPem"].as<String>();
      String caCertPem = responseDoc["caCertificatePem"].as<String>();

      if (saveCertificates(certPem, keyPem)) {
        // Save CA certificate too
        File caFile = SPIFFS.open("/ca.crt", "w");
        caFile.print(caCertPem);
        caFile.close();

        isProvisioned = true;
        provisioningInProgress = false;
        prefs.remove("prov_code");  // Clear used code
        saveConfiguration();

        Serial.println("🎉 DEVICE PROVISIONED via HTTPS!");
        Serial.println("   📱 Device ID: " + deviceId);
        Serial.println("   🔐 Certificate saved to SPIFFS");

        // Reconnect to MQTT with certificate
        setupMQTT();
      }
    }
  } else {
    Serial.println("❌ Provisioning failed, HTTP code: " + String(httpCode));
    provisioningInProgress = false;
  }

  http.end();
}
```

#### 2. Replace connectToMQTT() Function (Line 953)
**Complete replacement - 30 lines**

Changes from password auth to certificate auth:
- Load device certificate and private key from SPIFFS
- Configure WiFiClientSecure with client certificate
- Connect to MQTT without username/password

```cpp
void connectToMQTT() {
  if (!wifiConnected || !isProvisioned) return;

  // Load device certificate and private key
  String deviceCert, deviceKey;
  if (!loadDeviceCertificate(deviceCert, deviceKey)) {
    Serial.println("❌ Cannot connect to MQTT - certificates not found");
    return;
  }

  // Configure TLS with client certificate
  wifiClient.setCACert(caCertificate.c_str());  // Hospital CA
  wifiClient.setCertificate(deviceCert.c_str());  // Device cert
  wifiClient.setPrivateKey(deviceKey.c_str());    // Device key

  String clientId = "HospitalWatch_" + deviceId;
  Serial.println("🔄 Connecting to MQTT with client certificate...");
  Serial.println("🔐 Device ID from certificate CN: " + deviceId);

  // Connect WITHOUT username/password (certificate auth only)
  if (mqttClient.connect(clientId.c_str())) {
    Serial.println("✅ MQTT Connected with client certificate!");

    String assignTopic = "hospital/devices/" + deviceId + "/assign";
    mqttClient.subscribe(assignTopic.c_str());

    String commandTopic = "hospital/devices/" + deviceId + "/command";
    mqttClient.subscribe(commandTopic.c_str());
  } else {
    Serial.println("❌ MQTT Connection failed, rc=" + String(mqttClient.state()));
  }
}
```

#### 3. Update Captive Portal to Accept Provisioning Code (Lines 722-728)
**Replace provisioner credentials fields with provisioning code field**

```html
<div class='form-section'>
<h3>🔐 Provisioning Code</h3>
<label>One-Time Provisioning Code:</label>
<input type='text' name='prov_code' placeholder='Enter code from IT staff' required pattern='[A-Z0-9]{16}' title='16-character code'>
<p style='font-size:12px;color:#666;'>Get this code from hospital IT staff</p>
</div>
```

#### 4. Update handleConfigure() to Save Provisioning Code (Line 781-782)
```cpp
String provCode = server.arg("prov_code");
prefs.putString("prov_code", provCode);
```

#### 5. Update setup() to Check for Certificates (Line 479)
```cpp
if (wifiConnected) {
  syncNTPTime();
  if (isProvisioned && hasCertificates()) {  // ✅ ADDED certificate check
    setupMQTT();
  } else if (isProvisioned && !hasCertificates()) {
    Serial.println("⚠️  Device marked as provisioned but certificates missing!");
    Serial.println("⚠️  Resetting provisioning status...");
    isProvisioned = false;
    saveConfiguration();
  }
}
```

#### 6. Remove MQTT Provisioning Code (Lines 987-1034, 1100-1132)
Delete entire MQTT provisioning response handler and MQTT provisioning logic.

#### 7. Update loadConfiguration() (Lines 1233-1234)
Remove MQTT credential loading:
```cpp
// ✅ REMOVED: MQTT credentials no longer used
// mqttUsername = prefs.getString("mqttuser", "hospitalEsp32");
// mqttPassword = prefs.getString("mqttpwd", "ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF/Q=");
```

#### 8. Update saveConfiguration() (Lines 1265-1266)
Remove MQTT credential saving:
```cpp
// ✅ REMOVED: MQTT credentials no longer used
// prefs.putString("mqttuser", mqttUsername);
// prefs.putString("mqttpwd", mqttPassword);
```

---

## Files Modified

1. **esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino** (~300 lines changed)
   - Add HTTPClient library
   - Remove hardcoded credentials
   - Add certificate storage functions (80 lines)
   - Replace attemptProvisioning() (60 lines)
   - Replace connectToMQTT() (30 lines)
   - Update captive portal HTML
   - Update setup(), loadConfiguration(), saveConfiguration()
   - Remove MQTT provisioning handlers

---

## Testing Plan (Day 7)

After implementation, we'll test:
1. Backend certificate service initialization
2. Generate provisioning code via Swagger UI
3. ESP32 captive portal with code entry
4. Certificate issuance via HTTPS
5. Certificate storage in SPIFFS
6. MQTT connection with client certificate
7. Vitals data publishing
8. Certificate revocation
9. Device re-provisioning

---

## Risk Assessment

**Low Risk:**
- Backend and Mosquitto are already configured and tested (Days 1-4 complete)
- Backup of original firmware created
- Changes are well-defined and documented
- Can rollback by restoring .backup-before-cert-auth file

**Medium Risk:**
- ESP32 firmware changes are substantial (~300 lines)
- HTTPS provisioning is new (replacing MQTT provisioning)
- Certificate storage on SPIFFS needs to work correctly

**Mitigation:**
- Detailed step-by-step implementation plan
- Each change is documented with before/after examples
- Can test incrementally
- Original firmware backed up

---

## Ready to Proceed?

All prerequisites complete:
- ✅ Day 1: Hospital CA certificate generated
- ✅ Day 2: Certificate service created
- ✅ Day 3: Provisioning API endpoints ready
- ✅ Day 4: Mosquitto configured for mTLS
- ✅ Firmware backup created

**Estimated time to implement Days 5-6:** 1-2 hours
**Estimated time for Day 7 testing:** 1-2 hours

---

## User Decision Required

Do you want me to proceed with implementing these ESP32 firmware changes?

**Option 1:** Yes, implement all Day 5-6 changes now
**Option 2:** Pause here and test Days 1-4 (backend/Mosquitto) first
**Option 3:** Review and approve specific changes before implementation

Please confirm how you'd like to proceed.
