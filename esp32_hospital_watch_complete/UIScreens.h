#ifndef UI_SCREENS_H
#define UI_SCREENS_H

#include <Arduino.h>
#include <lvgl.h>

enum AlertSeverity { ALERT_INFO = 0, ALERT_WARNING = 1, ALERT_CRITICAL = 2 };
enum ScreenType { SCREEN_HOME = 0, SCREEN_WAVEFORM = 1, SCREEN_ALERTS = 2, SCREEN_SETTINGS = 3, SCREEN_COUNT = 4 };

class UIScreens {
public:
    UIScreens();
    ~UIScreens();

    void init();
    bool isInitialized() const;

    void showHomeScreen();
    void showWaveformScreen();
    void showAlertsScreen();
    void showSettingsScreen();
    void showNextScreen();
    void showPreviousScreen();
    ScreenType getCurrentScreen() const;

    void updateVitals(float hr, float spo2, float temp, float bpSys, float bpDia, float rr);
    void updateConnectionStatus(bool wifi, bool mqtt, bool nfc);
    void updateBattery(uint8_t percent);
    void updateDeviceId(const char *deviceId);
    void updatePatientId(const char *patientId);
    void updateTime(const char* timeStr);           // NEW
    void showCriticalAlert(const char* message);    // NEW
    void hideCriticalAlert();                       // NEW
    void updateAlertCount(uint8_t count);           // NEW
    void showAlert(const char* title, const char* message);  // ✅ v5.4.1: Show popup alert

    void updateWaveform(int16_t *samples, uint8_t numSamples, const char *mode, const char *leadName);
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

    // Home screen widgets
    lv_obj_t *labelTime;
    lv_obj_t *iconWiFi;
    lv_obj_t *iconBattery;
    lv_obj_t *labelBatteryPercent;

    lv_obj_t *objAlertBar;
    lv_obj_t *objCriticalAlert;
    lv_obj_t *labelCriticalAlert;

    // ✅ v5.4: Clickable boxes for navigation
    lv_obj_t *ecgBox;
    lv_obj_t *hrBox;
    lv_obj_t *spo2Box;
    lv_obj_t *bpBox;
    lv_obj_t *tempBox;

    lv_obj_t *labelHR;
    lv_obj_t *labelSpO2;
    lv_obj_t *labelBP;
    lv_obj_t *labelTemp;
    lv_chart_series_t *seriesMiniECG;

    // Other screens
    lv_obj_t *chartWaveform;
    lv_chart_series_t *seriesWaveform;
    lv_obj_t *labelWaveformMode;
    lv_obj_t *labelWaveformStatus;

    lv_obj_t *alertsList;
    lv_obj_t *buttonClearAlerts;

    lv_obj_t *sliderBrightness;
    lv_obj_t *labelBrightnessValue;

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