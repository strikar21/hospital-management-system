#ifndef UI_SCREENS_H
#define UI_SCREENS_H

#include <Arduino.h>
#include <lvgl.h>
#include "StatusBar.h"
#include "PatientBar.h"
#include "AlertPopup.h"
#include "VitalsCards.h"
#include "ECGChart.h"

enum ScreenType { SCREEN_HOME = 0, SCREEN_WAVEFORM = 1, SCREEN_ALERTS = 2, SCREEN_SETTINGS = 3, SCREEN_COUNT = 4 };

class UIScreens {
public:
    UIScreens();
    ~UIScreens();

    void init();
    bool isInitialized() const;
    void applyTextSmoothing(lv_obj_t *obj);  // ✅ v5.4.4: Apply text anti-aliasing globally

    void showHomeScreen();
    void showWaveformScreen();
    void showAlertsScreen();
    void showSettingsScreen();
    void showNextScreen();
    void showPreviousScreen();
    ScreenType getCurrentScreen() const;

    void updateVitals(float hr, float spo2, float temp, float bpSys, float bpDia, float rr);
    void updateVitalIMU(float fallRisk, float tremor);
    void updateConnectionStatus(bool wifi, bool mqtt, bool nfc);
    void updateBattery(uint8_t percent);
    void updateDeviceId(const char *deviceId);
    void updatePatientId(const char *patientId);
    void updateTime(const char* timeStr);
    void showCriticalAlert(const char* message);    // Show alert with default CRITICAL severity
    void showCriticalAlert(const char* message, AlertSeverity severity);  // ✅ v5.4.2: With severity color
    void hideCriticalAlert();
    void updateAlertCount(uint8_t count);
    void showAlert(const char* title, const char* message);  // ✅ v5.4.1: Show popup alert

    void updateWaveform(int16_t *samples, uint8_t numSamples, const char *mode, const char *leadName);
    void updateHomeECG(int32_t *samples, uint8_t numSamples);  // ✅ v5.4.3: Update home screen ECG chart (int32_t for microBatch compatibility)
    void setWaveformFrozen(bool frozen);
    bool isWaveformFrozen() const;

    void addAlert(const char *message, AlertSeverity severity);
    void clearAllAlerts();
    uint8_t getAlertCount() const;

private:
    bool initialized = false;
    ScreenType currentScreen = SCREEN_HOME;
    bool waveformFrozen = false;
    uint8_t alertCount = 0;

    lv_obj_t *homeScreen = nullptr;
    lv_obj_t *waveformScreen = nullptr;
    lv_obj_t *alertsScreen = nullptr;
    lv_obj_t *settingsScreen = nullptr;

    // ✅ v5.4.6: Modular components (home screen)
    StatusBar statusBar;
    PatientBar patientBar;
    AlertPopup alertPopup;
    VitalsCards vitalsCards;
    ECGChart ecgChart;

    // Other screens
    lv_obj_t *chartWaveform;
    lv_chart_series_t *seriesWaveform;
    lv_obj_t *labelWaveformMode;
    lv_obj_t *labelWaveformStatus;

    lv_obj_t *alertsList;
    lv_obj_t *buttonClearAlerts;

    lv_obj_t *sliderBrightness;
    lv_obj_t *labelBrightnessValue;
    lv_obj_t *sliderTimeout;       // ✅ v5.6.0: Screen timeout slider
    lv_obj_t *labelTimeoutValue;   // ✅ v5.6.0: Screen timeout value label
    lv_obj_t *switchTapWake;       // ✅ v5.6.0: Tap to wake toggle

    void createHomeScreen();
    void createWaveformScreen();
    void createAlertsScreen();
    void createSettingsScreen();

    void loadScreen(lv_obj_t *screen);
    static void clearAlertsButtonCallback(lv_event_t *event);
    static void brightnessSliderCallback(lv_event_t *event);
    static void waveformTapCallback(lv_event_t *event);
    static void event_callback(lv_event_t *event);  // ✅ v5.4: Generic event callback for screen navigation
};

#endif