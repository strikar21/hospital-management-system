#include "UIScreens.h"
#include "DisplayManager.h"

// ✅ v5.4: Removed duplicate 'ui' definition (already defined in .ino file)
static const uint16_t W = 280;
static const uint16_t H = 456;

UIScreens::UIScreens() {}
UIScreens::~UIScreens() {}

// ✅ v5.4.7: Apply text anti-aliasing and rendering improvements globally
void UIScreens::applyTextSmoothing(lv_obj_t *obj) {
    if (!obj) return;

    // Apply text rendering improvements for smoother display
    lv_obj_set_style_text_opa(obj, LV_OPA_COVER, 0);  // Full opacity for crisp text

    // ✅ Enable text font anti-aliasing (4bpp subpixel rendering)
    // Note: Requires fonts compiled with 4bpp format (Montserrat fonts are 4bpp by default)
    lv_obj_set_style_text_letter_space(obj, 0, 0);  // No extra letter spacing
    lv_obj_set_style_text_line_space(obj, 0, 0);    // No extra line spacing

    // Recursively apply to all children
    uint32_t childCount = lv_obj_get_child_cnt(obj);
    for (uint32_t i = 0; i < childCount; i++) {
        lv_obj_t *child = lv_obj_get_child(obj, i);
        if (child) {
            applyTextSmoothing(child);
        }
    }
}

void UIScreens::init() {
    if (initialized) return;

    createHomeScreen();
    createWaveformScreen();
    createAlertsScreen();
    createSettingsScreen();

    // ✅ v5.4.4: Apply text smoothing to all screens
    applyTextSmoothing(homeScreen);
    applyTextSmoothing(waveformScreen);
    applyTextSmoothing(alertsScreen);
    applyTextSmoothing(settingsScreen);

    showHomeScreen();
    initialized = true;
}

bool UIScreens::isInitialized() const { return initialized; }

void UIScreens::loadScreen(lv_obj_t *scr) { if (scr) lv_scr_load(scr); }
void UIScreens::showHomeScreen()     { loadScreen(homeScreen);     currentScreen = SCREEN_HOME; }
void UIScreens::showWaveformScreen() { loadScreen(waveformScreen); currentScreen = SCREEN_WAVEFORM; }
void UIScreens::showAlertsScreen()   { loadScreen(alertsScreen);   currentScreen = SCREEN_ALERTS; }
void UIScreens::showSettingsScreen() { loadScreen(settingsScreen); currentScreen = SCREEN_SETTINGS; }

void UIScreens::showNextScreen()     { int n = (currentScreen + 1) % SCREEN_COUNT; (n==0)?showHomeScreen():(n==1)?showWaveformScreen():(n==2)?showAlertsScreen():showSettingsScreen(); }
void UIScreens::showPreviousScreen(){ int n = (currentScreen - 1 + SCREEN_COUNT) % SCREEN_COUNT; (n==0)?showHomeScreen():(n==1)?showWaveformScreen():(n==2)?showAlertsScreen():showSettingsScreen(); }

void UIScreens::updateTime(const char* t) {
    statusBar.updateTime(t);
}

void UIScreens::updateBattery(uint8_t p) {
    statusBar.updateBattery(p);
}

void UIScreens::updateConnectionStatus(bool wifi, bool, bool) {
    statusBar.updateWiFi(wifi);
}

void UIScreens::updateVitals(float hr, float spo2, float temp, float bpSys, float bpDia, float rr) {
    // Update Page 1 vitals (HR, BP, SpO2, Temp)
    vitalsCards.updateAll(hr, spo2, temp, bpSys, bpDia);

    // Update Page 2 vitals (Respiratory Rate)
    vitalsCards.updateRespiratoryRate(rr);
}

void UIScreens::updateVitalIMU(float fallRisk, float tremor) {
    // Update Page 2 vitals (Fall Risk, Tremor)
    vitalsCards.updateFallRisk(fallRisk);
    vitalsCards.updateTremor(tremor);
}

// ✅ v5.4.2: Show alert in alert bar with severity-based color
void UIScreens::showCriticalAlert(const char* msg) {
    showCriticalAlert(msg, ALERT_CRITICAL);  // Default to critical (red)
}

// ✅ v5.4.6: Show alert using AlertPopup component
void UIScreens::showCriticalAlert(const char* msg, AlertSeverity severity) {
    alertPopup.show(msg, severity);
}

// ✅ v5.4.6: Hide alert using AlertPopup component
void UIScreens::hideCriticalAlert() {
    alertPopup.hide();
}

// ✅ v5.4.6: Update alert count (no longer shows popup - alerts only visible in alerts screen)
void UIScreens::updateAlertCount(uint8_t c) {
    alertCount = c;
    // Alert count is just tracked internally - no UI change on status bar
    // Users can see alerts by navigating to the alerts screen
    Serial.printf("📱 Alert count updated: %d\n", c);
}

// ✅ v5.4.6: Update patient ID using PatientBar component
void UIScreens::updatePatientId(const char* patientId) {
    patientBar.updatePatientId(patientId);
}

void UIScreens::updateDeviceId(const char* deviceId) {
    patientBar.updateDeviceId(deviceId);
}

// ✅ v5.4.6: HOME SCREEN - Modularized with component classes
// Layout: Status(35) + Patient(35) + Vitals(146) + ECG(240) = 456px
void UIScreens::createHomeScreen() {
    homeScreen = lv_obj_create(NULL);
    lv_obj_set_style_bg_color(homeScreen, lv_color_hex(0x000000), 0);
    lv_obj_set_style_bg_opa(homeScreen, LV_OPA_COVER, 0);
    lv_obj_clear_flag(homeScreen, LV_OBJ_FLAG_SCROLLABLE);  // Disable page scrolling

    // Create modular components
    statusBar.create(homeScreen);
    patientBar.create(homeScreen);
    vitalsCards.create(homeScreen, event_callback, this);
    ecgChart.create(homeScreen, event_callback, this);
    alertPopup.create(event_callback, this);

    Serial.println("✅ Home screen created with modular components");
}

// ✅ v5.4.6: Update home screen ECG chart using ECGChart component
void UIScreens::updateHomeECG(int32_t *samples, uint8_t numSamples) {
    ecgChart.updateSamples(samples, numSamples);
}

// ✅ v5.4: WAVEFORM SCREEN - Improved design with larger fonts
void UIScreens::createWaveformScreen() {
    waveformScreen = lv_obj_create(NULL);
    lv_obj_set_style_bg_color(waveformScreen, lv_color_hex(0x000000), 0);
    lv_obj_set_style_bg_opa(waveformScreen, LV_OPA_COVER, 0);

    lv_obj_t *title = lv_label_create(waveformScreen);
    lv_label_set_text(title, "ECG WAVEFORM");
    lv_obj_set_style_text_font(title, &lv_font_montserrat_28, 0);
    lv_obj_set_style_text_color(title, lv_color_hex(0xFFFFFF), 0);
    lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 20);

    labelWaveformMode = lv_label_create(waveformScreen);
    lv_label_set_text(labelWaveformMode, "Lead II");
    lv_obj_set_style_text_font(labelWaveformMode, &lv_font_montserrat_20, 0);
    lv_obj_set_style_text_color(labelWaveformMode, lv_color_hex(0xFFFFFF), 0);  // ✅ White text on black bg
    lv_obj_align(labelWaveformMode, LV_ALIGN_TOP_MID, 0, 55);

    chartWaveform = lv_chart_create(waveformScreen);
    lv_obj_set_size(chartWaveform, W-20, 300);
    lv_obj_center(chartWaveform);
    lv_chart_set_type(chartWaveform, LV_CHART_TYPE_LINE);
    lv_chart_set_range(chartWaveform, LV_CHART_AXIS_PRIMARY_Y, 0, 100);
    lv_chart_set_point_count(chartWaveform, 200);
    lv_obj_set_style_line_width(chartWaveform, 2, LV_PART_ITEMS);  // ✅ v5.4.9: 2px width for sharp green waveform
    lv_obj_set_style_size(chartWaveform, 0, LV_PART_INDICATOR);  // No point markers
    lv_obj_set_style_bg_color(chartWaveform, lv_color_hex(0x000000), 0);  // Pure black background
    lv_obj_set_style_line_rounded(chartWaveform, true, LV_PART_ITEMS);  // Smooth lines

    // ✅ Medical ECG grid - 5mm × 5mm squares (standard medical paper grid)
    // Chart: 260px wide, 300px tall
    // Standard: 5mm = 50px (at typical display DPI)
    // Horizontal: 260px ÷ 50px = 5.2 squares (~5 divisions)
    // Vertical: 300px ÷ 50px = 6 squares (6 divisions)
    lv_chart_set_div_line_count(chartWaveform, 5, 5);  // 5 horizontal lines, 5 vertical lines (creates 5×6 grid)
    lv_obj_set_style_line_color(chartWaveform, lv_color_hex(0x1A3A1A), LV_PART_MAIN);  // Dark green grid
    lv_obj_set_style_line_width(chartWaveform, 1, LV_PART_MAIN);  // Thin grid lines
    lv_obj_set_style_line_opa(chartWaveform, LV_OPA_50, LV_PART_MAIN);  // Semi-transparent

    // Hide axis ticks/labels for clean waveform display
    lv_obj_set_style_pad_all(chartWaveform, 0, LV_PART_MAIN);
    lv_obj_set_style_line_width(chartWaveform, 0, LV_PART_TICKS);
    lv_obj_set_style_text_opa(chartWaveform, LV_OPA_TRANSP, LV_PART_TICKS);

    seriesWaveform = lv_chart_add_series(chartWaveform, lv_color_hex(0x00FF00), LV_CHART_AXIS_PRIMARY_Y);

    // Initialize with baseline (value 30 = 70% from top, medical ECG standard)
    for (int i = 0; i < 200; i++) {
        lv_chart_set_next_value(chartWaveform, seriesWaveform, 30);
    }

    labelWaveformStatus = lv_label_create(waveformScreen);
    lv_label_set_text(labelWaveformStatus, "LIVE");
    lv_obj_set_style_text_font(labelWaveformStatus, &lv_font_montserrat_24, 0);
    lv_obj_set_style_text_color(labelWaveformStatus, lv_color_hex(0xFFFFFF), 0);  // ✅ White text on black bg
    lv_obj_align(labelWaveformStatus, LV_ALIGN_BOTTOM_MID, 0, -15);

    lv_obj_t *hint = lv_label_create(waveformScreen);
    lv_label_set_text(hint, "Tap to freeze/unfreeze");
    lv_obj_set_style_text_font(hint, &lv_font_montserrat_16, 0);
    lv_obj_set_style_text_color(hint, lv_color_hex(0xFFFFFF), 0);  // ✅ White text on black bg
    lv_obj_align(hint, LV_ALIGN_BOTTOM_MID, 0, -45);

    lv_obj_add_event_cb(chartWaveform, event_callback, LV_EVENT_PRESSING, this);
}

// ✅ v5.4.6: ALERTS SCREEN - Fixed styling for LVGL v9
void UIScreens::createAlertsScreen() {
    alertsScreen = lv_obj_create(NULL);
    lv_obj_set_style_bg_color(alertsScreen, lv_color_hex(0x000000), 0);
    lv_obj_set_style_bg_opa(alertsScreen, LV_OPA_COVER, 0);

    lv_obj_t *title = lv_label_create(alertsScreen);
    lv_label_set_text(title, "ACTIVE ALERTS");
    lv_obj_set_style_text_font(title, &lv_font_montserrat_28, 0);
    lv_obj_set_style_text_color(title, lv_color_hex(0xFFFFFF), 0);
    lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 20);

    // Create alerts list container (instead of lv_list which has default pink styling)
    alertsList = lv_obj_create(alertsScreen);
    lv_obj_set_size(alertsList, W-30, H-160);
    lv_obj_align(alertsList, LV_ALIGN_TOP_MID, 0, 65);
    lv_obj_set_style_bg_color(alertsList, lv_color_hex(0x1A1A1A), 0);
    lv_obj_set_style_bg_opa(alertsList, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(alertsList, 2, 0);
    lv_obj_set_style_border_color(alertsList, lv_color_hex(0x3A3A3A), 0);
    lv_obj_set_style_radius(alertsList, 8, 0);
    lv_obj_set_style_pad_all(alertsList, 10, 0);
    lv_obj_set_flex_flow(alertsList, LV_FLEX_FLOW_COLUMN);  // Stack alerts vertically
    lv_obj_set_flex_align(alertsList, LV_FLEX_ALIGN_START, LV_FLEX_ALIGN_START, LV_FLEX_ALIGN_START);
    lv_obj_set_scroll_dir(alertsList, LV_DIR_VER);  // Vertical scrolling

    // "No alerts" placeholder label
    lv_obj_t *noAlertsLabel = lv_label_create(alertsList);
    lv_label_set_text(noAlertsLabel, "No active alerts");
    lv_obj_set_style_text_font(noAlertsLabel, &lv_font_montserrat_22, 0);  // ✅ Increased from 20 to 22 for better readability
    lv_obj_set_style_text_color(noAlertsLabel, lv_color_hex(0xFFFFFF), 0);  // ✅ White text on dark bg
    lv_obj_set_style_text_opa(noAlertsLabel, LV_OPA_COVER, 0);  // ✅ Ensure full opacity for crisp rendering
    lv_obj_center(noAlertsLabel);

    // Clear all button
    buttonClearAlerts = lv_btn_create(alertsScreen);
    lv_obj_set_size(buttonClearAlerts, 200, 55);
    lv_obj_align(buttonClearAlerts, LV_ALIGN_BOTTOM_MID, 0, -20);
    lv_obj_set_style_bg_color(buttonClearAlerts, lv_color_hex(0xE74C3C), 0);
    lv_obj_set_style_bg_opa(buttonClearAlerts, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(buttonClearAlerts, 0, 0);
    lv_obj_set_style_radius(buttonClearAlerts, 8, 0);

    lv_obj_t *btnLabel = lv_label_create(buttonClearAlerts);
    lv_label_set_text(btnLabel, "Clear All");
    lv_obj_set_style_text_font(btnLabel, &lv_font_montserrat_22, 0);
    lv_obj_set_style_text_color(btnLabel, lv_color_hex(0xFFFFFF), 0);
    lv_obj_center(btnLabel);
    lv_obj_add_event_cb(buttonClearAlerts, event_callback, LV_EVENT_CLICKED, this);
}

// ✅ v5.4: SETTINGS SCREEN - Improved design with larger fonts
void UIScreens::createSettingsScreen() {
    settingsScreen = lv_obj_create(NULL);
    lv_obj_set_style_bg_color(settingsScreen, lv_color_hex(0x000000), 0);
    lv_obj_set_style_bg_opa(settingsScreen, LV_OPA_COVER, 0);

    lv_obj_t *title = lv_label_create(settingsScreen);
    lv_label_set_text(title, "SETTINGS");
    lv_obj_set_style_text_font(title, &lv_font_montserrat_28, 0);
    lv_obj_set_style_text_color(title, lv_color_hex(0xFFFFFF), 0);
    lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 30);

    lv_obj_t *brightLabel = lv_label_create(settingsScreen);
    lv_label_set_text(brightLabel, "Display Brightness");
    lv_obj_set_style_text_font(brightLabel, &lv_font_montserrat_24, 0);  // ✅ Increased from 22 to 24 for better readability
    lv_obj_set_style_text_color(brightLabel, lv_color_hex(0xFFFFFF), 0);  // ✅ White text on black bg
    lv_obj_set_style_text_opa(brightLabel, LV_OPA_COVER, 0);  // ✅ Ensure full opacity for crisp rendering
    lv_obj_align(brightLabel, LV_ALIGN_TOP_MID, 0, 100);

    sliderBrightness = lv_slider_create(settingsScreen);
    lv_slider_set_range(sliderBrightness, 0, 100);
    lv_slider_set_value(sliderBrightness, 100, LV_ANIM_OFF);
    lv_obj_set_size(sliderBrightness, 240, 25);
    lv_obj_align(sliderBrightness, LV_ALIGN_TOP_MID, 0, 145);
    lv_obj_set_style_bg_color(sliderBrightness, lv_color_hex(0x2C3E50), LV_PART_MAIN);
    lv_obj_set_style_bg_color(sliderBrightness, lv_color_hex(0x3498DB), LV_PART_INDICATOR);
    lv_obj_set_style_bg_color(sliderBrightness, lv_color_hex(0xFFFFFF), LV_PART_KNOB);
    lv_obj_add_event_cb(sliderBrightness, event_callback, LV_EVENT_VALUE_CHANGED, this);

    labelBrightnessValue = lv_label_create(settingsScreen);
    lv_label_set_text(labelBrightnessValue, "100%");
    lv_obj_set_style_text_font(labelBrightnessValue, &lv_font_montserrat_38, 0);
    lv_obj_set_style_text_color(labelBrightnessValue, lv_color_hex(0xFFFFFF), 0);  // ✅ White text on black bg
    lv_obj_align(labelBrightnessValue, LV_ALIGN_TOP_MID, 0, 190);

    // ✅ v5.6.0: Screen Timeout Slider
    lv_obj_t *timeoutLabel = lv_label_create(settingsScreen);
    lv_label_set_text(timeoutLabel, "Screen Timeout");
    lv_obj_set_style_text_font(timeoutLabel, &lv_font_montserrat_24, 0);
    lv_obj_set_style_text_color(timeoutLabel, lv_color_hex(0xFFFFFF), 0);
    lv_obj_set_style_text_opa(timeoutLabel, LV_OPA_COVER, 0);
    lv_obj_align(timeoutLabel, LV_ALIGN_TOP_MID, 0, 250);

    sliderTimeout = lv_slider_create(settingsScreen);
    lv_slider_set_range(sliderTimeout, 0, 60);  // 0-60 seconds (0 = never)
    lv_slider_set_value(sliderTimeout, 15, LV_ANIM_OFF);  // Default 15s
    lv_obj_set_size(sliderTimeout, 240, 25);
    lv_obj_align(sliderTimeout, LV_ALIGN_TOP_MID, 0, 295);
    lv_obj_set_style_bg_color(sliderTimeout, lv_color_hex(0x2C3E50), LV_PART_MAIN);
    lv_obj_set_style_bg_color(sliderTimeout, lv_color_hex(0x3498DB), LV_PART_INDICATOR);
    lv_obj_set_style_bg_color(sliderTimeout, lv_color_hex(0xFFFFFF), LV_PART_KNOB);
    lv_obj_add_event_cb(sliderTimeout, event_callback, LV_EVENT_VALUE_CHANGED, this);

    labelTimeoutValue = lv_label_create(settingsScreen);
    lv_label_set_text(labelTimeoutValue, "15s");
    lv_obj_set_style_text_font(labelTimeoutValue, &lv_font_montserrat_28, 0);
    lv_obj_set_style_text_color(labelTimeoutValue, lv_color_hex(0xFFFFFF), 0);
    lv_obj_align(labelTimeoutValue, LV_ALIGN_TOP_MID, 0, 335);

    // ✅ v5.6.0: Tap to Wake Toggle
    lv_obj_t *tapWakeLabel = lv_label_create(settingsScreen);
    lv_label_set_text(tapWakeLabel, "Tap to Wake");
    lv_obj_set_style_text_font(tapWakeLabel, &lv_font_montserrat_24, 0);
    lv_obj_set_style_text_color(tapWakeLabel, lv_color_hex(0xFFFFFF), 0);
    lv_obj_set_style_text_opa(tapWakeLabel, LV_OPA_COVER, 0);
    lv_obj_align(tapWakeLabel, LV_ALIGN_BOTTOM_MID, -50, -70);

    switchTapWake = lv_switch_create(settingsScreen);
    lv_obj_align(switchTapWake, LV_ALIGN_BOTTOM_MID, 60, -70);
    lv_obj_set_size(switchTapWake, 60, 30);
    lv_obj_add_state(switchTapWake, LV_STATE_CHECKED);  // Default ON
    lv_obj_add_event_cb(switchTapWake, event_callback, LV_EVENT_VALUE_CHANGED, this);

    lv_obj_t *hint = lv_label_create(settingsScreen);
    lv_label_set_text(hint, "Swipe left/right to switch screens");
    lv_obj_set_style_text_font(hint, &lv_font_montserrat_16, 0);
    lv_obj_set_style_text_color(hint, lv_color_hex(0xFFFFFF), 0);  // ✅ White text on black bg
    lv_obj_align(hint, LV_ALIGN_BOTTOM_MID, 0, -30);
}

void UIScreens::event_callback(lv_event_t *e) {
    lv_event_code_t code = lv_event_get_code(e);
    UIScreens *ui = (UIScreens*)lv_event_get_user_data(e);
    lv_obj_t *target = lv_event_get_target(e);

    // ✅ v5.4: Brightness slider
    if (code == LV_EVENT_VALUE_CHANGED && target == ui->sliderBrightness) {
        int v = lv_slider_get_value(ui->sliderBrightness);
        char b[8]; snprintf(b, sizeof(b), "%d%%", v);
        lv_label_set_text(ui->labelBrightnessValue, b);
        extern void setDisplayBrightness(uint8_t);
        setDisplayBrightness(v);
    }

    // ✅ v5.6.0: Screen timeout slider
    if (code == LV_EVENT_VALUE_CHANGED && target == ui->sliderTimeout) {
        int v = lv_slider_get_value(ui->sliderTimeout);
        char b[16];
        if (v == 0) {
            snprintf(b, sizeof(b), "Never");
        } else {
            snprintf(b, sizeof(b), "%ds", v);
        }
        lv_label_set_text(ui->labelTimeoutValue, b);
        extern void setScreenTimeout(uint8_t);
        setScreenTimeout(v);
    }

    // ✅ v5.6.0: Tap to wake toggle
    if (code == LV_EVENT_VALUE_CHANGED && target == ui->switchTapWake) {
        bool enabled = lv_obj_has_state(ui->switchTapWake, LV_STATE_CHECKED);
        extern void setTapToWake(bool);
        setTapToWake(enabled);
        Serial.printf("🔧 Tap to wake: %s\n", enabled ? "ON" : "OFF");
    }

    // ✅ v5.4: Clear alerts button
    if (code == LV_EVENT_CLICKED && target == ui->buttonClearAlerts) {
        ui->clearAllAlerts();
    }

    // ✅ v5.4: Waveform freeze/unfreeze
    if (code == LV_EVENT_PRESSING && target == ui->chartWaveform) {
        ui->setWaveformFrozen(!ui->isWaveformFrozen());
        lv_label_set_text(ui->labelWaveformStatus, ui->isWaveformFrozen() ? "FROZEN" : "LIVE");
        // ✅ Keep text white on black background (no color changes)
    }

    // ✅ v5.4.6: Clickable component navigation
    if (code == LV_EVENT_CLICKED) {
        lv_obj_t* ecgContainer = ui->ecgChart.getContainer();
        lv_obj_t* hrCard = ui->vitalsCards.getCard(VITAL_HEART_RATE);
        lv_obj_t* spo2Card = ui->vitalsCards.getCard(VITAL_SPO2);
        lv_obj_t* bpCard = ui->vitalsCards.getCard(VITAL_BLOOD_PRESSURE);
        lv_obj_t* tempCard = ui->vitalsCards.getCard(VITAL_TEMPERATURE);
        lv_obj_t* statusContainer = ui->statusBar.getContainer();
        lv_obj_t* popupContainer = ui->alertPopup.getContainer();

        if (target == ecgContainer || target == hrCard) {
            Serial.println("👆 ECG/HR card clicked - showing ECG waveform");
            ui->showWaveformScreen();
            // TODO: Set waveform mode to "ECG Lead II"
        }
        else if (target == spo2Card) {
            Serial.println("👆 SpO2 card clicked - showing SpO2 waveform");
            ui->showWaveformScreen();
            // TODO: Set waveform mode to "SpO2 PPG"
        }
        else if (target == bpCard) {
            Serial.println("👆 BP card clicked - showing BP trend");
            ui->showWaveformScreen();
            // TODO: Set waveform mode to "Blood Pressure Trend"
        }
        else if (target == tempCard) {
            Serial.println("👆 Temp card clicked - showing temperature trend");
            ui->showWaveformScreen();
            // TODO: Set waveform mode to "Temperature Trend"
        }
        else if (statusContainer && target == statusContainer) {
            Serial.println("👆 Status bar clicked - showing alerts screen");
            ui->showAlertsScreen();
        }
        else if (popupContainer && target == popupContainer) {
            Serial.println("👆 Alert popup clicked - hiding alert");
            ui->hideCriticalAlert();
        }
    }
}

void UIScreens::updateWaveform(int16_t *samples, uint8_t numSamples, const char*, const char*) {
    if (waveformFrozen) return;
    for (uint8_t i = 0; i < numSamples && i < 10; i++) {
        // Baseline at 70% from top (value 30) - medical ECG standard
        // Allows more space for upward deflections (P, R, T waves)
        // Samples are already scaled to 0-100 range by caller
        int v = constrain(samples[i], 0, 100);
        lv_chart_set_next_value(chartWaveform, seriesWaveform, v);
    }
    lv_chart_refresh(chartWaveform);
}

// ✅ v5.4.6: Add alert to flex container list
void UIScreens::addAlert(const char *msg, AlertSeverity severity) {
    if (!alertsList) return;

    // Remove "No alerts" placeholder if this is the first alert
    if (alertCount == 0) {
        lv_obj_clean(alertsList);
    }

    // Create alert item container
    lv_obj_t *alertItem = lv_obj_create(alertsList);
    lv_obj_set_width(alertItem, lv_pct(100));  // Full width
    lv_obj_set_height(alertItem, LV_SIZE_CONTENT);  // Auto height
    lv_obj_set_style_bg_color(alertItem, lv_color_hex(0x2A2A2A), 0);
    lv_obj_set_style_bg_opa(alertItem, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(alertItem, 1, 0);
    lv_obj_set_style_radius(alertItem, 5, 0);
    lv_obj_set_style_pad_all(alertItem, 10, 0);
    lv_obj_set_flex_flow(alertItem, LV_FLEX_FLOW_ROW);
    lv_obj_set_flex_align(alertItem, LV_FLEX_ALIGN_START, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_START);

    // Set border color based on severity
    uint32_t borderColor = (severity == ALERT_CRITICAL) ? 0xFF4444 :
                           (severity == ALERT_WARNING) ? 0xFFAA00 : 0x4488FF;
    lv_obj_set_style_border_color(alertItem, lv_color_hex(borderColor), 0);

    // Warning icon
    lv_obj_t *icon = lv_label_create(alertItem);
    lv_label_set_text(icon, LV_SYMBOL_WARNING);
    lv_obj_set_style_text_font(icon, &lv_font_montserrat_20, 0);
    lv_obj_set_style_text_color(icon, lv_color_hex(0xFFFFFF), 0);  // ✅ White text on dark bg (border provides color coding)
    lv_obj_set_style_pad_right(icon, 10, 0);

    // Alert message
    lv_obj_t *label = lv_label_create(alertItem);
    lv_label_set_text(label, msg);
    lv_obj_set_style_text_font(label, &lv_font_montserrat_16, 0);
    lv_obj_set_style_text_color(label, lv_color_hex(0xFFFFFF), 0);
    lv_obj_set_flex_grow(label, 1);  // Take remaining space
    lv_label_set_long_mode(label, LV_LABEL_LONG_WRAP);

    // Increment and update alert count
    alertCount++;
    updateAlertCount(alertCount);

    Serial.printf("📱 Alert added: %s (count: %d)\n", msg, alertCount);
}

// ✅ v5.4.6: Clear all alerts and show placeholder
void UIScreens::clearAllAlerts() {
    if (!alertsList) return;

    lv_obj_clean(alertsList);  // Remove all alert items
    alertCount = 0;  // Reset count
    updateAlertCount(0);

    // Show "No alerts" placeholder
    lv_obj_t *noAlertsLabel = lv_label_create(alertsList);
    lv_label_set_text(noAlertsLabel, "No active alerts");
    lv_obj_set_style_text_font(noAlertsLabel, &lv_font_montserrat_22, 0);  // ✅ Match font size from createAlertsScreen()
    lv_obj_set_style_text_color(noAlertsLabel, lv_color_hex(0xFFFFFF), 0);  // ✅ White text on dark bg
    lv_obj_set_style_text_opa(noAlertsLabel, LV_OPA_COVER, 0);  // ✅ Ensure full opacity for crisp rendering
    lv_obj_center(noAlertsLabel);

    Serial.println("📱 All alerts cleared");
}

// ✅ v5.4: Waveform freeze/unfreeze methods
void UIScreens::setWaveformFrozen(bool frozen) {
    waveformFrozen = frozen;
}

bool UIScreens::isWaveformFrozen() const {
    return waveformFrozen;
}

ScreenType UIScreens::getCurrentScreen() const {
    return currentScreen;
}

uint8_t UIScreens::getAlertCount() const {
    return alertCount;
}

// ✅ v5.4.6: Show popup alert AND add to alerts list
void UIScreens::showAlert(const char* title, const char* message) {
    // Combine title and message
    char buf[128];
    snprintf(buf, sizeof(buf), "%s - %s", title, message);

    // Show popup overlay
    showCriticalAlert(buf, ALERT_CRITICAL);

    // Add to alerts list so it appears in alerts screen
    addAlert(buf, ALERT_CRITICAL);

    // Log to serial
    Serial.printf("📱 UI Alert: %s\n", buf);
}
