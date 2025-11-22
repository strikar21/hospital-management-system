/*
 * BLEScanner Implementation
 */

#include "BLEScanner.h"

// BLE Device Callback Class
class BLEDeviceCallback : public BLEAdvertisedDeviceCallbacks {
private:
  BLEScanner* parentScanner;

public:
  BLEDeviceCallback(BLEScanner* scanner) : parentScanner(scanner) {}

  void onResult(BLEAdvertisedDevice advertisedDevice) {
    if (parentScanner) {
      parentScanner->addDevice(advertisedDevice);
    }
  }
};

// Constructor
BLEScanner::BLEScanner(int maxDeviceLimit)
  : scanner(nullptr), initialized(false), maxDevices(maxDeviceLimit) {
}

// Destructor
BLEScanner::~BLEScanner() {
  if (scanner) {
    scanner->stop();
  }
}

// Initialize BLE scanner
bool BLEScanner::begin(const char* scannerName) {
  try {
    BLEDevice::init(scannerName);
    scanner = BLEDevice::getScan();
    scanner->setAdvertisedDeviceCallbacks(new BLEDeviceCallback(this));
    scanner->setActiveScan(true);        // Active scan for better detection
    scanner->setInterval(SCAN_INTERVAL);
    scanner->setWindow(SCAN_WINDOW);
    initialized = true;
    return true;
  } catch (...) {
    initialized = false;
    return false;
  }
}

// Check if device is a hospital device
bool BLEScanner::isHospitalDevice(const String& name, const String& address) {
  // Check for hospital device naming convention
  if (name.startsWith("fit-") ||           // Patient watches: fit-00001
      name.startsWith("tab-") ||           // Tablets: tab-00001
      name.startsWith("door-") ||          // Other door scanners: door-00001
      name.indexOf("Hospital") >= 0 ||     // Generic hospital devices
      name.indexOf("Watch") >= 0 ||        // Watch keyword
      name.indexOf("Tablet") >= 0) {       // Tablet keyword
    return true;
  }

  // Check for ESP32 MAC prefixes
  if (isESP32MAC(address)) {
    return true;
  }

  return false;
}

// Check if MAC address is ESP32
bool BLEScanner::isESP32MAC(const String& address) {
  return (address.startsWith("30:ae:a4") ||  // ESP32 WROOM
          address.startsWith("24:6f:28") ||  // ESP32 WROVER
          address.startsWith("ac:67:b2") ||  // ESP32-S2
          address.startsWith("7c:9e:bd"));   // ESP32-C3
}

// Check if device already detected
bool BLEScanner::alreadyDetected(const BLEAddress& address) {
  for (auto& device : detectedDevices) {
    if (device.getAddress().equals(address)) {
      return true;
    }
  }
  return false;
}

// Add device to detected list (called by callback)
void BLEScanner::addDevice(BLEAdvertisedDevice device) {
  String name = device.getName().c_str();
  String address = device.getAddress().toString().c_str();

  // Filter for hospital devices
  if (!isHospitalDevice(name, address)) {
    return;
  }

  // Prevent duplicates
  if (alreadyDetected(device.getAddress())) {
    return;
  }

  // Respect device limit
  if (detectedDevices.size() >= maxDevices) {
    return;
  }

  // Add device
  detectedDevices.push_back(device);

  Serial.printf("🔍 Detected: %s (%s) RSSI: %d dBm\n",
               name.c_str(), address.c_str(), device.getRSSI());
}

// Start BLE scan
void BLEScanner::startScan(int durationSeconds) {
  if (!initialized || !scanner) {
    return;
  }

  detectedDevices.clear();
  Serial.printf("🔵 Scanning for BLE devices (%ds)...\n", durationSeconds);
  scanner->start(durationSeconds, false);
  scanner->clearResults();
  Serial.printf("   Found %d hospital devices\n", detectedDevices.size());
}

// Stop BLE scan
void BLEScanner::stopScan() {
  if (scanner) {
    scanner->stop();
  }
}

// Clear detected devices
void BLEScanner::clearResults() {
  detectedDevices.clear();
}
