/*
 * ESP32 Hospital Watch - Certificate-Based Authentication + Waveform Streaming
 * Version: 5.4.0
 *
 * Features:
 * - Automatic captive portal when connecting to hotspot
 * - Auto WiFi scanning with dropdown
 * - HTTPS certificate provisioning with one-time codes
 * - Certificate-based MQTT authentication (mTLS)
 * - MQTT TLS 1.2 authentication on port 8883
 * - NTP time synchronization for ISO 8601 timestamps
 * - MQTT vitals, alerts, and heartbeat
 * - 8 device-level alerts (moved 14 clinical alerts to backend)
 * - ✅ v5.1: Physiological simulator (realistic vitals + ECG/EEG waveforms)
 * - ✅ v5.2: Real-time waveform streaming (500Hz, 50 samples/100ms)
 * - ✅ v5.2: NFC support (PN532 I2C + IRQ for badges/wristbands/room tags)
 * - ✅ v5.2.1: MQTT QoS 1 with retry logic and exponential backoff
 * - ✅ v5.2.1: Offline data buffering (SPIFFS-based queue for vitals/alerts/waveforms)
 * - ✅ v5.2.2: Offline queue bug fixes (early exit, alert spam, disconnect counter)
 * - ✅ v5.2.3: Auto-reconnect to saved WiFi when network becomes available in captive portal mode
 * - ✅ v5.2.4: Patient monitoring continues offline (P0 critical fix)
 * - ✅ v5.2.4: millis() overflow protection for 49.7+ day uptime (P1 fix)
 * - ✅ v5.2.4: Non-blocking LED alerts (P1 fix - no more delay() blocking)
 * - ✅ v5.2.4: Debug logging flag for production deployment (P2 fix)
 * - ✅ v5.2.5: Delta encoding for waveforms (51% bandwidth reduction - 9.5MB/s → 4.6MB/s for 500 watches)
 * - ✅ v5.2.6: CRITICAL BUGFIX - SPIFFS file deletion (V-lead compression root cause)
 * - ✅ v5.2.6: Vitals sequence counter (message ID for tracking)
 * - ✅ v5.2.7: CRITICAL BUGFIX - Fixed augmented lead formulas (Goldberger amplification)
 * - ✅ v5.2.8: CRITICAL BUGFIX - DC offset removal for derived leads (Lead III, aVR, aVL, aVF)
 * - ✅ v5.2.9: CRITICAL BUGFIX - Simulator mode initialization (GPIO-based ECG/EEG selection)
 * - ✅ v5.2.10: CRITICAL BUGFIX - EEG timing fix (phase increments once per sample, not per channel)
 * - ✅ v5.2.11: MEDICAL ACCURACY FIX - Channel-specific frequency mixing (frontal=beta, occipital=alpha)
 * - ✅ v5.2.13: CRITICAL BUGFIX - Non-blocking calibration (removes 3.7s freeze, waveforms stream during calibration)
 * - ✅ v5.2.13: FEATURE - EEG calibration pulse support (100μV pulse, mode-specific calibration)
 * - ✅ v5.2.14: FEATURE - Blood pressure monitoring (systolic/diastolic transmission via MQTT)
 * - ✅ v5.3.0: FEATURE - LVGL display integration (touch UI with real-time vitals display)
 * - ✅ v5.4.0: FEATURE - Remote device configuration & management (17 MQTT commands)
 *
 * CHANGES FROM v5.0:
 * ✅ v5.1: PhysiologicalSimulator for realistic patient vitals
 * ✅ v5.2: Micro-batch waveform generation (10 samples every 20ms)
 * ✅ v5.2: MQTT waveform streaming to hospital/devices/{deviceId}/stream
 * ✅ v5.2: NFC IRQ mode for Mifare card detection
 * ✅ v5.2: ArduinoJson v7 compatibility
 * ✅ v5.2.1: MQTT QoS 1 + retry (3 attempts with exponential backoff)
 * ✅ v5.2.1: Offline queue (saves vitals/alerts/waveforms to SPIFFS when disconnected)
 * ✅ v5.2.1: Batch transmission (processes queued messages every 30s when reconnected)
 * ✅ v5.2.2: Bug #1 - Fixed offline queue early exit (sendVitals/sendAlert/sendWaveformStream)
 * ✅ v5.2.2: Bug #2 - Fixed disconnect counter persistence (resets to 0 on reboot)
 * ✅ v5.2.2: Bug #5 - Fixed deviceUnresponsive alert spam (only triggers once)
 * ✅ v5.2.2: Bug #6 - Fixed frequentDisconnects alert spam (only triggers once)
 * ✅ v5.2.3: Auto WiFi reconnection in captive portal mode when saved network detected
 * ✅ v5.2.4: P0 CRITICAL - Patient monitoring never stops (removed wifiConnected guards)
 * ✅ v5.2.4: P1 MEDIUM - millis() overflow handling (unsigned long casts for 49.7+ day uptime)
 * ✅ v5.2.4: P1 MEDIUM - Non-blocking LED flasher (replaced delay() with state machine)
 * ✅ v5.2.4: P2 LOW - Debug logging flag (reduce serial spam in production)
 * ✅ v5.2.5: Delta encoding for ECG/EEG waveforms (baseline + deltas storage)
 * ✅ v5.2.5: Fixed field naming (leadI/leadII/leadIII, Fp1/Fp2/F3/F4/C3/C4/O1/O2)
 * ✅ v5.2.5: Added duration field (0.1 seconds for 100ms packets)
 * ✅ v5.2.6: Fixed SPIFFS.remove() using full path instead of basename (line 354, 361)
 * ✅ v5.2.6: Added vitalsSequenceCounter for message tracking (line 165, 1838)
 * ✅ v5.2.6: Added "(deleted)" suffix to queue log messages for verification (line 363)
 * ✅ v5.2.7: Fixed aVL/aVF formulas with proper operator precedence (lines 2003-2005)
 * ✅ v5.2.7: Implemented Goldberger amplification (1.5x) for all augmented leads
 * ✅ v5.2.7: Changed variable names from ch0/ch1 to leadI/leadII for clarity
 * ✅ v5.2.8: CRITICAL FIX - Subtract ADC midpoint (8388608) before derived lead calculations
 * ✅ v5.2.8: Fixed Lead III, aVR, aVL, aVF to work in relative space, then convert back
 * ✅ v5.2.9: CRITICAL FIX - Set simulator mode at startup based on GPIO pin (MODE_SELECT_PIN)
 * ✅ v5.2.9: Bug: Simulator defaulted to ECG mode, never changed despite GPIO state
 * ✅ v5.2.9: Result: GPIO 4 LOW now correctly generates EEG waveforms, not ECG
 * ✅ v5.2.10: CRITICAL FIX - EEG phase increments ONCE per sample (not 8× per channel)
 * ✅ v5.2.10: Bug: generateEEGSample() called 8 times → phase advanced 8× faster (84 Hz instead of 10.5 Hz)
 * ✅ v5.2.10: Fix: New generateEEGSampleWithPhase() method + phase update outside channel loop
 * ✅ v5.2.10: Result: EEG now shows smooth 10.5 Hz alpha waves (not compressed noise)
 * ✅ v5.2.11: MEDICAL ACCURACY FIX - Channel-specific frequency mixing for anatomically correct brain regions
 * ✅ v5.2.11: Bug: All EEG channels used identical weights (alpha*0.6 + beta*0.3) → identical waveforms
 * ✅ v5.2.11: Fix: Frontal channels (Fp1/Fp2) = beta*0.6 + alpha*0.3, Occipital (O1/O2) = alpha*0.8 + beta*0.1
 * ✅ v5.2.11: Result: Frontal shows fast oscillations (beta-dominant), Occipital shows slow oscillations (alpha-dominant)
 * ✅ v5.2.12: CRITICAL BUGFIX - Simulator mode was only set once at boot, never updated when GPIO pin changed
 * ✅ v5.2.12: Bug: Swap ECG↔EEG cable → frontend shows correct mode label but wrong waveforms
 * ✅ v5.2.12: Fix: Check GPIO pin every 1s (before simulator.update()) and call setMode() dynamically
 * ✅ v5.2.12: Result: Mode switching now works correctly - waveforms match the current GPIO pin state
 * ✅ v5.2.14: FEATURE - Blood pressure monitoring (systolic/diastolic)
 * ✅ v5.2.14: Added bloodPressureSystolic and bloodPressureDiastolic global variables (lines 215-216)
 * ✅ v5.2.14: Read BP from PhysiologicalSimulator every 1s (lines 1136-1137)
 * ✅ v5.2.14: Transmit BP via MQTT in vitals message (lines 1940-1941)
 * ✅ v5.2.14: Updated serial debug output to show BP (e.g., "BP=120/80")
 * ✅ v5.3.0: FEATURE - LVGL display integration with touch UI
 * ✅ v5.3.0: Added DisplayManager, UIScreens, and TouchHandler includes
 * ✅ v5.3.0: Created global display, ui, and touch instances
 * ✅ v5.3.0: Initialize LVGL display subsystem in setup()
 * ✅ v5.3.0: Update LVGL timer and UI in main loop()
 * ✅ v5.3.0: Real-time vitals display update via ui.updateVitals()
 * ✅ v5.3.0: Connection status updates on NTP sync success/failure
 * ✅ v5.3.0: Added setDisplayBrightness() helper function (0-100% range)
 * ✅ v5.3.0: Version string updated to "v5.3.0 (LVGL Display Integration)"
 * ✅ v5.2.14: Result: Backend now receives and stores BP data in TimescaleDB vitals_realtime table
 * ✅ v5.4.0: FEATURE - Remote Device Configuration & Management via MQTT
 * ✅ v5.4.0: Added 17 MQTT command handlers for complete device control
 * ✅ v5.4.0: Configuration parameters: displayBrightness, waveformStreamingEnabled, samplingRate, vitalsTransmissionInterval, debugModeEnabled, ledAlertsEnabled
 * ✅ v5.4.0: Configurable alert thresholds for all vitals (HR, SpO2, Temp, BP, RR)
 * ✅ v5.4.0: Commands: setDisplayBrightness, setWaveformStreaming, setSamplingRate, setVitalsInterval, setDebugMode, setAlertThreshold, setLEDAlerts
 * ✅ v5.4.0: Management commands: getDeviceStatus, clearOfflineQueue, syncTime, setWaveformMode, reboot, unassign, custom
 * ✅ v5.4.0: Device status command returns comprehensive JSON (battery, memory, uptime, connectivity, config, vitals, device info)
 * ✅ v5.4.0: All configuration persisted to NVS flash (survives reboots)
 * ✅ v5.4.0: Configuration loaded at boot and applied to runtime behavior
 * ✅ v5.4.0: Vitals transmission interval now configurable (1-60 seconds, default: 5s)
 * ✅ v5.4.0: Waveform streaming can be enabled/disabled remotely
 * ✅ v5.4.0: Sampling rate adjustable (100-1000 Hz, default: 250 Hz)
 * ✅ v5.4.0: Display brightness remotely controllable (0-100%)
 * ✅ v5.4.0: LED alerts can be disabled for silent operation
 * ✅ v5.4.0: Remote ECG/EEG mode switching without GPIO pin
 * ✅ v5.4.0: Force NTP sync command for accurate time synchronization
 * ✅ v5.4.0: Clear offline queue command to free SPIFFS space
 * ✅ v5.4.0: Remote reboot capability for firmware updates
 * ✅ v5.4.0: Enhanced sendCommandAck() with optional data parameter for status responses
 * ✅ v5.4.0: All commands validated with detailed error messages
 * ✅ v5.4.0: Integration with backend REST API (device_commands_api.py)
 * ✅ v5.4.0: Version string updated to "v5.4.0 (Remote Configuration)"
 */

#include <WiFi.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <PubSubClient.h>
#include <time.h>
#include <WiFiClientSecure.h>
#include <SPIFFS.h>
#include <HTTPClient.h>  // ✅ v5.0: Added for HTTPS provisioning
#include "PhysiologicalSimulator.h"  // ✅ v5.1: Vitals and ECG simulator
#include "NFCManager.h"  // ✅ v5.2: NFC support for badges/wristbands/room tags
#include "DisplayManager.h"  // ✅ v5.3: LVGL display manager
#include "UIScreens.h"       // ✅ v5.3: UI screens
#include "TouchHandler.h"    // ✅ v5.3: Touch gestures
#include "QMI8658Manager.h"  // ✅ v5.4: Real IMU for fall & tremor detection

// ====================================
// DEVICE CONFIGURATION
// ====================================
const char* AP_SSID = "HospitalWatch";
const char* AP_PASSWORD = "";
const char* DEVICE_TYPE = "watch";

// ✅ SINGLE SOURCE OF TRUTH FOR VERSION
const char* FIRMWARE_VERSION = "5.4.0";
const char* VERSION_NAME = "Remote Configuration";
const char* VERSION_FEATURES = "17 MQTT commands | Remote config | Alert thresholds | Device status | Reboot";

// ====================================
// ✅ v5.2.4: DEBUG LOGGING (P2 fix)
// ====================================
const bool DEBUG_WAVEFORMS = false;  // Set to true to enable verbose waveform debugging

// ====================================
// GPIO PIN CONFIGURATION
// ====================================
#define MODE_SELECT_PIN 4   // GPIO 4 for ECG/EEG mode selection (HIGH=ECG, LOW=EEG)

// ✅ v5.3: NFC on separate I2C Bus 1 (to avoid conflict with display touch on Bus 0)
#define NFC_SDA_PIN 16      // GPIO 16 for NFC I2C SDA (Bus 1)
#define NFC_SCL_PIN 17      // GPIO 17 for NFC I2C SCL (Bus 1)
#define NFC_IRQ_PIN 25      // GPIO 25 for NFC interrupt (PN532 IRQ pin)

// ====================================
// TLS CERTIFICATE - LOADED FROM SPIFFS
// ====================================
const char* CA_CERT_PATH = "/ca.crt";
String caCertificate = "";
String deviceCertificate = "";  // ✅ v5.0.2: Global to prevent .c_str() dangling pointers
String devicePrivateKey = "";   // ✅ v5.0.2: Global to prevent .c_str() dangling pointers

// ====================================
// NTP CONFIGURATION
// ====================================
const char* NTP_SERVER = "pool.ntp.org";
const long GMT_OFFSET_SEC = 19800;  // IST (UTC+5:30)
const int DAYLIGHT_OFFSET_SEC = 0;

// ====================================
// NETWORK COMPONENTS
// ====================================
WebServer server(80);
DNSServer dnsServer;
WiFiClientSecure wifiClient;
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
String mqttPort = "8883";
// ✅ v5.0: REMOVED hardcoded shared credentials
// Certificates loaded from SPIFFS instead
String serialNumber = "";
String assignedPatientId = "";
bool isProvisioned = false;
bool isAssigned = false;
bool wifiConnected = false;
bool ntpSynced = false;
bool provisioningInProgress = false;
String availableNetworks = "";
int networkCount = 0;
bool mqttConfigured = false;  // ✅ v5.0.3: Track if MQTT certs already loaded

// ====================================
// PHYSIOLOGICAL SIMULATOR
// ====================================
PhysiologicalSimulator simulator;  // ✅ v5.1: Realistic vitals and ECG generator

// ====================================
// REAL IMU (v5.4) - QMI8658 6-Axis
// ====================================
QMI8658Manager imuSensor;  // ✅ v5.4: Real fall & tremor detection
bool imuAvailable = false;  // True if IMU initialized successfully

// ====================================
// NFC MANAGER (v5.2)
// ====================================
NFCManager nfc(NFC_SDA_PIN, NFC_SCL_PIN, NFC_IRQ_PIN);  // ✅ v5.3: NFC on I2C Bus 1 (separate from display)
bool nfcAvailable = false;

// ====================================
// DISPLAY & UI (v5.3)
// ====================================
DisplayManager display;
UIScreens ui;
TouchHandler touch;

// ====================================
// TIMING
// ====================================
unsigned long lastScan = 0;
unsigned long lastVitals = 0;
unsigned long lastHeartbeat = 0;
unsigned long lastProvisionAttempt = 0;
unsigned long lastNtpSync = 0;

// ====================================
// WAVEFORM STREAMING (v5.2)
// ====================================
unsigned long lastWaveformStream = 0;
uint32_t waveformSequenceCounter = 0;
unsigned long lastMicroBatch = 0;

// ====================================
// VITALS SEQUENCE COUNTER (v5.2.6)
// ====================================
uint32_t vitalsSequenceCounter = 0;

// Micro-batch waveform accumulator (GLOBAL to prevent stack overflow)
int32_t waveformAccumulator[8][50];  // 1,600 bytes global
int accumulatorIndex = 0;
int32_t microBatch[8][10];  // ✅ GLOBAL buffer - prevents 320-byte stack allocation

// ====================================
// SENSOR DATA - POPULATED FROM PHYSIOLOGICAL SIMULATOR
// ====================================
// ✅ v5.1: These variables are populated from PhysiologicalSimulator in loop()
// See lines 948-953: simulator.getHeartRate(), simulator.getTemperature(), etc.
float heartRate = 0;         // ✅ Read from simulator.getHeartRate()
float temperature = 0;       // ✅ Read from simulator.getTemperature()
int oxygenSat = 0;           // ✅ Read from simulator.getOxygenSaturation()
int batteryLevel = 100;      // Static for now (can add battery ADC later)
int respiratoryRate = 0;     // ✅ Read from simulator.getRespiratoryRate()
float quality = 0;           // ✅ Read from simulator.getSignalQuality()
int bloodPressureSystolic = 0;   // ✅ Read from simulator.getBloodPressureSystolic()
int bloodPressureDiastolic = 0;  // ✅ Read from simulator.getBloodPressureDiastolic()

// ====================================
// DEVICE MAINTENANCE
// ====================================
int batteryHealthPercentage = 100;
float batteryDrainRatePerHour = 0.0;
unsigned long lastBatteryUpdate = 0;
int lastBatteryLevel = 85;
int totalDisconnects = 0;
bool wasWifiConnected = false;
bool wasMqttConnected = false;
unsigned long disconnectTrackerLastCheck = 0;
unsigned long lastCommandReceivedAt = 0;
bool waveformCalibrationDue = false;

// ✅ v5.2.13: Non-blocking calibration tracking
bool calibrationRequested = false;
String calibrationCommandId = "";
unsigned long calibrationStartMillis = 0;

// ====================================
// ✅ v5.4: DEVICE CONFIGURATION (MQTT Commands Support)
// ====================================
// Configuration parameters (persisted to Preferences)
uint8_t displayBrightness = 100;           // 0-100%
bool waveformStreamingEnabled = true;      // Enable/disable ECG/EEG streaming
uint16_t samplingRate = 250;               // 100-1000 Hz
uint8_t vitalsTransmissionInterval = 5;   // 1-60 seconds
bool debugModeEnabled = false;             // Enable/disable debug logging
bool ledAlertsEnabled = true;              // Enable/disable LED visual alerts

// Alert thresholds (configurable per vital type)
struct AlertThreshold {
  float hrMin = 40.0;
  float hrMax = 120.0;
  float spo2Min = 90.0;
  float spo2Max = 100.0;
  float tempMin = 35.0;
  float tempMax = 38.5;
  float bpSysMin = 90.0;
  float bpSysMax = 140.0;
  float bpDiaMin = 60.0;
  float bpDiaMax = 90.0;
  float rrMin = 12.0;
  float rrMax = 20.0;
};
AlertThreshold alertThresholds;

// ====================================
// SYSTEM ALERTS
// ====================================
int consecutiveInvalidReadings = 0;
unsigned long lastValidReading = 0;
bool sensorMalfunctionAlertSent = false;

// ✅ v5.2.2: Alert spam prevention flags
bool frequentDisconnectsAlertSent = false;
bool deviceUnresponsiveAlertSent = false;

float heartRateHistory[5] = {0, 0, 0, 0, 0};
float spo2History[5] = {0, 0, 0, 0, 0};
float tempHistory[5] = {0, 0, 0, 0, 0};
int historyIndex = 0;

unsigned long lastAlertCheck = 0;

// ====================================
// ✅ v5.2.4: NON-BLOCKING LED STATE MACHINE (P1 fix)
// ====================================
enum LEDState {
  LED_OFF,
  LED_HIGH_ALERT,
  LED_MEDIUM_ALERT
};

LEDState currentLEDState = LED_OFF;
unsigned long ledStateStartTime = 0;
int ledFlashCount = 0;
bool ledOn = false;

// ====================================
// FORWARD DECLARATIONS
// ====================================
bool publishWithRetry(const char* topic, const char* payload, int maxRetries = 3);

// ====================================
// OFFLINE QUEUE (v5.2.1 - SPIFFS-based)
// ====================================
unsigned long lastQueueProcess = 0;

class OfflineQueue {
public:
  /**
   * Save vitals message to offline queue
   */
  bool saveVitals(String payload) {
    return saveToFile("/queue/vitals", payload);
  }

  /**
   * Save alert message to offline queue
   */
  bool saveAlert(String payload) {
    return saveToFile("/queue/alerts", payload);
  }

  /**
   * Save waveform message to offline queue
   */
  bool saveWaveform(String payload) {
    return saveToFile("/queue/waveforms", payload);
  }

  /**
   * Process all pending messages in offline queue (call when reconnected)
   */
  void processPendingMessages() {
    if (!mqttClient.connected()) {
      Serial.println("⚠️  Cannot process queue - MQTT disconnected");
      return;
    }

    Serial.println("📤 Processing offline queue...");

    // Process vitals queue
    sendBatch("/queue/vitals", "hospital/devices/" + deviceId + "/vitals");

    // Process alerts queue
    sendBatch("/queue/alerts", "hospital/devices/" + deviceId + "/alerts");

    // Process waveforms queue (lower priority)
    sendBatch("/queue/waveforms", "hospital/devices/" + deviceId + "/stream");

    Serial.println("✅ Offline queue processing complete");
  }

private:
  const int MAX_VITALS = 50;      // Keep up to 50 vitals messages (50 seconds)
  const int MAX_ALERTS = 20;      // Keep up to 20 alert messages
  const int MAX_WAVEFORMS = 10;   // Keep up to 10 waveform messages (1 second)

  /**
   * Save payload to queue directory
   * @param dir Queue directory (e.g., "/queue/vitals")
   * @param payload JSON payload to save
   */
  bool saveToFile(String dir, String payload) {
    if (!SPIFFS.begin(true)) {
      Serial.println("❌ SPIFFS mount failed - cannot save offline data");
      return false;
    }

    // Create directory if it doesn't exist
    if (!SPIFFS.exists(dir)) {
      // SPIFFS doesn't have mkdir, so we just create files with path
      Serial.println("📁 Creating queue directory: " + dir);
    }

    // Check file count and delete oldest if limit reached
    int fileCount = getFileCount(dir);
    int maxFiles = (dir.indexOf("vitals") >= 0) ? MAX_VITALS :
                   (dir.indexOf("alerts") >= 0) ? MAX_ALERTS : MAX_WAVEFORMS;

    if (fileCount >= maxFiles) {
      deleteOldestFile(dir);
    }

    // Save file with timestamp as filename
    String filename = dir + "/" + String(millis()) + ".json";
    File file = SPIFFS.open(filename, "w");
    if (!file) {
      Serial.println("❌ Failed to create queue file: " + filename);
      return false;
    }

    file.print(payload);
    file.close();

    Serial.println("💾 Queued offline: " + filename + " (" + String(payload.length()) + " bytes)");
    return true;
  }

  /**
   * Send all messages from a queue directory
   * @param queueDir Queue directory path
   * @param topic MQTT topic to publish to
   */
  bool sendBatch(String queueDir, String topic) {
    if (!SPIFFS.begin(true)) {
      return false;
    }

    File root = SPIFFS.open(queueDir, "r");
    if (!root || !root.isDirectory()) {
      return false;  // Queue empty or doesn't exist
    }

    int sentCount = 0;
    int failCount = 0;

    File file = root.openNextFile();
    while (file) {
      if (!file.isDirectory()) {
        String filename = String(file.name());
        String fullPath = queueDir + "/" + filename;  // ✅ v5.2.6: Build full path for SPIFFS
        String payload = file.readString();

        // Try to publish with retry
        if (publishWithRetry(topic.c_str(), payload.c_str(), 2)) {  // 2 retries for queued data
          // Success - delete file
          file.close();
          SPIFFS.remove(fullPath);  // ✅ v5.2.6: Use full path (was: filename only - BUG!)
          sentCount++;
          Serial.println("✅ Sent queued: " + filename + " (deleted)");
        } else {
          // Failed - keep file for next attempt
          failCount++;
          Serial.println("⚠️  Failed to send queued: " + filename);
          file.close();
          break;  // Stop processing on first failure
        }
      }

      file = root.openNextFile();
    }

    root.close();

    if (sentCount > 0) {
      Serial.println("📤 Sent " + String(sentCount) + " queued messages from " + queueDir);
    }
    if (failCount > 0) {
      Serial.println("⚠️  " + String(failCount) + " messages remain in " + queueDir);
    }

    return (failCount == 0);
  }

  /**
   * Get number of files in directory
   */
  int getFileCount(String dir) {
    if (!SPIFFS.begin(true)) {
      return 0;
    }

    File root = SPIFFS.open(dir, "r");
    if (!root || !root.isDirectory()) {
      return 0;
    }

    int count = 0;
    File file = root.openNextFile();
    while (file) {
      if (!file.isDirectory()) {
        count++;
      }
      file = root.openNextFile();
    }
    root.close();

    return count;
  }

  /**
   * Delete oldest file in directory (based on filename timestamp)
   */
  void deleteOldestFile(String dir) {
    if (!SPIFFS.begin(true)) {
      return;
    }

    File root = SPIFFS.open(dir, "r");
    if (!root || !root.isDirectory()) {
      return;
    }

    String oldestFile = "";
    unsigned long oldestTime = 0xFFFFFFFF;

    File file = root.openNextFile();
    while (file) {
      if (!file.isDirectory()) {
        String filename = String(file.name());
        // Extract timestamp from filename (e.g., "/queue/vitals/1234567890.json")
        int lastSlash = filename.lastIndexOf('/');
        int dotJson = filename.lastIndexOf('.');
        if (lastSlash >= 0 && dotJson > lastSlash) {
          String timestampStr = filename.substring(lastSlash + 1, dotJson);
          unsigned long timestamp = timestampStr.toInt();
          if (timestamp < oldestTime) {
            oldestTime = timestamp;
            oldestFile = filename;
          }
        }
      }
      file = root.openNextFile();
    }
    root.close();

    if (oldestFile.length() > 0) {
      SPIFFS.remove(oldestFile);
      Serial.println("🗑️  Deleted oldest queued file: " + oldestFile);
    }
  }
};

// Global offline queue instance
OfflineQueue offlineQueue;

// ====================================
// ✅ MQTT PUBLISH HELPER (Reduces code duplication)
// Template version - no std::function overhead
// MUST be declared AFTER offlineQueue
// ====================================
template<typename PayloadBuilder>
bool publishMessage(String topic, PayloadBuilder buildPayload, bool queueOffline = true) {
  // 1. Build JSON payload with common fields
  JsonDocument doc;
  doc["timestamp"] = getISO8601Timestamp();
  doc["deviceId"] = deviceId;

  // 2. Let caller add custom fields via lambda
  buildPayload(doc);

  // 3. Serialize to string
  String payload;
  serializeJson(doc, payload);

  // 4. Check connection and queue if offline
  if (!mqttClient.connected() || !isAssigned) {
    if (queueOffline) {
      Serial.println("⚠️  MQTT disconnected - queuing offline: " + topic);
      // Route to appropriate queue based on topic
      if (topic.indexOf("/vitals") > 0) {
        offlineQueue.saveVitals(payload);
      } else if (topic.indexOf("/alerts") > 0) {
        offlineQueue.saveAlert(payload);
      } else if (topic.indexOf("/stream") > 0) {
        offlineQueue.saveWaveform(payload);
      }
    }
    return false;
  }

  // 5. Publish with retry
  return publishWithRetry(topic.c_str(), payload.c_str());
}

// ====================================
// CERTIFICATE MANAGEMENT (v5.0.0)
// ====================================

/**
 * Check if device has provisioned certificates
 */
bool hasCertificates() {
  if (!SPIFFS.begin(true)) {
    Serial.println("❌ SPIFFS mount failed");
    return false;
  }

  bool certExists = SPIFFS.exists("/device.crt");
  bool keyExists = SPIFFS.exists("/device.key");

  if (certExists && keyExists) {
    Serial.println("✅ Device certificates found in SPIFFS");
    return true;
  }

  Serial.println("⚠️  Device certificates NOT found - provisioning required");
  return false;
}

/**
 * Load device certificate and private key from SPIFFS
 */
bool loadDeviceCertificate(String& cert, String& key) {
  if (!SPIFFS.begin(true)) {
    Serial.println("❌ SPIFFS mount failed");
    return false;
  }

  File certFile = SPIFFS.open("/device.crt", "r");
  if (!certFile) {
    Serial.println("❌ Device certificate file not found");
    return false;
  }
  cert = certFile.readString();
  certFile.close();

  File keyFile = SPIFFS.open("/device.key", "r");
  if (!keyFile) {
    Serial.println("❌ Device private key file not found");
    return false;
  }
  key = keyFile.readString();
  keyFile.close();

  if (cert.length() == 0 || key.length() == 0) {
    Serial.println("❌ Device certificate or key is empty");
    return false;
  }

  Serial.println("✅ Device certificate loaded (" + String(cert.length()) + " bytes)");
  Serial.println("✅ Device private key loaded (" + String(key.length()) + " bytes)");
  return true;
}

/**
 * Save device certificate and private key to SPIFFS
 */
bool saveCertificates(String cert, String key) {
  if (!SPIFFS.begin(true)) {
    Serial.println("❌ SPIFFS mount failed");
    return false;
  }

  File certFile = SPIFFS.open("/device.crt", "w");
  if (!certFile) {
    Serial.println("❌ Failed to open device certificate file for writing");
    return false;
  }
  certFile.print(cert);
  certFile.close();

  File keyFile = SPIFFS.open("/device.key", "w");
  if (!keyFile) {
    Serial.println("❌ Failed to open device private key file for writing");
    return false;
  }
  keyFile.print(key);
  keyFile.close();

  Serial.println("✅ Device certificates saved to SPIFFS");
  return true;
}

// ====================================
// SPIFFS CA CERTIFICATE LOADER
// ====================================
bool loadCACertificate() {
  if (!SPIFFS.begin(true)) {
    Serial.println("❌ SPIFFS mount failed");
    return false;
  }

  File file = SPIFFS.open(CA_CERT_PATH, "r");
  if (!file) {
    Serial.println("❌ CA certificate file not found: " + String(CA_CERT_PATH));
    Serial.println("💡 Please upload ca.crt to SPIFFS");
    return false;
  }

  caCertificate = file.readString();
  file.close();

  if (caCertificate.length() == 0) {
    Serial.println("❌ CA certificate file is empty");
    return false;
  }

  Serial.println("✅ CA certificate loaded from SPIFFS (" + String(caCertificate.length()) + " bytes)");
  return true;
}

// ====================================
// ISO 8601 TIMESTAMP GENERATION
// ====================================
String getISO8601Timestamp() {
  if (!ntpSynced) {
    Serial.println("⚠️ Time not synced! Using millis() fallback");
    return String(millis());
  }

  time_t now = time(nullptr);
  struct tm timeinfo;
  gmtime_r(&now, &timeinfo);

  char iso_timestamp[25];
  int milliseconds = (millis() % 1000);
  snprintf(iso_timestamp, sizeof(iso_timestamp),
           "%04d-%02d-%02dT%02d:%02d:%02d.%03dZ",
           timeinfo.tm_year + 1900,
           timeinfo.tm_mon + 1,
           timeinfo.tm_mday,
           timeinfo.tm_hour,
           timeinfo.tm_min,
           timeinfo.tm_sec,
           milliseconds);

  return String(iso_timestamp);
}

// ====================================
// DISPLAY BRIGHTNESS CONTROL (v5.3)
// ====================================
void setDisplayBrightness(uint8_t level) {
  // ✅ v5.4: Map 0-100% to 0-255 for hardware
  uint8_t hwLevel = map(level, 0, 100, 0, 255);
  display.setBrightness(hwLevel);
  Serial.printf("🔆 Display brightness set to %d%% (hardware: %d/255)\n", level, hwLevel);
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
    if (now > 1000000000) {
      ntpSynced = true;
      struct tm timeinfo;
      localtime_r(&now, &timeinfo);
      Serial.println("✅ NTP synced: " + String(asctime(&timeinfo)));
      lastNtpSync = millis();

      // ✅ v5.3: Update UI with sync status
      ui.updateConnectionStatus(true, mqttClient.connected(), ntpSynced);
      return;
    }
    delay(500);
    attempts++;
    Serial.print(".");
  }

  Serial.println("\n⚠️ NTP sync failed - timestamps will be degraded!");
  // ✅ v5.3: Update UI with sync failure
  ui.updateConnectionStatus(wifiConnected, mqttClient.connected(), false);
}

// ====================================
// ALERT SYSTEM
// ====================================
void sendAlert(String alertType, String severity, String message, float confidence) {
  // ✅ v5.4: Refactored to use publishMessage() helper
  String topic = "hospital/devices/" + deviceId + "/alerts";

  // Publish using helper template (handles connection check, retry, offline queueing)
  bool success = publishMessage(topic, [&](JsonDocument& doc) {
    doc["alertType"] = alertType;
    doc["severity"] = severity;
    doc["message"] = message;
    doc["source"] = "Watch";
    doc["confidence"] = confidence;
    doc["patientId"] = assignedPatientId;
    doc["category"] = "device";
  });

  // Always flash LED locally regardless of MQTT status
  String severityUpper = severity;
  severityUpper.toUpperCase();

  if (success) {
    Serial.println("🚨 [" + severityUpper + "] " + alertType);
  } else {
    Serial.println("⚠️  Alert queued offline: [" + severityUpper + "] " + alertType);
  }

  flashAlertPattern(severity);
}

// ✅ v5.2.4: Start LED alert pattern (non-blocking trigger)
void flashAlertPattern(String severity) {
  // Trigger the LED state machine (non-blocking)
  if (severity == "high") {
    currentLEDState = LED_HIGH_ALERT;
    ledFlashCount = 0;
    ledOn = false;
    ledStateStartTime = millis();
  } else if (severity == "medium") {
    currentLEDState = LED_MEDIUM_ALERT;
    ledFlashCount = 0;
    ledOn = false;
    ledStateStartTime = millis();
  }
}

// ✅ v5.2.4: Update LED state machine (non-blocking - call from loop())
void updateLEDFlasher() {
  if (currentLEDState == LED_OFF) return;

  unsigned long currentTime = millis();
  unsigned long elapsed = (unsigned long)(currentTime - ledStateStartTime);

  if (currentLEDState == LED_HIGH_ALERT) {
    // High alert: 6 flashes, 100ms on/off (200ms cycle)
    if (ledFlashCount >= 6) {
      currentLEDState = LED_OFF;
      digitalWrite(2, LOW);
      return;
    }

    if (!ledOn && elapsed >= 0) {
      // Turn LED on
      digitalWrite(2, HIGH);
      ledOn = true;
      ledStateStartTime = currentTime;
    } else if (ledOn && elapsed >= 100) {
      // Turn LED off after 100ms
      digitalWrite(2, LOW);
      ledOn = false;
      ledFlashCount++;
      ledStateStartTime = currentTime;
    }
  } else if (currentLEDState == LED_MEDIUM_ALERT) {
    // Medium alert: 3 flashes, 300ms on/off (600ms cycle)
    if (ledFlashCount >= 3) {
      currentLEDState = LED_OFF;
      digitalWrite(2, LOW);
      return;
    }

    if (!ledOn && elapsed >= 0) {
      // Turn LED on
      digitalWrite(2, HIGH);
      ledOn = true;
      ledStateStartTime = currentTime;
    } else if (ledOn && elapsed >= 300) {
      // Turn LED off after 300ms
      digitalWrite(2, LOW);
      ledOn = false;
      ledFlashCount++;
      ledStateStartTime = currentTime;
    }
  }
}

// ====================================
// DEVICE-LEVEL ALERTS
// ====================================
void checkBatteryAlerts() {
  if (batteryLevel < 10) {
    sendAlert("criticalBatteryLevel", "high", "CRITICAL BATTERY - " + String(batteryLevel) + "%", 1.0);
  } else if (batteryLevel < 20) {
    sendAlert("lowBatteryWarning", "medium", "LOW BATTERY - " + String(batteryLevel) + "%", 0.95);
  }

  if (batteryHealthPercentage < 70) {
    sendAlert("batteryDegradation", "medium", "BATTERY HEALTH - " + String(batteryHealthPercentage) + "%", 0.85);
  }
}

void updateBatteryHealth() {
  if (batteryLevel < 5 && lastBatteryLevel >= 5) {
    batteryHealthPercentage = max(0, batteryHealthPercentage - 1);
    prefs.putInt("batHealth", batteryHealthPercentage);
  }

  // ✅ v5.2.4: Fix millis() overflow with unsigned long cast
  unsigned long timeDiff = (unsigned long)(millis() - lastBatteryUpdate);
  if (timeDiff > 3600000) {
    int batteryDiff = lastBatteryLevel - batteryLevel;
    batteryDrainRatePerHour = (float)batteryDiff / (timeDiff / 3600000.0);
    lastBatteryUpdate = millis();
    lastBatteryLevel = batteryLevel;
  }
}

void checkConnectivityAlerts() {
  // ✅ v5.2.2: Bug #6 fix - Only send frequentDisconnects alert ONCE (spam prevention)
  if (totalDisconnects >= 5 && !frequentDisconnectsAlertSent) {
    sendAlert("frequentDisconnects", "medium", "DISCONNECTS - " + String(totalDisconnects) + "x", 0.9);
    frequentDisconnectsAlertSent = true;  // Prevent repeated alerts
  }

  // ✅ v5.2.2: Bug #5 fix - Only send deviceUnresponsive alert ONCE (spam prevention)
  // ✅ v5.2.4: Fix millis() overflow with unsigned long cast
  if (lastCommandReceivedAt > 0 && (unsigned long)(millis() - lastCommandReceivedAt) > 600000 && !deviceUnresponsiveAlertSent) {
    sendAlert("deviceUnresponsive", "high", "UNRESPONSIVE - " + String((unsigned long)(millis() - lastCommandReceivedAt) / 60000) + " min", 0.95);
    deviceUnresponsiveAlertSent = true;  // Prevent repeated alerts
  }
}

void trackConnectivity() {
  unsigned long now = millis();
  // ✅ v5.2.4: Fix millis() overflow with unsigned long cast
  if ((unsigned long)(now - disconnectTrackerLastCheck) < 1000) return;
  disconnectTrackerLastCheck = now;

  bool currentWifiState = (WiFi.status() == WL_CONNECTED);
  if (wasWifiConnected && !currentWifiState) {
    totalDisconnects++;
    // ✅ v5.2.2: Bug #2 fix - REMOVED prefs.putInt() - counter should NOT persist across reboots
  }
  wasWifiConnected = currentWifiState;

  bool currentMqttState = mqttClient.connected();
  if (wasMqttConnected && !currentMqttState && isProvisioned) {
    totalDisconnects++;
    // ✅ v5.2.2: Bug #2 fix - REMOVED prefs.putInt() - counter should NOT persist across reboots
  }
  wasMqttConnected = currentMqttState;
}

bool isValidReading(float hr, float spo2, float temp) {
  return (hr > 0 && hr <= 300 && spo2 > 0 && spo2 <= 100 && temp >= 80 && temp <= 115);
}

void checkSystemAlerts() {
  if (!isValidReading(heartRate, oxygenSat, temperature)) {
    consecutiveInvalidReadings++;
    if (consecutiveInvalidReadings >= 3 && !sensorMalfunctionAlertSent) {
      sendAlert("sensorMalfunction", "high", "SENSOR FAIL - " + String(consecutiveInvalidReadings) + " invalid", 0.95);
      sensorMalfunctionAlertSent = true;
    }
  } else {
    consecutiveInvalidReadings = 0;
    sensorMalfunctionAlertSent = false;
    lastValidReading = millis();
  }

  // ✅ v5.2.4: Fix millis() overflow with unsigned long cast
  if ((unsigned long)(millis() - lastValidReading) > 300000) {
    sendAlert("communicationFailure", "high", "COMM FAIL - 5+ min", 1.0);
  }

  float hrVariation = abs(heartRate - heartRateHistory[0]);
  if (hrVariation > 50 && heartRate > 0) {
    sendAlert("dataQualityIssue", "low", "DATA QUALITY - HR spike " + String(hrVariation), 0.7);
  }
}

void runAlertEngine() {
  if (!isAssigned) return;

  checkBatteryAlerts();
  checkConnectivityAlerts();
  checkSystemAlerts();
}

void updateSensorHistory() {
  heartRateHistory[historyIndex] = heartRate;
  spo2History[historyIndex] = oxygenSat;
  tempHistory[historyIndex] = temperature;
  historyIndex = (historyIndex + 1) % 5;
}

// ====================================
// MQTT PUBLISH WITH QoS & RETRY (v5.2.1)
// ====================================
/**
 * Publish MQTT message with QoS 1 and exponential backoff retry
 * @param topic MQTT topic
 * @param payload JSON payload
 * @param maxRetries Maximum retry attempts (default: 3)
 * @return true if published successfully, false if all retries failed
 */
bool publishWithRetry(const char* topic, const char* payload, int maxRetries) {
  for (int attempt = 0; attempt < maxRetries; attempt++) {
    // Publish with QoS 1 (at least once delivery, requires broker ACK)
    // PubSubClient::publish signature: (topic, payload, length, retained)
    // Note: PubSubClient doesn't support QoS parameter directly, using boolean publish for simplicity
    if (mqttClient.publish(topic, (const uint8_t*)payload, strlen(payload), false)) {
      if (attempt > 0) {
        Serial.println("✅ MQTT publish succeeded on retry " + String(attempt + 1));
      }
      return true;
    }

    // Exponential backoff: 100ms, 200ms, 400ms
    if (attempt < maxRetries - 1) {
      unsigned long backoff = 100 * (1 << attempt);
      delay(backoff);
      Serial.println("⚠️  MQTT publish retry " + String(attempt + 1) + "/" + String(maxRetries) + " (backoff: " + String(backoff) + "ms)");
    }
  }

  Serial.println("❌ MQTT publish FAILED after " + String(maxRetries) + " attempts - will queue for offline storage");
  return false;
}

// ====================================
// COMMAND HANDLERS
// ====================================
void sendCommandAck(String commandId, bool success, String msg) {
  sendCommandAck(commandId, success, msg, "");  // Call overloaded version with empty data
}

// ✅ v5.4: Overloaded version with optional data parameter (for status responses)
void sendCommandAck(String commandId, bool success, String msg, String data) {
  if (!mqttClient.connected()) return;

  String topic = "hospital/devices/" + deviceId + "/ack";
  JsonDocument doc;
  doc["commandId"] = commandId;
  doc["timestamp"] = getISO8601Timestamp();
  doc["status"] = success ? "success" : "error";
  doc["message"] = msg;

  // ✅ v5.4: Include data field if provided (for status responses)
  if (data.length() > 0) {
    JsonDocument dataDoc;
    if (deserializeJson(dataDoc, data) == DeserializationError::Ok) {
      doc["data"] = dataDoc;
    }
  }

  String payload;
  serializeJson(doc, payload);
  publishWithRetry(topic.c_str(), payload.c_str());  // ✅ v5.2.1: QoS 1 with retry
}

void handlePingCommand(String commandId) {
  sendCommandAck(commandId, true, "Pong");
}

void handleWaveformCalibrationCommand(String commandId) {
  Serial.println("🔧 Waveform calibration command received");

  // ✅ v5.2.13: NON-BLOCKING calibration - set flags and return immediately
  // PhysiologicalSimulator will generate calibration waveforms for next 3 seconds
  // loop() will detect completion and publish result
  simulator.startCalibrationPulse();
  calibrationRequested = true;
  calibrationCommandId = commandId;
  calibrationStartMillis = millis();

  // Flash LED briefly (200ms total - acceptable blocking for visual feedback)
  for (int i = 0; i < 2; i++) {
    digitalWrite(2, HIGH);
    delay(50);
    digitalWrite(2, LOW);
    delay(50);
  }

  waveformCalibrationDue = false;

  // Send immediate acknowledgment (calibration started)
  sendCommandAck(commandId, true, "Waveform calibration started (3000ms non-blocking)");

  Serial.println("✅ Waveform calibration started - waveforms will stream during calibration");
  digitalWrite(2, HIGH);
}

// ====================================
// ✅ v5.4: NEW DEVICE COMMAND HANDLERS
// ====================================

// 1. Display Brightness Control
void handleDisplayBrightnessCommand(String commandId, JsonDocument& doc) {
  if (!doc["brightness"].is<int>()) {
    sendCommandAck(commandId, false, "Missing or invalid 'brightness' parameter");
    return;
  }

  int brightness = doc["brightness"];
  if (brightness < 0 || brightness > 100) {
    sendCommandAck(commandId, false, "Brightness must be 0-100");
    return;
  }

  displayBrightness = (uint8_t)brightness;

  // Apply to display
  uint8_t lvl = map(displayBrightness, 0, 100, 0, 255);
  display.setBrightness(lvl);

  // Save to Preferences
  prefs.putUChar("disp_bright", displayBrightness);

  String msg = "Display brightness set to " + String(displayBrightness) + "%";
  sendCommandAck(commandId, true, msg);
  Serial.println("💡 " + msg);
}

// 2. Waveform Streaming Control
void handleWaveformStreamingCommand(String commandId, JsonDocument& doc) {
  if (!doc["enabled"].is<bool>()) {
    sendCommandAck(commandId, false, "Missing or invalid 'enabled' parameter");
    return;
  }

  waveformStreamingEnabled = doc["enabled"];
  prefs.putBool("wf_stream", waveformStreamingEnabled);

  String msg = waveformStreamingEnabled ? "Waveform streaming enabled" : "Waveform streaming disabled";
  sendCommandAck(commandId, true, msg);
  Serial.println("📊 " + msg);
}

// 3. Sampling Rate Control
void handleSamplingRateCommand(String commandId, JsonDocument& doc) {
  if (!doc["rate"].is<int>()) {
    sendCommandAck(commandId, false, "Missing or invalid 'rate' parameter");
    return;
  }

  int rate = doc["rate"];
  if (rate < 100 || rate > 1000) {
    sendCommandAck(commandId, false, "Sampling rate must be 100-1000 Hz");
    return;
  }

  samplingRate = (uint16_t)rate;
  prefs.putUShort("samp_rate", samplingRate);

  // Note: PhysiologicalSimulator uses fixed internal sampling rate
  // This value is stored for future use / display purposes only
  // simulator.setSamplingRate(samplingRate);  // Method not available

  String msg = "Sampling rate set to " + String(samplingRate) + " Hz (stored for future use)";
  sendCommandAck(commandId, true, msg);
  Serial.println("⏱️  " + msg);
}

// 4. Vitals Transmission Interval Control
void handleVitalsIntervalCommand(String commandId, JsonDocument& doc) {
  if (!doc["interval"].is<int>()) {
    sendCommandAck(commandId, false, "Missing or invalid 'interval' parameter");
    return;
  }

  int interval = doc["interval"];
  if (interval < 1 || interval > 60) {
    sendCommandAck(commandId, false, "Interval must be 1-60 seconds");
    return;
  }

  vitalsTransmissionInterval = (uint8_t)interval;
  prefs.putUChar("vitals_int", vitalsTransmissionInterval);

  String msg = "Vitals transmission interval set to " + String(vitalsTransmissionInterval) + "s";
  sendCommandAck(commandId, true, msg);
  Serial.println("⏰ " + msg);
}

// 5. Debug Mode Control
void handleDebugModeCommand(String commandId, JsonDocument& doc) {
  if (!doc["enabled"].is<bool>()) {
    sendCommandAck(commandId, false, "Missing or invalid 'enabled' parameter");
    return;
  }

  debugModeEnabled = doc["enabled"];
  prefs.putBool("debug_mode", debugModeEnabled);

  String msg = debugModeEnabled ? "Debug mode enabled" : "Debug mode disabled";
  sendCommandAck(commandId, true, msg);
  Serial.println("🐛 " + msg);
}

// 6. Alert Threshold Configuration
void handleAlertThresholdCommand(String commandId, JsonDocument& doc) {
  if (!doc["vitalType"].is<String>() || !doc["min"].is<float>() || !doc["max"].is<float>()) {
    sendCommandAck(commandId, false, "Missing parameters: vitalType, min, max");
    return;
  }

  String vitalType = doc["vitalType"].as<String>();
  float min = doc["min"];
  float max = doc["max"];

  if (min >= max) {
    sendCommandAck(commandId, false, "min must be less than max");
    return;
  }

  // Update thresholds based on vital type
  if (vitalType == "heartRate") {
    alertThresholds.hrMin = min;
    alertThresholds.hrMax = max;
    prefs.putFloat("hr_min", min);
    prefs.putFloat("hr_max", max);
  } else if (vitalType == "spo2") {
    alertThresholds.spo2Min = min;
    alertThresholds.spo2Max = max;
    prefs.putFloat("spo2_min", min);
    prefs.putFloat("spo2_max", max);
  } else if (vitalType == "temperature") {
    alertThresholds.tempMin = min;
    alertThresholds.tempMax = max;
    prefs.putFloat("temp_min", min);
    prefs.putFloat("temp_max", max);
  } else if (vitalType == "bpSystolic") {
    alertThresholds.bpSysMin = min;
    alertThresholds.bpSysMax = max;
    prefs.putFloat("bpsys_min", min);
    prefs.putFloat("bpsys_max", max);
  } else if (vitalType == "bpDiastolic") {
    alertThresholds.bpDiaMin = min;
    alertThresholds.bpDiaMax = max;
    prefs.putFloat("bpdia_min", min);
    prefs.putFloat("bpdia_max", max);
  } else if (vitalType == "respiratoryRate") {
    alertThresholds.rrMin = min;
    alertThresholds.rrMax = max;
    prefs.putFloat("rr_min", min);
    prefs.putFloat("rr_max", max);
  } else {
    sendCommandAck(commandId, false, "Invalid vitalType: " + vitalType);
    return;
  }

  String msg = "Alert threshold for " + vitalType + " set to [" + String(min, 1) + ", " + String(max, 1) + "]";
  sendCommandAck(commandId, true, msg);
  Serial.println("🚨 " + msg);
}

// 7. LED Alerts Control
void handleLEDAlertsCommand(String commandId, JsonDocument& doc) {
  if (!doc["enabled"].is<bool>()) {
    sendCommandAck(commandId, false, "Missing or invalid 'enabled' parameter");
    return;
  }

  ledAlertsEnabled = doc["enabled"];
  prefs.putBool("led_alerts", ledAlertsEnabled);

  // Turn off LED if alerts disabled
  if (!ledAlertsEnabled) {
    digitalWrite(2, LOW);
    currentLEDState = LED_OFF;
  }

  String msg = ledAlertsEnabled ? "LED alerts enabled" : "LED alerts disabled";
  sendCommandAck(commandId, true, msg);
  Serial.println("💡 " + msg);
}

// 8. Device Status Request
void handleDeviceStatusCommand(String commandId) {
  JsonDocument statusDoc;

  // Battery info
  statusDoc["battery"]["level"] = batteryLevel;
  statusDoc["battery"]["health"] = batteryHealthPercentage;
  statusDoc["battery"]["drainRate"] = batteryDrainRatePerHour;

  // Memory info
  statusDoc["memory"]["free"] = ESP.getFreeHeap();
  statusDoc["memory"]["total"] = ESP.getHeapSize();
  statusDoc["memory"]["used"] = ESP.getHeapSize() - ESP.getFreeHeap();
  statusDoc["memory"]["usagePercent"] = ((ESP.getHeapSize() - ESP.getFreeHeap()) * 100) / ESP.getHeapSize();

  // Uptime
  statusDoc["uptime"]["seconds"] = millis() / 1000;
  statusDoc["uptime"]["days"] = (millis() / 1000) / 86400;
  statusDoc["uptime"]["hours"] = ((millis() / 1000) % 86400) / 3600;
  statusDoc["uptime"]["minutes"] = (((millis() / 1000) % 86400) % 3600) / 60;

  // Connectivity
  statusDoc["connectivity"]["wifi"] = wifiConnected;
  statusDoc["connectivity"]["mqtt"] = mqttClient.connected();
  statusDoc["connectivity"]["ntp"] = ntpSynced;
  statusDoc["connectivity"]["disconnects"] = totalDisconnects;

  // Configuration
  statusDoc["config"]["brightness"] = displayBrightness;
  statusDoc["config"]["waveformStreaming"] = waveformStreamingEnabled;
  statusDoc["config"]["samplingRate"] = samplingRate;
  statusDoc["config"]["vitalsInterval"] = vitalsTransmissionInterval;
  statusDoc["config"]["debugMode"] = debugModeEnabled;
  statusDoc["config"]["ledAlerts"] = ledAlertsEnabled;

  // Current vitals
  statusDoc["vitals"]["heartRate"] = heartRate;
  statusDoc["vitals"]["spo2"] = oxygenSat;
  statusDoc["vitals"]["temperature"] = temperature;
  statusDoc["vitals"]["respiratoryRate"] = respiratoryRate;
  statusDoc["vitals"]["bpSystolic"] = bloodPressureSystolic;
  statusDoc["vitals"]["bpDiastolic"] = bloodPressureDiastolic;

  // Device info
  statusDoc["device"]["id"] = deviceId;
  statusDoc["device"]["mac"] = macAddress;
  statusDoc["device"]["patientId"] = assignedPatientId;
  statusDoc["device"]["assigned"] = isAssigned;

  String statusJson;
  serializeJson(statusDoc, statusJson);

  sendCommandAck(commandId, true, "Device status retrieved", statusJson);
  Serial.println("📊 Device status sent");
}

// 9. Clear Offline Queue
void handleClearOfflineQueueCommand(String commandId) {
  // Clear SPIFFS queue files
  File root = SPIFFS.open("/");
  if (!root || !root.isDirectory()) {
    sendCommandAck(commandId, false, "Failed to open SPIFFS root");
    return;
  }

  int filesCleared = 0;
  File file = root.openNextFile();
  while (file) {
    String fileName = file.name();
    if (fileName.startsWith("/queue_") && fileName.endsWith(".json")) {
      SPIFFS.remove(fileName);
      filesCleared++;
    }
    file = root.openNextFile();
  }

  String msg = "Cleared " + String(filesCleared) + " queued messages from SPIFFS";
  sendCommandAck(commandId, true, msg);
  Serial.println("🗑️  " + msg);
}

// 10. Sync Time (Force NTP)
void handleSyncTimeCommand(String commandId) {
  Serial.println("🕐 Force NTP sync requested");

  configTime(GMT_OFFSET_SEC, DAYLIGHT_OFFSET_SEC, "pool.ntp.org", "time.nist.gov");

  // Wait up to 5 seconds for sync
  unsigned long syncStart = millis();
  while (time(nullptr) < 100000 && (millis() - syncStart) < 5000) {
    delay(100);
  }

  time_t now = time(nullptr);
  if (now > 100000) {
    ntpSynced = true;
    String timeStr = String(ctime(&now));
    timeStr.trim();
    sendCommandAck(commandId, true, "NTP sync successful: " + timeStr);
    Serial.println("✅ NTP synced: " + timeStr);
  } else {
    sendCommandAck(commandId, false, "NTP sync failed - timeout");
    Serial.println("❌ NTP sync timeout");
  }
}

// 11. Waveform Mode Switch (ECG/EEG)
void handleWaveformModeCommand(String commandId, JsonDocument& doc) {
  if (!doc["mode"].is<String>()) {
    sendCommandAck(commandId, false, "Missing or invalid 'mode' parameter");
    return;
  }

  String mode = doc["mode"].as<String>();

  if (mode == "ECG") {
    simulator.setMode(PhysiologicalSimulator::MODE_ECG);
    prefs.putBool("wf_mode_ecg", true);
    sendCommandAck(commandId, true, "Switched to ECG mode");
    Serial.println("❤️  Switched to ECG mode");
  } else if (mode == "EEG") {
    simulator.setMode(PhysiologicalSimulator::MODE_EEG);
    prefs.putBool("wf_mode_ecg", false);
    sendCommandAck(commandId, true, "Switched to EEG mode");
    Serial.println("🧠 Switched to EEG mode");
  } else {
    sendCommandAck(commandId, false, "Invalid mode: " + mode + " (must be 'ECG' or 'EEG')");
  }
}

// 12. Device Reboot
void handleRebootCommand(String commandId) {
  sendCommandAck(commandId, true, "Rebooting device in 2 seconds...");
  Serial.println("🔄 REBOOT COMMAND RECEIVED - Rebooting in 2s");

  delay(2000);  // Give time for ACK to be sent
  ESP.restart();
}

// 13. Unassign Device
void handleUnassignCommand(String commandId) {
  assignedPatientId = "";
  isAssigned = false;
  prefs.putString("patient_id", "");
  prefs.putBool("is_assigned", false);

  sendCommandAck(commandId, true, "Device unassigned from patient");
  Serial.println("👤 Device unassigned");
}

// 14. Custom Command (Extensible)
void handleCustomCommand(String commandId, JsonDocument& doc) {
  String action = doc["action"].as<String>();
  String params = doc["params"].as<String>();

  String msg = "Custom command received: action=" + action + ", params=" + params;
  sendCommandAck(commandId, true, msg);
  Serial.println("🔧 " + msg);

  // Add custom command logic here as needed
}

// ====================================
// SETUP
// ====================================
void setup() {
  Serial.begin(115200);

  // ✅ Enable verbose logging for TLS debugging
  esp_log_level_set("*", ESP_LOG_VERBOSE);

  // ✅ Use version constants for startup banner
  Serial.printf("\n🏥 ESP32 Hospital Watch v%s (%s)\n", FIRMWARE_VERSION, VERSION_NAME);
  Serial.println("====================================================================");
  Serial.println("✨ MQTT TLS 1.2 | mTLS Auth | QoS 1 Retry | Offline Buffering | 500Hz Streaming");
  Serial.println("🔄 Auto WiFi Reconnect | Bug Fixes: Offline queue, alert spam, disconnect counter");
  Serial.println("✅ P0: Patient monitoring NEVER stops | P1: millis() overflow + non-blocking LED");
  Serial.printf("✅ v%s: %s\n", FIRMWARE_VERSION, VERSION_FEATURES);
#ifdef ARDUINO_ESP32_RELEASE
  Serial.printf("🔧 Arduino Core: %s\n", ARDUINO_ESP32_RELEASE);
#else
  Serial.println("🔧 Arduino Core: Version unknown (pre-2.0)");
#endif

  pinMode(2, OUTPUT);
  digitalWrite(2, LOW);

  // Configure mode selection GPIO pin
  pinMode(MODE_SELECT_PIN, INPUT_PULLUP);
  bool initialMode = digitalRead(MODE_SELECT_PIN) == HIGH;
  Serial.println("🔌 GPIO " + String(MODE_SELECT_PIN) + " configured for mode selection");
  Serial.println("   Current mode: " + String(initialMode ? "ECG" : "EEG") + " (HIGH=ECG, LOW=EEG)");

  Serial.println("📂 Loading CA certificate from SPIFFS...");
  if (!loadCACertificate()) {
    Serial.println("⚠️ WARNING: CA certificate not loaded - TLS will fail!");
    for (int i = 0; i < 10; i++) {
      digitalWrite(2, HIGH);
      delay(50);
      digitalWrite(2, LOW);
      delay(50);
    }
  }

  WiFi.mode(WIFI_STA);
  WiFi.begin();
  delay(100);

  macAddress = WiFi.macAddress();
  Serial.println("📱 MAC Address: " + macAddress);

  WiFi.disconnect();
  WiFi.mode(WIFI_OFF);

  prefs.begin("hospital", false);
  loadConfiguration();

  if (wifiSSID.length() > 0) {
    connectToWiFi();
    if (wifiConnected) {
      syncNTPTime();
      // ✅ v5.0: Check for certificates before connecting to MQTT
      if (isProvisioned && hasCertificates()) {
        setupMQTT();
      } else if (isProvisioned && !hasCertificates()) {
        Serial.println("⚠️  Device marked as provisioned but certificates missing!");
        Serial.println("⚠️  Clearing WiFi and resetting to captive portal...");
        mqttConfigured = false;  // ✅ v5.0.3: Reset flag when certs missing
        isProvisioned = false;

        // ✅ v5.0.1: Clear WiFi credentials to force captive portal
        wifiSSID = "";
        wifiPassword = "";
        serverIP = "";
        prefs.remove("ssid");
        prefs.remove("pass");
        prefs.remove("ip");
        prefs.remove("prov_code");
        saveConfiguration();

        Serial.println("⚠️  Restarting to captive portal...");
        delay(2000);
        ESP.restart();
      }
    }
  } else {
    startCaptivePortal();
  }

  wasWifiConnected = wifiConnected;
  wasMqttConnected = mqttClient.connected();
  lastBatteryUpdate = millis();
  lastValidReading = millis();

  // ✅ v5.1: Initialize physiological simulator
  simulator.begin();

  // ✅ v5.2.9: Set simulator mode based on GPIO pin
  bool initialECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;
  simulator.setMode(initialECGMode ? PhysiologicalSimulator::MODE_ECG : PhysiologicalSimulator::MODE_EEG);
  Serial.println("✅ Simulator mode set to: " + String(initialECGMode ? "ECG" : "EEG"));

  // ✅ v5.3: Initialize LVGL display subsystem
  Serial.println("🖥️  Initializing LVGL display...");
  if (display.init()) {
    Serial.println("✅ LVGL display initialized");
    ui.init();
    Serial.println("✅ UI manager initialized");
    touch.init(&ui);  // ✅ v5.4: Initialize touch handler for swipe gestures
    Serial.println("✅ Touch handler initialized (swipe navigation enabled)");
  } else {
    Serial.println("⚠️  Display initialization failed");
  }

  // ✅ v5.3: Initialize NFC module on I2C Bus 1 (separate from display touch)
  Serial.println("📡 Initializing NFC module on I2C Bus 1...");
  if (nfc.begin()) {
    nfcAvailable = true;
    Serial.println("✅ NFC module initialized (PN532 ready on I2C Bus 1)");
  } else {
    nfcAvailable = false;
    Serial.println("⚠️  NFC module not found (optional - system will work without it)");
    Serial.println("   To enable NFC:");
    Serial.println("   - Connect PN532 to I2C Bus 1: SDA=GPIO16, SCL=GPIO17, IRQ=GPIO25");
    Serial.println("   - Set DIP switches to I2C mode (OFF, ON)");
    Serial.println("   - Note: Display uses I2C Bus 0 (GPIO21/22)");
  }

  // ✅ v5.4: Initialize real IMU for fall & tremor detection
  Serial.println("\n🔧 Initializing QMI8658 IMU...");
  imuAvailable = imuSensor.begin(EXAMPLE_PIN_NUM_TOUCH_SDA, EXAMPLE_PIN_NUM_TOUCH_SCL);
  if (imuAvailable) {
    Serial.println("✅ QMI8658 IMU initialized successfully");
    Serial.println("   Features enabled:");
    Serial.println("   - Fall detection (threshold: 2.5g)");
    Serial.println("   - Tremor monitoring (Parkinson's range: 4-12 Hz)");
    Serial.println("   - Activity classification (stationary/walking/running)");
    Serial.println("   - Real-time motion data for MQTT streaming");
    Serial.println("\n📍 Calibrating IMU (keep device flat and stationary)...");
    imuSensor.calibrate();
  } else {
    Serial.println("⚠️  QMI8658 IMU not found (fall/tremor detection disabled)");
    Serial.println("   The watch will continue to work, but without:");
    Serial.println("   - Real-time fall detection");
    Serial.println("   - Tremor analysis (Parkinson's monitoring)");
    Serial.println("   - Motion-based activity tracking");
  }

  // ✅ Use version constants for completion message
  Serial.printf("\n✅ v%s: %s - Ready!\n", FIRMWARE_VERSION, VERSION_NAME);
  if (imuAvailable) {
    Serial.println("🩺 Real IMU enabled: Fall & tremor detection active");
  }
}

// ====================================
// MAIN LOOP
// ====================================
void loop() {
  // ✅ v5.3: Update LVGL timer and UI
  display.update();

  // ✅ v5.4: Update touch handler for swipe gesture detection
  touch.update();

  // ✅ v5.4: Update IMU and check for fall/tremor events (every loop iteration)
  if (imuAvailable) {
    imuSensor.update();  // Fetch latest accelerometer/gyroscope data

    // 🚨 FALL DETECTION (highest priority - check every loop)
    if (imuSensor.checkForFall()) {
      float magnitude = imuSensor.getAccelerationMagnitude();
      float confidence = imuSensor.getFallConfidence();

      // Send critical alert immediately
      sendAlert("FALL_DETECTED", "CRITICAL",
                "Patient fall detected! Acceleration: " + String(magnitude, 2) + "g",
                confidence);

      // Flash red LED urgently
      flashAlertPattern("critical");

      // Update UI to show fall alert
      ui.showAlert("FALL DETECTED", "🚨 Emergency Response");

      // Clear fall flag after handling
      imuSensor.clearFallFlag();

      Serial.printf("🚨 FALL EVENT HANDLED - Alert sent to hospital\n");
    }

    // ⚠️ TREMOR DETECTION (check every loop - internally rate-limited to 100Hz)
    static unsigned long lastTremorAlert = 0;
    if (imuSensor.checkForTremor()) {
      // Don't spam - only send alert every 30 seconds
      if (millis() - lastTremorAlert > 30000) {
        float freq = imuSensor.getTremorFrequency();
        float amp = imuSensor.getTremorAmplitude();

        sendAlert("TREMOR_DETECTED", "WARNING",
                  "Tremor detected! Frequency: " + String(freq, 1) + " Hz, Amplitude: " + String(amp, 3) + "g",
                  0.75);

        lastTremorAlert = millis();

        Serial.printf("⚠️  TREMOR EVENT HANDLED - Alert sent (Freq: %.1fHz, Amp: %.3fg)\n", freq, amp);
      }
    }
  }

  if (!wifiConnected) {
    dnsServer.processNextRequest();
  }

  server.handleClient();

  if (wifiConnected && mqttClient.connected()) {
    mqttClient.loop();
  }

  // ✅ v5.2.4: Fix millis() overflow handling with unsigned long cast
  if (wifiConnected && ntpSynced && (unsigned long)(millis() - lastNtpSync) > 3600000) {
    syncNTPTime();
  }

  // ⚠️ TEMPORARILY REMOVED NTP REQUIREMENT FOR TESTING
  if (wifiConnected && !isProvisioned && !provisioningInProgress && (unsigned long)(millis() - lastProvisionAttempt) > 15000) {
    lastProvisionAttempt = millis();
    attemptProvisioning();
  }

  if (wifiConnected && isProvisioned && mqttClient.connected() && (unsigned long)(millis() - lastHeartbeat) > 30000) {
    sendMQTTHeartbeat();
    lastHeartbeat = millis();
  }

  // ✅ v5.2.4: Generate vitals even when offline (patient monitoring never stops)
  // ✅ v5.4: Use configurable vitalsTransmissionInterval (default: 5 seconds)
  unsigned long vitalsInterval = vitalsTransmissionInterval * 1000UL;  // Convert seconds to milliseconds
  if (isProvisioned && isAssigned && (unsigned long)(millis() - lastVitals) > vitalsInterval) {
    // ✅ v5.2.12: Check GPIO pin and update simulator mode dynamically
    bool currentMode = digitalRead(MODE_SELECT_PIN) == HIGH;
    simulator.setMode(currentMode ? PhysiologicalSimulator::MODE_ECG : PhysiologicalSimulator::MODE_EEG);

    // ✅ v5.1: Update physiological state and get simulated vitals
    simulator.update();
    heartRate = simulator.getHeartRate();
    temperature = simulator.getTemperature();
    oxygenSat = simulator.getOxygenSaturation();
    respiratoryRate = simulator.getRespiratoryRate();
    quality = simulator.getSignalQuality();
    bloodPressureSystolic = simulator.getBloodPressureSystolic();
    bloodPressureDiastolic = simulator.getBloodPressureDiastolic();

    sendVitals();  // Already handles offline queueing internally
    lastVitals = millis();
  }

  // ✅ v5.2.13: Check if calibration completed (non-blocking detection)
  if (calibrationRequested && !simulator.isCalibrationActive()) {
    Serial.println("🔧 Calibration pulse complete - publishing completion message");

    // Detect current mode from GPIO
    bool isECGMode = (digitalRead(MODE_SELECT_PIN) == HIGH);
    String mode = isECGMode ? "ecg" : "eeg";

    // Publish completion notification
    String topic = "hospital/devices/" + deviceId + "/waveform_calibration_complete";
    JsonDocument doc;
    doc["timestamp"] = getISO8601Timestamp();
    doc["success"] = true;
    doc["duration"] = 3000;  // ms (1000ms head + 1000ms pulse + 1000ms tail)
    doc["mode"] = mode;      // ✅ NEW: Report which mode was calibrated

    String payload;
    serializeJson(doc, payload);
    publishWithRetry(topic.c_str(), payload.c_str());

    Serial.print("✅ Calibration complete - mode: ");
    Serial.println(mode);

    // Reset flags
    calibrationRequested = false;
    calibrationCommandId = "";
    calibrationStartMillis = 0;
  }

  // ✅ v5.2.4: Generate micro-batches even when offline (ECG/EEG never stops)
  if (isProvisioned && isAssigned && (unsigned long)(millis() - lastMicroBatch) > 20) {
    generateMicroBatch();
    lastMicroBatch = millis();
  }

  // ✅ v5.2.4: Send waveform even when offline (queues to SPIFFS automatically)
  // ✅ v5.4: Respect waveformStreamingEnabled configuration flag
  if (isProvisioned && isAssigned && waveformStreamingEnabled &&
      accumulatorIndex >= 50 && (unsigned long)(millis() - lastWaveformStream) > 100) {
    sendWaveformStream();  // Already handles offline queueing internally
    lastWaveformStream = millis();
    accumulatorIndex = 0;
  }

  // ✅ v5.2.3: Auto-reconnect to saved WiFi when in captive portal mode
  if (!wifiConnected && (unsigned long)(millis() - lastScan) > 60000) {
    scanWiFiNetworks();
    lastScan = millis();

    // Check if we have saved WiFi credentials and the network is available
    if (wifiSSID.length() > 0) {
      // Look for saved SSID in scan results
      bool networkFound = false;
      for (int i = 0; i < networkCount; i++) {
        if (WiFi.SSID(i) == wifiSSID) {
          networkFound = true;
          break;
        }
      }

      if (networkFound) {
        Serial.println("🔄 Saved WiFi network detected - attempting reconnection...");
        Serial.println("   SSID: " + wifiSSID);
        connectToWiFi();
      }
    }
  }

  trackConnectivity();
  updateBatteryHealth();
  updateSensorHistory();

  // ✅ v5.2.4: Check alerts even when offline (patient safety first)
  if (isProvisioned && (unsigned long)(millis() - lastAlertCheck) > 2000) {
    runAlertEngine();  // Already handles offline queueing internally
    lastAlertCheck = millis();
  }

  // ✅ v5.2.1: Process offline queue every 30 seconds when connected
  if (wifiConnected && mqttClient.connected() && (unsigned long)(millis() - lastQueueProcess) > 30000) {
    offlineQueue.processPendingMessages();
    lastQueueProcess = millis();
  }

  // ✅ v5.2: Check NFC IRQ pin for card detection
  if (nfcAvailable) {
    nfc.updateIRQ();
  }

  // ✅ v5.2.4: Update non-blocking LED flasher (P1 fix)
  updateLEDFlasher();

  delay(100);
}

// ====================================
// CAPTIVE PORTAL
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
// WIFI SCANNING
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
  // ✅ v5.0: Save provisioning code instead of credentials
  String provCode = server.arg("prov_code");

  if (wifiSSID.length() == 0 || serverIP.length() == 0 || provCode.length() != 6) {
    server.send(400, "text/html",
      "<html><body><h2>❌ Error</h2><p>WiFi SSID, Server IP, and valid 6-digit PIN are required!</p>"
      "<a href='/'>← Go Back</a></body></html>");
    return;
  }

  prefs.putString("prov_code", provCode);
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

void handleStatus() {
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

    syncNTPTime();

    // ✅ v5.0: Check for certificates before connecting
    if (isProvisioned && hasCertificates()) {
      setupMQTT();
    } else if (isProvisioned && !hasCertificates()) {
      Serial.println("⚠️  Certificates missing - resetting provisioning");
      mqttConfigured = false;  // ✅ v5.0.3: Reset flag when certs missing
      isProvisioned = false;
      saveConfiguration();
    }

  } else {
    wifiConnected = false;
    digitalWrite(2, LOW);
    Serial.println("\n❌ WiFi connection failed!");
    delay(2000);
    startCaptivePortal();
  }
}

// ====================================
// MQTT SETUP (v5.0.2 - Certificate Auth with Global Cert Fix)
// ====================================
void setupMQTT() {
  if (mqttServer.length() == 0) {
    mqttServer = serverIP;
  }

  // ✅ v5.0.3: Check if already configured - skip cert reload
  if (mqttConfigured) {
    Serial.println("🔐 MQTT already configured (skipping cert reload)");
    connectToMQTT();  // Just attempt reconnection
    return;
  }

  Serial.println("🔧 Configuring MQTT client...");
  Serial.println("📡 MQTT Server: " + mqttServer + ":" + mqttPort);

  // ====================================
  // ✅ v5.0.2: LOAD DEVICE CERTIFICATES INTO GLOBAL VARIABLES FIRST
  // This prevents .c_str() dangling pointer issues (errno 113)
  // ====================================
  if (!loadDeviceCertificate(deviceCertificate, devicePrivateKey)) {
    Serial.println("❌ Cannot setup MQTT - device certificates not found");
    Serial.println("⚠️  Device needs provisioning first");
    return;
  }

  Serial.println("🔐 Certificates loaded:");
  Serial.println("   CA: " + String(caCertificate.length()) + " bytes (global)");
  Serial.println("   Device cert: " + String(deviceCertificate.length()) + " bytes (global)");
  Serial.println("   Device key: " + String(devicePrivateKey.length()) + " bytes (global)");

  // ====================================
  // ✅ v5.0.2: SET ALL CERTIFICATES *BEFORE* setServer()
  // Using .c_str() from global String variables (no dangling pointers)
  // ====================================
  Serial.println("🔐 Setting TLS certificates...");

  // ✅ v5.0.2: Using setCertificate() with global String variables
  // These are stored in global scope, so .c_str() pointers remain valid
  wifiClient.setCACert(caCertificate.c_str());
  wifiClient.setCertificate(deviceCertificate.c_str());
  wifiClient.setPrivateKey(devicePrivateKey.c_str());

  Serial.println("   ✅ CA cert set (server validation ENABLED)");
  Serial.println("   ✅ Device cert set (client authentication)");
  Serial.println("   ✅ Private key set (mTLS complete)");

  // ====================================
  // NOW set server (AFTER certificates are configured)
  // ====================================
  mqttClient.setServer(mqttServer.c_str(), mqttPort.toInt());
  mqttClient.setCallback(onMqttMessage);
  mqttClient.setBufferSize(16384);  // ✅ v5.2: Increased for waveform streaming (12 leads × 50 samples)
  mqttClient.setKeepAlive(15);

  mqttConfigured = true;  // ✅ v5.0.3: Mark as configured
  Serial.println("✅ MQTT client configured with certificates");
  connectToMQTT();
}

// ✅ v5.0.2: Certificate-based MQTT connection (SIMPLIFIED - certs already set in setupMQTT)
void connectToMQTT() {
  if (!wifiConnected || !isProvisioned) return;

  // ====================================
  // ✅ v5.0.2: Certificates already set in setupMQTT() as globals
  // No need to reload or re-set them here - just connect
  // ====================================

  Serial.println("\n🔍 === TLS HANDSHAKE DIAGNOSTICS ===");
  Serial.println("📊 Free heap BEFORE MQTT connect: " + String(ESP.getFreeHeap()) + " bytes");
  Serial.println("📊 Free PSRAM: " + String(ESP.getFreePsram()) + " bytes");
  Serial.println("🔐 Using global certificates (already set in wifiClient):");
  Serial.println("   CA: " + String(caCertificate.length()) + " bytes");
  Serial.println("   Device cert: " + String(deviceCertificate.length()) + " bytes");
  Serial.println("   Device key: " + String(devicePrivateKey.length()) + " bytes");

  // ====================================
  // ATTEMPT MQTT CONNECTION
  // ====================================
  String clientId = "HospitalWatch_" + deviceId;
  Serial.println("\n🔄 Connecting to MQTT with client certificate...");
  Serial.println("🔐 Device ID (from cert CN): " + deviceId);
  Serial.println("📡 MQTT Server: " + mqttServer + ":" + mqttPort);

  // ✅ DEBUG: Re-verify certificates right before connect
  Serial.println("\n🔍 PRE-CONNECTION CERTIFICATE CHECK:");
  Serial.println("   CA cert length: " + String(caCertificate.length()));
  Serial.println("   Device cert length: " + String(deviceCertificate.length()));
  Serial.println("   Device key length: " + String(devicePrivateKey.length()));
  Serial.println("   CA cert starts with: " + caCertificate.substring(0, 27));
  Serial.println("   Device cert starts with: " + deviceCertificate.substring(0, 27));
  Serial.println("   Device key starts with: " + devicePrivateKey.substring(0, 27));

  // ✅ v5.0: Connect WITHOUT username/password (certificate auth only)
  if (mqttClient.connect(clientId.c_str())) {
    Serial.println("✅ MQTT Connected with client certificate (mTLS)!");
    Serial.println("📊 Free heap AFTER MQTT connect: " + String(ESP.getFreeHeap()) + " bytes");
    Serial.println("🔑 Current deviceId: '" + deviceId + "'");

    String assignTopic = "hospital/devices/" + deviceId + "/assign";
    bool assignSuccess = mqttClient.subscribe(assignTopic.c_str());
    Serial.println("📡 Subscribed to: " + assignTopic + (assignSuccess ? " ✅" : " ❌"));

    String commandTopic = "hospital/devices/" + deviceId + "/commands";
    bool commandSuccess = mqttClient.subscribe(commandTopic.c_str());
    Serial.println("📡 Subscribed to: " + commandTopic + (commandSuccess ? " ✅" : " ❌"));

  } else {
    Serial.println("❌ MQTT Connection failed, rc=" + String(mqttClient.state()));
    Serial.println("📊 Free heap AFTER failed connect: " + String(ESP.getFreeHeap()) + " bytes");
    Serial.println("\n💡 Troubleshooting:");
    Serial.println("   - Check heap memory (should be > 30KB before TLS)");
    Serial.println("   - Verify certificate valid (not expired)");
    Serial.println("   - Confirm Device ID matches cert CN");
    Serial.println("   - Ensure Mosquitto configured for mTLS");
  }

  Serial.println("🔍 === END DIAGNOSTICS ===\n");
}

void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  Serial.println("🔔 MQTT CALLBACK TRIGGERED!");
  Serial.println("   Topic: " + String(topic));
  Serial.println("   Length: " + String(length));

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

  if (String(topic).endsWith("/commands")) {
    Serial.println("✅ Topic ends with /commands - processing command");
    lastCommandReceivedAt = millis();
    // ✅ v5.2.2: Bug #5 fix - Reset deviceUnresponsiveAlertSent when command received
    deviceUnresponsiveAlertSent = false;

    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, message);
    if (error == DeserializationError::Ok) {
      String commandType = doc["command"].as<String>();
      String commandId = doc["commandId"].as<String>();
      Serial.println("🎯 Command parsed: type='" + commandType + "', id='" + commandId + "'");

      // ====================================
      // ✅ v5.4: EXTENDED COMMAND ROUTING
      // ====================================
      // Basic commands (existing)
      if (commandType == "ping") {
        Serial.println("📍 Handling ping command");
        handlePingCommand(commandId);
      }
      else if (commandType == "waveformCalibrate") {
        Serial.println("🔧 Handling waveformCalibrate command");
        handleWaveformCalibrationCommand(commandId);
      }
      else if (commandType == "unassign") {
        Serial.println("👤 Handling unassign command");
        handleUnassignCommand(commandId);
      }
      else if (commandType == "custom") {
        Serial.println("🔧 Handling custom command");
        handleCustomCommand(commandId, doc);
      }
      // Configuration commands (new in v5.4)
      else if (commandType == "setDisplayBrightness") {
        Serial.println("💡 Handling display brightness command");
        handleDisplayBrightnessCommand(commandId, doc);
      }
      else if (commandType == "setWaveformStreaming") {
        Serial.println("📊 Handling waveform streaming command");
        handleWaveformStreamingCommand(commandId, doc);
      }
      else if (commandType == "setSamplingRate") {
        Serial.println("⏱️  Handling sampling rate command");
        handleSamplingRateCommand(commandId, doc);
      }
      else if (commandType == "setVitalsInterval") {
        Serial.println("⏰ Handling vitals interval command");
        handleVitalsIntervalCommand(commandId, doc);
      }
      else if (commandType == "setDebugMode") {
        Serial.println("🐛 Handling debug mode command");
        handleDebugModeCommand(commandId, doc);
      }
      else if (commandType == "setAlertThreshold") {
        Serial.println("🚨 Handling alert threshold command");
        handleAlertThresholdCommand(commandId, doc);
      }
      else if (commandType == "setLEDAlerts") {
        Serial.println("💡 Handling LED alerts command");
        handleLEDAlertsCommand(commandId, doc);
      }
      // Management commands (new in v5.4)
      else if (commandType == "getDeviceStatus") {
        Serial.println("📊 Handling device status request");
        handleDeviceStatusCommand(commandId);
      }
      else if (commandType == "clearOfflineQueue") {
        Serial.println("🗑️  Handling clear offline queue command");
        handleClearOfflineQueueCommand(commandId);
      }
      else if (commandType == "syncTime") {
        Serial.println("🕐 Handling sync time command");
        handleSyncTimeCommand(commandId);
      }
      else if (commandType == "setWaveformMode") {
        Serial.println("❤️  Handling waveform mode command");
        handleWaveformModeCommand(commandId, doc);
      }
      else if (commandType == "reboot") {
        Serial.println("🔄 Handling reboot command");
        handleRebootCommand(commandId);
      }
      // Unknown command
      else {
        Serial.println("⚠️  Unknown command type: " + commandType);
        sendCommandAck(commandId, false, "Unknown command: " + commandType);
      }
    } else {
      Serial.println("❌ Failed to parse command JSON: " + String(error.c_str()));
    }
  }
}

// ====================================
// HTTPS PROVISIONING (v5.0)
// ====================================
void attemptProvisioning() {
  String provCode = prefs.getString("prov_code", "");

  if (provCode.length() == 0 || serverIP.length() == 0) {
    Serial.println("❌ Missing provisioning code or server IP");
    return;
  }

  if (provisioningInProgress) {
    Serial.println("⏳ Provisioning already in progress...");
    return;
  }

  Serial.println("🔄 Attempting HTTPS certificate provisioning...");
  provisioningInProgress = true;

  HTTPClient http;
  WiFiClientSecure httpsClient;
  httpsClient.setInsecure();  // Accept self-signed cert for provisioning

  String url = "https://" + serverIP + ":" + serverPort + "/api/v1/provisioning/provision-with-certificate";

  http.begin(httpsClient, url);
  http.addHeader("Content-Type", "application/json");

  JsonDocument doc;
  doc["code"] = provCode;

  // ✅ QUICK FIX: Remove colons from MAC to test ACL hypothesis
  String sanitizedMac = macAddress;
  sanitizedMac.replace(":", "");  // "A0:A3:B3:AA:13:B0" → "A0A3B3AA13B0"

  doc["deviceId"] = deviceId.length() > 0 ? deviceId : ("ESP32-WATCH-" + sanitizedMac);
  doc["macAddress"] = macAddress;
  doc["serialNumber"] = "SN-" + macAddress;

  String requestBody;
  serializeJson(doc, requestBody);

  Serial.println("📤 Sending provisioning request to: " + url);
  int httpCode = http.POST(requestBody);

  if (httpCode == 200) {
    String response = http.getString();
    JsonDocument responseDoc;

    if (deserializeJson(responseDoc, response) == DeserializationError::Ok) {
      deviceId = responseDoc["deviceId"].as<String>();
      String certPem = responseDoc["certificatePem"].as<String>();
      String keyPem = responseDoc["privateKeyPem"].as<String>();
      String caCertPem = responseDoc["caCertificatePem"].as<String>();

      Serial.println("📥 Received certificate from backend");

      if (saveCertificates(certPem, keyPem)) {
        // Save CA certificate
        File caFile = SPIFFS.open("/ca.crt", "w");
        if (caFile) {
          caFile.print(caCertPem);
          caFile.close();
          caCertificate = caCertPem;
          Serial.println("✅ CA certificate saved to SPIFFS");
        }

        mqttConfigured = false;  // ✅ v5.0.3: Reset flag to reload new certs
        isProvisioned = true;
        provisioningInProgress = false;
        prefs.remove("prov_code");  // Clear used code
        saveConfiguration();

        Serial.println("🎉 DEVICE PROVISIONED via HTTPS!");
        Serial.println("   📱 Device ID: " + deviceId);
        Serial.println("   🔐 Certificate saved to SPIFFS");
        Serial.println("   🔐 Private key saved to SPIFFS");

        // Flash LED to indicate success
        for(int i = 0; i < 10; i++) {
          digitalWrite(2, HIGH);
          delay(100);
          digitalWrite(2, LOW);
          delay(100);
        }
        digitalWrite(2, HIGH);

        // Connect to MQTT with certificate
        setupMQTT();
      } else {
        Serial.println("❌ Failed to save certificates");

        // ✅ v5.0.1: Clear WiFi credentials and restart to captive portal
        Serial.println("⚠️ Provisioning failed - clearing WiFi and restarting");
        wifiSSID = "";
        wifiPassword = "";
        serverIP = "";
        prefs.remove("prov_code");
        prefs.remove("ssid");
        prefs.remove("pass");
        prefs.remove("ip");

        provisioningInProgress = false;
        delay(2000);
        ESP.restart();  // Restart to captive portal
      }
    } else {
      Serial.println("❌ Failed to parse provisioning response");

      // ✅ v5.0.1: Clear WiFi credentials and restart
      Serial.println("⚠️ Invalid response - clearing WiFi and restarting");
      wifiSSID = "";
      wifiPassword = "";
      serverIP = "";
      prefs.remove("prov_code");
      prefs.remove("ssid");
      prefs.remove("pass");
      prefs.remove("ip");

      provisioningInProgress = false;
      delay(2000);
      ESP.restart();
    }
  } else {
    Serial.println("❌ Provisioning failed, HTTP code: " + String(httpCode));
    if (httpCode > 0) {
      Serial.println("Response: " + http.getString());
    }

    // ✅ v5.0.1: Clear provisioning code so user can try again with new PIN
    prefs.remove("prov_code");
    provisioningInProgress = false;

    // Device stays connected to WiFi so user can see error at /status
    // User can restart manually to go back to captive portal
  }

  http.end();
}

// ====================================
// MQTT HEARTBEAT
// ====================================
void sendMQTTHeartbeat() {
  // ✅ v5.4: Refactored to use publishMessage() helper
  if (!mqttClient.connected()) return;

  String topic = "hospital/devices/" + deviceId + "/heartbeat";

  // Heartbeats should NOT be queued offline (queueOffline = false)
  if (publishMessage(topic, [](JsonDocument& doc) {
    doc["batteryLevel"] = batteryLevel;
    doc["signalStrength"] = WiFi.RSSI();
    doc["firmwareVersion"] = FIRMWARE_VERSION;
  }, false)) {  // ✅ Don't queue heartbeats offline
    Serial.println("💓 MQTT Heartbeat sent");
  }
}

// ====================================
// VITALS (MQTT)
// ====================================
void sendVitals() {
  // ✅ v5.4: Refactored to use publishMessage() helper - reduces code duplication
  String topic = "hospital/devices/" + deviceId + "/vitals";

  // Read GPIO pin and convert temperature BEFORE lambda (captured by reference)
  bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;
  float tempCelsius = (temperature - 32.0) * 5.0 / 9.0;

  // ✅ v5.4: Process IMU data into actionable insights (not raw sensor values)
  const char* activityStr = "UNKNOWN";
  int movementIntensity = 0;  // 0-100 scale (0=still, 100=very active)

  if (imuAvailable) {
    // Get activity classification
    activityStr = imuSensor.getActivityString();

    // Calculate movement intensity (0-100 scale for UI/backend)
    float magnitude = imuSensor.getAccelerationMagnitude();
    // Map acceleration: 1.0g (still) → 0%, 2.0g (active) → 100%
    movementIntensity = constrain((int)((magnitude - 1.0) * 100.0), 0, 100);
  }

  // Publish using helper template (handles connection check, retry, offline queueing)
  bool success = publishMessage(topic, [&](JsonDocument& doc) {
    doc["sequence"] = vitalsSequenceCounter++;  // ✅ Message ID for vitals
    doc["mode"] = isECGMode ? "ecg" : "eeg";
    doc["patientId"] = assignedPatientId;
    doc["heartRate"] = (int)heartRate;
    doc["skinTemperature"] = tempCelsius;
    doc["oxygenSaturation"] = (int)oxygenSat;
    doc["signalQuality"] = quality / 100.0;
    doc["respiratoryRate"] = (int)respiratoryRate;
    doc["batteryLevel"] = batteryLevel;
    doc["bloodPressureSystolic"] = bloodPressureSystolic;
    doc["bloodPressureDiastolic"] = bloodPressureDiastolic;

    // ✅ v5.4: Send PROCESSED motion insights (not raw sensor data)
    if (imuAvailable) {
      doc["activity"] = activityStr;  // "STATIONARY", "WALKING", "RUNNING"
      doc["movementIntensity"] = movementIntensity;  // 0-100 scale (for UI charts)
    }
  });

  if (success) {
    Serial.println("📊 Vitals: Mode=" + String(isECGMode ? "ECG" : "EEG") +
                   ", HR=" + String((int)heartRate) +
                   ", BP=" + String(bloodPressureSystolic) + "/" + String(bloodPressureDiastolic) +
                   ", Temp=" + String(tempCelsius, 1) + "°C" +
                   ", SpO2=" + String(oxygenSat) + "%" +
                   ", RR=" + String(respiratoryRate));

    // ✅ Update UI with latest vitals
    ui.updateVitals(heartRate, oxygenSat, tempCelsius, bloodPressureSystolic, bloodPressureDiastolic, respiratoryRate);
  }
  // ✅ If !success, publishMessage() already queued offline and attempted reconnect
}

// ====================================
// MICRO-BATCH GENERATION (v5.2)
// ====================================
void generateMicroBatch() {
  // ✅ v5.2.4: P2 FIX - Debug logging flag
  if (DEBUG_WAVEFORMS) {
    static unsigned long debugCount = 0;
    if (debugCount % 50 == 0) {  // Print every 50th call (every 1 second)
      Serial.println("🔧 DEBUG: generateMicroBatch() called, accumulatorIndex=" + String(accumulatorIndex));
    }
    debugCount++;
  }

  if (accumulatorIndex >= 50) {
    return;  // Buffer full, wait for sendWaveformStream() to clear it
  }

  // ✅ Generate 10 samples using GLOBAL buffer (no stack allocation)
  simulator.fillSampleBuffer(microBatch);

  // Copy to accumulator
  for (int ch = 0; ch < 8; ch++) {
    for (int i = 0; i < 10; i++) {
      waveformAccumulator[ch][accumulatorIndex + i] = microBatch[ch][i];
    }
  }

  accumulatorIndex += 10;
}

// ====================================
// DELTA ENCODING HELPER (v5.2.5)
// ====================================
void addDeltaEncodedChannel(JsonObject& parent, const char* fieldName, int32_t* samples, int count) {
  JsonObject channel = parent.createNestedObject(fieldName);
  channel["baseline"] = samples[0];
  JsonArray deltas = channel.createNestedArray("deltas");
  for (int i = 1; i < count; i++) {
    deltas.add(samples[i] - samples[i-1]);
  }
}

// ====================================
// WAVEFORM STREAMING (v5.2)
// ====================================
void sendWaveformStream() {
  // ✅ v5.2.4: P2 FIX - Debug logging flag
  if (DEBUG_WAVEFORMS) {
    Serial.println("🔧 DEBUG: sendWaveformStream() ENTERED, accumulatorIndex=" + String(accumulatorIndex));
  }

  // ✅ v5.2.2: Check buffer readiness FIRST (before connection check)
  if (accumulatorIndex < 50) {
    if (DEBUG_WAVEFORMS) {
      Serial.println("🔧 DEBUG: BLOCKED - accumulatorIndex < 50");
    }
    return;
  }

  if (DEBUG_WAVEFORMS) {
    Serial.println("🔧 DEBUG: Proceeding to create waveform payload...");
  }
  String topic = "hospital/devices/" + deviceId + "/stream";

  // ✅ ArduinoJson v7 automatically allocates from heap
  JsonDocument doc;
  doc["deviceId"] = deviceId;
  doc["patientId"] = assignedPatientId;
  doc["timestamp"] = getISO8601Timestamp();

  bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;
  doc["mode"] = isECGMode ? "ecg" : "eeg";
  doc["sequence"] = waveformSequenceCounter++;
  doc["duration"] = 0.1;  // ✅ v5.2.5: 100ms packet = 0.1 seconds
  doc["sampleRate"] = 500;

  if (isECGMode) {
    JsonObject ecgWaveform = doc.createNestedObject("ecgWaveform");

    // ✅ v5.2.5: Limb leads (I, II, III) - Delta encoded with camelCase naming
    JsonObject limb = ecgWaveform.createNestedObject("limb");

    // Calculate lead III array (Lead III = II - I)
    // ✅ CRITICAL: Subtract DC offset before calculating derived lead
    int32_t lead3Array[50];
    for (int i = 0; i < 50; i++) {
      int32_t leadI_rel = waveformAccumulator[0][i] - 8388608;
      int32_t leadII_rel = waveformAccumulator[1][i] - 8388608;
      int32_t lead3_rel = leadII_rel - leadI_rel;
      lead3Array[i] = lead3_rel + 8388608;  // Convert back to absolute
    }

    // Add delta-encoded channels with correct naming (leadI, leadII, leadIII)
    addDeltaEncodedChannel(limb, "leadI", waveformAccumulator[0], 50);
    addDeltaEncodedChannel(limb, "leadII", waveformAccumulator[1], 50);
    addDeltaEncodedChannel(limb, "leadIII", lead3Array, 50);

    // ✅ v5.2.5: Precordial leads (V1-V5) - Delta encoded
    JsonObject precordial = ecgWaveform.createNestedObject("precordial");
    addDeltaEncodedChannel(precordial, "v1", waveformAccumulator[2], 50);
    addDeltaEncodedChannel(precordial, "v2", waveformAccumulator[3], 50);
    addDeltaEncodedChannel(precordial, "v3", waveformAccumulator[4], 50);
    addDeltaEncodedChannel(precordial, "v4", waveformAccumulator[5], 50);
    addDeltaEncodedChannel(precordial, "v5", waveformAccumulator[6], 50);

    // ✅ v5.2.7: Derived leads (aVR, aVL, aVF, V6) - Delta encoded with Goldberger amplification
    JsonObject derived = ecgWaveform.createNestedObject("derived");

    // Calculate derived lead arrays using Goldberger formulas (clinical standard)
    // Goldberger leads use 1.5x amplification compared to Wilson Central Terminal
    int32_t avrArray[50], avlArray[50], avfArray[50];
    for (int i = 0; i < 50; i++) {
      int32_t leadI = waveformAccumulator[0][i];
      int32_t leadII = waveformAccumulator[1][i];

      // ✅ CRITICAL: Subtract DC offset (ADC midpoint) before calculating derived leads
      // ADC values are ~8,388,608 ± 100,000, we need to work with relative values
      int32_t leadI_rel = leadI - 8388608;
      int32_t leadII_rel = leadII - 8388608;

      // Goldberger augmented lead formulas (1.5x amplified) in relative space:
      int32_t avr_rel = -(3 * (leadI_rel + leadII_rel)) / 4;        // aVR = -1.5*(I+II)/2
      int32_t avl_rel = (3 * (2 * leadI_rel - leadII_rel)) / 4;     // aVL = 1.5*(2I-II)/2
      int32_t avf_rel = (3 * (2 * leadII_rel - leadI_rel)) / 4;     // aVF = 1.5*(2II-I)/2

      // Convert back to absolute ADC values
      avrArray[i] = avr_rel + 8388608;
      avlArray[i] = avl_rel + 8388608;
      avfArray[i] = avf_rel + 8388608;
    }

    addDeltaEncodedChannel(derived, "avr", avrArray, 50);
    addDeltaEncodedChannel(derived, "avl", avlArray, 50);
    addDeltaEncodedChannel(derived, "avf", avfArray, 50);
    addDeltaEncodedChannel(derived, "v6", waveformAccumulator[7], 50);
  } else {
    // ✅ v5.2.5: EEG mode - Delta encoded with proper capitalization
    JsonObject eegWaveform = doc.createNestedObject("eegWaveform");

    // Frontal channels (Fp1, Fp2, F3, F4)
    JsonObject frontal = eegWaveform.createNestedObject("frontal");
    addDeltaEncodedChannel(frontal, "Fp1", waveformAccumulator[0], 50);
    addDeltaEncodedChannel(frontal, "Fp2", waveformAccumulator[1], 50);
    addDeltaEncodedChannel(frontal, "F3", waveformAccumulator[2], 50);
    addDeltaEncodedChannel(frontal, "F4", waveformAccumulator[3], 50);

    // Central channels (C3, C4)
    JsonObject central = eegWaveform.createNestedObject("central");
    addDeltaEncodedChannel(central, "C3", waveformAccumulator[4], 50);
    addDeltaEncodedChannel(central, "C4", waveformAccumulator[5], 50);

    // Occipital channels (O1, O2)
    JsonObject occipital = eegWaveform.createNestedObject("occipital");
    addDeltaEncodedChannel(occipital, "O1", waveformAccumulator[6], 50);
    addDeltaEncodedChannel(occipital, "O2", waveformAccumulator[7], 50);
  }

  String payload;
  serializeJson(doc, payload);

  if (DEBUG_WAVEFORMS) {
    Serial.println("🔧 DEBUG: Payload size=" + String(payload.length()) + " bytes, MQTT buffer=16384");
  }

  // ✅ v5.2.2: NOW check connection state
  if (!mqttClient.connected() || !isAssigned) {
    // Connection lost or not assigned - save to offline queue
    Serial.println("⚠️  MQTT disconnected - queuing waveform offline");
    offlineQueue.saveWaveform(payload);
    return;
  }

  // ✅ Connected - attempt publish with retry
  bool publishResult = publishWithRetry(topic.c_str(), payload.c_str());  // ✅ v5.2.1: QoS 1 with retry

  if (DEBUG_WAVEFORMS) {
    Serial.println("🔧 DEBUG: MQTT publish result=" + String(publishResult ? "SUCCESS" : "FAILED"));
  }

  if (publishResult) {
    if (waveformSequenceCounter % 10 == 0) {
      Serial.println("📈 Waveform stream: " + String(isECGMode ? "ECG" : "EEG") +
                    " (seq: " + String(waveformSequenceCounter) +
                    ", size: " + String(payload.length()) + " bytes)");
    }
  } else {
    // ✅ Publish failed after retries - save to offline queue
    Serial.println("⚠️  MQTT publish failed - queuing waveform offline");
    offlineQueue.saveWaveform(payload);
  }
}

// ====================================
// CONFIGURATION
// ====================================
void loadConfiguration() {
  wifiSSID = prefs.getString("ssid", "");
  wifiPassword = prefs.getString("pass", "");
  serverIP = prefs.getString("ip", "");
  serverPort = prefs.getString("port", "8001");
  mqttServer = prefs.getString("mqttip", "");
  mqttPort = prefs.getString("mqttport", "8883");

  // ✅ v5.0: REMOVED MQTT credential loading (now using certificates)

  deviceId = prefs.getString("deviceId", "");
  serialNumber = prefs.getString("serial", "");
  assignedPatientId = prefs.getString("patientId", "");
  isProvisioned = prefs.getBool("provisioned", false);
  isAssigned = prefs.getBool("assigned", false);
  batteryLevel = prefs.getInt("battery", 100);

  batteryHealthPercentage = prefs.getInt("batHealth", 100);

  // ✅ v5.2.2: Bug #2 fix - ALWAYS reset totalDisconnects to 0 on boot
  // Disconnect counter should NOT persist across reboots (each reboot is a fresh session)
  totalDisconnects = 0;

  // ====================================
  // ✅ v5.4: Load device configuration parameters
  // ====================================
  displayBrightness = prefs.getUChar("disp_bright", 100);
  waveformStreamingEnabled = prefs.getBool("wf_stream", true);
  samplingRate = prefs.getUShort("samp_rate", 250);
  vitalsTransmissionInterval = prefs.getUChar("vitals_int", 5);
  debugModeEnabled = prefs.getBool("debug_mode", false);
  ledAlertsEnabled = prefs.getBool("led_alerts", true);

  // Load alert thresholds
  alertThresholds.hrMin = prefs.getFloat("hr_min", 40.0);
  alertThresholds.hrMax = prefs.getFloat("hr_max", 120.0);
  alertThresholds.spo2Min = prefs.getFloat("spo2_min", 90.0);
  alertThresholds.spo2Max = prefs.getFloat("spo2_max", 100.0);
  alertThresholds.tempMin = prefs.getFloat("temp_min", 35.0);
  alertThresholds.tempMax = prefs.getFloat("temp_max", 38.5);
  alertThresholds.bpSysMin = prefs.getFloat("bpsys_min", 90.0);
  alertThresholds.bpSysMax = prefs.getFloat("bpsys_max", 140.0);
  alertThresholds.bpDiaMin = prefs.getFloat("bpdia_min", 60.0);
  alertThresholds.bpDiaMax = prefs.getFloat("bpdia_max", 90.0);
  alertThresholds.rrMin = prefs.getFloat("rr_min", 12.0);
  alertThresholds.rrMax = prefs.getFloat("rr_max", 20.0);

  // Load waveform mode (ECG/EEG)
  bool isECG = prefs.getBool("wf_mode_ecg", true);
  if (isECG) {
    simulator.setMode(PhysiologicalSimulator::MODE_ECG);
  } else {
    simulator.setMode(PhysiologicalSimulator::MODE_EEG);
  }

  Serial.println("⚙️  Configuration loaded:");
  Serial.println("   Brightness: " + String(displayBrightness) + "%");
  Serial.println("   Waveform streaming: " + String(waveformStreamingEnabled ? "ON" : "OFF"));
  Serial.println("   Sampling rate: " + String(samplingRate) + " Hz");
  Serial.println("   Vitals interval: " + String(vitalsTransmissionInterval) + "s");
  Serial.println("   Debug mode: " + String(debugModeEnabled ? "ON" : "OFF"));
  Serial.println("   LED alerts: " + String(ledAlertsEnabled ? "ON" : "OFF"));

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

  // ✅ v5.0: REMOVED MQTT credential saving (now using certificates)

  prefs.putString("deviceId", deviceId);
  prefs.putString("serial", serialNumber);
  prefs.putString("patientId", assignedPatientId);
  prefs.putBool("provisioned", isProvisioned);
  prefs.putBool("assigned", isAssigned);
  prefs.putInt("battery", batteryLevel);

  prefs.putInt("batHealth", batteryHealthPercentage);
  // ✅ v5.2.2: Bug #2 fix - REMOVED totalDisconnects persistence
  // Counter should NOT persist across reboots (always starts fresh at 0)

  Serial.println("💾 Configuration saved");
}
