/*
 * ESP32 Hospital Door Scanner with Captive Portal
 * Enhanced version with auto WiFi scanning and web configuration
 * Tracks BLE devices (watches/tablets) and reports room presence to backend
 */

#include <WiFi.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <BLEDevice.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>
#include <Preferences.h>
#include <EEPROM.h>

// Device Configuration
const String DEVICE_TYPE = "door_scanner";
const String FIRMWARE_VERSION = "2.0.0";
String DEVICE_ID = "DOOR_SCANNER_001";  // Will be set from MAC
String ROOM_ID = "ICU-101";
String LOCATION = "ICU-101 Entrance";

// Network Configuration
Preferences preferences;
String stored_ssid = "";
String stored_password = "";
String backend_server = "192.168.1.100";
String backend_port = "8001";

// Captive Portal Configuration
WebServer server(80);
DNSServer dnsServer;
const char* ap_ssid = "Hospital_Door_Config";
const char* ap_password = "hospital123";
const byte DNS_PORT = 53;
IPAddress apIP(192, 168, 4, 1);

// BLE Configuration
BLEScan* pBLEScan;
std::vector<BLEAdvertisedDevice> detectedDevices;
bool ble_initialized = false;

// State Management
bool config_mode = false;
bool wifi_connected = false;
bool provisioned = false;
bool backend_registered = false;

// Timing Variables
unsigned long last_scan_report = 0;
unsigned long last_heartbeat = 0;
unsigned long last_wifi_check = 0;
unsigned long config_mode_start = 0;
const unsigned long scan_interval = 10000;        // Report every 10 seconds
const unsigned long heartbeat_interval = 60000;   // Heartbeat every 60 seconds
const unsigned long wifi_check_interval = 30000;  // Check WiFi every 30 seconds
const unsigned long config_timeout = 300000;      // Exit config mode after 5 minutes

class MyAdvertisedDeviceCallbacks: public BLEAdvertisedDeviceCallbacks {
    void onResult(BLEAdvertisedDevice advertisedDevice) {
      String deviceName = advertisedDevice.getName().c_str();
      String deviceAddress = advertisedDevice.getAddress().toString().c_str();

      // Filter for hospital devices - look for ESP32 devices or specific patterns
      if (deviceName.startsWith("ESP32_") ||
          deviceName.startsWith("HOSPITAL_") ||
          deviceName.indexOf("WATCH") >= 0 ||
          deviceName.indexOf("TABLET") >= 0 ||
          deviceAddress.startsWith("30:ae:a4") ||  // ESP32 MAC prefix
          deviceAddress.startsWith("24:6f:28")) {  // Another common ESP32 prefix

        // Avoid duplicates
        bool already_detected = false;
        for (const auto& device : detectedDevices) {
          if (device.getAddress().equals(advertisedDevice.getAddress())) {
            already_detected = true;
            break;
          }
        }

        if (!already_detected && detectedDevices.size() < 10) {  // Limit to 10 devices
          detectedDevices.push_back(advertisedDevice);
          Serial.println("🔍 Detected: " + deviceName + " (" + deviceAddress +
                        ") RSSI: " + String(advertisedDevice.getRSSI()) + "dBm");
        }
      }
    }
};

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("═══════════════════════════════════════");
  Serial.println("🏥 HOSPITAL DOOR SCANNER v" + FIRMWARE_VERSION);
  Serial.println("═══════════════════════════════════════");

  // Generate device ID from MAC address
  DEVICE_ID = "DOOR_" + WiFi.macAddress().substring(9);
  DEVICE_ID.replace(":", "");
  Serial.println("📱 Device ID: " + DEVICE_ID);

  // Initialize preferences
  preferences.begin("door-config", false);

  // Load stored configuration
  loadConfiguration();

  // Initialize BLE
  initializeBLE();

  // Try to connect to stored WiFi first
  if (stored_ssid.length() > 0) {
    Serial.println("🔗 Attempting to connect to stored WiFi: " + stored_ssid);
    connectToWiFi(stored_ssid, stored_password);

    if (wifi_connected) {
      provisioned = true;
      registerWithBackend();
    }
  }

  // If not connected, start configuration mode
  if (!wifi_connected) {
    startConfigMode();
  }
}

void loop() {
  unsigned long current_time = millis();

  if (config_mode) {
    handleConfigMode();

    // Exit config mode after timeout
    if (current_time - config_mode_start > config_timeout) {
      Serial.println("⏰ Config mode timeout - restarting");
      ESP.restart();
    }
  } else {
    // Normal operation mode
    handleNormalOperation(current_time);
  }

  delay(100);
}

void loadConfiguration() {
  stored_ssid = preferences.getString("wifi_ssid", "");
  stored_password = preferences.getString("wifi_pass", "");
  backend_server = preferences.getString("backend_ip", "192.168.1.100");
  backend_port = preferences.getString("backend_port", "8001");
  ROOM_ID = preferences.getString("room_id", "ICU-101");
  LOCATION = preferences.getString("location", "ICU-101 Entrance");

  Serial.println("📋 Configuration loaded:");
  Serial.println("   WiFi: " + (stored_ssid.length() > 0 ? stored_ssid : "Not configured"));
  Serial.println("   Backend: " + backend_server + ":" + backend_port);
  Serial.println("   Room: " + ROOM_ID);
  Serial.println("   Location: " + LOCATION);
}

void initializeBLE() {
  try {
    Serial.println("🔵 Initializing BLE scanner...");
    BLEDevice::init("Hospital_Door_Scanner");
    pBLEScan = BLEDevice::getScan();
    pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
    pBLEScan->setActiveScan(true);
    pBLEScan->setInterval(100);
    pBLEScan->setWindow(99);
    ble_initialized = true;
    Serial.println("✅ BLE scanner ready");
  } catch (...) {
    Serial.println("❌ BLE initialization failed");
    ble_initialized = false;
  }
}

void startConfigMode() {
  Serial.println("🌐 Starting configuration mode...");
  config_mode = true;
  config_mode_start = millis();

  // Set up Access Point
  WiFi.mode(WIFI_AP);
  WiFi.softAPConfig(apIP, apIP, IPAddress(255, 255, 255, 0));
  WiFi.softAP(ap_ssid, ap_password);

  // Start DNS server for captive portal
  dnsServer.start(DNS_PORT, "*", apIP);

  // Set up web server routes
  setupWebServer();
  server.begin();

  Serial.println("📡 Access Point: " + String(ap_ssid));
  Serial.println("🔒 Password: " + String(ap_password));
  Serial.println("🌐 Connect to: http://192.168.4.1");
  Serial.println("⏱️  Configuration timeout: 5 minutes");
}

void setupWebServer() {
  // Captive portal redirect
  server.onNotFound([]() {
    server.sendHeader("Location", "http://192.168.4.1/", true);
    server.send(302, "text/plain", "");
  });

  // Main configuration page
  server.on("/", HTTP_GET, handleRoot);
  server.on("/scan", HTTP_GET, handleWiFiScan);
  server.on("/configure", HTTP_POST, handleConfigure);
  server.on("/status", HTTP_GET, handleStatus);
}

void handleConfigMode() {
  dnsServer.processNextRequest();
  server.handleClient();
}

void handleNormalOperation(unsigned long current_time) {
  // Check WiFi connection periodically
  if (current_time - last_wifi_check >= wifi_check_interval) {
    checkWiFiConnection();
    last_wifi_check = current_time;
  }

  if (wifi_connected) {
    // Perform BLE scan and report
    if (current_time - last_scan_report >= scan_interval) {
      performBLEScanAndReport();
      last_scan_report = current_time;
    }

    // Send heartbeat
    if (current_time - last_heartbeat >= heartbeat_interval) {
      sendHeartbeat();
      last_heartbeat = current_time;
    }
  }
}

void handleRoot() {
  String html = generateConfigPage();
  server.send(200, "text/html", html);
}

void handleWiFiScan() {
  Serial.println("🔍 Scanning for WiFi networks...");
  String json = "{\"networks\":[";

  int n = WiFi.scanNetworks();
  for (int i = 0; i < n; i++) {
    if (i > 0) json += ",";
    json += "{";
    json += "\"ssid\":\"" + WiFi.SSID(i) + "\",";
    json += "\"rssi\":" + String(WiFi.RSSI(i)) + ",";
    json += "\"security\":" + String(WiFi.encryptionType(i));
    json += "}";
  }

  json += "]}";
  server.send(200, "application/json", json);
}

void handleConfigure() {
  String ssid = server.arg("ssid");
  String password = server.arg("password");
  String backend_ip = server.arg("backend_ip");
  String backend_p = server.arg("backend_port");
  String room = server.arg("room_id");
  String loc = server.arg("location");

  Serial.println("📝 Received configuration:");
  Serial.println("   SSID: " + ssid);
  Serial.println("   Backend: " + backend_ip + ":" + backend_p);
  Serial.println("   Room: " + room);

  // Save configuration
  preferences.putString("wifi_ssid", ssid);
  preferences.putString("wifi_pass", password);
  preferences.putString("backend_ip", backend_ip);
  preferences.putString("backend_port", backend_p);
  preferences.putString("room_id", room);
  preferences.putString("location", loc);

  server.send(200, "text/html",
    "<html><body><h2>Configuration Saved!</h2>"
    "<p>Door scanner will restart in 3 seconds...</p>"
    "<script>setTimeout(function(){window.close();}, 3000);</script>"
    "</body></html>");

  delay(3000);
  ESP.restart();
}

void handleStatus() {
  DynamicJsonDocument doc(1024);
  doc["deviceId"] = DEVICE_ID;
  doc["roomId"] = ROOM_ID;
  doc["location"] = LOCATION;
  doc["wifiConnected"] = wifi_connected;
  doc["backendRegistered"] = backend_registered;
  doc["bleInitialized"] = ble_initialized;
  doc["uptime"] = millis();
  doc["freeMemory"] = ESP.getFreeHeap();
  doc["signalStrength"] = WiFi.RSSI();
  doc["detectedDevices"] = detectedDevices.size();

  String response;
  serializeJson(doc, response);
  server.send(200, "application/json", response);
}

String generateConfigPage() {
  return String(R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hospital Door Scanner Config</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { color: #2c5aa0; margin: 0; }
        .header p { color: #666; margin: 5px 0; }
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; color: #333; }
        .form-group input, .form-group select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
        .wifi-scan { background: #e3f2fd; border: 1px solid #2196f3; border-radius: 5px; padding: 10px; margin-bottom: 10px; }
        .scan-btn { background: #2196f3; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
        .scan-btn:hover { background: #1976d2; }
        .network-list { max-height: 200px; overflow-y: auto; border: 1px solid #ddd; border-radius: 5px; margin-top: 10px; }
        .network-item { padding: 10px; border-bottom: 1px solid #eee; cursor: pointer; display: flex; justify-content: between; }
        .network-item:hover { background: #f0f0f0; }
        .network-item:last-child { border-bottom: none; }
        .network-name { font-weight: bold; flex-grow: 1; }
        .network-signal { color: #666; font-size: 0.9em; }
        .submit-btn { background: #4caf50; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; cursor: pointer; width: 100%; }
        .submit-btn:hover { background: #45a049; }
        .status { background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px; padding: 15px; margin-bottom: 20px; }
        .loading { display: none; text-align: center; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏥 Hospital Door Scanner</h1>
            <p><strong>Device:</strong> )rawliteral" + DEVICE_ID + R"rawliteral(</p>
            <p><strong>Room:</strong> )rawliteral" + ROOM_ID + R"rawliteral(</p>
        </div>

        <div class="status">
            <strong>📍 Current Status:</strong><br>
            • Configuration Mode Active<br>
            • Captive Portal Running<br>
            • Ready for Setup
        </div>

        <form id="configForm" onsubmit="submitConfig(event)">
            <div class="wifi-scan">
                <button type="button" class="scan-btn" onclick="scanWiFi()">🔍 Scan for Networks</button>
                <div class="loading" id="scanLoading">Scanning for WiFi networks...</div>
                <div class="network-list" id="networkList" style="display: none;"></div>
            </div>

            <div class="form-group">
                <label for="ssid">WiFi Network Name (SSID):</label>
                <input type="text" id="ssid" name="ssid" required placeholder="Enter WiFi network name">
            </div>

            <div class="form-group">
                <label for="password">WiFi Password:</label>
                <input type="password" id="password" name="password" placeholder="Enter WiFi password">
            </div>

            <div class="form-group">
                <label for="backend_ip">Hospital Backend IP:</label>
                <input type="text" id="backend_ip" name="backend_ip" value="192.168.1.100" required>
            </div>

            <div class="form-group">
                <label for="backend_port">Backend Port:</label>
                <input type="number" id="backend_port" name="backend_port" value="8001" required>
            </div>

            <div class="form-group">
                <label for="room_id">Room ID:</label>
                <input type="text" id="room_id" name="room_id" value=")rawliteral" + ROOM_ID + R"rawliteral(" required>
            </div>

            <div class="form-group">
                <label for="location">Scanner Location:</label>
                <input type="text" id="location" name="location" value=")rawliteral" + LOCATION + R"rawliteral(" required>
            </div>

            <button type="submit" class="submit-btn">💾 Save Configuration & Restart</button>
        </form>
    </div>

    <script>
        function scanWiFi() {
            document.getElementById('scanLoading').style.display = 'block';
            document.getElementById('networkList').style.display = 'none';

            fetch('/scan')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('scanLoading').style.display = 'none';
                    const networkList = document.getElementById('networkList');
                    networkList.innerHTML = '';

                    data.networks.forEach(network => {
                        const div = document.createElement('div');
                        div.className = 'network-item';
                        div.onclick = () => selectNetwork(network.ssid);

                        const signalStrength = network.rssi > -50 ? '📶' : network.rssi > -70 ? '📶' : '📶';
                        const security = network.security > 0 ? '🔒' : '🔓';

                        div.innerHTML = `
                            <span class="network-name">${network.ssid}</span>
                            <span class="network-signal">${signalStrength} ${security} ${network.rssi}dBm</span>
                        `;
                        networkList.appendChild(div);
                    });

                    networkList.style.display = 'block';
                })
                .catch(error => {
                    document.getElementById('scanLoading').style.display = 'none';
                    alert('WiFi scan failed: ' + error.message);
                });
        }

        function selectNetwork(ssid) {
            document.getElementById('ssid').value = ssid;
            document.getElementById('networkList').style.display = 'none';
        }

        function submitConfig(event) {
            event.preventDefault();

            const formData = new FormData(document.getElementById('configForm'));

            fetch('/configure', {
                method: 'POST',
                body: formData
            })
            .then(response => response.text())
            .then(data => {
                document.body.innerHTML = data;
            })
            .catch(error => {
                alert('Configuration failed: ' + error.message);
            });
        }

        // Auto-scan on page load
        setTimeout(scanWiFi, 1000);
    </script>
</body>
</html>
  )rawliteral");
}

void connectToWiFi(String ssid, String password) {
  Serial.println("🔗 Connecting to WiFi: " + ssid);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid.c_str(), password.c_str());

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(1000);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    wifi_connected = true;
    Serial.println("\n✅ WiFi connected!");
    Serial.println("📍 IP address: " + WiFi.localIP().toString());
    Serial.println("📶 Signal strength: " + String(WiFi.RSSI()) + " dBm");
  } else {
    wifi_connected = false;
    Serial.println("\n❌ WiFi connection failed");
  }
}

void checkWiFiConnection() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("⚠️ WiFi disconnected - attempting reconnection...");
    wifi_connected = false;
    connectToWiFi(stored_ssid, stored_password);
  }
}

void registerWithBackend() {
  if (!wifi_connected) return;

  Serial.println("📝 Registering with hospital backend...");

  HTTPClient http;
  http.begin("http://" + backend_server + ":" + backend_port + "/api/v1/esp32/register");
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(10000);

  DynamicJsonDocument doc(1024);
  doc["deviceId"] = DEVICE_ID;
  doc["deviceType"] = DEVICE_TYPE;
  doc["macAddress"] = WiFi.macAddress();
  doc["location"] = LOCATION;
  doc["roomId"] = ROOM_ID;
  doc["firmwareVersion"] = FIRMWARE_VERSION;
  doc["ipAddress"] = WiFi.localIP().toString();
  doc["signalStrength"] = WiFi.RSSI();

  String payload;
  serializeJson(doc, payload);

  int httpCode = http.POST(payload);
  if (httpCode > 0) {
    String response = http.getString();
    Serial.println("✅ Backend registration successful");
    Serial.println("📋 Response: " + response);
    backend_registered = true;
  } else {
    Serial.println("❌ Backend registration failed: " + String(httpCode));
    backend_registered = false;
  }

  http.end();
}

void performBLEScanAndReport() {
  if (!ble_initialized) return;

  // Clear previous results
  detectedDevices.clear();

  // Perform BLE scan
  BLEScanResults foundDevices = pBLEScan->start(3, false);
  pBLEScan->clearResults();

  // Report results
  if (!detectedDevices.empty() || true) {  // Always report, even if empty
    reportDetectedDevices();
  }
}

void reportDetectedDevices() {
  if (!wifi_connected) return;

  HTTPClient http;
  http.begin("http://" + backend_server + ":" + backend_port +
             "/api/v1/esp32/door-scanner/" + DEVICE_ID + "/scan");
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(10000);

  DynamicJsonDocument doc(2048);
  doc["deviceId"] = DEVICE_ID;
  doc["roomId"] = ROOM_ID;
  doc["location"] = LOCATION;
  doc["scanTimestamp"] = millis();
  doc["deviceCount"] = detectedDevices.size();

  JsonArray devicesArray = doc.createNestedArray("detectedDevices");

  for (const auto& device : detectedDevices) {
    JsonObject deviceObj = devicesArray.createNestedObject();

    String deviceName = device.getName().c_str();
    String deviceId = deviceName.length() > 0 ? deviceName : device.getAddress().toString().c_str();

    deviceObj["deviceId"] = deviceId;
    deviceObj["name"] = deviceName;
    deviceObj["address"] = device.getAddress().toString().c_str();
    deviceObj["rssi"] = device.getRSSI();
    deviceObj["timestamp"] = millis();

    // Determine device type
    if (deviceName.indexOf("WATCH") >= 0 || deviceName.indexOf("ESP32_") >= 0) {
      deviceObj["type"] = "esp32_watch";
    } else if (deviceName.indexOf("TABLET") >= 0) {
      deviceObj["type"] = "tablet";
    } else {
      deviceObj["type"] = "unknown";
    }
  }

  String payload;
  serializeJson(doc, payload);

  int httpCode = http.POST(payload);
  if (httpCode > 0) {
    if (detectedDevices.size() > 0) {
      Serial.println("📊 Reported " + String(detectedDevices.size()) +
                    " devices in " + ROOM_ID);
    } else {
      Serial.println("📭 Reported empty room: " + ROOM_ID);
    }
  } else {
    Serial.println("❌ Failed to report scan results: " + String(httpCode));
  }

  http.end();
}

void sendHeartbeat() {
  if (!wifi_connected) return;

  HTTPClient http;
  http.begin("http://" + backend_server + ":" + backend_port +
             "/api/v1/esp32/" + DEVICE_ID + "/heartbeat");
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(5000);

  DynamicJsonDocument doc(512);
  doc["deviceId"] = DEVICE_ID;
  doc["deviceType"] = DEVICE_TYPE;
  doc["roomId"] = ROOM_ID;
  doc["location"] = LOCATION;
  doc["status"] = "active";
  doc["signalStrength"] = WiFi.RSSI();
  doc["freeMemory"] = ESP.getFreeHeap();
  doc["uptime"] = millis();
  doc["lastScanDevices"] = detectedDevices.size();

  String payload;
  serializeJson(doc, payload);

  int httpCode = http.POST(payload);
  if (httpCode > 0) {
    Serial.println("💓 Heartbeat sent for room " + ROOM_ID);
  } else {
    Serial.println("❌ Heartbeat failed: " + String(httpCode));
  }

  http.end();
}