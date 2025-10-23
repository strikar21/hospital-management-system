# ESP32 SPIFFS Certificate Upload Guide

## Overview

The ESP32 firmware now loads the CA certificate from the SPIFFS file system instead of having it embedded in the code. This makes it easier to update certificates without recompiling firmware.

## What Changed

### ✅ Before (v4.1.0 - Inline Certificate)
```cpp
const char* CA_CERT = \
"-----BEGIN CERTIFICATE-----\n" \
"MIIFnzCCA4egAwIBAgIUSN1JkAu/DkfYy8VcJFNZ8l0WAEkwDQ...\n" \
// 30+ lines of certificate data
"-----END CERTIFICATE-----\n";
```

### ✅ After (v4.2.0 - File-Based Certificate)
```cpp
const char* CA_CERT_PATH = "/ca.crt";
String caCertificate = "";  // Loaded from SPIFFS at startup
```

## Benefits

1. **No Recompilation**: Update certificates without reflashing firmware
2. **Smaller Firmware**: Certificate not embedded in compiled code
3. **Easier Management**: Just upload new certificate file
4. **Production Ready**: Separate certificate from code

## Prerequisites

### 1. Install ESP32 File System Uploader Plugin

**For Arduino IDE 1.x:**
1. Download ESP32FS plugin from: https://github.com/me-no-dev/arduino-esp32fs-plugin/releases
2. Extract to `<Arduino>/tools/ESP32FS/tool/esp32fs.jar`
3. Restart Arduino IDE
4. You should see **Tools → ESP32 Sketch Data Upload**

**For Arduino IDE 2.x:**
1. Install "arduino-esp32fs-plugin" from Extensions
2. Or use command line tool `esptool.py`

### 2. Certificate File Location

The certificate file is already prepared at:
```
esp32_hospital_watch_complete/data/ca.crt
```

This is a copy of the Mosquitto CA certificate from `mosquitto/certs/ca.crt`.

## Step-by-Step Upload Instructions

### Method 1: Using Arduino IDE Plugin (Recommended)

#### Step 1: Prepare Data Folder
Your data folder should contain:
```
esp32_hospital_watch_complete/
├── esp32_hospital_watch_complete.ino
└── data/
    └── ca.crt  ← Certificate file (already created)
```

#### Step 2: Upload to SPIFFS
1. Open Arduino IDE
2. Open `esp32_hospital_watch_complete.ino`
3. Connect ESP32 via USB
4. Select correct **Board** and **Port** from Tools menu
5. Go to **Tools → ESP32 Sketch Data Upload**
6. Wait for upload to complete (takes 10-30 seconds)

You should see:
```
SPIFFS Image: /tmp/image.bin
Uploading SPIFFS image to ESP32...
SPIFFS uploaded successfully!
```

#### Step 3: Verify Upload
1. Upload the firmware sketch (Ctrl+U or Upload button)
2. Open Serial Monitor (115200 baud)
3. Press ESP32 reset button
4. Look for:
```
📂 Loading CA certificate from SPIFFS...
✅ CA certificate loaded from SPIFFS (1850 bytes)
```

### Method 2: Using esptool.py (Command Line)

If the Arduino IDE plugin doesn't work, use command line:

#### Step 1: Install esptool
```bash
pip install esptool
```

#### Step 2: Create SPIFFS Image
```bash
# Install mkspiffs tool
# Download from: https://github.com/igrr/mkspiffs/releases

# Create SPIFFS image
mkspiffs -c esp32_hospital_watch_complete/data -b 4096 -p 256 -s 0x170000 spiffs.bin
```

#### Step 3: Find ESP32 Port
**Windows:**
```bash
# Check Device Manager → Ports (COM & LPT)
# Usually COM3, COM4, COM5, etc.
```

**Linux/Mac:**
```bash
ls /dev/tty* | grep -E "(USB|ACM)"
```

#### Step 4: Upload SPIFFS Image
```bash
# Replace COM3 with your port
esptool.py --chip esp32 --port COM3 --baud 921600 write_flash 0x290000 spiffs.bin
```

### Method 3: Using PlatformIO (If Using PlatformIO)

Add to `platformio.ini`:
```ini
[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino
board_build.filesystem = spiffs
```

Then run:
```bash
pio run --target uploadfs
```

## Verification

### 1. Check Serial Output

After uploading and resetting ESP32, you should see:

```
🏥 ESP32 Hospital Watch v4.2.0 (TLS + SPIFFS Certificate)
=======================================================
✨ MQTT TLS 1.2 | Port 8883 | Certificate from File

📂 Loading CA certificate from SPIFFS...
✅ CA certificate loaded from SPIFFS (1850 bytes)
📱 MAC Address: XX:XX:XX:XX:XX:XX
```

### 2. If Certificate Not Found

If you see:
```
📂 Loading CA certificate from SPIFFS...
❌ CA certificate file not found: /ca.crt
💡 Please upload ca.crt to SPIFFS
⚠️ WARNING: CA certificate not loaded - TLS will fail!
```

**Solutions:**
1. Verify `data/ca.crt` exists in sketch folder
2. Re-upload SPIFFS using Arduino IDE plugin
3. Check that SPIFFS size is configured (Tools → Partition Scheme → select one with SPIFFS)

### 3. Test MQTT Connection

After certificate is loaded, connect to WiFi and provision the device:

1. Connect to "HospitalWatch" WiFi network
2. Browser should open automatically to 192.168.4.1
3. Configure WiFi and server settings
4. Provision with TEC0001 / tech123
5. Watch Serial Monitor for:
```
🔧 Setting up MQTT TLS connection...
📡 MQTT Server: 192.168.0.113:8883
🔐 TLS configured with CA certificate from SPIFFS
✅ MQTT TLS Connected!
```

## Partition Scheme

Make sure your ESP32 has SPIFFS enabled:

**Arduino IDE:**
- Go to **Tools → Partition Scheme**
- Select one of:
  - "Default 4MB with spiffs (1.2MB APP/1.5MB SPIFFS)"
  - "Huge APP (3MB No OTA/1MB SPIFFS)"
  - "Minimal SPIFFS (1.9MB APP with OTA/190KB SPIFFS)"

**Note:** We only need ~2KB for the certificate, so any SPIFFS partition works.

## Updating Certificate in Future

When you need to update the certificate (e.g., when it expires):

1. Replace `esp32_hospital_watch_complete/data/ca.crt` with new certificate
2. Upload SPIFFS again using Arduino IDE plugin
3. **No need to reflash firmware!** Just reset ESP32

The device will automatically load the new certificate on next boot.

## Troubleshooting

### Issue 1: "ESP32 Sketch Data Upload" Not in Tools Menu

**Solution:**
- Reinstall ESP32FS plugin
- Make sure it's in `<Arduino>/tools/ESP32FS/tool/esp32fs.jar`
- Restart Arduino IDE

### Issue 2: Upload Fails with "Timed Out"

**Solution:**
1. Hold BOOT button on ESP32
2. Click Upload
3. Release BOOT when upload starts

### Issue 3: Certificate Loads But MQTT Still Fails (rc=-2)

**Possible causes:**
1. **Wrong certificate file** - Make sure it's the CA certificate, not server certificate
2. **File corruption** - Check file size matches original (~1850 bytes)
3. **SPIFFS not formatted** - First upload might need SPIFFS.format()

**Fix:**
Add to setup() temporarily:
```cpp
SPIFFS.format();  // Format SPIFFS
```
Then re-upload SPIFFS image.

### Issue 4: SPIFFS Mount Failed

**Error:**
```
❌ SPIFFS mount failed
```

**Solution:**
- Check partition scheme has SPIFFS enabled
- Erase flash: Tools → Erase Flash → All Flash Contents
- Upload SPIFFS again
- Upload firmware again

## File Structure Summary

```
esp32_hospital_watch_complete/
├── esp32_hospital_watch_complete.ino  ← Main firmware (v4.2.0)
└── data/                               ← SPIFFS data folder
    └── ca.crt                          ← CA certificate (1850 bytes)
```

After upload, ESP32 SPIFFS will contain:
```
/ (root)
└── ca.crt  ← Loaded at startup
```

## Certificate Details

**File:** `ca.crt`
**Size:** ~1850 bytes
**Type:** PEM-encoded X.509 CA certificate
**Issuer:** SymbiotMQTTCA
**Valid Until:** 2035-10-14

## Next Steps

After successful SPIFFS upload:

1. ✅ Upload firmware (`esp32_hospital_watch_complete.ino`)
2. ✅ Connect to "HospitalWatch" WiFi
3. ✅ Configure via captive portal
4. ✅ Provision device
5. ✅ Verify MQTT TLS connection
6. ✅ Device is ready for production!

## Benefits Recap

✨ **Production Benefits:**
- Certificates can be updated remotely (just upload new SPIFFS image)
- No source code changes needed for certificate updates
- Smaller firmware binary
- Industry-standard approach for embedded TLS
- Easy certificate rotation for security compliance