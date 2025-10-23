/*
 * ESP32 Hospital Watch - Certificate-Based Authentication
 * Version: 5.0.0
 *
 * Features:
 * - Automatic captive portal when connecting to hotspot
 * - Auto WiFi scanning with dropdown
 * - HTTPS certificate provisioning with one-time codes
 * - Certificate-based MQTT authentication (mTLS)
 * - MQTT TLS 1.2 authentication on port 8883
 * - NTP time synchronization for ISO 8601 timestamps
 * - MQTT vitals, alerts, and heartbeat
 * - 8 device-level alerts (moved 14 clinical alerts to backend)
 *
 * CHANGES FROM v4.2.0:
 * ✅ ADDED: HTTPClient library for HTTPS provisioning
 * ✅ REMOVED: Hardcoded shared MQTT credentials
 * ✅ ADDED: Certificate storage functions (SPIFFS)
 * ✅ CHANGED: HTTPS provisioning with one-time codes
 * ✅ CHANGED: MQTT connection uses client certificates (mTLS)
 */

#include <WiFi.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <PubSubClient.h>
#include <time.h>
#include <WiFiClientSecure.h>
#include <SPIFFS.h>
#include <HTTPClient.h>  // ✅ v5.0: Added for HTTPS provisioning
#include "PhysiologicalSimulator.h"  // ✅ v5.1: Vitals and ECG simulator

// ====================================
// DEVICE CONFIGURATION
// ====================================
const char* AP_SSID = "HospitalWatch";
const char* AP_PASSWORD = "";
const char* DEVICE_TYPE = "watch";
const char* FIRMWARE_VERSION = "5.0.0";

// ====================================
// GPIO PIN CONFIGURATION
// ====================================
#define MODE_SELECT_PIN 4  // GPIO 4 for ECG/EEG mode selection (HIGH=ECG, LOW=EEG)

// ====================================
// TLS CERTIFICATE - LOADED FROM SPIFFS
// ====================================
const char* CA_CERT_PATH = "/ca.crt";
String caCertificate = "";
String deviceCertificate = "";  // ✅ v5.0.2: Global to prevent .c_str() dangling pointers
String devicePrivateKey = "";   // ✅ v5.0.2: Global to prevent .c_str() dangling pointers

// ====================================
// NTP CONFIGURATION
// ====================================
const char* NTP_SERVER = "pool.ntp.org";
const long GMT_OFFSET_SEC = 19800;  // IST (UTC+5:30)
const int DAYLIGHT_OFFSET_SEC = 0;

// ====================================
// NETWORK COMPONENTS
// ====================================
WebServer server(80);
DNSServer dnsServer;
WiFiClientSecure wifiClient;
PubSubClient mqttClient(wifiClient);
Preferences prefs;

// DNS and Captive Portal
const byte DNS_PORT = 53;
IPAddress apIP(192, 168, 4, 1);
IPAddress netMsk(255, 255, 255, 0);

// ====================================
// DEVICE STATE
// ====================================
String deviceId = "";
String macAddress = "";
String wifiSSID = "";
String wifiPassword = "";
String serverIP = "";
String serverPort = "8001";
String mqttServer = "";
String mqttPort = "8883";
// ✅ v5.0: REMOVED hardcoded shared credentials
// Certificates loaded from SPIFFS instead
String serialNumber = "";
String assignedPatientId = "";
bool isProvisioned = false;
bool isAssigned = false;
bool wifiConnected = false;
bool ntpSynced = false;
bool provisioningInProgress = false;
String availableNetworks = "";
int networkCount = 0;
bool mqttConfigured = false;  // ✅ v5.0.3: Track if MQTT certs already loaded

// ====================================
// PHYSIOLOGICAL SIMULATOR
// ====================================
PhysiologicalSimulator simulator;  // ✅ v5.1: Realistic vitals and ECG generator

// ====================================
// TIMING
// ====================================
unsigned long lastScan = 0;
unsigned long lastVitals = 0;
unsigned long lastHeartbeat = 0;
unsigned long lastProvisionAttempt = 0;
unsigned long lastNtpSync = 0;

// ====================================
// SENSOR DATA - TODO: INTEGRATE REAL SENSORS
// ====================================
// TODO: Replace with MAX30102 (HR/SpO2) and MLX90614 (temperature) sensor readings
// For production: Read from I2C sensors instead of static values
float heartRate = 0;         // TODO: Read from MAX30102
float temperature = 0;       // TODO: Read from MLX90614
int oxygenSat = 0;           // TODO: Read from MAX30102
int batteryLevel = 100;      // TODO: Read from battery voltage ADC
int respiratoryRate = 0;     // TODO: Calculate from PPG waveform
float quality = 0;           // TODO: Read from sensor signal quality

// ====================================
// DEVICE MAINTENANCE
// ====================================
int batteryHealthPercentage = 100;
float batteryDrainRatePerHour = 0.0;
unsigned long lastBatteryUpdate = 0;
int lastBatteryLevel = 85;
int totalDisconnects = 0;
bool wasWifiConnected = false;
bool wasMqttConnected = false;
unsigned long disconnectTrackerLastCheck = 0;
unsigned long lastCommandReceivedAt = 0;
bool calibrationDue = false;

// ====================================
// SYSTEM ALERTS
// ====================================
int consecutiveInvalidReadings = 0;
unsigned long lastValidReading = 0;
bool sensorMalfunctionAlertSent = false;

float heartRateHistory[5] = {0, 0, 0, 0, 0};
float spo2History[5] = {0, 0, 0, 0, 0};
float tempHistory[5] = {0, 0, 0, 0, 0};
int historyIndex = 0;

unsigned long lastAlertCheck = 0;

// ====================================
// CERTIFICATE MANAGEMENT (v5.0.0)
// ====================================

/**
 * Check if device has provisioned certificates
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
 */
bool loadDeviceCertificate(String& cert, String& key) {
  if (!SPIFFS.begin(true)) {
    Serial.println("❌ SPIFFS mount failed");
    return false;
  }

  File certFile = SPIFFS.open("/device.crt", "r");
  if (!certFile) {
    Serial.println("❌ Device certificate file not found");
    return false;
  }
  cert = certFile.readString();
  certFile.close();

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
 */
bool saveCertificates(String cert, String key) {
  if (!SPIFFS.begin(true)) {
    Serial.println("❌ SPIFFS mount failed");
    return false;
  }

  File certFile = SPIFFS.open("/device.crt", "w");
  if (!certFile) {
    Serial.println("❌ Failed to open device certificate file for writing");
    return false;
  }
  certFile.print(cert);
  certFile.close();

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

// ====================================
// SPIFFS CA CERTIFICATE LOADER
// ====================================
bool loadCACertificate() {
  if (!SPIFFS.begin(true)) {
    Serial.println("❌ SPIFFS mount failed");
    return false;
  }

  File file = SPIFFS.open(CA_CERT_PATH, "r");
  if (!file) {
    Serial.println("❌ CA certificate file not found: " + String(CA_CERT_PATH));
    Serial.println("💡 Please upload ca.crt to SPIFFS");
    return false;
  }

  caCertificate = file.readString();
  file.close();

  if (caCertificate.length() == 0) {
    Serial.println("❌ CA certificate file is empty");
    return false;
  }

  Serial.println("✅ CA certificate loaded from SPIFFS (" + String(caCertificate.length()) + " bytes)");
  return true;
}

// ====================================
// ISO 8601 TIMESTAMP GENERATION
// ====================================
String getISO8601Timestamp() {
  if (!ntpSynced) {
    Serial.println("⚠️ Time not synced! Using millis() fallback");
    return String(millis());
  }

  time_t now = time(nullptr);
  struct tm timeinfo;
  gmtime_r(&now, &timeinfo);

  char iso_timestamp[25];
  int milliseconds = (millis() % 1000);
  snprintf(iso_timestamp, sizeof(iso_timestamp),
           "%04d-%02d-%02dT%02d:%02d:%02d.%03dZ",
           timeinfo.tm_year + 1900,
           timeinfo.tm_mon + 1,
           timeinfo.tm_mday,
           timeinfo.tm_hour,
           timeinfo.tm_min,
           timeinfo.tm_sec,
           milliseconds);

  return String(iso_timestamp);
}

// ====================================
// NTP TIME SYNCHRONIZATION
// ====================================
void syncNTPTime() {
  if (!wifiConnected) return;

  Serial.println("🕐 Syncing time with NTP...");
  configTime(GMT_OFFSET_SEC, DAYLIGHT_OFFSET_SEC, NTP_SERVER);

  int attempts = 0;
  while (attempts < 10) {
    time_t now = time(nullptr);
    if (now > 1000000000) {
      ntpSynced = true;
      struct tm timeinfo;
      localtime_r(&now, &timeinfo);
      Serial.println("✅ NTP synced: " + String(asctime(&timeinfo)));
      lastNtpSync = millis();
      return;
    }
    delay(500);
    attempts++;
    Serial.print(".");
  }

  Serial.println("\n⚠️ NTP sync failed - timestamps will be degraded!");
}

// ====================================
// ALERT SYSTEM
// ====================================
void sendAlert(String alertType, String severity, String message, float confidence) {
  if (!mqttClient.connected() || !isAssigned) return;

  String topic = "hospital/devices/" + deviceId + "/alerts";

  JsonDocument doc;
  doc["alertType"] = alertType;
  doc["severity"] = severity;
  doc["message"] = message;
  doc["source"] = "Watch";
  doc["confidence"] = confidence;
  doc["timestamp"] = getISO8601Timestamp();
  doc["deviceId"] = deviceId;
  doc["patientId"] = assignedPatientId;
  doc["category"] = "device";

  String payload;
  serializeJson(doc, payload);

  if (mqttClient.publish(topic.c_str(), payload.c_str())) {
    String severityUpper = severity;
    severityUpper.toUpperCase();
    Serial.println("🚨 [" + severityUpper + "] " + alertType);
    flashAlertPattern(severity);
  }
}

void flashAlertPattern(String severity) {
  if (severity == "high") {
    for (int i = 0; i < 6; i++) {
      digitalWrite(2, HIGH);
      delay(100);
      digitalWrite(2, LOW);
      delay(100);
    }
  } else if (severity == "medium") {
    for (int i = 0; i < 3; i++) {
      digitalWrite(2, HIGH);
      delay(300);
      digitalWrite(2, LOW);
      delay(300);
    }
  }
}

// ====================================
// DEVICE-LEVEL ALERTS
// ====================================
void checkBatteryAlerts() {
  if (batteryLevel < 10) {
    sendAlert("criticalBatteryLevel", "high", "CRITICAL BATTERY - " + String(batteryLevel) + "%", 1.0);
  } else if (batteryLevel < 20) {
    sendAlert("lowBatteryWarning", "medium", "LOW BATTERY - " + String(batteryLevel) + "%", 0.95);
  }

  if (batteryHealthPercentage < 70) {
    sendAlert("batteryDegradation", "medium", "BATTERY HEALTH - " + String(batteryHealthPercentage) + "%", 0.85);
  }
}

void updateBatteryHealth() {
  if (batteryLevel < 5 && lastBatteryLevel >= 5) {
    batteryHealthPercentage = max(0, batteryHealthPercentage - 1);
    prefs.putInt("batHealth", batteryHealthPercentage);
  }

  unsigned long timeDiff = millis() - lastBatteryUpdate;
  if (timeDiff > 3600000) {
    int batteryDiff = lastBatteryLevel - batteryLevel;
    batteryDrainRatePerHour = (float)batteryDiff / (timeDiff / 3600000.0);
    lastBatteryUpdate = millis();
    lastBatteryLevel = batteryLevel;
  }
}

void checkConnectivityAlerts() {
  if (totalDisconnects >= 5) {
    sendAlert("frequentDisconnects", "medium", "DISCONNECTS - " + String(totalDisconnects) + "x", 0.9);
  }

  if (lastCommandReceivedAt > 0 && (millis() - lastCommandReceivedAt) > 600000) {
    sendAlert("deviceUnresponsive", "high", "UNRESPONSIVE - " + String((millis() - lastCommandReceivedAt) / 60000) + " min", 0.95);
  }
}

void trackConnectivity() {
  unsigned long now = millis();
  if (now - disconnectTrackerLastCheck < 1000) return;
  disconnectTrackerLastCheck = now;

  bool currentWifiState = (WiFi.status() == WL_CONNECTED);
  if (wasWifiConnected && !currentWifiState) {
    totalDisconnects++;
    prefs.putInt("disconnects", totalDisconnects);
  }
  wasWifiConnected = currentWifiState;

  bool currentMqttState = mqttClient.connected();
  if (wasMqttConnected && !currentMqttState && isProvisioned) {
    totalDisconnects++;
    prefs.putInt("disconnects", totalDisconnects);
  }
  wasMqttConnected = currentMqttState;
}

bool isValidReading(float hr, float spo2, float temp) {
  return (hr > 0 && hr <= 300 && spo2 > 0 && spo2 <= 100 && temp >= 80 && temp <= 115);
}

void checkSystemAlerts() {
  if (!isValidReading(heartRate, oxygenSat, temperature)) {
    consecutiveInvalidReadings++;
    if (consecutiveInvalidReadings >= 3 && !sensorMalfunctionAlertSent) {
      sendAlert("sensorMalfunction", "high", "SENSOR FAIL - " + String(consecutiveInvalidReadings) + " invalid", 0.95);
      sensorMalfunctionAlertSent = true;
    }
  } else {
    consecutiveInvalidReadings = 0;
    sensorMalfunctionAlertSent = false;
    lastValidReading = millis();
  }

  if (millis() - lastValidReading > 300000) {
    sendAlert("communicationFailure", "high", "COMM FAIL - 5+ min", 1.0);
  }

  float hrVariation = abs(heartRate - heartRateHistory[0]);
  if (hrVariation > 50 && heartRate > 0) {
    sendAlert("dataQualityIssue", "low", "DATA QUALITY - HR spike " + String(hrVariation), 0.7);
  }
}

void runAlertEngine() {
  if (!isAssigned) return;

  checkBatteryAlerts();
  checkConnectivityAlerts();
  checkSystemAlerts();
}

void updateSensorHistory() {
  heartRateHistory[historyIndex] = heartRate;
  spo2History[historyIndex] = oxygenSat;
  tempHistory[historyIndex] = temperature;
  historyIndex = (historyIndex + 1) % 5;
}

// ====================================
// COMMAND HANDLERS
// ====================================
void sendCommandAck(String commandId, bool success, String msg) {
  if (!mqttClient.connected()) return;

  String topic = "hospital/devices/" + deviceId + "/ack";
  JsonDocument doc;
  doc["commandId"] = commandId;
  doc["timestamp"] = getISO8601Timestamp();
  doc["status"] = success ? "success" : "error";
  doc["message"] = msg;

  String payload;
  serializeJson(doc, payload);
  mqttClient.publish(topic.c_str(), payload.c_str());
}

void handlePingCommand(String commandId) {
  sendCommandAck(commandId, true, "Pong");
}

void handleCalibrationCommand(String commandId) {
  for (int i = 0; i < 3; i++) {
    digitalWrite(2, HIGH);
    delay(200);
    digitalWrite(2, LOW);
    delay(200);
  }
  delay(3000);

  String topic = "hospital/devices/" + deviceId + "/calibration_complete";
  JsonDocument doc;
  doc["timestamp"] = getISO8601Timestamp();
  doc["success"] = true;

  String payload;
  serializeJson(doc, payload);
  mqttClient.publish(topic.c_str(), payload.c_str());

  calibrationDue = false;
  sendCommandAck(commandId, true, "Calibration complete");
  digitalWrite(2, HIGH);
}

// ====================================
// SETUP
// ====================================
void setup() {
  Serial.begin(115200);

  // ✅ Enable verbose logging for TLS debugging
  esp_log_level_set("*", ESP_LOG_VERBOSE);

  Serial.println("\n🏥 ESP32 Hospital Watch v5.0.0 (Certificate Auth)");
  Serial.println("================================================================");
  Serial.println("✨ MQTT TLS 1.2 | HTTPS Provisioning | mTLS Certificate Auth");
#ifdef ARDUINO_ESP32_RELEASE
  Serial.printf("🔧 Arduino Core: %s\n", ARDUINO_ESP32_RELEASE);
#else
  Serial.println("🔧 Arduino Core: Version unknown (pre-2.0)");
#endif

  pinMode(2, OUTPUT);
  digitalWrite(2, LOW);

  // Configure mode selection GPIO pin
  pinMode(MODE_SELECT_PIN, INPUT_PULLUP);
  bool initialMode = digitalRead(MODE_SELECT_PIN) == HIGH;
  Serial.println("🔌 GPIO " + String(MODE_SELECT_PIN) + " configured for mode selection");
  Serial.println("   Current mode: " + String(initialMode ? "ECG" : "EEG") + " (HIGH=ECG, LOW=EEG)");

  Serial.println("📂 Loading CA certificate from SPIFFS...");
  if (!loadCACertificate()) {
    Serial.println("⚠️ WARNING: CA certificate not loaded - TLS will fail!");
    for (int i = 0; i < 10; i++) {
      digitalWrite(2, HIGH);
      delay(50);
      digitalWrite(2, LOW);
      delay(50);
    }
  }

  WiFi.mode(WIFI_STA);
  WiFi.begin();
  delay(100);

  macAddress = WiFi.macAddress();
  Serial.println("📱 MAC Address: " + macAddress);

  WiFi.disconnect();
  WiFi.mode(WIFI_OFF);

  prefs.begin("hospital", false);
  loadConfiguration();

  if (wifiSSID.length() > 0) {
    connectToWiFi();
    if (wifiConnected) {
      syncNTPTime();
      // ✅ v5.0: Check for certificates before connecting to MQTT
      if (isProvisioned && hasCertificates()) {
        setupMQTT();
      } else if (isProvisioned && !hasCertificates()) {
        Serial.println("⚠️  Device marked as provisioned but certificates missing!");
        Serial.println("⚠️  Clearing WiFi and resetting to captive portal...");
        mqttConfigured = false;  // ✅ v5.0.3: Reset flag when certs missing
        isProvisioned = false;

        // ✅ v5.0.1: Clear WiFi credentials to force captive portal
        wifiSSID = "";
        wifiPassword = "";
        serverIP = "";
        prefs.remove("ssid");
        prefs.remove("pass");
        prefs.remove("ip");
        prefs.remove("prov_code");
        saveConfiguration();

        Serial.println("⚠️  Restarting to captive portal...");
        delay(2000);
        ESP.restart();
      }
    }
  } else {
    startCaptivePortal();
  }

  wasWifiConnected = wifiConnected;
  wasMqttConnected = mqttClient.connected();
  lastBatteryUpdate = millis();
  lastValidReading = millis();

  // ✅ v5.1: Initialize physiological simulator
  simulator.begin();

  Serial.println("✅ v5.0.0 certificate-based auth initialized");
}

// ====================================
// MAIN LOOP
// ====================================
void loop() {
  if (!wifiConnected) {
    dnsServer.processNextRequest();
  }

  server.handleClient();

  if (wifiConnected && mqttClient.connected()) {
    mqttClient.loop();
  }

  if (wifiConnected && ntpSynced && millis() - lastNtpSync > 3600000) {
    syncNTPTime();
  }

  // ⚠️ TEMPORARILY REMOVED NTP REQUIREMENT FOR TESTING
  if (wifiConnected && !isProvisioned && !provisioningInProgress && millis() - lastProvisionAttempt > 15000) {
    lastProvisionAttempt = millis();
    attemptProvisioning();
  }

  if (wifiConnected && isProvisioned && mqttClient.connected() && millis() - lastHeartbeat > 30000) {
    sendMQTTHeartbeat();
    lastHeartbeat = millis();
  }

  if (wifiConnected && isProvisioned && isAssigned && millis() - lastVitals > 1000) {
    // ✅ v5.1: Update physiological state and get simulated vitals
    simulator.update();
    heartRate = simulator.getHeartRate();
    temperature = simulator.getTemperature();
    oxygenSat = simulator.getOxygenSaturation();
    respiratoryRate = simulator.getRespiratoryRate();
    quality = simulator.getSignalQuality();

    sendVitals();
    lastVitals = millis();
  }

  if (!wifiConnected && millis() - lastScan > 60000) {
    scanWiFiNetworks();
    lastScan = millis();
  }

  trackConnectivity();
  updateBatteryHealth();
  updateSensorHistory();

  if (wifiConnected && isProvisioned && millis() - lastAlertCheck > 2000) {
    runAlertEngine();
    lastAlertCheck = millis();
  }

  delay(100);
}

// ====================================
// CAPTIVE PORTAL
// ====================================
void startCaptivePortal() {
  Serial.println("🌐 Starting Captive Portal...");

  WiFi.disconnect();
  WiFi.mode(WIFI_OFF);
  delay(100);

  WiFi.mode(WIFI_AP);
  WiFi.softAPConfig(apIP, apIP, netMsk);
  WiFi.softAP(AP_SSID, AP_PASSWORD);

  delay(500);
  IPAddress IP = WiFi.softAPIP();
  Serial.println("📡 Captive Portal Network: " + String(AP_SSID));
  Serial.println("🌍 Access Point IP: " + IP.toString());

  dnsServer.setErrorReplyCode(DNSReplyCode::NoError);
  dnsServer.start(DNS_PORT, "*", apIP);

  scanWiFiNetworks();

  server.on("/", HTTP_GET, handleRoot);
  server.on("/scan", HTTP_GET, handleScan);
  server.on("/configure", HTTP_POST, handleConfigure);
  server.on("/status", HTTP_GET, handleStatus);
  server.on("/generate_204", HTTP_GET, handleRoot);
  server.on("/fwlink", HTTP_GET, handleRoot);
  server.onNotFound(handleRoot);

  server.begin();
  Serial.println("✅ Captive portal started");

  for(int i = 0; i < 5; i++) {
    digitalWrite(2, HIGH);
    delay(200);
    digitalWrite(2, LOW);
    delay(200);
  }
}

// ====================================
// WIFI SCANNING
// ====================================
void scanWiFiNetworks() {
  Serial.println("🔍 Scanning WiFi networks...");

  if (!wifiConnected) {
    WiFi.mode(WIFI_AP_STA);
  }

  networkCount = WiFi.scanNetworks();
  availableNetworks = "";

  if (networkCount > 0) {
    Serial.println("📶 Found " + String(networkCount) + " networks:");
    availableNetworks = "<option value=''>Select WiFi Network...</option>";

    for (int i = 0; i < min(networkCount, 20); i++) {
      String ssid = WiFi.SSID(i);
      int rssi = WiFi.RSSI(i);
      String security = (WiFi.encryptionType(i) == WIFI_AUTH_OPEN) ? "🔓" : "🔒";

      if (ssid.length() > 0 && !ssid.equals(AP_SSID)) {
        ssid.replace("\"", "&quot;");
        ssid.replace("<", "&lt;");
        ssid.replace(">", "&gt;");

        String signalStrength = String(rssi) + "dBm";
        availableNetworks += "<option value=\"" + ssid + "\">" + ssid + " " + security + " (" + signalStrength + ")</option>";

        Serial.println("  " + String(i+1) + ". " + ssid + " (" + signalStrength + ") " + security);
      }
    }
  } else {
    availableNetworks = "<option value=''>⚠️ No networks found</option>";
    Serial.println("❌ No networks found");
  }

  WiFi.scanDelete();

  if (!wifiConnected) {
    WiFi.mode(WIFI_AP);
  }
}

// ====================================
// WEB HANDLERS
// ====================================
void handleRoot() {
  String html = "<!DOCTYPE html><html><head>";
  html += "<title>Hospital Watch Setup</title>";
  html += "<meta name='viewport' content='width=device-width, initial-scale=1.0'>";
  html += "<style>";
  html += "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }";
  html += ".container { max-width: 500px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }";
  html += "h1 { color: #2c3e50; text-align: center; margin-bottom: 30px; }";
  html += ".device-info { background: #e8f4f8; padding: 15px; border-radius: 8px; margin-bottom: 25px; border-left: 4px solid #3498db; }";
  html += "label { display: block; margin-bottom: 5px; font-weight: 600; color: #34495e; }";
  html += "input, select { width: 100%; padding: 12px; margin-bottom: 15px; border: 2px solid #ddd; border-radius: 6px; font-size: 16px; box-sizing: border-box; }";
  html += "input:focus, select:focus { outline: none; border-color: #3498db; box-shadow: 0 0 5px rgba(52, 152, 219, 0.3); }";
  html += "button { width: 100%; padding: 15px; font-size: 16px; font-weight: 600; border: none; border-radius: 6px; cursor: pointer; margin: 10px 0; }";
  html += ".btn-primary { background: #3498db; color: white; }";
  html += ".btn-secondary { background: #95a5a6; color: white; }";
  html += ".btn-primary:hover { background: #2980b9; }";
  html += ".btn-secondary:hover { background: #7f8c8d; }";
  html += ".status { text-align: center; margin-top: 20px; padding: 10px; border-radius: 6px; }";
  html += ".status.info { background: #d4edda; color: #155724; }";
  html += ".form-section { margin-bottom: 25px; }";
  html += ".form-section h3 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }";
  html += "</style></head><body>";

  html += "<div class='container'>";
  html += "<h1>🏥 Hospital Watch Setup</h1>";

  html += "<div class='device-info'>";
  html += "<strong>📱 Device MAC:</strong> " + macAddress + "<br>";
  html += "<strong>🔧 Firmware:</strong> " + String(FIRMWARE_VERSION) + " (Certificate Auth)<br>";
  html += "<strong>📶 Networks Found:</strong> " + String(networkCount);
  html += "</div>";

  html += "<form action='/configure' method='post'>";
  html += "<div class='form-section'>";
  html += "<h3>📡 WiFi Configuration</h3>";
  html += "<label>WiFi Network:</label>";
  html += "<select name='wifi_ssid' required>" + availableNetworks + "</select>";
  html += "<label>WiFi Password:</label>";
  html += "<input type='password' name='wifi_pass' placeholder='Leave empty for open networks'>";
  html += "</div>";

  html += "<div class='form-section'>";
  html += "<h3>🏥 Hospital Server</h3>";
  html += "<label>Server IP Address:</label>";
  html += "<input type='text' name='server_ip' value='192.168.0.113' required pattern='^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}$' title='Enter valid IP address'>";
  html += "<label>HTTP Port:</label>";
  html += "<input type='text' name='http_port' value='8001' required>";
  html += "<label>MQTT Port:</label>";
  html += "<input type='text' name='mqtt_port' value='8883' required>";
  html += "</div>";

  // ✅ v5.0: Provisioning code instead of credentials
  html += "<div class='form-section'>";
  html += "<h3>🔐 Provisioning Code</h3>";
  html += "<label>One-Time Provisioning Code:</label>";
  html += "<input type='number' name='prov_code' placeholder='Enter 6-digit PIN' required pattern='[0-9]{6}' title='6-digit numeric PIN from IT staff' minlength='6' maxlength='6'>";
  html += "<p style='font-size:12px;color:#666;'>Get this code from hospital IT staff via backend API</p>";
  html += "</div>";

  html += "<button type='submit' class='btn-primary'>🚀 Configure & Connect</button>";
  html += "</form>";

  html += "<button onclick=\"window.location.href='/scan'\" class='btn-secondary'>🔄 Scan Networks Again</button>";

  html += "<div class='status info'>";
  html += "💡 <strong>Instructions:</strong><br>";
  html += "1. Select your WiFi network<br>";
  html += "2. Enter WiFi password<br>";
  html += "3. Verify hospital server details<br>";
  html += "4. Enter 6-digit PIN from IT staff<br>";
  html += "5. Click Configure & Connect";
  html += "</div>";
  html += "</div>";

  html += "<script>";
  html += "setTimeout(function() {";
  html += "if (!document.querySelector('form').checkValidity()) {";
  html += "window.location.reload();";
  html += "}";
  html += "}, 60000);";
  html += "</script>";
  html += "</body></html>";

  server.send(200, "text/html", html);
}

void handleScan() {
  Serial.println("🔄 Manual network scan requested");
  scanWiFiNetworks();
  server.sendHeader("Location", "/");
  server.send(302, "text/plain", "Scanning...");
}

void handleConfigure() {
  wifiSSID = server.arg("wifi_ssid");
  wifiPassword = server.arg("wifi_pass");
  serverIP = server.arg("server_ip");
  serverPort = server.arg("http_port");
  mqttServer = serverIP;
  mqttPort = server.arg("mqtt_port");
  // ✅ v5.0: Save provisioning code instead of credentials
  String provCode = server.arg("prov_code");

  if (wifiSSID.length() == 0 || serverIP.length() == 0 || provCode.length() != 6) {
    server.send(400, "text/html",
      "<html><body><h2>❌ Error</h2><p>WiFi SSID, Server IP, and valid 6-digit PIN are required!</p>"
      "<a href='/'>← Go Back</a></body></html>");
    return;
  }

  prefs.putString("prov_code", provCode);
  // ✅ v5.0.1: DON'T save WiFi credentials yet - only after successful provisioning
  // saveConfiguration();  // Removed - WiFi will be saved after certificate obtained

  Serial.println("📝 Configuration received (not saved yet):");
  Serial.println("   WiFi SSID: " + wifiSSID);
  Serial.println("   Server IP: " + serverIP);
  Serial.println("   HTTP Port: " + serverPort);
  Serial.println("   MQTT Port: " + mqttPort);
  Serial.println("   Provisioning Code: " + provCode);

  String html = "<!DOCTYPE html><html><head>";
  html += "<title>Connecting...</title>";
  html += "<meta name='viewport' content='width=device-width, initial-scale=1.0'>";
  html += "<style>";
  html += "body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }";
  html += ".spinner { border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; width: 40px; height: 40px; animation: spin 2s linear infinite; margin: 20px auto; }";
  html += "@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }";
  html += "</style></head><body>";
  html += "<h1>🔄 Connecting to WiFi...</h1>";
  html += "<div class='spinner'></div>";
  html += "<p>Please wait while the device connects and requests certificate from backend.</p>";
  html += "<p>Certificate-based MQTT TLS connection will be established automatically.</p>";
  html += "<p>This page will update automatically in <span id='countdown'>10</span> seconds.</p>";
  html += "<script>";
  html += "var count = 10;";
  html += "setInterval(function() {";
  html += "count--;";
  html += "document.getElementById('countdown').textContent = count;";
  html += "if (count <= 0) {";
  html += "window.location.href = '/status';";
  html += "}";
  html += "}, 1000);";
  html += "</script></body></html>";

  server.send(200, "text/html", html);

  delay(1000);
  connectToWiFi();
}

void handleStatus() {
  String status = "<!DOCTYPE html><html><head><title>Device Status</title>";
  status += "<meta name='viewport' content='width=device-width, initial-scale=1.0'>";
  status += "<style>body{font-family:Arial;padding:20px;} .status{padding:10px;margin:10px 0;border-radius:5px;}</style>";
  status += "</head><body><h1>🏥 Hospital Watch Status</h1>";

  status += "<div class='status' style='background:#e8f4f8;'>";
  status += "<strong>📱 Device ID:</strong> " + (deviceId.length() > 0 ? deviceId : "Not assigned") + "<br>";
  status += "<strong>📶 WiFi:</strong> ";
  status += (wifiConnected ? "Connected ✅" : "Disconnected ❌");
  status += "<br>";
  if (wifiConnected) {
    status += "<strong>🌐 IP Address:</strong> " + WiFi.localIP().toString() + "<br>";
    status += "<strong>📡 Signal:</strong> " + String(WiFi.RSSI()) + " dBm<br>";
  }
  status += "<strong>🕐 NTP Synced:</strong> ";
  status += (ntpSynced ? "Yes ✅" : "No ❌");
  status += "<br>";
  status += "<strong>🏥 Provisioned:</strong> ";
  status += (isProvisioned ? "Yes ✅" : "No ❌");
  status += "<br>";
  if (isProvisioned) {
    status += "<strong>🔐 Certificates:</strong> ";
    status += (hasCertificates() ? "Found ✅" : "Missing ❌");
    status += "<br>";
  }
  status += "<strong>👤 Patient:</strong> ";
  status += (isAssigned ? assignedPatientId + " ✅" : "Not assigned ❌");
  status += "<br>";
  status += "<strong>🔋 Battery:</strong> " + String(batteryLevel) + "%<br>";
  status += "<strong>🔐 Auth:</strong> Certificate-based mTLS ✅<br>";
  status += "<strong>📊 Firmware:</strong> " + String(FIRMWARE_VERSION);
  status += "</div>";

  status += "<p><a href='/'>← Back to Setup</a></p>";
  status += "<script>setTimeout(function(){location.reload();}, 10000);</script>";
  status += "</body></html>";

  server.send(200, "text/html", status);
}

// ====================================
// WIFI CONNECTION
// ====================================
void connectToWiFi() {
  if (wifiSSID.length() == 0) {
    Serial.println("❌ No WiFi SSID configured");
    return;
  }

  Serial.println("🔌 Connecting to WiFi: " + wifiSSID);

  dnsServer.stop();
  WiFi.mode(WIFI_STA);
  WiFi.begin(wifiSSID.c_str(), wifiPassword.c_str());

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
    digitalWrite(2, !digitalRead(2));
  }

  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    digitalWrite(2, HIGH);

    Serial.println("\n✅ WiFi Connected!");
    Serial.println("🌐 IP Address: " + WiFi.localIP().toString());
    Serial.println("📡 Signal Strength: " + String(WiFi.RSSI()) + " dBm");

    server.on("/", handleStatus);
    server.begin();

    syncNTPTime();

    // ✅ v5.0: Check for certificates before connecting
    if (isProvisioned && hasCertificates()) {
      setupMQTT();
    } else if (isProvisioned && !hasCertificates()) {
      Serial.println("⚠️  Certificates missing - resetting provisioning");
      mqttConfigured = false;  // ✅ v5.0.3: Reset flag when certs missing
      isProvisioned = false;
      saveConfiguration();
    }

  } else {
    wifiConnected = false;
    digitalWrite(2, LOW);
    Serial.println("\n❌ WiFi connection failed!");
    delay(2000);
    startCaptivePortal();
  }
}

// ====================================
// MQTT SETUP (v5.0.2 - Certificate Auth with Global Cert Fix)
// ====================================
void setupMQTT() {
  if (mqttServer.length() == 0) {
    mqttServer = serverIP;
  }

  // ✅ v5.0.3: Check if already configured - skip cert reload
  if (mqttConfigured) {
    Serial.println("🔐 MQTT already configured (skipping cert reload)");
    connectToMQTT();  // Just attempt reconnection
    return;
  }

  Serial.println("🔧 Configuring MQTT client...");
  Serial.println("📡 MQTT Server: " + mqttServer + ":" + mqttPort);

  // ====================================
  // ✅ v5.0.2: LOAD DEVICE CERTIFICATES INTO GLOBAL VARIABLES FIRST
  // This prevents .c_str() dangling pointer issues (errno 113)
  // ====================================
  if (!loadDeviceCertificate(deviceCertificate, devicePrivateKey)) {
    Serial.println("❌ Cannot setup MQTT - device certificates not found");
    Serial.println("⚠️  Device needs provisioning first");
    return;
  }

  Serial.println("🔐 Certificates loaded:");
  Serial.println("   CA: " + String(caCertificate.length()) + " bytes (global)");
  Serial.println("   Device cert: " + String(deviceCertificate.length()) + " bytes (global)");
  Serial.println("   Device key: " + String(devicePrivateKey.length()) + " bytes (global)");

  // ====================================
  // ✅ v5.0.2: SET ALL CERTIFICATES *BEFORE* setServer()
  // Using .c_str() from global String variables (no dangling pointers)
  // ====================================
  Serial.println("🔐 Setting TLS certificates...");

  // ✅ v5.0.2: Using setCertificate() with global String variables
  // These are stored in global scope, so .c_str() pointers remain valid
  wifiClient.setCACert(caCertificate.c_str());
  wifiClient.setCertificate(deviceCertificate.c_str());
  wifiClient.setPrivateKey(devicePrivateKey.c_str());

  Serial.println("   ✅ CA cert set (server validation ENABLED)");
  Serial.println("   ✅ Device cert set (client authentication)");
  Serial.println("   ✅ Private key set (mTLS complete)");

  // ====================================
  // NOW set server (AFTER certificates are configured)
  // ====================================
  mqttClient.setServer(mqttServer.c_str(), mqttPort.toInt());
  mqttClient.setCallback(onMqttMessage);
  mqttClient.setBufferSize(4096);
  mqttClient.setKeepAlive(15);

  mqttConfigured = true;  // ✅ v5.0.3: Mark as configured
  Serial.println("✅ MQTT client configured with certificates");
  connectToMQTT();
}

// ✅ v5.0.2: Certificate-based MQTT connection (SIMPLIFIED - certs already set in setupMQTT)
void connectToMQTT() {
  if (!wifiConnected || !isProvisioned) return;

  // ====================================
  // ✅ v5.0.2: Certificates already set in setupMQTT() as globals
  // No need to reload or re-set them here - just connect
  // ====================================

  Serial.println("\n🔍 === TLS HANDSHAKE DIAGNOSTICS ===");
  Serial.println("📊 Free heap BEFORE MQTT connect: " + String(ESP.getFreeHeap()) + " bytes");
  Serial.println("📊 Free PSRAM: " + String(ESP.getFreePsram()) + " bytes");
  Serial.println("🔐 Using global certificates (already set in wifiClient):");
  Serial.println("   CA: " + String(caCertificate.length()) + " bytes");
  Serial.println("   Device cert: " + String(deviceCertificate.length()) + " bytes");
  Serial.println("   Device key: " + String(devicePrivateKey.length()) + " bytes");

  // ====================================
  // ATTEMPT MQTT CONNECTION
  // ====================================
  String clientId = "HospitalWatch_" + deviceId;
  Serial.println("\n🔄 Connecting to MQTT with client certificate...");
  Serial.println("🔐 Device ID (from cert CN): " + deviceId);
  Serial.println("📡 MQTT Server: " + mqttServer + ":" + mqttPort);

  // ✅ DEBUG: Re-verify certificates right before connect
  Serial.println("\n🔍 PRE-CONNECTION CERTIFICATE CHECK:");
  Serial.println("   CA cert length: " + String(caCertificate.length()));
  Serial.println("   Device cert length: " + String(deviceCertificate.length()));
  Serial.println("   Device key length: " + String(devicePrivateKey.length()));
  Serial.println("   CA cert starts with: " + caCertificate.substring(0, 27));
  Serial.println("   Device cert starts with: " + deviceCertificate.substring(0, 27));
  Serial.println("   Device key starts with: " + devicePrivateKey.substring(0, 27));

  // ✅ v5.0: Connect WITHOUT username/password (certificate auth only)
  if (mqttClient.connect(clientId.c_str())) {
    Serial.println("✅ MQTT Connected with client certificate (mTLS)!");
    Serial.println("📊 Free heap AFTER MQTT connect: " + String(ESP.getFreeHeap()) + " bytes");

    String assignTopic = "hospital/devices/" + deviceId + "/assign";
    mqttClient.subscribe(assignTopic.c_str());
    Serial.println("📡 Subscribed to: " + assignTopic);

    String commandTopic = "hospital/devices/" + deviceId + "/command";
    mqttClient.subscribe(commandTopic.c_str());
    Serial.println("📡 Subscribed to: " + commandTopic);

  } else {
    Serial.println("❌ MQTT Connection failed, rc=" + String(mqttClient.state()));
    Serial.println("📊 Free heap AFTER failed connect: " + String(ESP.getFreeHeap()) + " bytes");
    Serial.println("\n💡 Troubleshooting:");
    Serial.println("   - Check heap memory (should be > 30KB before TLS)");
    Serial.println("   - Verify certificate valid (not expired)");
    Serial.println("   - Confirm Device ID matches cert CN");
    Serial.println("   - Ensure Mosquitto configured for mTLS");
  }

  Serial.println("🔍 === END DIAGNOSTICS ===\n");
}

void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  Serial.println("📨 MQTT Message: " + String(topic) + " -> " + message);

  if (String(topic).endsWith("/assign")) {
    JsonDocument doc;
    if (deserializeJson(doc, message) == DeserializationError::Ok) {
      if (doc["patientId"].is<String>()) {
        assignedPatientId = doc["patientId"].as<String>();
        isAssigned = true;
        saveConfiguration();
        Serial.println("👤 Assigned to patient: " + assignedPatientId);
      }
    }
  }

  if (String(topic).endsWith("/command")) {
    lastCommandReceivedAt = millis();

    JsonDocument doc;
    if (deserializeJson(doc, message) == DeserializationError::Ok) {
      String commandType = doc["command"].as<String>();
      String commandId = doc["commandId"].as<String>();

      if (commandType == "ping") {
        handlePingCommand(commandId);
      } else if (commandType == "calibrate") {
        handleCalibrationCommand(commandId);
      } else {
        sendCommandAck(commandId, false, "Unknown command: " + commandType);
      }
    }
  }
}

// ====================================
// HTTPS PROVISIONING (v5.0)
// ====================================
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

  // ✅ QUICK FIX: Remove colons from MAC to test ACL hypothesis
  String sanitizedMac = macAddress;
  sanitizedMac.replace(":", "");  // "A0:A3:B3:AA:13:B0" → "A0A3B3AA13B0"

  doc["deviceId"] = deviceId.length() > 0 ? deviceId : ("ESP32-WATCH-" + sanitizedMac);
  doc["macAddress"] = macAddress;
  doc["serialNumber"] = "SN-" + macAddress;

  String requestBody;
  serializeJson(doc, requestBody);

  Serial.println("📤 Sending provisioning request to: " + url);
  int httpCode = http.POST(requestBody);

  if (httpCode == 200) {
    String response = http.getString();
    JsonDocument responseDoc;

    if (deserializeJson(responseDoc, response) == DeserializationError::Ok) {
      deviceId = responseDoc["deviceId"].as<String>();
      String certPem = responseDoc["certificatePem"].as<String>();
      String keyPem = responseDoc["privateKeyPem"].as<String>();
      String caCertPem = responseDoc["caCertificatePem"].as<String>();

      Serial.println("📥 Received certificate from backend");

      if (saveCertificates(certPem, keyPem)) {
        // Save CA certificate
        File caFile = SPIFFS.open("/ca.crt", "w");
        if (caFile) {
          caFile.print(caCertPem);
          caFile.close();
          caCertificate = caCertPem;
          Serial.println("✅ CA certificate saved to SPIFFS");
        }

        mqttConfigured = false;  // ✅ v5.0.3: Reset flag to reload new certs
        isProvisioned = true;
        provisioningInProgress = false;
        prefs.remove("prov_code");  // Clear used code
        saveConfiguration();

        Serial.println("🎉 DEVICE PROVISIONED via HTTPS!");
        Serial.println("   📱 Device ID: " + deviceId);
        Serial.println("   🔐 Certificate saved to SPIFFS");
        Serial.println("   🔐 Private key saved to SPIFFS");

        // Flash LED to indicate success
        for(int i = 0; i < 10; i++) {
          digitalWrite(2, HIGH);
          delay(100);
          digitalWrite(2, LOW);
          delay(100);
        }
        digitalWrite(2, HIGH);

        // Connect to MQTT with certificate
        setupMQTT();
      } else {
        Serial.println("❌ Failed to save certificates");

        // ✅ v5.0.1: Clear WiFi credentials and restart to captive portal
        Serial.println("⚠️ Provisioning failed - clearing WiFi and restarting");
        wifiSSID = "";
        wifiPassword = "";
        serverIP = "";
        prefs.remove("prov_code");
        prefs.remove("ssid");
        prefs.remove("pass");
        prefs.remove("ip");

        provisioningInProgress = false;
        delay(2000);
        ESP.restart();  // Restart to captive portal
      }
    } else {
      Serial.println("❌ Failed to parse provisioning response");

      // ✅ v5.0.1: Clear WiFi credentials and restart
      Serial.println("⚠️ Invalid response - clearing WiFi and restarting");
      wifiSSID = "";
      wifiPassword = "";
      serverIP = "";
      prefs.remove("prov_code");
      prefs.remove("ssid");
      prefs.remove("pass");
      prefs.remove("ip");

      provisioningInProgress = false;
      delay(2000);
      ESP.restart();
    }
  } else {
    Serial.println("❌ Provisioning failed, HTTP code: " + String(httpCode));
    if (httpCode > 0) {
      Serial.println("Response: " + http.getString());
    }

    // ✅ v5.0.1: Clear provisioning code so user can try again with new PIN
    prefs.remove("prov_code");
    provisioningInProgress = false;

    // Device stays connected to WiFi so user can see error at /status
    // User can restart manually to go back to captive portal
  }

  http.end();
}

// ====================================
// MQTT HEARTBEAT
// ====================================
void sendMQTTHeartbeat() {
  if (!mqttClient.connected()) return;

  String topic = "hospital/devices/" + deviceId + "/heartbeat";

  JsonDocument doc;
  doc["deviceId"] = deviceId;
  doc["timestamp"] = getISO8601Timestamp();
  doc["batteryLevel"] = batteryLevel;
  doc["signalStrength"] = WiFi.RSSI();
  doc["firmwareVersion"] = FIRMWARE_VERSION;

  String payload;
  serializeJson(doc, payload);

  if (mqttClient.publish(topic.c_str(), payload.c_str())) {
    Serial.println("💓 MQTT Heartbeat sent");
  }
}

// ====================================
// VITALS (MQTT)
// ====================================
void sendVitals() {
  if (!mqttClient.connected() || !isAssigned) {
    if (!mqttClient.connected()) {
      connectToMQTT();
    }
    return;
  }

  String topic = "hospital/devices/" + deviceId + "/vitals";

  JsonDocument doc;
  doc["timestamp"] = getISO8601Timestamp();

  // Read GPIO pin to determine mode (HIGH = ECG, LOW = EEG)
  bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;
  doc["mode"] = isECGMode ? "ecg" : "eeg";

  doc["deviceId"] = deviceId;
  doc["patientId"] = assignedPatientId;
  doc["heartRate"] = (int)heartRate;

  float tempCelsius = (temperature - 32.0) * 5.0 / 9.0;
  doc["skinTemperature"] = tempCelsius;

  doc["oxygenSaturation"] = (int)oxygenSat;
  doc["signalQuality"] = quality / 100.0;
  doc["respiratoryRate"] = (int)respiratoryRate;
  doc["batteryLevel"] = batteryLevel;

  String payload;
  serializeJson(doc, payload);

  if (mqttClient.publish(topic.c_str(), payload.c_str())) {
    Serial.println("📊 Vitals: Mode=" + String(isECGMode ? "ECG" : "EEG") +
                   ", HR=" + String((int)heartRate) +
                   ", Temp=" + String(tempCelsius, 1) + "°C" +
                   ", SpO2=" + String(oxygenSat) + "%" +
                   ", RR=" + String(respiratoryRate));
  }
}

// ====================================
// ECG WAVEFORM STREAMING (v5.1)
// ====================================
void sendWaveformStream() {
  // This function is called when real-time ECG/EEG streaming is requested
  // Currently a placeholder - will be integrated with MQTT/WebSocket streaming

  // TODO: Add timing control (500 Hz = 2ms per sample, batch every 100ms)
  // TODO: Subscribe to backend streaming commands
  // TODO: Implement delta encoding for efficient transmission

  Serial.println("📈 Waveform streaming placeholder (v5.1)");
}

// ====================================
// CONFIGURATION
// ====================================
void loadConfiguration() {
  wifiSSID = prefs.getString("ssid", "");
  wifiPassword = prefs.getString("pass", "");
  serverIP = prefs.getString("ip", "");
  serverPort = prefs.getString("port", "8001");
  mqttServer = prefs.getString("mqttip", "");
  mqttPort = prefs.getString("mqttport", "8883");

  // ✅ v5.0: REMOVED MQTT credential loading (now using certificates)

  deviceId = prefs.getString("deviceId", "");
  serialNumber = prefs.getString("serial", "");
  assignedPatientId = prefs.getString("patientId", "");
  isProvisioned = prefs.getBool("provisioned", false);
  isAssigned = prefs.getBool("assigned", false);
  batteryLevel = prefs.getInt("battery", 100);

  batteryHealthPercentage = prefs.getInt("batHealth", 100);
  totalDisconnects = prefs.getInt("disconnects", 0);

  if (deviceId.length() > 0) {
    Serial.println("📖 Loaded: " + deviceId + " (" + serialNumber + ")");
    if (isAssigned) {
      Serial.println("👤 Assigned to patient: " + assignedPatientId);
    }
  }
}

void saveConfiguration() {
  prefs.putString("ssid", wifiSSID);
  prefs.putString("pass", wifiPassword);
  prefs.putString("ip", serverIP);
  prefs.putString("port", serverPort);
  prefs.putString("mqttip", mqttServer);
  prefs.putString("mqttport", mqttPort);

  // ✅ v5.0: REMOVED MQTT credential saving (now using certificates)

  prefs.putString("deviceId", deviceId);
  prefs.putString("serial", serialNumber);
  prefs.putString("patientId", assignedPatientId);
  prefs.putBool("provisioned", isProvisioned);
  prefs.putBool("assigned", isAssigned);
  prefs.putInt("battery", batteryLevel);

  prefs.putInt("batHealth", batteryHealthPercentage);
  prefs.putInt("disconnects", totalDisconnects);

  Serial.println("💾 Configuration saved");
}
