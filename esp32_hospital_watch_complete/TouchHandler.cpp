/**
 * TouchHandler.cpp
 * Hospital Watch Touch Gesture Handler Implementation
 */

#include "TouchHandler.h"

// Forward declaration for touch reading (from FT3168 driver)
extern "C" {
    uint8_t getTouch(uint16_t *x, uint16_t *y);
}

TouchHandler::TouchHandler()
    : initialized(false),
      enabled(true),
      uiScreens(nullptr),
      gestureCallback(nullptr),
      isTouching(false),
      wasTouching(false),
      startX(0), startY(0),
      currentX(0), currentY(0),
      touchStartTime(0) {
}

TouchHandler::~TouchHandler() {
}

void TouchHandler::init(UIScreens *screens) {
    if (initialized) {
        Serial.println("⚠️  TouchHandler already initialized");
        return;
    }

    if (screens == nullptr) {
        Serial.println("❌ TouchHandler init failed: screens is null");
        return;
    }

    uiScreens = screens;
    initialized = true;
    Serial.println("✅ TouchHandler initialized");
}

bool TouchHandler::isInitialized() const {
    return initialized;
}

void TouchHandler::update() {
    if (!initialized || !enabled) {
        return;
    }

    // Read touch state
    uint16_t x, y;
    uint8_t touched = getTouch(&x, &y);

    wasTouching = isTouching;
    isTouching = (touched != 0);

    // Touch started (pressed)
    if (isTouching && !wasTouching) {
        startX = x;
        startY = y;
        currentX = x;
        currentY = y;
        touchStartTime = millis();
    }

    // Touch moved (dragging)
    if (isTouching && wasTouching) {
        currentX = x;
        currentY = y;
    }

    // Touch ended (released)
    if (!isTouching && wasTouching) {
        GestureType gesture = detectGesture();
        if (gesture != GESTURE_NONE) {
            handleGesture(gesture);
        }
    }
}

void TouchHandler::setGestureCallback(void (*callback)(GestureType type)) {
    gestureCallback = callback;
}

void TouchHandler::setEnabled(bool en) {
    enabled = en;
}

bool TouchHandler::isEnabled() const {
    return enabled;
}

// ===== Private Gesture Detection Methods =====

GestureType TouchHandler::detectGesture() {
    int16_t deltaX = currentX - startX;
    int16_t deltaY = currentY - startY;
    uint32_t duration = millis() - touchStartTime;

    // Calculate absolute deltas
    int16_t absDeltaX = abs(deltaX);
    int16_t absDeltaY = abs(deltaY);

    // Long press detection
    if (duration >= LONG_PRESS_TIME && absDeltaX < TAP_MAX_MOVEMENT && absDeltaY < TAP_MAX_MOVEMENT) {
        return GESTURE_LONG_PRESS;
    }

    // Tap detection
    if (duration < TAP_MAX_TIME && absDeltaX < TAP_MAX_MOVEMENT && absDeltaY < TAP_MAX_MOVEMENT) {
        return GESTURE_TAP;
    }

    // Swipe detection
    if (isSwipeHorizontal(deltaX, deltaY)) {
        if (absDeltaX >= SWIPE_THRESHOLD) {
            return (deltaX > 0) ? GESTURE_SWIPE_RIGHT : GESTURE_SWIPE_LEFT;
        }
    }

    if (isSwipeVertical(deltaX, deltaY)) {
        if (absDeltaY >= SWIPE_THRESHOLD) {
            return (deltaY > 0) ? GESTURE_SWIPE_DOWN : GESTURE_SWIPE_UP;
        }
    }

    return GESTURE_NONE;
}

void TouchHandler::handleGesture(GestureType gesture) {
    // Call user callback if set
    if (gestureCallback != nullptr) {
        gestureCallback(gesture);
    }

    // Handle screen navigation
    if (uiScreens == nullptr) {
        return;
    }

    switch (gesture) {
        case GESTURE_SWIPE_LEFT:
            Serial.println("👆 Swipe left - next screen");
            uiScreens->showNextScreen();
            break;

        case GESTURE_SWIPE_RIGHT:
            Serial.println("👆 Swipe right - previous screen");
            uiScreens->showPreviousScreen();
            break;

        case GESTURE_SWIPE_UP:
            Serial.println("👆 Swipe up");
            // Reserved for future use (e.g., scroll)
            break;

        case GESTURE_SWIPE_DOWN:
            Serial.println("👆 Swipe down");
            // Reserved for future use (e.g., scroll)
            break;

        case GESTURE_TAP:
            // Taps are handled by LVGL button events
            break;

        case GESTURE_LONG_PRESS:
            Serial.println("👆 Long press");
            // Reserved for future use (e.g., show menu)
            break;

        default:
            break;
    }
}

bool TouchHandler::isSwipeHorizontal(int16_t deltaX, int16_t deltaY) {
    // Horizontal swipe: |deltaX| > |deltaY| * 2
    return (abs(deltaX) > abs(deltaY) * 2);
}

bool TouchHandler::isSwipeVertical(int16_t deltaX, int16_t deltaY) {
    // Vertical swipe: |deltaY| > |deltaX| * 2
    return (abs(deltaY) > abs(deltaX) * 2);
}
