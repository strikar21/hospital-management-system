/**
 * VitalsCards.cpp
 * Hospital Watch - Vital Signs Cards Component
 * REDESIGNED: Single static 2×2 grid - NO SCROLLING (per reference image)
 *
 * Author: Design Team
 * Date: 2025-11-24
 */

#include "VitalsCards.h"
#include "MedicalTheme.h"

VitalsCards::VitalsCards() :
    container(nullptr), tileview(nullptr), page1(nullptr), page2(nullptr), page3(nullptr),
    pageIndicator(nullptr),
    hrBox(nullptr), bpBox(nullptr), spo2Box(nullptr), tempBox(nullptr),
    rrBox(nullptr), fallRiskBox(nullptr), perfusionBox(nullptr), bioimpBox(nullptr),
    tremorBox(nullptr), stepsBox(nullptr), statusBox(nullptr), modeBox(nullptr),
    labelHR(nullptr), labelBP(nullptr), labelSpO2(nullptr), labelTemp(nullptr),
    labelRR(nullptr), labelFallRisk(nullptr), labelPerfusion(nullptr), labelBioimp(nullptr),
    labelTremor(nullptr), labelSteps(nullptr), labelStatus(nullptr), labelMode(nullptr),
    initialized(false), currentPage(0) {
}

VitalsCards::~VitalsCards() {
    // LVGL objects are automatically cleaned up when parent is deleted
}

lv_obj_t* VitalsCards::create(lv_obj_t* parent, lv_event_cb_t eventCallback, void* userData) {
    if (!parent) {
        Serial.println("❌ VitalsCards: Parent object is null!");
        return nullptr;
    }

    // ✅ FIXED: Single static container (NO scrolling/tileview) - just like reference image
    container = lv_obj_create(parent);
    lv_obj_set_size(container, 280, HEIGHT);
    lv_obj_align(container, LV_ALIGN_TOP_MID, 0, Y_POSITION);
    lv_obj_set_style_bg_opa(container, LV_OPA_TRANSP, 0);  // Transparent - cards float on black
    lv_obj_set_style_border_width(container, 0, 0);
    lv_obj_set_style_pad_all(container, 0, 0);
    lv_obj_clear_flag(container, LV_OBJ_FLAG_SCROLLABLE);  // NO SCROLLING!

    // Calculate card positions (2×2 grid) - centered with small gaps
    int16_t x1 = 5;   // Left column
    int16_t x2 = 5 + CARD_WIDTH + CARD_SPACING;  // Right column
    int16_t y1 = 5;   // Top row
    int16_t y2 = 5 + CARD_HEIGHT + ROW_SPACING;  // Bottom row

    // ✅ ONLY 4 CARDS - PRIMARY VITALS (like reference image)
    // Top-left: HR, Top-right: SpO2, Bottom-left: BP, Bottom-right: Temp
    hrBox = createCard(container, "HR", MedicalTheme::VITAL_HR, x1, y1, &labelHR, eventCallback, userData);
    spo2Box = createCard(container, "SpO\xe2\x82\x82", MedicalTheme::VITAL_SPO2, x2, y1, &labelSpO2, eventCallback, userData);  // SpO₂
    bpBox = createCard(container, "BP", MedicalTheme::VITAL_BP, x1, y2, &labelBP, eventCallback, userData);
    tempBox = createCard(container, "Temp", MedicalTheme::VITAL_TEMP, x2, y2, &labelTemp, eventCallback, userData);

    // Set initial values
    updateHeartRate(0.0);
    updateBloodPressure(0.0, 0.0);
    updateSpO2(0.0);
    updateTemperature(0.0);

    initialized = true;
    Serial.println("✅ VitalsCards: Initialized (SINGLE PAGE, 2×2 grid, NO SCROLLING)");

    return container;
}

lv_obj_t* VitalsCards::createCard(lv_obj_t* parent, const char* title, lv_color_t accentColor,
                                   int16_t x, int16_t y, lv_obj_t** labelPtr,
                                   lv_event_cb_t eventCallback, void* userData) {
    // Create card container - DARK THEME per reference
    lv_obj_t* card = lv_obj_create(parent);
    lv_obj_set_size(card, CARD_WIDTH, CARD_HEIGHT);
    lv_obj_set_pos(card, x, y);

    // ✅ Dark gray background - use theme constant
    lv_obj_set_style_bg_color(card, MedicalTheme::BG_DARK, 0);
    lv_obj_set_style_bg_opa(card, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(card, 8, 0);  // Slight rounding
    lv_obj_set_style_border_width(card, 0, 0);  // No borders
    lv_obj_set_style_pad_all(card, 8, 0);
    lv_obj_clear_flag(card, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_add_flag(card, LV_OBJ_FLAG_CLICKABLE);

    // ✅ LEFT ACCENT BAR (colored vertical line on left edge)
    lv_obj_t* accentBar = lv_obj_create(card);
    lv_obj_set_size(accentBar, 3, CARD_HEIGHT);
    lv_obj_align(accentBar, LV_ALIGN_LEFT_MID, 0, 0);
    lv_obj_set_style_bg_color(accentBar, accentColor, 0);
    lv_obj_set_style_bg_opa(accentBar, LV_OPA_70, 0);
    lv_obj_set_style_radius(accentBar, 0, 0);
    lv_obj_set_style_border_width(accentBar, 0, 0);

    if (eventCallback) {
        lv_obj_add_event_cb(card, eventCallback, LV_EVENT_CLICKED, userData);
    }

    // Title label (medium, gray, top-left) - use theme constant
    lv_obj_t* labelTitle = lv_label_create(card);
    lv_label_set_text(labelTitle, title);
    lv_obj_set_style_text_font(labelTitle, &lv_font_montserrat_16, 0);  // Increased from 12 to 16
    lv_obj_set_style_text_color(labelTitle, MedicalTheme::TEXT_TERTIARY, 0);  // Gray
    lv_obj_align(labelTitle, LV_ALIGN_TOP_LEFT, 10, 3);  // Reduced top padding slightly

    // Value label (Large white numbers at bottom) - 24px for 76px card height
    lv_obj_t* labelValue = lv_label_create(card);
    lv_label_set_text(labelValue, "---");
    lv_obj_set_style_text_font(labelValue, &lv_font_montserrat_24, 0);  // Keep at 24px
    lv_obj_set_style_text_color(labelValue, MedicalTheme::TEXT_PRIMARY, 0);  // White
    lv_obj_align(labelValue, LV_ALIGN_BOTTOM_LEFT, 10, -5);  // Reduced bottom padding

    *labelPtr = labelValue;
    return card;
}

// Empty stubs for page indicator (not used in single-page layout)
lv_obj_t* VitalsCards::createPageIndicator(lv_obj_t* parent) {
    return nullptr;  // Not used
}

void VitalsCards::updatePageIndicator(uint8_t activePage) {
    // Not used in single-page layout
}

void VitalsCards::tileviewScrollCallback(lv_event_t* e) {
    // Not used in single-page layout
}

// ========== UPDATE METHODS ==========

void VitalsCards::updateHeartRate(float hr) {
    if (!initialized || !labelHR) return;

    char buf[24];
    snprintf(buf, sizeof(buf), "%.0f BPM", hr);
    lv_label_set_text(labelHR, buf);

    // Keep white - use theme constant
    lv_obj_set_style_text_color(labelHR, MedicalTheme::TEXT_PRIMARY, 0);
}

void VitalsCards::updateBloodPressure(float systolic, float diastolic) {
    if (!initialized || !labelBP) return;
    char buf[32];
    snprintf(buf, sizeof(buf), "%.0f/%.0f\nmmHg", systolic, diastolic);
    lv_label_set_text(labelBP, buf);

    // Keep white - use theme constant
    lv_obj_set_style_text_color(labelBP, MedicalTheme::TEXT_PRIMARY, 0);
}

void VitalsCards::updateSpO2(float spo2) {
    if (!initialized || !labelSpO2) return;

    char buf[16];
    snprintf(buf, sizeof(buf), "%.0f %%", spo2);
    lv_label_set_text(labelSpO2, buf);

    // Keep white - use theme constant
    lv_obj_set_style_text_color(labelSpO2, MedicalTheme::TEXT_PRIMARY, 0);
}

void VitalsCards::updateTemperature(float temp) {
    if (!initialized || !labelTemp) return;

    char buf[16];
    snprintf(buf, sizeof(buf), "%.1f°C", temp);
    lv_label_set_text(labelTemp, buf);

    // Keep white - use theme constant
    lv_obj_set_style_text_color(labelTemp, MedicalTheme::TEXT_PRIMARY, 0);
}

// Page 2/3 stubs (not displayed in single-page layout)
void VitalsCards::updateRespiratoryRate(float rr) {}
void VitalsCards::updateFallRisk(float risk) {}
void VitalsCards::updatePerfusion(float perfusion) {}
void VitalsCards::updateBioimpedance(float impedance) {}
void VitalsCards::updateTremor(float tremor) {}
void VitalsCards::updateSteps(int steps) {}
void VitalsCards::updateWatchStatus(const char* status) {}
void VitalsCards::updateMode(const char* mode) {}

// ========== BATCH UPDATE METHODS ==========

void VitalsCards::updateAll(float hr, float spo2, float temp, float bpSys, float bpDia) {
    updateHeartRate(hr);
    updateBloodPressure(bpSys, bpDia);
    updateSpO2(spo2);
    updateTemperature(temp);
}

void VitalsCards::updateAllPages(float hr, float spo2, float temp, float bpSys, float bpDia, float rr) {
    updateAll(hr, spo2, temp, bpSys, bpDia);
    // Page 2/3 not used
}

// ========== GETTER/SETTER METHODS ==========

lv_obj_t* VitalsCards::getContainer() const {
    return container;
}

lv_obj_t* VitalsCards::getCard(VitalType type) const {
    switch (type) {
        case VITAL_HEART_RATE: return hrBox;
        case VITAL_BLOOD_PRESSURE: return bpBox;
        case VITAL_SPO2: return spo2Box;
        case VITAL_TEMPERATURE: return tempBox;
        default: return nullptr;
    }
}

uint8_t VitalsCards::getCurrentPage() const {
    return 0;  // Always page 0
}

void VitalsCards::setPage(uint8_t pageIndex) {
    // Not used in single-page layout
}

bool VitalsCards::isInitialized() const {
    return initialized;
}
