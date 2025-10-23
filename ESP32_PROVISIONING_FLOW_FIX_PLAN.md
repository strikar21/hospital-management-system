# ESP32 Provisioning Flow Fix Plan

## Problem
ESP32 saves WiFi credentials immediately when submitting captive portal form, even if provisioning fails. On reboot, it connects to WiFi but captive portal doesn't start, making the device inaccessible.

## Root Cause
In `handleConfigure()` (line 803-858), the code calls `saveConfiguration()` (line 821) which permanently saves WiFi credentials **before** provisioning succeeds.

## Solution
Change the provisioning flow to only save WiFi credentials AFTER successful certificate provisioning.

---

## Changes Required

### 1. handleConfigure() - Line 803-858
**Current behavior:**
- Saves WiFi credentials immediately (line 821)
- Then attempts to connect to WiFi

**New behavior:**
- Save provisioning code to prefs (keep this)
- Do NOT call `saveConfiguration()` yet
- Store WiFi/server config in memory only
- Connect to WiFi
- Wait for provisioning to complete
- Only save if provisioning succeeds

**Code change:**
```cpp
void handleConfigure() {
  wifiSSID = server.arg("wifi_ssid");
  wifiPassword = server.arg("wifi_pass");
  serverIP = server.arg("server_ip");
  serverPort = server.arg("http_port");
  mqttServer = serverIP;
  mqttPort = server.arg("mqtt_port");
  String provCode = server.arg("prov_code");

  if (wifiSSID.length() == 0 || serverIP.length() == 0 || provCode.length() != 6) {
    server.send(400, "text/html",
      "<html><body><h2>❌ Error</h2><p>WiFi SSID, Server IP, and valid 6-digit PIN are required!</p>"
      "<a href='/'>← Go Back</a></body></html>");
    return;
  }

  // ✅ ONLY save provisioning code - NOT WiFi credentials yet
  prefs.putString("prov_code", provCode);
  // ❌ REMOVED: saveConfiguration(); // Don't save WiFi yet!

  Serial.println("📝 Configuration received (not saved yet):");
  Serial.println("   WiFi SSID: " + wifiSSID);
  Serial.println("   Server IP: " + serverIP);
  Serial.println("   Provisioning Code: " + provCode);

  // Send response page
  String html = "..."; // Keep existing HTML
  server.send(200, "text/html", html);

  delay(1000);
  connectToWiFi();
  // WiFi credentials will be saved in attemptProvisioning() on success
}
```

### 2. attemptProvisioning() - Line 1063-1160
**Add save on success:**

After line 1125 `saveConfiguration();`, that call already exists and saves everything including WiFi credentials. This is correct.

After line 1145 (failure case), add:
```cpp
} else {
  Serial.println("❌ Failed to save certificates");

  // ✅ Clear WiFi credentials and restart captive portal
  Serial.println("⚠️ Provisioning failed - clearing WiFi and restarting portal");
  wifiSSID = "";
  wifiPassword = "";
  serverIP = "";
  prefs.remove("prov_code");
  // Don't save - just restart
  provisioningInProgress = false;

  delay(2000);
  ESP.restart();  // Restart to captive portal
}
```

After line 1156 (HTTP error case), add:
```cpp
    Serial.println("❌ Provisioning failed, HTTP code: " + String(httpCode));
    if (httpCode > 0) {
      Serial.println("Response: " + http.getString());
    }

    // ✅ Clear provisioning code to retry with new code
    prefs.remove("prov_code");
    provisioningInProgress = false;

    // If provisioning fails, device will stay connected to WiFi
    // User can access /status page to see error
    // Or they can restart device to go back to captive portal
```

### 3. setup() - Line 510-567
**Add certificate check on boot:**

Already exists! Lines 548-555 check for certificates and reset provisioning status if missing. Good!

But we need to also **clear WiFi credentials** and restart captive portal:

```cpp
} else if (isProvisioned && !hasCertificates()) {
  Serial.println("⚠️  Device marked as provisioned but certificates missing!");
  Serial.println("⚠️  Clearing WiFi and resetting provisioning...");
  isProvisioned = false;

  // ✅ Clear WiFi credentials
  wifiSSID = "";
  wifiPassword = "";
  serverIP = "";
  prefs.remove("ssid");
  prefs.remove("pass");
  prefs.remove("ip");
  prefs.remove("prov_code");
  saveConfiguration();

  // Restart to captive portal
  delay(2000);
  ESP.restart();
}
```

### 4. connectToWiFi() - Line 904-953
**Add check after WiFi connection fails:**

Lines 946-952 already restart captive portal on WiFi failure. Good!

But also add a check for missing certificates after WiFi succeeds:

```cpp
if (WiFi.status() == WL_CONNECTED) {
  wifiConnected = true;
  digitalWrite(2, HIGH);

  Serial.println("\n✅ WiFi Connected!");
  Serial.println("🌐 IP Address: " + WiFi.localIP().toString());

  server.on("/", handleStatus);
  server.begin();

  syncNTPTime();

  // ✅ v5.0: Check for certificates before connecting
  if (isProvisioned && hasCertificates()) {
    setupMQTT();
  } else if (isProvisioned && !hasCertificates()) {
    Serial.println("⚠️  Certificates missing - resetting provisioning");
    isProvisioned = false;

    // ✅ Clear WiFi and restart to captive portal
    wifiSSID = "";
    wifiPassword = "";
    prefs.remove("ssid");
    prefs.remove("pass");
    prefs.remove("prov_code");
    saveConfiguration();

    delay(2000);
    ESP.restart();
  }
} else {
  // WiFi failed - restart captive portal (already correct)
}
```

---

## Summary of Changes

1. **handleConfigure()**: Remove `saveConfiguration()` call - only save provisioning code
2. **attemptProvisioning()**: On failure, clear WiFi credentials and restart device
3. **setup()**: If no certificates but WiFi saved, clear WiFi and restart to captive portal
4. **connectToWiFi()**: After WiFi connects, if no certificates, clear WiFi and restart

## Testing Flow

### Scenario 1: Successful Provisioning
1. ESP32 starts captive portal
2. User enters WiFi + PIN
3. ESP32 connects to WiFi (credentials in memory only)
4. Provisioning succeeds, certificates saved
5. `saveConfiguration()` called - WiFi credentials now permanently saved ✅
6. MQTT connects with certificate

### Scenario 2: Provisioning Fails (bad PIN)
1. ESP32 starts captive portal
2. User enters WiFi + bad PIN
3. ESP32 connects to WiFi (credentials in memory only)
4. Provisioning fails (HTTP 401)
5. Provisioning code cleared
6. Device stays connected to WiFi, user can see error at /status
7. User can restart device manually → goes back to captive portal ✅

### Scenario 3: Provisioning Fails (500 error)
1. ESP32 starts captive portal
2. User enters WiFi + PIN
3. ESP32 connects to WiFi
4. Provisioning fails (HTTP 500)
5. Provisioning code cleared
6. Device stays connected to WiFi, user can see error
7. User restarts device → goes back to captive portal ✅

### Scenario 4: Power cycle after failed provision
1. Previous provision failed but WiFi was saved
2. ESP32 reboots
3. `setup()` checks: WiFi saved but no certificates
4. Clears WiFi credentials
5. Restarts to captive portal ✅

---

## Implementation

Apply these 4 changes to `esp32_hospital_watch_complete.ino` and test with intentionally bad PIN to verify captive portal restarts properly.
