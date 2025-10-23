/*
 * ESP32 Hospital Watch - HMAC Authentication Version
 * Version: 3.2.0
 *
 * Features:
 * - Automatic captive portal when connecting to hotspot
 * - Auto WiFi scanning with dropdown
 * - Staff-authenticated provisioning (Provisioner ID + Password)
 * - HMAC-SHA256 authentication for runtime requests
 * - NTP time synchronization for timestamp-based auth
 * - MQTT support for vitals and alerts
 * - Replay attack protection (5-minute timestamp window)
 * - MAC address-based device identity
 *
 * IMPORTANT: Change FACTORY_SECRET before production deployment!
 */

#include <WiFi.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <PubSubClient.h>
#include <time.h>
#include "mbedtls/md.h"  // For HMAC-SHA256

// ====================================
// DEVICE CONFIGURATION
// ====================================
const char* AP_SSID = "HospitalWatch";
const char* AP_PASSWORD = "";
const char* DEVICE_TYPE = "watch";
const char* FIRMWARE_VERSION = "3.2.0";

// ====================================
// SECURITY: HMAC Factory Secret
// ====================================
// THIS MUST MATCH THE BACKEND ESP32_FACTORY_SECRET
// In production, this should be set during firmware compilation
const char* FACTORY_SECRET = "CHANGE_THIS_IN_PRODUCTION_ESP32_HMAC_SECRET_KEY_MIN_64_CHARS_REQUIRED";

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
unsigned long lastProvisionAttempt = 0;
unsigned long lastNtpSync = 0;

// ====================================
// MOCK SENSOR DATA
// ====================================
float heartRate = 75;
float temperature = 98.6;
int oxygenSat = 98;
int batteryLevel = 85;

// ====================================
// HMAC-SHA256 COMPUTATION
// ====================================
String computeHMAC(String message) {
  byte hmacResult[32];

  mbedtls_md_context_t ctx;
  mbedtls_md_type_t md_type = MBEDTLS_MD_SHA256;

  mbedtls_md_init(&ctx);
  mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(md_type), 1);
  mbedtls_md_hmac_starts(&ctx, (const unsigned char*)FACTORY_SECRET, strlen(FACTORY_SECRET));
  mbedtls_md_hmac_update(&ctx, (const unsigned char*)message.c_str(), message.length());
  mbedtls_md_hmac_finish(&ctx, hmacResult);
  mbedtls_md_free(&ctx);

  // Convert to hex string
  String hmacHex = "";
  for(int i = 0; i < 32; i++){
    char str[3];
    sprintf(str, "%02x", (int)hmacResult[i]);
    hmacHex += str;
  }

  return hmacHex;
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

  Serial.println("\n⚠️ NTP sync failed - HMAC authentication will not work!");
}

unsigned long getUnixTimestamp() {
  if (!ntpSynced) {
    Serial.println("⚠️ Time not synced! Attempting sync...");
    syncNTPTime();
  }

  time_t now = time(nullptr);
  return (unsigned long)now;
}

// ====================================
// AUTHENTICATION HELPERS
// ====================================
void addHMACHeaders(HTTPClient &http, String endpoint) {
  if (!ntpSynced) {
    Serial.println("⚠️ Cannot add HMAC headers - time not synced");
    return;
  }

  // Get current time and format as ISO 8601 (UTC)
  time_t now = time(nullptr);
  struct tm timeinfo;
  gmtime_r(&now, &timeinfo);  // Use GMT/UTC

  char iso_timestamp[25];
  strftime(iso_timestamp, sizeof(iso_timestamp), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
  String timestamp = String(iso_timestamp);

  String message = macAddress + timestamp + endpoint;
  String signature = computeHMAC(message);

  http.addHeader("X-Device-MAC", macAddress);
  http.addHeader("X-Device-Signature", signature);
  http.addHeader("X-Timestamp", timestamp);

  Serial.println("🔐 HMAC Headers:");
  Serial.println("   MAC: " + macAddress);
  Serial.println("   Timestamp: " + timestamp);
  Serial.println("   Signature: " + signature.substring(0, 16) + "...");
}

// ====================================
// SETUP
// ====================================
void setup() {
  Serial.begin(115200);
  Serial.println("\n🏥 ESP32 Hospital Watch v3.2.0 (HMAC Auth)");
  Serial.println("==========================================");

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

  // Auto-provision if WiFi connected but not provisioned
  if (wifiConnected && !isProvisioned && ntpSynced && millis() - lastProvisionAttempt > 15000) {
    attemptProvisioning();
    lastProvisionAttempt = millis();
  }

  // Send heartbeat every 30 seconds (HMAC authenticated)
  if (wifiConnected && isProvisioned && ntpSynced && millis() - lastHeartbeat > 30000) {
    sendHeartbeat();
    lastHeartbeat = millis();
  }

  // Send vitals every 5 seconds if assigned to patient (MQTT)
  if (wifiConnected && isProvisioned && isAssigned && millis() - lastVitals > 5000) {
    sendVitals();
    lastVitals = millis();
  }

  // Rescan networks every 60 seconds if in provisioning mode
  if (!wifiConnected && millis() - lastScan > 60000) {
    scanWiFiNetworks();
    lastScan = millis();
  }

  // Update mock sensor data
  updateMockSensors();

  delay(100);
}

// ====================================
// CAPTIVE PORTAL SETUP
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
// WIFI NETWORK SCANNING
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
  html += "<strong>🔧 Firmware:</strong> " + String(FIRMWARE_VERSION) + " (HMAC Auth)<br>";
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
  html += "<input type='text' name='mqtt_port' value='1883' required>";
  html += "</div>";

  html += "<div class='form-section'>";
  html += "<h3>🔐 Provisioner Credentials</h3>";
  html += "<label>Provisioner ID:</label>";
  html += "<input type='text' name='prov_id' value='TEC0001' required>";
  html += "<label>Provisioner Password:</label>";
  html += "<input type='password' name='prov_pass' value='tech123' required>";
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
  serverPort = server.arg("http_port");
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

  saveConfiguration();

  Serial.println("📝 Configuration received:");
  Serial.println("   WiFi SSID: " + wifiSSID);
  Serial.println("   Server IP: " + serverIP);
  Serial.println("   HTTP Port: " + serverPort);
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
  html += "<p>Please wait while the device connects and provisions with the hospital backend.</p>";
  html += "<p>NTP time sync and HMAC authentication will be configured automatically.</p>";
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
  status += "<strong>📋 Serial:</strong> " + (serialNumber.length() > 0 ? serialNumber : "Not assigned") + "<br>";
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
  status += "<strong>🔐 Auth:</strong> HMAC-SHA256 ✅<br>";
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

    String assignTopic = "hospital/devices/" + deviceId + "/assign";
    mqttClient.subscribe(assignTopic.c_str());
    Serial.println("📡 Subscribed to: " + assignTopic);

  } else {
    Serial.println("❌ MQTT Connection failed, rc=" + String(mqttClient.state()));
  }
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
}

// ====================================
// PROVISIONING (Staff Auth)
// ====================================
void attemptProvisioning() {
  String provId = prefs.getString("prov_id", "");
  String provPass = prefs.getString("prov_pass", "");

  if (provId.length() == 0 || serverIP.length() == 0) {
    Serial.println("❌ Missing provisioning credentials");
    return;
  }

  Serial.println("🔄 Attempting device provisioning...");

  HTTPClient http;
  String url = "http://" + serverIP + ":" + serverPort + "/api/v1/esp32/provision";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(10000);

  JsonDocument doc;
  doc["macaddress"] = macAddress;  // lowercase for backend transformation
  doc["devicetype"] = DEVICE_TYPE;
  doc["firmwareversion"] = FIRMWARE_VERSION;
  doc["provisionerid"] = provId;
  doc["provisionerpassword"] = provPass;

  String payload;
  serializeJson(doc, payload);

  Serial.println("📤 POST " + url);
  int httpCode = http.POST(payload);

  if (httpCode == 200) {
    String response = http.getString();
    Serial.println("✅ Provision Response: " + response);

    JsonDocument responseDoc;
    if (deserializeJson(responseDoc, response) == DeserializationError::Ok) {
      if (responseDoc["success"]) {
        deviceId = responseDoc["deviceId"].as<String>();
        serialNumber = responseDoc["serialNumber"].as<String>();
        isProvisioned = true;
        saveConfiguration();

        Serial.println("🎉 DEVICE PROVISIONED!");
        Serial.println("   📱 Device ID: " + deviceId);
        Serial.println("   📋 Serial: " + serialNumber);

        setupMQTT();
        registerDevice();  // Register with HMAC auth

        for(int i = 0; i < 10; i++) {
          digitalWrite(2, HIGH);
          delay(100);
          digitalWrite(2, LOW);
          delay(100);
        }
        digitalWrite(2, HIGH);
      } else {
        Serial.println("❌ Provisioning failed: " + responseDoc["message"].as<String>());
      }
    }
  } else {
    Serial.println("❌ HTTP Error: " + String(httpCode));
    if (httpCode == 403) {
      Serial.println("❌ Invalid provisioner credentials!");
    }
  }

  http.end();
}

// ====================================
// REGISTER DEVICE (HMAC Auth)
// ====================================
void registerDevice() {
  if (!ntpSynced) {
    Serial.println("⚠️ Skipping registration - time not synced");
    return;
  }

  Serial.println("🔄 Registering device with HMAC authentication...");

  HTTPClient http;
  String url = "http://" + serverIP + ":" + serverPort + "/api/v1/esp32/register";
  String endpoint = "/api/v1/esp32/register";

  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  addHMACHeaders(http, endpoint);  // Add HMAC authentication

  JsonDocument doc;
  doc["macaddress"] = macAddress;
  doc["firmwareversion"] = FIRMWARE_VERSION;
  doc["batterylevel"] = batteryLevel;

  String payload;
  serializeJson(doc, payload);

  int httpCode = http.POST(payload);

  if (httpCode == 200) {
    Serial.println("✅ Device registered successfully");
  } else {
    Serial.println("❌ Registration failed: " + String(httpCode));
    String response = http.getString();
    Serial.println("   Response: " + response);
  }

  http.end();
}

// ====================================
// HEARTBEAT (HMAC Auth)
// ====================================
void sendHeartbeat() {
  if (!ntpSynced) {
    Serial.println("⚠️ Skipping heartbeat - time not synced");
    return;
  }

  HTTPClient http;
  String url = "http://" + serverIP + ":" + serverPort + "/api/v1/esp32/" + deviceId + "/heartbeat";
  String endpoint = "/api/v1/esp32/" + deviceId + "/heartbeat";

  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  addHMACHeaders(http, endpoint);  // Add HMAC authentication

  JsonDocument doc;
  doc["batterylevel"] = batteryLevel;
  doc["signalstrength"] = WiFi.RSSI();

  String payload;
  serializeJson(doc, payload);

  int httpCode = http.POST(payload);

  if (httpCode == 200) {
    Serial.println("💓 Heartbeat sent (HMAC authenticated)");
  } else {
    Serial.println("❌ Heartbeat failed: " + String(httpCode));
    String response = http.getString();
    Serial.println("   Response: " + response);
  }

  http.end();
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
  doc["deviceId"] = deviceId;
  doc["patientId"] = assignedPatientId;
  doc["timestamp"] = millis();
  doc["heartRate"] = heartRate;
  doc["temperature"] = temperature;
  doc["oxygenSat"] = oxygenSat;
  doc["batteryLevel"] = batteryLevel;
  doc["quality"] = 95;

  String payload;
  serializeJson(doc, payload);

  if (mqttClient.publish(topic.c_str(), payload.c_str())) {
    Serial.println("📊 Vitals sent via MQTT: HR=" + String(heartRate) + ", Temp=" + String(temperature) + ", SpO2=" + String(oxygenSat) + "%");
  }
}

// ====================================
// UTILITY FUNCTIONS
// ====================================
void updateMockSensors() {
  heartRate = 70 + random(-10, 15);
  temperature = 98.6 + random(-5, 5) / 10.0;
  oxygenSat = 95 + random(0, 5);
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

  Serial.println("💾 Configuration saved");
}
