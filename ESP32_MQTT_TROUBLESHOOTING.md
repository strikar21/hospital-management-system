# ESP32 MQTT TLS Connection Troubleshooting

## Current Issue
```
❌ MQTT Connection failed, rc=-2
```

Mosquitto logs show:
```
OpenSSL Error: error:0A000126:SSL routines::unexpected eof while reading
Client <unknown> disconnected: Protocol error
```

## Root Cause
TLS handshake is failing between ESP32 and Mosquitto broker.

## ✅ What's Working
- ✅ Backend connected to Mosquitto successfully on port 8883
- ✅ ESP32 can reach the broker (network connectivity is fine)
- ✅ Mosquitto is listening on port 8883 with TLS

## ❌ What's Failing
- ❌ ESP32 TLS handshake with Mosquitto

## Troubleshooting Steps

### Step 1: Verify ESP32 Configuration in Provisioning Form

When you open the captive portal (connect to "HospitalWatch" WiFi), verify:

1. **MQTT Server IP**: Should be `192.168.0.113` (your PC's IP)
2. **MQTT Port**: Should be `8883` (TLS port)
3. **WiFi credentials**: Correct SSID and password
4. **Provisioner**: TEC0001 / tech123

### Step 2: Check Serial Monitor Output

Open Arduino IDE Serial Monitor (115200 baud) and look for:

```
🔧 Setting up MQTT TLS connection...
📡 MQTT Server: 192.168.0.113:8883
🔄 Connecting to MQTT TLS broker as: HospitalWatch_ESP32_WATCH_XXX
```

If you see `❌ MQTT Connection failed, rc=-2`, continue troubleshooting.

### Step 3: Common Issues and Fixes

#### Issue A: Wrong CA Certificate
**Symptom**: `rc=-2` with TLS error
**Fix**: The CA certificate is embedded in the firmware. Ensure you flashed the correct TLS firmware.

**Verify**: Check that your uploaded firmware is `esp32_hospital_watch_complete.ino` (which contains TLS code)

#### Issue B: Firewall Blocking Port 8883
**Symptom**: `rc=-2` immediately
**Fix**: Add Windows Firewall rule for port 8883

```powershell
netsh advfirewall firewall add rule name="MQTT TLS 8883" dir=in action=allow protocol=TCP localport=8883
```

#### Issue C: ESP32 Not Using Secure Client
**Symptom**: Protocol error in Mosquitto logs
**Fix**: Verify firmware has:
```cpp
WiFiClientSecure wifiClient;  // Line 89
```

NOT:
```cpp
WiFiClient wifiClient;  // ❌ Wrong - won't do TLS
```

### Step 4: Test with Insecure Mode (Temporary)

If TLS keeps failing, you can temporarily test with `setInsecure()` mode:

**Current firmware already has this:**
```cpp
wifiClient.setCACert(CA_CERT);
wifiClient.setInsecure();  // ✅ Accepts cert even if hostname doesn't match
```

### Step 5: Verify Mosquitto Configuration

Check that Mosquitto is configured for TLS:

```bash
docker exec hospital-mosquitto cat /mosquitto/config/mosquitto.conf
```

Should show:
```
listener 8883
protocol mqtt
cafile /mosquitto/certs/ca.crt
certfile /mosquitto/certs/server.crt
keyfile /mosquitto/certs/server.key
tls_version tlsv1.2
```

### Step 6: Test MQTT Connection from PC

Test if MQTT TLS works from your PC:

```bash
docker run -it --rm --network host eclipse-mosquitto:2 mosquitto_pub -h 192.168.0.113 -p 8883 --cafile /path/to/ca.crt -t "test/topic" -m "hello" -d
```

## Expected Successful Output

When working correctly, ESP32 Serial Monitor should show:

```
✅ MQTT TLS Connected!
📡 Subscribed to: hospital/devices/ESP32_WATCH_XXX/assign
📡 Subscribed to: hospital/devices/ESP32_WATCH_XXX/command
💓 MQTT Heartbeat sent
```

Mosquitto logs should show:
```
New connection from 192.168.0.XXX on port 8883.
New client connected from 192.168.0.XXX as HospitalWatch_ESP32_WATCH_XXX
```

## Still Not Working?

### Option 1: Re-flash with Clean Upload

1. Close Arduino IDE
2. Unplug ESP32
3. Delete old preferences: In Arduino IDE, go to File → Preferences → Delete Preferences
4. Plug in ESP32
5. Open `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`
6. Upload fresh

### Option 2: Check ESP32 WiFi Connection

Ensure ESP32 is on the same network as your PC:

```
ESP32 IP: 192.168.0.XXX (check Serial Monitor)
PC IP: 192.168.0.113
```

They should be on same subnet (192.168.0.x).

### Option 3: Use Ping Test

From ESP32 Serial Monitor, verify it can reach PC:

1. Note ESP32's IP from Serial Monitor
2. From PC: `ping [ESP32_IP]`
3. Should get replies

## Quick Checklist

- [ ] Firmware uploaded: `esp32_hospital_watch_complete.ino`
- [ ] Arduino IDE shows "Done uploading"
- [ ] Serial Monitor at 115200 baud
- [ ] ESP32 connected to WiFi (same network as PC)
- [ ] MQTT server IP is 192.168.0.113
- [ ] MQTT port is 8883
- [ ] Provisioner is TEC0001 / tech123
- [ ] Mosquitto container running: `docker ps | grep mosquitto`
- [ ] Backend shows "MQTT broker connected"

## Next Steps

If all above checks pass but still failing:
1. Copy full Serial Monitor output
2. Copy Mosquitto logs: `docker logs hospital-mosquitto --tail 100`
3. Share with developer for analysis