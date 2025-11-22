/**
 * AlertPopup.h
 * Hospital Watch - Alert Popup Overlay Component
 *
 * Displays critical alerts as popup overlay (does NOT hijack status bar)
 * - Appears centered on screen with drop shadow
 * - Color-coded by severity (red/orange/blue)
 * - Clickable to dismiss
 * - Semi-transparent background
 *
 * Size: 260×80px
 * Position: Centered, slightly above middle
 *
 * Author: Claude/Anthropic
 * Date: 2025-11-22
 */

#ifndef ALERT_POPUP_H
#define ALERT_POPUP_H

#include <Arduino.h>
#include <lvgl.h>

enum AlertSeverity { ALERT_INFO = 0, ALERT_WARNING = 1, ALERT_CRITICAL = 2 };

class AlertPopup {
public:
    /**
     * Constructor
     */
    AlertPopup();

    /**
     * Destructor
     */
    ~AlertPopup();

    /**
     * Create alert popup overlay on active screen
     * @param eventCallback Event callback for popup clicks (optional)
     * @param userData User data to pass to callback (optional)
     * @return Alert popup container object
     */
    lv_obj_t* create(lv_event_cb_t eventCallback = nullptr, void* userData = nullptr);

    /**
     * Show alert popup with message and severity
     * @param message Alert message text
     * @param severity Alert severity (CRITICAL/WARNING/INFO)
     */
    void show(const char* message, AlertSeverity severity = ALERT_CRITICAL);

    /**
     * Hide alert popup
     */
    void hide();

    /**
     * Check if popup is currently visible
     * @return true if visible, false if hidden
     */
    bool isVisible() const;

    /**
     * Get alert popup container object
     * @return LVGL object pointer
     */
    lv_obj_t* getContainer() const;

    /**
     * Get alert text label object (for direct manipulation)
     * @return LVGL label object pointer
     */
    lv_obj_t* getTextLabel() const;

    /**
     * Check if alert popup is initialized
     * @return true if initialized, false otherwise
     */
    bool isInitialized() const;

private:
    lv_obj_t* popup;           // Popup container
    lv_obj_t* labelText;       // Alert message text

    bool initialized;
    bool visible;

    // Constants
    static const uint16_t WIDTH = 260;
    static const uint16_t HEIGHT = 80;
    static const int16_t Y_OFFSET = -50;  // Slightly above center

    // Severity colors
    static const uint32_t COLOR_INFO = 0x3498DB;      // Blue
    static const uint32_t COLOR_WARNING = 0xF39C12;   // Orange
    static const uint32_t COLOR_CRITICAL = 0xE74C3C;  // Red
};

#endif // ALERT_POPUP_H
