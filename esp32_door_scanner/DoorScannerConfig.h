/*
 * DoorScannerConfig - Configuration and State Management
 *
 * Manages all persistent configuration for the door scanner including:
 * - Network credentials (WiFi SSID/password)
 * - Backend server details (host, port, HTTPS)
 * - Provisioning state (device ID, certificates)
 * - Room configuration (room ID, location, ward)
 *
 * Uses ESP32 Preferences library for non-volatile storage.
 *
 * Version: 1.0.0
 */

#ifndef DOOR_SCANNER_CONFIG_H
#define DOOR_SCANNER_CONFIG_H

#include <Arduino.h>
#include <Preferences.h>

class DoorScannerConfig {
private:
  Preferences prefs;

  // Preference keys
  static const char* PREF_NAMESPACE;
  static const char* KEY_WIFI_SSID;
  static const char* KEY_WIFI_PASS;
  static const char* KEY_BACKEND_HOST;
  static const char* KEY_BACKEND_PORT;
  static const char* KEY_USE_HTTPS;
  static const char* KEY_PROVISIONED;
  static const char* KEY_DEVICE_ID;
  static const char* KEY_DEVICE_NAME;
  static const char* KEY_ROOM_ID;
  static const char* KEY_LOCATION;
  static const char* KEY_WARD;
  static const char* KEY_DEVICE_CERT;
  static const char* KEY_DEVICE_KEY;
  static const char* KEY_CA_CERT;

public:
  // Configuration data
  struct Config {
    // Network
    String wifiSsid;
    String wifiPassword;
    String backendHost;
    String backendPort;
    bool useHttps;

    // Provisioning
    bool provisioned;
    String deviceId;
    String deviceName;

    // Room assignment
    String roomId;
    String locationDescription;
    String ward;

    // Certificates
    String deviceCertPem;
    String deviceKeyPem;
    String caCertPem;

    // Constructor with defaults
    Config() :
      wifiSsid(""),
      wifiPassword(""),
      backendHost(""),
      backendPort("8001"),
      useHttps(true),
      provisioned(false),
      deviceId(""),
      deviceName(""),
      roomId(""),
      locationDescription(""),
      ward(""),
      deviceCertPem(""),
      deviceKeyPem(""),
      caCertPem("")
    {}
  };

  DoorScannerConfig();
  ~DoorScannerConfig();

  // Initialization
  bool begin();
  void end();

  // Load/Save
  Config load();
  void save(const Config& config);

  // Individual setters
  void setWiFiCredentials(const String& ssid, const String& password);
  void setBackendDetails(const String& host, const String& port, bool https);
  void setProvisioningData(const String& deviceId, const String& deviceName,
                          const String& cert, const String& key, const String& ca);
  void setRoomConfig(const String& roomId, const String& location, const String& ward);

  // Clear all data
  void clear();

  // Debug
  void printConfig(const Config& config);
};

#endif
