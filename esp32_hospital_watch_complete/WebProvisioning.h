#ifndef WEB_PROVISIONING_H
#define WEB_PROVISIONING_H

#include <Arduino.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <WiFi.h>
#include <Preferences.h>

// ====================================
// WEB PROVISIONING MODULE
// ====================================
// HTTP Captive Portal for WiFi and MQTT configuration
// Provides web interface for device provisioning

class WebProvisioning {
public:
  WebProvisioning();

  // Initialization
  void begin(const char* apSSID, const char* apPassword, Preferences* prefsPtr);

  // Start captive portal (WiFi AP mode with DNS redirect)
  void startCaptivePortal();

  // Handle client requests (call in loop)
  void handleClient(bool wifiConnected);

  // Scan WiFi networks and populate dropdown
  void scanWiFiNetworks(bool wifiConnected);

  // Get network scan results
  String getAvailableNetworks() { return availableNetworks; }
  int getNetworkCount() { return networkCount; }

private:
  // Server instances
  WebServer server;
  DNSServer dnsServer;
  Preferences* prefs;

  // AP configuration
  String apSSID;
  String apPassword;

  // DNS and network config
  const byte DNS_PORT = 53;
  IPAddress apIP;
  IPAddress netMsk;

  // Network scan results
  String availableNetworks;
  int networkCount;

  // HTTP request handlers
  void handleRoot();
  void handleScan();
  void handleConfigure();
  void handleStatus();
};

#endif
