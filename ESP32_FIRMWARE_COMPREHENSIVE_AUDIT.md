# ESP32 Hospital Watch Firmware - Comprehensive Audit

## Current Analysis

### Code Structure Review

The firmware has:
- ✅ Good separation of concerns (captive portal, WiFi, MQTT, alerts)
- ✅ Proper state management (isProvisioned, isAssigned, wifiConnected)
- ✅ NTP time synchronization
- ✅ TLS support with SPIFFS certificate loading
- ✅ Device-level alert engine (8 alerts)
- ✅ Configuration persistence (Preferences)

### Critical Issues Found in MQTT Provisioning Implementation

#### Issue 1: Loop Structure Problem ⚠️
**Location:** Line 518-521 (main loop)

```cpp
// Auto-provision if WiFi connected but not provisioned
if (wifiConnected && !isProvisioned && ntpSynced && millis() - lastProvisionAttempt > 15000) {
  attemptProvisioning();
  lastProvisionAttempt = millis();
}
```

**Problem:** The loop calls `attemptProvisioning()` every 15 seconds, but the function connects to MQTT and publishes a request. However, `mqttClient.loop()` is only called on line 509 when `isProvisioned` is true:

```cpp
// Handle MQTT if connected
if (wifiConnected && isProvisioned && mqttClient.connected()) {
  mqttClient.loop();  // ❌ Never called during provisioning!
}
```

**Impact:**
- MQTT messages (provisioning response) will NEVER be received
- The device publishes the provisioning request but can't receive the response
- `onMqttMessage()` callback will never fire for provisioning response

#### Issue 2: Multiple TLS Configuration ⚠️
**Locations:**
- `setupMQTT()` at line 468-490
- `attemptProvisioning()` at line 602-682

**Problem:** Both functions configure TLS independently, which is redundant and could cause conflicts.

#### Issue 3: State Management ⚠️
**Problem:** No proper handling of MQTT loop during provisioning state

The firmware has three states:
1. **Unprovisioned + disconnected** - Needs to handle provisioning
2. **Unprovisioned + MQTT connected** - Waiting for provisioning response
3. **Provisioned** - Normal operation

Currently, `mqttClient.loop()` only runs in state 3, not state 2.

### Root Cause Analysis

The **actual problem** is:

```cpp
// CURRENT (BROKEN):
if (wifiConnected && isProvisioned && mqttClient.connected()) {
  mqttClient.loop();  // ❌ Only runs when provisioned
}

// SHOULD BE:
if (wifiConnected && mqttClient.connected()) {
  mqttClient.loop();  // ✅ Runs during provisioning too
}
```

Without `mqttClient.loop()` running, the ESP32:
1. ✅ Connects to MQTT
2. ✅ Subscribes to response topic
3. ✅ Publishes provisioning request
4. ❌ **Never processes incoming messages** (loop not called)
5. ❌ Response arrives but is never handled
6. ❌ Stays in unprovisioned state forever

## Proper Fix Required

### Fix 1: Update Main Loop MQTT Handling
**File:** esp32_hospital_watch_complete.ino
**Line:** 508-510

**Change:**
```cpp
// BEFORE:
if (wifiConnected && isProvisioned && mqttClient.connected()) {
  mqttClient.loop();
}

// AFTER:
if (wifiConnected && mqttClient.connected()) {
  mqttClient.loop();  // Run MQTT loop even during provisioning
}
```

**Reason:** We need to process MQTT messages during provisioning to receive the provisioning response.

### Fix 2: Improve Provisioning State Management

Add proper state tracking to prevent duplicate provisioning attempts while waiting for response:

```cpp
// After successful MQTT connection in attemptProvisioning():
if (mqttClient.connect(...)) {
  Serial.println("✅ MQTT connected (unprovisioned)");

  // Subscribe to provisioning response topic
  String responseTopic = "hospital/provisioning/response/" + macAddress;
  mqttClient.subscribe(responseTopic.c_str());

  // Publish provisioning request
  if (mqttClient.publish(...)) {
    Serial.println("📤 Provisioning request sent via MQTT");
    Serial.println("⏳ Waiting for response...");

    // ✅ IMPORTANT: Set flag to prevent re-provisioning
    provisioningInProgress = true;

    // ✅ IMPORTANT: Don't increment lastProvisionAttempt here
    // Let it happen in the calling loop so we can timeout if needed
  }
}
```

### Fix 3: Add Provisioning Timeout

Add timeout handling in case backend doesn't respond:

```cpp
// In main loop, add:
// Timeout provisioning attempt after 30 seconds
if (provisioningInProgress && millis() - lastProvisionAttempt > 30000) {
  Serial.println("⏰ Provisioning timeout - will retry");
  provisioningInProgress = false;
  mqttClient.disconnect();  // Force reconnect on next attempt
}
```

### Fix 4: Cleanup Redundant TLS Configuration

The `attemptProvisioning()` function currently duplicates TLS setup. Since we're now ensuring `mqttClient.loop()` runs during provisioning, we should:

1. Remove duplicate TLS configuration from `attemptProvisioning()`
2. Call a shared setup function instead

**Better approach:**
```cpp
void attemptProvisioning() {
  // ... validation code ...

  // Ensure MQTT is configured (idempotent)
  if (!mqttClient.connected()) {
    if (mqttServer.length() == 0) {
      mqttServer = serverIP;
    }

    // Call shared MQTT setup if not already done
    if (!mqttConfigured) {
      setupMQTTClient();  // New shared function
    }

    // Connect with unprovisioned client ID
    String unprovisionedClientId = "HospitalWatch_UNPROVISIONED_" + macAddress;
    unprovisionedClientId.replace(":", "");

    if (mqttClient.connect(...)) {
      // Subscribe and publish
      ...
    }
  }
}
```

## Implementation Plan

### Phase 1: Critical Fix (Main Loop)
1. ✅ Update `mqttClient.loop()` condition to run during provisioning
2. ✅ Test that provisioning response is received

### Phase 2: State Management
1. ✅ Add provisioning timeout (30 seconds)
2. ✅ Prevent duplicate provisioning requests
3. ✅ Add better logging for debugging

### Phase 3: Code Cleanup
1. ✅ Extract shared MQTT configuration function
2. ✅ Remove code duplication
3. ✅ Add comments explaining provisioning flow

### Phase 4: Error Handling
1. ✅ Handle backend errors gracefully
2. ✅ Add retry logic with exponential backoff
3. ✅ Flash LED patterns for different states

## Testing Checklist

- [ ] ESP32 connects to WiFi
- [ ] NTP time syncs
- [ ] MQTT connects with unprovisioned client ID
- [ ] Provisioning request published
- [ ] **Provisioning response received** (THIS IS THE KEY TEST)
- [ ] Credentials saved to Preferences
- [ ] MQTT reconnects with device-specific credentials
- [ ] Normal operation resumes

## Recommended Changes Priority

1. **CRITICAL (Fix Now):** Update main loop to call `mqttClient.loop()` during provisioning
2. **HIGH:** Add provisioning timeout
3. **MEDIUM:** Clean up code duplication
4. **LOW:** Add better error handling and logging

## Questions to Resolve

1. Should we keep the 15-second provisioning retry interval or make it configurable?
2. Should we add a max retry count before reverting to captive portal?
3. Do we want visual feedback (LED patterns) for provisioning states?

## Conclusion

The current implementation has the **right structure** but a **critical bug** in the main loop that prevents MQTT messages from being processed during provisioning.

The fix is simple: Remove the `isProvisioned` check from the `mqttClient.loop()` condition.

All other code (TLS setup, publishing, subscribing) appears correct - it just can't receive the response because the MQTT loop isn't running.
