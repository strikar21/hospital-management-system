# Fix: Allow WiFi Devices to Connect to Mosquitto

## Problem

- ✅ Your PC can connect to Mosquitto (via localhost 172.20.0.1)
- ❌ WiFi devices (ESP32, phone) CANNOT connect from 192.168.0.x network
- **Reason**: Windows Firewall is blocking inbound port 8883

---

## Solution: Add Windows Firewall Rule

### Step 1: Open CMD as Administrator

1. Press Windows key
2. Type `cmd`
3. Right-click "Command Prompt"
4. Click "Run as administrator"

### Step 2: Add Firewall Rule

Copy and paste this command:

```cmd
netsh advfirewall firewall add rule name="Mosquitto MQTT TLS" dir=in action=allow protocol=TCP localport=8883
```

**Expected output:**
```
Ok.
```

### Step 3: Verify Rule Was Added

```cmd
netsh advfirewall firewall show rule name="Mosquitto MQTT TLS"
```

**Expected output:**
```
Rule Name:                            Mosquitto MQTT TLS
Enabled:                              Yes
Direction:                            In
Profiles:                             Domain,Private,Public
LocalIP:                              Any
RemoteIP:                             Any
Protocol:                             TCP
LocalPort:                            8883
Action:                               Allow
```

---

## Test from Phone

### Option 1: Using MQTT Dashboard App (Easiest)

**Install:**
- Download "MQTT Dashboard" from Google Play Store (free)

**Connection Settings:**
- **Broker**: `192.168.0.113`
- **Port**: `8883`
- **Client ID**: `phone_test` (any name)
- **Username**: (leave blank)
- **Password**: (leave blank)
- **SSL/TLS**: ✅ Enable
- **Certificate verification**: ❌ Disable

**Test:**
1. Save and click "Connect"
2. Should show "Connected" status
3. Subscribe to topic: `test/topic`
4. Publish message: "Hello from phone"

### Option 2: Quick Network Test (Before MQTT)

**Check if phone can reach your PC:**

1. Install "Network Utilities" app from Play Store
2. Use "Ping" tool
3. Ping: `192.168.0.113`
4. Should get replies (if not, phone is not on same WiFi network)

---

## Verify in Mosquitto Logs

After phone connects, check logs:

```cmd
docker logs hospital_mosquitto --tail 20
```

**Should show:**
```
New connection from 192.168.0.xxx on port 8883.
New client connected from 192.168.0.xxx as phone_test
```

Where `xxx` is your phone's IP address on WiFi.

---

## What This Proves

**If phone CAN connect after adding firewall rule:**
- ✅ Mosquitto is accessible from WiFi network
- ✅ TLS 1.2 handshake works for external devices
- ✅ **ESP32 errno 113 is an ESP32 WiFiClientSecure library bug, NOT a network/Mosquitto issue**

**If phone STILL cannot connect:**
- Check phone is on same WiFi network as PC
- Check Windows Firewall is not blocking anyway (try temporarily disabling it)
- Check router is not blocking connections between WiFi devices

---

## Alternative: Temporarily Disable Firewall for Testing

**CAUTION: Only do this temporarily for testing!**

```cmd
# Disable firewall (AS ADMIN)
netsh advfirewall set allprofiles state off

# Test from phone

# Re-enable firewall
netsh advfirewall set allprofiles state on
```

---

## Summary

1. **Add firewall rule** (CMD as Admin):
   ```cmd
   netsh advfirewall firewall add rule name="Mosquitto MQTT TLS" dir=in action=allow protocol=TCP localport=8883
   ```

2. **Test from phone** using MQTT Dashboard app:
   - Broker: 192.168.0.113:8883
   - SSL: ON, Cert verification: OFF

3. **Check Mosquitto logs** - should see connection from 192.168.0.xxx

4. **Result**: If phone works, ESP32 has WiFiClientSecure bug (not network issue)
