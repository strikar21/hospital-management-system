# MQTT Connectivity Testing Guide

## Current Mosquitto Status
- **Host IP**: 192.168.0.113
- **Port**: 8883 (TLS/SSL)
- **Version**: Mosquitto 1.6
- **TLS**: 1.2 only
- **Client Cert Required**: No (disabled for testing)
- **Anonymous**: Allowed

---

## Option 1: Test from Windows CMD (Recommended)

### Step 1: Install MQTT Client Tool

**Option A: MQTT Explorer (GUI - Easiest)**
1. Download from: https://mqtt-explorer.com/
2. Install and open
3. Configure connection:
   - **Name**: Hospital Mosquitto
   - **Host**: 192.168.0.113
   - **Port**: 8883
   - **Protocol**: mqtt (or mqtts)
   - **Username**: (leave blank - anonymous allowed)
   - **Password**: (leave blank)
   - **Encryption**: TLS
   - **Validate certificate**: NO (uncheck)
4. Click "Connect"

**Option B: mosquitto_sub/pub (Command Line)**
1. Download Mosquitto Windows installer: https://mosquitto.org/download/
2. Install to `C:\Program Files\mosquitto\`
3. Add to PATH or use full path

### Step 2: Test Connection from CMD

```cmd
# Test subscribe (listens for messages)
"C:\Program Files\mosquitto\mosquitto_sub.exe" -h 192.168.0.113 -p 8883 -t "test/topic" --insecure -v

# Test publish (send a message)
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h 192.168.0.113 -p 8883 -t "test/topic" -m "Hello from Windows" --insecure
```

**Parameters:**
- `-h 192.168.0.113` = Your PC's IP (Mosquitto host)
- `-p 8883` = TLS port
- `-t "test/topic"` = Topic name (can be anything)
- `-m "message"` = Message to send
- `--insecure` = Don't validate server certificate
- `-v` = Verbose (show topic names)

### Step 3: Expected Output

**Success:**
```
Client mosqsub|12345 sending CONNECT
Client mosqsub|12345 received CONNACK (0)
```

**Failure:**
```
Error: Connection refused
```
or
```
Error: A TLS error occurred.
```

---

## Option 2: Test from Phone/Android

### Method A: MQTT Dashboard App (Best for Android)

1. **Install App**:
   - Download "MQTT Dashboard" by Telenor Connexion (free)
   - OR "IoT MQTT Panel" by Rahul Kundu

2. **Create Connection**:
   - Tap "+" to add connection
   - **Name**: Hospital MQTT
   - **Broker**: 192.168.0.113
   - **Port**: 8883
   - **Client ID**: (leave default or use "android_test")
   - **SSL/TLS**: Enable
   - **Certificate verification**: Disable/Skip
   - **Username**: (leave blank)
   - **Password**: (leave blank)

3. **Test**:
   - Save and connect
   - Subscribe to topic: `test/topic`
   - Publish message: "Hello from Android"

### Method B: Terminal App (For Advanced Users)

If you have Termux on Android:
```bash
# Install mosquitto clients
pkg install mosquitto

# Test subscribe
mosquitto_sub -h 192.168.0.113 -p 8883 -t "test/topic" --insecure -v

# Test publish
mosquitto_pub -h 192.168.0.113 -p 8883 -t "test/topic" -m "Hello from Phone" --insecure
```

---

## Option 3: Quick TCP Ping Test (No MQTT Client Needed)

This tests if port 8883 is reachable from CMD:

```cmd
# Test if port 8883 is open
telnet 192.168.0.113 8883
```

**If telnet not installed:**
```cmd
# Enable telnet on Windows
dism /online /Enable-Feature /FeatureName:TelnetClient
```

**OR use PowerShell:**
```powershell
Test-NetConnection -ComputerName 192.168.0.113 -Port 8883
```

**Expected Output (Success):**
```
TcpTestSucceeded : True
```

---

## Option 4: Test with OpenSSL (Verify TLS Handshake)

```cmd
# Test TLS connection from CMD
openssl s_client -connect 192.168.0.113:8883 -showcerts
```

**Expected Success:**
- Shows certificate chain
- Shows "Verify return code: 19 (self signed certificate in certificate chain)" - THIS IS OK
- Connection stays open
- Shows `Protocol  : TLSv1.2`

**Expected Failure:**
- `connect: Connection refused`
- `SSL handshake failed`

---

## From Phone's Perspective

### What Your Phone Needs:
1. **Same WiFi network** as 192.168.0.113 (your PC)
2. **No firewall blocking** port 8883 on Windows
3. **Windows Firewall rule** allowing inbound 8883

### Check Windows Firewall:

```powershell
# Check if port 8883 is allowed
netsh advfirewall firewall show rule name=all | findstr 8883
```

**If no rule exists, add one:**
```powershell
# Allow inbound 8883 (run CMD as Administrator)
netsh advfirewall firewall add rule name="Mosquitto MQTT TLS" dir=in action=allow protocol=TCP localport=8883
```

---

## Troubleshooting

### Phone Can't Connect:

**Check 1: Is phone on same WiFi?**
```
Settings → WiFi → Check network name matches PC's WiFi
```

**Check 2: Can phone ping PC?**
- Install "Network Utilities" app (Android)
- Ping 192.168.0.113
- Should get replies

**Check 3: Is Windows Firewall blocking?**
```cmd
# Temporarily disable firewall to test (AS ADMIN)
netsh advfirewall set allprofiles state off

# Test from phone

# Re-enable firewall
netsh advfirewall set allprofiles state on
```

### CMD Can't Connect:

**Check 1: Is Mosquitto running?**
```cmd
docker ps | findstr mosquitto
```

**Check 2: Is port 8883 listening?**
```cmd
netstat -an | findstr 8883
```
Should show:
```
TCP    0.0.0.0:8883    0.0.0.0:0    LISTENING
```

---

## Quick Test Procedure

### 5-Minute Test:

1. **CMD Test** (from your Windows PC):
   ```cmd
   openssl s_client -connect 192.168.0.113:8883
   ```
   - Should connect and show TLSv1.2

2. **Phone Test** (from your Android phone):
   - Install "MQTT Dashboard" app
   - Connect to 192.168.0.113:8883 with SSL enabled, cert validation disabled
   - Subscribe to `test/topic`

3. **Cross Test**:
   - From CMD: Publish message
     ```cmd
     mosquitto_pub -h 192.168.0.113 -p 8883 -t "test/topic" -m "PC to Phone" --insecure
     ```
   - Phone should receive message in app

---

## Summary

**Easiest Methods:**
- **Windows**: MQTT Explorer (GUI app)
- **Phone**: MQTT Dashboard app
- **Quick Check**: `openssl s_client -connect 192.168.0.113:8883`

**What You're Testing:**
- Can devices on same network reach Mosquitto?
- Is TLS handshake working?
- Can messages be sent/received?

**This helps diagnose ESP32 errno 113 by comparing:**
- ✅ If phone/PC can connect → Problem is ESP32-specific
- ❌ If phone/PC also fails → Problem is Mosquitto/network configuration
