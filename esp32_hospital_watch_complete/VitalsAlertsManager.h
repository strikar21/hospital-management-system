/**
 * VitalsAlertsManager.h
 * Hospital Watch - Vital Signs Alert Management
 *
 * Monitors vital signs and triggers alerts when thresholds are exceeded:
 * - Heart Rate (Bradycardia/Tachycardia)
 * - SpO2 (Hypoxia)
 * - Temperature (Fever/Hypothermia)
 * - Blood Pressure (Hyper/Hypotension)
 * - Respiratory Rate (Tachypnea/Bradypnea)
 *
 * Features:
 * - 3-tier severity (INFO/WARNING/CRITICAL)
 * - Hysteresis (prevents boundary oscillation)
 * - Persistence window (filters transient spikes)
 * - Median filtering (noise immunity)
 * - Post-fall suppression (30s cooldown)
 *
 * Author: Expert Team Analysis
 * Date: 2025-11-22
 * Version: 5.5.0
 */

#ifndef VITALS_ALERTS_MANAGER_H
#define VITALS_ALERTS_MANAGER_H

#include <Arduino.h>
#include "AlertPopup.h"

// Alert state for each vital sign
struct VitalAlertState {
  bool alertActive;              // Is alert currently showing?
  uint8_t consecutiveViolations; // Count for persistence window
  unsigned long lastAlertTime;   // For rate limiting
  float hysteresisValue;         // Value when state changed
  AlertSeverity currentSeverity; // Current alert level (INFO/WARNING/CRITICAL)
};

// Alert thresholds structure
struct AlertThreshold {
  float hrMin;
  float hrMax;
  float spo2Min;
  float spo2Max;  // Note: Not used (100% is normal)
  float tempMin;
  float tempMax;
  float bpSysMin;
  float bpSysMax;
  float bpDiaMin;
  float bpDiaMax;
  float rrMin;
  float rrMax;
};

class VitalsAlertsManager {
public:
  /**
   * Constructor
   */
  VitalsAlertsManager();

  /**
   * Destructor
   */
  ~VitalsAlertsManager();

  /**
   * Initialize alert manager with vital history arrays and thresholds
   * @param hrHistory Pointer to heart rate history array [5]
   * @param spo2History Pointer to SpO2 history array [5]
   * @param tempHistory Pointer to temperature history array [5]
   * @param bpSysHistory Pointer to systolic BP history array [5]
   * @param bpDiaHistory Pointer to diastolic BP history array [5]
   * @param rrHistory Pointer to respiratory rate history array [5]
   * @param histIdx Pointer to history index variable
   * @param thresholds Pointer to AlertThreshold struct
   */
  void init(float* hrHistory, float* spo2History, float* tempHistory,
            float* bpSysHistory, float* bpDiaHistory, float* rrHistory,
            int* histIdx, AlertThreshold* thresholds);

  /**
   * Check all vital signs for threshold violations
   * Call this every 5 seconds (vitals transmission interval)
   * @param isAssigned Is device assigned to patient?
   * @return true if any alert was triggered
   */
  bool checkAllVitals(bool isAssigned);

  /**
   * Set persistence window (number of consecutive violations required)
   * @param readings Number of readings (1-10), default 3 = 15 seconds at 5s interval
   */
  void setPersistence(uint8_t readings);

  /**
   * Set post-fall cooldown time
   * @param milliseconds Cooldown duration (default 30000 = 30s)
   */
  void setFallCooldown(unsigned long milliseconds);

  /**
   * Trigger post-fall cooldown (suppress vitals alerts temporarily)
   * Call this when fall alert is cleared
   */
  void triggerFallCooldown();

  /**
   * Check if vitals alerts are currently suppressed (cooldown active)
   * @return true if in cooldown period
   */
  bool isInCooldown() const;

  /**
   * Get number of active alerts
   * @return Count of currently active alerts
   */
  uint8_t getActiveAlertCount() const;

  /**
   * Reset all alert states (clear all active alerts)
   */
  void resetAllAlerts();

  /**
   * Set alert callback function
   * @param callback Function to call when alert triggers: void callback(const char* alertType, const char* severity, const char* message, float confidence)
   */
  void setAlertCallback(void (*callback)(const char*, const char*, const char*, float));

  /**
   * Set UI alert callback function (for showing on screen)
   * @param callback Function to call for UI display: void callback(const char* title, const char* message)
   */
  void setUICallback(void (*callback)(const char*, const char*));

private:
  // Vital history arrays (pointers to main .ino arrays)
  float* hrHistory;
  float* spo2History;
  float* tempHistory;
  float* bpSysHistory;
  float* bpDiaHistory;
  float* rrHistory;
  int* historyIndex;

  // Alert thresholds (pointer to main .ino struct)
  AlertThreshold* thresholds;

  // Alert states
  VitalAlertState hrAlertState;
  VitalAlertState spo2AlertState;
  VitalAlertState tempAlertState;
  VitalAlertState bpSysAlertState;
  VitalAlertState bpDiaAlertState;
  VitalAlertState rrAlertState;

  // Configuration
  uint8_t vitalAlertPersistence;       // Consecutive readings required
  unsigned long vitalsAlertCooldownUntil; // Timestamp when cooldown ends
  unsigned long fallCooldownDuration;   // Duration of post-fall cooldown

  // Callbacks
  void (*alertCallback)(const char*, const char*, const char*, float);
  void (*uiCallback)(const char*, const char*);

  // Median filter functions
  float getMedianHR();
  float getMedianSpO2();
  float getMedianTemp();
  float getMedianBPSystolic();
  float getMedianRR();

  // Individual vital check functions
  void checkHRAlerts();
  void checkSpO2Alerts();
  void checkTempAlerts();
  void checkBPAlerts();
  void checkRRAlerts();

  // Helper function to trigger alert (calls both callbacks)
  void triggerAlert(const char* alertType, const char* severity, const char* message,
                    float confidence, const char* title);
};

#endif // VITALS_ALERTS_MANAGER_H
