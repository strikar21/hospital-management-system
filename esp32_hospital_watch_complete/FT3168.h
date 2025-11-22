#ifndef FT3168_H
#define FT3168_H
#include "driver/i2c.h"
#include "driver/i2c_master.h"  // ✅ v5.4.1: For shared bus handle type

#ifdef __cplusplus
extern "C" {
#endif

// ✅ v5.4.1: Export shared I2C bus handle for use by IMU (QMI8658)
extern i2c_master_bus_handle_t shared_i2c_bus;

void Touch_Init(void);

uint8_t getTouch(uint16_t *x,uint16_t *y);
#ifdef __cplusplus
}
#endif
#endif