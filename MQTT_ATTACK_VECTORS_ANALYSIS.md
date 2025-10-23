# MQTT Attack Vectors Analysis - Hospital System

## Your Concern: "Insecure MQTT might cause spoof/spam/attacks"

### ✅ YOU'RE RIGHT TO WORRY!

Let me analyze the actual risks in your architecture:

---

## Current Architecture

```
┌─────────────┐
│ ESP32 Watch │
│   (v3.3.0)  │
└──────┬──────┘
       │
       │ ① HTTP POST (HMAC-SHA256)
       │    /api/v1/esp32/{deviceId}/heartbeat
       │    Headers: X-Device-MAC, X-Device-Signature, X-Timestamp
       │
       ▼
┌──────────────┐
│   Backend    │
│  Port 8001   │────┐
└──────────────┘    │
       ▲            │
       │            │ ② MQTT (localhost:1883)
       │            │    Topic: hospital/devices/{deviceId}/vitals
       │            │    Username: hospitalEsp32
       │            │    Password: esp32Secure
       │            │
       │            ▼
       │      ┌─────────────┐
       │      │  Mosquitto  │
       └──────│  Broker     │
              └─────────────┘
```

---

## Attack Vector Analysis

### ❌ Attack 1: Spoofing ESP32 Watch → Backend (HTTP)

**Attack**: Hacker sends fake vitals via HTTP

**Example**:
```bash
curl -X POST http://192.168.0.113:8001/api/v1/esp32/ESP32_WATCH_003/heartbeat \
  -H "Content-Type: application/json" \
  -d '{"batterylevel": 10, "signalstrength": -50}'
```

**Result**: ✅ **BLOCKED!**

**Why**: Backend validates HMAC signature
```python
# Backend validates (Line 225-245 in esp32.py):
def validate_hmac(mac_address, signature, timestamp, endpoint):
    # Recompute HMAC
    message = mac_address + timestamp + endpoint
    expected_signature = compute_hmac(message, FACTORY_SECRET)

    if signature != expected_signature:
        raise HTTPException(401, "Invalid HMAC signature")

    # Check timestamp (replay protection)
    if abs(current_time - timestamp) > 300:  # 5 min window
        raise HTTPException(401, "Timestamp expired")
```

**Attacker would need**:
- Device MAC address (visible on network)
- Current timestamp (easy)
- ❌ **FACTORY_SECRET** (only you and ESP32 know this)

**Verdict**: ✅ **SECURE** (HMAC prevents spoofing)

---

### 🔴 Attack 2: Spoofing Backend → MQTT (Internal)

**Attack**: Hacker on hospital network publishes fake vitals to MQTT

**Scenario A - No Authentication**:
```bash
# If MQTT has allow_anonymous = true
mosquitto_pub -h 192.168.0.113 -p 1883 \
  -t "hospital/devices/ESP32_WATCH_003/vitals" \
  -m '{"patientId":"PAT001","heartRate":200,"oxygenSat":50}'
```

**Result**: 🔴 **SUCCEEDS! Backend processes fake vitals!**

**This is your concern!** ✅ You're right!

---

**Scenario B - With Authentication (username/password)**:
```bash
# With authentication
mosquitto_pub -h 192.168.0.113 -p 1883 \
  -u "attacker" -P "guessed_password" \
  -t "hospital/devices/ESP32_WATCH_003/vitals" \
  -m '{"patientId":"PAT001","heartRate":200}'
```

**Result**:
- If password weak: 🔴 **SUCCEEDS after brute force**
- If password strong: 🟡 **Blocked, but password could be sniffed on network (no TLS)**

---

### 🔴 Attack 3: MQTT Password Sniffing (No TLS)

**Attack**: Packet capture on hospital network

```bash
# Attacker runs Wireshark on hospital network
# Captures MQTT CONNECT packet
# Extracts: username="hospitalEsp32", password="esp32Secure"
```

**Result**: 🔴 **PASSWORD EXPOSED!**

**Why**: MQTT without TLS sends credentials in plaintext

**Then**: Attacker can publish fake vitals, subscribe to patient data, etc.

---

### 🔴 Attack 4: MQTT Topic Injection (No ACLs)

**Attack**: Authenticated client publishes to wrong topics

```bash
# Backend publishes vitals for patient A
# But attacker with same credentials publishes to patient B
mosquitto_pub -u hospitalEsp32 -P esp32Secure \
  -t "hospital/devices/ESP32_WATCH_005/vitals" \
  -m '{"patientId":"PATIENT_B", "heartRate":200}'
```

**Result**: 🔴 **SUCCEEDS!** (No topic-level permissions)

**Impact**: Attacker can:
- Inject fake vitals for ANY patient
- Subscribe to ALL patients' data
- Trigger false alarms

---

### 🔴 Attack 5: Denial of Service (No Rate Limiting)

**Attack**: Flood MQTT broker with messages

```bash
# Spam 10,000 messages/second
while true; do
  mosquitto_pub -u hospitalEsp32 -P esp32Secure \
    -t "hospital/devices/+/vitals" \
    -m '{"spam": true}'
done
```

**Result**: 🔴 **SUCCEEDS!**

**Impact**:
- Broker crashes
- Backend overwhelmed
- Real vitals lost
- System unavailable

---

## Risk Assessment (Without Mitigations)

| Attack Vector | Likelihood | Impact | Risk Level |
|---------------|------------|--------|------------|
| **ESP32 → Backend Spoofing** | 🟢 Low | Critical | 🟢 LOW (HMAC protects) |
| **Backend → MQTT Spoofing** | 🔴 High | Critical | 🔴 **CRITICAL** |
| **Password Sniffing (No TLS)** | 🔴 High | Critical | 🔴 **CRITICAL** |
| **Topic Injection (No ACLs)** | 🔴 High | High | 🔴 **CRITICAL** |
| **Denial of Service** | 🟡 Medium | High | 🟡 **HIGH** |

**Verdict**: 🔴 **YOU'RE RIGHT - INSECURE MQTT IS DANGEROUS!**

---

## Required Mitigations (In Priority Order)

### 🔴 CRITICAL - Must Have Before Production

#### 1. **MQTT Authentication (Username/Password)**

**mosquitto.conf**:
```conf
listener 1883
allow_anonymous false
password_file /mosquitto/config/passwords.txt
```

**Why**: Blocks unauthenticated attackers

**Mitigates**:
- ✅ Anonymous spoofing
- ❌ Still vulnerable to password sniffing

---

#### 2. **Strong Password (32+ random characters)**

```bash
# Generate strong password
openssl rand -base64 32
# Example: xK8pL5mN9qR2tU6vW1xY4zA7bC0dE3fF==

mosquitto_passwd -c passwords.txt hospitalEsp32
# Enter: xK8pL5mN9qR2tU6vW1xY4zA7bC0dE3fF==
```

**Why**: Prevents brute force

**Mitigates**:
- ✅ Brute force attacks
- ❌ Still vulnerable to sniffing

---

#### 3. **TLS Encryption (Prevent Sniffing)** ⭐ CRITICAL

**mosquitto.conf**:
```conf
listener 8883
protocol mqtt

# TLS
cafile /mosquitto/certs/ca.crt
certfile /mosquitto/certs/server.crt
keyfile /mosquitto/certs/server.key
require_certificate false
tls_version tlsv1.2

# Auth
allow_anonymous false
password_file /mosquitto/config/passwords.txt
```

**Why**: Encrypts password and all data on wire

**Mitigates**:
- ✅ Password sniffing
- ✅ Data interception
- ✅ Man-in-the-middle attacks

---

#### 4. **ACLs (Topic-Level Permissions)** ⭐ CRITICAL

**acl.conf**:
```conf
# Backend - full access
user hospitalEsp32
topic readwrite hospital/#
topic read $SYS/#

# Deny everything else by default
user #
topic read $SYS/broker/connection/#
```

**Why**: Limits what authenticated clients can do

**Mitigates**:
- ✅ Topic injection
- ✅ Data exfiltration
- ✅ Cross-patient data access

---

#### 5. **Rate Limiting**

**mosquitto.conf**:
```conf
max_connections 100
max_inflight_messages 20
max_queued_messages 1000
message_size_limit 10240  # 10KB max
```

**Why**: Prevents DoS attacks

**Mitigates**:
- ✅ Message flooding
- ✅ Connection exhaustion

---

### 🟡 HIGH PRIORITY - Add Soon

#### 6. **Network Isolation**

```
Hospital Network:
├── VLAN 10: ESP32 Watches (192.168.10.0/24)
├── VLAN 20: Backend + MQTT (192.168.20.0/24)
│   └── Firewall: Only backend can access MQTT
└── VLAN 30: Staff/Frontend (192.168.30.0/24)
```

**Why**: Limits who can reach MQTT broker

**Mitigates**:
- ✅ Lateral movement
- ✅ Reduces attack surface

---

#### 7. **MQTT on Localhost Only**

**mosquitto.conf**:
```conf
bind_address 127.0.0.1  # Only accept local connections
listener 1883 127.0.0.1
```

**Why**: MQTT not accessible from network

**Mitigates**:
- ✅ Remote attacks impossible
- ✅ Only backend can connect

**Trade-off**: ESP32 watches can't connect directly (but they don't in your architecture!)

---

#### 8. **Backend Message Validation**

**In `mqtt_service.py` (add this)**:
```python
async def _handleVitalsMessageNew(self, deviceId: str, payload: Dict[str, Any]):
    # VALIDATION #1: Check device is actually assigned
    async with getDbConnection() as conn:
        assignment = await conn.fetchrow(
            'SELECT "deviceId" FROM deviceassignments WHERE "deviceId" = $1 AND status = \'active\'',
            deviceId
        )
        if not assignment:
            logger.warning(f"🚨 SECURITY: Vitals from unassigned device {deviceId}")
            return  # REJECT

    # VALIDATION #2: Check patientId matches assignment
    if assignment['patientId'] != payload.get('patientId'):
        logger.warning(f"🚨 SECURITY: Patient ID mismatch for device {deviceId}")
        return  # REJECT

    # VALIDATION #3: Rate limiting per device
    lastMessage = self.deviceLastMessage.get(deviceId, 0)
    if (time.time() - lastMessage) < 1:  # Max 1 msg/sec per device
        logger.warning(f"🚨 SECURITY: Rate limit exceeded for {deviceId}")
        return  # REJECT

    self.deviceLastMessage[deviceId] = time.time()

    # VALIDATION #4: Validate data ranges
    if not self._validateVitalsRanges(payload):
        logger.warning(f"🚨 SECURITY: Invalid vitals data from {deviceId}")
        return  # REJECT

    # Process message...
```

**Why**: Backend validates ALL messages from MQTT

**Mitigates**:
- ✅ Fake vitals injection
- ✅ Out-of-range attacks
- ✅ Rate-based DoS

---

## Secure Configuration (Full Stack)

### Step 1: Generate Certificates
```bash
cd mosquitto/certs

# CA certificate
openssl req -new -x509 -days 3650 -keyout ca.key -out ca.crt \
  -subj "/CN=HospitalMQTTCA"

# Server certificate
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -subj "/CN=localhost"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out server.crt -days 3650
```

### Step 2: Create Strong Password
```bash
openssl rand -base64 32 > mqtt_password.txt
mosquitto_passwd -c passwords.txt hospitalEsp32
# Paste generated password
```

### Step 3: mosquitto.conf (Secure)
```conf
# TLS listener
listener 8883
protocol mqtt

# TLS certificates
cafile /mosquitto/certs/ca.crt
certfile /mosquitto/certs/server.crt
keyfile /mosquitto/certs/server.key
require_certificate false
tls_version tlsv1.2

# Authentication
allow_anonymous false
password_file /mosquitto/config/passwords.txt

# ACLs
acl_file /mosquitto/config/acl.conf

# Rate limiting
max_connections 50
max_inflight_messages 20
max_queued_messages 500
message_size_limit 10240

# Bind to localhost only (if ESP32 doesn't connect directly)
bind_address 127.0.0.1

# Persistence
persistence true
persistence_location /mosquitto/data/

# Logging
log_dest stdout
log_type all
```

### Step 4: acl.conf (Restrict Topics)
```conf
# Backend user - full access to hospital topics
user hospitalEsp32
topic readwrite hospital/#
topic read $SYS/#

# Deny all others
pattern read $SYS/broker/connection/%u
pattern readwrite hospital/devices/%u/#
```

### Step 5: Backend Validation Layer
```python
# Add to mqtt_service.py
class MQTTService:
    def __init__(self):
        # ... existing code ...
        self.deviceLastMessage = {}  # Rate limiting tracker

    def _validateVitalsRanges(self, vitals):
        """Validate vitals are in physiologically possible ranges"""
        hr = vitals.get('heartRate', 0)
        spo2 = vitals.get('oxygenSaturation', 0)
        temp = vitals.get('skinTemperature', 0)

        # Physiologically possible ranges
        if not (20 <= hr <= 300): return False
        if not (50 <= spo2 <= 100): return False
        if not (80 <= temp <= 115): return False

        return True
```

---

## Recommended Configuration for Your Kit

### For Hospitals (Private Network):

**Tier 1: Minimum Viable Security** ✅
```
✅ MQTT Authentication (strong password)
✅ Localhost binding (127.0.0.1)
✅ Backend validation layer
✅ Rate limiting
```

**Tier 2: Production Security** ⭐ RECOMMENDED
```
✅ Everything in Tier 1, PLUS:
✅ TLS encryption
✅ ACLs
✅ Network segmentation (VLAN)
```

**Tier 3: High Security / Multi-Hospital**
```
✅ Everything in Tier 2, PLUS:
✅ Per-device certificates
✅ Hardware security modules
✅ Intrusion detection
```

---

## My Recommendation

**Use Tier 2 (Production Security)** with:
1. ✅ TLS encryption (prevent sniffing)
2. ✅ Strong password (32+ chars)
3. ✅ ACLs (topic isolation)
4. ✅ Backend validation (last line of defense)
5. ✅ Localhost binding (if possible)

**Time to implement**: ~30 minutes
**Security gain**: 🔴 CRITICAL → 🟢 LOW risk

---

## Want Me to Set Up Tier 2 Security Now?

I can implement:
1. Generate TLS certificates (self-signed for development)
2. Create strong random password
3. Configure Mosquitto with TLS + ACLs
4. Add backend validation layer
5. Test everything works

**Say "yes, set up tier 2 security" and I'll do it!** 🔒
