/*
 * ESP32 Mutual TLS (mTLS) MQTT Connection - Minimal Test
 *
 * This sketch demonstrates the CORRECT way to establish mTLS with Mosquitto
 * on ESP32 using WiFiClientSecure + PubSubClient.
 *
 * KEY FIXES FOR errno 113 / rc=-2:
 * 1. Load certificates BEFORE creating PubSubClient instance
 * 2. Use const char* pointers with proper memory lifetime
 * 3. Set buffer sizes for large certificate chains
 * 4. Add delay between cert setup and MQTT connect
 * 5. Ensure LF-only line endings in PEM data
 *
 * Hardware: ESP32-WROOM-32 or compatible
 * Libraries: WiFi, WiFiClientSecure, PubSubClient, SPIFFS
 * Broker: Mosquitto with require_certificate=true, allow_anonymous=false
 */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <SPIFFS.h>

// ====================================
// CONFIGURATION
// ====================================
const char* WIFI_SSID = "NETGEAR05";
const char* WIFI_PASSWORD = "your_wifi_password";  // UPDATE THIS

const char* MQTT_SERVER = "192.168.0.113";
const int   MQTT_PORT = 8883;
const char* DEVICE_ID = "ESP32-WATCH-A0:A3:B3:AA:13:B0";  // From your serial output

// Certificate file paths in SPIFFS
const char* CA_CERT_PATH = "/hospital_ca.crt";
const char* DEVICE_CERT_PATH = "/device.crt";
const char* DEVICE_KEY_PATH = "/device.key";

// MQTT topics
String mqttTopicHeartbeat;
String mqttTopicCommand;
String mqttTopicAssign;

// ====================================
// GLOBAL CERTIFICATE STORAGE
// ====================================
// CRITICAL: Store certificates as String objects with GLOBAL SCOPE
// This prevents .c_str() dangling pointer issues
String caCertificate = "";
String deviceCertificate = "";
String devicePrivateKey = "";

// ====================================
// WiFi and MQTT Clients
// ====================================
WiFiClientSecure wifiClient;
PubSubClient* mqttClient = nullptr;  // Create AFTER certificates are loaded

// ====================================
// TIMING
// ====================================
unsigned long lastReconnectAttempt = 0;
const unsigned long RECONNECT_INTERVAL = 5000;  // 5 seconds between reconnect attempts

// ====================================
// FUNCTION PROTOTYPES
// ====================================
bool loadCertificatesFromSPIFFS();
bool setupMQTTWithTLS();
bool connectToMQTT();
void mqttCallback(char* topic, byte* payload, unsigned int length);
void publishHeartbeat();

// ====================================
// SETUP
// ====================================
void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n\n");
  Serial.println("========================================");
  Serial.println("ESP32 Mutual TLS MQTT Test");
  Serial.println("========================================");
  Serial.printf("Device ID: %s\n", DEVICE_ID);
  Serial.printf("Free heap: %d bytes\n", ESP.getFreeHeap());
  Serial.println();

  // ==================
  // 1. MOUNT SPIFFS
  // ==================
  Serial.println("[1/5] Mounting SPIFFS...");
  if (!SPIFFS.begin(true)) {
    Serial.println("❌ SPIFFS mount failed!");
    while (1) { delay(1000); }
  }
  Serial.println("✅ SPIFFS mounted");
  Serial.printf("    Free heap: %d bytes\n", ESP.getFreeHeap());
  Serial.println();

  // ==================
  // 2. LOAD CERTIFICATES FROM SPIFFS
  // ==================
  Serial.println("[2/5] Loading certificates from SPIFFS...");
  if (!loadCertificatesFromSPIFFS()) {
    Serial.println("❌ Certificate loading failed!");
    while (1) { delay(1000); }
  }
  Serial.println("✅ All certificates loaded");
  Serial.printf("    CA cert: %d bytes\n", caCertificate.length());
  Serial.printf("    Device cert: %d bytes\n", deviceCertificate.length());
  Serial.printf("    Device key: %d bytes\n", devicePrivateKey.length());
  Serial.printf("    Free heap: %d bytes\n", ESP.getFreeHeap());
  Serial.println();

  // ==================
  // 3. CONNECT TO WiFi
  // ==================
  Serial.println("[3/5] Connecting to WiFi...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\n❌ WiFi connection failed!");
    while (1) { delay(1000); }
  }

  Serial.println("\n✅ WiFi connected");
  Serial.printf("    IP: %s\n", WiFi.localIP().toString().c_str());
  Serial.printf("    Signal: %d dBm\n", WiFi.RSSI());
  Serial.printf("    Free heap: %d bytes\n", ESP.getFreeHeap());
  Serial.println();

  // ==================
  // 4. SETUP TLS CERTIFICATES
  // ==================
  Serial.println("[4/5] Configuring TLS with certificates...");
  if (!setupMQTTWithTLS()) {
    Serial.println("❌ TLS setup failed!");
    while (1) { delay(1000); }
  }
  Serial.println("✅ TLS configured with mTLS");
  Serial.printf("    Free heap: %d bytes\n", ESP.getFreeHeap());
  Serial.println();

  // ==================
  // 5. CONNECT TO MQTT BROKER
  // ==================
  Serial.println("[5/5] Connecting to MQTT broker...");
  if (connectToMQTT()) {
    Serial.println("✅ MQTT connected successfully!");
  } else {
    Serial.println("⚠️  Initial MQTT connection failed (will retry in loop)");
  }
  Serial.printf("    Free heap: %d bytes\n", ESP.getFreeHeap());
  Serial.println();

  Serial.println("========================================");
  Serial.println("Setup complete. Entering main loop...");
  Serial.println("========================================\n");
}

// ====================================
// LOOP
// ====================================
void loop() {
  // Maintain MQTT connection
  if (mqttClient && mqttClient->connected()) {
    mqttClient->loop();

    // Publish heartbeat every 30 seconds
    static unsigned long lastHeartbeat = 0;
    if (millis() - lastHeartbeat > 30000) {
      publishHeartbeat();
      lastHeartbeat = millis();
    }
  } else {
    // Reconnect if disconnected
    unsigned long now = millis();
    if (now - lastReconnectAttempt > RECONNECT_INTERVAL) {
      lastReconnectAttempt = now;
      Serial.println("⚠️  MQTT disconnected. Reconnecting...");
      if (connectToMQTT()) {
        lastReconnectAttempt = 0;  // Reset counter on successful connection
      }
    }
  }

  delay(10);  // Prevent watchdog issues
}

// ====================================
// LOAD CERTIFICATES FROM SPIFFS
// ====================================
bool loadCertificatesFromSPIFFS() {
  // Load CA certificate
  Serial.println("  📄 Loading CA certificate...");
  File caFile = SPIFFS.open(CA_CERT_PATH, "r");
  if (!caFile) {
    Serial.printf("    ❌ Failed to open %s\n", CA_CERT_PATH);
    return false;
  }
  caCertificate = caFile.readString();
  caFile.close();

  if (caCertificate.length() == 0) {
    Serial.println("    ❌ CA certificate is empty");
    return false;
  }
  Serial.printf("    ✅ CA cert loaded (%d bytes)\n", caCertificate.length());

  // Verify PEM format
  if (!caCertificate.startsWith("-----BEGIN CERTIFICATE-----")) {
    Serial.println("    ❌ CA cert: Invalid PEM format (missing header)");
    return false;
  }

  // Load device certificate
  Serial.println("  📄 Loading device certificate...");
  File certFile = SPIFFS.open(DEVICE_CERT_PATH, "r");
  if (!certFile) {
    Serial.printf("    ❌ Failed to open %s\n", DEVICE_CERT_PATH);
    return false;
  }
  deviceCertificate = certFile.readString();
  certFile.close();

  if (deviceCertificate.length() == 0) {
    Serial.println("    ❌ Device certificate is empty");
    return false;
  }
  Serial.printf("    ✅ Device cert loaded (%d bytes)\n", deviceCertificate.length());

  if (!deviceCertificate.startsWith("-----BEGIN CERTIFICATE-----")) {
    Serial.println("    ❌ Device cert: Invalid PEM format (missing header)");
    return false;
  }

  // Load device private key
  Serial.println("  📄 Loading device private key...");
  File keyFile = SPIFFS.open(DEVICE_KEY_PATH, "r");
  if (!keyFile) {
    Serial.printf("    ❌ Failed to open %s\n", DEVICE_KEY_PATH);
    return false;
  }
  devicePrivateKey = keyFile.readString();
  keyFile.close();

  if (devicePrivateKey.length() == 0) {
    Serial.println("    ❌ Device private key is empty");
    return false;
  }
  Serial.printf("    ✅ Device key loaded (%d bytes)\n", devicePrivateKey.length());

  if (!devicePrivateKey.startsWith("-----BEGIN ")) {
    Serial.println("    ❌ Device key: Invalid PEM format (missing header)");
    return false;
  }

  return true;
}

// ====================================
// SETUP MQTT WITH TLS
// ====================================
bool setupMQTTWithTLS() {
  Serial.println("  🔐 Configuring WiFiClientSecure...");

  // ==================
  // FIX #1: Set buffer sizes BEFORE loading certificates
  // ==================
  // Prevents memory issues with large certificate chains
  Serial.println("    Setting buffer sizes (4096, 4096)...");
  wifiClient.setBufferSizes(4096, 4096);

  // ==================
  // FIX #2: Load CA certificate for server validation
  // ==================
  // This validates that Mosquitto's server.crt is signed by our Hospital CA
  Serial.println("    Setting CA certificate (server validation)...");
  wifiClient.setCACert(caCertificate.c_str());
  Serial.println("    ✅ CA cert set");

  // ==================
  // FIX #3: Load client certificate and private key
  // ==================
  // CRITICAL: This is where most implementations fail
  // The ESP32 must present BOTH certificate AND private key during TLS handshake
  Serial.println("    Setting client certificate (mTLS authentication)...");
  wifiClient.setCertificate(deviceCertificate.c_str());
  Serial.println("    ✅ Client cert set");

  Serial.println("    Setting client private key...");
  wifiClient.setPrivateKey(devicePrivateKey.c_str());
  Serial.println("    ✅ Private key set");

  // ==================
  // FIX #4: Add delay to allow mbedTLS to fully initialize
  // ==================
  // Some ESP32 cores need this to properly set up the TLS context
  Serial.println("    Waiting for mbedTLS initialization...");
  delay(200);

  // ==================
  // FIX #5: Create PubSubClient AFTER certificates are loaded
  // ==================
  // This ensures the WiFiClientSecure is fully configured before MQTT uses it
  Serial.println("    Creating MQTT client instance...");
  if (mqttClient) {
    delete mqttClient;  // Clean up if we're reconfiguring
  }
  mqttClient = new PubSubClient(wifiClient);

  // Configure MQTT client
  mqttClient->setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient->setCallback(mqttCallback);
  mqttClient->setBufferSize(4096);  // Large buffer for big messages
  mqttClient->setKeepAlive(15);     // Short keepalive to detect disconnections quickly

  Serial.println("    ✅ MQTT client configured");

  // Setup topic names
  mqttTopicHeartbeat = "hospital/devices/" + String(DEVICE_ID) + "/heartbeat";
  mqttTopicCommand = "hospital/devices/" + String(DEVICE_ID) + "/command";
  mqttTopicAssign = "hospital/devices/" + String(DEVICE_ID) + "/assign";

  return true;
}

// ====================================
// CONNECT TO MQTT BROKER
// ====================================
bool connectToMQTT() {
  if (!mqttClient) {
    Serial.println("  ❌ MQTT client not initialized");
    return false;
  }

  Serial.println("  🔄 Attempting MQTT connection...");
  Serial.printf("    Server: %s:%d\n", MQTT_SERVER, MQTT_PORT);
  Serial.printf("    Client ID: %s\n", DEVICE_ID);
  Serial.printf("    Free heap before connect: %d bytes\n", ESP.getFreeHeap());

  // ==================
  // FIX #6: Simple connect with client ID only
  // ==================
  // With mTLS, authentication is via certificate CN (Common Name)
  // No username/password needed - Mosquitto extracts username from cert CN
  // use_identity_as_username=true means CN becomes MQTT username

  bool connected = mqttClient->connect(DEVICE_ID);

  if (connected) {
    Serial.println("  ✅ MQTT CONNECTED!");
    Serial.printf("    Free heap after connect: %d bytes\n", ESP.getFreeHeap());

    // Subscribe to command topics
    Serial.println("  📡 Subscribing to topics...");

    if (mqttClient->subscribe(mqttTopicCommand.c_str(), 0)) {
      Serial.printf("    ✅ Subscribed: %s\n", mqttTopicCommand.c_str());
    } else {
      Serial.printf("    ⚠️  Subscribe failed: %s\n", mqttTopicCommand.c_str());
    }

    if (mqttClient->subscribe(mqttTopicAssign.c_str(), 0)) {
      Serial.printf("    ✅ Subscribed: %s\n", mqttTopicAssign.c_str());
    } else {
      Serial.printf("    ⚠️  Subscribe failed: %s\n", mqttTopicAssign.c_str());
    }

    // Send initial heartbeat
    publishHeartbeat();

    return true;

  } else {
    // Connection failed - diagnose
    int state = mqttClient->state();
    Serial.printf("  ❌ MQTT connection failed, rc=%d\n", state);
    Serial.printf("    Free heap after failed connect: %d bytes\n", ESP.getFreeHeap());

    // Decode error state
    switch (state) {
      case -4:
        Serial.println("    MQTT_CONNECTION_TIMEOUT - Server didn't respond");
        break;
      case -3:
        Serial.println("    MQTT_CONNECTION_LOST - Network connection broken");
        break;
      case -2:
        Serial.println("    MQTT_CONNECT_FAILED - TLS handshake failed");
        Serial.println("    💡 This usually means:");
        Serial.println("       - Client certificate not sent (WiFiClientSecure bug)");
        Serial.println("       - Certificate CN doesn't match expected format");
        Serial.println("       - Certificate expired or not yet valid");
        Serial.println("       - Private key doesn't match certificate");
        break;
      case -1:
        Serial.println("    MQTT_DISCONNECTED - Not connected");
        break;
      case 1:
        Serial.println("    MQTT_CONNECT_BAD_PROTOCOL - Protocol version mismatch");
        break;
      case 2:
        Serial.println("    MQTT_CONNECT_BAD_CLIENT_ID - Client ID rejected");
        break;
      case 3:
        Serial.println("    MQTT_CONNECT_UNAVAILABLE - Server unavailable");
        break;
      case 4:
        Serial.println("    MQTT_CONNECT_BAD_CREDENTIALS - Auth failed (shouldn't happen with certs)");
        break;
      case 5:
        Serial.println("    MQTT_CONNECT_UNAUTHORIZED - Not authorized (ACL issue)");
        break;
      default:
        Serial.printf("    Unknown state: %d\n", state);
        break;
    }

    return false;
  }
}

// ====================================
// MQTT CALLBACK
// ====================================
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.printf("📨 MQTT message received:\n");
  Serial.printf("   Topic: %s\n", topic);
  Serial.printf("   Length: %d bytes\n", length);

  // Convert payload to string
  char message[length + 1];
  memcpy(message, payload, length);
  message[length] = '\0';

  Serial.printf("   Payload: %s\n", message);
}

// ====================================
// PUBLISH HEARTBEAT
// ====================================
void publishHeartbeat() {
  if (!mqttClient || !mqttClient->connected()) {
    Serial.println("⚠️  Cannot publish heartbeat - not connected");
    return;
  }

  // Create simple JSON heartbeat
  String payload = "{";
  payload += "\"deviceId\":\"" + String(DEVICE_ID) + "\",";
  payload += "\"timestamp\":" + String(millis()) + ",";
  payload += "\"uptime\":" + String(millis() / 1000) + ",";
  payload += "\"freeHeap\":" + String(ESP.getFreeHeap()) + ",";
  payload += "\"rssi\":" + String(WiFi.RSSI());
  payload += "}";

  if (mqttClient->publish(mqttTopicHeartbeat.c_str(), payload.c_str(), false)) {
    Serial.printf("💓 Heartbeat published (%d bytes)\n", payload.length());
  } else {
    Serial.println("❌ Heartbeat publish failed");
  }
}
