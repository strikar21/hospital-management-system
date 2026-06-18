/**
 * StatusBar.h
 * Hospital Watch - Top Status Bar Component
 *
 * Displays:
 * - Current time (HH:MM)
 * - WiFi connection status icon
 * - Battery level icon and percentage
 *
 * Height: 35px
 * Background: Magenta (#E91E63)
 *
 * Author: Claude/Anthropic
 * Date: 2025-11-22
 */

#ifndef STATUS_BAR_H
#define STATUS_BAR_H

#include <Arduino.h>
#include <lvgl.h>
#include "MedicalTheme.h"

class StatusBar {
public:
    /**
     * Constructor
     */
    StatusBar();

    /**
     * Destructor
     */
    ~StatusBar();

    /**
     * Create status bar on parent screen
     * @param parent Parent LVGL screen object
     * @return Status bar container object
     */
    lv_obj_t* create(lv_obj_t* parent);

    /**
     * Update time display
     * @param timeStr Time string in format "HH:MM"
     */
    void updateTime(const char* timeStr);

    /**
     * Update WiFi connection status
     * @param connected true if WiFi connected, false otherwise
     */
    void updateWiFi(bool connected);

    /**
     * Update battery level
     * @param percent Battery percentage (0-100)
     */
    void updateBattery(uint8_t percent);

    /**
     * Get status bar container object
     * @return LVGL object pointer
     */
    lv_obj_t* getContainer() const;

    /**
     * Check if status bar is initialized
     * @return true if initialized, false otherwise
     */
    bool isInitialized() const;

private:
    lv_obj_t* container;         // Status bar container
    lv_obj_t* labelTime;         // Time label (HH:MM)
    lv_obj_t* iconWiFi;          // WiFi icon
    lv_obj_t* iconBattery;       // Battery icon
    lv_obj_t* labelBatteryPercent; // Battery percentage label

    bool initialized;

    // Constants
    static const uint16_t HEIGHT = 30;
    // Use `MedicalTheme::BG_BLACK` at runtime when styling the object; no in-class lv_color_t constant here.
};

#endif // STATUS_BAR_H
