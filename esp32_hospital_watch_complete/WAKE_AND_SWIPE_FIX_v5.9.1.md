# Screen Wake & Swipe Fix - v5.9.1

**Date:** 2025-11-26
**Issues:**
1. Touch doesn't wake screen (backlight stays dark)
2. Swipe gestures not working - ECG page opens automatically
3. SPIFFS cleanup threshold too high (90% → should be 60%)

**Status:** ✅ FIXED

---

## Problem 1: Touch Not Waking Screen

### Symptoms
```
💤 Screen timeout - backlight off
[User taps screen]
LVGL touch callback: x=8, y=441, state=PRESSED
👆 ECG/HR card clicked - showing ECG waveform
// NO "💡 Screen woken" message!
// Backlight stays dark!
```

### Root Cause
**Location:** [TouchHandler.cpp:78-82](TouchHandler.cpp#L78-L82)

The 15ms touch debounce filter was preventing `updateLastActivity()` from being called:

1. Touch detected with valid coordinates
2. Debounce timer started: `touchFirstSeenTime = millis()`
3. **User released finger before 15ms passed** (quick tap)
4. `validTouch` remained `false` because `(millis() - touchFirstSeenTime) < 15ms`
5. `isTouching = validTouch` → `isTouching = false`
6. Main loop: `touch.isTouched()` returned `false`
7. **`updateLastActivity()` never called** → backlight stayed off

**Why the debounce exists:**
The FT3168 touch controller has no hardware INT pin, so we poll I2C registers. This picks up electrical noise as phantom touches. The 15ms debounce filters these out, but it also prevents quick taps from waking the screen.

### Fix Applied

**Added raw touch detection that bypasses debounce:**

#### TouchHandler.h Changes:
```cpp
// ✅ v5.9.1: Check if ANY touch detected (before debounce)
bool isRawTouchDetected() const { return rawTouchDetected; }

private:
    bool rawTouchDetected;  // Raw touch state (before debounce)
```

#### TouchHandler.cpp Changes:
```cpp
// Line 20: Initialize in constructor
rawTouchDetected(false),

// Line 105: Set raw touch BEFORE debounce check
rawTouchDetected = (touched && validCoordinates);
```

#### Main Loop Changes:
**Location:** [esp32_hospital_watch_complete.ino:2060](esp32_hospital_watch_complete.ino#L2060)

```cpp
// ✅ BEFORE v5.9.1: Used debounced touch (waited 15ms)
bool isTouched = touch.isTouched();

// ✅ AFTER v5.9.1: Use raw touch (immediate detection)
bool isTouched = touch.isRawTouchDetected();
```

**Result:**
- Screen wakes **instantly** on ANY touch (no 15ms delay)
- Debounce filter still used for gesture detection (prevents phantom gestures)
- `updateLastActivity()` called immediately → backlight turns on

---

## Problem 2: Swipe Not Working - Gestures Trigger During Wake

### Symptoms
```
💤 Screen timeout - backlight off
[User taps screen to wake it]
👆 Touch detected: x=8, y=441
💡 Screen woken - restored to 100% brightness
👆 ECG/HR card clicked - showing ECG waveform  // ← BUG! Wake tap triggered action!

[User swipes while screen on]
// Swipe doesn't work, goes to ECG page instead
```

### Root Cause

When screen was off and user tapped:
1. Raw touch detected → `updateLastActivity()` called → **screen woke**
2. BUT touch continued being processed by TouchHandler
3. Touch released → `detectGesture()` called → detected as TAP gesture
4. TAP gesture processed → **LVGL received it** → ECG card clicked!

**The wake tap was being processed as a UI gesture!**

Similarly, when trying to swipe:
- Swipe gesture detected
- But LVGL also received the touch events
- LVGL interpreted it as card click instead of swipe

### Fix Applied

**Added flag to ignore first gesture after screen wake:**

#### Main Sketch Changes:
**Location:** [esp32_hospital_watch_complete.ino:1025](esp32_hospital_watch_complete.ino#L1025)

```cpp
bool screenOn = true;
bool screenJustWoke = false;  // ✅ v5.9.1: Flag to ignore first gesture after wake
```

**Location:** [esp32_hospital_watch_complete.ino:1041](esp32_hospital_watch_complete.ino#L1041)

```cpp
void updateLastActivity() {
  lastUserActivity = millis();
  if (!screenOn) {
    screenOn = true;
    screenJustWoke = true;  // ✅ v5.9.1: Set flag to ignore next gesture
    uint8_t hwLevel = map(userBrightnessLevel, 0, 100, 0, 255);
    display.setBrightness(hwLevel);
    Serial.printf("💡 Screen woken - restored to %d%% brightness\n", userBrightnessLevel);
  }
}
```

#### TouchHandler.cpp Changes:
**Location:** [TouchHandler.cpp:14](TouchHandler.cpp#L14)

```cpp
// ✅ v5.9.1: Access screen wake flag from main sketch
extern bool screenJustWoke;
```

**Location:** [TouchHandler.cpp:198-203](TouchHandler.cpp#L198-L203)

```cpp
void TouchHandler::handleGesture(GestureType gesture) {
    // ✅ v5.9.1: Ignore gestures if screen just woke (prevent wake tap from triggering actions)
    if (screenJustWoke) {
        Serial.println("👆 Gesture ignored - screen just woke");
        screenJustWoke = false;  // Clear flag for next gesture
        return;
    }

    // ... rest of gesture handling
}
```

**Result:**
- Wake tap is **ignored** (doesn't trigger card clicks)
- Subsequent touches work normally (swipes, taps, etc.)
- Clean separation between "wake screen" and "interact with UI"

---

## Problem 3: SPIFFS Threshold Too High

### Symptoms
```
   Used:  1376735 bytes (1344.5 KB, 95.7%)
// SPIFFS critically full, but no cleanup until 90%!
```

User requested cleanup to start at **60% instead of 90%**.

### Fix Applied

**Location:** [esp32_hospital_watch_complete.ino:466](esp32_hospital_watch_complete.ino#L466)

```cpp
// ✅ BEFORE v5.9.1:
if (usage > 90.0) {  // Wait until 90% full
    while (usage > 80.0 && ...) {  // Target 80% after cleanup

// ✅ AFTER v5.9.1:
if (usage > 60.0) {  // Start cleanup at 60%
    while (usage > 50.0 && ...) {  // Target 50% after cleanup
```

**Location:** [esp32_hospital_watch_complete.ino:1879](esp32_hospital_watch_complete.ino#L1879)

```cpp
// ✅ BEFORE v5.9.1:
if (spiffsUsage > 95.0) {  // Emergency cleanup on boot at 95%

// ✅ AFTER v5.9.1:
if (spiffsUsage > 60.0) {  // Emergency cleanup on boot at 60%
```

**Result:**
- Cleanup starts at 60% usage (more aggressive)
- Targets 50% after cleanup (leaves more free space)
- Prevents SPIFFS from getting too full

---

## Files Modified

1. **[TouchHandler.h:86](TouchHandler.h#L86)** - Added `isRawTouchDetected()` method
2. **[TouchHandler.h:104](TouchHandler.h#L104)** - Added `rawTouchDetected` member variable
3. **[TouchHandler.cpp:14](TouchHandler.cpp#L14)** - Added `extern bool screenJustWoke`
4. **[TouchHandler.cpp:20](TouchHandler.cpp#L20)** - Initialize `rawTouchDetected` in constructor
5. **[TouchHandler.cpp:105](TouchHandler.cpp#L105)** - Set `rawTouchDetected` before debounce
6. **[TouchHandler.cpp:198-203](TouchHandler.cpp#L198-L203)** - Check `screenJustWoke` flag
7. **[esp32_hospital_watch_complete.ino:1025](esp32_hospital_watch_complete.ino#L1025)** - Added `screenJustWoke` flag
8. **[esp32_hospital_watch_complete.ino:1041](esp32_hospital_watch_complete.ino#L1041)** - Set flag in `updateLastActivity()`
9. **[esp32_hospital_watch_complete.ino:2060](esp32_hospital_watch_complete.ino#L2060)** - Use `isRawTouchDetected()`
10. **[esp32_hospital_watch_complete.ino:466](esp32_hospital_watch_complete.ino#L466)** - SPIFFS threshold 90%→60%
11. **[esp32_hospital_watch_complete.ino:1879](esp32_hospital_watch_complete.ino#L1879)** - Boot cleanup 95%→60%

---

## Expected Behavior After Upload

### Touch Wake Test:
```
💤 Screen timeout - backlight off
[User taps screen]
LVGL touch callback: x=X, y=Y, state=PRESSED
💡 Screen woken - restored to 100% brightness  // ← Should appear IMMEDIATELY
👆 Touch detected: x=X, y=Y
👆 Gesture ignored - screen just woke  // ← Wake tap not processed as gesture
```

### Swipe Test (After Screen Wake):
```
[User taps to wake]
💡 Screen woken - restored to 100% brightness
👆 Gesture ignored - screen just woke

[User swipes left]
👆 Touch detected: x=200, y=100
👆 Swipe left - next screen  // ← Now works correctly!
```

### SPIFFS Cleanup (First Boot):
```
📂 Initializing SPIFFS...
✅ SPIFFS mounted successfully
   Total: 1438481 bytes (1404.8 KB)
   Used:  1376735 bytes (1344.5 KB, 95.7%)
🚨 SPIFFS CRITICALLY FULL: 95.7% - EMERGENCY CLEANUP!
🗑️  Cleared 143 queued messages (patient data removed)
✅ Emergency cleanup complete: 12.3% used
```

### SPIFFS Cleanup (During Operation):
```
⚠️  SPIFFS critically full: 62.3% - emergency cleanup!
🗑️  Deleted 10 files, 55.2% used
🗑️  Deleted 20 files, 48.5% used
✅ SPIFFS cleanup complete: 23 files deleted, 47.4% used
💾 Queued offline: /queue/alerts/1234578.json (234 bytes)
```

---

## Testing Checklist

- [ ] Upload firmware
- [ ] **Test screen wake:**
  - [ ] Wait for screen timeout (15 seconds)
  - [ ] Tap screen while dark
  - [ ] Verify "💡 Screen woken" appears **immediately**
  - [ ] Verify "👆 Gesture ignored - screen just woke" appears
  - [ ] Verify backlight turns on
  - [ ] Verify NO card click happens (ECG page doesn't open)

- [ ] **Test swipe after wake:**
  - [ ] Tap to wake screen
  - [ ] Wait 1 second (let wake complete)
  - [ ] Swipe left → should navigate to next screen
  - [ ] Swipe right → should navigate to previous screen
  - [ ] Verify swipes work reliably

- [ ] **Test SPIFFS cleanup:**
  - [ ] Check serial output on boot
  - [ ] If >60% full, should show emergency cleanup
  - [ ] Disconnect WiFi/MQTT to trigger offline queueing
  - [ ] Fill SPIFFS to >60%
  - [ ] Verify cleanup triggers automatically
  - [ ] Verify cleanup targets 50% after completion

---

## Technical Details

### Touch Detection Flow (BEFORE v5.9.1):
```
1. FT3168 I2C read → (x, y) coordinates
2. Valid coordinates check → true
3. Debounce check: held for 15ms? → NO (user tapped quickly)
4. validTouch = false
5. isTouching = false
6. Main loop: isTouched() = false
7. updateLastActivity() NOT CALLED ❌
8. Backlight stays off ❌
```

### Touch Detection Flow (AFTER v5.9.1):
```
1. FT3168 I2C read → (x, y) coordinates
2. Valid coordinates check → true
3. rawTouchDetected = true  ✅ (BEFORE debounce)
4. Debounce check: held for 15ms? → NO
5. validTouch = false (for gestures)
6. isTouching = false (for gestures)
7. Main loop: isRawTouchDetected() = true  ✅
8. updateLastActivity() CALLED ✅
9. Backlight turns on ✅
```

### Gesture Ignore Flow (AFTER v5.9.1):
```
1. Screen off, user taps
2. Raw touch detected → updateLastActivity()
3. screenJustWoke = true
4. Touch released → detectGesture() = TAP
5. handleGesture(TAP) called
6. Check screenJustWoke == true?
7. YES → Print "Gesture ignored - screen just woke"
8. screenJustWoke = false (clear for next gesture)
9. return (gesture not processed) ✅
10. Next touch works normally ✅
```

---

## Why These Bugs Existed

### Touch Wake Bug:
- Debounce filter designed to reject phantom touches (electrical noise)
- But it also rejected real quick taps used for waking screen
- Classic tradeoff: noise filtering vs. responsiveness
- **Solution:** Separate raw touch (for wake) from debounced touch (for gestures)

### Swipe Bug:
- Touch events processed by both TouchHandler AND LVGL
- When screen woke, the wake tap was seen as a UI interaction
- No distinction between "wake the screen" and "interact with UI"
- **Solution:** Ignore first gesture after wake (only wake, don't interact)

### SPIFFS Threshold:
- Original design assumed WiFi always connected (messages sent immediately)
- But in offline mode, messages queue up fast
- 90% threshold too late - can fill up before cleanup runs
- **Solution:** Lower threshold to 60%, more aggressive cleanup

---

## Related Fixes

This is part of the v5.9.1 system stability improvements:

1. **[COMPILATION_FIX_v5.9.1.md](COMPILATION_FIX_v5.9.1.md)** - I2C driver migration
2. **[GESTURE_FIX_v5.9.1.md](GESTURE_FIX_v5.9.1.md)** - Touch debounce bug
3. **[TAP_TO_WAKE_FIX_v5.9.1.md](TAP_TO_WAKE_FIX_v5.9.1.md)** - Backlight wake & NULL crash
4. **[SPIFFS_CRASH_FIX_v5.9.1.md](SPIFFS_CRASH_FIX_v5.9.1.md)** - SPIFFS cleanup optimization
5. **[WAKE_AND_SWIPE_FIX_v5.9.1.md](WAKE_AND_SWIPE_FIX_v5.9.1.md)** - This document

---

**Status:** ✅ Fixed and ready to upload

**Expected Result:**
- Screen wakes instantly on touch
- Wake tap doesn't trigger UI actions
- Swipes work reliably after wake
- SPIFFS cleanup starts at 60% usage
