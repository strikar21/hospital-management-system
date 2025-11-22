/*
 * BLEScanner - Hospital Device Detection via Bluetooth Low Energy
 *
 * Detects and tracks hospital devices (watches, tablets, other scanners)
 * using BLE advertising packets and RSSI-based proximity.
 *
 * Features:
 * - Active scanning for better detection
 * - Hospital device filtering (fit-*, tab-*, door-*)
 * - ESP32 MAC prefix detection
 * - Duplicate prevention
 * - RSSI signal strength measurement
 * - Configurable device limit
 *
 * Version: 1.0.0
 */

#ifndef BLE_SCANNER_H
#define BLE_SCANNER_H

#include <BLEDevice.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>
#include <vector>

class BLEScanner {
private:
  BLEScan* scanner;
  std::vector<BLEAdvertisedDevice> detectedDevices;
  bool initialized;
  int maxDevices;

  // BLE scan parameters
  static const int SCAN_INTERVAL = 100;  // milliseconds
  static const int SCAN_WINDOW = 99;     // milliseconds

  // Hospital device filtering
  bool isHospitalDevice(const String& name, const String& address);
  bool isESP32MAC(const String& address);

  // Duplicate detection
  bool alreadyDetected(const BLEAddress& address);

public:
  BLEScanner(int maxDeviceLimit = 20);
  ~BLEScanner();

  // Initialization
  bool begin(const char* scannerName = "Hospital_Door_Scanner");
  bool isInitialized() const { return initialized; }

  // Scanning operations
  void startScan(int durationSeconds = 3);
  void stopScan();
  void clearResults();

  // Device access
  int getDeviceCount() const { return detectedDevices.size(); }
  std::vector<BLEAdvertisedDevice>& getDevices() { return detectedDevices; }

  // Device callback (friend class)
  void addDevice(BLEAdvertisedDevice device);
};

#endif
