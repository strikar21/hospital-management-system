/**
 * DisplayManager.cpp
 * Hospital Watch Display Manager - LVGL v8 Integration Implementation
 *
 * Thin wrapper around Waveshare BSP (lcd_bsp.c)
 * The BSP handles all LVGL driver registration for display and touch
 */

#include "DisplayManager.h"

// LVGL tick timer
static unsigned long lastLvglTick = 0;

DisplayManager::DisplayManager()
    : initialized(false),
      currentBrightness(173) {  // 68% brightness (173/255 = 0.678)
}

DisplayManager::~DisplayManager() {
}

bool DisplayManager::init() {
    if (initialized) {
        Serial.println("⚠️ DisplayManager already initialized");
        return true;
    }

    Serial.println("🖥️ Initializing DisplayManager...");

    // ✅ v5.3: Initialize touch controller FIRST (before LVGL)
    // This is critical! lcd_lvgl_Init() assumes touch is already initialized
    Serial.println("📱 Initializing touch controller (FT3168)...");
    Touch_Init();
    Serial.println("✅ Touch controller initialized");

    // ✅ v5.3: Use Waveshare BSP function - it handles display + LVGL:
    // - Initializes LVGL library (lv_init)
    // - Initializes SPI bus and display hardware
    // - Creates LVGL display buffers (DMA-capable)
    // - Registers LVGL display driver with flush callback
    // - Registers LVGL input device driver with touch callback (uses getTouch())
    // - Creates LVGL task and timer
    Serial.println("🖥️ Initializing LVGL and display...");
    lcd_lvgl_Init();
    Serial.println("✅ Display initialized (280×456 AMOLED with touch)");

    // Set default brightness
    setBrightness(currentBrightness);

    initialized = true;
    Serial.println("✅ DisplayManager initialization complete");

    return true;
}

void DisplayManager::update() {
    // ✅ v5.3: lcd_lvgl_Init() creates a FreeRTOS task that handles lv_task_handler()
    // No need to call it from loop() - the Waveshare BSP handles everything
    // This function is kept for API compatibility but does nothing
}

bool DisplayManager::isInitialized() const {
    return initialized;
}

void DisplayManager::setBrightness(uint8_t level) {
    currentBrightness = level;
    set_amoled_backlight(level);
}

uint8_t DisplayManager::getBrightness() const {
    return currentBrightness;
}

uint16_t DisplayManager::getWidth() const {
    return DISPLAY_WIDTH;
}

uint16_t DisplayManager::getHeight() const {
    return DISPLAY_HEIGHT;
}

void DisplayManager::lvglTickCallback() {
    // Tick handling is done in update() method
    // This function exists for API compatibility but is not used
}
