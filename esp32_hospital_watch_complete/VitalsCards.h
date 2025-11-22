/**
 * VitalsCards.h
 * Hospital Watch - Vital Signs Cards Component
 *
 * Displays 4 vital sign cards in a 2×2 grid:
 * - Heart Rate (HR) - Red border, clickable
 * - SpO2 - Blue border, clickable
 * - Blood Pressure (BP) - Purple border, clickable
 * - Temperature - Green border, clickable
 *
 * Layout:
 * - Total height: 146px
 * - Position: Below patient bar (Y=70)
 * - 2 rows × 2 columns
 * - White background, black text, colored borders
 *
 * Author: Claude/Anthropic
 * Date: 2025-11-22
 */

#ifndef VITALS_CARDS_H
#define VITALS_CARDS_H

#include <Arduino.h>
#include <lvgl.h>

enum VitalType {
    VITAL_HEART_RATE = 0,
    VITAL_SPO2 = 1,
    VITAL_BLOOD_PRESSURE = 2,
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
     * Update all vitals at once
     * @param hr Heart rate (BPM)
     * @param spo2 SpO2 (%)
     * @param temp Temperature (°C)
     * @param bpSys Systolic BP (mmHg)
     * @param bpDia Diastolic BP (mmHg)
     */
    void updateAll(float hr, float spo2, float temp, float bpSys, float bpDia);

    /**
     * Get vitals container object
     * @return LVGL object pointer
     */
    lv_obj_t* getContainer() const;

    /**
     * Get specific vital card object
     * @param type Vital type (HR/SpO2/BP/Temp)
     * @return LVGL card object pointer
     */
    lv_obj_t* getCard(VitalType type) const;

    /**
     * Check if vitals cards are initialized
     * @return true if initialized, false otherwise
     */
    bool isInitialized() const;

private:
    lv_obj_t* container;      // Vitals container
    lv_obj_t* hrBox;          // Heart rate card
    lv_obj_t* spo2Box;        // SpO2 card
    lv_obj_t* bpBox;          // Blood pressure card
    lv_obj_t* tempBox;        // Temperature card

    lv_obj_t* labelHR;        // HR value label
    lv_obj_t* labelSpO2;      // SpO2 value label
    lv_obj_t* labelBP;        // BP value label
    lv_obj_t* labelTemp;      // Temp value label

    bool initialized;

    // Constants
    static const uint16_t HEIGHT = 146;
    static const uint16_t Y_POSITION = 70;  // Below patient bar (35+35)
    static const uint16_t CARD_WIDTH = 130;
    static const uint16_t CARD_HEIGHT = 65;
    static const uint16_t CARD_SPACING = 8;
    static const uint16_t ROW_SPACING = 8;

    // Colors
    static const uint32_t COLOR_HR = 0xFF0000;      // Red
    static const uint32_t COLOR_SPO2 = 0x0000FF;    // Blue
    static const uint32_t COLOR_BP = 0x9B59B6;      // Purple
    static const uint32_t COLOR_TEMP = 0x00FF00;    // Green

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
};

#endif // VITALS_CARDS_H
