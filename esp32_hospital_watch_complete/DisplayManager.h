/**
 * DisplayManager.h
 * Hospital Watch Display Manager - LVGL Integration
 *
 * Handles QSPI AMOLED display (CO5300) and I2C touch (FT3168) initialization
 * Manages LVGL display driver, input device driver, and update loop
 *
 * Hardware: Waveshare ESP32-S3-Touch-AMOLED-1.64
 * Resolution: 280×456 pixels
 * Color: RGB565 (16-bit)
 */

#ifndef DISPLAY_MANAGER_H
#define DISPLAY_MANAGER_H

#include <Arduino.h>
#include <lvgl.h>

// Forward declarations for Waveshare BSP drivers
extern "C" {
    void lcd_lvgl_Init(void);
    void Touch_Init(void);
    uint8_t getTouch(uint16_t *x, uint16_t *y);
    void set_amoled_backlight(uint8_t level);
}

class DisplayManager {
public:
    /**
     * Constructor
     */
    DisplayManager();

    /**
     * Destructor
     */
    ~DisplayManager();

    /**
     * Initialize display hardware, touch controller, and LVGL
     * Must be called once in setup()
     * @return true if initialization successful, false otherwise
     */
    bool init();

    /**
     * Update LVGL (call lv_task_handler())
     * MUST be called frequently in loop() - every 5-10ms
     */
    void update();

    /**
     * Check if display is initialized and ready
     * @return true if initialized, false otherwise
     */
    bool isInitialized() const;

    /**
     * Set AMOLED display brightness
     * @param level Brightness level (0-255, 0=off, 255=max)
     */
    void setBrightness(uint8_t level);

    /**
     * Get current brightness level
     * @return Current brightness (0-255)
     */
    uint8_t getBrightness() const;

    /**
     * Get display width in pixels
     * @return Display width (280)
     */
    uint16_t getWidth() const;

    /**
     * Get display height in pixels
     * @return Display height (456)
     */
    uint16_t getHeight() const;

private:
    bool initialized;
    uint8_t currentBrightness;

    // Display dimensions (constant for this hardware)
    static const uint16_t DISPLAY_WIDTH = 280;
    static const uint16_t DISPLAY_HEIGHT = 456;

    // LVGL tick timer interval (milliseconds)
    static const uint32_t LVGL_TICK_PERIOD_MS = 2;

    // Note: LVGL v8 callbacks are handled by lcd_bsp.c (Waveshare BSP layer)

    /**
     * LVGL tick increment callback (static)
     * Called periodically to increment LVGL internal tick counter
     */
    static void lvglTickCallback();
};

#endif // DISPLAY_MANAGER_H
