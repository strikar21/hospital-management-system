# MQTT Test Credentials - Quick Reference

## Connection Parameters

| Parameter | Value |
|-----------|-------|
| **Server/Host** | `192.168.0.113` |
| **Port** | `8883` |
| **Client ID** | `test_client_001` (use any unique name) |
| **Username** | `hospitalEsp32` |
| **Password** | `ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF/Q=` |
| **SSL/TLS** | ✅ Enabled (TLS 1.2) |
| **Certificate Validation** | ❌ Disabled (use `--insecure` flag) |

---

## Quick Test from Windows CMD

### Option 1: Using mosquitto_pub/sub (Recommended)

**Install First:**
1. Download: https://mosquitto.org/download/
2. Install to `C:\Program Files\mosquitto\`

**Test Subscribe (Listen for messages):**
```cmd
"C:\Program Files\mosquitto\mosquitto_sub.exe" -h 192.168.0.113 -p 8883 -u hospitalEsp32 -P "ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF/Q=" -t "test/topic" --insecure -v
```

**Test Publish (Send a message):**
```cmd
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h 192.168.0.113 -p 8883 -u hospitalEsp32 -P "ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF/Q=" -t "test/topic" -m "Hello from Windows" --insecure
```

### Option 2: Using MQTT Explorer GUI (Easiest)

**Download:** https://mqtt-explorer.com/

**Connection Settings:**
- **Name**: Hospital Test
- **Host**: `192.168.0.113`
- **Port**: `8883`
- **Protocol**: `mqtt`
- **Username**: `hospitalEsp32`
- **Password**: `ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF/Q=`
- **Encryption (SSL/TLS)**: ✅ Enable
- **Validate certificate**: ❌ Uncheck
- Click "CONNECT"

---

## Quick Test from Android Phone

### Using MQTT Dashboard App

**Install:** "MQTT Dashboard" by Telenor Connexion (Google Play Store - Free)

**Connection Settings:**
- **Broker**: `192.168.0.113`
- **Port**: `8883`
- **Client ID**: `android_test` (any name)
- **Username**: `hospitalEsp32`
- **Password**: `ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF/Q=`
- **SSL/TLS**: ✅ Enable
- **Certificate verification**: ❌ Disable

**Test:**
1. Save and connect
2. Subscribe to topic: `test/topic`
3. Publish message: "Hello from Android"

---

## What This Tests

✅ **If connection succeeds:**
- Mosquitto is reachable from your network
- TLS 1.2 handshake is working
- Username/password authentication works
- **Problem is ESP32-specific** (WiFiClientSecure bug)

❌ **If connection fails:**
- Check Windows Firewall (port 8883 may be blocked)
- Check if phone is on same WiFi network
- Check if Mosquitto is running (`docker ps`)

---

## Expected Success Output

**mosquitto_sub:**
```
Client test_client_001 sending CONNECT
Client test_client_001 received CONNACK (0)
```

**MQTT Explorer:**
- Green "Connected" status
- Shows topic tree structure
- Can publish/subscribe to topics

**Mosquitto Logs (should show):**
```bash
docker logs hospital_mosquitto --tail 20
```
Should show:
```
New connection from 192.168.0.xxx on port 8883.
New client connected from 192.168.0.xxx as test_client_001
```

---

## Troubleshooting

### "Connection refused" Error

**Check if Mosquitto is running:**
```cmd
docker ps | findstr mosquitto
```

**Check if port 8883 is listening:**
```powershell
Test-NetConnection -ComputerName 192.168.0.113 -Port 8883
```

### "TLS handshake failed" Error

**This is normal with `--insecure` flag** - it means:
- TLS connection established ✅
- But self-signed certificate not trusted (expected)
- Connection should still work with `--insecure`

### Phone Can't Connect

**Allow port 8883 in Windows Firewall:**
```powershell
# Run CMD as Administrator
netsh advfirewall firewall add rule name="Mosquitto MQTT" dir=in action=allow protocol=TCP localport=8883
```

**Check phone is on same WiFi:**
- Phone WiFi network name should match PC's WiFi
- Ping PC from phone (use "Network Utilities" app)

---

## Why Backend Uses Same Credentials

Currently, Mosquitto has **username/password authentication disabled** (`allow_anonymous true` in config).

The backend uses these credentials but they're **not being checked** by Mosquitto (anonymous mode).

ESP32 should be able to connect with:
- No username/password (anonymous)
- OR same credentials as backend
- With TLS certificate validation bypassed (`setInsecure()`)

---

## Summary

**Copy-Paste Test (CMD):**
```cmd
"C:\Program Files\mosquitto\mosquitto_sub.exe" -h 192.168.0.113 -p 8883 -u hospitalEsp32 -P "ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF/Q=" -t "test/topic" --insecure -v
```

If this works → ESP32 has a WiFiClientSecure library bug, not a Mosquitto configuration issue.
