/**
 * PatientBar.cpp
 * Hospital Watch - Patient Info Bar Component Implementation
 *
 * Author: Claude/Anthropic
 * Date: 2025-11-22
 */

#include "PatientBar.h"

PatientBar::PatientBar() : container(nullptr), labelPatientInfo(nullptr), initialized(false) {
}

PatientBar::~PatientBar() {
    // LVGL objects are automatically cleaned up when parent is deleted
}

lv_obj_t* PatientBar::create(lv_obj_t* parent) {
    if (!parent) {
        Serial.println("❌ PatientBar: Parent object is null!");
        return nullptr;
    }

    // Create patient bar container
    container = lv_obj_create(parent);
    lv_obj_set_size(container, 280, HEIGHT);
    lv_obj_align(container, LV_ALIGN_TOP_MID, 0, Y_POSITION);
    lv_obj_set_style_bg_color(container, lv_color_hex(0x00FF00), 0);  // ✅ Green background
    lv_obj_set_style_bg_opa(container, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(container, 0, 0);
    lv_obj_set_style_radius(container, 0, 0);
    lv_obj_set_style_pad_all(container, 5, 0);
    lv_obj_clear_flag(container, LV_OBJ_FLAG_SCROLLABLE);

    // Patient/Device ID label (centered)
    labelPatientInfo = lv_label_create(container);
    lv_label_set_text(labelPatientInfo, "Device: Unknown");
    lv_obj_set_style_text_font(labelPatientInfo, &lv_font_montserrat_18, 0);
    lv_obj_set_style_text_color(labelPatientInfo, lv_color_hex(0x000000), 0);  // ✅ Black text on green bg
    lv_obj_set_style_text_align(labelPatientInfo, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_set_width(labelPatientInfo, 260);
    lv_label_set_long_mode(labelPatientInfo, LV_LABEL_LONG_SCROLL_CIRCULAR);  // Scroll if too long
    lv_obj_center(labelPatientInfo);

    initialized = true;
    Serial.println("✅ PatientBar: Initialized (35px height at Y=35)");

    return container;
}

void PatientBar::updatePatientId(const char* patientId) {
    if (!initialized || !labelPatientInfo) return;

    char buf[64];
    if (patientId && strlen(patientId) > 0) {
        snprintf(buf, sizeof(buf), "Patient: %s", patientId);
    } else {
        snprintf(buf, sizeof(buf), "No Patient Assigned");
    }
    lv_label_set_text(labelPatientInfo, buf);
}

void PatientBar::updateDeviceId(const char* deviceId) {
    if (!initialized || !labelPatientInfo) return;

    char buf[64];
    if (deviceId && strlen(deviceId) > 0) {
        snprintf(buf, sizeof(buf), "Device: %s", deviceId);
    } else {
        snprintf(buf, sizeof(buf), "Device: Unknown");
    }
    lv_label_set_text(labelPatientInfo, buf);
}

lv_obj_t* PatientBar::getContainer() const {
    return container;
}

bool PatientBar::isInitialized() const {
    return initialized;
}
