/**
 * TouchHandler.h
 * Hospital Watch Touch Gesture Handler
 *
 * Detects swipe gestures for screen navigation:
 * - Swipe Left: Next screen
 * - Swipe Right: Previous screen
 * - Tap: Button interactions (handled by LVGL)
 * - Long Press: Reserved for future use
 */

#ifndef TOUCH_HANDLER_H
#define TOUCH_HANDLER_H

#include <Arduino.h>
#include "UIScreens.h"

// Gesture types
enum GestureType {
    GESTURE_NONE = 0,
    GESTURE_SWIPE_LEFT,
    GESTURE_SWIPE_RIGHT,
    GESTURE_SWIPE_UP,
    GESTURE_SWIPE_DOWN,
    GESTURE_TAP,
    GESTURE_LONG_PRESS
};

class TouchHandler {
public:
    /**
     * Constructor
     */
    TouchHandler();

    /**
     * Destructor
     */
    ~TouchHandler();

    /**
     * Initialize touch handler
     * @param screens Pointer to UIScreens instance for navigation
     */
    void init(UIScreens *screens);

    /**
     * Check if initialized
     */
    bool isInitialized() const;

    /**
     * Update touch handler (detect gestures)
     * Should be called in main loop
     */
    void update();

    /**
     * Set gesture callback function
     * @param callback Function to call when gesture detected
     */
    void setGestureCallback(void (*callback)(GestureType type));

    /**
     * Enable/disable gesture detection
     * @param enabled true=enabled, false=disabled
     */
    void setEnabled(bool enabled);

    /**
     * Check if gesture detection is enabled
     */
    bool isEnabled() const;

    /**
     * Check if screen is currently being touched
     * @return true if screen is touched, false otherwise
     */
    bool isTouched() const { return isTouching; }

    /**
     * Get the last detected tap gesture
     * @return true if a tap was just detected (debounced, minimum 50ms duration)
     */
    bool getTapEvent();

private:
    bool tapEventFlag = false;  // Flag set when tap gesture detected
    bool initialized;
    bool enabled;
    UIScreens *uiScreens;
    void (*gestureCallback)(GestureType type);

    // Touch state tracking
    bool isTouching;
    bool wasTouching;
    int16_t startX, startY;
    int16_t currentX, currentY;
    uint32_t touchStartTime;

    // ✅ v5.8.14: Time-based debouncing for phantom touch rejection
    // ✅ v5.8.15: Tuned debounce to 7ms (balance: filters noise, allows swipes)
    //     FT3168 has no hardware INT pin, so I2C polling picks up bus noise
    //     7ms = just enough to filter electrical spikes without breaking gestures
    uint16_t lastX, lastY;
    uint32_t touchFirstSeenTime;  // When current coordinates first appeared
    static const uint32_t DEBOUNCE_TIME = 7;  // 7ms debounce period (was 2ms, tested 20ms too high)

    // ✅ v5.8.15: I2C polling rate limiter (reduces bus contention with IMU)
    uint32_t lastTouchPollTime;   // Last time we polled FT3168 via I2C
    static const uint32_t TOUCH_POLL_INTERVAL = 10;  // Poll every 10ms (100Hz max)

    // Gesture detection thresholds
    static const int16_t SWIPE_THRESHOLD = 60;      // Minimum pixels for swipe
    static const uint32_t TAP_MAX_TIME = 200;       // Maximum time for tap (ms)
    static const uint32_t LONG_PRESS_TIME = 1000;   // Minimum time for long press (ms)
    static const int16_t TAP_MAX_MOVEMENT = 10;     // Maximum movement for tap (pixels)

    // Gesture detection methods
    GestureType detectGesture();
    void handleGesture(GestureType gesture);
    bool isSwipeHorizontal(int16_t deltaX, int16_t deltaY);
    bool isSwipeVertical(int16_t deltaX, int16_t deltaY);
};

#endif // TOUCH_HANDLER_H
