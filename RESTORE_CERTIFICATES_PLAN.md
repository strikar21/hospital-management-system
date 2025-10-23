# Plan: Re-enable Certificate Security

## What We Disabled During Testing

### ESP32 Firmware
1. ✅ CA certificate - currently BYPASSED with `setInsecure()`
2. ✅ Client certificate - currently COMMENTED OUT
3. ✅ Client private key - currently COMMENTED OUT

### Mosquitto Config
1. ✅ Client certificate requirement - `require_certificate false`
2. ✅ Certificate-based username - `use_identity_as_username false`
3. ✅ Anonymous connections - `allow_anonymous true`

---

## Restore Plan (Step by Step)

### Step 1: ESP32 Firmware - Enable CA Certificate
**File:** `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`
**Line:** 1006-1009

**Change FROM:**
```cpp
wifiClient.setInsecure();  // TESTING
Serial.println("   ⚠️ INSECURE MODE FORCED");
```

**Change TO:**
```cpp
if (caCertificate.length() > 0) {
  wifiClient.setCACert(caCertificate.c_str());
  Serial.println("   ✅ CA cert set");
} else {
  Serial.println("⚠️ WARNING: No CA certificate - using insecure mode!");
  wifiClient.setInsecure();
}
```

**Test:** ESP32 should connect with CA cert validation

---

### Step 2: ESP32 Firmware - Enable Client Certificates
**File:** `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`
**Line:** 1012-1020

**Change FROM:**
```cpp
// ⚠️ TEMPORARILY DISABLED FOR TESTING (errno 113 debug)
// wifiClient.setCertificate(deviceCertificate.c_str());
// wifiClient.setPrivateKey(devicePrivateKey.c_str());
Serial.println("   ⚠️ CLIENT CERT DISABLED");
```

**Change TO:**
```cpp
if (deviceCertificate.length() > 0 && devicePrivateKey.length() > 0) {
  wifiClient.setCertificate(deviceCertificate.c_str());
  Serial.println("   ✅ Device cert set");

  wifiClient.setPrivateKey(devicePrivateKey.c_str());
  Serial.println("   ✅ Private key set");
} else {
  Serial.println("⚠️ WARNING: No client certificate - server may reject connection");
}
```

**Test:** ESP32 should connect with full mTLS

---

### Step 3: Mosquitto - Require Client Certificates
**File:** `mosquitto/config/mosquitto.conf`
**Line:** 37

**Change FROM:**
```conf
require_certificate false  # Was: true
```

**Change TO:**
```conf
require_certificate true
```

**Test:** Mosquitto should require client certificates

---

### Step 4: Mosquitto - Enable Certificate-Based Username
**File:** `mosquitto/config/mosquitto.conf`
**Line:** 42

**Change FROM:**
```conf
use_identity_as_username false
```

**Change TO:**
```conf
use_identity_as_username true
```

**Test:** Mosquitto should extract username from certificate CN

---

### Step 5: Mosquitto - Disable Anonymous Access
**File:** `mosquitto/config/mosquitto.conf`
**Line:** 58

**Change FROM:**
```conf
allow_anonymous true
```

**Change TO:**
```conf
allow_anonymous false
```

**Test:** Mosquitto should reject connections without certificates

---

## Testing Order

### Test 1: ESP32 with CA Cert Only
1. Restore Step 1 (CA cert in ESP32)
2. Upload to ESP32
3. Check if it connects
4. **Expected:** Should connect (Mosquitto still allows anonymous)

### Test 2: ESP32 with Full mTLS (Client Cert)
1. Restore Step 2 (client cert in ESP32)
2. Upload to ESP32
3. Check if it connects
4. **Expected:** Should connect (Mosquitto not requiring yet)

### Test 3: Mosquitto Requires Client Cert
1. Restore Step 3 (require_certificate true)
2. Restart Mosquitto
3. Check if ESP32 stays connected
4. **Expected:** ESP32 should maintain connection with client cert

### Test 4: Certificate-Based Username
1. Restore Step 4 (use_identity_as_username true)
2. Restart Mosquitto
3. Check Mosquitto logs for username
4. **Expected:** Should show "ESP32-WATCH-A0:A3:B3:AA:13:B0" as username

### Test 5: Disable Anonymous
1. Restore Step 5 (allow_anonymous false)
2. Restart Mosquitto
3. Try connecting without certificate (should fail)
4. ESP32 with certificate should still work
5. **Expected:** Only certificate-based clients can connect

---

## Rollback Plan

If any step breaks connectivity:
1. Revert the last change
2. Restart Mosquitto or re-upload ESP32 firmware
3. Verify ESP32 reconnects
4. Document what failed

---

## Ready to Start?

**First step:** Restore CA certificate in ESP32 firmware (Step 1)
