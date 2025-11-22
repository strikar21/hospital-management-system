/**
 * StatusBar.cpp
 * Hospital Watch - Top Status Bar Component Implementation
 *
 * Author: Claude/Anthropic
 * Date: 2025-11-22
 */

#include "StatusBar.h"

StatusBar::StatusBar() : container(nullptr), labelTime(nullptr), iconWiFi(nullptr),
                         iconBattery(nullptr), labelBatteryPercent(nullptr), initialized(false) {
}

StatusBar::~StatusBar() {
    // LVGL objects are automatically cleaned up when parent is deleted
}

lv_obj_t* StatusBar::create(lv_obj_t* parent) {
    if (!parent) {
        Serial.println("❌ StatusBar: Parent object is null!");
        return nullptr;
    }

    // Create status bar container
    container = lv_obj_create(parent);
    lv_obj_set_size(container, 280, HEIGHT);
    lv_obj_align(container, LV_ALIGN_TOP_MID, 0, 0);
    lv_obj_set_style_bg_color(container, lv_color_hex(BG_COLOR), 0);
    lv_obj_set_style_bg_opa(container, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(container, 0, 0);
    lv_obj_set_style_radius(container, 0, 0);
    lv_obj_set_style_pad_all(container, 5, 0);
    lv_obj_clear_flag(container, LV_OBJ_FLAG_SCROLLABLE);

    // Time label (left side)
    labelTime = lv_label_create(container);
    lv_label_set_text(labelTime, "00:00");
    lv_obj_set_style_text_font(labelTime, &lv_font_montserrat_20, 0);
    lv_obj_set_style_text_color(labelTime, lv_color_hex(0xFFFFFF), 0);  // White text on dark bg
    lv_obj_align(labelTime, LV_ALIGN_LEFT_MID, 10, 0);

    // WiFi icon (right side, before battery)
    iconWiFi = lv_label_create(container);
    lv_label_set_text(iconWiFi, LV_SYMBOL_WIFI);
    lv_obj_set_style_text_font(iconWiFi, &lv_font_montserrat_20, 0);
    lv_obj_set_style_text_color(iconWiFi, lv_color_hex(0xFFFFFF), 0);  // White text on dark bg
    lv_obj_align(iconWiFi, LV_ALIGN_RIGHT_MID, -105, 0);  // ✅ Shifted left from -80 to -105

    // Battery icon (right side)
    iconBattery = lv_label_create(container);
    lv_label_set_text(iconBattery, LV_SYMBOL_BATTERY_FULL);
    lv_obj_set_style_text_font(iconBattery, &lv_font_montserrat_20, 0);
    lv_obj_set_style_text_color(iconBattery, lv_color_hex(0xFFFFFF), 0);  // White text on dark bg
    lv_obj_align(iconBattery, LV_ALIGN_RIGHT_MID, -70, 0);  // ✅ Shifted left from -45 to -70

    // Battery percentage (right side, after battery icon)
    labelBatteryPercent = lv_label_create(container);
    lv_label_set_text(labelBatteryPercent, "100%");
    lv_obj_set_style_text_font(labelBatteryPercent, &lv_font_montserrat_20, 0);  // ✅ Increased from 16 to 20
    lv_obj_set_style_text_color(labelBatteryPercent, lv_color_hex(0xFFFFFF), 0);  // White text on dark bg
    lv_obj_align(labelBatteryPercent, LV_ALIGN_RIGHT_MID, -10, 0);  // ✅ Shifted left from -5 to -30

    initialized = true;
    Serial.println("✅ StatusBar: Initialized (35px height)");

    return container;
}

void StatusBar::updateTime(const char* timeStr) {
    if (!initialized || !labelTime) return;
    lv_label_set_text(labelTime, timeStr);
}

void StatusBar::updateWiFi(bool connected) {
    if (!initialized || !iconWiFi) return;
    // WiFi icon stays white on dark background
}

void StatusBar::updateBattery(uint8_t percent) {
    if (!initialized || !iconBattery || !labelBatteryPercent) return;

    // Update percentage text
    char buf[8];
    snprintf(buf, sizeof(buf), "%d%%", percent);
    lv_label_set_text(labelBatteryPercent, buf);

    // Update battery icon based on level (white text on dark background)
    if (percent > 75) {
        lv_label_set_text(iconBattery, LV_SYMBOL_BATTERY_FULL);
    } else if (percent > 50) {
        lv_label_set_text(iconBattery, LV_SYMBOL_BATTERY_3);
    } else if (percent > 25) {
        lv_label_set_text(iconBattery, LV_SYMBOL_BATTERY_2);
    } else if (percent > 10) {
        lv_label_set_text(iconBattery, LV_SYMBOL_BATTERY_1);
    } else {
        lv_label_set_text(iconBattery, LV_SYMBOL_BATTERY_EMPTY);
    }
}

lv_obj_t* StatusBar::getContainer() const {
    return container;
}

bool StatusBar::isInitialized() const {
    return initialized;
}
