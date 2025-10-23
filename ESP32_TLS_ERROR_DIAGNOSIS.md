# ESP32 TLS Connection Error - Deep Diagnosis

## Current Situation

ESP32 is getting TLS error **before connection reaches Mosquitto broker**.

### ESP32 Error:
```
[ 33336][E][ssl_client.cpp:150] start_ssl_client(): socket error on fd 49, errno: 113, "Software caused connection abort"
❌ MQTT connection failed for provisioning, rc=-2
```

### Mosquitto Logs:
```
# NO CONNECTION ATTEMPTS from 192.168.0.148 (ESP32)
# Only backend (172.17.0.1) is connecting
```

## Key Insight

**ESP32 TLS handshake failing BEFORE reaching Mosquitto!**

This means the problem is NOT:
- ❌ Certificate mismatch (Mosquitto never sees the connection)
- ❌ Wrong credentials (Mosquitto never sees the connection)
- ❌ Mosquitto configuration (Mosquitto never sees the connection)

The problem IS:
- ⚠️ ESP32 TLS client setup
- ⚠️ Network routing issue (Docker vs ESP32)
- ⚠️ Port blocking or firewall
- ⚠️ TLS library incompatibility

## Root Cause Analysis

### Issue: Docker Network Isolation

**Mosquitto is listening on 127.0.0.1 (Docker internal) NOT 0.0.0.0 (all interfaces)**

```bash
# Backend connects from Docker network (172.17.0.1)
# ESP32 tries to connect from WiFi network (192.168.0.148)
# ESP32 → 192.168.0.113:8883 → Docker → ???
```

**Mosquitto may not be accessible from outside Docker network!**

## Testing Theory

### Test 1: Check Mosquitto Listening Address
```bash
docker exec hospital-mosquitto netstat -tulpn | grep 8883
```

Expected if working:
```
tcp  0  0.0.0.0:8883  0.0.0.0:*  LISTEN
```

Expected if broken:
```
tcp  0  127.0.0.1:8883  0.0.0.0:*  LISTEN
```

### Test 2: Try Connection from Host Machine
```bash
# Install mosquitto clients on Windows
# Or use Python paho-mqtt

mosquitto_sub -h 192.168.0.113 -p 8883 \
  -u hospitalEsp32 \
  -P ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF+Q= \
  -t "hospital/#" \
  --cafile mosquitto/certs/ca.crt
```

**If this fails → Mosquitto not accessible from host network**

### Test 3: Check Docker Port Binding
```bash
docker port hospital-mosquitto
```

Expected:
```
8883/tcp -> 0.0.0.0:8883
```

## Most Likely Fix

### Option 1: Mosquitto Config Issue

**Check mosquitto.conf listener configuration:**

Current (maybe):
```conf
listener 8883
protocol mqtt
```

Should be:
```conf
listener 8883 0.0.0.0
protocol mqtt
```

### Option 2: Docker Network Mode

**Current docker run command may be missing network binding.**

Check if Mosquitto container is running in bridge mode with proper port exposure.

### Option 3: Windows Firewall

**Windows Firewall may be blocking port 8883 for external connections.**

```powershell
# Check if port 8883 is allowed
netsh advfirewall firewall show rule name=all | findstr 8883

# Allow port 8883 if needed
netsh advfirewall firewall add rule name="Mosquitto MQTT TLS" dir=in action=allow protocol=TCP localport=8883
```

## Immediate Action

**Try connecting from host machine (Windows) to Mosquitto to see if it's accessible:**

### Quick Python Test Script

```python
# test_mqtt_connection.py
import paho.mqtt.client as mqtt
import ssl

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected successfully!")
    else:
        print(f"❌ Connection failed with code {rc}")

client = mqtt.Client("TestClient")
client.username_pw_set("hospitalEsp32", "ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF+Q=")

# TLS configuration
client.tls_set(
    ca_certs="mosquitto/certs/ca.crt",
    tls_version=ssl.PROTOCOL_TLSv1_2
)

client.on_connect = on_connect

print("🔄 Connecting to 192.168.0.113:8883...")
try:
    client.connect("192.168.0.113", 8883, 60)
    client.loop_start()
    import time
    time.sleep(5)
    client.loop_stop()
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

Run:
```bash
cd hospital-management-system
python test_mqtt_connection.py
```

**If this fails → Mosquitto is not accessible from WiFi network**

## Solution Path

### If Mosquitto Not Accessible:

1. **Update mosquitto.conf:**
   ```conf
   listener 8883 0.0.0.0
   ```

2. **Restart Mosquitto:**
   ```bash
   docker restart hospital-mosquitto
   ```

3. **Check firewall:**
   ```bash
   netsh advfirewall firewall add rule name="Mosquitto MQTT TLS" dir=in action=allow protocol=TCP localport=8883
   ```

4. **Test again from ESP32**

### If Mosquitto IS Accessible:

Then the issue is ESP32 TLS library configuration. We need to:

1. **Try insecure mode temporarily:**
   ```cpp
   wifiClient.setInsecure();  // Skip certificate validation
   ```

2. **If insecure works → certificate issue**
3. **If insecure fails → MQTT protocol issue**

## Next Step

**Run the Python test script above to determine if Mosquitto is accessible from the host network.**

Report back with the result, and we'll proceed accordingly.
