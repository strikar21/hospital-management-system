/**
 * QMI8658Manager.cpp
 *
 * Implementation of real-time fall and tremor detection
 *
 * @version 1.0.0
 * @date 2025-01-22
 */

#include "QMI8658Manager.h"

// ====================================
// CONSTRUCTOR
// ====================================

QMI8658Manager::QMI8658Manager() {
  initialized = false;
  i2cAddr = QMI8658_I2C_ADDR_PRIMARY;
  i2c_dev = NULL;  // ✅ v5.4.1: Initialize device handle
  consecutive_errors = 0;  // ✅ v5.4.1: Initialize error counter

  // Initialize sensor data
  accelX = accelY = accelZ = 0.0;
  gyroX = gyroY = gyroZ = 0.0;
  temperature = 0.0;

  // Initialize calibration offsets
  accelOffsetX = accelOffsetY = accelOffsetZ = 0.0;

  // Initialize fall detection
  fallDetected = false;
  fallTimestamp = 0;
  fallMagnitude = 0.0;
  lastFallCheck = 0;
  fallCooldownUntil = 0;  // ✅ v5.4.8: No cooldown initially
  fallThreshold = 3.0;  // ✅ v5.6.0: Reduced to 3.0g (clinical standard: 2.5-3.5g) - touch false positives prevented by cooldown

  // Initialize tremor detection
  historyIndex = 0;
  lastTremorCheck = 0;
  tremorFreqMin = 4.0;      // 4 Hz (Parkinson's lower bound)
  tremorFreqMax = 12.0;     // 12 Hz (Parkinson's upper bound)
  tremorAmplitudeMin = 0.1; // 0.1g minimum
  currentTremorFreq = 0.0;
  currentTremorAmp = 0.0;

  // Clear acceleration history buffer
  for (int i = 0; i < TREMOR_BUFFER_SIZE; i++) {
    accelHistory[i] = 0.0;
  }

  // Initialize activity
  currentActivity = STATIONARY;
}

// ====================================
// INITIALIZATION
// ====================================

bool QMI8658Manager::begin(i2c_master_bus_handle_t bus_handle) {
  Serial.println("🔧 Initializing QMI8658 IMU...");

  // ✅ v5.4.1: Validate bus handle
  if (bus_handle == NULL) {
    Serial.println("❌ QMI8658: Invalid bus handle (NULL)");
    Serial.println("   → Ensure FT3168 touch initialized first (creates shared bus)");
    initialized = false;
    return false;
  }

  // ✅ v5.4.1: Power-on delay (critical for IMU stability)
  delay(100);

  // ✅ v5.4.1: Try primary address first (0x6A)
  i2cAddr = QMI8658_I2C_ADDR_PRIMARY;

  i2c_device_config_t dev_config = {};
  dev_config.dev_addr_length = I2C_ADDR_BIT_LEN_7;
  dev_config.device_address = i2cAddr;
  dev_config.scl_speed_hz = 400000;  // 400kHz

  esp_err_t ret = i2c_master_bus_add_device(bus_handle, &dev_config, &i2c_dev);
  if (ret != ESP_OK) {
    Serial.printf("❌ QMI8658: Failed to add device to I2C bus (error %d)\n", ret);

    // ✅ Detailed error messages
    if (ret == ESP_ERR_TIMEOUT) {
      Serial.println("   → I2C timeout (check pull-up resistors)");
    } else if (ret == ESP_ERR_INVALID_ARG) {
      Serial.println("   → Invalid I2C address or config");
    }

    initialized = false;
    return false;
  }

  Serial.println("✅ QMI8658 IMU added to shared I2C bus");

  // ✅ Read WHO_AM_I register to verify device
  uint8_t chipId = 0;
  ret = readRegister(QMI8658_WHO_AM_I, &chipId);

  if (ret != ESP_OK || chipId != QMI8658_CHIP_ID) {
    // Try secondary address (0x6B)
    Serial.printf("⚠️  No response at 0x%02X, trying 0x%02X...\n",
                  QMI8658_I2C_ADDR_PRIMARY, QMI8658_I2C_ADDR_SECONDARY);

    // Remove old device handle
    if (i2c_dev != NULL) {
      i2c_master_bus_rm_device(i2c_dev);
      i2c_dev = NULL;
    }

    // Try secondary address
    i2cAddr = QMI8658_I2C_ADDR_SECONDARY;
    dev_config.device_address = i2cAddr;

    ret = i2c_master_bus_add_device(bus_handle, &dev_config, &i2c_dev);
    if (ret != ESP_OK) {
      Serial.printf("❌ QMI8658: Failed at secondary address too (error %d)\n", ret);
      initialized = false;
      return false;
    }

    ret = readRegister(QMI8658_WHO_AM_I, &chipId);
  }

  if (ret != ESP_OK || chipId != QMI8658_CHIP_ID) {
    Serial.printf("❌ QMI8658 not found! Expected 0x%02X, got 0x%02X\n",
                  QMI8658_CHIP_ID, chipId);
    initialized = false;
    return false;
  }

  Serial.printf("✅ QMI8658 found at I2C address 0x%02X (Chip ID: 0x%02X)\n",
                i2cAddr, chipId);

  // ✅ Soft reset
  writeRegister(QMI8658_RESET, 0xB0);
  delay(10);

  // ✅ Configure CTRL1: Enable accelerometer
  // [7]: SelfTest=0, [6:4]: AccRange=010 (±4g), [3:0]: AccODR=0110 (250Hz)
  writeRegister(QMI8658_CTRL1, 0x26);

  // ✅ Configure CTRL2: Enable gyroscope
  // [7]: SelfTest=0, [6:4]: GyrRange=011 (±512dps), [3:0]: GyrODR=0110 (250Hz)
  writeRegister(QMI8658_CTRL2, 0x36);

  // ✅ Configure CTRL3: Enable sensors
  // [7]: AccEnable=1, [6]: GyrEnable=1, [5:0]: Reserved
  writeRegister(QMI8658_CTRL3, 0xC0);

  // ✅ Configure CTRL7: Enable accelerometer and gyroscope data ready
  writeRegister(QMI8658_CTRL7, 0x03);

  delay(50);  // Allow sensors to stabilize

  initialized = true;
  Serial.println("✅ QMI8658 configured:");
  Serial.println("   - Accelerometer: ±4g @ 250Hz");
  Serial.println("   - Gyroscope: ±512dps @ 250Hz");
  Serial.println("   - Fall threshold: 3.0g");  // ✅ v5.6.0: Clinical standard (2.5-3.5g)
  Serial.println("   - Tremor range: 4-12 Hz");

  return true;
}

void QMI8658Manager::calibrate() {
  if (!initialized) {
    Serial.println("⚠️  Cannot calibrate - IMU not initialized");
    return;
  }

  Serial.println("📍 Calibrating IMU...");
  Serial.println("   ⚠️  Keep device FLAT and STATIONARY for 2 seconds");

  delay(2000);

  // Sample 100 readings
  float sumX = 0, sumY = 0, sumZ = 0;
  for (int i = 0; i < 100; i++) {
    update();
    sumX += accelX;
    sumY += accelY;
    sumZ += accelZ;
    delay(10);
  }

  // Calculate offsets (when flat: X≈0, Y≈0, Z≈1g due to gravity)
  accelOffsetX = sumX / 100.0;
  accelOffsetY = sumY / 100.0;
  accelOffsetZ = (sumZ / 100.0) - 1.0;  // Gravity compensation

  Serial.printf("✅ Calibration complete\n");
  Serial.printf("   Offsets: X=%.3fg, Y=%.3fg, Z=%.3fg\n",
                accelOffsetX, accelOffsetY, accelOffsetZ);
}

// ====================================
// DATA ACQUISITION
// ====================================

void QMI8658Manager::update() {
  if (!initialized) return;

  // Read 6 bytes of accelerometer data (X, Y, Z as 16-bit each)
  uint8_t accelData[6];
  readRegisters(QMI8658_AX_L, accelData, 6);

  int16_t rawAccelX = combineBytes(accelData[0], accelData[1]);
  int16_t rawAccelY = combineBytes(accelData[2], accelData[3]);
  int16_t rawAccelZ = combineBytes(accelData[4], accelData[5]);

  // Read 6 bytes of gyroscope data (X, Y, Z as 16-bit each)
  uint8_t gyroData[6];
  readRegisters(QMI8658_GX_L, gyroData, 6);

  int16_t rawGyroX = combineBytes(gyroData[0], gyroData[1]);
  int16_t rawGyroY = combineBytes(gyroData[2], gyroData[3]);
  int16_t rawGyroZ = combineBytes(gyroData[4], gyroData[5]);

  // Read 2 bytes of temperature data
  uint8_t tempData[2];
  readRegisters(QMI8658_TEMP_L, tempData, 2);
  int16_t rawTemp = combineBytes(tempData[0], tempData[1]);

  // Convert to physical units
  accelX = convertAccel(rawAccelX) - accelOffsetX;
  accelY = convertAccel(rawAccelY) - accelOffsetY;
  accelZ = convertAccel(rawAccelZ) - accelOffsetZ;

  gyroX = convertGyro(rawGyroX);
  gyroY = convertGyro(rawGyroY);
  gyroZ = convertGyro(rawGyroZ);

  temperature = convertTemp(rawTemp);
}

void QMI8658Manager::getAcceleration(float& x, float& y, float& z) {
  x = accelX;
  y = accelY;
  z = accelZ;
}

void QMI8658Manager::getGyroscope(float& x, float& y, float& z) {
  x = gyroX;
  y = gyroY;
  z = gyroZ;
}

float QMI8658Manager::getTemperature() {
  return temperature;
}

// ====================================
// FALL DETECTION
// ====================================

bool QMI8658Manager::checkForFall() {
  if (!initialized) return false;

  unsigned long now = millis();

  // ✅ v5.4.8: Check cooldown period (prevent re-triggering after manual clear)
  if (now < fallCooldownUntil) {
    return false;  // In cooldown - ignore all acceleration
  }

  // ✅ v5.4.8: Check every 200ms (5 Hz) to reduce CPU load and improve touch responsiveness
  // (Falls take ~100-300ms to develop, so 200ms sampling is still safe)
  if (now - lastFallCheck < 200) {
    return fallDetected;
  }
  lastFallCheck = now;

  // Calculate acceleration magnitude
  float magnitude = getAccelerationMagnitude();

  // Fall detected: sudden acceleration > threshold
  if (magnitude > fallThreshold) {
    if (!fallDetected) {  // New fall event
      fallDetected = true;
      fallTimestamp = now;
      fallMagnitude = magnitude;

      Serial.printf("🚨 FALL DETECTED!\n");
      Serial.printf("   Acceleration: %.2fg (threshold: %.2fg)\n",
                    magnitude, fallThreshold);
      Serial.printf("   Vector: X=%.2f, Y=%.2f, Z=%.2f\n",
                    accelX, accelY, accelZ);
    }
  }

  // Auto-clear fall flag after 5 seconds (to avoid spam)
  if (fallDetected && (now - fallTimestamp > 5000)) {
    Serial.println("   Fall flag auto-cleared after 5s");
    fallDetected = false;
  }

  return fallDetected;
}

float QMI8658Manager::getAccelerationMagnitude() {
  return calculateMagnitude(accelX, accelY, accelZ);
}

float QMI8658Manager::getFallConfidence() {
  if (!fallDetected) return 0.0;

  // Confidence based on how much threshold was exceeded
  float excess = (fallMagnitude - fallThreshold) / fallThreshold;
  float confidence = 0.75 + (excess * 0.25);  // 0.75-1.0 range

  return constrain(confidence, 0.0, 1.0);
}

void QMI8658Manager::clearFallFlag() {
  fallDetected = false;
  // ✅ v5.4.8: Set 10-second cooldown to prevent immediate re-triggering
  fallCooldownUntil = millis() + 10000;  // 10 seconds from now
  Serial.println("   Fall flag manually cleared (10s cooldown active)");
}

// ====================================
// TREMOR DETECTION
// ====================================

bool QMI8658Manager::checkForTremor() {
  if (!initialized) return false;

  unsigned long now = millis();

  // Sample at 100Hz for tremor analysis (every 10ms)
  if (now - lastTremorCheck < 10) {
    return false;
  }
  lastTremorCheck = now;

  // Get current acceleration magnitude
  float magnitude = getAccelerationMagnitude();

  // Store in circular buffer
  accelHistory[historyIndex] = magnitude;
  historyIndex = (historyIndex + 1) % TREMOR_BUFFER_SIZE;

  // Need at least one full buffer before analyzing (320ms of data)
  static int sampleCount = 0;
  sampleCount++;
  if (sampleCount < TREMOR_BUFFER_SIZE) {
    return false;  // Not enough samples yet
  }

  // Analyze tremor every 320ms (when buffer is full)
  if (sampleCount % TREMOR_BUFFER_SIZE == 0) {
    analyzeTremor();
  }

  // Tremor detected if frequency in range AND sufficient amplitude
  bool tremorActive = (currentTremorFreq >= tremorFreqMin &&
                       currentTremorFreq <= tremorFreqMax &&
                       currentTremorAmp >= tremorAmplitudeMin);

  if (tremorActive) {
    Serial.printf("⚠️  TREMOR: %.1f Hz, %.3fg\n",
                  currentTremorFreq, currentTremorAmp);
  }

  return tremorActive;
}

float QMI8658Manager::getTremorFrequency() {
  return currentTremorFreq;
}

float QMI8658Manager::getTremorAmplitude() {
  return currentTremorAmp;
}

void QMI8658Manager::analyzeTremor() {
  // Calculate mean
  float mean = 0.0;
  for (int i = 0; i < TREMOR_BUFFER_SIZE; i++) {
    mean += accelHistory[i];
  }
  mean /= TREMOR_BUFFER_SIZE;

  // Count zero-crossings (simplified frequency estimation)
  int zeroCrossings = 0;
  for (int i = 1; i < TREMOR_BUFFER_SIZE; i++) {
    bool prevAboveMean = (accelHistory[i-1] >= mean);
    bool currAboveMean = (accelHistory[i] >= mean);
    if (prevAboveMean != currAboveMean) {
      zeroCrossings++;
    }
  }

  // Frequency = (crossings / 2) / window_duration
  // Window duration = 32 samples @ 100Hz = 0.32s
  currentTremorFreq = (zeroCrossings / 2.0) / 0.32;  // Hz

  // Calculate amplitude (peak-to-peak)
  float minVal = accelHistory[0];
  float maxVal = accelHistory[0];
  for (int i = 1; i < TREMOR_BUFFER_SIZE; i++) {
    if (accelHistory[i] < minVal) minVal = accelHistory[i];
    if (accelHistory[i] > maxVal) maxVal = accelHistory[i];
  }
  currentTremorAmp = maxVal - minVal;
}

// ====================================
// ACTIVITY CLASSIFICATION
// ====================================

QMI8658Manager::Activity QMI8658Manager::classifyActivity() {
  if (!initialized) return STATIONARY;

  // Check for fall first (highest priority)
  if (fallDetected) {
    currentActivity = FALL_DETECTED;
    return FALL_DETECTED;
  }

  float magnitude = getAccelerationMagnitude();

  // Activity thresholds (empirical values)
  if (magnitude > 2.0) {
    currentActivity = RUNNING;
  } else if (magnitude > 1.2) {
    currentActivity = WALKING;
  } else {
    currentActivity = STATIONARY;
  }

  return currentActivity;
}

const char* QMI8658Manager::getActivityString() {
  switch (currentActivity) {
    case STATIONARY:    return "STATIONARY";
    case WALKING:       return "WALKING";
    case RUNNING:       return "RUNNING";
    case FALL_DETECTED: return "FALLING";
    default:            return "UNKNOWN";
  }
}

// ====================================
// CONFIGURATION
// ====================================

void QMI8658Manager::setFallThreshold(float threshold) {
  fallThreshold = threshold;
  Serial.printf("🔧 Fall threshold updated: %.2fg\n", threshold);
}

void QMI8658Manager::setTremorParameters(float minFreq, float maxFreq, float minAmplitude) {
  tremorFreqMin = minFreq;
  tremorFreqMax = maxFreq;
  tremorAmplitudeMin = minAmplitude;
  Serial.printf("🔧 Tremor parameters updated:\n");
  Serial.printf("   Frequency: %.1f-%.1f Hz\n", minFreq, maxFreq);
  Serial.printf("   Amplitude: >%.3fg\n", minAmplitude);
}

// ====================================
// DIAGNOSTICS
// ====================================

bool QMI8658Manager::isConnected() {
  if (!initialized || i2c_dev == NULL) return false;

  uint8_t chipId = 0;
  esp_err_t ret = readRegister(QMI8658_WHO_AM_I, &chipId);
  return (ret == ESP_OK && chipId == QMI8658_CHIP_ID);
}

void QMI8658Manager::printDiagnostics() {
  if (!initialized) {
    Serial.println("❌ IMU not initialized");
    return;
  }

  Serial.println("\n📊 QMI8658 DIAGNOSTICS");
  Serial.println("========================");
  Serial.printf("Accelerometer: X=%.3fg, Y=%.3fg, Z=%.3fg (Mag: %.3fg)\n",
                accelX, accelY, accelZ, getAccelerationMagnitude());
  Serial.printf("Gyroscope:     X=%.1fdps, Y=%.1fdps, Z=%.1fdps\n",
                gyroX, gyroY, gyroZ);
  Serial.printf("Temperature:   %.2f°C\n", temperature);
  Serial.printf("Activity:      %s\n", getActivityString());
  Serial.printf("Fall detected: %s\n", fallDetected ? "YES" : "NO");
  Serial.printf("Tremor:        %.1f Hz @ %.3fg\n", currentTremorFreq, currentTremorAmp);
  Serial.println("========================\n");
}

// ====================================
// I2C HELPER FUNCTIONS (PRIVATE)
// ✅ v5.4.1: Rewritten to use NEW ESP-IDF I2C driver API
// ====================================

esp_err_t QMI8658Manager::readRegister(uint8_t reg, uint8_t* value) {
  if (i2c_dev == NULL) {
    consecutive_errors++;
    return ESP_ERR_INVALID_STATE;
  }

  // ✅ Use NEW driver transmit-receive API
  esp_err_t ret = i2c_master_transmit_receive(
    i2c_dev,
    &reg, 1,        // Write register address
    value, 1,       // Read 1 byte
    1000            // Timeout: 1000ms
  );

  if (ret != ESP_OK) {
    consecutive_errors++;
    Serial.printf("❌ I2C read error (reg 0x%02X): %d (consecutive: %d)\n",
                  reg, ret, consecutive_errors);

    // ✅ Trigger bus health warning if too many errors
    if (consecutive_errors >= MAX_CONSECUTIVE_ERRORS) {
      Serial.println("⚠️  WARNING: I2C bus health degraded!");
      Serial.println("   → Check connections, power, and pull-up resistors");
    }
  } else {
    consecutive_errors = 0;  // Reset on success
  }

  return ret;
}

esp_err_t QMI8658Manager::readRegisters(uint8_t reg, uint8_t* buffer, uint8_t length) {
  if (i2c_dev == NULL) {
    consecutive_errors++;
    return ESP_ERR_INVALID_STATE;
  }

  esp_err_t ret = i2c_master_transmit_receive(
    i2c_dev,
    &reg, 1,
    buffer, length,
    1000
  );

  if (ret != ESP_OK) {
    consecutive_errors++;
    Serial.printf("❌ I2C bulk read error (reg 0x%02X, len %d): %d\n",
                  reg, length, ret);
  } else {
    consecutive_errors = 0;
  }

  return ret;
}

esp_err_t QMI8658Manager::writeRegister(uint8_t reg, uint8_t value) {
  if (i2c_dev == NULL) {
    consecutive_errors++;
    return ESP_ERR_INVALID_STATE;
  }

  uint8_t data[2] = {reg, value};

  esp_err_t ret = i2c_master_transmit(
    i2c_dev,
    data, 2,
    1000
  );

  if (ret != ESP_OK) {
    consecutive_errors++;
    Serial.printf("❌ I2C write error (reg 0x%02X = 0x%02X): %d\n",
                  reg, value, ret);
  } else {
    consecutive_errors = 0;
  }

  return ret;
}

// ====================================
// DATA CONVERSION (PRIVATE)
// ====================================

int16_t QMI8658Manager::combineBytes(uint8_t lsb, uint8_t msb) {
  return (int16_t)((msb << 8) | lsb);
}

float QMI8658Manager::convertAccel(int16_t rawValue) {
  // ±4g range: 16-bit signed → ±32768 = ±4g
  // Scale factor: 4g / 32768 = 0.0001221 g/LSB
  return rawValue * 0.0001221;
}

float QMI8658Manager::convertGyro(int16_t rawValue) {
  // ±512dps range: 16-bit signed → ±32768 = ±512dps
  // Scale factor: 512 / 32768 = 0.015625 dps/LSB
  return rawValue * 0.015625;
}

float QMI8658Manager::convertTemp(int16_t rawValue) {
  // Temperature formula from datasheet:
  // Temp(°C) = rawValue / 256.0
  return rawValue / 256.0;
}

float QMI8658Manager::calculateMagnitude(float x, float y, float z) {
  return sqrt(x*x + y*y + z*z);
}
