# ESP32-S3 I2C Bus Conflict Fix

**Device**: Waveshare ESP32-S3-Touch-AMOLED-1.64
**Issue**: QMI8658 IMU fails with "I2C bus id(0) has already been acquired"
**Root Cause**: Mixing NEW ESP-IDF I2C driver with old Arduino Wire library

---

## Hardware Configuration (from datasheet)

### I2C Bus 0 (Shared by Touch + IMU):
- **SDA**: GPIO 47
- **SCL**: GPIO 48
- **Frequency**: 400 kHz
- **Pull-ups**: Internal (enabled in FT3168.cpp)

### Devices on Bus 0:
1. **FT3168 Touch Controller** (Address: 0x38)
   - Currently uses: NEW ESP-IDF driver (`i2c_new_master_bus`)
   - File: `FT3168.cpp`

2. **QMI8658C IMU** (Address: 0x6A or 0x6B)
   - Currently uses: OLD Arduino Wire library
   - File: `QMI8658Manager.cpp`
   - **CONFLICT**: Can't mix drivers on same bus!

### NFC Module (Separate Bus 1):
- **SDA**: GPIO 16
- **SCL**: GPIO 17
- **IRQ**: GPIO 25
- Uses: Arduino `TwoWire(1)` - separate bus, no conflict

---

## Problem Analysis

**Error from serial log**:
```
E (7263) i2c.common: I2C bus id(0) has already been acquired
E (7263) i2c.common: acquire bus failed
```

**What happened**:
1. FT3168 init calls `i2c_new_master_bus()` → acquires bus 0
2. QMI8658 init calls `Wire.begin(47, 48)` → tries to acquire bus 0 again
3. ESP-IDF blocks second acquisition → IMU fails

**Why mixing drivers fails**:
- NEW driver: `i2c_master_bus_handle_t` (ESP-IDF v5.0+)
- OLD driver: `Wire` (Arduino compatibility layer)
- Both cannot coexist on same bus ID

---

## Solution: Share I2C Bus Handle

### Option 1: Make Touch Controller Export Bus Handle (RECOMMENDED)

Modify `FT3168.cpp` to expose the bus handle so QMI8658 can reuse it.

**FT3168.h** (add):
```cpp
// Global I2C bus handle (shared with other devices)
extern i2c_master_bus_handle_t shared_i2c_bus;

// Function to get bus handle
i2c_master_bus_handle_t getSharedI2CBus();
```

**FT3168.cpp** (modify):
```cpp
// Make bus handle global so IMU can share it
i2c_master_bus_handle_t shared_i2c_bus = NULL;

i2c_master_bus_handle_t getSharedI2CBus() {
  return shared_i2c_bus;
}

void Touch_Init(void) {
  // ✅ Initialize I2C bus (ONLY if not already done)
  if (shared_i2c_bus == NULL) {
    i2c_master_bus_config_t bus_config = {};
    bus_config.clk_source = I2C_CLK_SRC_DEFAULT;
    bus_config.sda_io_num = EXAMPLE_PIN_NUM_TOUCH_SDA;  // GPIO 47
    bus_config.scl_io_num = EXAMPLE_PIN_NUM_TOUCH_SCL;  // GPIO 48
    bus_config.i2c_port = I2C_NUM_0;
    bus_config.flags.enable_internal_pullup = true;

    ESP_ERROR_CHECK(i2c_new_master_bus(&bus_config, &shared_i2c_bus));
    Serial.println("✅ I2C Bus 0 initialized (shared by touch + IMU)");
  }

  // Add FT3168 device to shared bus
  i2c_device_config_t dev_cfg = {};
  dev_cfg.dev_addr_length = I2C_ADDR_BIT_LEN_7;
  dev_cfg.device_address = I2C_ADDR_FT3168;
  dev_cfg.scl_speed_hz = 400000;

  ESP_ERROR_CHECK(i2c_master_bus_add_device(shared_i2c_bus, &dev_cfg, &i2c_dev_handle));
}
```

**QMI8658Manager.h** (modify):
```cpp
#include <driver/i2c_master.h>

class QMI8658Manager {
public:
  /**
   * Initialize using shared I2C bus handle
   * @param bus_handle I2C bus handle from touch controller
   * @return true if successful
   */
  bool begin(i2c_master_bus_handle_t bus_handle);

private:
  i2c_master_bus_handle_t i2c_bus;
  i2c_master_dev_handle_t i2c_dev;
  uint8_t i2cAddr;
};
```

**QMI8658Manager.cpp** (rewrite I2C functions):
```cpp
#include <driver/i2c_master.h>

bool QMI8658Manager::begin(i2c_master_bus_handle_t bus_handle) {
  if (bus_handle == NULL) {
    Serial.println("❌ NULL I2C bus handle");
    return false;
  }

  i2c_bus = bus_handle;

  // Try address 0x6A first
  i2cAddr = QMI8658_I2C_ADDR;

  // Add QMI8658 device to shared bus
  i2c_device_config_t dev_cfg = {};
  dev_cfg.dev_addr_length = I2C_ADDR_BIT_LEN_7;
  dev_cfg.device_address = i2cAddr;
  dev_cfg.scl_speed_hz = 400000;

  esp_err_t ret = i2c_master_bus_add_device(i2c_bus, &dev_cfg, &i2c_dev);
  if (ret != ESP_OK) {
    // Try alternate address 0x6B
    i2cAddr = QMI8658_I2C_ADDR_ALT;
    dev_cfg.device_address = i2cAddr;
    ret = i2c_master_bus_add_device(i2c_bus, &dev_cfg, &i2c_dev);

    if (ret != ESP_OK) {
      Serial.println("❌ QMI8658 not found on I2C bus");
      return false;
    }
  }

  // Read WHO_AM_I register
  uint8_t whoami = readRegister(QMI8658_REG_WHO_AM_I);
  if (whoami != QMI8658_CHIP_ID) {
    Serial.printf("❌ QMI8658 wrong chip ID: 0x%02X (expected 0x05)\n", whoami);
    return false;
  }

  Serial.println("✅ QMI8658 initialized on shared I2C bus");
  initialized = true;
  return true;
}

uint8_t QMI8658Manager::readRegister(uint8_t reg) {
  uint8_t data = 0;

  // Write register address, then read
  esp_err_t ret = i2c_master_transmit_receive(
    i2c_dev,
    &reg, 1,          // Write: register address
    &data, 1,         // Read: 1 byte
    pdMS_TO_TICKS(1000)
  );

  if (ret != ESP_OK) {
    Serial.printf("❌ I2C read error: %d\n", ret);
    return 0xFF;
  }

  return data;
}

void QMI8658Manager::writeRegister(uint8_t reg, uint8_t value) {
  uint8_t data[2] = {reg, value};

  esp_err_t ret = i2c_master_transmit(
    i2c_dev,
    data, 2,
    pdMS_TO_TICKS(1000)
  );

  if (ret != ESP_OK) {
    Serial.printf("❌ I2C write error: %d\n", ret);
  }
}

void QMI8658Manager::readRegisters(uint8_t reg, uint8_t* buffer, uint8_t length) {
  esp_err_t ret = i2c_master_transmit_receive(
    i2c_dev,
    &reg, 1,              // Write: register address
    buffer, length,       // Read: multiple bytes
    pdMS_TO_TICKS(1000)
  );

  if (ret != ESP_OK) {
    Serial.printf("❌ I2C read burst error: %d\n", ret);
  }
}
```

**main .ino** (modify IMU init):
```cpp
// After touch init, before IMU init:
extern i2c_master_bus_handle_t shared_i2c_bus;

// ✅ Initialize IMU using shared I2C bus
Serial.println("🔧 Initializing QMI8658 IMU on shared I2C bus...");
if (shared_i2c_bus != NULL) {
  imuAvailable = imuSensor.begin(shared_i2c_bus);
  if (imuAvailable) {
    Serial.println("✅ QMI8658 IMU initialized (shared bus with touch)");
    imuSensor.calibrate();
  }
} else {
  Serial.println("❌ I2C bus not initialized by touch controller");
}
```

---

## SPIFFS Fix

**Error**:
```
❌ SPIFFS mount failed
```

**Root Cause**: Partition table doesn't allocate SPIFFS partition, or it's not formatted.

**Fix**:

**Option 1: Force format on first mount**
```cpp
// In setup():
Serial.println("📂 Mounting SPIFFS...");
if (!SPIFFS.begin(true)) {  // true = format if mount fails
  Serial.println("❌ SPIFFS mount failed even after format");
  Serial.println("⚠️ CA cert loading disabled - insecure mode");
} else {
  Serial.println("✅ SPIFFS mounted");
  loadCACertificate();
}
```

**Option 2: Use LittleFS instead (more reliable)**
```cpp
#include <LittleFS.h>

// Replace all SPIFFS.* with LittleFS.*
if (!LittleFS.begin(true)) {
  Serial.println("❌ LittleFS mount failed");
}
```

**Option 3: Check partition table**

Use **Arduino IDE** → **Tools** → **Partition Scheme**:
- Select: **"16M Flash (3MB APP/9.9MB FATFS)"**
- This allocates 9.9MB for SPIFFS

Or in **PlatformIO**:
```ini
[env:esp32-s3-devkitc-1]
board_build.partitions = default_16MB.csv
```

---

## Testing Checklist

After fixes:

- [ ] Touch controller still works
- [ ] IMU chip ID reads correctly (0x05)
- [ ] Fall detection triggers on shake
- [ ] SPIFFS mounts successfully
- [ ] CA certificate loads
- [ ] No I2C errors in serial log

---

## Summary

**Root Issues**:
1. **I2C Bus Conflict**: Touch uses NEW driver, IMU uses OLD driver → can't mix
2. **SPIFFS Mount**: Partition not formatted or not allocated

**Fixes**:
1. **Share I2C bus handle** from touch to IMU (use NEW driver for both)
2. **Force SPIFFS format** on first mount with `begin(true)`

**Estimated Fix Time**: 2 hours (code changes + testing)

---

**Created**: 2025-11-22
**Status**: Ready for implementation
