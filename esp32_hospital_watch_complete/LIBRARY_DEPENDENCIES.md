# Library Dependencies for ESP32 Hospital Watch v5.2.14 + LVGL

## Required Arduino Libraries

### 1. LVGL (Light and Versatile Graphics Library)
- **Version**: v9.x (latest stable - 9.2.0 or newer)
- **Installation**: Arduino Library Manager
  1. Open Arduino IDE
  2. Go to Sketch → Include Library → Manage Libraries
  3. Search for "lvgl"
  4. Install "lvgl by kisvegabor"
- **Alternative**: Download from https://github.com/lvgl/lvgl
- **Configuration**: Requires `lv_conf.h` in Arduino `libraries/` folder

### 2. Existing Libraries (Already in Project)
- **WiFi** - Built-in with ESP32 core
- **WebServer** - Built-in with ESP32 core
- **DNSServer** - Built-in with ESP32 core
- **ArduinoJson** (v7+) - For JSON serialization
- **Preferences** - Built-in with ESP32 core
- **PubSubClient** - For MQTT
- **WiFiClientSecure** - For TLS/mTLS
- **SPIFFS** - Built-in with ESP32 core
- **HTTPClient** - Built-in with ESP32 core

### 3. Waveshare BSP Drivers (Included in Project)
- **lcd_bsp.h/c** - CO5300 QSPI AMOLED display driver
- **FT3168.h/cpp** - FT3168 I2C touch controller driver
- **lcd_config.h** - Pin definitions and display configuration

## ESP32 Board Support

### Arduino Core for ESP32
- **Version**: v3.0.0 or newer
- **Installation**:
  1. File → Preferences
  2. Add to "Additional Board Manager URLs":
     ```
     https://espressif.github.io/arduino-esp32/package_esp32_index.json
     ```
  3. Tools → Board → Boards Manager
  4. Search "esp32"
  5. Install "esp32 by Espressif Systems"

### Board Selection
- **Board**: ESP32S3 Dev Module
- **Flash Size**: 16MB (128Mb)
- **PSRAM**: OPI PSRAM
- **Partition Scheme**: 16MB Flash (3MB APP/9.9MB FATFS)
- **USB CDC On Boot**: Enabled
- **USB DFU On Boot**: Disabled
- **Upload Speed**: 921600

## LVGL Configuration

### lv_conf.h Setup

Create or edit `lv_conf.h` in your Arduino `libraries/` folder:

**Location**: `C:\Users\YourName\Documents\Arduino\libraries\lv_conf.h`

```c
/**
 * LVGL Configuration for ESP32-S3 Hospital Watch
 * Waveshare ESP32-S3-Touch-AMOLED-1.64 (280×456)
 */

#ifndef LV_CONF_H
#define LV_CONF_H

#include <stdint.h>

/* Color settings */
#define LV_COLOR_DEPTH 16                    // RGB565 for 16-bit color
#define LV_COLOR_16_SWAP 0                   // No byte swapping needed

/* Memory settings */
#define LV_MEM_CUSTOM 0                      // Use built-in allocator
#define LV_MEM_SIZE (128 * 1024U)            // 128KB for LVGL heap

/* Display buffer settings */
#define LV_DISP_DEF_REFR_PERIOD 30           // Refresh every 30ms
#define LV_INDEV_DEF_READ_PERIOD 30          // Read input every 30ms

/* Feature settings */
#define LV_USE_PERF_MONITOR 1                // Show FPS counter (disable in production)
#define LV_USE_MEM_MONITOR 1                 // Show memory usage (disable in production)
#define LV_USE_LOG 1                         // Enable logging
#define LV_LOG_LEVEL LV_LOG_LEVEL_WARN       // Only warnings and errors

/* Font settings */
#define LV_FONT_MONTSERRAT_12 1
#define LV_FONT_MONTSERRAT_14 1
#define LV_FONT_MONTSERRAT_16 1
#define LV_FONT_MONTSERRAT_18 1
#define LV_FONT_MONTSERRAT_20 1
#define LV_FONT_MONTSERRAT_22 1
#define LV_FONT_MONTSERRAT_24 1
#define LV_FONT_MONTSERRAT_26 1
#define LV_FONT_MONTSERRAT_28 1
#define LV_FONT_MONTSERRAT_30 1
#define LV_FONT_MONTSERRAT_32 1

/* Widget settings */
#define LV_USE_BTN 1
#define LV_USE_LABEL 1
#define LV_USE_SLIDER 1
#define LV_USE_LIST 1
#define LV_USE_CHART 1

/* Theme settings */
#define LV_THEME_DEFAULT_DARK 1              // Dark theme by default
#define LV_THEME_DEFAULT_GROW 1
#define LV_THEME_DEFAULT_TRANSITION_TIME 80

#endif /* LV_CONF_H */
```

## Project File Structure

```
esp32_hospital_watch_complete/
├── esp32_hospital_watch_complete.ino    # Main firmware (MODIFIED)
├── DisplayManager.h                      # NEW: Display initialization
├── DisplayManager.cpp                    # NEW: Display implementation
├── UIScreens.h                           # NEW: UI screens header
├── UIScreens.cpp                         # NEW: UI screens implementation
├── TouchHandler.h                        # NEW: Touch gestures header
├── TouchHandler.cpp                      # NEW: Touch gestures implementation
├── lcd_config.h                          # Waveshare: Pin definitions
├── lcd_bsp.h                             # Waveshare: Display BSP header
├── lcd_bsp.c                             # Waveshare: Display BSP implementation
├── FT3168.h                              # Waveshare: Touch controller header
├── FT3168.cpp                            # Waveshare: Touch controller implementation
├── PhysiologicalSimulator.h              # Existing: Vitals simulator
├── PhysiologicalSimulator.cpp            # Existing: Vitals simulator impl
├── ADS1298Simulator.h                    # Existing: ECG simulator
├── ADS1298Simulator.cpp                  # Existing: ECG simulator impl
├── MAX86178Simulator.h                   # Existing: PPG simulator
├── MAX86178Simulator.cpp                 # Existing: PPG simulator impl
├── BMI323Simulator.h                     # Existing: IMU simulator
├── BMI323Simulator.cpp                   # Existing: IMU simulator impl
├── STS40Simulator.h                      # Existing: Temp simulator
├── STS40Simulator.cpp                    # Existing: Temp simulator impl
├── NFCManager.h                          # Existing: NFC handler
├── NFCManager.cpp                        # Existing: NFC handler impl
├── LVGL_INTEGRATION_PLAN.md              # Documentation
├── LIBRARY_DEPENDENCIES.md               # This file
└── waveshare_demo/                       # Downloaded demo (can be deleted after copy)
```

## Compilation Settings

### Memory Allocation
- **PSRAM**: MANDATORY - LVGL display buffers are allocated in PSRAM
- **SRAM**: Used for stack and small variables
- **Flash**: 16MB for code and SPIFFS

### Compiler Flags (Optional Optimization)
Add to `platform.local.txt` or `boards.txt`:
```
compiler.cpp.extra_flags=-DLV_CONF_INCLUDE_SIMPLE -DLV_LVGL_H_INCLUDE_SIMPLE
```

## Troubleshooting

### Issue 1: "lv_conf.h: No such file or directory"
**Solution**: Create `lv_conf.h` in Arduino libraries folder (see above)

### Issue 2: "undefined reference to lv_..."
**Solution**: Ensure LVGL library is installed via Library Manager

### Issue 3: "PSRAM not found"
**Solution**:
- Check board settings: Tools → PSRAM → "OPI PSRAM"
- Verify hardware has PSRAM (ESP32-S3R8 has 8MB PSRAM)

### Issue 4: "Stack overflow" or random crashes
**Solution**:
- Increase FreeRTOS stack size in main loop
- Move large buffers to PSRAM
- Reduce `LV_MEM_SIZE` if needed

### Issue 5: "Touch not working"
**Solution**:
- Verify I2C pins: SDA=GPIO47, SCL=GPIO48
- Check FT3168 I2C address: 0x38
- Test with Waveshare demo first

### Issue 6: "Display shows garbage"
**Solution**:
- Verify QSPI pins match lcd_config.h
- Check `LV_COLOR_DEPTH` is set to 16
- Ensure CO5300 driver initialization succeeds

## Testing Procedure

1. **Compile Test**: Verify → Compiles without errors
2. **Upload Test**: Upload → Device boots and shows serial output
3. **Display Test**: Screen shows LVGL UI (home screen)
4. **Touch Test**: Swipe left/right changes screens
5. **Vitals Test**: Real-time vitals update on home screen
6. **Waveform Test**: Waveform screen shows scrolling ECG/EEG
7. **Alerts Test**: Alerts appear when device alerts trigger
8. **Integration Test**: MQTT transmission continues while UI updates

## Performance Targets

- **Frame Rate**: 30 FPS (minimum)
- **Touch Latency**: <100ms
- **MQTT Impact**: <5% increase in loop time
- **Memory Usage**: <150KB SRAM, <1MB PSRAM
- **Power Consumption**: TBD (measure with ammeter)

## Version Compatibility

| Component | Version | Notes |
|-----------|---------|-------|
| Arduino IDE | 2.x | Recommended (or 1.8.19+) |
| ESP32 Core | 3.0.0+ | Required for ESP32-S3 |
| LVGL | 9.x | v9.2.0 or newer |
| ArduinoJson | 7.x | Already in project |
| PubSubClient | 2.8+ | Already in project |

## Next Steps After Library Installation

1. Install LVGL library
2. Create `lv_conf.h` configuration file
3. Verify ESP32 board support is installed
4. Select correct board: "ESP32S3 Dev Module"
5. Configure PSRAM: "OPI PSRAM"
6. Compile firmware
7. Upload to device
8. Test display and touch
9. Monitor serial output for errors

---

**Last Updated**: 2025-01-21
**Firmware Version**: v5.2.14 + LVGL Integration
**Hardware**: Waveshare ESP32-S3-Touch-AMOLED-1.64
