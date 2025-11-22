#include "FT3168.h"
#include "esp_err.h"
#include "lcd_config.h"
#include "driver/i2c_master.h"  // ✅ NEW I2C driver API
#include "Arduino.h"            // ✅ For Serial.printf() debugging

// ✅ v5.3: Use NEW I2C master driver API (compatible with Wire library)
static i2c_master_bus_handle_t i2c_bus_handle = NULL;
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
  esp_err_t ret = i2c_master_transmit_receive(ft3168_handle, &reg, 1, buf, len, 1000);
  return (ret == ESP_OK) ? 0 : 1;
}

uint8_t I2C_master_write_read_device(uint8_t addr, uint8_t *writeBuf, uint8_t writeLen, uint8_t *readBuf, uint8_t readLen)
{
  esp_err_t ret = i2c_master_transmit_receive(ft3168_handle, writeBuf, writeLen, readBuf, readLen, 1000);
  return (ret == ESP_OK) ? 0 : 1;
}

void Touch_Init(void)
{
  // ✅ v5.3: Initialize I2C using NEW driver API (compatible with Wire/TwoWire)
  i2c_master_bus_config_t bus_config = {};
  bus_config.clk_source = I2C_CLK_SRC_DEFAULT;
  bus_config.i2c_port = I2C_NUM_0;
  bus_config.scl_io_num = (gpio_num_t)EXAMPLE_PIN_NUM_TOUCH_SCL;
  bus_config.sda_io_num = (gpio_num_t)EXAMPLE_PIN_NUM_TOUCH_SDA;
  bus_config.glitch_ignore_cnt = 7;
  bus_config.flags.enable_internal_pullup = true;

  ESP_ERROR_CHECK(i2c_new_master_bus(&bus_config, &i2c_bus_handle));

  // Add FT3168 device to I2C bus
  i2c_device_config_t dev_config = {};
  dev_config.dev_addr_length = I2C_ADDR_BIT_LEN_7;
  dev_config.device_address = I2C_ADDR_FT3168;
  dev_config.scl_speed_hz = 300000;  // 300kHz

  ESP_ERROR_CHECK(i2c_master_bus_add_device(i2c_bus_handle, &dev_config, &ft3168_handle));

  // Switch to normal mode
  uint8_t data = 0x00;
  I2C_writr_buff(I2C_ADDR_FT3168, 0x00, &data, 1);
}

uint8_t getTouch(uint16_t *x, uint16_t *y)
{
  uint8_t data;
  uint8_t buf[4];

  I2C_read_buff(I2C_ADDR_FT3168, 0x02, &data, 1);
  if(data)
  {
    I2C_read_buff(I2C_ADDR_FT3168, 0x03, buf, 4);
    *x = (((uint16_t)buf[0] & 0x0f) << 8) | (uint16_t)buf[1];
    *y = (((uint16_t)buf[2] & 0x0f) << 8) | (uint16_t)buf[3];

    // ✅ v5.3: Bounds checking (like Waveshare demo)
    if(*x > EXAMPLE_LCD_H_RES)
      *x = EXAMPLE_LCD_H_RES;
    if(*y > EXAMPLE_LCD_V_RES)
      *y = EXAMPLE_LCD_V_RES;

    // Debug output (can be disabled later)
    Serial.printf("👆 Touch detected: x=%d, y=%d\n", *x, *y);

    return 1;
  }
  return 0;
}
