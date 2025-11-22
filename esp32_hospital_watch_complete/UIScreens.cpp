#include "UIScreens.h"
#include "DisplayManager.h"

UIScreens ui;
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

void UIScreens::createHomeScreen() {
    homeScreen = lv_obj_create(NULL);
    lv_obj_set_style_bg_color(homeScreen, lv_color_hex(0x000000), 0);

    // Status bar
    lv_obj_t *status = lv_obj_create(homeScreen);
    lv_obj_set_size(status, W, 60);
    lv_obj_align(status, LV_ALIGN_TOP_MID, 0, 0);
    lv_obj_set_style_bg_opa(status, LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_width(status, 0, 0);

    labelTime = lv_label_create(status);
    lv_label_set_text(labelTime, "10:10");
    lv_obj_set_style_text_font(labelTime, &lv_font_montserrat_28, 0);
    lv_obj_align(labelTime, LV_ALIGN_LEFT_MID, 15, 0);

    iconWiFi = lv_label_create(status);
    lv_label_set_text(iconWiFi, LV_SYMBOL_WIFI);
    lv_obj_align(iconWiFi, LV_ALIGN_RIGHT_MID, -70, 0);

    lv_obj_t *bt = lv_label_create(status);
    lv_label_set_text(bt, LV_SYMBOL_BLUETOOTH);
    lv_obj_align(bt, LV_ALIGN_RIGHT_MID, -45, 0);

    iconBattery = lv_label_create(status);
    lv_label_set_text(iconBattery, LV_SYMBOL_BATTERY_FULL);
    lv_obj_align(iconBattery, LV_ALIGN_RIGHT_MID, -15, 0);

    labelBatteryPercent = lv_label_create(status);
    lv_label_set_text(labelBatteryPercent, "75%");
    lv_obj_align(labelBatteryPercent, LV_ALIGN_RIGHT_MID, -35, 15);

    // Alerts bar
    objAlertBar = lv_obj_create(homeScreen);
    lv_obj_set_size(objAlertBar, W-40, 45);
    lv_obj_align(objAlertBar, LV_ALIGN_TOP_MID, 0, 65);
    lv_obj_set_style_bg_color(objAlertBar, lv_color_hex(0x1C2526), 0);
    lv_obj_set_style_radius(objAlertBar, 10, 0);

    lv_obj_t *a = lv_label_create(objAlertBar);
    lv_label_set_text(a, "Alerts");
    lv_obj_set_style_text_font(a, &lv_font_montserrat_20, 0);
    lv_obj_align(a, LV_ALIGN_LEFT_MID, 15, 0);

    lv_obj_t *cnt = lv_label_create(objAlertBar);
    lv_label_set_text(cnt, "0");
    lv_obj_set_style_text_color(cnt, lv_color_hex(0x00FFFF), 0);
    lv_obj_set_style_text_font(cnt, &lv_font_montserrat_20, 0);
    lv_obj_align(cnt, LV_ALIGN_RIGHT_MID, -40, 0);

    lv_obj_t *arrow = lv_label_create(objAlertBar);
    lv_label_set_text(arrow, LV_SYMBOL_RIGHT);
    lv_obj_align(arrow, LV_ALIGN_RIGHT_MID, -10, 0);

    lv_obj_add_flag(objAlertBar, LV_OBJ_FLAG_HIDDEN);

    // Critical banner
    objCriticalAlert = lv_obj_create(homeScreen);
    lv_obj_set_size(objCriticalAlert, W, 50);
    lv_obj_align(objCriticalAlert, LV_ALIGN_TOP_MID, 0, 0);
    lv_obj_set_style_bg_color(objCriticalAlert, lv_color_hex(0xCC0000), 0);
    lv_obj_set_style_bg_opa(objCriticalAlert, LV_OPA_90, 0);

    labelCriticalAlert = lv_label_create(objCriticalAlert);
    lv_label_set_text(labelCriticalAlert, "ALERT: Tachycardia");
    lv_obj_set_style_text_font(labelCriticalAlert, &lv_font_montserrat_18, 0);
    lv_obj_center(labelCriticalAlert);
    lv_obj_add_flag(objCriticalAlert, LV_OBJ_FLAG_HIDDEN);

    // HR + mini ECG
    lv_obj_t *hr = lv_obj_create(homeScreen);
    lv_obj_set_size(hr, 260, 110);
    lv_obj_align(hr, LV_ALIGN_TOP_MID, 0, 120);
    lv_obj_set_style_bg_color(hr, lv_color_hex(0x8B0000), 0);
    lv_obj_set_style_radius(hr, 15, 0);

    labelHR = lv_label_create(hr);
    lv_label_set_text(labelHR, "130");
    lv_obj_set_style_text_font(labelHR, &lv_font_montserrat_48, 0);
    lv_obj_align(labelHR, LV_ALIGN_LEFT_MID, 20, -5);

    lv_obj_t *bpm = lv_label_create(hr);
    lv_label_set_text(bpm, "BPM");
    lv_obj_align(bpm, LV_ALIGN_BOTTOM_LEFT, 20, -10);

    lv_obj_t *mini = lv_chart_create(hr);
    lv_obj_set_size(mini, 130, 60);
    lv_obj_align(mini, LV_ALIGN_RIGHT_MID, -10, 0);
    lv_chart_set_type(mini, LV_CHART_TYPE_LINE);
    lv_chart_set_range(mini, LV_CHART_AXIS_PRIMARY_Y, 0, 100);
    lv_obj_set_style_line_width(mini, 3, LV_PART_ITEMS);
    lv_obj_set_style_size(mini, 0, LV_PART_INDICATOR);
    lv_chart_set_point_count(mini, 80);
    seriesMiniECG = lv_chart_add_series(mini, lv_color_hex(0x00FF00), LV_CHART_AXIS_PRIMARY_Y);

    // SpO2
    lv_obj_t *spo2 = lv_obj_create(homeScreen);
    lv_obj_set_size(spo2, 125, 90);
    lv_obj_align(spo2, LV_ALIGN_TOP_LEFT, 10, 240);
    lv_obj_set_style_bg_color(spo2, lv_color_hex(0x006400), 0);
    lv_obj_set_style_radius(spo2, 15, 0);

    labelSpO2 = lv_label_create(spo2);
    lv_label_set_text(labelSpO2, "98%");
    lv_obj_set_style_text_font(labelSpO2, &lv_font_montserrat_36, 0);
    lv_obj_center(labelSpO2);

    // BP
    lv_obj_t *bp = lv_obj_create(homeScreen);
    lv_obj_set_size(bp, 125, 90);
    lv_obj_align(bp, LV_ALIGN_TOP_RIGHT, -10, 240);
    lv_obj_set_style_bg_color(bp, lv_color_hex(0x8B8000), 0);
    lv_obj_set_style_radius(bp, 15, 0);

    labelBP = lv_label_create(bp);
    lv_label_set_text(labelBP, "120/80");
    lv_obj_set_style_text_font(labelBP, &lv_font_montserrat_28, 0);
    lv_obj_center(labelBP);

    // Temp
    lv_obj_t *temp = lv_obj_create(homeScreen);
    lv_obj_set_size(temp, 260, 90);
    lv_obj_align(temp, LV_ALIGN_BOTTOM_MID, 0, -20);
    lv_obj_set_style_bg_color(temp, lv_color_hex(0x00FF00), 0);
    lv_obj_set_style_radius(temp, 15, 0);

    labelTemp = lv_label_create(temp);
    lv_label_set_text(labelTemp, "37.5°C");
    lv_obj_set_style_text_color(labelTemp, lv_color_hex(0x000000), 0);
    lv_obj_set_style_text_font(labelTemp, &lv_font_montserrat_48, 0);
    lv_obj_center(labelTemp);
}

void UIScreens::createWaveformScreen() {
    waveformScreen = lv_obj_create(NULL);
    lv_obj_set_style_bg_color(waveformScreen, lv_color_hex(0x000000), 0);

    labelWaveformMode = lv_label_create(waveformScreen);
    lv_label_set_text(labelWaveformMode, "ECG - Lead II");
    lv_obj_align(labelWaveformMode, LV_ALIGN_TOP_MID, 0, 10);

    chartWaveform = lv_chart_create(waveformScreen);
    lv_obj_set_size(chartWaveform, W-20, 300);
    lv_obj_center(chartWaveform);
    lv_chart_set_type(chartWaveform, LV_CHART_TYPE_LINE);
    lv_chart_set_range(chartWaveform, LV_CHART_AXIS_PRIMARY_Y, 0, 100);
    lv_chart_set_point_count(chartWaveform, 200);
    seriesWaveform = lv_chart_add_series(chartWaveform, lv_color_hex(0x00FF00), LV_CHART_AXIS_PRIMARY_Y);

    labelWaveformStatus = lv_label_create(waveformScreen);
    lv_label_set_text(labelWaveformStatus, "LIVE");
    lv_obj_set_style_text_color(labelWaveformStatus, lv_color_hex(0x00FF00), 0);
    lv_obj_align(labelWaveformStatus, LV_ALIGN_BOTTOM_MID, 0, -10);

    lv_obj_add_event_cb(chartWaveform, event_callback, LV_EVENT_PRESSING, this);
}

void UIScreens::createAlertsScreen() {
    alertsScreen = lv_obj_create(NULL);
    lv_obj_set_style_bg_color(alertsScreen, lv_color_hex(0x000814), 0);

    lv_obj_t *title = lv_label_create(alertsScreen);
    lv_label_set_text(title, "Active Alerts");
    lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 20);

    alertsList = lv_list_create(alertsScreen);
    lv_obj_set_size(alertsList, W-40, H-140);
    lv_obj_center(alertsList);

    buttonClearAlerts = lv_btn_create(alertsScreen);
    lv_obj_set_size(buttonClearAlerts, 180, 50);
    lv_obj_align(buttonClearAlerts, LV_ALIGN_BOTTOM_MID, 0, -20);
    lv_obj_t *lbl = lv_label_create(buttonClearAlerts);
    lv_label_set_text(lbl, "Clear All");
    lv_obj_center(lbl);
    lv_obj_add_event_cb(buttonClearAlerts, event_callback, LV_EVENT_CLICKED, this);
}

void UIScreens::createSettingsScreen() {
    settingsScreen = lv_obj_create(NULL);
    lv_obj_set_style_bg_color(settingsScreen, lv_color_hex(0x000814), 0);

    lv_obj_t *t = lv_label_create(settingsScreen);
    lv_label_set_text(t, "Settings");
    lv_obj_align(t, LV_ALIGN_TOP_MID, 0, 20);

    sliderBrightness = lv_slider_create(settingsScreen);
    lv_slider_set_range(sliderBrightness, 10, 255);
    lv_slider_set_value(sliderBrightness, 200, LV_ANIM_OFF);
    lv_obj_set_size(sliderBrightness, 240, 20);
    lv_obj_align(sliderBrightness, LV_ALIGN_CENTER, 0, -50);
    lv_obj_add_event_cb(sliderBrightness, event_callback, LV_EVENT_VALUE_CHANGED, this);

    labelBrightnessValue = lv_label_create(settingsScreen);
    lv_label_set_text(labelBrightnessValue, "200");
    lv_obj_align(labelBrightnessValue, LV_ALIGN_CENTER, 0, -20);
}

void UIScreens::event_callback(lv_event_t *e) {
    lv_event_code_t code = lv_event_get_code(e);
    UIScreens *ui = (UIScreens*)lv_event_get_user_data(e);

    if (code == LV_EVENT_VALUE_CHANGED && lv_event_get_target(e) == ui->sliderBrightness) {
        int v = lv_slider_get_value(ui->sliderBrightness);
        char b[8]; snprintf(b, sizeof(b), "%d", v);
        lv_label_set_text(ui->labelBrightnessValue, b);
        extern void setDisplayBrightness(uint8_t);
        setDisplayBrightness(v);
    }
    if (code == LV_EVENT_CLICKED && lv_event_get_target(e) == ui->buttonClearAlerts) {
        ui->clearAllAlerts();
    }
    if (code == LV_EVENT_PRESSING && lv_event_get_target(e) == ui->chartWaveform) {
        ui->setWaveformFrozen(!ui->isWaveformFrozen());
        lv_label_set_text(ui->labelWaveformStatus, ui->isWaveformFrozen() ? "FROZEN" : "LIVE");
        lv_obj_set_style_text_color(ui->labelWaveformStatus, ui->isWaveformFrozen() ? lv_color_hex(0xFFFF00) : lv_color_hex(0x00FF00), 0);
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