#ifndef WEB_PROVISIONING_H
#define WEB_PROVISIONING_H

#include <Arduino.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <WiFi.h>
#include <Preferences.h>

class WebProvisioning {
public:
  WebProvisioning();

  // Initialize web provisioning
  void begin(const char* apSSID, const char* apPassword);

  // Start captive portal
  void startCaptivePortal();

  // Handle client requests (call in loop)
  void handleClient();

  // Check if provisioned
  bool isProvisioned();

  // Get provisioned WiFi credentials
  String getWiFiSSID();
  String getWiFiPassword();
  String getServerIP();
  String getServerPort();
  String getMQTTPort();
  String getProvCode();

  // Set external variables (for connectToWiFi callback)
  void setExternalVars(String* ssid, String* pass, String* serverIp,
                       String* httpPort, String* mqttServer, String* mqttPortStr,
                       String* macAddr, int* netCount, String* availNets);

private:
  WebServer server;
  DNSServer dnsServer;
  Preferences prefs;

  // AP settings
  String apSSID;
  String apPassword;

  // Network info
  String macAddress;
  int networkCount;
  String availableNetworks;

  // Provisioned credentials
  String wifiSSID;
  String wifiPassword;
  String serverIP;
  String serverPort;
  String mqttServer;
  String mqttPort;
  String provCode;

  // DNS and Captive Portal
  const byte DNS_PORT = 53;
  IPAddress apIP;
  IPAddress netMsk;

  // External variables (set by main sketch)
  String* ext_wifiSSID;
  String* ext_wifiPassword;
  String* ext_serverIP;
  String* ext_serverPort;
  String* ext_mqttServer;
  String* ext_mqttPort;
  String* ext_macAddress;
  int* ext_networkCount;
  String* ext_availableNetworks;

  // Internal methods
  void scanWiFiNetworks();
  void handleRoot();
  void handleScan();
  void handleConfigure();
  void handleStatus();

  // Callback for WiFi connection
  void (*connectToWiFiCallback)();
};

#endif
