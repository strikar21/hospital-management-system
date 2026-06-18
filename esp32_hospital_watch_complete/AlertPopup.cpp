/**
 * AlertPopup.cpp
 * Hospital Watch - Alert Popup Overlay Component Implementation
 *
 * Author: Claude/Anthropic
 * Date: 2025-11-22
 */

#include "AlertPopup.h"
#include "MedicalTheme.h"

AlertPopup::AlertPopup() : popup(nullptr), labelText(nullptr), initialized(false), visible(false) {
}

AlertPopup::~AlertPopup() {
    // LVGL objects are automatically cleaned up when parent is deleted
}

lv_obj_t* AlertPopup::create(lv_event_cb_t eventCallback, void* userData) {
    // Create popup overlay on active screen (top layer)
    popup = lv_obj_create(lv_scr_act());
    lv_obj_set_size(popup, WIDTH, HEIGHT);
    lv_obj_align(popup, LV_ALIGN_CENTER, 0, Y_OFFSET);
    lv_obj_set_style_bg_color(popup, MedicalTheme::STATUS_CRITICAL, 0);  // Red default
    lv_obj_set_style_bg_opa(popup, LV_OPA_TRANSP, 0);  // Start completely transparent (will be set to 90 when shown)
    lv_obj_set_style_border_width(popup, 2, 0);
    lv_obj_set_style_border_color(popup, MedicalTheme::TEXT_PRIMARY, 0);  // White border
    lv_obj_set_style_border_opa(popup, LV_OPA_TRANSP, 0);  // Start with transparent border too
    lv_obj_set_style_radius(popup, 10, 0);
    lv_obj_set_style_shadow_width(popup, 20, 0);  // Drop shadow
    lv_obj_set_style_shadow_opa(popup, LV_OPA_TRANSP, 0);  // Start with transparent shadow (will be set to 50 when shown)
    lv_obj_add_flag(popup, LV_OBJ_FLAG_HIDDEN);  // Hidden initially
    lv_obj_add_flag(popup, LV_OBJ_FLAG_CLICKABLE);  // Tap to dismiss

    // Add event callback if provided
    if (eventCallback) {
        lv_obj_add_event_cb(popup, eventCallback, LV_EVENT_CLICKED, userData);
    }

    // Alert message text
    labelText = lv_label_create(popup);
    lv_label_set_text(labelText, "Alert message");
    lv_obj_set_style_text_font(labelText, &lv_font_montserrat_20, 0);
    lv_obj_set_style_text_color(labelText, MedicalTheme::TEXT_PRIMARY, 0);  // White text
    lv_obj_set_style_text_align(labelText, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_set_width(labelText, WIDTH - 20);  // 10px padding on each side
    lv_label_set_long_mode(labelText, LV_LABEL_LONG_WRAP);  // Wrap long text
    lv_obj_center(labelText);

    initialized = true;
    visible = false;
    Serial.println("✅ AlertPopup: Initialized (260×80px, hidden by default)");

    return popup;
}

void AlertPopup::show(const char* message, AlertSeverity severity) {
    if (!initialized || !popup || !labelText) return;

    // Set message
    lv_label_set_text(labelText, message);

    // Set color based on severity (use MedicalTheme status colors)
    lv_color_t color;
    switch (severity) {
        case ALERT_INFO:
            color = MedicalTheme::STATUS_INFO;
            break;
        case ALERT_WARNING:
            color = MedicalTheme::STATUS_WARNING;
            break;
        case ALERT_CRITICAL:
        default:
            color = MedicalTheme::STATUS_CRITICAL;
            break;
    }
    lv_obj_set_style_bg_color(popup, color, 0);
    lv_obj_set_style_bg_opa(popup, LV_OPA_90, 0);  // Make semi-transparent when shown
    lv_obj_set_style_border_opa(popup, LV_OPA_COVER, 0);  // Show border
    lv_obj_set_style_shadow_opa(popup, LV_OPA_50, 0);  // Show shadow

    // Show popup (overlay on top of everything)
    lv_obj_clear_flag(popup, LV_OBJ_FLAG_HIDDEN);
    lv_obj_move_foreground(popup);

    visible = true;
    Serial.printf("📱 AlertPopup: Shown - %s (severity: %d)\n", message, severity);
}

void AlertPopup::hide() {
    if (!initialized || !popup) return;

    lv_obj_add_flag(popup, LV_OBJ_FLAG_HIDDEN);
    lv_obj_set_style_bg_opa(popup, LV_OPA_TRANSP, 0);  // Make completely transparent when hidden
    lv_obj_set_style_border_opa(popup, LV_OPA_TRANSP, 0);  // Hide border
    lv_obj_set_style_shadow_opa(popup, LV_OPA_TRANSP, 0);  // Hide shadow
    visible = false;
    Serial.println("📱 AlertPopup: Hidden");
}

bool AlertPopup::isVisible() const {
    return visible;
}

lv_obj_t* AlertPopup::getContainer() const {
    return popup;
}

lv_obj_t* AlertPopup::getTextLabel() const {
    return labelText;
}

bool AlertPopup::isInitialized() const {
    return initialized;
}
