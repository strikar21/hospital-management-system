/**
 * FT3168.h - FocalTech FT3168 Touch Controller Driver
 * ESP-IDF v5+ I2C Master Driver API
 *
 * Version: 5.9.1 - New I2C master driver API with shared bus support
 */

#ifndef FT3168_H
#define FT3168_H

#include "driver/i2c_master.h"  // ✅ v5.9.1: New I2C master driver
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// ✅ v5.9.1: Shared I2C bus handle - created by Touch_Init(), used by IMU
extern i2c_master_bus_handle_t shared_i2c_bus;

/**
 * Initialize FT3168 touch controller
 * Creates shared I2C bus (shared_i2c_bus) for touch + IMU
 */
void Touch_Init(void);

/**
 * Read touch coordinates
 * @param x Pointer to store X coordinate (0-279)
 * @param y Pointer to store Y coordinate (0-455)
 * @return 1 if touch detected, 0 if no touch
 */
uint8_t getTouch(uint16_t *x, uint16_t *y);

// Legacy wrapper functions (for compatibility)
uint8_t I2C_writr_buff(uint8_t addr, uint8_t reg, uint8_t *buf, uint8_t len);
uint8_t I2C_read_buff(uint8_t addr, uint8_t reg, uint8_t *buf, uint8_t len);
uint8_t I2C_master_write_read_device(uint8_t addr, uint8_t *writeBuf, uint8_t writeLen,
                                      uint8_t *readBuf, uint8_t readLen);

#ifdef __cplusplus
}
#endif

#endif // FT3168_H
