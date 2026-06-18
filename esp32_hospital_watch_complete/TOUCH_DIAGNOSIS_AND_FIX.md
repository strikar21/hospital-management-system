# FT3168 Touch Controller - Diagnosis & Fix

**Device:** Waveshare ESP32-S3-Touch-AMOLED-1.64
**Touch IC:** FocalTech FT3168
**Issue:** Touch was working earlier, now not responding
**Date:** 2025-11-25

---

## Hardware Specifications (Confirmed)

| Parameter | Value | Source |
|-----------|-------|--------|
| **Touch Controller** | FocalTech FT3168 | Waveshare Wiki |
| **I2C Address** | 0x38 (7-bit) | [lcd_config.h:25](lcd_config.h#L25) |
| **SDA Pin** | GPIO 47 | [lcd_config.h:27](lcd_config.h#L27) |
| **SCL Pin** | GPIO 48 | [lcd_config.h:26](lcd_config.h#L26) |
| **I2C Bus** | I2C_NUM_0 | [FT3168.cpp:62](FT3168.cpp#L62) |
| **Clock Speed** | 300kHz | [FT3168.cpp:85](FT3168.cpp#L85) |
| **Screen Resolution** | 280×456 | [lcd_config.h:4-5](lcd_config.h#L4-L5) |
| **Max Touch Points** | 5 (multi-touch) | FT3168 spec |
| **INT/IRQ Pin** | None (polling mode) | [TouchHandler.h:103](TouchHandler.h#L103) |
| **Pull-ups** | External 4.7kΩ | [FT3168.cpp:69](FT3168.cpp#L69) |

---

## Current Implementation Analysis

### Architecture
```
TouchHandler.cpp (Gesture Detection)
         ↓
    getTouch() - External C function
         ↓
    FT3168.cpp (I2C Driver)
         ↓
    ESP-IDF I2C Master API (New Driver)
         ↓
    Hardware I2C Bus 0 (shared with IMU)
```

### Initialization Sequence ([DisplayManager.cpp:33](DisplayManager.cpp#L33))
1. `Touch_Init()` called before LVGL init
2. Creates shared I2C bus (if not exists)
3. Adds FT3168 device to bus
4. Writes 0x00 to register 0x00 (normal mode)

### Touch Reading Flow ([FT3168.cpp:100-160](FT3168.cpp#L100-L160))
1. Read register 0x02 (touch point count)
2. If count > 0, read registers 0x03-0x06 (coordinates)
3. Validate coordinates (reject if outside 1-278, 1-454)
4. Return touch status + coordinates

### Polling Strategy ([TouchHandler.cpp:51-67](TouchHandler.cpp#L51-L67))
- **Rate:** 100Hz (10ms interval) - rate limited
- **Debounce:** 7ms for stationary touches
- **No INT pin:** Software polling only

---

## Diagnostic Findings

### ✅ **What's Working**

1. **I2C Bus Configuration**
   - Correct pins (GPIO 47/48)
   - Correct address (0x38)
   - Correct clock speed (300kHz)
   - Glitch filtering enabled (12 cycles = 40µs)

2. **Code Logic**
   - Proper ESP-IDF v5.2+ I2C master API usage
   - Shared bus with IMU (correct approach)
   - Retry logic on I2C errors (2 retries)
   - Coordinate validation

3. **Initialization Order**
   - Touch initialized before LVGL ✅
   - Shared I2C bus created correctly ✅

### 🔴 **Potential Issues**

#### ISSUE 1: **Excessive Debug Logging**
[FT3168.cpp:103-127](FT3168.cpp#L103-L127) - Debug prints every touch poll!
```cpp
if (poll_count % 5000 == 0) {
  Serial.printf("[DEBUG] getTouch() poll #%u\n", poll_count);
}
Serial.printf("[DEBUG] 🔍 FT3168 touch count: %d\n", data);  // ⚠️ EVERY TOUCH!
Serial.printf("[DEBUG] 👆 FT3168 touch detected: x=%d, y=%d\n", *x, *y);  // ⚠️ EVERY TOUCH!
```
**Impact:** Serial floods can cause I2C timing issues

---

#### ISSUE 2: **No Hardware Reset**
FT3168 has no RST pin configured!
- **Problem:** Touch controller may be in unknown state after power-on
- **Missing:** Hardware reset pulse (10ms LOW → HIGH)
- **Workaround:** Soft reset via I2C register

---

#### ISSUE 3: **Missing Register Initialization**
[FT3168.cpp:96-97](FT3168.cpp#L96-L97) - Only one register written!
```cpp
uint8_t data = 0x00;
I2C_writr_buff(I2C_ADDR_FT3168, 0x00, &data, 1);  // Device mode only
```

**Missing FT3168 Configuration:**
- No gesture mode configuration
- No interrupt mode setting (even though we poll)
- No threshold configuration
- No power mode setting

---

#### ISSUE 4: **I2C Bus Contention**
Both touch (100Hz) and IMU (25Hz) share I2C bus:
- Touch polls every 10ms
- IMU reads every 40ms
- **Potential collision** if IMU read happens during touch poll

**Current Mitigation:** Rate limiting reduces collisions but doesn't eliminate them

---

#### ISSUE 5: **Touch Validation Too Strict**
[TouchHandler.cpp:72-73](TouchHandler.cpp#L72-L73)
```cpp
bool validCoordinates = (x > 0 && x < 279) &&  // Rejects 0 and 279!
                        (y > 0 && y < 455);     // Rejects 0 and 455!
```
**Problem:** Valid edge touches rejected (screen is 280×456, includes 0-279 and 0-455)

---

#### ISSUE 6: **Debounce Logic Complexity**
[TouchHandler.cpp:75-98](TouchHandler.cpp#L75-L98) - Complex state machine:
- Stationary touches require 7ms stability
- Moving touches accepted immediately
- But FT3168 already has internal filtering!

**Risk:** Overly aggressive filtering may reject real touches

---

## Failure Scenarios

### Scenario A: Touch Controller Hung
**Symptoms:**
- `getTouch()` always returns 0
- I2C reads return 0 (no error, but no touches)
- Touch screen physically works (other devices confirm)

**Diagnosis Steps:**
1. Check if FT3168 responds to I2C address scan
2. Read chip ID register (if exists)
3. Check if register 0x02 stuck at 0

**Solution:** Hardware or soft reset

---

### Scenario B: I2C Bus Lockup
**Symptoms:**
- I2C reads fail (`readResult != 0`)
- Debug logs show "❌ FT3168 I2C read failed"
- IMU also affected (shared bus)

**Diagnosis Steps:**
1. Check if IMU still works
2. Check for SDA/SCL stuck low
3. Verify pull-ups present

**Solution:** Bus recovery (9 clock pulses on SCL with SDA high)

---

### Scenario C: Touch Works But Not Detected
**Symptoms:**
- FT3168 returns valid coordinates
- But TouchHandler rejects them
- Debug logs show coordinates but "Invalid touch ignored"

**Diagnosis Steps:**
1. Check coordinate validation logic
2. Check debounce timing
3. Check if LVGL input driver registered

**Solution:** Loosen validation, reduce debounce

---

## Recommended Fix Strategy

### Phase 1: Minimal Debug Touch Driver (NEW)
Create simple standalone test to isolate hardware:
```cpp
// test_touch_raw.cpp
void setup() {
  Touch_Init();
}

void loop() {
  uint16_t x, y;
  if (getTouch(&x, &y)) {
    Serial.printf("RAW TOUCH: x=%d, y=%d\n", x, y);
  }
  delay(50);  // 20Hz polling for test
}
```

**Test Cases:**
1. ✅ Touch screen - do coordinates appear?
2. ✅ Touch corners - do all areas register?
3. ✅ Touch and hold - does it stay stable?
4. ✅ Swipe - do coordinates update smoothly?

---

### Phase 2: Fix FT3168 Driver

#### Fix 1: Add Soft Reset
```cpp
void Touch_Init(void) {
  // ... existing bus setup ...

  // ✅ Soft reset FT3168
  uint8_t resetCmd = 0x07;  // Reset command
  I2C_writr_buff(I2C_ADDR_FT3168, 0xFC, &resetCmd, 1);  // Write to reset register
  delay(200);  // Wait for reset to complete

  // Switch to normal operating mode
  uint8_t data = 0x00;
  I2C_writr_buff(I2C_ADDR_FT3168, 0x00, &data, 1);

  // ✅ Configure touch controller
  // Set active mode (not monitor mode)
  data = 0x00;
  I2C_writr_buff(I2C_ADDR_FT3168, 0x86, &data, 1);  // CTRL register

  // Set touch threshold (adjust sensitivity)
  data = 0x16;  // Default threshold (22 units)
  I2C_writr_buff(I2C_ADDR_FT3168, 0x80, &data, 1);  // TH_GROUP register
}
```

---

#### Fix 2: Remove Debug Floods
```cpp
uint8_t getTouch(uint16_t *x, uint16_t *y) {
  // ❌ REMOVE all debug Serial.printf() except errors
  // Only log on I2C errors or initialization

  uint8_t data;
  uint8_t buf[4];

  uint8_t readResult = I2C_read_buff(I2C_ADDR_FT3168, 0x02, &data, 1);

  if (readResult != 0) {
    // Only log errors (not every poll)
    static uint32_t lastErrorLog = 0;
    if (millis() - lastErrorLog > 1000) {  // Max 1/second
      Serial.println("❌ FT3168 I2C read failed");
      lastErrorLog = millis();
    }
    return 0;
  }

  // ... rest of function WITHOUT debug prints ...
}
```

---

#### Fix 3: Fix Coordinate Validation
```cpp
// BEFORE (rejects edges):
bool validCoordinates = (x > 0 && x < 279) && (y > 0 && y < 455);

// AFTER (accepts all valid pixels):
bool validCoordinates = (x < EXAMPLE_LCD_H_RES) && (y < EXAMPLE_LCD_V_RES);
// Allows 0-279 for X (280 pixels) and 0-455 for Y (456 pixels)
```

---

#### Fix 4: Simplify Debounce
```cpp
// BEFORE: Complex moving vs stationary logic

// AFTER: Simple time-based debounce
bool validTouch = false;
if (touched && validCoordinates) {
  if (touchFirstSeenTime == 0) {
    touchFirstSeenTime = millis();  // First time seeing this touch
  }

  if ((millis() - touchFirstSeenTime) >= 5) {  // 5ms debounce
    validTouch = true;
  }
} else {
  touchFirstSeenTime = 0;  // Reset on no-touch
}
```

---

### Phase 3: Add I2C Bus Health Check
```cpp
bool testFT3168Connection() {
  uint8_t chipID;

  // Try to read device mode register
  if (I2C_read_buff(I2C_ADDR_FT3168, 0x00, &chipID, 1) != 0) {
    Serial.println("❌ FT3168 not responding on I2C");
    return false;
  }

  Serial.printf("✅ FT3168 connected, mode register: 0x%02X\n", chipID);
  return true;
}
```

Call this in `Touch_Init()` to verify connectivity.

---

### Phase 4: I2C Bus Mutex (If Needed)
If touch still conflicts with IMU:
```cpp
// In main code:
SemaphoreHandle_t i2c_mutex = xSemaphoreCreateMutex();

// In FT3168.cpp:
uint8_t I2C_read_buff(...) {
  if (i2c_mutex) xSemaphoreTake(i2c_mutex, portMAX_DELAY);

  esp_err_t ret = i2c_master_transmit_receive(...);

  if (i2c_mutex) xSemaphoreGive(i2c_mutex);
  return (ret == ESP_OK) ? 0 : 1;
}
```

---

## Implementation Plan

### Step 1: Enable Verbose Logging (Temporarily)
**Goal:** See what's actually happening

Add to `setup()`:
```cpp
Serial.println("==== TOUCH DEBUG MODE ====");

// Test I2C bus
Wire.begin(47, 48);  // SDA, SCL
Wire.beginTransmission(0x38);
uint8_t error = Wire.endTransmission();
Serial.printf("FT3168 I2C scan result: %d (0=success)\n", error);

// Test touch read
uint16_t x, y;
for (int i = 0; i < 10; i++) {
  if (getTouch(&x, &y)) {
    Serial.printf("[%d] Touch: x=%d, y=%d\n", i, x, y);
  } else {
    Serial.printf("[%d] No touch\n", i);
  }
  delay(100);
}
```

---

### Step 2: Apply Fixes to FT3168.cpp
1. ✅ Add soft reset
2. ✅ Add register configuration
3. ✅ Remove debug floods
4. ✅ Add connection test

---

### Step 3: Apply Fixes to TouchHandler.cpp
1. ✅ Fix coordinate validation (allow 0-279, 0-455)
2. ✅ Simplify debounce logic
3. ✅ Reduce poll rate if needed (50Hz instead of 100Hz)

---

### Step 4: Test & Validate
- [ ] Touch screen responds
- [ ] Coordinates accurate (corners, center)
- [ ] Swipe gestures detected
- [ ] No phantom touches
- [ ] No I2C errors

---

## Emergency Fallback: Start From Scratch

If all else fails, rewrite minimal touch driver:

```cpp
// touch_simple.cpp
#include "driver/i2c_master.h"

#define FT3168_ADDR 0x38
static i2c_master_dev_handle_t touch_dev = NULL;

void touchInit() {
  // Create bus
  i2c_master_bus_config_t bus_cfg = {
    .i2c_port = I2C_NUM_0,
    .sda_io_num = 47,
    .scl_io_num = 48,
    .clk_source = I2C_CLK_SRC_DEFAULT,
    .glitch_ignore_cnt = 7,
    .flags.enable_internal_pullup = false
  };

  i2c_master_bus_handle_t bus;
  ESP_ERROR_CHECK(i2c_new_master_bus(&bus_cfg, &bus));

  // Add device
  i2c_device_config_t dev_cfg = {
    .dev_addr_length = I2C_ADDR_BIT_LEN_7,
    .device_address = FT3168_ADDR,
    .scl_speed_hz = 300000
  };

  ESP_ERROR_CHECK(i2c_master_bus_add_device(bus, &dev_cfg, &touch_dev));

  // Soft reset
  uint8_t cmd[] = {0xFC, 0x07};
  i2c_master_transmit(touch_dev, cmd, 2, 1000);
  vTaskDelay(pdMS_TO_TICKS(200));

  // Normal mode
  cmd[0] = 0x00;
  cmd[1] = 0x00;
  i2c_master_transmit(touch_dev, cmd, 2, 1000);
}

bool touchRead(uint16_t *x, uint16_t *y) {
  uint8_t reg = 0x02;
  uint8_t count;

  // Read touch count
  if (i2c_master_transmit_receive(touch_dev, &reg, 1, &count, 1, 1000) != ESP_OK) {
    return false;
  }

  if (count == 0 || count > 5) return false;

  // Read coordinates
  reg = 0x03;
  uint8_t buf[4];
  if (i2c_master_transmit_receive(touch_dev, &reg, 1, buf, 4, 1000) != ESP_OK) {
    return false;
  }

  *x = ((buf[0] & 0x0F) << 8) | buf[1];
  *y = ((buf[2] & 0x0F) << 8) | buf[3];

  return (*x < 280 && *y < 456);  // Validate
}
```

---

## Conclusion

**Most Likely Issue:** Debug logging floods causing I2C timing problems

**Quick Fix Priority:**
1. ⚠️ Remove all `Serial.printf()` from `getTouch()` ([FT3168.cpp](FT3168.cpp))
2. ⚠️ Fix coordinate validation ([TouchHandler.cpp:72](TouchHandler.cpp#L72))
3. ⚠️ Add soft reset to `Touch_Init()` ([FT3168.cpp:56](FT3168.cpp#L56))

**Next Review:** After applying Phase 2 fixes, test with screen touches

---

## Sources

- [I2C Address 0x38 | I2C Device Directory](https://i2cdevices.org/addresses/0x38)
- [FT6x06 Application Note](https://cdn-shop.adafruit.com/datasheets/FT6x06_AN_public_ver0.1.3.pdf)
- [Waveshare ESP32-S3-Touch-AMOLED-1.64 Wiki](https://www.waveshare.com/wiki/ESP32-S3-Touch-AMOLED-1.64)

