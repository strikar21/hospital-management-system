# LVGL Integration Plan for ESP32-S3 Hospital Watch
## Waveshare ESP32-S3-Touch-AMOLED-1.64 (280×456 AMOLED Display)

**Date**: 2025-01-21
**Firmware Version**: v5.2.14
**Hardware**: Waveshare ESP32-S3-Touch-AMOLED-1.64

---

## Hardware Specifications

### Display
- **Model**: 1.64" AMOLED Capacitive Touch Display
- **Resolution**: 280×456 pixels
- **Color Depth**: 16-bit (RGB565) - 16.7M colors
- **Driver IC**: CO5300 (QSPI interface)
- **Touch Controller**: FT3168 (I2C interface)

### MCU
- **Chip**: ESP32-S3R8
- **CPU**: Dual-core Xtensa 32-bit LX7 @ 240MHz
- **Flash**: 16MB
- **PSRAM**: 8MB
- **SRAM**: 512KB

### Onboard Sensors
- **IMU**: QMI8658 6-axis (3-axis accelerometer + 3-axis gyroscope)
- **Interface**: I2C (shared with touch controller)

---

## Pin Assignments (Extracted from Waveshare Demo)

### QSPI Display Pins (CO5300 Driver)
| Function | GPIO Pin |
|----------|----------|
| CS       | GPIO 9   |
| PCLK     | GPIO 10  |
| DATA0    | GPIO 11  |
| DATA1    | GPIO 12  |
| DATA2    | GPIO 13  |
| DATA3    | GPIO 14  |
| RST      | GPIO 21  |
| BL       | -1 (No backlight control - AMOLED) |

### I2C Touch & IMU Pins (FT3168 + QMI8658)
| Function | GPIO Pin | I2C Address |
|----------|----------|-------------|
| SDA      | GPIO 47  | -           |
| SCL      | GPIO 48  | -           |
| FT3168   | -        | 0x38        |
| QMI8658  | -        | 0x6A (typical) |

### Other Pins (From Current Firmware)
| Function | GPIO Pin | Usage |
|----------|----------|-------|
| MODE_SELECT | GPIO 4 | ECG/EEG mode selection |
| LED_PIN | GPIO 5 | Alert LED indicator |

---

## LVGL Configuration

### Version
- **Target**: LVGL v9.x (latest stable)
- **Reason**: Future-proof, modern API, better performance

### Memory Configuration
- **Display Buffer**: Single buffering (280 × 456 ÷ 4 = 114 lines)
- **Buffer Size**: 280 × 114 × 2 bytes = 63,840 bytes (~62KB)
- **Color Format**: RGB565 (16-bit)
- **Total LVGL Memory**: ~128KB allocated

### LVGL Task Settings
| Parameter | Value | Notes |
|-----------|-------|-------|
| Tick Period | 2ms | System tick for animations |
| Task Priority | 2 | FreeRTOS priority |
| Task Stack | 4KB | Adequate for UI operations |
| Max Delay | 500ms | Maximum LVGL task delay |
| Min Delay | 1ms | Minimum LVGL task delay |

---

## Required Libraries

### Arduino IDE Libraries
1. **LVGL** (v9.x)
   - Install from Arduino Library Manager
   - Or download from: https://github.com/lvgl/lvgl

2. **FT3168 Touch Driver** (from Waveshare demo)
   - Copy from downloaded demo: `waveshare_demo/ESP32-S3-Touch-AMOLED-1.64-Demo/Arduino/examples/06_LVGL_Test/FT3168.h/cpp`

3. **LCD BSP** (from Waveshare demo)
   - Copy from downloaded demo: `waveshare_demo/ESP32-S3-Touch-AMOLED-1.64-Demo/Arduino/examples/06_LVGL_Test/lcd_bsp.h/c`

4. **Existing Libraries** (already in firmware)
   - WiFi.h
   - PubSubClient.h
   - ArduinoJson.h
   - Preferences.h
   - SPIFFS.h

---

## Architecture & File Structure

### New Files to Create

#### 1. `DisplayManager.h` / `DisplayManager.cpp`
**Purpose**: Initialize and manage LVGL display and touch input

**Responsibilities**:
- Initialize QSPI display (CO5300 driver)
- Initialize I2C touch controller (FT3168)
- Set up LVGL display driver
- Set up LVGL input device driver
- Manage display buffer
- Provide display update function (`lv_task_handler()`)

**Key Functions**:
```cpp
class DisplayManager {
public:
    void init();                          // Initialize display, touch, and LVGL
    void update();                        // Call lv_task_handler()
    void setBrightness(uint8_t level);    // Control AMOLED brightness (0-255)
    bool isInitialized();                 // Check if display is ready
private:
    static void displayFlush(lv_display_t *disp, const lv_area_t *area, uint8_t *px_map);
    static void touchRead(lv_indev_t *indev, lv_indev_data_t *data);
};
```

#### 2. `UIScreens.h` / `UIScreens.cpp`
**Purpose**: Define and manage all UI screens

**Screen Types**:
1. **Home Screen** (default)
   - Patient vitals: HR, SpO2, Temp, BP, RR
   - Connection status (WiFi, MQTT, NFC)
   - Battery level
   - Device ID

2. **Waveform Screen** (ECG/EEG)
   - Real-time 12-lead ECG or 8-channel EEG chart
   - Lead labels (I, II, III, aVR, aVL, aVF, V1-V6) or (Fp1, Fp2, F3, F4, C3, C4, O1, O2)
   - Time scale indicator
   - Mode indicator (ECG/EEG)

3. **Alerts Screen**
   - Active alerts list
   - Alert severity (critical/warning/info)
   - Alert timestamps
   - Clear/acknowledge button

4. **Settings Screen**
   - WiFi credentials
   - Device pairing status
   - Display brightness
   - Debug info toggle

**Key Functions**:
```cpp
class UIScreens {
public:
    void init();                                    // Create all screens
    void showHomeScreen();                          // Switch to home screen
    void showWaveformScreen();                      // Switch to waveform screen
    void showAlertsScreen();                        // Switch to alerts screen
    void showSettingsScreen();                      // Switch to settings screen

    // Update functions (called from main loop)
    void updateVitals(float hr, float spo2, float temp, float bpSys, float bpDia, float rr);
    void updateWaveform(int16_t *samples, uint8_t numSamples, const char *mode);
    void updateConnectionStatus(bool wifi, bool mqtt, bool nfc);
    void updateBattery(uint8_t percent);
    void addAlert(const char *message, uint8_t severity);

private:
    lv_obj_t *homeScreen;
    lv_obj_t *waveformScreen;
    lv_obj_t *alertsScreen;
    lv_obj_t *settingsScreen;

    // Home screen widgets
    lv_obj_t *labelHR;
    lv_obj_t *labelSpO2;
    lv_obj_t *labelTemp;
    lv_obj_t *labelBP;
    lv_obj_t *labelRR;
    lv_obj_t *iconWiFi;
    lv_obj_t *iconMQTT;
    lv_obj_t *iconBattery;

    // Waveform screen widgets
    lv_obj_t *chartECG;
    lv_chart_series_t *seriesLeadI;
    lv_chart_series_t *seriesLeadII;
    // ... more series

    // Alert screen widgets
    lv_obj_t *alertList;
};
```

#### 3. `TouchHandler.h` / `TouchHandler.cpp`
**Purpose**: Handle touch gestures and screen navigation

**Gestures**:
- **Swipe Left**: Next screen
- **Swipe Right**: Previous screen
- **Tap**: Button interactions
- **Long Press**: Show menu/settings

**Key Functions**:
```cpp
class TouchHandler {
public:
    void init(UIScreens *screens);        // Initialize with screen manager
    void update();                        // Process touch events
    void setGestureCallback(void (*callback)(GestureType type));

private:
    UIScreens *uiScreens;
    int16_t startX, startY;
    uint32_t touchStartTime;
    bool isSwiping;

    void handleSwipe(int16_t deltaX, int16_t deltaY);
    void handleTap(int16_t x, int16_t y);
    void handleLongPress(int16_t x, int16_t y);
};

enum GestureType {
    SWIPE_LEFT,
    SWIPE_RIGHT,
    SWIPE_UP,
    SWIPE_DOWN,
    TAP,
    LONG_PRESS
};
```

---

## Integration with Existing Firmware

### Main Loop Modifications (`esp32_hospital_watch_complete.ino`)

#### In `setup()`:
```cpp
#include "DisplayManager.h"
#include "UIScreens.h"
#include "TouchHandler.h"

DisplayManager display;
UIScreens ui;
TouchHandler touch;

void setup() {
    // ... existing setup code ...

    // Initialize display system
    display.init();
    ui.init();
    touch.init(&ui);

    Serial.println("LVGL display initialized");
}
```

#### In `loop()`:
```cpp
void loop() {
    unsigned long currentMillis = millis();

    // ... existing WiFi/MQTT handling ...

    // Update display (MUST be called frequently - every 5-10ms)
    display.update();
    touch.update();

    // Update vitals display (every 1 second)
    if ((unsigned long)(currentMillis - lastVitalsUpdateDisplay) >= 1000) {
        lastVitalsUpdateDisplay = currentMillis;
        ui.updateVitals(heartRate, spo2, temperature, bloodPressureSystolic, bloodPressureDiastolic, respiratoryRate);
        ui.updateConnectionStatus(wifiConnected, mqttConnected, nfcDetected);
    }

    // Update waveform display (when new samples arrive)
    if (newWaveformSamples) {
        ui.updateWaveform(waveformBuffer, numSamples, currentMode);
        newWaveformSamples = false;
    }

    // ... rest of existing loop ...
}
```

### Alert Integration
When device alerts are triggered, add them to the UI:
```cpp
// In triggerAlert() function
void triggerAlert(const char* type, const char* message) {
    // ... existing MQTT alert code ...

    // Add to display
    uint8_t severity = 2; // Critical
    if (strcmp(type, "warning") == 0) severity = 1;
    if (strcmp(type, "info") == 0) severity = 0;
    ui.addAlert(message, severity);
}
```

---

## Display Content Design

### Home Screen Layout (280×456)
```
┌──────────────────────────┐
│  Hospital Watch v5.2.14  │  ← Title bar
│  [WiFi] [MQTT] [Battery] │  ← Status icons
├──────────────────────────┤
│                          │
│    ♥ 75 bpm              │  ← Heart rate (large)
│                          │
│    SpO2: 98%             │  ← Oxygen saturation
│    Temp: 36.8°C          │  ← Temperature
│    BP: 120/80 mmHg       │  ← Blood pressure
│    RR: 16 bpm            │  ← Respiratory rate
│                          │
│  Device: WATCH-ABC123    │  ← Device ID
│  Patient: John Doe       │  ← Patient name (from NFC/MQTT)
│                          │
│  ← Swipe for waveforms   │  ← Gesture hint
└──────────────────────────┘
```

### Waveform Screen Layout
```
┌──────────────────────────┐
│  ECG - 12 Lead View      │  ← Mode indicator
├──────────────────────────┤
│ I   ～～～～～～～～～～  │  ← Lead I
│ II  ～～～～～～～～～～  │  ← Lead II
│ III ～～～～～～～～～～  │  ← Lead III
│ aVR ～～～～～～～～～～  │  ← aVR
│ aVL ～～～～～～～～～～  │  ← aVL
│ aVF ～～～～～～～～～～  │  ← aVF
│ V1  ～～～～～～～～～～  │  ← V1 (scroll down)
│                          │
│  ← Swipe to navigate     │
└──────────────────────────┘
```

### Alerts Screen Layout
```
┌──────────────────────────┐
│  Active Alerts (3)       │  ← Alert count
├──────────────────────────┤
│ [!] HR HIGH: 145 bpm     │  ← Critical alert
│     14:32:15             │
├──────────────────────────┤
│ [!] Battery Low: 15%     │  ← Warning alert
│     14:30:02             │
├──────────────────────────┤
│ [i] WiFi reconnected     │  ← Info alert
│     14:25:48             │
├──────────────────────────┤
│                          │
│  [Clear All Alerts]      │  ← Action button
└──────────────────────────┘
```

---

## Memory Budget Analysis

### Current Firmware Memory Usage (Estimated)
- Global variables: ~50KB
- MQTT buffers: ~32KB
- SPIFFS queue: ~20KB
- Stack/heap: ~100KB
- **Total**: ~202KB

### LVGL Memory Requirements
- Display buffer: 62KB
- LVGL heap: 64KB
- Touch buffer: 2KB
- **Total**: ~128KB

### ESP32-S3 Memory Available
- PSRAM: 8MB (8192KB) ← Use this for LVGL buffers
- SRAM: 512KB

**Strategy**: Allocate LVGL display buffer in PSRAM to avoid SRAM overflow

---

## Implementation Steps

### Phase 1: Display Initialization (Priority: P0)
- [ ] Copy Waveshare demo files (lcd_bsp, FT3168) to project
- [ ] Create DisplayManager class
- [ ] Initialize QSPI display driver
- [ ] Initialize I2C touch controller
- [ ] Test display output (show test pattern)
- [ ] Test touch input (print coordinates to serial)

### Phase 2: Basic UI (Priority: P0)
- [ ] Create UIScreens class
- [ ] Implement Home screen with static vitals
- [ ] Add connection status icons
- [ ] Integrate with main loop
- [ ] Test display updates

### Phase 3: Waveform Display (Priority: P1)
- [ ] Create LVGL chart widget for ECG/EEG
- [ ] Implement real-time waveform streaming to chart
- [ ] Add lead labels and time scale
- [ ] Test with physiological simulator data

### Phase 4: Touch Navigation (Priority: P1)
- [ ] Create TouchHandler class
- [ ] Implement swipe gesture detection
- [ ] Add screen transitions
- [ ] Test navigation between screens

### Phase 5: Alerts & Settings (Priority: P2)
- [ ] Implement Alerts screen
- [ ] Implement Settings screen
- [ ] Add alert notifications with vibration (if hardware supports)
- [ ] Add brightness control

### Phase 6: Polish & Optimization (Priority: P3)
- [ ] Add animations and transitions
- [ ] Optimize memory usage
- [ ] Add visual themes (day/night mode)
- [ ] Performance tuning

---

## Testing Checklist

### Display Tests
- [ ] Display initializes without errors
- [ ] Touch responds accurately across entire screen
- [ ] Colors render correctly (RGB565)
- [ ] No screen flicker or tearing
- [ ] Brightness control works (0-255)

### UI Tests
- [ ] All vitals update correctly
- [ ] Waveforms display in real-time
- [ ] Connection status icons update
- [ ] Battery indicator works
- [ ] Alert list populates correctly

### Touch Tests
- [ ] Swipe left/right navigates screens
- [ ] Tap activates buttons
- [ ] Multi-touch not interfering
- [ ] Touch calibration accurate
- [ ] No ghost touches

### Integration Tests
- [ ] Display updates don't block MQTT
- [ ] Waveform streaming continues during UI updates
- [ ] Alert generation triggers UI notification
- [ ] WiFi captive portal still works
- [ ] NFC scanning not affected
- [ ] Offline queue still functions

### Memory Tests
- [ ] No memory leaks after 24h runtime
- [ ] PSRAM usage stays within limits
- [ ] SRAM usage stays within limits
- [ ] Stack overflow protection works

---

## Code Style Requirements (From CLAUDE.md)

### Naming Conventions
- **ALL variables**: camelCase (e.g., `heartRate`, `spo2`, `bloodPressureSystolic`)
- **ALL functions**: camelCase (e.g., `updateVitals()`, `showHomeScreen()`)
- **ALL class names**: PascalCase (e.g., `DisplayManager`, `UIScreens`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `EXAMPLE_LCD_H_RES`)

### Code Structure
- **Modular**: Small, focused functions (<100 lines)
- **No stubs**: All functions fully implemented
- **No quick fixes**: Root cause analysis required
- **Production ready**: No TODOs or incomplete code

### Medical Compliance
- **ALL medical logic**: Backend only
- **Frontend/Display**: Display layer only, NO medical calculations
- **Alerts**: Watch generates device alerts (battery, connection), backend generates clinical alerts
- **NO clinical decisions**: Watch does NOT detect arrhythmias or diagnose conditions

---

## Dependencies & Installation

### Arduino IDE Setup
1. Install ESP32 board support (v3.0+)
2. Install LVGL library (v9.x)
3. Copy Waveshare demo files to project folder:
   - `lcd_bsp.h`, `lcd_bsp.c`
   - `FT3168.h`, `FT3168.cpp`
   - `lcd_config.h`

### Library Configuration
- **lv_conf.h**: Must be created in Arduino libraries folder
- **Configuration options**:
  ```c
  #define LV_COLOR_DEPTH 16
  #define LV_MEM_SIZE (128 * 1024)
  #define LV_USE_PERF_MONITOR 1
  #define LV_USE_MEM_MONITOR 1
  ```

---

## Risk Analysis & Mitigation

### Risk 1: Memory Overflow
- **Probability**: Medium
- **Impact**: High (device crash)
- **Mitigation**: Use PSRAM for display buffers, monitor heap usage

### Risk 2: Display Update Blocking MQTT
- **Probability**: Low
- **Impact**: High (missed vitals transmission)
- **Mitigation**: Keep `lv_task_handler()` calls short (<5ms), use FreeRTOS tasks if needed

### Risk 3: Touch Not Working
- **Probability**: Low
- **Impact**: Medium (no user interaction)
- **Mitigation**: Test with Waveshare demo first, verify I2C pins

### Risk 4: Waveform Display Lag
- **Probability**: Medium
- **Impact**: Medium (poor user experience)
- **Mitigation**: Use downsampling (display every 2nd or 4th sample), optimize chart rendering

---

## Success Criteria

### Must-Have (P0)
- ✅ Display shows vitals in real-time
- ✅ Touch navigation works (swipe between screens)
- ✅ No impact on MQTT transmission
- ✅ Device remains stable for 24+ hours

### Should-Have (P1)
- ✅ Waveform display shows ECG/EEG
- ✅ Alert notifications appear on screen
- ✅ Connection status indicators work

### Nice-to-Have (P2)
- ✅ Settings screen functional
- ✅ Brightness control
- ✅ Smooth animations

---

## Next Steps

After plan approval:
1. Create DisplayManager files
2. Create UIScreens files
3. Create TouchHandler files
4. Update main .ino file
5. Test compilation
6. Flash and test on hardware

**Estimated Implementation Time**: 6-8 hours (excluding testing)

---

## Questions for User (BEFORE Implementation)

1. ✅ Do you want patient name/ID displayed on the watch? (If yes, how is it loaded - NFC, MQTT, manual entry?)
2. ✅ Should the watch vibrate on critical alerts? (Need to know if there's a vibration motor)
3. ✅ Do you want to display all 12 ECG leads or just a subset (e.g., Lead I, II, V1)?
4. ✅ Battery monitoring - is there a battery voltage pin to read? (Need GPIO pin number)
5. ✅ Do you want the waveform screen to auto-scroll or freeze at user request?

---

**Plan Status**: ✅ READY FOR IMPLEMENTATION
**Approval Required**: YES (per CLAUDE.md guidelines - ask before implementing)
