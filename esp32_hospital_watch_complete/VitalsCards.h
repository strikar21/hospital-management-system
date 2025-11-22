/**
 * VitalsCards.h
 * Hospital Watch - Vital Signs Cards Component (Swipeable 3-Page Layout)
 *
 * Displays vital sign cards in horizontally swipeable pages (2×2 grid per page):
 * - Page 1: Heart Rate, Blood Pressure, Oxygen Sat, Temperature
 * - Page 2: Respiratory Rate, Fall Risk, Perfusion, Bioimpedance
 * - Page 3: Tremor, Steps, Watch Status, ECG/EEG Mode
 *
 * Features:
 * - Swipe left/right to navigate 3 pages
 * - Page indicator dots at bottom (● ○ ○ or ○ ● ○ or ○ ○ ●)
 * - Colored borders for quick visual reference
 * - 2×2 grid maintains readability on 1.64" AMOLED display
 *
 * Layout:
 * - Total height: 164px (146px cards + 18px indicators)
 * - Position: Below patient bar (Y=70)
 * - 2 rows × 2 columns per page (4 cards per page, 12 total)
 *
 * Author: Claude/Anthropic
 * Date: 2025-11-23
 */

#ifndef VITALS_CARDS_H
#define VITALS_CARDS_H

#include <Arduino.h>
#include <lvgl.h>

enum VitalType {
    // Page 1 - Primary Vitals
    VITAL_HEART_RATE = 0,
    VITAL_BLOOD_PRESSURE = 1,
    VITAL_SPO2 = 2,
    VITAL_TEMPERATURE = 3,
    // Page 2 - Respiratory & Risk
    VITAL_RESPIRATORY_RATE = 4,
    VITAL_FALL_RISK = 5,
    VITAL_PERFUSION = 6,
    VITAL_BIOIMPEDANCE = 7,
    // Page 3 - Activity & Status
    VITAL_TREMOR = 8,
    VITAL_STEPS = 9,
    VITAL_WATCH_STATUS = 10,
    VITAL_MODE = 11
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
     * Update respiratory rate (Page 2)
     * @param rr Respiratory rate (breaths/min)
     */
    void updateRespiratoryRate(float rr);

    /**
     * Update fall risk score (Page 2)
     * @param risk Fall risk score (0-10)
     */
    void updateFallRisk(float risk);

    /**
     * Update perfusion percentage (Page 2)
     * @param perfusion Perfusion (%)
     */
    void updatePerfusion(float perfusion);

    /**
     * Update bioimpedance (Page 2)
     * @param impedance Bioimpedance (Ω)
     */
    void updateBioimpedance(float impedance);

    /**
     * Update tremor score (Page 3)
     * @param tremor Tremor score (0-10)
     */
    void updateTremor(float tremor);

    /**
     * Update step count (Page 3)
     * @param steps Step count
     */
    void updateSteps(int steps);

    /**
     * Update watch status indicator (Page 3)
     * @param status Status string (e.g., "Connected", "Offline")
     */
    void updateWatchStatus(const char* status);

    /**
     * Update ECG/EEG mode indicator (Page 3)
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
     * Update all vitals including Page 2
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
     * Get current page index (0 = Page 1, 1 = Page 2, 2 = Page 3)
     * @return Current page index
     */
    uint8_t getCurrentPage() const;

    /**
     * Set current page (programmatic navigation)
     * @param pageIndex Page index (0, 1, or 2)
     */
    void setPage(uint8_t pageIndex);

    /**
     * Check if vitals cards are initialized
     * @return true if initialized, false otherwise
     */
    bool isInitialized() const;

private:
    lv_obj_t* container;      // Main container with tileview
    lv_obj_t* tileview;       // Tileview for swipeable pages
    lv_obj_t* page1;          // Page 1 tile
    lv_obj_t* page2;          // Page 2 tile
    lv_obj_t* page3;          // Page 3 tile
    lv_obj_t* pageIndicator;  // Page dots indicator

    // Page 1 cards (Primary Vitals)
    lv_obj_t* hrBox;          // Heart rate
    lv_obj_t* bpBox;          // Blood pressure
    lv_obj_t* spo2Box;        // SpO2
    lv_obj_t* tempBox;        // Temperature

    // Page 2 cards (Respiratory & Risk)
    lv_obj_t* rrBox;          // Respiratory rate
    lv_obj_t* fallRiskBox;    // Fall risk
    lv_obj_t* perfusionBox;   // Perfusion
    lv_obj_t* bioimpBox;      // Bioimpedance

    // Page 3 cards (Activity & Status)
    lv_obj_t* tremorBox;      // Tremor
    lv_obj_t* stepsBox;       // Steps
    lv_obj_t* statusBox;      // Watch status
    lv_obj_t* modeBox;        // ECG/EEG mode

    // Value labels Page 1
    lv_obj_t* labelHR;
    lv_obj_t* labelBP;
    lv_obj_t* labelSpO2;
    lv_obj_t* labelTemp;

    // Value labels Page 2
    lv_obj_t* labelRR;
    lv_obj_t* labelFallRisk;
    lv_obj_t* labelPerfusion;
    lv_obj_t* labelBioimp;

    // Value labels Page 3
    lv_obj_t* labelTremor;
    lv_obj_t* labelSteps;
    lv_obj_t* labelStatus;
    lv_obj_t* labelMode;

    bool initialized;
    uint8_t currentPage;

    // Constants
    static const uint16_t HEIGHT = 164;  // Increased for page indicators
    static const uint16_t Y_POSITION = 70;  // Below patient bar (35+35)
    static const uint16_t CARD_WIDTH = 130;
    static const uint16_t CARD_HEIGHT = 65;
    static const uint16_t CARD_SPACING = 8;
    static const uint16_t ROW_SPACING = 8;

    // Colors - Page 1 (Primary Vitals)
    static const uint32_t COLOR_HR = 0xFF0000;        // Red
    static const uint32_t COLOR_BP = 0x9B59B6;        // Purple
    static const uint32_t COLOR_SPO2 = 0x0000FF;      // Blue
    static const uint32_t COLOR_TEMP = 0x00FF00;      // Green

    // Colors - Page 2 (Respiratory & Risk)
    static const uint32_t COLOR_RR = 0xFF8C00;        // Dark Orange
    static const uint32_t COLOR_FALL = 0xFFD700;      // Gold
    static const uint32_t COLOR_PERFUSION = 0xFF1493; // Deep Pink
    static const uint32_t COLOR_BIOIMP = 0x1E90FF;    // Dodger Blue

    // Colors - Page 3 (Activity & Status)
    static const uint32_t COLOR_TREMOR = 0x32CD32;    // Lime Green
    static const uint32_t COLOR_STEPS = 0x00CED1;     // Dark Turquoise
    static const uint32_t COLOR_STATUS = 0x808080;    // Gray
    static const uint32_t COLOR_MODE = 0xDA70D6;      // Orchid

    /**
     * Create a single vital card
     * @param parent Parent container
     * @param title Card title text
     * @param borderColor Border color hex
     * @param x X position
     * @param y Y position
     * @param labelPtr Pointer to store created label
     * @param eventCallback Event callback for clicks
     * @param userData User data for callback
     * @return Created card object
     */
    lv_obj_t* createCard(lv_obj_t* parent, const char* title, uint32_t borderColor,
                         int16_t x, int16_t y, lv_obj_t** labelPtr,
                         lv_event_cb_t eventCallback, void* userData);

    /**
     * Create page indicator dots
     * @param parent Parent object
     * @return Indicator object
     */
    lv_obj_t* createPageIndicator(lv_obj_t* parent);

    /**
     * Update page indicator dots
     * @param activePage Active page index (0 or 1)
     */
    void updatePageIndicator(uint8_t activePage);

    /**
     * Static callback for tileview scroll events
     */
    static void tileviewScrollCallback(lv_event_t* e);
};

#endif // VITALS_CARDS_H
