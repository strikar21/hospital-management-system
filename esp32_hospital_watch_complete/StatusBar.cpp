/**
 * StatusBar.cpp
 * Hospital Watch - Top Status Bar Component Implementation
 * REDESIGNED: Modern dark theme with MedicalTheme system
 *
 * Author: Design Team
 * Date: 2025-11-23
 */

#include "StatusBar.h"
#include "MedicalTheme.h"

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

    // Create status bar container (pure black for AMOLED) - 30px per your spec
    container = lv_obj_create(parent);
    lv_obj_set_size(container, 280, HEIGHT);  // 30px as per layout (Status:30px + Patient:40px + Vitals:204px + ECG:182px = 456px)
    lv_obj_align(container, LV_ALIGN_TOP_MID, 0, 0);
    lv_obj_set_style_bg_color(container, MedicalTheme::BG_BLACK, 0);  // Pure black
    lv_obj_set_style_bg_opa(container, MedicalTheme::OPA_FULL, 0);
    lv_obj_set_style_border_width(container, 0, 0);
    lv_obj_set_style_radius(container, 0, 0);
    lv_obj_set_style_pad_all(container, 0, 0);
    lv_obj_clear_flag(container, LV_OBJ_FLAG_SCROLLABLE);

    // Time label (left side) - larger for 30px height
    labelTime = lv_label_create(container);
    lv_label_set_text(labelTime, "00:00");
    lv_obj_set_style_text_font(labelTime, &lv_font_montserrat_20, 0);  // Increased from 16 to 20
    lv_obj_set_style_text_color(labelTime, MedicalTheme::TEXT_PRIMARY, 0);
    lv_obj_align(labelTime, LV_ALIGN_LEFT_MID, 8, 0);

    // WiFi icon (right side, before battery) - blue when connected
    iconWiFi = lv_label_create(container);
    lv_label_set_text(iconWiFi, LV_SYMBOL_WIFI);
    lv_obj_set_style_text_font(iconWiFi, &lv_font_montserrat_18, 0);  // Increased from 14 to 18
    lv_obj_set_style_text_color(iconWiFi, MedicalTheme::ACCENT, 0);  // Blue accent
    lv_obj_align(iconWiFi, LV_ALIGN_RIGHT_MID, -95, 0);  // Moved left from -75 to -95

    // Battery icon (right side)
    iconBattery = lv_label_create(container);
    lv_label_set_text(iconBattery, LV_SYMBOL_BATTERY_FULL);
    lv_obj_set_style_text_font(iconBattery, &lv_font_montserrat_20, 0);  // Increased from 16 to 20
    lv_obj_set_style_text_color(iconBattery, MedicalTheme::TEXT_PRIMARY, 0);
    lv_obj_align(iconBattery, LV_ALIGN_RIGHT_MID, -65, 0);  // Moved left from -45 to -65

    // Battery percentage (right side, after battery icon) - slightly dimmed
    labelBatteryPercent = lv_label_create(container);
    lv_label_set_text(labelBatteryPercent, "100%");
    lv_obj_set_style_text_font(labelBatteryPercent, &lv_font_montserrat_14, 0);  // Increased from 12 to 14
    lv_obj_set_style_text_color(labelBatteryPercent, MedicalTheme::TEXT_SECONDARY, 0);  // Gray
    lv_obj_align(labelBatteryPercent, LV_ALIGN_RIGHT_MID, -8, 0);  // Keep at -8 for edge alignment

    initialized = true;
    Serial.println("✅ StatusBar: Initialized with MedicalTheme (30px height)");

    return container;
}

void StatusBar::updateTime(const char* timeStr) {
    if (!initialized || !labelTime) return;
    lv_label_set_text(labelTime, timeStr);
}

void StatusBar::updateWiFi(bool connected) {
    if (!initialized || !iconWiFi) return;

    if (connected) {
        lv_obj_set_style_text_color(iconWiFi, MedicalTheme::ACCENT, 0);  // Blue
        lv_label_set_text(iconWiFi, LV_SYMBOL_WIFI);
    } else {
        lv_obj_set_style_text_color(iconWiFi, MedicalTheme::TEXT_DIM, 0);  // Dim gray
        lv_label_set_text(iconWiFi, LV_SYMBOL_WARNING);  // Warning symbol when disconnected
    }
}

void StatusBar::updateBattery(uint8_t percent) {
    if (!initialized || !iconBattery || !labelBatteryPercent) return;

    // Update percentage text
    char buf[8];
    snprintf(buf, sizeof(buf), "%d%%", percent);
    lv_label_set_text(labelBatteryPercent, buf);

    // Update battery icon based on level + color coding
    if (percent > 90) {
        lv_label_set_text(iconBattery, LV_SYMBOL_BATTERY_FULL);
        lv_obj_set_style_text_color(iconBattery, MedicalTheme::TEXT_PRIMARY, 0);
    } else if (percent > 50) {
        lv_label_set_text(iconBattery, LV_SYMBOL_BATTERY_3);
        lv_obj_set_style_text_color(iconBattery, MedicalTheme::TEXT_PRIMARY, 0);
    } else if (percent > 20) {
        lv_label_set_text(iconBattery, LV_SYMBOL_BATTERY_2);
        lv_obj_set_style_text_color(iconBattery, MedicalTheme::STATUS_WARNING, 0);  // Orange
    } else {
        lv_label_set_text(iconBattery, LV_SYMBOL_BATTERY_1);
        lv_obj_set_style_text_color(iconBattery, MedicalTheme::STATUS_CRITICAL, 0);  // Red
    }
}

lv_obj_t* StatusBar::getContainer() const {
    return container;
}

bool StatusBar::isInitialized() const {
    return initialized;
}
