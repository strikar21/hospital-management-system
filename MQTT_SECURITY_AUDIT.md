# MQTT Security Audit - Hospital Management System

## Current Setup Analysis

### ✅ What's Secure (Good)

1. **Authentication Required**
   ```conf
   allow_anonymous false
   password_file /mosquitto/config/passwords.txt
   ```
   - ✅ Anonymous connections blocked
   - ✅ Username/password required

2. **Credentials in Backend**
   ```python
   'username': 'hospitalEsp32',
   'password': 'esp32Secure',
   ```
   - ✅ Separate credentials for backend client
   - ✅ Not hardcoded in ESP32 firmware (watches don't use MQTT directly in current v3.3.0)

3. **Network Isolation**
   - ✅ MQTT runs on localhost (127.0.0.1) by default
   - ✅ Backend connects via localhost (no external exposure)

### ⚠️ Security Concerns (Needs Improvement)

#### 1. **ESP32 Watches DON'T Use MQTT Directly**
Looking at your firmware (v3.3.0), watches use:
- ✅ HMAC-SHA256 for HTTP heartbeats (SECURE)
- ❌ MQTT vitals transmission (NOT IMPLEMENTED YET)

**Current Architecture:**
```
ESP32 Watch → HTTP (HMAC) → Backend → MQTT → Internal Services
```

**Issue**: If you enable MQTT on ESP32, credentials need to be stored on watch.

#### 2. **Plaintext Credentials in Code**
```python
# In mqtt_service.py (Line 40-45)
'username': 'hospitalEsp32',
'password': 'esp32Secure',
```

**Risk**: 🔴 HIGH
- Credentials visible in source code
- If repo is public, credentials exposed
- Version control history contains credentials

**Fix**: Use environment variables

#### 3. **No TLS/SSL Encryption**
```python
# Line 78-81 in mqtt_service.py
if self.config.get('use_tls'):
    # TLS is optional, not enforced
```

**Risk**: 🟡 MEDIUM (if on local network only)
- MQTT traffic unencrypted on wire
- Credentials sent in plaintext over network
- Vulnerable to packet sniffing

**Fix**: Enable TLS for production

#### 4. **Weak Password**
```
password: 'esp32Secure'
```

**Risk**: 🟡 MEDIUM
- Short password (11 characters)
- Dictionary word + number pattern
- Vulnerable to brute force

**Fix**: Use strong random password (32+ chars)

#### 5. **Single User for All Devices**
```python
'username': 'hospitalEsp32',  # Same for all ESP32 watches
```

**Risk**: 🟡 MEDIUM
- If one device compromised, all devices compromised
- No per-device authentication
- Cannot revoke single device access

**Fix**: Individual credentials per device OR certificate-based auth

#### 6. **No ACL (Access Control Lists)**
```conf
# Missing in mosquitto.conf:
acl_file /mosquitto/config/acl.conf
```

**Risk**: 🟡 MEDIUM
- Any authenticated client can publish/subscribe to ANY topic
- No topic-level permissions
- Device could read other patients' data

**Fix**: Implement ACLs per device

---

## Security Recommendations

### 🔴 CRITICAL (Fix Immediately)

#### 1. Move Credentials to Environment Variables

**Backend `.env` file:**
```env
# MQTT Configuration
MQTT_HOST=127.0.0.1
MQTT_PORT=1883
MQTT_USERNAME=hospitalEsp32
MQTT_PASSWORD=<GENERATE_STRONG_PASSWORD_HERE>
MQTT_USE_TLS=false  # Set to true in production
```

**Update `mqtt_service.py`:**
```python
import os

self.config = {
    'host': os.getenv('MQTT_HOST', '127.0.0.1'),
    'port': int(os.getenv('MQTT_PORT', 1883)),
    'username': os.getenv('MQTT_USERNAME'),
    'password': os.getenv('MQTT_PASSWORD'),
    'use_tls': os.getenv('MQTT_USE_TLS', 'false').lower() == 'true',
}
```

**Add `.env` to `.gitignore`:**
```gitignore
.env
.env.local
.env.production
*.env
```

#### 2. Generate Strong Password

```bash
# Generate random 32-character password
openssl rand -base64 32

# Example output: 8K9mN2pQ5rT8uV1wX4yZ7aB0cD3eF6g==
```

Update:
- Backend `.env` file
- Mosquitto password file

---

### 🟡 HIGH PRIORITY (Fix Before Production)

#### 3. Enable TLS/SSL Encryption

**Generate self-signed certificates (development):**
```bash
# Create certs directory
mkdir -p mosquitto/certs
cd mosquitto/certs

# Generate CA certificate
openssl req -new -x509 -days 365 -extensions v3_ca -keyout ca.key -out ca.crt -subj "/CN=HospitalMQTTCA"

# Generate server key and certificate
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -subj "/CN=localhost"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 365
```

**Update `mosquitto.conf`:**
```conf
# Regular MQTT (disable in production)
# listener 1883

# Secure MQTT with TLS
listener 8883
allow_anonymous false
password_file /mosquitto/config/passwords.txt

# TLS Configuration
cafile /mosquitto/certs/ca.crt
certfile /mosquitto/certs/server.crt
keyfile /mosquitto/certs/server.key
require_certificate false
tls_version tlsv1.2

# Persistence
persistence true
persistence_location /mosquitto/data/

# Logging
log_dest stdout
log_type all
```

**Update Backend `.env`:**
```env
MQTT_PORT=8883
MQTT_USE_TLS=true
MQTT_CA_CERT=/path/to/ca.crt
```

#### 4. Implement ACLs (Access Control Lists)

**Create `mosquitto/config/acl.conf`:**
```conf
# Backend user - full access
user hospitalEsp32
topic readwrite hospital/#
topic readwrite $SYS/#

# ESP32 watches - restricted per device
# pattern read hospital/devices/%u/command
# pattern write hospital/devices/%u/vitals
# pattern write hospital/devices/%u/alerts
# pattern write hospital/devices/%u/heartbeat
```

**Update `mosquitto.conf`:**
```conf
acl_file /mosquitto/config/acl.conf
```

#### 5. Per-Device Authentication (Optional but Recommended)

**Option A: Individual MQTT Users**
```bash
# Create password for each device
mosquitto_passwd -b /mosquitto/config/passwords.txt ESP32_WATCH_001 <random_password_1>
mosquitto_passwd -b /mosquitto/config/passwords.txt ESP32_WATCH_002 <random_password_2>
mosquitto_passwd -b /mosquitto/config/passwords.txt ESP32_WATCH_003 <random_password_3>
```

**Option B: Certificate-Based Authentication (Most Secure)**
- Generate client certificates for each device
- ESP32 stores certificate in flash
- Mosquitto validates certificate
- No passwords needed

---

### 🟢 NICE TO HAVE (Future Enhancements)

#### 6. Network Segmentation
```
┌─────────────────────────────────────────┐
│  Hospital Network (192.168.0.0/24)     │
│                                          │
│  ┌──────────────┐    ┌──────────────┐  │
│  │ ESP32 Watches│───▶│   Mosquitto  │  │
│  │ VLAN 10      │    │   VLAN 20    │  │
│  └──────────────┘    └──────┬───────┘  │
│                              │           │
│                       ┌──────▼───────┐  │
│                       │   Backend    │  │
│                       │   VLAN 20    │  │
│                       └──────────────┘  │
└─────────────────────────────────────────┘
```

#### 7. Rate Limiting
```conf
# In mosquitto.conf
max_connections 100
max_inflight_messages 20
max_queued_messages 1000
```

#### 8. Monitoring & Alerting
- Log all authentication failures
- Alert on suspicious patterns
- Monitor connection rates

#### 9. MQTT Bridge (Future)
- Separate external/internal brokers
- ESP32 → External Broker → Bridge → Internal Broker
- Better security isolation

---

## Indian Medical Compliance

### Digital Personal Data Protection Act (DPDP) 2023
- ✅ Patient data encrypted in transit (if TLS enabled)
- ✅ Access controls implemented (ACLs)
- ✅ Audit trails (MQTT logs)

### Clinical Establishments Act
- ✅ Device authentication
- ✅ Data integrity (HMAC signatures)
- ✅ Real-time monitoring

---

## Current Risk Assessment

| Component | Current Risk | With Fixes | Priority |
|-----------|--------------|------------|----------|
| **Credentials in Code** | 🔴 HIGH | 🟢 LOW | CRITICAL |
| **No TLS** | 🟡 MEDIUM | 🟢 LOW | HIGH |
| **Weak Password** | 🟡 MEDIUM | 🟢 LOW | CRITICAL |
| **No ACLs** | 🟡 MEDIUM | 🟢 LOW | HIGH |
| **Single User** | 🟡 MEDIUM | 🟢 LOW | MEDIUM |
| **No Network Segmentation** | 🟢 LOW | 🟢 LOW | NICE TO HAVE |

---

## Action Plan (Priority Order)

### Phase 1: Immediate (Today) 🔴
1. ✅ Install paho-mqtt: `pip install paho-mqtt`
2. ✅ Create `.env` file with strong password
3. ✅ Update `mqtt_service.py` to use environment variables
4. ✅ Add `.env` to `.gitignore`
5. ✅ Run Mosquitto with authentication

### Phase 2: Before Testing (This Week) 🟡
6. ✅ Enable TLS/SSL encryption
7. ✅ Implement ACLs
8. ✅ Update ESP32 firmware to use TLS (if direct MQTT)
9. ✅ Test end-to-end encrypted communication

### Phase 3: Production Hardening (Before Deployment) 🟢
10. ✅ Get proper SSL certificates (Let's Encrypt or hospital CA)
11. ✅ Implement per-device authentication
12. ✅ Set up monitoring and alerting
13. ✅ Network segmentation (VLAN)
14. ✅ Regular security audits

---

## Decision: Direct MQTT or Relay?

### Option 1: ESP32 → MQTT Directly (Less Secure)
**Pros:**
- Real-time data
- Low latency

**Cons:**
- Credentials stored on watch
- TLS overhead on ESP32
- Harder to revoke single device

### Option 2: ESP32 → Backend → MQTT (More Secure) ⭐ RECOMMENDED
**Pros:**
- No credentials on watch
- HMAC authentication (already implemented)
- Backend validates before forwarding
- Can revoke individual devices

**Cons:**
- Slight latency increase
- Backend becomes single point of failure

**Your Current v3.3.0 Firmware Uses Option 2** ✅

---

## Conclusion

**Current State**: 🟡 MEDIUM RISK
- Basic authentication ✅
- No TLS ❌
- Credentials in code ❌

**After Phase 1 Fixes**: 🟢 LOW RISK (Safe for Development)
- Environment variables ✅
- Strong passwords ✅
- Local network only ✅

**After Phase 2 Fixes**: 🟢 LOW RISK (Safe for Production)
- TLS encryption ✅
- ACLs ✅
- Audit logging ✅

---

## Immediate Next Steps

1. **Create `.env` file** with strong credentials
2. **Update `mqtt_service.py`** to use env vars
3. **Run Mosquitto** with authentication
4. **Test** that vitals flow securely

**Want me to implement Phase 1 fixes right now?** 🚀
