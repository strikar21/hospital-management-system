# ESP32 setupMQTT() Complete Research Analysis

**Date**: October 20, 2025
**Research First**: All relevant files checked before planning

---

## Research Findings

### Where setupMQTT() is Called:

1. **Line 560** - In `setup()` function:
```cpp
if (wifiSSID.length() > 0) {
  connectToWiFi();
  if (wifiConnected) {
    syncNTPTime();
    if (isProvisioned && hasCertificates()) {
      setupMQTT();  // ← CALLED HERE (boot)
    }
  }
}
```
**When**: Once at boot if WiFi connects and device already provisioned
**Frequency**: ONCE per boot

2. **Line 965** - In `connectToWiFi()` function:
```cpp
if (WiFi.status() == WL_CONNECTED) {
  wifiConnected = true;
  // ... other code ...
  syncNTPTime();
  if (isProvisioned && hasCertificates()) {
    setupMQTT();  // ← CALLED HERE (WiFi connect)
  }
}
```
**When**: Every time `connectToWiFi()` successfully connects to WiFi
**Frequency**: MULTIPLE TIMES (every WiFi reconnect)

3. **Line 1216** - In `attemptProvisioning()` function:
```cpp
if (saveCertificates(certPem, keyPem)) {
  isProvisioned = true;
  // ... save config ...
  setupMQTT();  // ← CALLED HERE (after provisioning)
}
```
**When**: After successful HTTPS provisioning from backend
**Frequency**: ONCE per provisioning

### What setupMQTT() Does (Lines 984-1033):

```cpp
void setupMQTT() {
  // Line 985-987: Set mqttServer if not set
  if (mqttServer.length() == 0) {
    mqttServer = serverIP;
  }

  Serial.println("🔧 Configuring MQTT client...");
  Serial.println("📡 MQTT Server: " + mqttServer + ":" + mqttPort);

  // Line 996-1000: Load device certificates from SPIFFS
  if (!loadDeviceCertificate(deviceCertificate, devicePrivateKey)) {
    Serial.println("❌ Cannot setup MQTT - device certificates not found");
    return;
  }

  // Line 1015-1017: Set certificates using .c_str()
  wifiClient.setCACert(caCertificate.c_str());
  wifiClient.setCertificate(deviceCertificate.c_str());
  wifiClient.setPrivateKey(devicePrivateKey.c_str());

  // Line 1026-1029: Configure MQTT client
  mqttClient.setServer(mqttServer.c_str(), mqttPort.toInt());
  mqttClient.setCallback(onMqttMessage);
  mqttClient.setBufferSize(4096);
  mqttClient.setKeepAlive(15);

  // Line 1032: Connect to MQTT
  connectToMQTT();
}
```

### What loadDeviceCertificate() Does (Lines 169-199):

```cpp
bool loadDeviceCertificate(String& cert, String& key) {
  if (!SPIFFS.begin(true)) {
    return false;
  }

  // Read /device.crt from SPIFFS
  File certFile = SPIFFS.open("/device.crt", "r");
  if (!certFile) return false;
  cert = certFile.readString();  // ← READS FILE INTO GLOBAL STRING
  certFile.close();

  // Read /device.key from SPIFFS
  File keyFile = SPIFFS.open("/device.key", "r");
  if (!keyFile) return false;
  key = keyFile.readString();  // ← READS FILE INTO GLOBAL STRING
  keyFile.close();

  return true;
}
```

### What connectToMQTT() Does (Lines 1036-1093):

```cpp
void connectToMQTT() {
  if (!wifiConnected || !isProvisioned) return;

  // Lines 1044-1050: Print diagnostics
  Serial.println("\n🔍 === TLS HANDSHAKE DIAGNOSTICS ===");
  // ... prints heap, cert lengths ...

  // Line 1070: Attempt MQTT connection
  if (mqttClient.connect(clientId.c_str())) {
    // Subscribe to topics
    mqttClient.subscribe(assignTopic.c_str());
    mqttClient.subscribe(commandTopic.c_str());
  } else {
    Serial.println("❌ MQTT Connection failed, rc=" + String(mqttClient.state()));
  }
}
```

### Where sendVitals() Calls connectToMQTT() (Lines 1294-1300):

```cpp
void sendVitals() {
  if (!mqttClient.connected() || !isAssigned) {
    if (!mqttClient.connected()) {
      connectToMQTT();  // ← ONLY calls connectToMQTT(), NOT setupMQTT()
    }
    return;
  }
  // ... send vitals ...
}
```

---

## The Problem

### Current Behavior:

**Scenario 1: Device boots already provisioned**
1. Boot → `setup()` line 560 calls `setupMQTT()` ✅
   - Loads certs from SPIFFS → global strings
   - Calls `setCertificate()` with .c_str()
   - Attempts MQTT connection

**Scenario 2: WiFi reconnects** (THIS IS THE PROBLEM)
1. WiFi disconnects for any reason
2. WiFi reconnects → `connectToWiFi()` line 965 calls `setupMQTT()` ❌
   - **Loads certs AGAIN** from SPIFFS → global strings (I/O overhead)
   - **Calls `setCertificate()` AGAIN** with .c_str() (may overwrite pointers)
   - Attempts MQTT connection AGAIN

**Scenario 3: Fresh provisioning**
1. Captive portal → user configures WiFi
2. `connectToWiFi()` line 965 calls `setupMQTT()` (first time, but certs don't exist yet - returns early)
3. Later: `attemptProvisioning()` succeeds → line 1216 calls `setupMQTT()` ✅
   - Loads certs from SPIFFS → global strings
   - Calls `setCertificate()` with .c_str()
   - Attempts MQTT connection

**Scenario 4: MQTT disconnects** (NOT A PROBLEM)
1. MQTT connection lost
2. `sendVitals()` line 1297 calls `connectToMQTT()` ✅
   - Does NOT reload certs
   - Does NOT call `setCertificate()` again
   - Just attempts reconnection

### The Issue:

**Line 965 in `connectToWiFi()` calls `setupMQTT()` every time WiFi connects**, which means:

- Certificates are loaded from SPIFFS **MULTIPLE TIMES** (I/O overhead)
- `setCertificate()` is called **MULTIPLE TIMES** with .c_str() from global strings
- This is inefficient and **may cause pointer issues**

---

## Senior Tech Lead Analysis

### Question 1: Do I have a detailed failproof plan?

**YES**. The plan is:
1. Add a global flag `bool mqttConfigured = false`
2. Check flag at start of `setupMQTT()` - if already configured, skip cert loading
3. Set flag to `true` after first successful configuration
4. Reset flag when certificates change (re-provisioning, cert missing)

### Question 2: Have I thought of alternative plans?

**YES**. Three alternatives analyzed:

**Option A: Flag-based (RECOMMENDED)**
- Add `mqttConfigured` flag
- Skip cert loading if already configured
- Pros: Minimal changes, clear intent, easy to debug
- Cons: Need to remember to reset flag in edge cases

**Option B: Remove setupMQTT() from connectToWiFi()**
- Just don't call `setupMQTT()` at line 965
- Pros: Cleaner separation - WiFi doesn't trigger MQTT setup
- Cons: MQTT won't auto-reconnect after WiFi comes back

**Option C: Separate configure from connect**
- Split into `configureMQTT()` (once) and `connectToMQTT()` (many times)
- Pros: Perfect separation of concerns
- Cons: More refactoring, changes existing function names

### Question 3: Does the code conform to project guidelines?

**YES**:
- ✅ camelCase naming (`mqttConfigured`)
- ✅ No quick fixes - proper root cause fix
- ✅ Modular approach - flag controls behavior
- ✅ Comments explain why

### Question 4: Have I thought about fixes with logic and sense?

**YES**:
- Loading certs multiple times is wasteful (SPIFFS I/O is slow)
- Calling `setCertificate()` multiple times may cause pointer confusion
- The fix prevents both issues
- Edge cases handled (re-provisioning, cert missing)

### Question 5: Have I thought this out like a senior tech lead?

**YES**:
- **Root cause**: Line 965 calls setupMQTT() every WiFi reconnect
- **Proper fix**: Prevent reloading certs if already loaded
- **Not a hack**: Flag-based approach is industry standard
- **Maintainable**: Future developers will understand the intent
- **Testable**: Can verify certs only loaded once via serial logs

---

## Recommended Solution (Option A)

### Changes Required:

1. **Add flag at line 93** (after `int networkCount = 0;`):
```cpp
bool mqttConfigured = false;  // Track if MQTT certs already loaded
```

2. **Check flag in setupMQTT() at line 989** (after serial prints):
```cpp
void setupMQTT() {
  if (mqttServer.length() == 0) {
    mqttServer = serverIP;
  }

  // ✅ NEW: Skip if already configured
  if (mqttConfigured) {
    Serial.println("🔐 MQTT already configured (skipping cert reload)");
    connectToMQTT();  // Just attempt reconnection
    return;
  }

  Serial.println("🔧 Configuring MQTT client...");
  // ... rest of function ...
```

3. **Set flag at line 1031** (after MQTT client configured):
```cpp
  Serial.println("✅ MQTT client configured with certificates");
  mqttConfigured = true;  // ✅ NEW: Mark as configured
  connectToMQTT();
}
```

4. **Reset flag when certs missing at line 562**:
```cpp
if (isProvisioned && !hasCertificates()) {
  Serial.println("⚠️  Device marked as provisioned but certificates missing!");
  mqttConfigured = false;  // ✅ NEW: Reset flag
  isProvisioned = false;
  // ... rest of code ...
}
```

5. **Reset flag when certs missing at line 967**:
```cpp
} else if (isProvisioned && !hasCertificates()) {
  Serial.println("⚠️  Certificates missing - resetting provisioning");
  mqttConfigured = false;  // ✅ NEW: Reset flag
  isProvisioned = false;
  saveConfiguration();
}
```

6. **Reset flag before re-provisioning at line 1196**:
```cpp
if (saveCertificates(certPem, keyPem)) {
  // ... save CA cert ...
  mqttConfigured = false;  // ✅ NEW: Reset flag to reload new certs
  isProvisioned = true;
  provisioningInProgress = false;
  // ... rest of code ...
}
```

---

## Expected Behavior After Fix

### Scenario 1: Boot already provisioned
1. `setup()` → `setupMQTT()` called
2. `mqttConfigured = false` → Loads certs, sets flag to `true`
3. WiFi stays connected
4. **Result**: Certs loaded ONCE ✅

### Scenario 2: WiFi reconnects
1. WiFi disconnects
2. WiFi reconnects → `connectToWiFi()` → `setupMQTT()` called
3. `mqttConfigured = true` → Skips cert loading, just calls `connectToMQTT()`
4. **Result**: Certs NOT reloaded ✅

### Scenario 3: Fresh provisioning
1. Captive portal → WiFi connects → `setupMQTT()` called
2. No certs yet → returns early (flag stays `false`)
3. Provisioning succeeds → `setupMQTT()` called again
4. `mqttConfigured = false` → Loads certs, sets flag to `true`
5. **Result**: Certs loaded ONCE after provisioning ✅

### Scenario 4: Re-provisioning
1. Device already provisioned
2. New provisioning → `saveCertificates()` succeeds
3. Flag reset to `false` before calling `setupMQTT()`
4. `setupMQTT()` loads new certs, sets flag to `true`
5. **Result**: New certs loaded once ✅

### Scenario 5: Certs missing
1. Device marked as provisioned but no certs in SPIFFS
2. Code detects missing certs → resets flag to `false`
3. After re-provisioning → certs loaded again
4. **Result**: Flag properly reset ✅

---

## Testing Plan

### Test 1: Normal boot
1. Upload firmware
2. Device boots with saved WiFi
3. Check serial logs: "🔧 Configuring MQTT client..." appears ONCE
4. Check serial logs: "🔐 Loading certificates..." appears ONCE
5. **Expected**: Certs loaded once, flag set

### Test 2: WiFi reconnect
1. Device running, MQTT connected
2. Turn off router for 10 seconds
3. Turn router back on
4. WiFi reconnects
5. Check serial logs: "🔐 MQTT already configured (skipping cert reload)" appears
6. **Expected**: Certs NOT reloaded

### Test 3: Multiple WiFi disconnects
1. Device running
2. Turn router off/on 5 times
3. Check serial logs: "🔧 Configuring MQTT client..." appears only ONCE (at boot)
4. Check serial logs: "🔐 MQTT already configured..." appears 5 times (at reconnects)
5. **Expected**: Certs loaded once, reconnects skip loading

### Test 4: Fresh provisioning
1. Factory reset device (clear SPIFFS)
2. Captive portal setup
3. Enter WiFi credentials and provisioning code
4. Check serial logs: "🔧 Configuring MQTT client..." appears ONCE (after provisioning)
5. **Expected**: Certs loaded once after successful provisioning

---

## Conclusion

**Problem confirmed**: `setupMQTT()` is called multiple times (line 560, 965, 1216), each time reloading certificates from SPIFFS and calling `setCertificate()`.

**Root cause**: Line 965 in `connectToWiFi()` calls `setupMQTT()` every WiFi reconnect.

**Proper fix**: Add `mqttConfigured` flag to prevent reloading certificates multiple times.

**Benefits**:
- ✅ Certificates loaded from SPIFFS only ONCE (faster, less I/O)
- ✅ `setCertificate()` called only ONCE (no pointer confusion)
- ✅ Reconnects are faster (skip SPIFFS reads)
- ✅ Clean, maintainable code
- ✅ Handles all edge cases (re-provisioning, certs missing)

**Ready to implement**: Yes, all research done, plan is detailed and failproof.
