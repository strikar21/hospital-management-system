/**
 * QMI8658Manager.h
 *
 * Real-time fall detection and tremor monitoring using QMI8658 6-axis IMU
 *
 * Hardware: Waveshare ESP32-S3-Touch-AMOLED-1.64
 * IMU: QMI8658C (3-axis accelerometer + 3-axis gyroscope + temperature)
 * I2C: Shared with FT3168 touch controller (SDA=GPIO47, SCL=GPIO48)
 *
 * Features:
 * - Fall detection (sudden acceleration >2.5g)
 * - Tremor detection (4-12 Hz Parkinson's range)
 * - Activity classification (stationary, walking, running, falling)
 * - Real-time motion data for MQTT streaming
 *
 * @version 1.0.0
 * @date 2025-01-22
 */

#ifndef QMI8658_MANAGER_H
#define QMI8658_MANAGER_H

#include <Arduino.h>
#include <esp_idf_version.h>
// ❌ v5.4.1: REMOVED Wire library (caused I2C bus conflict with FT3168 touch)
// #include <Wire.h>

// ✅ v5.4.1: Use NEW ESP-IDF I2C driver API (shared bus with touch controller)
#include <esp_err.h>

// ESP-IDF v5.2+ uses new I2C driver API (redesigned in v5.2, not v5.0)
#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 2, 0)
    #include <driver/i2c_master.h>
#else
    #include <driver/i2c.h>
    // Define compatibility types for older ESP-IDF
    typedef void* i2c_master_bus_handle_t;
    typedef void* i2c_master_dev_handle_t;
#endif

// QMI8658C I2C Address (may be 0x6A or 0x6B depending on SA0 pin)
#define QMI8658_I2C_ADDR_PRIMARY   0x6A
#define QMI8658_I2C_ADDR_SECONDARY 0x6B

// QMI8658C Register Map
#define QMI8658_WHO_AM_I           0x00
#define QMI8658_CTRL1              0x02
#define QMI8658_CTRL2              0x03
#define QMI8658_CTRL3              0x04
#define QMI8658_CTRL7              0x08
#define QMI8658_TEMP_L             0x33
#define QMI8658_AX_L               0x35
#define QMI8658_GX_L               0x3B
#define QMI8658_RESET              0x60

// Expected WHO_AM_I value
#define QMI8658_CHIP_ID            0x05

class QMI8658Manager {
public:
  // Activity classification enum
  enum Activity {
    STATIONARY    = 0,  // Sitting, lying down, standing still
    WALKING       = 1,  // Normal walking
    RUNNING       = 2,  // Running, fast walking
    FALL_DETECTED = 3   // Fall detected (renamed from FALLING to avoid Arduino.h macro conflict)
  };

  // Constructor
  QMI8658Manager();

  // ====================================
  // INITIALIZATION
  // ====================================

  /**
   * Initialize QMI8658 IMU using shared I2C bus handle
   * ✅ v5.4.1: Now uses shared bus created by FT3168 touch controller
   * @param bus_handle Shared I2C bus handle (from FT3168.h: shared_i2c_bus)
   * @return true if successful
   */
  bool begin(i2c_master_bus_handle_t bus_handle);

  /**
   * Calibrate IMU (call when device is stationary)
   * Calculates zero offsets for accelerometer
   */
  void calibrate();

  // ====================================
  // DATA ACQUISITION
  // ====================================

  /**
   * Update sensor readings (call every loop iteration)
   * Fetches latest accelerometer, gyroscope, and temperature data
   */
  void update();

  /**
   * Get accelerometer data in g (1g = 9.81 m/s²)
   * @param x X-axis acceleration (output)
   * @param y Y-axis acceleration (output)
   * @param z Z-axis acceleration (output)
   */
  void getAcceleration(float& x, float& y, float& z);

  /**
   * Get gyroscope data in degrees per second (dps)
   * @param x X-axis rotation rate (output)
   * @param y Y-axis rotation rate (output)
   * @param z Z-axis rotation rate (output)
   */
  void getGyroscope(float& x, float& y, float& z);

  /**
   * Get IMU temperature in Celsius
   * @return Temperature in °C
   */
  float getTemperature();

  // ====================================
  // FALL DETECTION
  // ====================================

  /**
   * Check for fall event
   * Detects sudden acceleration spikes (>2.5g)
   * @return true if fall detected in last 5 seconds
   */
  bool checkForFall();

  /**
   * Get current acceleration magnitude
   * @return Magnitude in g (sqrt(x² + y² + z²))
   */
  float getAccelerationMagnitude();

  /**
   * Get fall confidence score
   * @return 0.0 (no fall) to 1.0 (definite fall)
   */
  float getFallConfidence();

  /**
   * Reset fall detection flag
   * Call after handling fall alert
   */
  void clearFallFlag();

  // ====================================
  // TREMOR DETECTION
  // ====================================

  /**
   * Check for tremor activity
   * Analyzes acceleration frequency (Parkinson's range: 4-12 Hz)
   * @return true if tremor detected
   */
  bool checkForTremor();

  /**
   * Get tremor frequency
   * @return Dominant frequency in Hz (0 if no tremor)
   */
  float getTremorFrequency();

  /**
   * Get tremor amplitude
   * @return Peak-to-peak amplitude in g
   */
  float getTremorAmplitude();

  // ====================================
  // ACTIVITY CLASSIFICATION
  // ====================================

  /**
   * Classify current activity based on motion
   * @return Activity enum (STATIONARY, WALKING, RUNNING, FALLING)
   */
  Activity classifyActivity();

  /**
   * Get activity as string
   * @return "STATIONARY", "WALKING", "RUNNING", or "FALLING"
   */
  const char* getActivityString();

  // ====================================
  // CONFIGURATION
  // ====================================

  /**
   * Set fall detection threshold
   * @param threshold Acceleration in g (default: 2.5g)
   */
  void setFallThreshold(float threshold);

  /**
   * Set tremor detection parameters
   * @param minFreq Minimum frequency in Hz (default: 4.0)
   * @param maxFreq Maximum frequency in Hz (default: 12.0)
   * @param minAmplitude Minimum amplitude in g (default: 0.1)
   */
  void setTremorParameters(float minFreq, float maxFreq, float minAmplitude);

  // ====================================
  // DIAGNOSTICS
  // ====================================

  /**
   * Check if IMU is connected and responsive
   * @return true if IMU responds to I2C
   */
  bool isConnected();

  /**
   * Print raw sensor data to Serial
   * For debugging and calibration
   */
  void printDiagnostics();

private:
  // ✅ v5.4.1: I2C communication using NEW driver API
  uint8_t i2cAddr;
  bool initialized;
  i2c_master_dev_handle_t i2c_dev;  // ✅ Device handle (added to shared bus)

  // ✅ v5.4.1: Error tracking for bus health monitoring
  uint8_t consecutive_errors;
  static const uint8_t MAX_CONSECUTIVE_ERRORS = 5;

  // Sensor data
  float accelX, accelY, accelZ;  // g
  float gyroX, gyroY, gyroZ;     // dps
  float temperature;              // °C

  // Calibration offsets
  float accelOffsetX, accelOffsetY, accelOffsetZ;

  // Fall detection state
  bool fallDetected;
  unsigned long fallTimestamp;
  float fallMagnitude;
  unsigned long lastFallCheck;
  unsigned long fallCooldownUntil;  // ✅ v5.4.8: Prevent re-triggering after manual clear
  float fallThreshold;           // g (default: 2.0 dynamic)

  // ✅ v5.8.11: Spike rejection filter (prevents touch-induced false positives)
  static const int FALL_CONFIRMATION_SAMPLES = 2;  // Require 2 consecutive high readings
  float previousDynamicAccel;    // Previous reading for spike detection
  int highAccelCount;            // Counter for consecutive high acceleration readings

  // Tremor detection state
  static const int TREMOR_BUFFER_SIZE = 32;  // 320ms @ 100Hz
  float accelHistory[TREMOR_BUFFER_SIZE];
  int historyIndex;
  unsigned long lastTremorCheck;
  float tremorFreqMin;           // Hz (default: 4.0)
  float tremorFreqMax;           // Hz (default: 12.0)
  float tremorAmplitudeMin;      // g (default: 0.1)
  float currentTremorFreq;
  float currentTremorAmp;

  // Activity classification
  Activity currentActivity;

  // ✅ v5.4.1: I2C helper functions using NEW driver API
  esp_err_t readRegister(uint8_t reg, uint8_t* value);
  esp_err_t readRegisters(uint8_t reg, uint8_t* buffer, uint8_t length);
  esp_err_t writeRegister(uint8_t reg, uint8_t value);

  // Data conversion
  int16_t combineBytes(uint8_t lsb, uint8_t msb);
  float convertAccel(int16_t rawValue);
  float convertGyro(int16_t rawValue);
  float convertTemp(int16_t rawValue);

  // Analysis functions
  float calculateMagnitude(float x, float y, float z);
  void analyzeTremor();
};

#endif // QMI8658_MANAGER_H
