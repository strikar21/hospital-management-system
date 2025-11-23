#include "FT3168.h"
#include "esp_err.h"
#include "lcd_config.h"
#include "driver/i2c_master.h"  // ✅ NEW I2C driver API
#include "Arduino.h"            // ✅ For Serial.printf() debugging

// ✅ v5.4.1: Export shared I2C bus handle for use by IMU (QMI8658)
i2c_master_bus_handle_t shared_i2c_bus = NULL;

// ✅ v5.3: Use NEW I2C master driver API (compatible with Wire library)
static i2c_master_dev_handle_t ft3168_handle = NULL;

uint8_t I2C_writr_buff(uint8_t addr, uint8_t reg, uint8_t *buf, uint8_t len)
{
  uint8_t *pbuf = (uint8_t*)malloc(len + 1);
  pbuf[0] = reg;
  for(uint8_t i = 0; i < len; i++)
  {
    pbuf[i + 1] = buf[i];
  }

  esp_err_t ret = i2c_master_transmit(ft3168_handle, pbuf, len + 1, 1000);
  free(pbuf);
  pbuf = NULL;

  return (ret == ESP_OK) ? 0 : 1;
}

uint8_t I2C_read_buff(uint8_t addr, uint8_t reg, uint8_t *buf, uint8_t len)
{
  // ✅ v5.8.15: Retry on I2C errors (filters transient bus noise)
  const int MAX_RETRIES = 2;
  for (int attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    esp_err_t ret = i2c_master_transmit_receive(ft3168_handle, &reg, 1, buf, len, 1000);

    if (ret == ESP_OK) {
      return 0;  // Success
    }

    // On error, retry after brief delay (allows bus to settle)
    if (attempt < MAX_RETRIES) {
      delayMicroseconds(100);  // 100µs settling time
    }
  }

  // All retries failed
  return 1;
}

uint8_t I2C_master_write_read_device(uint8_t addr, uint8_t *writeBuf, uint8_t writeLen, uint8_t *readBuf, uint8_t readLen)
{
  esp_err_t ret = i2c_master_transmit_receive(ft3168_handle, writeBuf, writeLen, readBuf, readLen, 1000);
  return (ret == ESP_OK) ? 0 : 1;
}

void Touch_Init(void)
{
  // ✅ v5.4.1: Only create shared I2C bus if not already created (by IMU or other device)
  if (shared_i2c_bus == NULL) {
    i2c_master_bus_config_t bus_config = {};
    bus_config.clk_source = I2C_CLK_SRC_DEFAULT;
    bus_config.i2c_port = I2C_NUM_0;
    bus_config.scl_io_num = (gpio_num_t)EXAMPLE_PIN_NUM_TOUCH_SCL;  // GPIO 48
    bus_config.sda_io_num = (gpio_num_t)EXAMPLE_PIN_NUM_TOUCH_SDA;  // GPIO 47

    // ✅ v5.8.15: Enhanced noise filtering
    bus_config.glitch_ignore_cnt = 12;  // Increased from 7 → 12 (filters more noise)
                                         // 12 cycles @ 300kHz = 40µs spike rejection
    bus_config.flags.enable_internal_pullup = false;  // ✅ Board has external 4.7kΩ pull-ups

    esp_err_t ret = i2c_new_master_bus(&bus_config, &shared_i2c_bus);
    if (ret != ESP_OK) {
      Serial.printf("❌ Failed to create I2C master bus: %d\n", ret);
      return;
    }

    Serial.println("✅ I2C Bus 0 created (shared by touch + IMU)");
    delay(100);  // ✅ Power settling delay
  }

  // ✅ Add FT3168 touch device to shared I2C bus
  i2c_device_config_t dev_config = {};
  dev_config.dev_addr_length = I2C_ADDR_BIT_LEN_7;
  dev_config.device_address = I2C_ADDR_FT3168;  // 0x38
  dev_config.scl_speed_hz = 300000;  // 300kHz

  esp_err_t ret = i2c_master_bus_add_device(shared_i2c_bus, &dev_config, &ft3168_handle);
  if (ret != ESP_OK) {
    Serial.printf("❌ Failed to add FT3168 to I2C bus: %d\n", ret);
    return;
  }

  Serial.println("✅ FT3168 touch controller added to shared I2C bus");

  // Switch to normal mode
  uint8_t data = 0x00;
  I2C_writr_buff(I2C_ADDR_FT3168, 0x00, &data, 1);
}

uint8_t getTouch(uint16_t *x, uint16_t *y)
{
  uint8_t data;
  uint8_t buf[4];

  // Read touch point count register (0x02)
  uint8_t readResult = I2C_read_buff(I2C_ADDR_FT3168, 0x02, &data, 1);

  // ✅ v5.8.15: Reject if I2C read failed (filters bus errors)
  if (readResult != 0) {
    return 0;  // I2C error - reject this reading
  }

  // ✅ v5.8.15: Sanity check touch count (FT3168 supports max 5 touches)
  if (data > 5 || data == 0) {
    return 0;  // Invalid touch count - likely noise
  }

  if(data)
  {
    // Read touch coordinates
    readResult = I2C_read_buff(I2C_ADDR_FT3168, 0x03, buf, 4);

    // ✅ v5.8.15: Reject if coordinate read failed
    if (readResult != 0) {
      return 0;  // I2C error during coordinate read
    }

    *x = (((uint16_t)buf[0] & 0x0f) << 8) | (uint16_t)buf[1];
    *y = (((uint16_t)buf[2] & 0x0f) << 8) | (uint16_t)buf[3];

    // ✅ v5.8.3: REJECT invalid touches instead of clamping (prevents phantom edge touches)
    // Invalid coordinates indicate I2C noise or touch controller glitch
    if(*x >= EXAMPLE_LCD_H_RES || *y >= EXAMPLE_LCD_V_RES) {
      // Serial.printf("⚠️  FT3168: Invalid touch rejected: x=%d, y=%d\n", *x, *y);
      return 0;  // Reject this touch reading
    }

    // ✅ v5.8.15: Additional sanity check - reject all-zeros or all-ones (bus stuck)
    if ((*x == 0 && *y == 0) || (*x == 0xFFF && *y == 0xFFF)) {
      return 0;  // Bus stuck condition
    }

    // ✅ v5.8.3: Debug print moved to TouchHandler (with additional validation)
    // Serial.printf("👆 Touch detected: x=%d, y=%d\n", *x, *y);

    return 1;
  }
  return 0;
}
