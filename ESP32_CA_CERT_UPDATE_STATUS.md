# ESP32 CA Certificate Update - Status Report

## Date: 2025-10-18

## What Was Done

### ✅ Successfully Replaced CA Certificate in ESP32 SPIFFS

**Old Certificate (WRONG):**
```
Issuer: C=IN, ST=Telangana, L=Hyderabad, O=Symbiot, OU=SymHMS Development, CN=192.168.0.113
Subject: C=IN, ST=Telangana, L=Hyderabad, O=Symbiot, OU=SymHMS Development, CN=192.168.0.113
```
This was the **backend SSL certificate**, NOT the Hospital CA certificate!

**New Certificate (CORRECT):**
```
Issuer: C=IN, ST=Telangana, L=Hyderabad, O=Symbiot, OU=SymHMS Development, CN=Symbiot Hospital CA
Subject: C=IN, ST=Telangana, L=Hyderabad, O=Symbiot, OU=SymHMS Development, CN=Symbiot Hospital CA
Valid: Oct 18 2025 - Oct 16 2035 (10 years)
Size: 2164 bytes
```
This is the **correct Hospital CA certificate** that signs both device certificates and Mosquitto server certificate.

### Steps Executed:
1. ✅ Copied `mosquitto/certs/hospital_ca.crt` → `esp32_hospital_watch_complete/data/ca.crt`
2. ✅ Verified certificate details with openssl
3. ✅ Uploaded SPIFFS to ESP32 via Arduino IDE
4. ✅ ESP32 successfully loaded new CA certificate (2164 bytes)

## Current Status: Re-Provisioning Required

### ESP32 Serial Output:
```
✅ CA certificate loaded from SPIFFS (2164 bytes)
✅ WiFi Connected!
❌ Missing provisioning code or server IP
```

### Why Re-Provisioning is Needed:

**Option 1: SPIFFS Upload Cleared Device Certificates**
When you upload SPIFFS data folder, it overwrites the ENTIRE SPIFFS filesystem. This means:
- ✅ New `ca.crt` was uploaded
- ❌ Device certificate (`device.crt`) was ERASED
- ❌ Device private key (`device.key`) was ERASED
- ❌ Provisioning metadata was lost

**Option 2: ESP32 Cleared Provisioning on Certificate Mismatch**
ESP32 may have detected that the CA certificate changed and automatically cleared provisioning data as a safety measure.

### What ESP32 Needs Now:
1. **Device Certificate** - Unique certificate for this ESP32 device
2. **Device Private Key** - Private key for device certificate
3. **Server IP** - Backend server IP address (192.168.0.113)
4. **MQTT Port** - MQTT broker port (8883)

These can ONLY be obtained through the provisioning process.

## Solution: Re-Provision ESP32

### Step 1: Generate New 6-Digit PIN
1. Open frontend Device Provisioning page
2. Click "Generate Provisioning PIN"
3. Copy the 6-digit PIN (valid for 10 minutes)

### Step 2: Factory Reset ESP32 (Optional but Recommended)
Clear all NVP storage to ensure clean state:
```cpp
// In Arduino IDE Serial Monitor, you could send a command, or just reflash
// Alternatively, the ESP32 should automatically enter provisioning mode since it's missing certificates
```

### Step 3: Connect to ESP32 Captive Portal
1. ESP32 should create "HospitalWatch" WiFi network
2. Connect to it from your phone/laptop
3. Browser should auto-open captive portal (192.168.4.1)
4. If not, manually navigate to http://192.168.4.1

### Step 4: Complete Provisioning
1. Enter WiFi credentials: SSID = "NETGEAR05"
2. Enter backend server IP: 192.168.0.113
3. Enter HTTP port: 8001
4. Enter MQTT port: 8883
5. Enter 6-digit PIN from Step 1
6. Click "Submit"

### Step 5: Verify Provisioning Success
ESP32 should show:
```
✅ Device certificates saved to SPIFFS
✅ CA certificate saved to SPIFFS
✅ DEVICE PROVISIONED via HTTPS!
🔐 Certificate saved to SPIFFS
🔐 Private key saved to SPIFFS
```

### Step 6: Verify MQTT Connection
After provisioning, ESP32 should automatically connect:
```
✅ Device certificates found in SPIFFS
✅ Device certificate loaded (1939 bytes)
✅ Device private key loaded (1700 bytes)
🔄 Connecting to MQTT with client certificate...
✅ MQTT Connected with client certificate (mTLS)!
📡 Subscribed to: hospital/devices/ESP32-WATCH-A0:A3:B3:AA:13:B0/assign
📡 Subscribed to: hospital/devices/ESP32-WATCH-A0:A3:B3:AA:13:B0/command
```

## Why This Happened: SPIFFS Data Folder Only Had CA Certificate

The `esp32_hospital_watch_complete/data/` folder contains:
- `ca.crt` - Hospital CA certificate (for verifying server)

**It does NOT contain:**
- `device.crt` - Device certificate (unique per device)
- `device.key` - Device private key (unique per device)

**Why?**
Device certificates are **dynamically generated** during provisioning:
1. Backend generates unique certificate for each device
2. Backend signs it with Hospital CA private key
3. Backend sends it to ESP32 over HTTPS
4. ESP32 saves it to SPIFFS (`/spiffs/device.crt` and `/spiffs/device.key`)

**When you upload SPIFFS from `data/` folder, it only contains `ca.crt`, so device certificates are erased.**

## Lessons Learned

### 1. SPIFFS Upload Erases Everything
Uploading SPIFFS data folder is **destructive** - it replaces the entire filesystem. Use with caution on provisioned devices.

### 2. Two Types of Certificates in ESP32:
- **Static CA Certificate** (`ca.crt`) - Same for all devices, can be in `data/` folder
- **Dynamic Device Certificates** (`device.crt`, `device.key`) - Unique per device, obtained during provisioning

### 3. Better Approach for CA Certificate Update
Instead of SPIFFS upload, we should have:
- Created OTA update that replaces just `ca.crt` file
- Or re-provisioned from the start (which we'll do now anyway)

## Files Modified

- [esp32_hospital_watch_complete/data/ca.crt](esp32_hospital_watch_complete/data/ca.crt) - Updated with correct Hospital CA

## Next Action Required

**🔴 USER ACTION NEEDED: Re-provision ESP32**

1. Generate 6-digit PIN from frontend Device Provisioning page
2. Connect to ESP32 captive portal (WiFi: "HospitalWatch")
3. Complete provisioning form with WiFi credentials and PIN
4. Verify MQTT connection success

Once re-provisioned with the **correct CA certificate**, ESP32 will successfully:
- Verify Mosquitto server certificate ✅
- Establish mTLS connection ✅
- Subscribe to MQTT topics ✅
- Send/receive device data ✅

---
**Status:** Waiting for user to complete re-provisioning
**Blocker:** Device certificates erased by SPIFFS upload (expected behavior)
**Resolution:** Re-provision ESP32 with new PIN
