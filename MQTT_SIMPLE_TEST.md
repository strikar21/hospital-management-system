# MQTT Simple Test - No Password Needed

## Quick Test (Anonymous Mode)

Since Mosquitto has `allow_anonymous true`, you don't need username/password!

---

## From Windows CMD

### Step 1: Install Mosquitto Client
Download: https://mosquitto.org/download/
Install to: `C:\Program Files\mosquitto\`

### Step 2: Test Connection

**Subscribe (Listen for messages):**
```cmd
"C:\Program Files\mosquitto\mosquitto_sub.exe" -h 192.168.0.113 -p 8883 -t "test/topic" --insecure -v
```

**Publish (Send a message):**
```cmd
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h 192.168.0.113 -p 8883 -t "test/topic" -m "Hello" --insecure
```

**That's it! No username, no password.**

---

## From Android Phone

### MQTT Dashboard App

**Connection Settings:**
- **Broker:** `192.168.0.113`
- **Port:** `8883`
- **SSL/TLS:** ✅ Enable
- **Certificate verification:** ❌ Disable
- **Username:** (leave blank)
- **Password:** (leave blank)

---

## Expected Output

**Success:**
```
Client mosqsub|12345 sending CONNECT
Client mosqsub|12345 received CONNACK (0)
```

**Mosquitto logs should show:**
```bash
docker logs hospital_mosquitto --tail 10
```
Output:
```
New connection from 192.168.0.xxx on port 8883.
New client connected from 192.168.0.xxx as mosqsub|12345
```

---

## If You Get "Connection Refused"

### Check Mosquitto is running:
```cmd
docker ps | findstr mosquitto
```

### Check port 8883 is open:
```powershell
Test-NetConnection -ComputerName 192.168.0.113 -Port 8883
```

### Allow firewall (run CMD as Admin):
```cmd
netsh advfirewall firewall add rule name="MQTT" dir=in action=allow protocol=TCP localport=8883
```

---

## Summary

**One-line test from CMD:**
```cmd
"C:\Program Files\mosquitto\mosquitto_sub.exe" -h 192.168.0.113 -p 8883 -t "test" --insecure -v
```

No username, no password, no hassle! 🎉
