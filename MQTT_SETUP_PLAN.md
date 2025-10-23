# MQTT Setup Plan - Mosquitto on Docker

## Goal
Get ESP32 watches sending vitals data to backend via MQTT by setting up Mosquitto broker in Docker.

---

## Quick Setup (Recommended)

### Step 1: Create Mosquitto Configuration

**File**: `mosquitto/mosquitto.conf`
```conf
# Allow anonymous connections (for development)
listener 1883
allow_anonymous true

# Enable persistence
persistence true
persistence_location /mosquitto/data/

# Logging
log_dest stdout
log_type all
```

### Step 2: Add to docker-compose.yml

```yaml
version: '3.8'

services:
  # ... existing services (postgres, timescaledb, etc.)

  mosquitto:
    image: eclipse-mosquitto:2.0
    container_name: hospital-mosquitto
    ports:
      - "1883:1883"  # MQTT port
      - "9001:9001"  # WebSocket port (optional)
    volumes:
      - ./mosquitto/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro
      - mosquitto-data:/mosquitto/data
      - mosquitto-logs:/mosquitto/log
    restart: unless-stopped
    networks:
      - hospital-network

volumes:
  # ... existing volumes
  mosquitto-data:
  mosquitto-logs:

networks:
  hospital-network:
    driver: bridge
```

### Step 3: Start Mosquitto

```bash
docker-compose up -d mosquitto
```

### Step 4: Enable Backend MQTT Service

**In `hospital-backend/main.py`**, uncomment or enable MQTT initialization.

---

## Detailed Implementation

### Option A: Docker Compose (Recommended)

**Pros:**
- ✅ Easy to manage alongside other services
- ✅ Automatic restart
- ✅ Network isolation
- ✅ Volume persistence

**Setup Steps:**
1. Create `mosquitto/` directory
2. Create `mosquitto/mosquitto.conf` file
3. Update `docker-compose.yml` (if exists) or create new one
4. Run `docker-compose up -d mosquitto`

---

### Option B: Standalone Docker Container

If you don't have docker-compose:

```bash
# Create config directory
mkdir mosquitto
cd mosquitto
mkdir config data logs

# Create config file (as shown above)

# Run container
docker run -d \
  --name hospital-mosquitto \
  -p 1883:1883 \
  -p 9001:9001 \
  -v ${PWD}/config/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro \
  -v ${PWD}/data:/mosquitto/data \
  -v ${PWD}/logs:/mosquitto/log \
  --restart unless-stopped \
  eclipse-mosquitto:2.0
```

---

## Testing the Setup

### Test 1: Verify Mosquitto is Running

```bash
docker ps | grep mosquitto
```

Expected output:
```
CONTAINER ID   IMAGE                    STATUS         PORTS
abc123         eclipse-mosquitto:2.0    Up 10 seconds  0.0.0.0:1883->1883/tcp
```

### Test 2: Test MQTT Connection (from host)

**Install mosquitto clients:**
```bash
# Windows (via chocolatey)
choco install mosquitto

# Or use Python
pip install paho-mqtt
```

**Subscribe to watch vitals:**
```bash
mosquitto_sub -h localhost -p 1883 -t "hospital/devices/+/vitals" -v
```

**Or with Python:**
```python
import paho.mqtt.client as mqtt

def on_message(client, userdata, msg):
    print(f"Topic: {msg.topic}, Payload: {msg.payload.decode()}")

client = mqtt.Client()
client.on_message = on_message
client.connect("localhost", 1883)
client.subscribe("hospital/devices/+/vitals")
client.loop_forever()
```

### Test 3: Check Backend Logs

After starting Mosquitto, restart backend and look for:
```
✅ MQTT service initialized
✅ Connected to MQTT broker at localhost:1883
✅ Subscribed to hospital/devices/+/vitals
```

Instead of:
```
⚠️ MQTT service not available
```

---

## Backend MQTT Service Configuration

### Check Current Backend MQTT Code

**File**: `hospital-backend/app/services/mqtt_service.py`

The backend should have code like:
```python
import paho.mqtt.client as mqtt

class MQTTService:
    def __init__(self, broker_host="localhost", broker_port=1883):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        # Connect to broker
        self.client.connect(broker_host, broker_port)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("✅ Connected to MQTT broker")
            # Subscribe to all device topics
            client.subscribe("hospital/devices/+/vitals")
            client.subscribe("hospital/devices/+/alerts")
        else:
            print(f"❌ MQTT connection failed with code {rc}")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()

        if "/vitals" in topic:
            self.handle_vitals(topic, payload)
        elif "/alerts" in topic:
            self.handle_alerts(topic, payload)
```

### Enable MQTT in Backend Startup

**File**: `hospital-backend/main.py`

Look for startup code:
```python
@app.on_event("startup")
async def startup_event():
    # ... existing startup code

    # Initialize MQTT service
    try:
        global mqtt_service
        mqtt_service = MQTTService(
            broker_host=os.getenv("MQTT_HOST", "localhost"),
            broker_port=int(os.getenv("MQTT_PORT", "1883"))
        )
        logger.info("✅ MQTT service initialized")
    except Exception as e:
        logger.warning(f"⚠️ MQTT service not available: {e}")
```

---

## Environment Variables

Add to `.env` file (or backend config):
```env
# MQTT Configuration
MQTT_HOST=localhost
MQTT_PORT=1883
MQTT_ENABLED=true
```

---

## Security (Production)

For production, update `mosquitto.conf`:

```conf
# Require authentication
listener 1883
allow_anonymous false
password_file /mosquitto/config/passwords.txt

# Enable TLS (optional but recommended)
# listener 8883
# cafile /mosquitto/certs/ca.crt
# certfile /mosquitto/certs/server.crt
# keyfile /mosquitto/certs/server.key

persistence true
persistence_location /mosquitto/data/
```

Create password file:
```bash
docker exec -it hospital-mosquitto mosquitto_passwd -c /mosquitto/config/passwords.txt admin
```

---

## Firewall Rules

If watch is on different network, ensure port 1883 is open:

**Windows:**
```powershell
netsh advfirewall firewall add rule name="MQTT" dir=in action=allow protocol=TCP localport=1883
```

**Linux:**
```bash
sudo ufw allow 1883/tcp
```

---

## Expected Data Flow (After Fix)

1. **ESP32 Watch** → MQTT publish to `hospital/devices/ESP32_WATCH_003/vitals`
2. **Mosquitto Broker** → Routes message to subscribers
3. **Backend MQTT Service** → Receives message (subscribed to `hospital/devices/+/vitals`)
4. **Backend** → Stores vitals in TimescaleDB
5. **Frontend/Displays** → WebSocket push to connected clients for real-time display

---

## Troubleshooting

### Issue: Backend can't connect to Mosquitto

**Check:**
```bash
docker logs hospital-mosquitto
```

**Fix:** Verify Mosquitto is listening:
```
1234567890: mosquitto version 2.0.15 starting
1234567890: Opening ipv4 listen socket on port 1883.
1234567890: Opening ipv6 listen socket on port 1883.
```

### Issue: Watch can't connect to MQTT

**Check ESP32 serial monitor:**
```
❌ MQTT Connection failed, rc=-2
```

**Fix:** Ensure:
- Mosquitto is running on correct IP (192.168.0.113)
- Port 1883 is accessible from watch's network
- Firewall allows connections

### Issue: No vitals data appearing

**Check:**
1. Is watch assigned to a patient?
2. Is MQTT connection successful on watch?
3. Is backend MQTT service subscribed to correct topic?

**Debug with mosquitto_sub:**
```bash
mosquitto_sub -h 192.168.0.113 -p 1883 -t "hospital/#" -v
```

---

## Verification Checklist

- [ ] Mosquitto container running (`docker ps`)
- [ ] Port 1883 accessible (`telnet localhost 1883`)
- [ ] Backend MQTT service initialized (check logs)
- [ ] Backend subscribed to topics (check logs)
- [ ] Watch MQTT connected (check serial monitor)
- [ ] Vitals appearing in backend logs
- [ ] Vitals stored in TimescaleDB

---

## Next Steps After Setup

1. **Start Mosquitto** → `docker-compose up -d mosquitto`
2. **Restart Backend** → Restart Python backend to initialize MQTT service
3. **Check Watch Serial** → Verify watch connects to MQTT broker
4. **Monitor Topic** → Use `mosquitto_sub` to see vitals flowing
5. **Test Alert System** → Trigger an alert condition (e.g., simulate high HR)

---

## Resources

- Mosquitto Docker: https://hub.docker.com/_/eclipse-mosquitto
- MQTT Protocol: https://mqtt.org/
- paho-mqtt Python: https://pypi.org/project/paho-mqtt/

---

## Estimated Time

- ⏱️ **Setup**: 5-10 minutes
- ⏱️ **Testing**: 5 minutes
- ⏱️ **Troubleshooting**: 10-20 minutes (if needed)
- **Total**: ~30 minutes

---

## Success Criteria

✅ Mosquitto running in Docker
✅ Backend MQTT service connected
✅ ESP32 watch connected to broker
✅ Vitals flowing every 5 seconds
✅ Alerts triggering correctly
✅ Real-time display updates working
