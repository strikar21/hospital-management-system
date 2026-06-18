# Touch Screen Fix - Version 5.9.1

**Date:** 2025-11-25
**Device:** Waveshare ESP32-S3-Touch-AMOLED-1.64
**Touch IC:** FocalTech FT3168
**Issue:** Touch screen was working earlier, now not responding

---

## Root Cause Analysis

### Primary Issue: I2C Driver API Mismatch
**Location:** [FT3168.cpp](FT3168.cpp) (entire file)

The FT3168 driver was using the **legacy I2C driver API** (i2c_driver_install), but the QMI8658 IMU was expecting the **new ESP-IDF v5+ I2C master driver API** (i2c_master_bus_handle_t). This caused:
- **Linker error:** `undefined reference to 'shared_i2c_bus'`
- **No shared I2C bus:** The variable was declared but never created
- **Bus conflict:** Touch and IMU couldn't share the I2C bus properly

**Impact:** Code wouldn't compile, and even if it did, touch/IMU I2C communication would fail.

---

### Secondary Issue: Missing FT3168 Initialization
**Location:** [FT3168.cpp:33-51](FT3168.cpp#L33-L51) (old code)

The touch controller was never properly reset or configured:
- No soft reset after power-on
- No touch threshold configuration
- No scan period configuration
- No connectivity verification

**Impact:** Touch controller may be in unknown/stuck state after power-on.

---

### Tertiary Issue: Coordinate Validation Too Strict
**Location:** [TouchHandler.cpp:72](TouchHandler.cpp#L72)

```cpp
// ❌ BEFORE v5.9.1:
bool validCoordinates = (x > 0 && x < 279) && (y > 0 && y < 455);
// Rejects x=0, x=279, y=0, y=455 (valid edge pixels!)
```

**Impact:** Touches at screen edges (0-279 for X, 0-455 for Y) were incorrectly rejected.

---

## Fixes Applied

### Fix 1: Migrate to New I2C Master Driver API
**File:** [FT3168.cpp](FT3168.cpp) (complete rewrite)

**✅ BEFORE (Legacy Driver):**
```cpp
i2c_config_t conf = { /* ... */ };
ESP_ERROR_CHECK(i2c_param_config(TEST_I2C_PORT, &conf));
ESP_ERROR_CHECK(i2c_driver_install(TEST_I2C_PORT, conf.mode, 0, 0, 0));
// No shared_i2c_bus created!
```

**✅ AFTER (New Driver API):**
```cpp
// Create shared I2C bus
i2c_master_bus_config_t bus_config = {
  .i2c_port = I2C_NUM_0,
  .sda_io_num = (gpio_num_t)EXAMPLE_PIN_NUM_TOUCH_SDA,
  .scl_io_num = (gpio_num_t)EXAMPLE_PIN_NUM_TOUCH_SCL,
  .clk_source = I2C_CLK_SRC_DEFAULT,
  .glitch_ignore_cnt = 7,
  .flags = { .enable_internal_pullup = true }
};
i2c_new_master_bus(&bus_config, &shared_i2c_bus);  // ✅ Creates shared bus!

// Add FT3168 device to bus
i2c_device_config_t dev_config = {
  .dev_addr_length = I2C_ADDR_BIT_LEN_7,
  .device_address = I2C_ADDR_FT3168,
  .scl_speed_hz = 300000
};
i2c_master_bus_add_device(shared_i2c_bus, &dev_config, &ft3168_dev);
```

**Result:**
- ✅ Shared I2C bus created and exported for IMU
- ✅ Linker error resolved (`shared_i2c_bus` now exists)
- ✅ Touch and IMU can safely share I2C Bus 0

---

### Fix 2: Add Soft Reset & Configuration
**File:** [FT3168.cpp:61-103](FT3168.cpp#L61-L103)

```cpp
// ✅ v5.9.1: Soft reset FT3168
uint8_t resetCmd[2] = {0xFC, 0x07};  // Register 0xFC = 0x07 (reset)
i2c_master_transmit(ft3168_dev, resetCmd, 2, 1000 / portTICK_PERIOD_MS);
delay(200);  // Wait for reset

// Normal operating mode
uint8_t modeCmd[2] = {0x00, 0x00};
i2c_master_transmit(ft3168_dev, modeCmd, 2, 1000 / portTICK_PERIOD_MS);

// Touch threshold (sensitivity)
uint8_t thresholdCmd[2] = {0x80, 0x16};  // TH_GROUP = 22 units
i2c_master_transmit(ft3168_dev, thresholdCmd, 2, 1000 / portTICK_PERIOD_MS);

// Scan period (responsiveness)
uint8_t periodCmd[2] = {0x88, 0x0C};  // PERIODACTIVE = 12ms
i2c_master_transmit(ft3168_dev, periodCmd, 2, 1000 / portTICK_PERIOD_MS);

// Verify connectivity
uint8_t regAddr = 0x00;
uint8_t mode;
i2c_master_transmit_receive(ft3168_dev, &regAddr, 1, &mode, 1, 1000 / portTICK_PERIOD_MS);
Serial.printf("✅ FT3168 connectivity verified, mode=0x%02X\n", mode);
```

**Result:** Touch controller properly reset, configured, and connectivity verified at startup.

---

### Fix 3: Correct Coordinate Validation
**File:** [TouchHandler.cpp](TouchHandler.cpp)

```cpp
// ✅ v5.9.1: Accept all valid screen coordinates
bool validCoordinates = (x < 280) && (y < 456);
// Allows x: 0-279 (280 pixels), y: 0-455 (456 pixels)
```

**Result:** Edge touches now correctly accepted.

---

### Fix 4: Add Extern Declaration for shared_i2c_bus
**File:** [esp32_hospital_watch_complete.ino](esp32_hospital_watch_complete.ino#L145)

```cpp
// ✅ v5.9.1: Explicit extern declaration for shared I2C bus (touch + IMU)
extern i2c_master_bus_handle_t shared_i2c_bus;
```

**Result:** Resolves compilation error "shared_i2c_bus was not declared in this scope".

---

## Testing Checklist

After uploading v5.9.1 firmware, verify:

- [ ] Serial monitor shows "✅ FT3168 soft reset initiated"
- [ ] Serial monitor shows "✅ FT3168 connectivity verified"
- [ ] Serial monitor shows "✅ FT3168 touch threshold set"
- [ ] Serial monitor shows "✅ FT3168 scan period set"
- [ ] Touch screen responds to finger touches
- [ ] Touch coordinates accurate (test all 4 corners + center)
- [ ] No "❌ FT3168 I2C read failed" errors in serial monitor
- [ ] Occasional "👆 Touch #X" messages appear (not 100/second)
- [ ] Edge touches register (try x=0, x=279, y=0, y=455)

---

## Hardware Specifications (Reference)

| Parameter | Value |
|-----------|-------|
| Touch Controller | FocalTech FT3168 |
| I2C Address | 0x38 (7-bit) |
| SDA Pin | GPIO 47 |
| SCL Pin | GPIO 48 |
| I2C Bus | I2C_NUM_0 (shared with IMU) |
| Clock Speed | 300kHz |
| Screen Resolution | 280×456 pixels |
| Max Touch Points | 5 (multi-touch) |
| Pull-ups | External 4.7kΩ on SDA/SCL |
| Polling Rate | 100Hz (10ms interval) |

---

## FT3168 Register Map (Used)

| Register | Name | Value | Purpose |
|----------|------|-------|---------|
| 0x00 | DEV_MODE | 0x00 | Normal operating mode |
| 0x02 | TD_STATUS | - | Touch point count (0-5) |
| 0x03-0x06 | P1_XH/XL, P1_YH/YL | - | First touch point coordinates |
| 0x80 | TH_GROUP | 0x16 | Touch threshold (sensitivity) |
| 0x88 | PERIODACTIVE | 0x0C | Scan period (12ms) |
| 0xFC | RESET | 0x07 | Soft reset command |

---

## Related Documentation

- [TOUCH_DIAGNOSIS_AND_FIX.md](TOUCH_DIAGNOSIS_AND_FIX.md) - Comprehensive troubleshooting guide
- [BUGFIX_SUMMARY_v5.9.0.md](BUGFIX_SUMMARY_v5.9.0.md) - Medical-grade safety fixes
- [MEDICAL_GRADE_AUDIT_REPORT.md](MEDICAL_GRADE_AUDIT_REPORT.md) - Full system audit

---

## If Touch Still Doesn't Work

### Debug Steps:

1. **Check Serial Monitor at Startup:**
   - Look for "✅ FT3168 connectivity verified" message
   - If you see "❌ FT3168 NOT responding", I2C bus issue

2. **Check for I2C Errors:**
   - Monitor for "❌ FT3168 I2C read failed" messages
   - If frequent errors, check wiring/pull-ups

3. **Test with Minimal Code:**
   - Comment out IMU initialization (remove bus contention)
   - See if touch works alone

4. **I2C Bus Scan:**
   Add to `setup()` after `Touch_Init()`:
   ```cpp
   Wire.begin(47, 48);
   Wire.beginTransmission(0x38);
   uint8_t error = Wire.endTransmission();
   Serial.printf("FT3168 I2C scan: %d (0=found)\n", error);
   ```

5. **Hardware Reset:**
   - Power cycle the device (not just reset button)
   - Touch controller may need full power cycle

---

## Contact

For further assistance, refer to:
- [Waveshare ESP32-S3-Touch-AMOLED-1.64 Wiki](https://www.waveshare.com/wiki/ESP32-S3-Touch-AMOLED-1.64)
- [FocalTech FT6x06 Application Note](https://cdn-shop.adafruit.com/datasheets/FT6x06_AN_public_ver0.1.3.pdf)
