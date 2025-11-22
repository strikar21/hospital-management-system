/**
 * VitalsAlertsManager.cpp
 * Hospital Watch - Vital Signs Alert Management Implementation
 *
 * Author: Expert Team Analysis
 * Date: 2025-11-22
 * Version: 5.5.0
 */

#include "VitalsAlertsManager.h"

VitalsAlertsManager::VitalsAlertsManager() {
  // Initialize all states to default
  hrAlertState = {false, 0, 0, 0, ALERT_INFO};
  spo2AlertState = {false, 0, 0, 0, ALERT_INFO};
  tempAlertState = {false, 0, 0, 0, ALERT_INFO};
  bpSysAlertState = {false, 0, 0, 0, ALERT_INFO};
  bpDiaAlertState = {false, 0, 0, 0, ALERT_INFO};
  rrAlertState = {false, 0, 0, 0, ALERT_INFO};

  vitalAlertPersistence = 3;  // 3 consecutive readings (15s at 5s interval)
  vitalsAlertCooldownUntil = 0;
  fallCooldownDuration = 30000;  // 30 seconds

  alertCallback = nullptr;
  uiCallback = nullptr;

  // History pointers will be set in init()
  hrHistory = nullptr;
  spo2History = nullptr;
  tempHistory = nullptr;
  bpSysHistory = nullptr;
  bpDiaHistory = nullptr;
  rrHistory = nullptr;
  historyIndex = nullptr;
  thresholds = nullptr;
}

VitalsAlertsManager::~VitalsAlertsManager() {
  // Nothing to clean up (we don't own the arrays)
}

void VitalsAlertsManager::init(float* hrHist, float* spo2Hist, float* tempHist,
                                float* bpSysHist, float* bpDiaHist, float* rrHist,
                                int* histIdx, AlertThreshold* thresh) {
  hrHistory = hrHist;
  spo2History = spo2Hist;
  tempHistory = tempHist;
  bpSysHistory = bpSysHist;
  bpDiaHistory = bpDiaHist;
  rrHistory = rrHist;
  historyIndex = histIdx;
  thresholds = thresh;

  Serial.println("✅ VitalsAlertsManager initialized");
}

void VitalsAlertsManager::setPersistence(uint8_t readings) {
  if (readings >= 1 && readings <= 10) {
    vitalAlertPersistence = readings;
    Serial.printf("✅ Alert persistence set to %d readings (~%ds)\n", readings, readings * 5);
  }
}

void VitalsAlertsManager::setFallCooldown(unsigned long milliseconds) {
  fallCooldownDuration = milliseconds;
  Serial.printf("✅ Fall cooldown set to %lu ms\n", milliseconds);
}

void VitalsAlertsManager::triggerFallCooldown() {
  vitalsAlertCooldownUntil = millis() + fallCooldownDuration;
  Serial.printf("🚨 Fall cooldown activated (%lu ms)\n", fallCooldownDuration);
}

bool VitalsAlertsManager::isInCooldown() const {
  return (millis() < vitalsAlertCooldownUntil);
}

uint8_t VitalsAlertsManager::getActiveAlertCount() const {
  uint8_t count = 0;
  if (hrAlertState.alertActive) count++;
  if (spo2AlertState.alertActive) count++;
  if (tempAlertState.alertActive) count++;
  if (bpSysAlertState.alertActive) count++;
  if (bpDiaAlertState.alertActive) count++;
  if (rrAlertState.alertActive) count++;
  return count;
}

void VitalsAlertsManager::resetAllAlerts() {
  hrAlertState.alertActive = false;
  hrAlertState.consecutiveViolations = 0;
  spo2AlertState.alertActive = false;
  spo2AlertState.consecutiveViolations = 0;
  tempAlertState.alertActive = false;
  tempAlertState.consecutiveViolations = 0;
  bpSysAlertState.alertActive = false;
  bpSysAlertState.consecutiveViolations = 0;
  bpDiaAlertState.alertActive = false;
  bpDiaAlertState.consecutiveViolations = 0;
  rrAlertState.alertActive = false;
  rrAlertState.consecutiveViolations = 0;

  Serial.println("✅ All vital alerts reset");
}

void VitalsAlertsManager::setAlertCallback(void (*callback)(const char*, const char*, const char*, float)) {
  alertCallback = callback;
}

void VitalsAlertsManager::setUICallback(void (*callback)(const char*, const char*)) {
  uiCallback = callback;
}

bool VitalsAlertsManager::checkAllVitals(bool isAssigned) {
  if (!isAssigned) return false;
  if (isInCooldown()) return false;

  bool anyAlert = false;

  checkHRAlerts();
  checkSpO2Alerts();
  checkTempAlerts();
  checkBPAlerts();
  checkRRAlerts();

  return anyAlert;
}

// ====================================
// MEDIAN FILTER FUNCTIONS
// ====================================

float VitalsAlertsManager::getMedianHR() {
  if (!hrHistory || !historyIndex) return 0;

  float sorted[3];
  int idx = *historyIndex;
  sorted[0] = hrHistory[idx];
  sorted[1] = hrHistory[(idx + 4) % 5];
  sorted[2] = hrHistory[(idx + 3) % 5];

  // Bubble sort
  for (int i = 0; i < 2; i++) {
    for (int j = 0; j < 2 - i; j++) {
      if (sorted[j] > sorted[j + 1]) {
        float temp = sorted[j];
        sorted[j] = sorted[j + 1];
        sorted[j + 1] = temp;
      }
    }
  }

  return sorted[1];
}

float VitalsAlertsManager::getMedianSpO2() {
  if (!spo2History || !historyIndex) return 0;

  float sorted[3];
  int idx = *historyIndex;
  sorted[0] = spo2History[idx];
  sorted[1] = spo2History[(idx + 4) % 5];
  sorted[2] = spo2History[(idx + 3) % 5];

  for (int i = 0; i < 2; i++) {
    for (int j = 0; j < 2 - i; j++) {
      if (sorted[j] > sorted[j + 1]) {
        float temp = sorted[j];
        sorted[j] = sorted[j + 1];
        sorted[j + 1] = temp;
      }
    }
  }

  return sorted[1];
}

float VitalsAlertsManager::getMedianTemp() {
  if (!tempHistory || !historyIndex) return 0;

  float sorted[3];
  int idx = *historyIndex;
  sorted[0] = tempHistory[idx];
  sorted[1] = tempHistory[(idx + 4) % 5];
  sorted[2] = tempHistory[(idx + 3) % 5];

  for (int i = 0; i < 2; i++) {
    for (int j = 0; j < 2 - i; j++) {
      if (sorted[j] > sorted[j + 1]) {
        float temp = sorted[j];
        sorted[j] = sorted[j + 1];
        sorted[j + 1] = temp;
      }
    }
  }

  return sorted[1];
}

float VitalsAlertsManager::getMedianBPSystolic() {
  if (!bpSysHistory || !historyIndex) return 0;

  float sorted[3];
  int idx = *historyIndex;
  sorted[0] = bpSysHistory[idx];
  sorted[1] = bpSysHistory[(idx + 4) % 5];
  sorted[2] = bpSysHistory[(idx + 3) % 5];

  for (int i = 0; i < 2; i++) {
    for (int j = 0; j < 2 - i; j++) {
      if (sorted[j] > sorted[j + 1]) {
        float temp = sorted[j];
        sorted[j] = sorted[j + 1];
        sorted[j + 1] = temp;
      }
    }
  }

  return sorted[1];
}

float VitalsAlertsManager::getMedianRR() {
  if (!rrHistory || !historyIndex) return 0;

  float sorted[3];
  int idx = *historyIndex;
  sorted[0] = rrHistory[idx];
  sorted[1] = rrHistory[(idx + 4) % 5];
  sorted[2] = rrHistory[(idx + 3) % 5];

  for (int i = 0; i < 2; i++) {
    for (int j = 0; j < 2 - i; j++) {
      if (sorted[j] > sorted[j + 1]) {
        float temp = sorted[j];
        sorted[j] = sorted[j + 1];
        sorted[j + 1] = temp;
      }
    }
  }

  return sorted[1];
}

// ====================================
// HELPER FUNCTION - TRIGGER ALERT
// ====================================

void VitalsAlertsManager::triggerAlert(const char* alertType, const char* severity,
                                        const char* message, float confidence, const char* title) {
  // Call MQTT callback (sendAlert)
  if (alertCallback) {
    alertCallback(alertType, severity, message, confidence);
  }

  // Call UI callback (ui.showAlert)
  if (uiCallback) {
    uiCallback(title, message);
  }
}

// ====================================
// HEART RATE ALERTS
// ====================================

void VitalsAlertsManager::checkHRAlerts() {
  if (!thresholds) return;

  float filteredHR = getMedianHR();

  // CRITICAL Tachycardia (>140 bpm)
  if (filteredHR > 140.0) {
    hrAlertState.consecutiveViolations++;
    if (hrAlertState.consecutiveViolations >= vitalAlertPersistence &&
        (!hrAlertState.alertActive || hrAlertState.currentSeverity < ALERT_CRITICAL)) {

      String msg = "CRITICAL HR - " + String((int)filteredHR) + " bpm";
      triggerAlert("tachycardiaCritical", "high", msg.c_str(), 0.98, "CRITICAL HR");

      hrAlertState.alertActive = true;
      hrAlertState.currentSeverity = ALERT_CRITICAL;
      hrAlertState.hysteresisValue = filteredHR;
      hrAlertState.lastAlertTime = millis();
    }
  }
  // WARNING Tachycardia (120-140 bpm)
  else if (filteredHR > thresholds->hrMax) {
    hrAlertState.consecutiveViolations++;
    if (hrAlertState.consecutiveViolations >= vitalAlertPersistence &&
        (!hrAlertState.alertActive || hrAlertState.currentSeverity < ALERT_WARNING)) {

      String msg = "High HR - " + String((int)filteredHR) + " bpm";
      triggerAlert("tachycardiaWarning", "medium", msg.c_str(), 0.90, "High Heart Rate");

      hrAlertState.alertActive = true;
      hrAlertState.currentSeverity = ALERT_WARNING;
      hrAlertState.hysteresisValue = filteredHR;
      hrAlertState.lastAlertTime = millis();
    }
  }
  // CRITICAL Bradycardia (<30 bpm)
  else if (filteredHR < 30.0 && filteredHR > 0) {
    hrAlertState.consecutiveViolations++;
    if (hrAlertState.consecutiveViolations >= vitalAlertPersistence &&
        (!hrAlertState.alertActive || hrAlertState.currentSeverity < ALERT_CRITICAL)) {

      String msg = "CRITICAL HR - " + String((int)filteredHR) + " bpm";
      triggerAlert("bradycardiaCritical", "high", msg.c_str(), 0.98, "CRITICAL HR");

      hrAlertState.alertActive = true;
      hrAlertState.currentSeverity = ALERT_CRITICAL;
      hrAlertState.hysteresisValue = filteredHR;
      hrAlertState.lastAlertTime = millis();
    }
  }
  // WARNING Bradycardia (30-40 bpm)
  else if (filteredHR < thresholds->hrMin && filteredHR > 0) {
    hrAlertState.consecutiveViolations++;
    if (hrAlertState.consecutiveViolations >= vitalAlertPersistence &&
        (!hrAlertState.alertActive || hrAlertState.currentSeverity < ALERT_WARNING)) {

      String msg = "Low HR - " + String((int)filteredHR) + " bpm";
      triggerAlert("bradycardiaWarning", "medium", msg.c_str(), 0.90, "Low Heart Rate");

      hrAlertState.alertActive = true;
      hrAlertState.currentSeverity = ALERT_WARNING;
      hrAlertState.hysteresisValue = filteredHR;
      hrAlertState.lastAlertTime = millis();
    }
  }
  // Hysteresis: Clear only when 5 bpm away from threshold
  else if (hrAlertState.alertActive) {
    bool shouldClear = false;

    if (filteredHR > thresholds->hrMax && filteredHR < (hrAlertState.hysteresisValue - 5.0)) {
      shouldClear = true;
    } else if (filteredHR < thresholds->hrMin && filteredHR > (hrAlertState.hysteresisValue + 5.0)) {
      shouldClear = true;
    } else if (filteredHR >= thresholds->hrMin && filteredHR <= thresholds->hrMax) {
      shouldClear = true;
    }

    if (shouldClear) {
      hrAlertState.consecutiveViolations = 0;
      hrAlertState.alertActive = false;
      hrAlertState.currentSeverity = ALERT_INFO;
      Serial.println("✅ HR alert cleared (hysteresis)");
    }
  } else {
    hrAlertState.consecutiveViolations = 0;
  }
}

// ====================================
// SPO2 ALERTS
// ====================================

void VitalsAlertsManager::checkSpO2Alerts() {
  if (!thresholds) return;

  float filteredSpO2 = getMedianSpO2();

  // CRITICAL Hypoxia (<85%)
  if (filteredSpO2 < 85.0 && filteredSpO2 > 0) {
    spo2AlertState.consecutiveViolations++;
    if (spo2AlertState.consecutiveViolations >= vitalAlertPersistence &&
        (!spo2AlertState.alertActive || spo2AlertState.currentSeverity < ALERT_CRITICAL)) {

      String msg = "CRITICAL SpO2 - " + String((int)filteredSpO2) + "%";
      triggerAlert("hypoxiaCritical", "high", msg.c_str(), 0.98, "CRITICAL SpO2");

      spo2AlertState.alertActive = true;
      spo2AlertState.currentSeverity = ALERT_CRITICAL;
      spo2AlertState.hysteresisValue = filteredSpO2;
      spo2AlertState.lastAlertTime = millis();
    }
  }
  // WARNING Hypoxia (85-90%)
  else if (filteredSpO2 < thresholds->spo2Min && filteredSpO2 > 0) {
    spo2AlertState.consecutiveViolations++;
    if (spo2AlertState.consecutiveViolations >= vitalAlertPersistence &&
        (!spo2AlertState.alertActive || spo2AlertState.currentSeverity < ALERT_WARNING)) {

      String msg = "Low SpO2 - " + String((int)filteredSpO2) + "%";
      triggerAlert("hypoxiaWarning", "medium", msg.c_str(), 0.90, "Low SpO2");

      spo2AlertState.alertActive = true;
      spo2AlertState.currentSeverity = ALERT_WARNING;
      spo2AlertState.hysteresisValue = filteredSpO2;
      spo2AlertState.lastAlertTime = millis();
    }
  }
  // Hysteresis: Clear when 2% above threshold
  else if (spo2AlertState.alertActive && filteredSpO2 > (spo2AlertState.hysteresisValue + 2.0)) {
    spo2AlertState.consecutiveViolations = 0;
    spo2AlertState.alertActive = false;
    spo2AlertState.currentSeverity = ALERT_INFO;
    Serial.println("✅ SpO2 alert cleared (hysteresis)");
  } else if (!spo2AlertState.alertActive) {
    spo2AlertState.consecutiveViolations = 0;
  }
}

// ====================================
// TEMPERATURE ALERTS
// ====================================

void VitalsAlertsManager::checkTempAlerts() {
  if (!thresholds) return;

  float filteredTemp = getMedianTemp();

  // CRITICAL Fever (>103.1°F / 39.5°C)
  if (filteredTemp > 103.1) {
    tempAlertState.consecutiveViolations++;
    if (tempAlertState.consecutiveViolations >= vitalAlertPersistence &&
        (!tempAlertState.alertActive || tempAlertState.currentSeverity < ALERT_CRITICAL)) {

      String msg = "CRITICAL Temp - " + String(filteredTemp, 1) + "°F";
      triggerAlert("feverCritical", "high", msg.c_str(), 0.98, "CRITICAL Temp");

      tempAlertState.alertActive = true;
      tempAlertState.currentSeverity = ALERT_CRITICAL;
      tempAlertState.hysteresisValue = filteredTemp;
      tempAlertState.lastAlertTime = millis();
    }
  }
  // WARNING Fever (>100.4°F / 38°C)
  else if (filteredTemp > thresholds->tempMax) {
    tempAlertState.consecutiveViolations++;
    if (tempAlertState.consecutiveViolations >= vitalAlertPersistence &&
        (!tempAlertState.alertActive || tempAlertState.currentSeverity < ALERT_WARNING)) {

      String msg = "Fever - " + String(filteredTemp, 1) + "°F";
      triggerAlert("feverWarning", "medium", msg.c_str(), 0.90, "Fever");

      tempAlertState.alertActive = true;
      tempAlertState.currentSeverity = ALERT_WARNING;
      tempAlertState.hysteresisValue = filteredTemp;
      tempAlertState.lastAlertTime = millis();
    }
  }
  // CRITICAL Hypothermia (<95°F / 35°C)
  else if (filteredTemp < thresholds->tempMin) {
    tempAlertState.consecutiveViolations++;
    if (tempAlertState.consecutiveViolations >= vitalAlertPersistence &&
        (!tempAlertState.alertActive || tempAlertState.currentSeverity < ALERT_CRITICAL)) {

      String msg = "CRITICAL Temp - " + String(filteredTemp, 1) + "°F";
      triggerAlert("hypothermiaCritical", "high", msg.c_str(), 0.98, "CRITICAL Temp");

      tempAlertState.alertActive = true;
      tempAlertState.currentSeverity = ALERT_CRITICAL;
      tempAlertState.hysteresisValue = filteredTemp;
      tempAlertState.lastAlertTime = millis();
    }
  }
  // Hysteresis: Clear when 0.9°F away from threshold
  else if (tempAlertState.alertActive) {
    bool shouldClear = false;

    if (filteredTemp > thresholds->tempMax && filteredTemp < (tempAlertState.hysteresisValue - 0.9)) {
      shouldClear = true;
    } else if (filteredTemp < thresholds->tempMin && filteredTemp > (tempAlertState.hysteresisValue + 0.9)) {
      shouldClear = true;
    } else if (filteredTemp >= thresholds->tempMin && filteredTemp <= thresholds->tempMax) {
      shouldClear = true;
    }

    if (shouldClear) {
      tempAlertState.consecutiveViolations = 0;
      tempAlertState.alertActive = false;
      tempAlertState.currentSeverity = ALERT_INFO;
      Serial.println("✅ Temp alert cleared (hysteresis)");
    }
  } else {
    tempAlertState.consecutiveViolations = 0;
  }
}

// ====================================
// BLOOD PRESSURE ALERTS
// ====================================

void VitalsAlertsManager::checkBPAlerts() {
  if (!thresholds || !bpSysHistory || !bpDiaHistory) return;

  float filteredBPSys = getMedianBPSystolic();
  // Note: Could add getMedianBPDiastolic() for diastolic filtering

  // Get current diastolic (not median filtered - could enhance)
  int idx = *historyIndex;
  float bpDia = bpDiaHistory[idx];

  // CRITICAL Hypertension (>160/100)
  if (filteredBPSys > 160.0 || bpDia > 100.0) {
    bpSysAlertState.consecutiveViolations++;
    if (bpSysAlertState.consecutiveViolations >= vitalAlertPersistence &&
        (!bpSysAlertState.alertActive || bpSysAlertState.currentSeverity < ALERT_CRITICAL)) {

      String msg = "CRITICAL BP - " + String((int)filteredBPSys) + "/" + String((int)bpDia);
      triggerAlert("hypertensionCritical", "high", msg.c_str(), 0.98, "CRITICAL BP");

      bpSysAlertState.alertActive = true;
      bpSysAlertState.currentSeverity = ALERT_CRITICAL;
      bpSysAlertState.hysteresisValue = filteredBPSys;
      bpSysAlertState.lastAlertTime = millis();
    }
  }
  // WARNING Hypertension (>140/90)
  else if (filteredBPSys > thresholds->bpSysMax || bpDia > thresholds->bpDiaMax) {
    bpSysAlertState.consecutiveViolations++;
    if (bpSysAlertState.consecutiveViolations >= vitalAlertPersistence &&
        (!bpSysAlertState.alertActive || bpSysAlertState.currentSeverity < ALERT_WARNING)) {

      String msg = "High BP - " + String((int)filteredBPSys) + "/" + String((int)bpDia);
      triggerAlert("hypertensionWarning", "medium", msg.c_str(), 0.90, "High BP");

      bpSysAlertState.alertActive = true;
      bpSysAlertState.currentSeverity = ALERT_WARNING;
      bpSysAlertState.hysteresisValue = filteredBPSys;
      bpSysAlertState.lastAlertTime = millis();
    }
  }
  // CRITICAL Hypotension (<70/40)
  else if (filteredBPSys < 70.0 || bpDia < 40.0) {
    bpSysAlertState.consecutiveViolations++;
    if (bpSysAlertState.consecutiveViolations >= vitalAlertPersistence &&
        (!bpSysAlertState.alertActive || bpSysAlertState.currentSeverity < ALERT_CRITICAL)) {

      String msg = "CRITICAL BP - " + String((int)filteredBPSys) + "/" + String((int)bpDia);
      triggerAlert("hypotensionCritical", "high", msg.c_str(), 0.98, "CRITICAL BP");

      bpSysAlertState.alertActive = true;
      bpSysAlertState.currentSeverity = ALERT_CRITICAL;
      bpSysAlertState.hysteresisValue = filteredBPSys;
      bpSysAlertState.lastAlertTime = millis();
    }
  }
  // WARNING Hypotension (<90/60)
  else if (filteredBPSys < thresholds->bpSysMin || bpDia < thresholds->bpDiaMin) {
    bpSysAlertState.consecutiveViolations++;
    if (bpSysAlertState.consecutiveViolations >= vitalAlertPersistence &&
        (!bpSysAlertState.alertActive || bpSysAlertState.currentSeverity < ALERT_WARNING)) {

      String msg = "Low BP - " + String((int)filteredBPSys) + "/" + String((int)bpDia);
      triggerAlert("hypotensionWarning", "medium", msg.c_str(), 0.90, "Low BP");

      bpSysAlertState.alertActive = true;
      bpSysAlertState.currentSeverity = ALERT_WARNING;
      bpSysAlertState.hysteresisValue = filteredBPSys;
      bpSysAlertState.lastAlertTime = millis();
    }
  }
  // Hysteresis: Clear when 10 mmHg away from threshold
  else if (bpSysAlertState.alertActive) {
    bool shouldClear = false;

    if (filteredBPSys > thresholds->bpSysMax && filteredBPSys < (bpSysAlertState.hysteresisValue - 10.0)) {
      shouldClear = true;
    } else if (filteredBPSys < thresholds->bpSysMin && filteredBPSys > (bpSysAlertState.hysteresisValue + 10.0)) {
      shouldClear = true;
    } else if (filteredBPSys >= thresholds->bpSysMin && filteredBPSys <= thresholds->bpSysMax &&
               bpDia >= thresholds->bpDiaMin && bpDia <= thresholds->bpDiaMax) {
      shouldClear = true;
    }

    if (shouldClear) {
      bpSysAlertState.consecutiveViolations = 0;
      bpSysAlertState.alertActive = false;
      bpSysAlertState.currentSeverity = ALERT_INFO;
      Serial.println("✅ BP alert cleared (hysteresis)");
    }
  } else {
    bpSysAlertState.consecutiveViolations = 0;
  }
}

// ====================================
// RESPIRATORY RATE ALERTS
// ====================================

void VitalsAlertsManager::checkRRAlerts() {
  if (!thresholds) return;

  float filteredRR = getMedianRR();

  // CRITICAL Tachypnea (>30 breaths/min)
  if (filteredRR > 30.0) {
    rrAlertState.consecutiveViolations++;
    if (rrAlertState.consecutiveViolations >= vitalAlertPersistence &&
        (!rrAlertState.alertActive || rrAlertState.currentSeverity < ALERT_CRITICAL)) {

      String msg = "CRITICAL RR - " + String((int)filteredRR) + " br/min";
      triggerAlert("tachypneaCritical", "high", msg.c_str(), 0.98, "CRITICAL RR");

      rrAlertState.alertActive = true;
      rrAlertState.currentSeverity = ALERT_CRITICAL;
      rrAlertState.hysteresisValue = filteredRR;
      rrAlertState.lastAlertTime = millis();
    }
  }
  // WARNING Tachypnea (>20 breaths/min)
  else if (filteredRR > thresholds->rrMax) {
    rrAlertState.consecutiveViolations++;
    if (rrAlertState.consecutiveViolations >= vitalAlertPersistence &&
        (!rrAlertState.alertActive || rrAlertState.currentSeverity < ALERT_WARNING)) {

      String msg = "High RR - " + String((int)filteredRR) + " br/min";
      triggerAlert("tachypneaWarning", "medium", msg.c_str(), 0.90, "High RR");

      rrAlertState.alertActive = true;
      rrAlertState.currentSeverity = ALERT_WARNING;
      rrAlertState.hysteresisValue = filteredRR;
      rrAlertState.lastAlertTime = millis();
    }
  }
  // CRITICAL Bradypnea (<8 breaths/min)
  else if (filteredRR < 8.0 && filteredRR > 0) {
    rrAlertState.consecutiveViolations++;
    if (rrAlertState.consecutiveViolations >= vitalAlertPersistence &&
        (!rrAlertState.alertActive || rrAlertState.currentSeverity < ALERT_CRITICAL)) {

      String msg = "CRITICAL RR - " + String((int)filteredRR) + " br/min";
      triggerAlert("bradypneaCritical", "high", msg.c_str(), 0.98, "CRITICAL RR");

      rrAlertState.alertActive = true;
      rrAlertState.currentSeverity = ALERT_CRITICAL;
      rrAlertState.hysteresisValue = filteredRR;
      rrAlertState.lastAlertTime = millis();
    }
  }
  // WARNING Bradypnea (<12 breaths/min)
  else if (filteredRR < thresholds->rrMin && filteredRR > 0) {
    rrAlertState.consecutiveViolations++;
    if (rrAlertState.consecutiveViolations >= vitalAlertPersistence &&
        (!rrAlertState.alertActive || rrAlertState.currentSeverity < ALERT_WARNING)) {

      String msg = "Low RR - " + String((int)filteredRR) + " br/min";
      triggerAlert("bradypneaWarning", "medium", msg.c_str(), 0.90, "Low RR");

      rrAlertState.alertActive = true;
      rrAlertState.currentSeverity = ALERT_WARNING;
      rrAlertState.hysteresisValue = filteredRR;
      rrAlertState.lastAlertTime = millis();
    }
  }
  // Hysteresis: Clear when 2 breaths/min away from threshold
  else if (rrAlertState.alertActive) {
    bool shouldClear = false;

    if (filteredRR > thresholds->rrMax && filteredRR < (rrAlertState.hysteresisValue - 2.0)) {
      shouldClear = true;
    } else if (filteredRR < thresholds->rrMin && filteredRR > (rrAlertState.hysteresisValue + 2.0)) {
      shouldClear = true;
    } else if (filteredRR >= thresholds->rrMin && filteredRR <= thresholds->rrMax) {
      shouldClear = true;
    }

    if (shouldClear) {
      rrAlertState.consecutiveViolations = 0;
      rrAlertState.alertActive = false;
      rrAlertState.currentSeverity = ALERT_INFO;
      Serial.println("✅ RR alert cleared (hysteresis)");
    }
  } else {
    rrAlertState.consecutiveViolations = 0;
  }
}
