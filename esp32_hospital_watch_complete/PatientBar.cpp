/**
 * PatientBar.cpp
 * Hospital Watch - Patient Info Bar Component Implementation
 * REDESIGNED: Dark theme, NO MORE NEON GREEN
 *
 * Author: Design Team
 * Date: 2025-11-23
 */

#include "PatientBar.h"
#include "MedicalTheme.h"

// LVGL mutex helpers (from lcd_bsp.c) - use defensively in public update methods
extern "C" {
    bool example_lvgl_lock(int timeout_ms);
    void example_lvgl_unlock(void);
}
PatientBar::PatientBar() : container(nullptr), labelPatientInfo(nullptr), labelMRN(nullptr), initialized(false) {
}

PatientBar::~PatientBar() {
    // LVGL objects are automatically cleaned up when parent is deleted
}

lv_obj_t* PatientBar::create(lv_obj_t* parent) {
    if (!parent) {
        Serial.println("❌ PatientBar: Parent object is null!");
        return nullptr;
    }

    // Create patient bar container - DARK GRAY - 40px per your spec
    container = lv_obj_create(parent);
    lv_obj_set_size(container, 280, HEIGHT);  // 40px as per layout
    lv_obj_align(container, LV_ALIGN_TOP_MID, 0, Y_POSITION);  // Below status bar (30px)

    // ✅ Set background color explicitly (dark gray)
    lv_obj_set_style_bg_color(container, MedicalTheme::BG_DARK, 0);  // Dark gray
    Serial.printf("PatientBar: BG_DARK set to 0x1A1A1A (should be dark gray, not pink!)\n");
    lv_obj_set_style_bg_opa(container, LV_OPA_COVER, 0);  // Full opacity
    lv_obj_set_style_border_width(container, 0, 0);
    lv_obj_set_style_radius(container, 0, 0);
    lv_obj_set_style_pad_all(container, 0, 0);
    lv_obj_clear_flag(container, LV_OBJ_FLAG_SCROLLABLE);

    // Patient icon (left side) - using HOME symbol (closest to person)
    lv_obj_t* patientIcon = lv_label_create(container);
    lv_label_set_text(patientIcon, LV_SYMBOL_HOME);  // No USER symbol in LVGL, using HOME
    lv_obj_set_style_text_color(patientIcon, MedicalTheme::ACCENT, 0);  // Blue icon
    lv_obj_set_style_text_font(patientIcon, &lv_font_montserrat_22, 0);  // Increased from 16 to 22
    lv_obj_align(patientIcon, LV_ALIGN_LEFT_MID, 8, 0);

    // Patient name (white, larger for 40px height) - "John Smith  45M"
    labelPatientInfo = lv_label_create(container);
    lv_label_set_text(labelPatientInfo, "Unassigned");
    lv_obj_set_style_text_color(labelPatientInfo, MedicalTheme::TEXT_PRIMARY, 0);  // White
    lv_obj_set_style_text_font(labelPatientInfo, &lv_font_montserrat_18, 0);  // Increased from 14 to 18
    lv_obj_set_width(labelPatientInfo, 150);
    lv_label_set_long_mode(labelPatientInfo, LV_LABEL_LONG_SCROLL_CIRCULAR);  // Scroll if too long
    lv_obj_align(labelPatientInfo, LV_ALIGN_LEFT_MID, 35, 0);

    // MRN label (right side, WHITE text for legibility)
    labelMRN = lv_label_create(container);
    lv_label_set_text(labelMRN, "MRN-000000");
    lv_obj_set_style_text_color(labelMRN, MedicalTheme::TEXT_PRIMARY, 0);  // WHITE (was blue - illegible on pink/gray)
    lv_obj_set_style_text_font(labelMRN, &lv_font_montserrat_20, 0);  // Increased from 16 to 20 for legibility
    lv_obj_align(labelMRN, LV_ALIGN_RIGHT_MID, -8, 0);

    // ✅ Hide MRN by default (shown only when patient is assigned)
    lv_obj_add_flag(labelMRN, LV_OBJ_FLAG_HIDDEN);

    initialized = true;
    Serial.println("✅ PatientBar: Initialized with MedicalTheme (NO MORE GREEN!)");

    return container;
}

void PatientBar::updatePatientId(const char* patientId) {
    if (!initialized || !labelPatientInfo || !labelMRN) return;

    // Defensively acquire LVGL mutex to avoid concurrent UI updates
    if (example_lvgl_lock(50)) {
        if (patientId && strlen(patientId) > 0) {
            // Patient assigned - show patient name and MRN
            lv_label_set_text(labelPatientInfo, patientId);
            lv_obj_set_style_text_color(labelPatientInfo, MedicalTheme::TEXT_PRIMARY, 0);  // White

            // Show MRN label (make it visible)
            lv_obj_clear_flag(labelMRN, LV_OBJ_FLAG_HIDDEN);
        } else {
            // No patient - show "Unassigned" and hide MRN
            lv_label_set_text(labelPatientInfo, "Unassigned");
            lv_obj_set_style_text_color(labelPatientInfo, MedicalTheme::TEXT_SECONDARY, 0);  // Gray

            // Hide MRN label completely
            lv_obj_add_flag(labelMRN, LV_OBJ_FLAG_HIDDEN);
        }
        example_lvgl_unlock();
    } else {
        Serial.println("⚠️ PatientBar::updatePatientId skipped - LVGL mutex timeout");
    }
}

void PatientBar::updateDeviceId(const char* deviceId) {
    if (!initialized || !labelPatientInfo) return;

    char buf[64];
    if (deviceId && strlen(deviceId) > 0) {
        snprintf(buf, sizeof(buf), "Device %s", deviceId);  // Compact format
    } else {
        snprintf(buf, sizeof(buf), "Unknown Device");
    }

    if (example_lvgl_lock(50)) {
        lv_label_set_text(labelPatientInfo, buf);
        lv_obj_set_style_text_color(labelPatientInfo, MedicalTheme::TEXT_SECONDARY, 0);  // Gray when no patient
        example_lvgl_unlock();
    } else {
        Serial.println("⚠️ PatientBar::updateDeviceId skipped - LVGL mutex timeout");
    }
}

lv_obj_t* PatientBar::getContainer() const {
    return container;
}

bool PatientBar::isInitialized() const {
    return initialized;
}
