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
#include <Wire.h>

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
   * Initialize QMI8658 IMU on I2C bus
   * @param sda SDA pin (default: GPIO47)
   * @param scl SCL pin (default: GPIO48)
   * @return true if successful
   */
  bool begin(int sda = 47, int scl = 48);

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
  // I2C communication
  uint8_t i2cAddr;
  bool initialized;

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
  float fallThreshold;           // g (default: 2.5)

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

  // I2C helper functions
  uint8_t readRegister(uint8_t reg);
  void readRegisters(uint8_t reg, uint8_t* buffer, uint8_t length);
  void writeRegister(uint8_t reg, uint8_t value);

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
