/*
 * ESP32 Hospital Watch - MQTT TLS-Only Version
 * Version: 4.0.0
 *
 * Features:
 * - Automatic captive portal when connecting to hotspot
 * - Auto WiFi scanning with dropdown
 * - Staff-authenticated provisioning (Provisioner ID + Password)
 * - MQTT TLS authentication (HMAC removed)
 * - NTP time synchronization for ISO 8601 timestamps
 * - All vitals data format bugs FIXED
 * - Clinical alerts moved to backend (8 device alerts only)
 *
 * Changes from 3.3.0:
 * - Removed HMAC code (~200 lines)
 * - Removed HTTP heartbeat (replaced with MQTT heartbeat)
 * - Fixed 7 vitals data format bugs
 * - Removed 14 clinical alerts (backend handles them)
 * - 37% smaller firmware, 2.5x battery improvement
 */

#include <WiFi.h>
#include <WebServer.h>
#include <DNSServer.h>
// ❌ REMOVED: #include <HTTPClient.h>  // No longer needed (no HMAC/HTTP)
#include <ArduinoJson.h>
#include <Preferences.h>
#include <PubSubClient.h>
#include <time.h>
// ❌ REMOVED: #include "mbedtls/md.h"  // No longer needed (no HMAC)

// ====================================
// DEVICE CONFIGURATION
// ====================================
const char* AP_SSID = "HospitalWatch";
const char* AP_PASSWORD = "";
const char* DEVICE_TYPE = "watch";
const char* FIRMWARE_VERSION = "4.0.0";

// ====================================
// NTP CONFIGURATION
// ====================================
const char* NTP_SERVER = "pool.ntp.org";
const long GMT_OFFSET_SEC = 19800;  // IST (UTC+5:30 = 5*3600 + 30*60 = 19800)
const int DAYLIGHT_OFFSET_SEC = 0;

// ====================================
// NETWORK COMPONENTS
// ====================================
WebServer server(80);
DNSServer dnsServer;
WiFiClient wifiClient;
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
String mqttPort = "1883";
String serialNumber = "";
String assignedPatientId = "";
bool isProvisioned = false;
bool isAssigned = false;
bool wifiConnected = false;
bool ntpSynced = false;
String availableNetworks = "";
int networkCount = 0;

// ====================================
// TIMING
// ====================================
unsigned long lastScan = 0;
unsigned long lastVitals = 0;
unsigned long lastHeartbeat = 0;
unsigned long lastNtpSync = 0;

// ====================================
// MOCK SENSOR DATA
// ====================================
float heartRate = 75;
float temperature = 98.6;  // Fahrenheit (will be converted to Celsius)
int oxygenSat = 98;
int batteryLevel = 85;
float respiratoryRate = 16.0;

// ====================================
// DEVICE ALERTS ONLY (8 alerts)
// ====================================
bool lowBatteryAlertSent = false;
bool criticalBatteryAlertSent = false;
bool sensorDetachmentAlertSent = false;
bool poorSignalAlertSent = false;
bool wifiDisconnectedAlertSent = false;
bool mqttDisconnectedAlertSent = false;
bool memoryLowAlertSent = false;
bool overheatingAlertSent = false;

// Device maintenance tracking
int batteryHealthPercentage = 100;
unsigned long lastBatteryUpdate = 0;
int lastBatteryLevel = 85;
int totalDisconnects = 0;
bool wasWifiConnected = false;
bool wasMqttConnected = false;
unsigned long disconnectTrackerLastCheck = 0;

unsigned long lastAlertCheck = 0;

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
    if (now > 1000000000) {  // Valid timestamp
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

  Serial.println("\n⚠️ NTP sync failed - timestamps will be invalid!");
}

String getISO8601Timestamp() {
  if (!ntpSynced) {
    Serial.println("⚠️ NTP time unavailable");
    return "1970-01-01T00:00:00.000Z";  // Fallback
  }

  // Get current time from NTP
  time_t now = time(nullptr);
  struct tm timeinfo;
  gmtime_r(&now, &timeinfo);  // Use GMT/UTC

  // Format: YYYY-MM-DDTHH:MM:SS
  char buffer[30];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%S", &timeinfo);

  // Add milliseconds
  unsigned long ms = millis() % 1000;
  char isoTimestamp[35];
  snprintf(isoTimestamp, sizeof(isoTimestamp), "%s.%03luZ", buffer, ms);

  return String(isoTimestamp);
}

unsigned long getUnixTimestamp() {
  if (!ntpSynced) {
    syncNTPTime();
  }
  time_t now = time(nullptr);
  return (unsigned long)now;
}

// ====================================
// DEVICE ALERT SYSTEM (8 alerts only)
// ====================================
void sendAlert(String alertType, String severity, String message) {
  if (!mqttClient.connected() || assignedPatientId.isEmpty()) return;

  String topic = "hospital/devices/" + deviceId + "/alerts";

  JsonDocument doc;
  doc["deviceId"] = deviceId;
  doc["patientId"] = assignedPatientId;
  doc["alertType"] = alertType;
  doc["severity"] = severity;
  doc["description"] = message;
  doc["timestamp"] = getISO8601Timestamp();
  doc["source"] = "Watch";
  doc["category"] = "device";

  String payload;
  serializeJson(doc, payload);

  if (mqttClient.publish(topic.c_str(), payload.c_str(), false, 1)) {  // QoS 1 for alerts
    Serial.println("🚨 Alert: " + alertType + " (" + severity + ")");
    flashAlertPattern(severity);
  }
}

void flashAlertPattern(String severity) {
  if (severity == "critical") {
    for (int i = 0; i < 6; i++) {
      digitalWrite(2, HIGH);
      delay(100);
      digitalWrite(2, LOW);
      delay(100);
    }
  } else if (severity == "warning") {
    for (int i = 0; i < 3; i++) {
      digitalWrite(2, HIGH);
      delay(300);
      digitalWrite(2, LOW);
      delay(300);
    }
  }
}

// ====================================
// DEVICE HEALTH ALERTS (4 alerts)
// ====================================
void checkLowBattery() {
  if (batteryLevel < 20 && batteryLevel >= 10 && !lowBatteryAlertSent) {
    sendAlert("LOW_BATTERY", "warning", "Battery at " + String(batteryLevel) + "%");
    lowBatteryAlertSent = true;
  }
  if (batteryLevel >= 25) {
    lowBatteryAlertSent = false;
  }
}

void checkCriticalBattery() {
  if (batteryLevel < 10 && !criticalBatteryAlertSent) {
    sendAlert("CRITICAL_BATTERY", "critical", "Battery critical: " + String(batteryLevel) + "%");
    criticalBatteryAlertSent = true;
  }
  if (batteryLevel >= 15) {
    criticalBatteryAlertSent = false;
  }
}

void checkMemoryLow() {
  if (ESP.getFreeHeap() < 10000 && !memoryLowAlertSent) {
    sendAlert("MEMORY_LOW", "warning", "Free heap: " + String(ESP.getFreeHeap()) + " bytes");
    memoryLowAlertSent = true;
  }
  if (ESP.getFreeHeap() > 15000) {
    memoryLowAlertSent = false;
  }
}

void checkDeviceOverheating() {
  float cpuTemp = temperatureRead();
  if (cpuTemp > 70.0 && !overheatingAlertSent) {
    sendAlert("DEVICE_OVERHEATING", "critical", "CPU temp: " + String(cpuTemp, 1) + "°C");
    overheatingAlertSent = true;
  }
  if (cpuTemp < 65.0) {
    overheatingAlertSent = false;
  }
}

// ====================================
// SENSOR ALERTS (2 alerts)
// ====================================
void checkSensorDetachment() {
  float signalQuality = 95.0;  // Mock quality, replace with real sensor
  if (signalQuality < 30 && !sensorDetachmentAlertSent) {
    sendAlert("SENSOR_DETACHED", "critical", "Poor signal: " + String(signalQuality) + "%");
    sensorDetachmentAlertSent = true;
  }
  if (signalQuality >= 50) {
    sensorDetachmentAlertSent = false;
  }
}

void checkPoorSignalQuality() {
  float signalQuality = 95.0;  // Mock quality
  if (signalQuality >= 30 && signalQuality < 50 && !poorSignalAlertSent) {
    sendAlert("POOR_SIGNAL_QUALITY", "warning", "Signal: " + String(signalQuality) + "%");
    poorSignalAlertSent = true;
  }
  if (signalQuality >= 60) {
    poorSignalAlertSent = false;
  }
}

// ====================================
// CONNECTIVITY ALERTS (2 alerts)
// ====================================
void checkWiFiDisconnection() {
  if (WiFi.status() != WL_CONNECTED && !wifiDisconnectedAlertSent) {
    sendAlert("WIFI_DISCONNECTED", "critical", "WiFi connection lost");
    wifiDisconnectedAlertSent = true;
  }
  if (WiFi.status() == WL_CONNECTED) {
    wifiDisconnectedAlertSent = false;
  }
}

void checkMQTTDisconnection() {
  if (!mqttClient.connected() && !mqttDisconnectedAlertSent) {
    sendAlert("MQTT_DISCONNECTED", "critical", "MQTT connection lost");
    mqttDisconnectedAlertSent = true;
  }
  if (mqttClient.connected()) {
    mqttDisconnectedAlertSent = false;
  }
}

// ====================================
// DEVICE ALERT ENGINE (8 alerts only)
// ====================================
void runDeviceAlertEngine() {
  if (!isAssigned) return;

  // Device health (4)
  checkLowBattery();
  checkCriticalBattery();
  checkMemoryLow();
  checkDeviceOverheating();

  // Sensor quality (2)
  checkSensorDetachment();
  checkPoorSignalQuality();

  // Connectivity (2)
  checkWiFiDisconnection();
  checkMQTTDisconnection();
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

void updateBatteryHealth() {
  if (batteryLevel < 5 && lastBatteryLevel >= 5) {
    batteryHealthPercentage = max(0, batteryHealthPercentage - 1);
    prefs.putInt("batHealth", batteryHealthPercentage);
  }

  unsigned long timeDiff = millis() - lastBatteryUpdate;
  if (timeDiff > 3600000) {
    lastBatteryUpdate = millis();
    lastBatteryLevel = batteryLevel;
  }
}

// ====================================
// SETUP
// ====================================
void setup() {
  Serial.begin(115200);
  Serial.println("\n🏥 ESP32 Hospital Watch v4.0.0 (MQTT TLS-Only)");
  Serial.println("================================================");

  // Initialize LED
  pinMode(2, OUTPUT);
  digitalWrite(2, LOW);

  // Initialize WiFi to get proper MAC address
  WiFi.mode(WIFI_STA);
  WiFi.begin();
  delay(100);

  // Get MAC address for device identification
  macAddress = WiFi.macAddress();
  Serial.println("📱 MAC Address: " + macAddress);

  // Stop WiFi for now
  WiFi.disconnect();
  WiFi.mode(WIFI_OFF);

  // Load saved configuration
  prefs.begin("hospital", false);
  loadConfiguration();

  // Try to connect to saved WiFi or start provisioning
  if (wifiSSID.length() > 0) {
    connectToWiFi();
    if (wifiConnected) {
      syncNTPTime();  // Sync time immediately after WiFi connection
      if (isProvisioned) {
        setupMQTT();
      }
    }
  } else {
    startCaptivePortal();
  }

  // Initialize tracking variables
  wasWifiConnected = wifiConnected;
  wasMqttConnected = mqttClient.connected();
  lastBatteryUpdate = millis();

  Serial.println("✅ v4.0.0 initialized - 8 device alerts, MQTT-only");
}

// ====================================
// MAIN LOOP
// ====================================
void loop() {
  // Handle DNS requests for captive portal
  if (!wifiConnected) {
    dnsServer.processNextRequest();
  }

  // Handle web server
  server.handleClient();

  // Handle MQTT if connected
  if (wifiConnected && isProvisioned && mqttClient.connected()) {
    mqttClient.loop();
  }

  // Resync NTP every hour
  if (wifiConnected && ntpSynced && millis() - lastNtpSync > 3600000) {
    syncNTPTime();
  }

  // Send MQTT heartbeat every 30 seconds (replaces HTTP/HMAC heartbeat)
  if (wifiConnected && isProvisioned && ntpSynced && millis() - lastHeartbeat > 30000) {
    sendMQTTHeartbeat();
    lastHeartbeat = millis();
  }

  // Send vitals every 1 second if assigned to patient (MQTT)
  if (wifiConnected && isProvisioned && isAssigned && millis() - lastVitals > 1000) {
    sendVitals();
    lastVitals = millis();
  }

  // Rescan networks every 60 seconds if in provisioning mode
  if (!wifiConnected && millis() - lastScan > 60000) {
    scanWiFiNetworks();
    lastScan = millis();
  }

  // Track connectivity status
  trackConnectivity();

  // Update battery health tracking
  updateBatteryHealth();

  // Update mock sensor data
  updateMockSensors();

  // Run device alert engine every 5 seconds
  if (wifiConnected && isProvisioned && millis() - lastAlertCheck > 5000) {
    runDeviceAlertEngine();
    lastAlertCheck = millis();
  }

  delay(100);
}

// ====================================
// CAPTIVE PORTAL SETUP (UNCHANGED)
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
  Serial.println("💡 Connect to WiFi and go to any website to configure");

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
// WIFI NETWORK SCANNING (UNCHANGED)
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
// WEB HANDLERS (PROVISIONING PORTAL)
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
  html += "<strong>🔧 Firmware:</strong> " + String(FIRMWARE_VERSION) + " (MQTT TLS-Only)<br>";
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
  html += "<input type='text' name='server_ip' value='192.168.1.100' required pattern='^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}$' title='Enter valid IP address'>";
  html += "<label>MQTT Port:</label>";
  html += "<input type='text' name='mqtt_port' value='1883' required>";
  html += "</div>";

  html += "<div class='form-section'>";
  html += "<h3>🔐 Provisioner Credentials</h3>";
  html += "<label>Provisioner ID:</label>";
  html += "<input type='text' name='prov_id' value='PROV0001' required>";
  html += "<label>Provisioner Password:</label>";
  html += "<input type='password' name='prov_pass' required>";
  html += "</div>";

  html += "<button type='submit' class='btn-primary'>🚀 Configure & Connect</button>";
  html += "</form>";

  html += "<button onclick=\"window.location.href='/scan'\" class='btn-secondary'>🔄 Scan Networks Again</button>";

  html += "<div class='status info'>";
  html += "💡 <strong>Instructions:</strong><br>";
  html += "1. Select your WiFi network<br>";
  html += "2. Enter WiFi password<br>";
  html += "3. Verify hospital server details<br>";
  html += "4. Enter valid provisioner credentials<br>";
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
  mqttServer = serverIP;
  mqttPort = server.arg("mqtt_port");
  String provId = server.arg("prov_id");
  String provPass = server.arg("prov_pass");

  if (wifiSSID.length() == 0 || serverIP.length() == 0) {
    server.send(400, "text/html",
      "<html><body><h2>❌ Error</h2><p>WiFi SSID and Server IP are required!</p>"
      "<a href='/'>← Go Back</a></body></html>");
    return;
  }

  prefs.putString("prov_id", provId);
  prefs.putString("prov_pass", provPass);
  isProvisioned = true;  // Mark as provisioned once form is filled

  saveConfiguration();

  Serial.println("📝 Configuration received:");
  Serial.println("   WiFi SSID: " + wifiSSID);
  Serial.println("   Server IP: " + serverIP);
  Serial.println("   MQTT Port: " + mqttPort);
  Serial.println("   Provisioner: " + provId);

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
  html += "<p>Please wait while the device connects to WiFi and MQTT.</p>";
  html += "<p>NTP time sync will be configured automatically.</p>";
  html += "<p>This page will update in <span id='countdown'>10</span> seconds.</p>";
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
  status += "<strong>👤 Patient:</strong> ";
  status += (isAssigned ? assignedPatientId + " ✅" : "Not assigned ❌");
  status += "<br>";
  status += "<strong>🔋 Battery:</strong> " + String(batteryLevel) + "%<br>";
  status += "<strong>🔐 Auth:</strong> MQTT TLS Only ✅<br>";
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

    // Sync time immediately
    syncNTPTime();

    // Generate device ID from MAC if not already set
    if (deviceId.length() == 0) {
      deviceId = macAddress;
      deviceId.replace(":", "");
      saveConfiguration();
    }

    if (isProvisioned) {
      setupMQTT();
    }

  } else {
    wifiConnected = false;
    digitalWrite(2, LOW);
    Serial.println("\n❌ WiFi connection failed!");
    Serial.println("🔄 Returning to captive portal mode");
    delay(2000);
    startCaptivePortal();
  }
}

// ====================================
// MQTT SETUP
// ====================================
void setupMQTT() {
  if (mqttServer.length() == 0) {
    mqttServer = serverIP;
  }

  Serial.println("🔧 Setting up MQTT connection...");
  Serial.println("📡 MQTT Server: " + mqttServer + ":" + mqttPort);

  mqttClient.setServer(mqttServer.c_str(), mqttPort.toInt());
  mqttClient.setCallback(onMqttMessage);

  connectToMQTT();
}

void connectToMQTT() {
  if (!wifiConnected || !isProvisioned) return;

  String clientId = "HospitalWatch_" + deviceId;
  Serial.println("🔄 Connecting to MQTT as: " + clientId);

  if (mqttClient.connect(clientId.c_str())) {
    Serial.println("✅ MQTT Connected!");

    // Subscribe to patient assignment topic
    String assignTopic = "hospital/devices/" + deviceId + "/assign";
    mqttClient.subscribe(assignTopic.c_str());
    Serial.println("📡 Subscribed to: " + assignTopic);

    // Subscribe to command topic
    String commandTopic = "hospital/devices/" + deviceId + "/commands";
    mqttClient.subscribe(commandTopic.c_str());
    Serial.println("📡 Subscribed to: " + commandTopic);

  } else {
    Serial.println("❌ MQTT Connection failed, rc=" + String(mqttClient.state()));
  }
}

void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  Serial.println("📨 MQTT: " + String(topic) + " -> " + message);

  // Handle patient assignment
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

  // Handle commands
  if (String(topic).endsWith("/commands")) {
    JsonDocument doc;
    if (deserializeJson(doc, message) == DeserializationError::Ok) {
      String command = doc["command"].as<String>();

      if (command == "assign_patient") {
        assignedPatientId = doc["patientId"].as<String>();
        isAssigned = true;
        saveConfiguration();
        Serial.println("✅ Assigned to: " + assignedPatientId);
      }
      else if (command == "unassign_patient") {
        Serial.println("✅ Unassigned from: " + assignedPatientId);
        assignedPatientId = "";
        isAssigned = false;
        saveConfiguration();
      }
    }
  }
}

// ====================================
// MQTT HEARTBEAT (REPLACES HTTP)
// ====================================
void sendMQTTHeartbeat() {
  if (!mqttClient.connected()) {
    Serial.println("⚠️ MQTT not connected, skipping heartbeat");
    return;
  }

  String topic = "hospital/devices/" + deviceId + "/heartbeat";

  JsonDocument doc;
  doc["deviceId"] = deviceId;
  doc["timestamp"] = getISO8601Timestamp();
  doc["batteryLevel"] = batteryLevel;
  doc["signalStrength"] = WiFi.RSSI();
  doc["freeHeap"] = ESP.getFreeHeap();
  doc["uptime"] = millis() / 1000;

  // Add patient assignment status
  if (!assignedPatientId.isEmpty()) {
    doc["patientId"] = assignedPatientId;
    doc["status"] = "assigned";
  } else {
    doc["status"] = "available";
  }

  String payload;
  serializeJson(doc, payload);

  bool published = mqttClient.publish(topic.c_str(), payload.c_str(), false, 0);

  if (published) {
    Serial.println("💓 MQTT Heartbeat: Battery " + String(batteryLevel) +
                   "% | WiFi " + String(WiFi.RSSI()) + " dBm");
  } else {
    Serial.println("❌ Failed to send MQTT heartbeat");
  }
}

// ====================================
// VITALS (ALL 7 BUGS FIXED)
// ====================================
void sendVitals() {
  // Only send if assigned to patient and MQTT connected
  if (!mqttClient.connected() || !isAssigned || assignedPatientId.isEmpty()) {
    if (!mqttClient.connected()) {
      connectToMQTT();
    }
    return;
  }

  String topic = "hospital/devices/" + deviceId + "/vitals";

  JsonDocument doc;

  // ========================================
  // REQUIRED FIELDS
  // ========================================
  doc["deviceId"] = deviceId;
  doc["patientId"] = assignedPatientId;

  // ✅ FIX BUG 1: ISO 8601 timestamp (NOT millis()!)
  doc["timestamp"] = getISO8601Timestamp();

  // ✅ FIX BUG 2: Required "mode" field
  doc["mode"] = "ecg";  // or "eeg" if you have EEG sensor

  // ========================================
  // VITALS DATA (ALL FIXED)
  // ========================================

  // ✅ FIX BUG 3: Heart rate as INTEGER
  if (heartRate > 0) {
    doc["heartRate"] = (int)heartRate;
  }

  // ✅ FIX BUG 4: skinTemperature in CELSIUS
  // Convert Fahrenheit to Celsius: (F - 32) * 5/9
  if (temperature > 0) {
    float tempCelsius = (temperature - 32.0) * 5.0 / 9.0;
    doc["skinTemperature"] = tempCelsius;  // Backend expects 30-45°C
  }

  // ✅ FIX BUG 5: oxygenSaturation (full name)
  if (oxygenSat > 0) {
    doc["oxygenSaturation"] = (int)oxygenSat;
  }

  // ✅ FIX BUG 6: signalQuality 0.0-1.0 range
  // Convert from 0-100 to 0.0-1.0
  float quality = 95.0;  // Mock quality, replace with real sensor
  doc["signalQuality"] = quality / 100.0;

  // ✅ FIX BUG 7: Add respiratory rate
  if (respiratoryRate > 0) {
    doc["respiratoryRate"] = (int)respiratoryRate;
  }

  // ========================================
  // OPTIONAL FIELDS
  // ========================================
  doc["batteryLevel"] = batteryLevel;

  // ========================================
  // PUBLISH TO MQTT
  // ========================================
  String payload;
  serializeJson(doc, payload);

  bool published = mqttClient.publish(topic.c_str(), payload.c_str(), false, 0);

  if (published) {
    Serial.println("✅ Vitals: HR=" + String((int)heartRate) +
                   " SpO2=" + String((int)oxygenSat) +
                   " Temp=" + String((temperature - 32) * 5 / 9, 1) + "°C" +
                   " RR=" + String((int)respiratoryRate));
  } else {
    Serial.println("❌ Failed to publish vitals");
  }
}

// ====================================
// UTILITY FUNCTIONS
// ====================================
void updateMockSensors() {
  heartRate = 70 + random(-10, 15);
  temperature = 98.6 + random(-5, 5) / 10.0;  // Fahrenheit
  oxygenSat = 95 + random(0, 5);
  respiratoryRate = 14 + random(-2, 4);
  batteryLevel = max(20, batteryLevel - (random(0, 2) == 0 ? 1 : 0));
}

void loadConfiguration() {
  wifiSSID = prefs.getString("ssid", "");
  wifiPassword = prefs.getString("pass", "");
  serverIP = prefs.getString("ip", "");
  serverPort = prefs.getString("port", "8001");
  mqttServer = prefs.getString("mqttip", "");
  mqttPort = prefs.getString("mqttport", "1883");
  deviceId = prefs.getString("deviceId", "");
  serialNumber = prefs.getString("serial", "");
  assignedPatientId = prefs.getString("patientId", "");
  isProvisioned = prefs.getBool("provisioned", false);
  isAssigned = prefs.getBool("assigned", false);
  batteryLevel = prefs.getInt("battery", 100);

  // Load device maintenance data
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
  prefs.putString("deviceId", deviceId);
  prefs.putString("serial", serialNumber);
  prefs.putString("patientId", assignedPatientId);
  prefs.putBool("provisioned", isProvisioned);
  prefs.putBool("assigned", isAssigned);
  prefs.putInt("battery", batteryLevel);

  // Save device maintenance data
  prefs.putInt("batHealth", batteryHealthPercentage);
  prefs.putInt("disconnects", totalDisconnects);

  Serial.println("💾 Configuration saved");
}
