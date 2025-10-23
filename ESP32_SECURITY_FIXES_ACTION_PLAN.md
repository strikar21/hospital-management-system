# ESP32 Security Fixes - Action Plan

**Date:** October 17, 2025
**Priority:** CRITICAL - Testing Environment
**Scope:** Issues 2, 3, 4, 7 (Issues 1, 5, 6, 8 deferred for testing phase)

---

## OVERVIEW

For testing environment, we're focusing on the **4 security-critical issues** that can be fixed quickly:

| # | Issue | Severity | Fix Effort | Timeline |
|---|-------|----------|------------|----------|
| 2 | HTTP instead of HTTPS | 🔴 CRITICAL | MEDIUM | 1-2 days |
| 3 | MQTT TLS not enforced on ESP32 | 🔴 CRITICAL | LOW | 4-8 hours |
| 4 | Plaintext credential storage | 🔴 CRITICAL | MEDIUM | 1-2 days |
| 7 | No fail-safe mechanisms | 🔴 CRITICAL | MEDIUM | 1-2 days |

**Deferred for Testing:**
- ❌ Issue 1: Mock sensor data (acceptable for testing)
- ❌ Issue 5: No secure boot (requires eFUSE burning)
- ❌ Issue 6: No sensor calibration (mock data doesn't need calibration)
- ❌ Issue 8: Door scanner no auth (lower priority)

---

## ISSUE #2: HTTP INSTEAD OF HTTPS

### Current State
- ❌ Backend HTTP on port 8001
- ❌ ESP32 firmware uses HTTP
- ❌ PHI data (vitals, patient IDs) exposed in plaintext

### Fix Plan

#### Backend: Enable HTTPS (1-2 days)

**Step 1: Generate SSL Certificate (30 mins)**

For testing, use self-signed certificate:

```bash
# Navigate to backend directory
cd hospital-backend

# Create certs directory
mkdir -p certs

# Generate self-signed certificate (valid for 1 year)
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout certs/server.key \
  -out certs/server.crt \
  -days 365 \
  -subj "/C=IN/ST=Karnataka/L=Bangalore/O=Hospital/CN=192.168.0.113"

# Verify certificate created
ls -la certs/
```

**Step 2: Update Backend Configuration (15 mins)**

Edit [hospital-backend/app/core/config.py](./hospital-backend/app/core/config.py):

```python
# Line 35 - Add SSL configuration
class Settings(BaseSettings):
    # ... existing config ...

    # SSL Configuration
    enableSsl: bool = True  # ✅ CHANGED: Enable by default
    sslCertPath: str = "certs/server.crt"
    sslKeyPath: str = "certs/server.key"
```

**Step 3: Update main.py (Already configured!)**

[main.py:449-468](./hospital-backend/main.py#L449-L468) already has SSL support:

```python
if __name__ == "__main__":
    ssl_config = {}
    if settings.enableSsl and settings.sslCertPath and settings.sslKeyPath:
        if os.path.exists(settings.sslCertPath) and os.path.exists(settings.sslKeyPath):
            ssl_config = {
                "ssl_certfile": settings.sslCertPath,
                "ssl_keyfile": settings.sslKeyPath
            }
            logger.info(f"🔒 HTTPS enabled with SSL certificate: {settings.sslCertPath}")
```

✅ **No changes needed!** Just enable in config.

**Step 4: Test Backend HTTPS (10 mins)**

```bash
# Restart backend
cd hospital-backend
python main.py

# Should see:
# 🔒 HTTPS enabled with SSL certificate: certs/server.crt

# Test HTTPS endpoint
curl -k https://192.168.0.113:8001/health
# (-k flag ignores self-signed cert warning)
```

#### ESP32: Update to HTTPS (2-4 hours)

**Step 5: Update ESP32 Firmware**

Edit [esp32_hospital_watch_complete.ino](./esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino):

**FINDING:** ESP32 firmware **ALREADY REMOVED HTTP** in v4.2.0!

Looking at the firmware:
- Line 16: `✅ REMOVED: HTTP provisioning (now MQTT-only)`
- Line 544: No HTTP provisioning URL (commented out)
- **Provisioning is now 100% MQTT-only** (Lines 1071-1132)

**✅ GOOD NEWS:** ESP32 watch doesn't use HTTP anymore! It's MQTT-only.

**❌ BUT:** Door scanner still uses HTTP (Lines 557-613 in esp32_door_scanner.ino)

**Step 6: Update Door Scanner to HTTPS (if needed)**

Edit [esp32_door_scanner.ino](./esp32_door_scanner/esp32_door_scanner.ino):

Currently uses HTTP:
```cpp
// Line 557-570 (approximate)
String url = "http://" + backend_server + ":" + backend_port + "/api/v1/esp32/door-scanner/" + DEVICE_ID + "/scan";
HTTPClient http;
http.begin(url);
```

Change to HTTPS:
```cpp
// Use WiFiClientSecure for HTTPS
WiFiClientSecure httpsClient;
httpsClient.setInsecure();  // For testing with self-signed cert

String url = "https://" + backend_server + ":" + backend_port + "/api/v1/esp32/door-scanner/" + DEVICE_ID + "/scan";
HTTPClient http;
http.begin(httpsClient, url);  // ✅ Pass secure client
```

**Alternative for Testing:** Keep door scanner HTTP for now (lower priority).

#### Step 7: Update Frontend to HTTPS (10 mins)

Edit [hospital-display-app/src/config/apiConfig.ts](./hospital-display-app/src/config/apiConfig.ts):

```typescript
export const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://192.168.0.113:8001';
// ✅ CHANGED: http → https
```

**Step 8: Update CORS (5 mins)**

Edit [hospital-backend/main.py](./hospital-backend/main.py#L199-206):

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://localhost:3000",  # ✅ ADD: HTTPS support
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)
```

### Testing Issue #2 Fix

```bash
# 1. Start backend with HTTPS
cd hospital-backend
python main.py
# Verify: "🔒 HTTPS enabled"

# 2. Test health endpoint
curl -k https://192.168.0.113:8001/health

# 3. Start frontend
cd hospital-display-app
npm start

# 4. Open browser: https://localhost:3000
# Accept self-signed cert warning
# Verify: API calls work

# 5. Check browser console: No CORS errors
```

**✅ Success Criteria:**
- Backend logs show "🔒 HTTPS enabled"
- Browser shows lock icon (may show warning for self-signed)
- All API calls work
- No CORS errors

---

## ISSUE #3: MQTT TLS NOT ENFORCED ON ESP32

### Current State
- ✅ Backend MQTT service configured for TLS 1.2 (port 8883)
- ✅ Mosquitto broker configured for TLS
- ✅ CA certificate path set in firmware
- ⚠️ ESP32 falls back to insecure if TLS fails

### Fix Plan (4-8 hours)

#### Step 1: Verify Mosquitto TLS Configuration (30 mins)

Check [docker-compose.yml](./docker-compose.yml#L41-55):

```yaml
mosquitto:
  image: eclipse-mosquitto:2.0
  container_name: hospital_mosquitto
  ports:
    - "8883:8883"  # ✅ TLS MQTT
  volumes:
    - ./mosquitto/config:/mosquitto/config:ro
    - ./mosquitto/certs:/mosquitto/certs:ro
    - ./mosquitto/data:/mosquitto/data
```

Verify configuration:
```bash
# Check mosquitto config
cat mosquitto/config/mosquitto.conf

# Should have:
# listener 8883
# cafile /mosquitto/certs/ca.crt
# certfile /mosquitto/certs/server.crt
# keyfile /mosquitto/certs/server.key
# require_certificate false
# allow_anonymous false
```

#### Step 2: Generate/Verify MQTT TLS Certificates (1 hour)

```bash
cd mosquitto/certs

# Generate CA certificate (if not exists)
openssl req -new -x509 -days 365 -extensions v3_ca \
  -keyout ca.key -out ca.crt \
  -subj "/C=IN/ST=Karnataka/L=Bangalore/O=Hospital/CN=Hospital-MQTT-CA"

# Generate server certificate
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr \
  -subj "/C=IN/ST=Karnataka/L=Bangalore/O=Hospital/CN=192.168.0.113"

# Sign server certificate with CA
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out server.crt -days 365

# Set permissions
chmod 644 ca.crt server.crt
chmod 600 ca.key server.key

# Verify certificates
openssl verify -CAfile ca.crt server.crt
# Should output: server.crt: OK
```

#### Step 3: Upload CA Certificate to ESP32 SPIFFS (2-3 hours)

**A. Install ESP32 Filesystem Uploader (if not already)**

Download from: https://github.com/me-no-dev/arduino-esp32fs-plugin/releases

Install to: `C:\Users\Srika\Documents\Arduino\tools\ESP32FS\tool\esp32fs.jar`

**B. Create SPIFFS Data Directory**

```bash
cd esp32_hospital_watch_complete

# Create data directory
mkdir data

# Copy CA certificate
cp ../mosquitto/certs/ca.crt data/ca.crt

# Verify file exists
ls -la data/
# Should show: ca.crt
```

**C. Upload to ESP32**

1. Connect ESP32 via USB
2. In Arduino IDE: Tools → ESP32 Sketch Data Upload
3. Wait for upload to complete (~30 seconds)
4. Verify: Serial monitor shows "✅ CA certificate loaded from SPIFFS"

**Alternative: Manual SPIFFS Upload via esptool**

```bash
# Generate SPIFFS image
mkspiffs -c data -b 4096 -p 256 -s 1507328 spiffs.bin

# Upload to ESP32 (replace COM3 with your port)
esptool.py --chip esp32 --port COM3 --baud 921600 \
  write_flash 0x291000 spiffs.bin
```

#### Step 4: Remove Insecure Fallback in ESP32 Firmware (15 mins)

Edit [esp32_hospital_watch_complete.ino](./esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino):

**Line 916-924:**
```cpp
void configureTLS() {
  if (caCertificate.length() > 0) {
    wifiClient.setCACert(caCertificate.c_str());
    Serial.println("🔐 TLS configured with CA certificate from SPIFFS");
  } else {
    Serial.println("⚠️ WARNING: No CA certificate loaded - using insecure mode");
    wifiClient.setInsecure();  // ❌ REMOVE THIS
  }
}
```

**FIX:**
```cpp
void configureTLS() {
  if (caCertificate.length() > 0) {
    wifiClient.setCACert(caCertificate.c_str());
    Serial.println("🔐 TLS configured with CA certificate from SPIFFS");
  } else {
    // ✅ FAIL HARD instead of falling back
    Serial.println("❌ CRITICAL: No CA certificate loaded - CANNOT connect securely");
    Serial.println("❌ Please upload ca.crt to SPIFFS before using device");
    // Flash LED rapidly to indicate critical error
    while (true) {
      digitalWrite(2, HIGH);
      delay(100);
      digitalWrite(2, LOW);
      delay(100);
    }
  }
}
```

#### Step 5: Test MQTT TLS Connection (30 mins)

```bash
# 1. Restart MQTT broker with TLS
docker-compose restart mosquitto

# 2. Verify broker listening on TLS port
docker logs hospital_mosquitto
# Should show: "Opening ipv4 listen socket on port 8883"

# 3. Test MQTT TLS from command line
mosquitto_sub -h 192.168.0.113 -p 8883 \
  -u hospitalEsp32 -P "ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF/Q=" \
  -t "hospital/devices/+/vitals" \
  --cafile mosquitto/certs/ca.crt

# Should connect without errors

# 4. Flash updated firmware to ESP32
# (Arduino IDE: Upload)

# 5. Monitor ESP32 serial output
# Should see:
# "✅ CA certificate loaded from SPIFFS (xxxx bytes)"
# "🔐 TLS configured with CA certificate from SPIFFS"
# "✅ MQTT TLS Connected with device credentials!"
```

**✅ Success Criteria:**
- ESP32 serial shows "✅ CA certificate loaded from SPIFFS"
- ESP32 serial shows "✅ MQTT TLS Connected"
- No "using insecure mode" warnings
- Vitals transmitted successfully

---

## ISSUE #4: PLAINTEXT CREDENTIAL STORAGE

### Current State
- ❌ MQTT passwords stored in NVS flash without encryption
- ❌ WiFi passwords stored in NVS flash without encryption
- ❌ Physical access allows credential theft

### Fix Plan (1-2 days)

#### Understanding ESP32 Flash Encryption

**How it works:**
1. Generate 256-bit AES encryption key
2. Burn key to eFUSE (one-time programmable, cannot be read back)
3. All flash writes automatically encrypted by hardware
4. All flash reads automatically decrypted by hardware
5. **IMPORTANT:** Once enabled, cannot be disabled (hardware enforced)

**Trade-offs:**
- ✅ Credentials protected even with physical access
- ✅ Firmware also encrypted
- ❌ Cannot downgrade firmware without re-flashing (loses all data)
- ❌ Slightly slower flash operations (~10% performance hit)
- ❌ Cannot use esptool.py to read flash anymore

#### Step 1: Backup Current Device Configuration (30 mins)

**BEFORE enabling flash encryption, backup all devices:**

```bash
# For each ESP32 device:
# 1. Connect via USB
# 2. Read device info via Serial monitor
# 3. Save to file

# Create backup directory
mkdir esp32_backups
cd esp32_backups

# Backup Device 1
# (Connect ESP32_WATCH_001)
# Open Arduino Serial Monitor
# Type: /status
# Save output to: ESP32_WATCH_001_backup.txt

# Repeat for all devices
```

**Save configuration:**
```
Device ID: ESP32_WATCH_001
Serial: SN_W001
MAC: 30:AE:A4:12:34:56
WiFi SSID: HospitalNetwork
MQTT Server: 192.168.0.113
MQTT Port: 8883
MQTT Username: ESP32_WATCH_001_mqtt
Patient ID: (if assigned)
```

#### Step 2: Enable Flash Encryption (Per Device, 1-2 hours total)

**⚠️ CRITICAL WARNING:**
- This is **IRREVERSIBLE** (eFUSE burning)
- Once enabled, **CANNOT be disabled**
- Device will **LOSE ALL DATA** during encryption
- Must **RE-PROVISION** device after encryption

**Process for EACH device:**

1. **Connect ESP32 via USB**

2. **Check if already encrypted:**
```bash
esptool.py --port COM3 summary
# Look for: "Flash Encryption: Enabled"
# If already enabled, skip this device
```

3. **Enable flash encryption:**
```bash
# Navigate to firmware directory
cd esp32_hospital_watch_complete

# Flash firmware with flash encryption
esptool.py --chip esp32 --port COM3 \
  --before default_reset --after no_reset \
  write_flash --flash_mode dio --flash_freq 40m \
  --flash_size detect 0x1000 bootloader.bin \
  0x8000 partitions.bin 0x10000 firmware.bin

# Burn eFUSE (IRREVERSIBLE)
espefuse.py --port COM3 burn_efuse FLASH_CRYPT_CNT
espefuse.py --port COM3 burn_efuse FLASH_CRYPT_CONFIG 0xF

# Device will reboot and encrypt flash (takes 1-2 minutes)
```

4. **Verify encryption enabled:**
```bash
esptool.py --port COM3 summary
# Should show: "Flash Encryption: Enabled"
```

5. **Re-provision device:**
- Device will lose all configuration (WiFi, credentials, etc.)
- Connect to "HospitalWatch" hotspot
- Configure WiFi and provisioner credentials
- Provision via MQTT

6. **Verify credentials protected:**
```bash
# Try to read flash (should fail or show encrypted data)
esptool.py --port COM3 read_flash 0x9000 0x5000 flash_dump.bin
# Data should be encrypted (not readable)
```

#### Alternative: Simpler Approach for Testing

**If flash encryption is too risky for testing, use application-level encryption:**

Add to firmware (Lines 1265-1280):

```cpp
// Simple XOR encryption for credentials (better than plaintext)
String encryptCredential(String plaintext, String key) {
  String encrypted = "";
  for (int i = 0; i < plaintext.length(); i++) {
    char encChar = plaintext[i] ^ key[i % key.length()];
    encrypted += encChar;
  }
  return encrypted;
}

void saveConfiguration() {
  String encryptionKey = "HospitalEncryptKey2025";  // Hardcoded (not ideal but better than plaintext)

  prefs.putString("ssid", wifiSSID);
  prefs.putString("pass", encryptCredential(wifiPassword, encryptionKey));  // ✅ ENCRYPTED
  prefs.putString("mqttuser", mqttUsername);
  prefs.putString("mqttpwd", encryptCredential(mqttPassword, encryptionKey));  // ✅ ENCRYPTED
  // ... rest of config
}

void loadConfiguration() {
  String encryptionKey = "HospitalEncryptKey2025";

  wifiSSID = prefs.getString("ssid", "");
  wifiPassword = encryptCredential(prefs.getString("pass", ""), encryptionKey);  // ✅ DECRYPT
  mqttUsername = prefs.getString("mqttuser", "hospitalEsp32");
  mqttPassword = encryptCredential(prefs.getString("mqttpwd", ""), encryptionKey);  // ✅ DECRYPT
  // ... rest of config
}
```

**⚠️ This is NOT as secure as flash encryption but:**
- ✅ Better than plaintext
- ✅ Reversible (can disable for testing)
- ✅ No eFUSE burning required
- ❌ Attacker with firmware source can decrypt

**Recommendation for Testing:** Use application-level encryption, then enable flash encryption for production.

### Testing Issue #4 Fix

```bash
# Test 1: Verify credentials encrypted in flash
# 1. Configure and provision device
# 2. Dump flash
esptool.py --port COM3 read_flash 0x9000 0x5000 flash_dump.bin

# 3. Open flash_dump.bin in hex editor
# 4. Search for WiFi password or MQTT password
# 5. Should NOT find plaintext passwords

# Test 2: Verify device still works after encryption
# 1. Reboot device
# 2. Check serial output
# 3. Should reconnect to WiFi and MQTT
# 4. Vitals should transmit normally

# Test 3: Verify re-provisioning works
# 1. Factory reset device (erase flash)
# 2. Re-configure via captive portal
# 3. Should provision and work normally
```

**✅ Success Criteria:**
- Passwords not visible in flash dump
- Device connects to WiFi/MQTT after reboot
- Re-provisioning works correctly

---

## ISSUE #7: NO FAIL-SAFE MECHANISMS

### Current State
- ❌ No watchdog timer (device can hang silently)
- ❌ No sensor validation (accepts any values)
- ❌ No connectivity monitoring (doesn't detect prolonged disconnection)
- ❌ No automatic recovery (requires manual reset)

### Fix Plan (1-2 days)

#### Step 1: Add Hardware Watchdog Timer (2 hours)

Add to [esp32_hospital_watch_complete.ino](./esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino):

**After Line 31 (includes):**
```cpp
#include <esp_task_wdt.h>

// Watchdog Configuration
#define WDT_TIMEOUT 30  // 30 seconds (if no feed, device resets)
```

**In setup() function (after Line 493):**
```cpp
void setup() {
  // ... existing setup code ...

  // ✅ NEW: Initialize watchdog timer
  Serial.println("⏱️ Initializing hardware watchdog (30s timeout)...");
  esp_task_wdt_init(WDT_TIMEOUT, true);  // Enable panic on timeout
  esp_task_wdt_add(NULL);  // Add current thread to watchdog
  Serial.println("✅ Watchdog enabled - device will reset if hung for >30s");

  // ... rest of setup ...
}
```

**In loop() function (after Line 576):**
```cpp
void loop() {
  // ✅ FIRST LINE: Feed watchdog
  esp_task_wdt_reset();  // Tell watchdog we're alive

  // ... existing loop code ...

  delay(100);
}
```

**Purpose:**
- If device hangs/crashes, watchdog resets after 30 seconds
- Prevents silent failures (device appears on but not working)

#### Step 2: Add Sensor Value Validation (1 hour)

Add validation function (after Line 340):

```cpp
// ====================================
// SENSOR VALIDATION (v4.3.0)
// ====================================

struct VitalsValidation {
  bool valid;
  String reason;
};

VitalsValidation validateVitals(float hr, float temp, int spo2, int rr) {
  VitalsValidation result = {true, ""};

  // Heart Rate validation
  if (hr < 20 || hr > 300) {
    result.valid = false;
    result.reason = "Invalid heart rate: " + String(hr);
    return result;
  }

  // Temperature validation (Celsius)
  float tempC = (temp - 32.0) * 5.0 / 9.0;
  if (tempC < 30.0 || tempC > 45.0) {
    result.valid = false;
    result.reason = "Invalid temperature: " + String(tempC) + "°C";
    return result;
  }

  // SpO2 validation
  if (spo2 < 50 || spo2 > 100) {
    result.valid = false;
    result.reason = "Invalid SpO2: " + String(spo2) + "%";
    return result;
  }

  // Respiratory Rate validation
  if (rr < 4 || rr > 60) {
    result.valid = false;
    result.reason = "Invalid respiratory rate: " + String(rr);
    return result;
  }

  return result;
}

int invalidVitalsCount = 0;
unsigned long lastValidVitalsTime = 0;
```

**Update sendVitals() function (Line 1160):**

```cpp
void sendVitals() {
  if (!mqttClient.connected() || !isAssigned) {
    if (!mqttClient.connected()) {
      connectToMQTT();
    }
    return;
  }

  // ✅ NEW: Validate vitals before sending
  VitalsValidation validation = validateVitals(heartRate, temperature, oxygenSat, respiratoryRate);

  if (!validation.valid) {
    invalidVitalsCount++;
    Serial.println("⚠️ VALIDATION FAILED: " + validation.reason);

    // After 5 consecutive failures, send alert
    if (invalidVitalsCount >= 5) {
      sendAlert("sensorValidationFailure", "high",
                "5+ invalid readings: " + validation.reason, 0.95);
      invalidVitalsCount = 0;  // Reset counter
    }
    return;  // Don't send invalid data
  }

  // Reset failure counter on valid reading
  invalidVitalsCount = 0;
  lastValidVitalsTime = millis();

  // ... rest of sendVitals() function ...
}
```

#### Step 3: Add Connectivity Monitoring (1 hour)

Add after Line 575 in loop():

```cpp
void loop() {
  // ... existing loop code ...

  // ✅ NEW: Monitor prolonged disconnection (v4.3.0)
  checkConnectivityHealth();

  delay(100);
}

// Add this function after line 575
void checkConnectivityHealth() {
  static unsigned long lastCheck = 0;
  if (millis() - lastCheck < 60000) return;  // Check every 60 seconds
  lastCheck = millis();

  // Check WiFi connectivity
  if (!wifiConnected && stored_ssid.length() > 0) {
    Serial.println("🔄 WiFi disconnected - attempting reconnect...");
    connectToWiFi();
  }

  // Check MQTT connectivity
  if (wifiConnected && isProvisioned && !mqttClient.connected()) {
    Serial.println("🔄 MQTT disconnected - attempting reconnect...");
    connectToMQTT();
  }

  // Check if vitals haven't been sent in >5 minutes (silent failure)
  if (isAssigned && (millis() - lastValidVitalsTime) > 300000) {
    Serial.println("⚠️ WARNING: No valid vitals sent in 5+ minutes");
    sendAlert("vitalsSendingFailure", "high",
              "No vitals sent for 5+ minutes", 1.0);
    lastValidVitalsTime = millis();  // Reset to avoid spam
  }
}
```

#### Step 4: Add Automatic Recovery (30 mins)

Add recovery logic (after Line 575):

```cpp
// ====================================
// AUTOMATIC RECOVERY (v4.3.0)
// ====================================

unsigned long lastSuccessfulOperation = 0;
int consecutiveFailures = 0;

void checkAndRecover() {
  static unsigned long lastRecoveryCheck = 0;
  if (millis() - lastRecoveryCheck < 300000) return;  // Check every 5 minutes
  lastRecoveryCheck = millis();

  // If no successful operations in 10 minutes, restart
  if (isProvisioned && (millis() - lastSuccessfulOperation) > 600000) {
    Serial.println("❌ CRITICAL: No successful operations in 10 minutes");
    Serial.println("🔄 Initiating automatic recovery...");

    // Try one last time to reconnect
    if (!wifiConnected) connectToWiFi();
    if (wifiConnected && !mqttClient.connected()) connectToMQTT();

    // If still failed, restart device
    delay(5000);
    if (!wifiConnected || !mqttClient.connected()) {
      Serial.println("🔄 Recovery failed - restarting device...");
      ESP.restart();
    }
  }
}

// Call in loop()
void loop() {
  // ... existing code ...

  checkConnectivityHealth();
  checkAndRecover();  // ✅ ADD THIS

  delay(100);
}
```

**Update successful operations tracker:**

```cpp
// In sendVitals() after successful publish:
if (mqttClient.publish(topic.c_str(), payload.c_str())) {
  lastSuccessfulOperation = millis();  // ✅ TRACK SUCCESS
  consecutiveFailures = 0;
  Serial.println("📊 Vitals sent successfully");
}

// In sendMQTTHeartbeat() after successful publish:
if (mqttClient.publish(topic.c_str(), payload.c_str())) {
  lastSuccessfulOperation = millis();  // ✅ TRACK SUCCESS
  Serial.println("💓 MQTT Heartbeat sent");
}
```

#### Step 5: Add Status LED Indicators (30 mins)

Add LED feedback for device state:

```cpp
// After Line 138
// ====================================
// STATUS LED PATTERNS (v4.3.0)
// ====================================

void updateStatusLED() {
  static unsigned long lastBlink = 0;
  static bool ledState = false;

  unsigned long blinkInterval;

  if (!wifiConnected) {
    // Fast blink - No WiFi
    blinkInterval = 200;
  } else if (!isProvisioned) {
    // Medium blink - WiFi but not provisioned
    blinkInterval = 500;
  } else if (!isAssigned) {
    // Slow blink - Provisioned but not assigned
    blinkInterval = 1000;
  } else {
    // Solid on - Fully operational
    digitalWrite(2, HIGH);
    return;
  }

  if (millis() - lastBlink > blinkInterval) {
    ledState = !ledState;
    digitalWrite(2, ledState);
    lastBlink = millis();
  }
}

// Call in loop()
void loop() {
  // ... existing code ...

  updateStatusLED();  // ✅ ADD THIS

  delay(100);
}
```

### Testing Issue #7 Fixes

```bash
# Test 1: Watchdog Timer
# 1. Flash updated firmware
# 2. Add delay(60000) in loop() temporarily (to simulate hang)
# 3. Device should auto-reset after 30 seconds
# 4. Serial output should show: "Hardware Watchdog Timer Triggered"

# Test 2: Sensor Validation
# 1. Modify mock data to send invalid values
heartRate = 500;  // Invalid
# 2. Serial should show: "⚠️ VALIDATION FAILED: Invalid heart rate: 500"
# 3. After 5 failures, should send alert
# 4. Vitals should NOT be transmitted to backend

# Test 3: Connectivity Monitoring
# 1. Disconnect WiFi (turn off router)
# 2. Wait 60 seconds
# 3. Serial should show: "🔄 WiFi disconnected - attempting reconnect..."
# 4. Reconnect WiFi
# 5. Device should auto-reconnect

# Test 4: Automatic Recovery
# 1. Block MQTT broker (docker stop hospital_mosquitto)
# 2. Wait 10 minutes
# 3. Device should restart automatically
# 4. Serial should show: "🔄 Recovery failed - restarting device..."

# Test 5: Status LED
# 1. Observe LED pattern during each state:
#    - Fast blink (200ms): No WiFi
#    - Medium blink (500ms): WiFi but not provisioned
#    - Slow blink (1000ms): Provisioned but not assigned
#    - Solid on: Fully operational
```

**✅ Success Criteria:**
- Watchdog resets device if hung >30s
- Invalid vitals rejected with alert after 5 failures
- Auto-reconnects to WiFi/MQTT
- Auto-restarts if no activity for 10 minutes
- LED indicates device state clearly

---

## IMPLEMENTATION TIMELINE

### Day 1: HTTPS + MQTT TLS (Priority 1)
**Morning (4 hours):**
- Generate SSL certificates (backend + MQTT)
- Enable HTTPS on backend
- Update frontend API URL
- Test HTTPS endpoints

**Afternoon (4 hours):**
- Generate MQTT CA certificate
- Upload CA cert to ESP32 SPIFFS
- Remove insecure fallback in firmware
- Test MQTT TLS connection

**Evening (1 hour):**
- Full end-to-end testing
- Verify vitals transmission over TLS
- Document any issues

### Day 2: Credential Encryption + Fail-Safe (Priority 2)
**Morning (4 hours):**
- Backup all device configurations
- Choose encryption approach (flash vs application)
- Implement credential encryption
- Test on one device

**Afternoon (3 hours):**
- Add watchdog timer
- Add sensor validation
- Add connectivity monitoring

**Evening (2 hours):**
- Add automatic recovery
- Add status LED patterns
- Full testing of all fail-safe mechanisms

### Day 3: Testing & Validation
**Full Day:**
- Comprehensive testing of all 4 fixes
- Stress testing (disconnect scenarios)
- Security validation
- Documentation updates

---

## TESTING CHECKLIST

### Pre-Implementation Checklist
- [ ] Backup all ESP32 device configurations
- [ ] Backup current firmware versions
- [ ] Note all device MAC addresses
- [ ] Document current WiFi/MQTT settings
- [ ] Test baseline vitals transmission

### Issue #2: HTTPS
- [ ] Backend shows "🔒 HTTPS enabled"
- [ ] curl -k https://192.168.0.113:8001/health works
- [ ] Frontend connects via HTTPS
- [ ] No CORS errors in browser console
- [ ] All API endpoints work

### Issue #3: MQTT TLS
- [ ] CA certificate uploaded to ESP32 SPIFFS
- [ ] ESP32 shows "✅ CA certificate loaded"
- [ ] ESP32 shows "✅ MQTT TLS Connected"
- [ ] No "insecure mode" warnings
- [ ] Vitals transmitted successfully
- [ ] mosquitto_sub with TLS works

### Issue #4: Credential Encryption
- [ ] Flash dump doesn't show plaintext passwords
- [ ] Device reconnects after reboot
- [ ] Re-provisioning works
- [ ] Credentials survive power cycle
- [ ] No performance degradation

### Issue #7: Fail-Safe Mechanisms
- [ ] Watchdog resets hung device
- [ ] Invalid vitals rejected
- [ ] Auto-reconnects to WiFi
- [ ] Auto-reconnects to MQTT
- [ ] Auto-restarts after prolonged failure
- [ ] LED indicates correct states

### Post-Implementation Validation
- [ ] All 4 issues marked as FIXED
- [ ] System stable for 24 hours
- [ ] No regressions in existing features
- [ ] Documentation updated
- [ ] Team trained on new security features

---

## ROLLBACK PLAN

If issues arise during implementation:

### Rollback Issue #2 (HTTPS)
```python
# In config.py
enableSsl: bool = False  # Disable HTTPS

# In frontend
API_BASE_URL = 'http://192.168.0.113:8001'  # Revert to HTTP
```

### Rollback Issue #3 (MQTT TLS)
```cpp
// In ESP32 firmware
wifiClient.setInsecure();  // Re-enable insecure fallback
```

### Rollback Issue #4 (Encryption)
- If using flash encryption: **CANNOT ROLLBACK** (eFUSE burned)
- If using application encryption: Remove encryption functions, re-flash firmware

### Rollback Issue #7 (Fail-Safe)
- Comment out watchdog init
- Comment out validation checks
- Re-flash firmware

---

## SUCCESS METRICS

**Security:**
- ✅ 0% credentials in plaintext
- ✅ 100% connections encrypted (HTTPS + MQTT TLS)
- ✅ 0 security warnings in logs

**Reliability:**
- ✅ <0.1% device hang rate (watchdog prevents)
- ✅ <1% invalid vitals transmitted
- ✅ >99% uptime with auto-recovery
- ✅ <5 minutes to recover from connectivity loss

**User Experience:**
- ✅ No manual resets required
- ✅ Clear LED status indicators
- ✅ Automatic problem resolution
- ✅ No data loss during failures

---

## NOTES

**Why These 4 Issues?**
1. **Issue #2 (HTTPS)** - Protects PHI data in transit
2. **Issue #3 (MQTT TLS)** - Protects vitals data in transit
3. **Issue #4 (Encryption)** - Protects credentials at rest
4. **Issue #7 (Fail-Safe)** - Ensures system reliability

Together, these 4 fixes address the **"data in transit"** and **"device reliability"** attack surfaces, making the system suitable for testing with real network deployment.

**Deferred Issues (Acceptable for Testing):**
- Issue #1 (Mock data) - Testing doesn't need real sensors
- Issue #5 (Secure boot) - Requires eFUSE burning, can defer
- Issue #6 (Calibration) - Mock data doesn't need calibration
- Issue #8 (Door scanner auth) - Lower priority, separate system

---

**END OF ACTION PLAN**

Ready to implement these 4 critical security fixes for your testing environment.
