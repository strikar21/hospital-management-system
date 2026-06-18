/**
 * FT3168.cpp - FocalTech FT3168 Touch Controller Driver
 * ESP-IDF v5+ I2C Master Driver API
 *
 * Uses shared I2C bus for both touch (FT3168) and IMU (QMI8658)
 * Version: 5.9.1 - Fixed touch with new driver API + soft reset + debug cleanup
 */

#include "FT3168.h"
#include "esp_err.h"
#include "esp_log.h"
#include "lcd_config.h"
#include <Arduino.h>

#define TEST_I2C_PORT I2C_NUM_0

// ✅ v5.9.1: Shared I2C bus handle for touch + IMU
i2c_master_bus_handle_t shared_i2c_bus = NULL;
static i2c_master_dev_handle_t ft3168_dev = NULL;

/**
 * Initialize FT3168 touch controller
 * Creates shared I2C bus that can be used by IMU (QMI8658)
 */
void Touch_Init(void) {
  Serial.println("\n🔧 Initializing FT3168 Touch Controller...");

  // ✅ Create shared I2C bus (new driver API)
  i2c_master_bus_config_t bus_config = {
    .i2c_port = TEST_I2C_PORT,
    .sda_io_num = (gpio_num_t)EXAMPLE_PIN_NUM_TOUCH_SDA,
    .scl_io_num = (gpio_num_t)EXAMPLE_PIN_NUM_TOUCH_SCL,
    .clk_source = I2C_CLK_SRC_DEFAULT,
    .glitch_ignore_cnt = 7,  // Noise filtering
    .flags = {
      .enable_internal_pullup = true  // Enable internal pull-ups
    }
  };

  esp_err_t ret = i2c_new_master_bus(&bus_config, &shared_i2c_bus);
  if (ret != ESP_OK) {
    Serial.printf("❌ Failed to create I2C bus: %d\n", ret);
    return;
  }
  Serial.println("✅ I2C Bus 0 created (shared with IMU)");

  // ✅ Add FT3168 device to bus
  i2c_device_config_t dev_config = {
    .dev_addr_length = I2C_ADDR_BIT_LEN_7,
    .device_address = I2C_ADDR_FT3168,
    .scl_speed_hz = 300000  // 300kHz (FT3168 max 400kHz)
  };

  ret = i2c_master_bus_add_device(shared_i2c_bus, &dev_config, &ft3168_dev);
  if (ret != ESP_OK) {
    Serial.printf("❌ Failed to add FT3168 device: %d\n", ret);
    return;
  }
  Serial.println("✅ FT3168 device added to I2C bus");

  // ✅ v5.9.1: Soft reset FT3168
  delay(10);  // Wait for power stabilization
  uint8_t resetCmd[2] = {0xFC, 0x07};  // Register 0xFC = 0x07 (reset)
  ret = i2c_master_transmit(ft3168_dev, resetCmd, 2, 2000 / portTICK_PERIOD_MS);  // ✅ Increased timeout to 2000ms
  if (ret == ESP_OK) {
    Serial.println("✅ FT3168 soft reset initiated");
    delay(200);  // Wait for reset to complete
  } else {
    Serial.printf("⚠️  FT3168 soft reset failed: %d (may be OK if touch works)\n", ret);
  }

  // ✅ v5.9.1: Configure FT3168 registers
  // Normal operating mode
  uint8_t modeCmd[2] = {0x00, 0x00};
  ret = i2c_master_transmit(ft3168_dev, modeCmd, 2, 1000 / portTICK_PERIOD_MS);
  if (ret == ESP_OK) {
    Serial.println("✅ FT3168 set to normal mode");
  }

  // Touch threshold (sensitivity)
  uint8_t thresholdCmd[2] = {0x80, 0x16};  // TH_GROUP = 22 units
  ret = i2c_master_transmit(ft3168_dev, thresholdCmd, 2, 1000 / portTICK_PERIOD_MS);
  if (ret == ESP_OK) {
    Serial.println("✅ FT3168 touch threshold set (0x16)");
  }

  // Scan period (responsiveness)
  uint8_t periodCmd[2] = {0x88, 0x0C};  // PERIODACTIVE = 12ms
  ret = i2c_master_transmit(ft3168_dev, periodCmd, 2, 1000 / portTICK_PERIOD_MS);
  if (ret == ESP_OK) {
    Serial.println("✅ FT3168 scan period set (12ms)");
  }

  // ✅ v5.9.1: Verify connectivity by reading device mode
  uint8_t regAddr = 0x00;
  uint8_t mode;
  ret = i2c_master_transmit_receive(ft3168_dev, &regAddr, 1, &mode, 1, 1000 / portTICK_PERIOD_MS);
  if (ret == ESP_OK) {
    Serial.printf("✅ FT3168 connectivity verified, mode=0x%02X\n", mode);
    Serial.println("✅ Touch controller initialization complete\n");
  } else {
    Serial.println("❌ FT3168 NOT responding - touch will not work!");
  }
}

/**
 * Read touch coordinates from FT3168
 * Returns 1 if touch detected, 0 if no touch
 *
 * ✅ v5.9.1: Removed debug floods, only rate-limited error logging
 */
uint8_t getTouch(uint16_t *x, uint16_t *y) {
  if (ft3168_dev == NULL) {
    return 0;  // Not initialized
  }

  // Read touch point count (register 0x02)
  uint8_t regAddr = 0x02;
  uint8_t touchCount;

  esp_err_t ret = i2c_master_transmit_receive(ft3168_dev, &regAddr, 1, &touchCount, 1,
                                               100 / portTICK_PERIOD_MS);

  if (ret != ESP_OK) {
    // ✅ v5.9.1: Rate-limited error logging (max 1/second)
    static uint32_t lastErrorLog = 0;
    if (millis() - lastErrorLog > 1000) {
      Serial.printf("❌ FT3168 I2C read failed: %d\n", ret);
      lastErrorLog = millis();
    }
    return 0;
  }

  // No touch detected
  if (touchCount == 0 || touchCount > 5) {
    return 0;
  }

  // Read touch coordinates (registers 0x03-0x06)
  regAddr = 0x03;
  uint8_t buf[4];
  ret = i2c_master_transmit_receive(ft3168_dev, &regAddr, 1, buf, 4,
                                     100 / portTICK_PERIOD_MS);

  if (ret != ESP_OK) {
    static uint32_t lastErrorLog = 0;
    if (millis() - lastErrorLog > 1000) {
      Serial.printf("❌ FT3168 coordinate read failed: %d\n", ret);
      lastErrorLog = millis();
    }
    return 0;
  }

  // Parse coordinates
  *x = (((uint16_t)buf[0] & 0x0F) << 8) | (uint16_t)buf[1];
  *y = (((uint16_t)buf[2] & 0x0F) << 8) | (uint16_t)buf[3];

  // Clamp to screen resolution
  if (*x > EXAMPLE_LCD_H_RES) *x = EXAMPLE_LCD_H_RES;
  if (*y > EXAMPLE_LCD_V_RES) *y = EXAMPLE_LCD_V_RES;

  // ✅ v5.9.1: Occasional debug logging (every 100th touch instead of EVERY touch)
  static uint32_t touchDebugCount = 0;
  touchDebugCount++;
  if (touchDebugCount % 100 == 0) {
    Serial.printf("👆 Touch #%u: x=%d, y=%d\n", touchDebugCount, *x, *y);
  }

  return 1;
}

// ============================================
// Legacy wrapper functions (for compatibility)
// ============================================

/**
 * Legacy I2C write function - kept for compatibility
 * Now uses new driver internally
 */
uint8_t I2C_writr_buff(uint8_t addr, uint8_t reg, uint8_t *buf, uint8_t len) {
  if (ft3168_dev == NULL) return 1;

  // Combine register address + data
  uint8_t *txBuf = (uint8_t*)malloc(len + 1);
  if (txBuf == NULL) return 1;

  txBuf[0] = reg;
  memcpy(&txBuf[1], buf, len);

  esp_err_t ret = i2c_master_transmit(ft3168_dev, txBuf, len + 1, 1000 / portTICK_PERIOD_MS);

  free(txBuf);
  return (ret == ESP_OK) ? 0 : 1;
}

/**
 * Legacy I2C read function - kept for compatibility
 * Now uses new driver internally
 */
uint8_t I2C_read_buff(uint8_t addr, uint8_t reg, uint8_t *buf, uint8_t len) {
  if (ft3168_dev == NULL) return 1;

  esp_err_t ret = i2c_master_transmit_receive(ft3168_dev, &reg, 1, buf, len,
                                               1000 / portTICK_PERIOD_MS);
  return (ret == ESP_OK) ? 0 : 1;
}

/**
 * Legacy I2C write-read function - kept for compatibility
 */
uint8_t I2C_master_write_read_device(uint8_t addr, uint8_t *writeBuf, uint8_t writeLen,
                                      uint8_t *readBuf, uint8_t readLen) {
  if (ft3168_dev == NULL) return 1;

  esp_err_t ret = i2c_master_transmit_receive(ft3168_dev, writeBuf, writeLen,
                                               readBuf, readLen, 1000 / portTICK_PERIOD_MS);
  return (ret == ESP_OK) ? 0 : 1;
}
