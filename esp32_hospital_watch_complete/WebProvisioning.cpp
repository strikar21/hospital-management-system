#include "WebProvisioning.h"

// External variables from main sketch
extern String wifiSSID;
extern String wifiPassword;
extern String serverIP;
extern String serverPort;
extern String mqttServer;
extern String mqttPort;
extern String macAddress;
extern const char* FIRMWARE_VERSION;
extern String deviceId;
extern bool wifiConnected;
extern bool ntpSynced;
extern bool isProvisioned;
extern bool isAssigned;
extern String assignedPatientId;
extern int batteryLevel;

// External functions from main sketch
extern void connectToWiFi();
extern bool hasCertificates();

// ====================================
// CONSTRUCTOR
// ====================================
WebProvisioning::WebProvisioning()
  : server(80),
    apIP(192, 168, 4, 1),
    netMsk(255, 255, 255, 0),
    networkCount(0),
    availableNetworks("") {
}

// ====================================
// INITIALIZATION
// ====================================
void WebProvisioning::begin(const char* apSSID, const char* apPassword, Preferences* prefsPtr) {
  this->apSSID = apSSID;
  this->apPassword = apPassword;
  this->prefs = prefsPtr;
}

// ====================================
// START CAPTIVE PORTAL
// ====================================
void WebProvisioning::startCaptivePortal() {
  Serial.println("🌐 Starting Captive Portal...");

  WiFi.disconnect();
  WiFi.mode(WIFI_OFF);
  delay(100);

  WiFi.mode(WIFI_AP);
  WiFi.softAPConfig(apIP, apIP, netMsk);
  WiFi.softAP(apSSID.c_str(), apPassword.c_str());

  delay(500);
  IPAddress IP = WiFi.softAPIP();
  Serial.println("📡 Captive Portal Network: " + apSSID);
  Serial.println("🌍 Access Point IP: " + IP.toString());

  dnsServer.setErrorReplyCode(DNSReplyCode::NoError);
  dnsServer.start(DNS_PORT, "*", apIP);

  scanWiFiNetworks(false);

  // Set up HTTP routes with lambda functions to capture 'this'
  server.on("/", HTTP_GET, [this]() { handleRoot(); });
  server.on("/scan", HTTP_GET, [this]() { handleScan(); });
  server.on("/configure", HTTP_POST, [this]() { handleConfigure(); });
  server.on("/status", HTTP_GET, [this]() { handleStatus(); });
  server.on("/generate_204", HTTP_GET, [this]() { handleRoot(); });  // Android captive portal
  server.on("/fwlink", HTTP_GET, [this]() { handleRoot(); });  // Windows captive portal
  server.onNotFound([this]() { handleRoot(); });

  server.begin();
  Serial.println("✅ Captive portal started");

  // LED blink confirmation
  for(int i = 0; i < 5; i++) {
    digitalWrite(2, HIGH);
    delay(200);
    digitalWrite(2, LOW);
    delay(200);
  }
}

// ====================================
// HANDLE CLIENT REQUESTS
// ====================================
void WebProvisioning::handleClient(bool wifiConnected) {
  if (!wifiConnected) {
    dnsServer.processNextRequest();
  }
  server.handleClient();
}

// ====================================
// SCAN WIFI NETWORKS
// ====================================
void WebProvisioning::scanWiFiNetworks(bool wifiConnected) {
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

      if (ssid.length() > 0 && !ssid.equals(apSSID)) {
        // HTML escape SSID
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
// HTTP HANDLER: ROOT (SETUP FORM)
// ====================================
void WebProvisioning::handleRoot() {
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

// ====================================
// HTTP HANDLER: SCAN NETWORKS
// ====================================
void WebProvisioning::handleScan() {
  Serial.println("🔄 Manual network scan requested");
  scanWiFiNetworks(false);
  server.sendHeader("Location", "/");
  server.send(302, "text/plain", "Scanning...");
}

// ====================================
// HTTP HANDLER: CONFIGURE
// ====================================
void WebProvisioning::handleConfigure() {
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

  prefs->putString("prov_code", provCode);
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

// ====================================
// HTTP HANDLER: STATUS
// ====================================
void WebProvisioning::handleStatus() {
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
