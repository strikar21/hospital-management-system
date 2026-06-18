/**
 * VitalsCards.h
 * Hospital Watch - Vital Signs Cards Component
 * REDESIGNED: Single static 2×2 grid - NO SCROLLING (per reference image)
 *
 * Displays 4 primary vital sign cards in a 2×2 grid:
 * - Top row: Heart Rate, SpO2
 * - Bottom row: Blood Pressure, Temperature
 *
 * Features:
 * - NO scrolling/swiping - static single page
 * - Dark theme with colored left accent bars
 * - Large readable fonts (28px for values)
 * - Matches reference image layout exactly
 *
 * Layout:
 * - Total height: 218px (per reference: Status:24px + Patient:32px + Vitals:218px + ECG:182px = 456px)
 * - Position: Below patient bar (Y=56px, after 24px status + 32px patient)
 * - 2 rows × 2 columns (4 cards total - PRIMARY VITALS ONLY)
 *
 * Author: Design Team
 * Date: 2025-11-24
 */

#ifndef VITALS_CARDS_H
#define VITALS_CARDS_H

#include <Arduino.h>
#include <lvgl.h>

// Simplified enum - only 4 primary vitals (Page 2/3 removed)
enum VitalType {
    VITAL_HEART_RATE = 0,
    VITAL_BLOOD_PRESSURE = 1,
    VITAL_SPO2 = 2,
    VITAL_TEMPERATURE = 3
};

class VitalsCards {
public:
    /**
     * Constructor
     */
    VitalsCards();

    /**
     * Destructor
     */
    ~VitalsCards();

    /**
     * Create vitals cards container on parent screen
     * @param parent Parent LVGL screen object
     * @param eventCallback Event callback for card clicks (optional)
     * @param userData User data to pass to callback (optional)
     * @return Vitals container object
     */
    lv_obj_t* create(lv_obj_t* parent, lv_event_cb_t eventCallback = nullptr, void* userData = nullptr);

    /**
     * Update heart rate value
     * @param hr Heart rate in BPM
     */
    void updateHeartRate(float hr);

    /**
     * Update SpO2 value
     * @param spo2 SpO2 percentage
     */
    void updateSpO2(float spo2);

    /**
     * Update blood pressure values
     * @param systolic Systolic pressure (mmHg)
     * @param diastolic Diastolic pressure (mmHg)
     */
    void updateBloodPressure(float systolic, float diastolic);

    /**
     * Update temperature value
     * @param temp Temperature in °C
     */
    void updateTemperature(float temp);

    /**
     * Update respiratory rate (stub - not displayed)
     * @param rr Respiratory rate (breaths/min)
     */
    void updateRespiratoryRate(float rr);

    /**
     * Update fall risk score (stub - not displayed)
     * @param risk Fall risk score (0-10)
     */
    void updateFallRisk(float risk);

    /**
     * Update perfusion percentage (stub - not displayed)
     * @param perfusion Perfusion (%)
     */
    void updatePerfusion(float perfusion);

    /**
     * Update bioimpedance (stub - not displayed)
     * @param impedance Bioimpedance (Ω)
     */
    void updateBioimpedance(float impedance);

    /**
     * Update tremor score (stub - not displayed)
     * @param tremor Tremor score (0-10)
     */
    void updateTremor(float tremor);

    /**
     * Update step count (stub - not displayed)
     * @param steps Step count
     */
    void updateSteps(int steps);

    /**
     * Update watch status indicator (stub - not displayed)
     * @param status Status string (e.g., "Connected", "Offline")
     */
    void updateWatchStatus(const char* status);

    /**
     * Update ECG/EEG mode indicator (stub - not displayed)
     * @param mode Mode string ("ECG" or "EEG")
     */
    void updateMode(const char* mode);

    /**
     * Update all Page 1 vitals at once
     * @param hr Heart rate (BPM)
     * @param spo2 SpO2 (%)
     * @param temp Temperature (°C)
     * @param bpSys Systolic BP (mmHg)
     * @param bpDia Diastolic BP (mmHg)
     */
    void updateAll(float hr, float spo2, float temp, float bpSys, float bpDia);

    /**
     * Update all vitals (stub for compatibility)
     * @param hr Heart rate (BPM)
     * @param spo2 SpO2 (%)
     * @param temp Temperature (°C)
     * @param bpSys Systolic BP (mmHg)
     * @param bpDia Diastolic BP (mmHg)
     * @param rr Respiratory Rate (breaths/min)
     */
    void updateAllPages(float hr, float spo2, float temp, float bpSys, float bpDia, float rr);

    /**
     * Get vitals container object
     * @return LVGL object pointer
     */
    lv_obj_t* getContainer() const;

    /**
     * Get specific vital card object
     * @param type Vital type
     * @return LVGL card object pointer
     */
    lv_obj_t* getCard(VitalType type) const;

    /**
     * Get current page index (always returns 0 - single page only)
     * @return Current page index
     */
    uint8_t getCurrentPage() const;

    /**
     * Set current page (stub - single page only)
     * @param pageIndex Page index (ignored)
     */
    void setPage(uint8_t pageIndex);

    /**
     * Check if vitals cards are initialized
     * @return true if initialized, false otherwise
     */
    bool isInitialized() const;

private:
    lv_obj_t* container;      // Main container (NO tileview)
    lv_obj_t* tileview;       // Unused (kept for compatibility)
    lv_obj_t* page1;          // Unused (kept for compatibility)
    lv_obj_t* page2;          // Unused (kept for compatibility)
    lv_obj_t* page3;          // Unused (kept for compatibility)
    lv_obj_t* pageIndicator;  // Unused (kept for compatibility)

    // Primary vitals cards (ONLY these 4 are displayed)
    lv_obj_t* hrBox;          // Heart rate
    lv_obj_t* bpBox;          // Blood pressure
    lv_obj_t* spo2Box;        // SpO2
    lv_obj_t* tempBox;        // Temperature

    // Page 2/3 cards (unused - kept for compatibility)
    lv_obj_t* rrBox;          // Respiratory rate
    lv_obj_t* fallRiskBox;    // Fall risk
    lv_obj_t* perfusionBox;   // Perfusion
    lv_obj_t* bioimpBox;      // Bioimpedance
    lv_obj_t* tremorBox;      // Tremor
    lv_obj_t* stepsBox;       // Steps
    lv_obj_t* statusBox;      // Watch status
    lv_obj_t* modeBox;        // ECG/EEG mode

    // Value labels - primary vitals
    lv_obj_t* labelHR;
    lv_obj_t* labelBP;
    lv_obj_t* labelSpO2;
    lv_obj_t* labelTemp;

    // Value labels - page 2/3 (unused - kept for compatibility)
    lv_obj_t* labelRR;
    lv_obj_t* labelFallRisk;
    lv_obj_t* labelPerfusion;
    lv_obj_t* labelBioimp;
    lv_obj_t* labelTremor;
    lv_obj_t* labelSteps;
    lv_obj_t* labelStatus;
    lv_obj_t* labelMode;

    bool initialized;
    uint8_t currentPage;

    // Constants - Updated Layout (Status:30px + Patient:40px + Vitals:170px + ECG:216px = 456px)
    static const uint16_t HEIGHT = 170;  // Total vitals area height (reduced from 204px)
    static const uint16_t Y_POSITION = 70;  // Below patient bar (30+40)
    static const uint16_t CARD_WIDTH = 130;
    static const uint16_t CARD_HEIGHT = 76;  // Reduced from 93px to fit new layout (5+76+8+76+5=170)
    static const uint16_t CARD_SPACING = 8;
    static const uint16_t ROW_SPACING = 8;

    // Note: per-vital accent colors are provided by MedicalTheme (VITAL_*)

    /**
     * Create a single vital card
     * @param parent Parent container
     * @param title Card title text
     * @param accentColor Accent color for the card (use MedicalTheme::VITAL_*)
     * @param x X position
     * @param y Y position
     * @param labelPtr Pointer to store created label
     * @param eventCallback Event callback for clicks
     * @param userData User data for callback
     * @return Created card object
     */
    lv_obj_t* createCard(lv_obj_t* parent, const char* title, lv_color_t accentColor,
                         int16_t x, int16_t y, lv_obj_t** labelPtr,
                         lv_event_cb_t eventCallback, void* userData);

    /**
     * Create page indicator dots (stub - not used)
     * @param parent Parent object
     * @return Indicator object
     */
    lv_obj_t* createPageIndicator(lv_obj_t* parent);

    /**
     * Update page indicator dots (stub - not used)
     * @param activePage Active page index
     */
    void updatePageIndicator(uint8_t activePage);

    /**
     * Static callback for tileview scroll events (stub - not used)
     */
    static void tileviewScrollCallback(lv_event_t* e);
};

#endif // VITALS_CARDS_H
