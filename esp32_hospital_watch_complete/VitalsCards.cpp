/**
 * VitalsCards.cpp
 * Hospital Watch - Vital Signs Cards Component Implementation
 *
 * Author: Claude/Anthropic
 * Date: 2025-11-22
 */

#include "VitalsCards.h"

VitalsCards::VitalsCards() : container(nullptr), hrBox(nullptr), spo2Box(nullptr),
                             bpBox(nullptr), tempBox(nullptr), labelHR(nullptr),
                             labelSpO2(nullptr), labelBP(nullptr), labelTemp(nullptr),
                             initialized(false) {
}

VitalsCards::~VitalsCards() {
    // LVGL objects are automatically cleaned up when parent is deleted
}

lv_obj_t* VitalsCards::create(lv_obj_t* parent, lv_event_cb_t eventCallback, void* userData) {
    if (!parent) {
        Serial.println("❌ VitalsCards: Parent object is null!");
        return nullptr;
    }

    // Create vitals container
    container = lv_obj_create(parent);
    lv_obj_set_size(container, 280, HEIGHT);
    lv_obj_align(container, LV_ALIGN_TOP_MID, 0, Y_POSITION);
    lv_obj_set_style_bg_opa(container, LV_OPA_TRANSP, 0);  // Transparent background
    lv_obj_set_style_border_width(container, 0, 0);
    lv_obj_set_style_pad_all(container, 6, 0);

    // ✅ No scrolling needed - 2×2 grid fits perfectly (disable scrolling to prevent page scroll)
    lv_obj_clear_flag(container, LV_OBJ_FLAG_SCROLLABLE);

    // Calculate positions
    int16_t x1 = 6;   // Left column
    int16_t x2 = 6 + CARD_WIDTH + CARD_SPACING;  // Right column
    int16_t y1 = 8;   // Top row
    int16_t y2 = 8 + CARD_HEIGHT + ROW_SPACING;  // Bottom row

    // Create 4 vital cards
    hrBox = createCard(container, "HR", COLOR_HR, x1, y1, &labelHR, eventCallback, userData);
    spo2Box = createCard(container, "SpO2", COLOR_SPO2, x2, y1, &labelSpO2, eventCallback, userData);
    bpBox = createCard(container, "BP", COLOR_BP, x1, y2, &labelBP, eventCallback, userData);
    tempBox = createCard(container, "Temp", COLOR_TEMP, x2, y2, &labelTemp, eventCallback, userData);

    // Set initial values
    updateHeartRate(0.0);
    updateSpO2(0.0);
    updateBloodPressure(0.0, 0.0);
    updateTemperature(0.0);

    initialized = true;
    Serial.println("✅ VitalsCards: Initialized (2×2 grid, 146px height at Y=70)");

    return container;
}

lv_obj_t* VitalsCards::createCard(lv_obj_t* parent, const char* title, uint32_t borderColor,
                                   int16_t x, int16_t y, lv_obj_t** labelPtr,
                                   lv_event_cb_t eventCallback, void* userData) {
    // Create card container
    lv_obj_t* card = lv_obj_create(parent);
    lv_obj_set_size(card, CARD_WIDTH, CARD_HEIGHT);
    lv_obj_set_pos(card, x, y);
    lv_obj_set_style_bg_color(card, lv_color_hex(0xF0F0F0), 0);  // ✅ Light gray background (was pure white 0xFFFFFF)
    lv_obj_set_style_bg_opa(card, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(card, 3, 0);
    lv_obj_set_style_border_color(card, lv_color_hex(borderColor), 0);
    lv_obj_set_style_radius(card, 8, 0);
    lv_obj_set_style_pad_all(card, 4, 0);
    lv_obj_clear_flag(card, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_add_flag(card, LV_OBJ_FLAG_CLICKABLE);

    // Add event callback if provided
    if (eventCallback) {
        lv_obj_add_event_cb(card, eventCallback, LV_EVENT_CLICKED, userData);
    }

    // Title label
    lv_obj_t* labelTitle = lv_label_create(card);
    lv_label_set_text(labelTitle, title);
    lv_obj_set_style_text_font(labelTitle, &lv_font_montserrat_14, 0);
    lv_obj_set_style_text_color(labelTitle, lv_color_hex(0x000000), 0);  // Black text
    lv_obj_align(labelTitle, LV_ALIGN_TOP_MID, 0, 2);

    // Value label
    lv_obj_t* labelValue = lv_label_create(card);
    lv_label_set_text(labelValue, "---");
    lv_obj_set_style_text_font(labelValue, &lv_font_montserrat_24, 0);
    lv_obj_set_style_text_color(labelValue, lv_color_hex(0x000000), 0);  // Black text
    lv_obj_align(labelValue, LV_ALIGN_BOTTOM_MID, 0, -2);

    // Store value label pointer
    *labelPtr = labelValue;

    return card;
}

void VitalsCards::updateHeartRate(float hr) {
    if (!initialized || !labelHR) return;

    char buf[16];
    snprintf(buf, sizeof(buf), "%.0f", hr);
    lv_label_set_text(labelHR, buf);
}

void VitalsCards::updateSpO2(float spo2) {
    if (!initialized || !labelSpO2) return;

    char buf[16];
    snprintf(buf, sizeof(buf), "%.0f%%", spo2);
    lv_label_set_text(labelSpO2, buf);
}

void VitalsCards::updateBloodPressure(float systolic, float diastolic) {
    if (!initialized || !labelBP) return;

    char buf[16];
    snprintf(buf, sizeof(buf), "%.0f/%.0f", systolic, diastolic);
    lv_label_set_text(labelBP, buf);
}

void VitalsCards::updateTemperature(float temp) {
    if (!initialized || !labelTemp) return;

    char buf[16];
    snprintf(buf, sizeof(buf), "%.1f", temp);
    lv_label_set_text(labelTemp, buf);
}

void VitalsCards::updateAll(float hr, float spo2, float temp, float bpSys, float bpDia) {
    updateHeartRate(hr);
    updateSpO2(spo2);
    updateTemperature(temp);
    updateBloodPressure(bpSys, bpDia);
}

lv_obj_t* VitalsCards::getContainer() const {
    return container;
}

lv_obj_t* VitalsCards::getCard(VitalType type) const {
    switch (type) {
        case VITAL_HEART_RATE:
            return hrBox;
        case VITAL_SPO2:
            return spo2Box;
        case VITAL_BLOOD_PRESSURE:
            return bpBox;
        case VITAL_TEMPERATURE:
            return tempBox;
        default:
            return nullptr;
    }
}

bool VitalsCards::isInitialized() const {
    return initialized;
}
