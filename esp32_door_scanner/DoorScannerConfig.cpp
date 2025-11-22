/*
 * DoorScannerConfig Implementation
 */

#include "DoorScannerConfig.h"

// Preference keys
const char* DoorScannerConfig::PREF_NAMESPACE = "door-scanner";
const char* DoorScannerConfig::KEY_WIFI_SSID = "wifiSsid";
const char* DoorScannerConfig::KEY_WIFI_PASS = "wifiPass";
const char* DoorScannerConfig::KEY_BACKEND_HOST = "backendHost";
const char* DoorScannerConfig::KEY_BACKEND_PORT = "backendPort";
const char* DoorScannerConfig::KEY_USE_HTTPS = "useHttps";
const char* DoorScannerConfig::KEY_PROVISIONED = "provisioned";
const char* DoorScannerConfig::KEY_DEVICE_ID = "deviceId";
const char* DoorScannerConfig::KEY_DEVICE_NAME = "deviceName";
const char* DoorScannerConfig::KEY_ROOM_ID = "roomId";
const char* DoorScannerConfig::KEY_LOCATION = "location";
const char* DoorScannerConfig::KEY_WARD = "ward";
const char* DoorScannerConfig::KEY_DEVICE_CERT = "deviceCert";
const char* DoorScannerConfig::KEY_DEVICE_KEY = "deviceKey";
const char* DoorScannerConfig::KEY_CA_CERT = "caCert";

// Constructor
DoorScannerConfig::DoorScannerConfig() {
}

// Destructor
DoorScannerConfig::~DoorScannerConfig() {
  end();
}

// Initialize preferences
bool DoorScannerConfig::begin() {
  return prefs.begin(PREF_NAMESPACE, false);
}

// End preferences
void DoorScannerConfig::end() {
  prefs.end();
}

// Load configuration from preferences
DoorScannerConfig::Config DoorScannerConfig::load() {
  Config config;

  config.wifiSsid = prefs.getString(KEY_WIFI_SSID, "");
  config.wifiPassword = prefs.getString(KEY_WIFI_PASS, "");
  config.backendHost = prefs.getString(KEY_BACKEND_HOST, "");
  config.backendPort = prefs.getString(KEY_BACKEND_PORT, "8001");
  config.useHttps = prefs.getBool(KEY_USE_HTTPS, true);

  config.provisioned = prefs.getBool(KEY_PROVISIONED, false);
  config.deviceId = prefs.getString(KEY_DEVICE_ID, "");
  config.deviceName = prefs.getString(KEY_DEVICE_NAME, "");

  config.roomId = prefs.getString(KEY_ROOM_ID, "");
  config.locationDescription = prefs.getString(KEY_LOCATION, "");
  config.ward = prefs.getString(KEY_WARD, "");

  config.deviceCertPem = prefs.getString(KEY_DEVICE_CERT, "");
  config.deviceKeyPem = prefs.getString(KEY_DEVICE_KEY, "");
  config.caCertPem = prefs.getString(KEY_CA_CERT, "");

  return config;
}

// Save configuration to preferences
void DoorScannerConfig::save(const Config& config) {
  prefs.putString(KEY_WIFI_SSID, config.wifiSsid);
  prefs.putString(KEY_WIFI_PASS, config.wifiPassword);
  prefs.putString(KEY_BACKEND_HOST, config.backendHost);
  prefs.putString(KEY_BACKEND_PORT, config.backendPort);
  prefs.putBool(KEY_USE_HTTPS, config.useHttps);

  prefs.putBool(KEY_PROVISIONED, config.provisioned);
  prefs.putString(KEY_DEVICE_ID, config.deviceId);
  prefs.putString(KEY_DEVICE_NAME, config.deviceName);

  prefs.putString(KEY_ROOM_ID, config.roomId);
  prefs.putString(KEY_LOCATION, config.locationDescription);
  prefs.putString(KEY_WARD, config.ward);

  prefs.putString(KEY_DEVICE_CERT, config.deviceCertPem);
  prefs.putString(KEY_DEVICE_KEY, config.deviceKeyPem);
  prefs.putString(KEY_CA_CERT, config.caCertPem);
}

// Set WiFi credentials
void DoorScannerConfig::setWiFiCredentials(const String& ssid, const String& password) {
  prefs.putString(KEY_WIFI_SSID, ssid);
  prefs.putString(KEY_WIFI_PASS, password);
}

// Set backend details
void DoorScannerConfig::setBackendDetails(const String& host, const String& port, bool https) {
  prefs.putString(KEY_BACKEND_HOST, host);
  prefs.putString(KEY_BACKEND_PORT, port);
  prefs.putBool(KEY_USE_HTTPS, https);
}

// Set provisioning data
void DoorScannerConfig::setProvisioningData(const String& deviceId, const String& deviceName,
                                           const String& cert, const String& key, const String& ca) {
  prefs.putBool(KEY_PROVISIONED, true);
  prefs.putString(KEY_DEVICE_ID, deviceId);
  prefs.putString(KEY_DEVICE_NAME, deviceName);
  prefs.putString(KEY_DEVICE_CERT, cert);
  prefs.putString(KEY_DEVICE_KEY, key);
  prefs.putString(KEY_CA_CERT, ca);
}

// Set room configuration
void DoorScannerConfig::setRoomConfig(const String& roomId, const String& location, const String& ward) {
  prefs.putString(KEY_ROOM_ID, roomId);
  prefs.putString(KEY_LOCATION, location);
  prefs.putString(KEY_WARD, ward);
}

// Clear all preferences
void DoorScannerConfig::clear() {
  prefs.clear();
}

// Print configuration for debugging
void DoorScannerConfig::printConfig(const Config& config) {
  Serial.println("📋 Configuration:");
  Serial.println("   WiFi: " + (config.wifiSsid.length() > 0 ? config.wifiSsid : "Not configured"));
  Serial.println("   Backend: " + config.backendHost + ":" + config.backendPort);
  Serial.println("   HTTPS: " + String(config.useHttps ? "Enabled" : "Disabled"));
  Serial.println("   Provisioned: " + String(config.provisioned ? "Yes" : "No"));

  if (config.provisioned) {
    Serial.println("   Device ID: " + config.deviceId);
    Serial.println("   Device Name: " + config.deviceName);
    Serial.println("   Room: " + config.roomId);
    Serial.println("   Location: " + config.locationDescription);
    Serial.println("   Ward: " + config.ward);
  }
}
