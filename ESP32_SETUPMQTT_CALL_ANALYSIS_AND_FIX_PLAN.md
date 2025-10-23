# ESP32 setupMQTT() Call Analysis & Fix Plan

**Date**: October 20, 2025
**Problem**: `setupMQTT()` is being called MULTIPLE TIMES, each time reloading certificates and calling `setCertificate()` again

---

## Current Behavior - setupMQTT() Called Multiple Times

### Where setupMQTT() is Called:

1. **Line 560**: In `setup()` function
   ```cpp
   if (wifiConnected) {
     syncNTPTime();
     if (isProvisioned && hasCertificates()) {
       setupMQTT();  // ✅ FIRST CALL - At boot if already provisioned
     }
   }
   ```
   **When**: Once at device boot if WiFi connects and device is already provisioned
   **Status**: ✅ CORRECT - Should run once

2. **Line 965**: In `connectToWiFi()` function
   ```cpp
   if (WiFi.status() == WL_CONNECTED) {
     wifiConnected = true;
     // ... other code ...
     syncNTPTime();
     if (isProvisioned && hasCertificates()) {
       setupMQTT();  // ❌ PROBLEM - Called EVERY WiFi reconnect
     }
   }
   ```
   **When**: Every time WiFi connects successfully
   **Status**: ❌ PROBLEM - Gets called multiple times when WiFi reconnects

3. **Line 1216**: In `attemptProvisioning()` function
   ```cpp
   if (saveCertificates(certPem, keyPem)) {
     isProvisioned = true;
     provisioningInProgress = false;
     saveConfiguration();
     // ... LED flashing ...
     setupMQTT();  // ✅ FIRST PROVISION - After successful provisioning
   }
   ```
   **When**: Once after successful provisioning from backend
   **Status**: ✅ CORRECT - Should run once after getting certificates

### What setupMQTT() Does Each Time:

```cpp
void setupMQTT() {
  // Line 996: Load certificates from SPIFFS into global strings
  if (!loadDeviceCertificate(deviceCertificate, devicePrivateKey)) {
    return;
  }

  // Lines 1015-1017: Call setCertificate() with .c_str()
  wifiClient.setCACert(caCertificate.c_str());
  wifiClient.setCertificate(deviceCertificate.c_str());
  wifiClient.setPrivateKey(devicePrivateKey.c_str());

  // Lines 1026-1029: Configure MQTT client
  mqttClient.setServer(mqttServer.c_str(), mqttPort.toInt());
  mqttClient.setCallback(onMqttMessage);
  mqttClient.setBufferSize(4096);
  mqttClient.setKeepAlive(15);

  // Line 1032: Attempt MQTT connection
  connectToMQTT();
}
```

**Problem**: Every call to `setupMQTT()`:
1. Reloads certificates from SPIFFS (I/O overhead)
2. Calls `setCertificate()` again (may overwrite pointers)
3. Calls `connectToMQTT()` which attempts TLS handshake

---

## The Root Cause

### Scenario: WiFi Reconnection Triggers setupMQTT()

1. **Device boots** → `setup()` line 560 calls `setupMQTT()` ✅
2. **MQTT connect fails** (error -30592)
3. **WiFi stays connected** (no disconnection yet)
4. **But if WiFi ever disconnects and reconnects**:
   - Line 965 in `connectToWiFi()` calls `setupMQTT()` again ❌
   - Certificates are reloaded from SPIFFS
   - `setCertificate()` is called again
   - New TLS connection attempt

**OR** simpler scenario:

1. **User configures device** via captive portal
2. **WiFi connects** → Line 965 calls `setupMQTT()` ✅ (first time, OK)
3. **Provisioning fails** (no cert yet)
4. **Later provisioning succeeds** → Line 1216 calls `setupMQTT()` ✅ (second time, also OK)
5. **If WiFi reconnects** → Line 965 calls `setupMQTT()` again ❌ (third time, BAD)

---

## The Fix - Only Setup MQTT Once

### Option 1: Flag-Based Approach (RECOMMENDED)

Add a global flag to track if MQTT has been configured:

```cpp
// Line 93: Add flag
bool mqttConfigured = false;

// Modify setupMQTT() to only run once:
void setupMQTT() {
  if (mqttConfigured) {
    Serial.println("🔐 MQTT already configured, attempting reconnect...");
    connectToMQTT();  // Just reconnect, don't reload certs
    return;
  }

  // ... existing certificate loading code ...

  mqttConfigured = true;  // Mark as configured
}
```

**Benefits**:
- Certificates only loaded ONCE from SPIFFS
- `setCertificate()` only called ONCE
- Subsequent calls just attempt reconnection

**Drawback**:
- If certificates change (re-provisioning), flag needs to be reset

### Option 2: Remove setupMQTT() from connectToWiFi() (CLEANER)

```cpp
// Line 965: Remove the setupMQTT() call entirely
if (WiFi.status() == WL_CONNECTED) {
  wifiConnected = true;
  // ... other code ...
  syncNTPTime();

  // ❌ REMOVE THIS:
  // if (isProvisioned && hasCertificates()) {
  //   setupMQTT();
  // }

  // ✅ INSTEAD: Just try to reconnect if already configured
  if (isProvisioned && hasCertificates() && mqttConfigured) {
    Serial.println("🔄 WiFi reconnected, attempting MQTT reconnect...");
    connectToMQTT();  // Just reconnect, don't reload
  }
}
```

**Benefits**:
- Cleaner logic - WiFi connection doesn't trigger MQTT setup
- setupMQTT() only called from:
  1. Line 560 (boot if provisioned)
  2. Line 1216 (after provisioning)

**Drawback**:
- Need to ensure MQTT reconnects when WiFi comes back

### Option 3: Separate Configuration from Connection

Refactor into two functions:
- `configureMQTT()` - Load certs and set them (ONCE)
- `connectToMQTT()` - Just attempt connection (MANY TIMES)

```cpp
bool mqttConfigured = false;

void configureMQTT() {
  if (mqttConfigured) {
    Serial.println("🔐 MQTT already configured");
    return;
  }

  // Load certificates
  if (!loadDeviceCertificate(deviceCertificate, devicePrivateKey)) {
    return;
  }

  // Set certificates
  wifiClient.setCACert(caCertificate.c_str());
  wifiClient.setCertificate(deviceCertificate.c_str());
  wifiClient.setPrivateKey(devicePrivateKey.c_str());

  // Configure MQTT client
  mqttClient.setServer(mqttServer.c_str(), mqttPort.toInt());
  mqttClient.setCallback(onMqttMessage);
  mqttClient.setBufferSize(4096);
  mqttClient.setKeepAlive(15);

  mqttConfigured = true;
}

void connectToMQTT() {
  if (!mqttConfigured) {
    configureMQTT();  // Configure first if not done
  }

  // ... existing connection attempt code ...
}
```

**Benefits**:
- Clear separation of concerns
- Configuration happens once
- Connection can be retried many times

---

## Recommended Solution: Option 1 (Flag-Based)

**Why**: Minimal code changes, easy to understand, solves the problem directly.

### Implementation Steps:

1. **Add flag at line 93**:
   ```cpp
   bool mqttConfigured = false;
   ```

2. **Modify setupMQTT() at line 984**:
   ```cpp
   void setupMQTT() {
     // Check if already configured
     if (mqttConfigured) {
       Serial.println("🔐 MQTT already configured (certs loaded), attempting reconnect...");
       connectToMQTT();
       return;
     }

     // ... existing code to load certs and configure ...

     // Mark as configured BEFORE calling connectToMQTT()
     mqttConfigured = true;
     Serial.println("✅ MQTT client configured with certificates");
     connectToMQTT();
   }
   ```

3. **Reset flag when re-provisioning** (line 1196):
   ```cpp
   if (saveCertificates(certPem, keyPem)) {
     mqttConfigured = false;  // Reset flag to reload new certificates
     isProvisioned = true;
     // ... rest of code ...
   }
   ```

4. **Reset flag when certificates missing** (line 562):
   ```cpp
   if (isProvisioned && !hasCertificates()) {
     mqttConfigured = false;  // Reset flag
     isProvisioned = false;
     // ... rest of code ...
   }
   ```

---

## Testing Plan

### Test 1: Normal Boot (Already Provisioned)
1. Device boots with saved WiFi credentials
2. WiFi connects → Line 560 calls `setupMQTT()` → Certs loaded, flag set
3. MQTT connection attempted
4. **Expected**: Certificates loaded once, setupMQTT() prints "MQTT client configured"

### Test 2: WiFi Reconnection
1. Device running, MQTT connected
2. Manually disconnect WiFi (turn off router)
3. Wait for WiFi to reconnect
4. Line 965 calls `setupMQTT()` again
5. **Expected**: setupMQTT() prints "already configured", calls connectToMQTT() without reloading certs

### Test 3: Fresh Provisioning
1. Device in captive portal mode
2. Configure WiFi and provisioning code
3. Line 1216 calls `setupMQTT()` after getting certificates
4. **Expected**: Certificates loaded once, flag set, MQTT connection attempted

### Test 4: Re-Provisioning
1. Device already provisioned
2. Clear certificates, get new ones
3. Line 1196 resets `mqttConfigured = false`
4. setupMQTT() loads new certificates
5. **Expected**: Flag reset, new certificates loaded

---

## Summary

**Current Problem**: setupMQTT() called multiple times → certificates reloaded → setCertificate() called multiple times

**Solution**: Add `mqttConfigured` flag, only load certificates once

**Changes Required**:
- Line 93: Add `bool mqttConfigured = false;`
- Line 984-986: Add flag check at start of setupMQTT()
- Line 1031-1032: Set flag to true after configuration
- Line 562: Reset flag when certs missing
- Line 1196: Reset flag when re-provisioning

**Result**: Certificates loaded ONCE, connection can retry multiple times without reloading
