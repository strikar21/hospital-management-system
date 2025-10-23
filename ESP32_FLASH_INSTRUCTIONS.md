# ESP32 Hospital Watch v4.1.0 TLS - Complete Setup Guide

## 📋 Overview

**New Firmware:** `esp32_hospital_watch_v4_1_TLS.ino`
**Version:** 4.1.0
**MQTT Port:** 8883 (TLS encrypted)
**Status:** ✅ Backend connected to MQTT broker, ready for ESP32

---

## 🛠️ Required Hardware & Software

### Hardware:
- ESP32 Development Board
- USB Cable (data + power)
- Computer (Windows/Mac/Linux)

### Software:
1. **Arduino IDE** (version 1.8.x or 2.x)
   - Download: https://www.arduino.cc/en/software

2. **ESP32 Board Support**
   - Already installed if you've been using Arduino IDE with ESP32

3. **Required Libraries** (Install via Arduino Library Manager):
   - `WiFi` (built-in)
   - `WebServer` (built-in)
   - `DNSServer` (built-in)
   - `HTTPClient` (built-in)
   - `ArduinoJson` (by Benoit Blanchon) - v7.x
   - `Preferences` (built-in)
   - `PubSubClient` (by Nick O'Leary) - v2.8
   - `WiFiClientSecure` (built-in)

---

## 📂 Step 1: Locate the Firmware

**File Path:**
```
C:\Users\Srika\OneDrive\Desktop\hospital-management-system\esp32_hospital_watch_complete\esp32_hospital_watch_v4_1_TLS.ino
```

**Or use the file I just created:**
- `esp32_hospital_watch_v4_1_TLS.ino` (complete TLS-enabled version)

---

## 🔧 Step 2: Open in Arduino IDE

1. **Launch Arduino IDE**

2. **Open the firmware:**
   - File → Open
   - Navigate to: `C:\Users\Srika\OneDrive\Desktop\hospital-management-system\esp32_hospital_watch_complete\`
   - Select: `esp32_hospital_watch_v4_1_TLS.ino`
   - Click **Open**

3. **Verify the file opened correctly:**
   - You should see the code with version "4.1.0" at the top
   - Check for `#include <WiFiClientSecure.h>` (line 32)
   - Check for `const char* CA_CERT` certificate definition (starts around line 44)

---

## ⚙️ Step 3: Configure Arduino IDE

### 3.1 Select Board:
1. **Tools → Board → ESP32 Arduino**
2. Select: **ESP32 Dev Module** (or your specific ESP32 board)

### 3.2 Configure Board Settings:
- **Upload Speed:** 921600
- **CPU Frequency:** 240MHz (WiFi/BT)
- **Flash Frequency:** 80MHz
- **Flash Mode:** QIO
- **Flash Size:** 4MB (32Mb)
- **Partition Scheme:** Default 4MB with spiffs
- **Core Debug Level:** None (or "Info" for debugging)
- **PSRAM:** Disabled (unless your board has PSRAM)

### 3.3 Select Port:
1. **Connect ESP32 to computer via USB**
2. **Tools → Port**
3. Select the COM port showing your ESP32 (usually **COM3** or **COM4** on Windows)
   - On Windows: `COM3`, `COM4`, etc.
   - On Mac/Linux: `/dev/ttyUSB0` or `/dev/cu.usbserial-*`

---

## 🔍 Step 4: Install Required Libraries (if missing)

1. **Open Library Manager:**
   - Tools → Manage Libraries (or Ctrl+Shift+I)

2. **Install ArduinoJson:**
   - Search: `ArduinoJson`
   - Install version **7.x** by Benoit Blanchon
   - Click **Install**

3. **Install PubSubClient:**
   - Search: `PubSubClient`
   - Install version **2.8** by Nick O'Leary
   - Click **Install**

4. **Verify built-in libraries are available:**
   - WiFi ✅ (built-in)
   - WebServer ✅ (built-in)
   - DNSServer ✅ (built-in)
   - HTTPClient ✅ (built-in)
   - Preferences ✅ (built-in)
   - WiFiClientSecure ✅ (built-in)

---

## ✅ Step 5: Verify/Compile the Code

1. **Click the ✓ (Verify) button** in Arduino IDE
   - Or: Sketch → Verify/Compile
   - Or: Ctrl+R

2. **Wait for compilation** (takes 30-60 seconds)

3. **Check for "Done compiling" message** at the bottom
   - Should show: `Sketch uses X bytes (Y%) of program storage space`

4. **If you see errors:**
   - Missing libraries? → Install them (Step 4)
   - Wrong board selected? → Check board settings (Step 3.1)
   - Syntax errors? → Make sure you opened the correct `.ino` file

---

## ⬆️ Step 6: Upload to ESP32

### 6.1 Prepare ESP32:
1. **Connect ESP32 via USB**
2. **Hold the BOOT button** on ESP32 (optional, some boards require this)

### 6.2 Upload:
1. **Click the → (Upload) button** in Arduino IDE
   - Or: Sketch → Upload
   - Or: Ctrl+U

2. **Wait for upload** (takes 60-120 seconds)
   - You'll see: "Connecting........"
   - Then: "Writing at 0x00001000..."
   - Progress bar will show upload status

3. **If "Connecting..." hangs:**
   - **Hold the BOOT button** on ESP32
   - Click Upload again while holding BOOT
   - Release BOOT after "Connecting..." succeeds

4. **Wait for "Done uploading" message**

### 6.3 Monitor Serial Output:
1. **Open Serial Monitor:**
   - Tools → Serial Monitor
   - Or: Ctrl+Shift+M

2. **Set baud rate to 115200**

3. **Press RST button** on ESP32 to restart

4. **You should see:**
   ```
   🏥 ESP32 Hospital Watch v4.1.0 (TLS + 8 Device Alerts)
   =======================================================
   ✨ MQTT TLS 1.2 | Port 8883 | VITALS FIXED
   📱 MAC Address: XX:XX:XX:XX:XX:XX
   🌐 Starting Captive Portal...
   📡 Captive Portal Network: HospitalWatch
   🌍 Access Point IP: 192.168.4.1
   💡 Connect to WiFi and go to any website to configure
   ```

---

## 📱 Step 7: Provision the ESP32 Watch

### 7.1 Connect to ESP32 Hotspot:
1. **On your phone/laptop:**
   - Open WiFi settings
   - Connect to: **HospitalWatch**
   - Password: (none - open network)

2. **Open browser**
   - Type any URL (e.g., `google.com`)
   - Captive portal will appear automatically
   - Or manually go to: `http://192.168.4.1`

### 7.2 Fill Provisioning Form:

**WiFi Configuration:**
- **WiFi Network:** [Select your WiFi from dropdown]
- **WiFi Password:** [Enter your WiFi password]

**Hospital Server:**
- **Server IP Address:** `192.168.0.113` ✅
- **HTTP Port:** `8001` ✅
- **MQTT Port:** `8883` ✅ (**IMPORTANT: TLS port**)

**Provisioner Credentials:**
- **Provisioner ID:** `TEC0001` ✅
- **Provisioner Password:** `tech123` ✅

### 7.3 Click "Configure & Connect"

---

## 🎯 Step 8: Verify Connection

### 8.1 Monitor Serial Output:
You should see this sequence:

```
📝 Configuration received:
   WiFi SSID: YourWiFiName
   Server IP: 192.168.0.113
   HTTP Port: 8001
   MQTT Port: 8883
   Provisioner: TEC0001

🔌 Connecting to WiFi: YourWiFiName
...
✅ WiFi Connected!
🌐 IP Address: 192.168.0.XXX
📡 Signal Strength: -XX dBm

🕐 Syncing time with NTP...
✅ NTP synced: Wed Oct 16 20:XX:XX 2025

🔄 Attempting device provisioning...
📤 POST http://192.168.0.113:8001/api/v1/esp32/provision
✅ Provision Response: {"success":true,"deviceId":"DEV_WATCH_001","serialNumber":"SN_XXXX"}

🎉 DEVICE PROVISIONED!
   📱 Device ID: DEV_WATCH_001
   📋 Serial: SN_XXXX

🔧 Setting up MQTT TLS connection...
📡 MQTT Server: 192.168.0.113:8883
🔄 Connecting to MQTT TLS broker as: HospitalWatch_DEV_WATCH_001
✅ MQTT TLS Connected!
📡 Subscribed to: hospital/devices/DEV_WATCH_001/assign
📡 Subscribed to: hospital/devices/DEV_WATCH_001/command
```

### 8.2 Check Backend Logs:
On your backend terminal, you should see:
```
New client connected from 192.168.0.XXX:XXXXX as HospitalWatch_DEV_WATCH_001
```

---

## 🏥 Step 9: Assign to Patient (Optional Testing)

### 9.1 Via Backend API:
```bash
curl -X POST http://localhost:8001/api/v1/devices/DEV_WATCH_001/assign \
  -H "Content-Type: application/json" \
  -d '{"patientId": "PAT_123"}'
```

### 9.2 Watch Serial Monitor:
```
📨 MQTT Message: hospital/devices/DEV_WATCH_001/assign -> {"patientId":"PAT_123"}
👤 Assigned to patient: PAT_123
💾 Configuration saved

📊 Vitals: HR=75, Temp=37.0°C, SpO2=98%, RR=16
💓 MQTT Heartbeat sent
```

---

## 🎉 SUCCESS INDICATORS

### ✅ ESP32 Watch:
- Green LED stays ON (connected)
- Serial shows vitals every 1 second
- Serial shows heartbeat every 30 seconds

### ✅ Backend:
- Mosquitto logs show client connected
- Backend MQTT service shows vitals received
- No certificate errors in logs

### ✅ Database:
- New device record created in `devices` table
- Vitals stored in TimescaleDB `vitals_realtime` table

---

## 🐛 Troubleshooting

### Problem: "Connecting..." hangs during upload
**Solution:** Hold BOOT button on ESP32 while clicking Upload

### Problem: "Failed to connect to WiFi"
**Solution:**
- Check WiFi password is correct
- Ensure WiFi is 2.4GHz (ESP32 doesn't support 5GHz)
- Check router allows new devices

### Problem: "MQTT Connection failed, rc=-2"
**Solution:**
- Check MQTT port is 8883 (not 1883)
- Verify backend MQTT service is running: `docker ps | grep mosquitto`
- Check firewall allows port 8883

### Problem: "❌ Provisioning failed: Invalid provisioner credentials"
**Solution:**
- Use `TEC0001` / `tech123` (case sensitive)
- Check backend database has TEC0001 user:
  ```sql
  SELECT id, role FROM staff WHERE id = 'TEC0001';
  ```

### Problem: "⚠️ NTP sync failed"
**Solution:**
- Check internet connection
- ESP32 needs internet access for NTP (pool.ntp.org)
- If behind firewall, allow UDP port 123

### Problem: Certificate verification errors
**Solution:**
- Firmware already has correct CA certificate embedded
- Backend certificate was regenerated with SANs
- If still failing, check Mosquitto is using new certificate

---

## 📊 Monitoring & Logs

### ESP32 Serial Monitor:
```bash
# Arduino IDE: Tools → Serial Monitor (115200 baud)
```

### Backend MQTT Logs:
```bash
docker logs hospital-mosquitto --follow
```

### Backend Python Logs:
```bash
cd hospital-backend
python main.py
# Look for: "✅ MQTT service started"
```

### Database Vitals Query:
```sql
SELECT * FROM vitals_realtime
WHERE "deviceId" = 'DEV_WATCH_001'
ORDER BY timestamp DESC
LIMIT 10;
```

---

## 🔒 Security Summary

✅ **TLS 1.2** - All MQTT traffic encrypted
✅ **CA Certificate** - Embedded in firmware
✅ **Port 8883** - Secure MQTT port
✅ **Staff Authentication** - Provisioner credentials required (TEC0001)
✅ **ISO 8601 Timestamps** - Proper time synchronization
✅ **7 Vitals Bugs Fixed** - Correct data format for backend

---

## 📝 Next Steps After Flashing

1. **Flash firmware** to ESP32 (Steps 1-6)
2. **Provision watch** via captive portal (Step 7)
3. **Verify connection** via serial monitor (Step 8)
4. **Assign to patient** via backend API (Step 9)
5. **Monitor vitals** in backend logs and database

**You're done!** 🎉

The ESP32 watch is now:
- ✅ Connected to WiFi
- ✅ Authenticated with backend (TEC0001)
- ✅ Connected to MQTT broker via TLS (port 8883)
- ✅ Sending vitals every 1 second
- ✅ Sending heartbeats every 30 seconds
- ✅ Ready to be assigned to patients!
