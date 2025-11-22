# ESP32 Hospital Watch - Refactor Plan

**Based on**: Expert Panel Audit (EXPERT_AUDIT_REPORT.md)
**Current Score**: 8.1/10
**Target Score**: 9.5/10
**Timeline**: 4 weeks

---

## Phase 1: Security Hardening (Week 1)

**Goal**: Pass IEC 62304 Class C security requirements
**Effort**: 1 day (8 hours)
**Impact**: Critical for medical device certification

### Tasks:

#### 1.1 TLS Certificate Pinning (30 minutes)
**File**: `esp32_hospital_watch_complete.ino`
**Priority**: CRITICAL

```cpp
// Add after WiFi connection, before MQTT setup
const char* mqtt_cert_fingerprint =
  "AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD";

wifiClient.setFingerprint(mqtt_cert_fingerprint);

// Also add fingerprint verification callback
wifiClient.setInsecure(false);  // Enforce verification
```

**Test**: Try connecting to wrong broker → should fail

#### 1.2 OTA Signature Verification (2 hours)
**File**: Create `OTASecure.h` and `OTASecure.cpp`
**Priority**: HIGH (IEC 62304 requirement)

```cpp
// OTASecure.h
#include <Update.h>
#include <mbedtls/rsa.h>

class OTASecure {
public:
  bool verifyAndFlash(const uint8_t* firmware, size_t len, const uint8_t* signature);
private:
  bool verifySignature(const uint8_t* hash, const uint8_t* signature);
  const uint8_t public_key[294] = { /* Embedded RSA public key */ };
};
```

**Test**: Flash unsigned firmware → should reject

#### 1.3 NFC UID Hashing (1 hour)
**File**: `NFCManager.cpp`
**Priority**: MEDIUM (DPDP compliance)

```cpp
#include <mbedtls/sha256.h>

String NFCManager::hashUID(String uid) {
  unsigned char hash[32];
  mbedtls_sha256((unsigned char*)uid.c_str(), uid.length(), hash, 0);

  // Return first 8 bytes as hex (sufficient for de-duplication)
  char hex[17];
  for (int i = 0; i < 8; i++) {
    sprintf(&hex[i*2], "%02x", hash[i]);
  }
  return String(hex);
}

// In handleCardDetected():
result.uid = hashUID(uidToString(uid, uidLength));
```

**Test**: Same card → same hash, different cards → different hashes

#### 1.4 Security Audit Logging (2 hours)
**File**: Create `SecurityLog.h` and `SecurityLog.cpp`
**Priority**: MEDIUM

```cpp
class SecurityLog {
public:
  void logEvent(const char* event, const char* details);
  void logAuthFailure(const char* reason);
  void logOTAAttempt(bool success);
  void dumpLog();  // For debug
private:
  struct LogEntry {
    unsigned long timestamp;
    char event[32];
    char details[64];
  };
  LogEntry log[100];  // Circular buffer
  int logIndex = 0;
};
```

**Test**: Trigger security events → verify logs

#### 1.5 MQTT Last Will (30 minutes)
**File**: `esp32_hospital_watch_complete.ino`
**Priority**: LOW

```cpp
// In connectMQTT():
String willTopic = "hospital/devices/" + deviceId + "/status";
String willMessage = "{\"status\":\"offline\",\"timestamp\":\"" + getISO8601Timestamp() + "\"}";
mqttClient.setWill(willTopic.c_str(), willMessage.c_str(), true, 1);
```

**Test**: Unplug device → verify offline status published

---

## Phase 2: Power Optimization (Week 2)

**Goal**: Extend battery life from 3 hours to 24 hours
**Effort**: 1 day (8 hours)
**Impact**: Critical for 24/7 ICU use

### Tasks:

#### 2.1 Deep Sleep Implementation (3 hours)
**File**: Create `PowerManager.h` and `PowerManager.cpp`
**Priority**: HIGH

```cpp
class PowerManager {
public:
  void enterLightSleep(unsigned long duration_ms);
  void enterDeepSleep(unsigned long duration_ms);
  void enableWakeOnMotion(int gpio_pin);
  void enableWakeOnTouch(int gpio_pin);

private:
  bool canSleep();  // Check if safe to sleep (no pending MQTT)
};

// In loop():
if (inactivityTime > 30000 && powerManager.canSleep()) {
  powerManager.enterLightSleep(10000);  // 10s naps
}
```

**Current**: ~120mA continuous
**Target**: ~15mA average (10s sleep, 1s wake cycles)
**Battery Life**: 3hrs → 20hrs

**Test**: Monitor current draw with multimeter

#### 2.2 Display Auto-Dim (1 hour)
**File**: `DisplayManager.cpp`
**Priority**: MEDIUM

```cpp
// In DisplayManager::update():
static unsigned long lastTouch = 0;

if (millis() - lastTouch > 15000) {
  ledcWrite(LCD_BACKLIGHT_CH, 50);  // 50% brightness
} else {
  ledcWrite(LCD_BACKLIGHT_CH, 255);  // 100% brightness
}

// Saves ~30mA when dimmed
```

**Test**: No touch for 15s → dim, touch → brighten

#### 2.3 WiFi Light Sleep (2 hours)
**File**: `esp32_hospital_watch_complete.ino`
**Priority**: MEDIUM

```cpp
// In setup():
esp_wifi_set_ps(WIFI_PS_MIN_MODEM);  // Beacon interval sleep

// In loop() - disable during critical ops:
if (sendingVitals) {
  esp_wifi_set_ps(WIFI_PS_NONE);
} else {
  esp_wifi_set_ps(WIFI_PS_MIN_MODEM);
}

// Saves ~20mA when idle
```

**Test**: Ping device → verify latency <100ms (acceptable)

#### 2.4 IMU Interrupt Wake (2 hours)
**File**: `QMI8658Manager.cpp`
**Priority**: LOW

```cpp
// Configure IMU to raise INT pin on motion
void QMI8658Manager::enableMotionInterrupt(int threshold_mg) {
  writeRegister(QMI8658_REG_INT_EN, 0x01);  // Enable motion int
  writeRegister(QMI8658_REG_MOTION_TH, threshold_mg / 16);
}

// In main:
esp_sleep_enable_ext0_wakeup(GPIO_IMU_INT, 0);  // Wake on low
```

**Test**: Device asleep → shake → wakes and displays alert

---

## Phase 3: Testing & Quality (Week 3)

**Goal**: Achieve 80% test coverage
**Effort**: 2 days (16 hours)
**Impact**: Catch regressions, enable CI/CD

### Tasks:

#### 3.1 Unit Test Framework Setup (2 hours)
**File**: `platformio.ini` (if using PlatformIO) or Arduino test folder
**Priority**: HIGH

```ini
[env:native]
platform = native
test_framework = unity
build_flags = -D UNIT_TEST
```

Create `test/` folder:
```
test/
  test_vitals/
    test_simulator.cpp
  test_mqtt/
    test_payload.cpp
  test_offline/
    test_queue.cpp
```

#### 3.2 Vitals Simulation Tests (3 hours)
**File**: `test/test_vitals/test_simulator.cpp`
**Priority**: HIGH

```cpp
#include <unity.h>
#include "PhysiologicalSimulator.h"

void test_heart_rate_range() {
  PhysiologicalSimulator sim;
  sim.update();
  float hr = sim.getHeartRate();
  TEST_ASSERT_TRUE(hr >= 60 && hr <= 100);  // Normal range
}

void test_temperature_range() {
  PhysiologicalSimulator sim;
  sim.update();
  float temp = sim.getTemperature();
  TEST_ASSERT_TRUE(temp >= 36.0 && temp <= 38.0);
}

void test_mode_switching() {
  PhysiologicalSimulator sim;
  sim.setMode(PhysiologicalSimulator::MODE_ECG);
  TEST_ASSERT_EQUAL(PhysiologicalSimulator::MODE_ECG, sim.getMode());
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_heart_rate_range);
  RUN_TEST(test_temperature_range);
  RUN_TEST(test_mode_switching);
  return UNITY_END();
}
```

**Test**: `pio test` → all pass

#### 3.3 MQTT Payload Tests (3 hours)
**File**: `test/test_mqtt/test_payload.cpp`
**Priority**: HIGH

```cpp
#include <unity.h>
#include <ArduinoJson.h>

void test_vitals_payload_format() {
  JsonDocument doc;
  doc["heartRate"] = 78;
  doc["spo2"] = 98;
  doc["timestamp"] = "2025-11-22T12:00:00Z";

  TEST_ASSERT_TRUE(doc.containsKey("heartRate"));
  TEST_ASSERT_TRUE(doc.containsKey("timestamp"));
  TEST_ASSERT_EQUAL(78, doc["heartRate"].as<int>());
}

void test_message_id_uniqueness() {
  std::set<String> ids;
  for (int i = 0; i < 1000; i++) {
    String id = generateMessageId();
    TEST_ASSERT_TRUE(ids.find(id) == ids.end());  // No duplicates
    ids.insert(id);
  }
}
```

#### 3.4 Offline Queue Tests (3 hours)
**File**: `test/test_offline/test_queue.cpp`
**Priority**: MEDIUM

```cpp
void test_queue_persistence() {
  OfflineQueue queue;
  queue.saveVitals("{\"test\":1}");

  // Simulate power cycle
  queue.~OfflineQueue();
  OfflineQueue queue2;

  TEST_ASSERT_EQUAL(1, queue2.getPendingCount());
}

void test_queue_fifo() {
  OfflineQueue queue;
  queue.saveVitals("{\"seq\":1}");
  queue.saveVitals("{\"seq\":2}");

  String first = queue.getNext();
  TEST_ASSERT_TRUE(first.indexOf("\"seq\":1") > 0);
}
```

#### 3.5 CI/CD Pipeline (3 hours)
**File**: `.github/workflows/esp32-test.yml`
**Priority**: MEDIUM

```yaml
name: ESP32 Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup PlatformIO
        run: pip install platformio
      - name: Run Tests
        run: pio test -e native
      - name: Static Analysis
        run: |
          pip install cppcheck
          cppcheck --enable=all --error-exitcode=1 esp32_hospital_watch_complete/
```

#### 3.6 Static Analysis (2 hours)
**Priority**: LOW

```bash
# Run locally:
cppcheck --enable=all --inconclusive esp32_hospital_watch_complete/
clang-tidy esp32_hospital_watch_complete/*.cpp
```

---

## Phase 4: UX Polish (Week 4)

**Goal**: Professional medical device feel
**Effort**: 1 day (8 hours)
**Impact**: User satisfaction, certification readiness

### Tasks:

#### 4.1 Touch Debounce (1 hour)
**File**: `TouchHandler.cpp`
**Priority**: LOW (FT3168 has hardware debounce)

```cpp
// If needed after hardware testing:
static unsigned long lastTouch = 0;
void TouchHandler::onTouchEvent(lv_event_t* e) {
  unsigned long now = millis();
  if (now - lastTouch < 200) return;  // 200ms debounce
  lastTouch = now;
  // ... handle touch
}
```

**Test**: Rapid taps → only one registers per 200ms

#### 4.2 Haptic Feedback (2 hours)
**File**: Create `HapticManager.h`
**Priority**: MEDIUM

```cpp
class HapticManager {
public:
  void begin(int pwm_pin);
  void click();      // Short buzz (50ms)
  void success();    // Double buzz
  void error();      // Long buzz (200ms)
  void alert();      // Pulse pattern

private:
  int pin;
};

// Usage:
haptic.click();  // On button press
haptic.success();  // On NFC scan
haptic.alert();  // On fall detection
```

**Hardware**: Add vibration motor on GPIO2 (PWM channel)

**Test**: Trigger events → feel vibration

#### 4.3 LVGL Dirty Rect Optimization (3 hours)
**File**: `UIScreens.cpp`
**Priority**: LOW

```cpp
// In updateVitals():
void UIScreens::updateVitals(float hr, float spo2, ...) {
  // Only update changed labels (not full redraw)
  static float lastHR = 0;
  if (abs(hr - lastHR) > 0.5) {
    lv_label_set_text_fmt(labelHR, "%.0f", hr);
    lastHR = hr;
  }

  // LVGL automatically handles dirty rects
  lv_obj_invalidate(hrBox);  // Mark for redraw
}
```

**Benefit**: 30 FPS → 60 FPS, -10% CPU

**Test**: Monitor FPS with `lv_refr_get_fps_avg()`

#### 4.4 Alert Sound (2 hours)
**File**: Create `AudioManager.h`
**Priority**: LOW

```cpp
class AudioManager {
public:
  void begin(int buzzer_pin);
  void playTone(int freq_hz, int duration_ms);
  void playAlert(AlertSeverity severity);

private:
  int pin;
};

// Alert patterns:
void AudioManager::playAlert(AlertSeverity severity) {
  switch (severity) {
    case ALERT_CRITICAL:
      playTone(1000, 500); delay(100);
      playTone(1000, 500);  // Double beep
      break;
    case ALERT_WARNING:
      playTone(800, 300);
      break;
  }
}
```

**Hardware**: Add passive buzzer on GPIO18

**Test**: Trigger fall alert → hear beep

---

## Implementation Schedule

### Week 1: Security (Priority 1)
| Day | Tasks | Hours |
|-----|-------|-------|
| Mon | TLS pinning, Last Will | 2 |
| Tue | OTA signature verification | 4 |
| Wed | NFC hashing, Security log | 3 |
| Thu | Testing, documentation | 1 |

### Week 2: Power (Priority 1)
| Day | Tasks | Hours |
|-----|-------|-------|
| Mon | Deep sleep implementation | 4 |
| Tue | Display dim, WiFi light sleep | 3 |
| Wed | IMU interrupt wake | 2 |
| Thu | Power testing, benchmarks | 1 |

### Week 3: Testing (Priority 2)
| Day | Tasks | Hours |
|-----|-------|-------|
| Mon | Unit test setup, vitals tests | 5 |
| Tue | MQTT payload tests | 3 |
| Wed | Offline queue tests | 3 |
| Thu | CI/CD, static analysis | 5 |

### Week 4: UX (Priority 3)
| Day | Tasks | Hours |
|-----|-------|-------|
| Mon | Haptic feedback | 2 |
| Tue | LVGL optimization | 3 |
| Wed | Alert sound | 2 |
| Thu | Touch debounce (if needed) | 1 |

---

## Success Metrics

### Before Refactor:
- Battery Life: 3 hours
- Security Score: 8/10 (no cert pinning)
- Test Coverage: 0%
- Power Draw: 120mA active
- Loop Time: 100ms

### After Refactor:
- Battery Life: **24 hours** ✅
- Security Score: **10/10** (IEC 62304 compliant) ✅
- Test Coverage: **80%** ✅
- Power Draw: **15mA average** ✅
- Loop Time: **50ms** ✅

---

## Testing Checklist

### Phase 1 Tests:
- [ ] TLS connects to broker with correct cert
- [ ] TLS rejects broker with wrong cert
- [ ] OTA rejects unsigned firmware
- [ ] OTA accepts signed firmware
- [ ] NFC hashes are consistent
- [ ] Security events logged

### Phase 2 Tests:
- [ ] Device enters light sleep
- [ ] Device wakes on timer
- [ ] Device wakes on motion
- [ ] Display dims after 15s
- [ ] WiFi latency <100ms in light sleep
- [ ] Battery life >20 hours

### Phase 3 Tests:
- [ ] All unit tests pass
- [ ] MQTT payloads valid JSON
- [ ] Offline queue survives reboot
- [ ] CI pipeline passes
- [ ] No cppcheck warnings

### Phase 4 Tests:
- [ ] Haptic feedback on touch
- [ ] Alert sound on fall
- [ ] UI renders at 60 FPS
- [ ] Touch debounce (if added)

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Deep sleep breaks MQTT | Implement graceful disconnect before sleep |
| OTA signature slows boot | Verify async in background task |
| Tests fail on hardware | Mock hardware dependencies |
| Power optimization too aggressive | Add "debug mode" flag to disable sleep |
| Haptic motor drains battery | Use short pulses (<100ms) |

---

## Rollback Plan

If issues arise:
1. Keep `refactor/esp32-cleanup-redundancy` branch
2. Create feature branches for each phase
3. Test on dev device before production
4. Maintain "stable" tag for last working version

---

## Post-Refactor

### Documentation Updates:
- [ ] Update ESP32_WATCH_STATUS.md with new features
- [ ] Add TESTING.md guide
- [ ] Update SETUP.md for new dependencies
- [ ] Create POWER_OPTIMIZATION.md guide

### Certification Prep:
- [ ] IEC 62304 software design documentation
- [ ] Risk management file (ISO 14971)
- [ ] Clinical evaluation report
- [ ] Technical file for CDSCO submission

---

**Plan Created**: 2025-11-22
**Author**: Expert Panel
**Status**: Ready for implementation
