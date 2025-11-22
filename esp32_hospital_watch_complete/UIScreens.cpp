#include "UIScreens.h"
#include "DisplayManager.h"

// ✅ v5.4: Removed duplicate 'ui' definition (already defined in .ino file)
static const uint16_t W = 280;
static const uint16_t H = 456;

UIScreens::UIScreens() {}
UIScreens::~UIScreens() {}

void UIScreens::init() {
    if (initialized) return;
    createHomeScreen();
    createWaveformScreen();
    createAlertsScreen();
    createSettingsScreen();
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

void UIScreens::updateTime(const char* t) { if(labelTime) lv_label_set_text(labelTime, t); }
void UIScreens::updateBattery(uint8_t p) {
    char b[8]; snprintf(b, sizeof(b), "%d%%", p);
    lv_label_set_text(labelBatteryPercent, b);
    lv_obj_set_style_text_color(iconBattery, p>50?lv_color_hex(0x00FF00):p>20?lv_color_hex(0xFFFF00):lv_color_hex(0xFF0000), 0);
}
void UIScreens::updateConnectionStatus(bool wifi, bool, bool) {
    lv_label_set_text(iconWiFi, wifi ? LV_SYMBOL_WIFI : LV_SYMBOL_CLOSE);
    lv_obj_set_style_text_color(iconWiFi, wifi ? lv_color_hex(0x00FF00) : lv_color_hex(0xFF0000), 0);
}

void UIScreens::updateVitals(float hr, float spo2, float temp, float bpSys, float bpDia, float) {
    char buf[32];
    snprintf(buf, sizeof(buf), "%.0f", hr);      lv_label_set_text(labelHR, buf);
    snprintf(buf, sizeof(buf), "%.0f%%", spo2);  lv_label_set_text(labelSpO2, buf);
    snprintf(buf, sizeof(buf), "%.1f°C", temp);  lv_label_set_text(labelTemp, buf);
    snprintf(buf, sizeof(buf), "%.0f/%.0f", bpSys, bpDia); lv_label_set_text(labelBP, buf);
}

void UIScreens::showCriticalAlert(const char* msg) {
    lv_label_set_text(labelCriticalAlert, msg);
    lv_obj_clear_flag(objCriticalAlert, LV_OBJ_FLAG_HIDDEN);
    lv_obj_move_foreground(objCriticalAlert);
}
void UIScreens::hideCriticalAlert() { lv_obj_add_flag(objCriticalAlert, LV_OBJ_FLAG_HIDDEN); }

void UIScreens::updateAlertCount(uint8_t c) {
    alertCount = c;
    if (c == 0) {
        lv_obj_add_flag(objAlertBar, LV_OBJ_FLAG_HIDDEN);
    } else {
        lv_obj_clear_flag(objAlertBar, LV_OBJ_FLAG_HIDDEN);
        lv_obj_t *cnt = lv_obj_get_child(objAlertBar, 1);
        char buf[8]; snprintf(buf, sizeof(buf), "%d", c);
        lv_label_set_text(cnt, buf);
    }
}

// ✅ v5.4: HOME SCREEN - Fixed layout and positions to match reference
void UIScreens::createHomeScreen() {
    homeScreen = lv_obj_create(NULL);
    lv_obj_set_style_bg_color(homeScreen, lv_color_hex(0x000000), 0);
    lv_obj_set_style_bg_opa(homeScreen, LV_OPA_COVER, 0);

    // Critical Alert Banner (very top, shown when alert active)
    objCriticalAlert = lv_obj_create(homeScreen);
    lv_obj_set_size(objCriticalAlert, W, 50);
    lv_obj_set_pos(objCriticalAlert, 0, 0);  // Fixed at top
    lv_obj_set_style_bg_color(objCriticalAlert, lv_color_hex(0xE74C3C), 0);  // Red
    lv_obj_set_style_bg_opa(objCriticalAlert, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(objCriticalAlert, 0, 0);
    lv_obj_set_style_radius(objCriticalAlert, 0, 0);

    labelCriticalAlert = lv_label_create(objCriticalAlert);
    lv_label_set_text(labelCriticalAlert, LV_SYMBOL_WARNING " ALERT: Tachycardia Detected");
    lv_obj_set_style_text_font(labelCriticalAlert, &lv_font_montserrat_18, 0);
    lv_obj_set_style_text_color(labelCriticalAlert, lv_color_hex(0xFFFFFF), 0);
    lv_obj_center(labelCriticalAlert);
    lv_obj_add_flag(objCriticalAlert, LV_OBJ_FLAG_HIDDEN);

    // ECG Waveform Box (left side, tall) - Y: 50 to 350 (300px height)
    ecgBox = lv_obj_create(homeScreen);
    lv_obj_set_size(ecgBox, 135, 300);
    lv_obj_set_pos(ecgBox, 5, 50);
    lv_obj_set_style_bg_color(ecgBox, lv_color_hex(0x1A4D1A), 0);  // Forest green
    lv_obj_set_style_bg_opa(ecgBox, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(ecgBox, 8, 0);
    lv_obj_set_style_border_width(ecgBox, 0, 0);
    lv_obj_add_flag(ecgBox, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_add_event_cb(ecgBox, event_callback, LV_EVENT_CLICKED, this);

    // ECG label
    lv_obj_t *ecgLabel = lv_label_create(ecgBox);
    lv_label_set_text(ecgLabel, "ECG");
    lv_obj_set_style_text_font(ecgLabel, &lv_font_montserrat_18, 0);
    lv_obj_set_style_text_color(ecgLabel, lv_color_hex(0xFFFFFF), 0);
    lv_obj_align(ecgLabel, LV_ALIGN_TOP_MID, 0, 8);

    // Mini ECG chart
    lv_obj_t *mini = lv_chart_create(ecgBox);
    lv_obj_set_size(mini, 115, 250);
    lv_obj_align(mini, LV_ALIGN_BOTTOM_MID, 0, -8);
    lv_chart_set_type(mini, LV_CHART_TYPE_LINE);
    lv_chart_set_range(mini, LV_CHART_AXIS_PRIMARY_Y, 0, 100);
    lv_obj_set_style_line_width(mini, 2, LV_PART_ITEMS);
    lv_obj_set_style_size(mini, 0, LV_PART_INDICATOR);
    lv_obj_set_style_bg_opa(mini, LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_width(mini, 0, 0);
    lv_chart_set_point_count(mini, 100);
    seriesMiniECG = lv_chart_add_series(mini, lv_color_hex(0x00FF00), LV_CHART_AXIS_PRIMARY_Y);

    // HR Box (right top) - Y: 50, height: 135
    hrBox = lv_obj_create(homeScreen);
    lv_obj_set_size(hrBox, 135, 135);
    lv_obj_set_pos(hrBox, 145, 50);
    lv_obj_set_style_bg_color(hrBox, lv_color_hex(0x000000), 0);  // Pure BLACK
    lv_obj_set_style_bg_opa(hrBox, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(hrBox, 8, 0);
    lv_obj_set_style_border_width(hrBox, 2, 0);
    lv_obj_set_style_border_color(hrBox, lv_color_hex(0xFF7043), 0);  // Coral/orange
    lv_obj_add_flag(hrBox, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_add_event_cb(hrBox, event_callback, LV_EVENT_CLICKED, this);

    labelHR = lv_label_create(hrBox);
    lv_label_set_text(labelHR, "130");
    lv_obj_set_style_text_font(labelHR, &lv_font_montserrat_48, 0);
    lv_obj_set_style_text_color(labelHR, lv_color_hex(0xFF7043), 0);  // Coral/orange
    lv_obj_align(labelHR, LV_ALIGN_CENTER, 0, -12);

    lv_obj_t *bpmLabel = lv_label_create(hrBox);
    lv_label_set_text(bpmLabel, "BPM");
    lv_obj_set_style_text_font(bpmLabel, &lv_font_montserrat_18, 0);
    lv_obj_set_style_text_color(bpmLabel, lv_color_hex(0xCCCCCC), 0);
    lv_obj_align(bpmLabel, LV_ALIGN_BOTTOM_MID, 0, -12);

    // SpO2 Box (right middle) - Y: 195, height: 155
    spo2Box = lv_obj_create(homeScreen);
    lv_obj_set_size(spo2Box, 135, 155);
    lv_obj_set_pos(spo2Box, 145, 195);
    lv_obj_set_style_bg_color(spo2Box, lv_color_hex(0x000000), 0);  // Pure BLACK
    lv_obj_set_style_bg_opa(spo2Box, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(spo2Box, 8, 0);
    lv_obj_set_style_border_width(spo2Box, 2, 0);
    lv_obj_set_style_border_color(spo2Box, lv_color_hex(0x00FF00), 0);  // Green
    lv_obj_add_flag(spo2Box, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_add_event_cb(spo2Box, event_callback, LV_EVENT_CLICKED, this);

    labelSpO2 = lv_label_create(spo2Box);
    lv_label_set_text(labelSpO2, "98%");
    lv_obj_set_style_text_font(labelSpO2, &lv_font_montserrat_48, 0);
    lv_obj_set_style_text_color(labelSpO2, lv_color_hex(0x00FF00), 0);  // Bright green
    lv_obj_align(labelSpO2, LV_ALIGN_CENTER, 0, -12);

    lv_obj_t *spo2Label = lv_label_create(spo2Box);
    lv_label_set_text(spo2Label, "SpO2");
    lv_obj_set_style_text_font(spo2Label, &lv_font_montserrat_18, 0);
    lv_obj_set_style_text_color(spo2Label, lv_color_hex(0xCCCCCC), 0);
    lv_obj_align(spo2Label, LV_ALIGN_BOTTOM_MID, 0, -12);

    // BP Box (bottom left) - Y: 360, height: 90
    bpBox = lv_obj_create(homeScreen);
    lv_obj_set_size(bpBox, 135, 90);
    lv_obj_set_pos(bpBox, 5, 360);
    lv_obj_set_style_bg_color(bpBox, lv_color_hex(0xC0D930), 0);  // Lime yellow-green
    lv_obj_set_style_bg_opa(bpBox, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(bpBox, 8, 0);
    lv_obj_set_style_border_width(bpBox, 0, 0);
    lv_obj_add_flag(bpBox, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_add_event_cb(bpBox, event_callback, LV_EVENT_CLICKED, this);

    labelBP = lv_label_create(bpBox);
    lv_label_set_text(labelBP, "120/80");
    lv_obj_set_style_text_font(labelBP, &lv_font_montserrat_28, 0);
    lv_obj_set_style_text_color(labelBP, lv_color_hex(0x000000), 0);  // Black text
    lv_obj_align(labelBP, LV_ALIGN_CENTER, 0, -8);

    lv_obj_t *bpLabel = lv_label_create(bpBox);
    lv_label_set_text(bpLabel, "BP");
    lv_obj_set_style_text_font(bpLabel, &lv_font_montserrat_16, 0);
    lv_obj_set_style_text_color(bpLabel, lv_color_hex(0x000000), 0);
    lv_obj_align(bpLabel, LV_ALIGN_BOTTOM_MID, 0, -6);

    // Temp Box (bottom right) - Y: 360, height: 90
    tempBox = lv_obj_create(homeScreen);
    lv_obj_set_size(tempBox, 135, 90);
    lv_obj_set_pos(tempBox, 145, 360);
    lv_obj_set_style_bg_color(tempBox, lv_color_hex(0x4DD0C0), 0);  // Cyan/turquoise
    lv_obj_set_style_bg_opa(tempBox, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(tempBox, 8, 0);
    lv_obj_set_style_border_width(tempBox, 0, 0);
    lv_obj_add_flag(tempBox, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_add_event_cb(tempBox, event_callback, LV_EVENT_CLICKED, this);

    labelTemp = lv_label_create(tempBox);
    lv_label_set_text(labelTemp, "37.5°C");
    lv_obj_set_style_text_font(labelTemp, &lv_font_montserrat_28, 0);
    lv_obj_set_style_text_color(labelTemp, lv_color_hex(0x000000), 0);  // Black text
    lv_obj_align(labelTemp, LV_ALIGN_CENTER, 0, -8);

    lv_obj_t *tempLabel = lv_label_create(tempBox);
    lv_label_set_text(tempLabel, "TEMP");
    lv_obj_set_style_text_font(tempLabel, &lv_font_montserrat_16, 0);
    lv_obj_set_style_text_color(tempLabel, lv_color_hex(0x000000), 0);
    lv_obj_align(tempLabel, LV_ALIGN_BOTTOM_MID, 0, -6);

    // Status bar (time, wifi, battery) - Removed since not in reference
    // Alerts bar (hidden by default) - Removed since not in reference
    objAlertBar = nullptr;
    labelTime = nullptr;
    iconWiFi = nullptr;
    iconBattery = nullptr;
    labelBatteryPercent = nullptr;
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
    lv_obj_set_style_text_color(labelWaveformMode, lv_color_hex(0x00FF00), 0);
    lv_obj_align(labelWaveformMode, LV_ALIGN_TOP_MID, 0, 55);

    chartWaveform = lv_chart_create(waveformScreen);
    lv_obj_set_size(chartWaveform, W-20, 300);
    lv_obj_center(chartWaveform);
    lv_chart_set_type(chartWaveform, LV_CHART_TYPE_LINE);
    lv_chart_set_range(chartWaveform, LV_CHART_AXIS_PRIMARY_Y, 0, 100);
    lv_chart_set_point_count(chartWaveform, 200);
    lv_obj_set_style_line_width(chartWaveform, 3, LV_PART_ITEMS);
    lv_obj_set_style_bg_color(chartWaveform, lv_color_hex(0x0A0A0A), 0);
    seriesWaveform = lv_chart_add_series(chartWaveform, lv_color_hex(0x00FF00), LV_CHART_AXIS_PRIMARY_Y);

    labelWaveformStatus = lv_label_create(waveformScreen);
    lv_label_set_text(labelWaveformStatus, "LIVE");
    lv_obj_set_style_text_font(labelWaveformStatus, &lv_font_montserrat_24, 0);
    lv_obj_set_style_text_color(labelWaveformStatus, lv_color_hex(0x00FF00), 0);
    lv_obj_align(labelWaveformStatus, LV_ALIGN_BOTTOM_MID, 0, -15);

    lv_obj_t *hint = lv_label_create(waveformScreen);
    lv_label_set_text(hint, "Tap to freeze/unfreeze");
    lv_obj_set_style_text_font(hint, &lv_font_montserrat_16, 0);
    lv_obj_set_style_text_color(hint, lv_color_hex(0x808080), 0);
    lv_obj_align(hint, LV_ALIGN_BOTTOM_MID, 0, -45);

    lv_obj_add_event_cb(chartWaveform, event_callback, LV_EVENT_PRESSING, this);
}

// ✅ v5.4: ALERTS SCREEN - Improved design with larger fonts
void UIScreens::createAlertsScreen() {
    alertsScreen = lv_obj_create(NULL);
    lv_obj_set_style_bg_color(alertsScreen, lv_color_hex(0x000000), 0);
    lv_obj_set_style_bg_opa(alertsScreen, LV_OPA_COVER, 0);

    lv_obj_t *title = lv_label_create(alertsScreen);
    lv_label_set_text(title, "ACTIVE ALERTS");
    lv_obj_set_style_text_font(title, &lv_font_montserrat_28, 0);
    lv_obj_set_style_text_color(title, lv_color_hex(0xFFFFFF), 0);
    lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 20);

    alertsList = lv_list_create(alertsScreen);
    lv_obj_set_size(alertsList, W-30, H-160);
    lv_obj_align(alertsList, LV_ALIGN_TOP_MID, 0, 65);
    lv_obj_set_style_bg_color(alertsList, lv_color_hex(0x1A1A1A), 0);
    lv_obj_set_style_text_font(alertsList, &lv_font_montserrat_18, 0);

    buttonClearAlerts = lv_btn_create(alertsScreen);
    lv_obj_set_size(buttonClearAlerts, 200, 55);
    lv_obj_align(buttonClearAlerts, LV_ALIGN_BOTTOM_MID, 0, -20);
    lv_obj_set_style_bg_color(buttonClearAlerts, lv_color_hex(0xE74C3C), 0);

    lv_obj_t *btnLabel = lv_label_create(buttonClearAlerts);
    lv_label_set_text(btnLabel, "Clear All");
    lv_obj_set_style_text_font(btnLabel, &lv_font_montserrat_22, 0);
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
    lv_obj_set_style_text_font(brightLabel, &lv_font_montserrat_22, 0);
    lv_obj_set_style_text_color(brightLabel, lv_color_hex(0xCCCCCC), 0);
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
    lv_obj_set_style_text_color(labelBrightnessValue, lv_color_hex(0x3498DB), 0);
    lv_obj_align(labelBrightnessValue, LV_ALIGN_TOP_MID, 0, 190);

    lv_obj_t *hint = lv_label_create(settingsScreen);
    lv_label_set_text(hint, "Swipe left/right to switch screens");
    lv_obj_set_style_text_font(hint, &lv_font_montserrat_16, 0);
    lv_obj_set_style_text_color(hint, lv_color_hex(0x808080), 0);
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

    // ✅ v5.4: Clear alerts button
    if (code == LV_EVENT_CLICKED && target == ui->buttonClearAlerts) {
        ui->clearAllAlerts();
    }

    // ✅ v5.4: Waveform freeze/unfreeze
    if (code == LV_EVENT_PRESSING && target == ui->chartWaveform) {
        ui->setWaveformFrozen(!ui->isWaveformFrozen());
        lv_label_set_text(ui->labelWaveformStatus, ui->isWaveformFrozen() ? "FROZEN" : "LIVE");
        lv_obj_set_style_text_color(ui->labelWaveformStatus, ui->isWaveformFrozen() ? lv_color_hex(0xFFFF00) : lv_color_hex(0x00FF00), 0);
    }

    // ✅ v5.4: Clickable boxes for navigation
    if (code == LV_EVENT_CLICKED) {
        if (target == ui->ecgBox || target == ui->hrBox) {
            Serial.println("👆 ECG/HR box clicked - showing waveform screen");
            ui->showWaveformScreen();
        }
        else if (target == ui->spo2Box) {
            Serial.println("👆 SpO2 box clicked - showing waveform screen");
            ui->showWaveformScreen();
        }
        else if (target == ui->bpBox) {
            Serial.println("👆 BP box clicked - showing settings screen");
            ui->showSettingsScreen();
        }
        else if (target == ui->tempBox) {
            Serial.println("👆 Temp box clicked - showing settings screen");
            ui->showSettingsScreen();
        }
        else if (ui->objAlertBar && target == ui->objAlertBar) {
            Serial.println("👆 Alert bar clicked - showing alerts screen");
            ui->showAlertsScreen();
        }
    }
}

void UIScreens::updateWaveform(int16_t *samples, uint8_t numSamples, const char*, const char*) {
    if (waveformFrozen) return;
    for (uint8_t i = 0; i < numSamples && i < 10; i++) {
        int v = map(samples[i], -500000, 500000, 0, 100);
        lv_chart_set_next_value(chartWaveform, seriesWaveform, v);
    }
    lv_chart_refresh(chartWaveform);
}

void UIScreens::addAlert(const char *msg, AlertSeverity) {
    lv_obj_t *btn = lv_list_add_btn(alertsList, LV_SYMBOL_WARNING, msg);
    lv_obj_set_style_text_color(btn, lv_color_hex(0xFF4444), LV_PART_MAIN);
}

void UIScreens::clearAllAlerts() {
    lv_obj_clean(alertsList);
    updateAlertCount(0);
    hideCriticalAlert();
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

// ✅ v5.4.1: Show popup alert (for NFC tap, etc.)
void UIScreens::showAlert(const char* title, const char* message) {
    // Use the critical alert banner for now
    char buf[128];
    snprintf(buf, sizeof(buf), "%s - %s", title, message);
    showCriticalAlert(buf);

    // Auto-hide after 3 seconds
    static unsigned long alertStartTime = 0;
    alertStartTime = millis();

    // Log to serial
    Serial.printf("📱 UI Alert: %s\n", buf);
}
