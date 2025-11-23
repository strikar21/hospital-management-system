/**
 * VitalsCards.cpp
 * Hospital Watch - Vital Signs Cards Component (Swipeable 3-Page Implementation)
 *
 * Author: Claude/Anthropic
 * Date: 2025-11-23
 */

#include "VitalsCards.h"

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

    // Create main container
    container = lv_obj_create(parent);
    lv_obj_set_size(container, 280, HEIGHT);
    lv_obj_align(container, LV_ALIGN_TOP_MID, 0, Y_POSITION);
    lv_obj_set_style_bg_opa(container, LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_width(container, 0, 0);
    lv_obj_set_style_pad_all(container, 0, 0);
    lv_obj_clear_flag(container, LV_OBJ_FLAG_SCROLLABLE);

    // Create tileview for swipeable pages
    tileview = lv_tileview_create(container);
    lv_obj_set_size(tileview, 280, 146);  // Cards area only
    lv_obj_align(tileview, LV_ALIGN_TOP_MID, 0, 0);
    lv_obj_set_style_bg_opa(tileview, LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_width(tileview, 0, 0);

    // Add scroll event callback for page tracking and cyclic wrapping
    lv_obj_add_event_cb(tileview, tileviewScrollCallback, LV_EVENT_SCROLL, this);
    lv_obj_add_event_cb(tileview, tileviewScrollCallback, LV_EVENT_SCROLL_END, this);

    // ✅ v5.8.2: Create 3 tiles with cyclic navigation (Page 3 → Page 1)
    page1 = lv_tileview_add_tile(tileview, 0, 0, LV_DIR_LEFT | LV_DIR_RIGHT);  // Can swipe both ways (wraps from Page 3)
    page2 = lv_tileview_add_tile(tileview, 1, 0, LV_DIR_LEFT | LV_DIR_RIGHT);  // Can swipe both ways
    page3 = lv_tileview_add_tile(tileview, 2, 0, LV_DIR_LEFT | LV_DIR_RIGHT);  // Can swipe both ways (wraps to Page 1)

    // Calculate card positions (2×2 grid)
    int16_t x1 = 6;   // Left column
    int16_t x2 = 6 + CARD_WIDTH + CARD_SPACING;  // Right column
    int16_t y1 = 8;   // Top row
    int16_t y2 = 8 + CARD_HEIGHT + ROW_SPACING;  // Bottom row

    // ========== PAGE 1: Primary Vitals ==========
    hrBox = createCard(page1, "HR", COLOR_HR, x1, y1, &labelHR, eventCallback, userData);
    bpBox = createCard(page1, "BP", COLOR_BP, x2, y1, &labelBP, eventCallback, userData);
    spo2Box = createCard(page1, "SpO2", COLOR_SPO2, x1, y2, &labelSpO2, eventCallback, userData);
    tempBox = createCard(page1, "Temp", COLOR_TEMP, x2, y2, &labelTemp, eventCallback, userData);

    // ========== PAGE 2: Respiratory & Risk ==========
    rrBox = createCard(page2, "RR", COLOR_RR, x1, y1, &labelRR, eventCallback, userData);
    fallRiskBox = createCard(page2, "Fall", COLOR_FALL, x2, y1, &labelFallRisk, eventCallback, userData);
    perfusionBox = createCard(page2, "Perfusion", COLOR_PERFUSION, x1, y2, &labelPerfusion, eventCallback, userData);
    bioimpBox = createCard(page2, "Bioimp", COLOR_BIOIMP, x2, y2, &labelBioimp, eventCallback, userData);

    // ========== PAGE 3: Activity & Status ==========
    tremorBox = createCard(page3, "Tremor", COLOR_TREMOR, x1, y1, &labelTremor, eventCallback, userData);
    stepsBox = createCard(page3, "Steps", COLOR_STEPS, x2, y1, &labelSteps, eventCallback, userData);
    statusBox = createCard(page3, "Status", COLOR_STATUS, x1, y2, &labelStatus, eventCallback, userData);
    modeBox = createCard(page3, "Mode", COLOR_MODE, x2, y2, &labelMode, eventCallback, userData);

    // Create page indicators
    pageIndicator = createPageIndicator(container);

    // Set initial values
    updateHeartRate(0.0);
    updateBloodPressure(0.0, 0.0);
    updateSpO2(0.0);
    updateTemperature(0.0);
    updateRespiratoryRate(0.0);
    updateFallRisk(0.0);
    updatePerfusion(0.0);
    updateBioimpedance(0.0);
    updateTremor(0.0);
    updateSteps(0);
    updateWatchStatus("--");
    updateMode("--");

    initialized = true;
    Serial.println("✅ VitalsCards: Initialized (3 pages, 2×2 grid, swipeable)");

    return container;
}

lv_obj_t* VitalsCards::createCard(lv_obj_t* parent, const char* title, uint32_t borderColor,
                                   int16_t x, int16_t y, lv_obj_t** labelPtr,
                                   lv_event_cb_t eventCallback, void* userData) {
    // Create card container
    lv_obj_t* card = lv_obj_create(parent);
    lv_obj_set_size(card, CARD_WIDTH, CARD_HEIGHT);
    lv_obj_set_pos(card, x, y);
    lv_obj_set_style_bg_color(card, lv_color_hex(0xF0F0F0), 0);
    lv_obj_set_style_bg_opa(card, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(card, 3, 0);
    lv_obj_set_style_border_color(card, lv_color_hex(borderColor), 0);
    lv_obj_set_style_radius(card, 8, 0);
    lv_obj_set_style_pad_all(card, 4, 0);
    lv_obj_clear_flag(card, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_add_flag(card, LV_OBJ_FLAG_CLICKABLE);

    if (eventCallback) {
        lv_obj_add_event_cb(card, eventCallback, LV_EVENT_CLICKED, userData);
    }

    // Title label
    lv_obj_t* labelTitle = lv_label_create(card);
    lv_label_set_text(labelTitle, title);
    lv_obj_set_style_text_font(labelTitle, &lv_font_montserrat_14, 0);
    lv_obj_set_style_text_color(labelTitle, lv_color_hex(0x000000), 0);
    lv_obj_align(labelTitle, LV_ALIGN_TOP_MID, 0, 2);

    // Value label
    lv_obj_t* labelValue = lv_label_create(card);
    lv_label_set_text(labelValue, "---");
    lv_obj_set_style_text_font(labelValue, &lv_font_montserrat_24, 0);
    lv_obj_set_style_text_color(labelValue, lv_color_hex(0x000000), 0);
    lv_obj_align(labelValue, LV_ALIGN_BOTTOM_MID, 0, -2);

    *labelPtr = labelValue;
    return card;
}

lv_obj_t* VitalsCards::createPageIndicator(lv_obj_t* parent) {
    // Create indicator container at bottom
    lv_obj_t* indicator = lv_obj_create(parent);
    lv_obj_set_size(indicator, 60, 12);
    lv_obj_align(indicator, LV_ALIGN_BOTTOM_MID, 0, -2);
    lv_obj_set_style_bg_opa(indicator, LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_width(indicator, 0, 0);
    lv_obj_set_style_pad_all(indicator, 0, 0);
    lv_obj_clear_flag(indicator, LV_OBJ_FLAG_SCROLLABLE);

    // Create 3 dot indicators
    for (int i = 0; i < 3; i++) {
        lv_obj_t* dot = lv_obj_create(indicator);
        lv_obj_set_size(dot, 8, 8);
        lv_obj_set_pos(dot, i * 16 + 10, 2);
        lv_obj_set_style_radius(dot, LV_RADIUS_CIRCLE, 0);
        lv_obj_set_style_border_width(dot, 0, 0);
        lv_obj_set_style_bg_color(dot, lv_color_hex(i == 0 ? 0xFFFFFF : 0x808080), 0);  // First dot active
        lv_obj_set_style_bg_opa(dot, LV_OPA_COVER, 0);
        lv_obj_clear_flag(dot, LV_OBJ_FLAG_SCROLLABLE);
    }

    return indicator;
}

void VitalsCards::updatePageIndicator(uint8_t activePage) {
    if (!pageIndicator) return;

    // Update dot colors
    uint32_t activeChild = 0;
    lv_obj_t* child = lv_obj_get_child(pageIndicator, activeChild);
    while (child != NULL) {
        uint32_t color = (activeChild == activePage) ? 0xFFFFFF : 0x808080;  // White active, gray inactive
        lv_obj_set_style_bg_color(child, lv_color_hex(color), 0);
        activeChild++;
        child = lv_obj_get_child(pageIndicator, activeChild);
    }
}

// ✅ v5.8.2: Handle tileview scroll with cyclic wrapping (Page 3 → Page 1, Page 1 → Page 3)
void VitalsCards::tileviewScrollCallback(lv_event_t* e) {
    VitalsCards* vitalsCards = (VitalsCards*)lv_event_get_user_data(e);
    if (!vitalsCards || !vitalsCards->tileview) return;

    lv_obj_t* tv = lv_event_get_target(e);
    lv_event_code_t code = lv_event_get_code(e);

    if (code == LV_EVENT_SCROLL) {
        // ✅ During scroll, detect edge cases and wrap
        lv_point_t scroll_offset;
        lv_obj_get_scroll_end(tv, &scroll_offset);

        // Get scroll position
        lv_coord_t x = lv_obj_get_scroll_x(tv);
        lv_coord_t max_scroll = 280 * 2;  // 280px per page × 2 pages to the right

        // Wrap from Page 3 to Page 1 (swipe right on page 3)
        if (x >= max_scroll + 50) {  // Threshold: 50px past last page
            lv_obj_scroll_to_x(tv, 0, LV_ANIM_OFF);  // Jump to Page 1
            vitalsCards->currentPage = 0;
            vitalsCards->updatePageIndicator(0);
        }
        // Wrap from Page 1 to Page 3 (swipe left on page 1)
        else if (x <= -50) {  // Threshold: 50px before first page
            lv_obj_scroll_to_x(tv, max_scroll, LV_ANIM_OFF);  // Jump to Page 3
            vitalsCards->currentPage = 2;
            vitalsCards->updatePageIndicator(2);
        }
    }
    else if (code == LV_EVENT_SCROLL_END) {
        // Update page indicator after scroll ends
        lv_obj_t* tile = lv_tileview_get_tile_act(tv);

        if (tile == vitalsCards->page1) {
            vitalsCards->currentPage = 0;
        } else if (tile == vitalsCards->page2) {
            vitalsCards->currentPage = 1;
        } else if (tile == vitalsCards->page3) {
            vitalsCards->currentPage = 2;
        }

        vitalsCards->updatePageIndicator(vitalsCards->currentPage);
    }
}

// ========== UPDATE METHODS - PAGE 1 ==========

void VitalsCards::updateHeartRate(float hr) {
    if (!initialized || !labelHR) return;
    char buf[16];
    snprintf(buf, sizeof(buf), "%.0f", hr);
    lv_label_set_text(labelHR, buf);
}

void VitalsCards::updateBloodPressure(float systolic, float diastolic) {
    if (!initialized || !labelBP) return;
    char buf[16];
    snprintf(buf, sizeof(buf), "%.0f/%.0f", systolic, diastolic);
    lv_label_set_text(labelBP, buf);
}

void VitalsCards::updateSpO2(float spo2) {
    if (!initialized || !labelSpO2) return;
    char buf[16];
    snprintf(buf, sizeof(buf), "%.0f%%", spo2);
    lv_label_set_text(labelSpO2, buf);
}

void VitalsCards::updateTemperature(float temp) {
    if (!initialized || !labelTemp) return;
    char buf[16];
    snprintf(buf, sizeof(buf), "%.1f", temp);
    lv_label_set_text(labelTemp, buf);
}

// ========== UPDATE METHODS - PAGE 2 ==========

void VitalsCards::updateRespiratoryRate(float rr) {
    if (!initialized || !labelRR) return;
    char buf[16];
    snprintf(buf, sizeof(buf), "%.0f", rr);
    lv_label_set_text(labelRR, buf);
}

void VitalsCards::updateFallRisk(float risk) {
    if (!initialized || !labelFallRisk) return;
    char buf[16];
    snprintf(buf, sizeof(buf), "%.0f/10", risk);
    lv_label_set_text(labelFallRisk, buf);
}

void VitalsCards::updatePerfusion(float perfusion) {
    if (!initialized || !labelPerfusion) return;
    char buf[16];
    snprintf(buf, sizeof(buf), "%.0f%%", perfusion);
    lv_label_set_text(labelPerfusion, buf);
}

void VitalsCards::updateBioimpedance(float impedance) {
    if (!initialized || !labelBioimp) return;
    char buf[16];
    snprintf(buf, sizeof(buf), "%.0f", impedance);
    lv_label_set_text(labelBioimp, buf);
}

// ========== UPDATE METHODS - PAGE 3 ==========

void VitalsCards::updateTremor(float tremor) {
    if (!initialized || !labelTremor) return;
    char buf[16];
    if (tremor >= 4.0 && tremor <= 12.0) {
        // Active tremor detected in Parkinson's range
        snprintf(buf, sizeof(buf), "%.1fHz", tremor);
    } else if (tremor > 0.1) {
        // Some movement but outside Parkinson's range
        snprintf(buf, sizeof(buf), "%.1fHz", tremor);
    } else {
        // No tremor
        snprintf(buf, sizeof(buf), "None");
    }
    lv_label_set_text(labelTremor, buf);
}

void VitalsCards::updateSteps(int steps) {
    if (!initialized || !labelSteps) return;
    char buf[16];
    snprintf(buf, sizeof(buf), "%d", steps);
    lv_label_set_text(labelSteps, buf);
}

void VitalsCards::updateWatchStatus(const char* status) {
    if (!initialized || !labelStatus) return;
    lv_label_set_text(labelStatus, status);
}

void VitalsCards::updateMode(const char* mode) {
    if (!initialized || !labelMode) return;
    lv_label_set_text(labelMode, mode);
}

// ========== BATCH UPDATE METHODS ==========

void VitalsCards::updateAll(float hr, float spo2, float temp, float bpSys, float bpDia) {
    updateHeartRate(hr);
    updateBloodPressure(bpSys, bpDia);
    updateSpO2(spo2);
    updateTemperature(temp);
}

void VitalsCards::updateAllPages(float hr, float spo2, float temp, float bpSys, float bpDia, float rr) {
    // Page 1
    updateHeartRate(hr);
    updateBloodPressure(bpSys, bpDia);
    updateSpO2(spo2);
    updateTemperature(temp);
    // Page 2
    updateRespiratoryRate(rr);
    // Note: Fall risk, perfusion, bioimpedance updated separately
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
        case VITAL_RESPIRATORY_RATE: return rrBox;
        case VITAL_FALL_RISK: return fallRiskBox;
        case VITAL_PERFUSION: return perfusionBox;
        case VITAL_BIOIMPEDANCE: return bioimpBox;
        case VITAL_TREMOR: return tremorBox;
        case VITAL_STEPS: return stepsBox;
        case VITAL_WATCH_STATUS: return statusBox;
        case VITAL_MODE: return modeBox;
        default: return nullptr;
    }
}

uint8_t VitalsCards::getCurrentPage() const {
    return currentPage;
}

void VitalsCards::setPage(uint8_t pageIndex) {
    if (!tileview || pageIndex > 2) return;
    lv_obj_set_tile_id(tileview, pageIndex, 0, LV_ANIM_ON);
    currentPage = pageIndex;
    updatePageIndicator(currentPage);
}

bool VitalsCards::isInitialized() const {
    return initialized;
}
