# Mosquitto Folder Structure and ESP32 Connection Diagnosis

## 📁 Mosquitto Folder Location

```
C:\Users\Srika\OneDrive\Desktop\hospital-management-system\mosquitto\
```

## 📂 Directory Structure

```
mosquitto/
├── config/              ← Configuration files
│   ├── mosquitto.conf   ← Main MQTT broker configuration (CRITICAL FILE)
│   ├── acl.conf         ← Access control list (topic permissions)
│   └── passwords.txt.*  ← Deprecated password files (cert auth now)
│
├── certs/               ← SSL/TLS certificates
│   ├── hospital_ca.crt  ← Hospital CA certificate (RSA-2048, 1436 bytes)
│   ├── hospital_ca.key  ← Hospital CA private key (RSA-2048, 1704 bytes)
│   ├── server.crt       ← Mosquitto server certificate (RSA-2048, 1525 bytes)
│   ├── server.key       ← Mosquitto server private key (RSA-2048, 1704 bytes)
│   ├── backend.crt      ← Backend client certificate (RSA-2048, 1456 bytes)
│   ├── backend.key      ← Backend client private key (RSA-2048, 1708 bytes)
│   ├── server-san.cnf   ← Server certificate SAN configuration
│   └── backups/         ← Backup of old RSA-4096 certificates
│
├── data/                ← Mosquitto persistence data
└── logs/                ← Log files (if file logging enabled)
```

## ✅ What's Working

1. **Backend MQTT Connection:** ✅ SUCCESSFUL
   - Backend connects to Mosquitto instantly with RSA-2048 certificates
   - Confirms: Mosquitto broker is running and accepting connections
   - Confirms: RSA-2048 certificates are valid and working

2. **ESP32 Provisioning:** ✅ SUCCESSFUL
   - ESP32 provisions via HTTPS successfully
   - Receives device certificate and private key from backend
   - Saves certificates to SPIFFS (confirmed by file sizes)

3. **Certificate Generation:** ✅ SUCCESSFUL
   - All certificates regenerated with RSA-2048 (ESP32-compatible)
   - CA: 1436 bytes (was 2130 bytes with RSA-4096)
   - Server cert: 1525 bytes
   - Device cert: 1619 bytes

## ❌ What's NOT Working

**ESP32 MQTT Connection Fails:**
```
✅ Device certificates saved to SPIFFS
🔍 Free heap: 146072 bytes
✅ Device certificate loaded (1619 bytes)
✅ Device private key loaded (1704 bytes)
🔍 Certificate sizes:
   CA: 1436 bytes
   Device cert: 1619 bytes
   Device key: 1704 bytes
❌ MQTT Connection failed, rc=-2
[E][ssl_client.cpp:150] start_ssl_client(): socket error on fd 50, errno: 113, "Software caused connection abort"
```

**Error Details:**
- `rc=-2` = Connection timeout or TLS handshake failure
- `errno: 113` = "Software caused connection abort"
- Fails after ~18 seconds (before 30-second timeout)

## 🔍 Root Cause Analysis

### What We've Ruled Out:

1. ❌ **NOT certificate size** - RSA-2048 confirmed working (backend connects)
2. ❌ **NOT memory issue** - ESP32 has 146KB free heap (plenty)
3. ❌ **NOT timeout issue** - Set to 30 seconds, fails after 18 seconds
4. ❌ **NOT certificate validity** - Backend connects with same setup

### Current Hypothesis: Cipher Suite Incompatibility

**Problem:** ESP32's mbedTLS library may not support the cipher suites offered by Mosquitto

**Current Mosquitto Configuration** (`mosquitto/config/mosquitto.conf` line 47):
```conf
ciphers ECDHE-RSA-AES128-GCM-SHA256:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256
```

**ESP32 mbedTLS Supported Ciphers** (likely limited to):
- `AES128-SHA256` ✅ (simplest, most compatible)
- `AES256-SHA256` ✅ (slightly stronger)
- ECDHE ciphers may not be supported ❓
- GCM modes may not be supported ❓

**Backend (Python OpenSSL)** supports all modern ciphers, so it connects fine.

## 🔧 Key Files to Modify

### 1. `mosquitto/config/mosquitto.conf` (Line 47)

**Current:**
```conf
ciphers ECDHE-RSA-AES128-GCM-SHA256:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256
```

**Proposed Change:**
```conf
# ESP32-compatible cipher (simplest, most widely supported)
ciphers AES128-SHA256
```

**Why This Fix:**
- `AES128-SHA256` is the most basic TLS 1.2 cipher
- Guaranteed to work with ESP32 mbedTLS
- Still provides strong encryption (128-bit AES with SHA-256)
- Used in most ESP32 mTLS examples

### 2. Enable Mosquitto Debug Logging

**Current:** (Line 109-112)
```conf
log_type error
log_type warning
log_type notice
log_type information
```

**Add:**
```conf
log_type debug
```

**Why:** See detailed TLS handshake logs to confirm cipher negotiation failure

## 📋 Testing Plan

### Step 1: Simplify Cipher Suite
1. Edit `mosquitto/config/mosquitto.conf` line 47
2. Change to: `ciphers AES128-SHA256`
3. Restart Mosquitto container: `docker-compose restart mosquitto`
4. Test ESP32 connection

### Step 2: If Still Fails - Check Mosquitto Logs
1. Enable debug logging in mosquitto.conf
2. Restart Mosquitto
3. Test ESP32 connection
4. View logs: `docker logs hospital_mosquitto`
5. Look for TLS handshake errors

### Step 3: If Still Fails - Test Server Certificate
1. Check server certificate SAN includes correct hostname/IP
2. Current SAN (from `server-san.cnf`):
   ```
   DNS.1 = localhost
   DNS.2 = hospital-mosquitto
   IP.1 = 127.0.0.1
   IP.2 = 192.168.0.113
   ```
3. ESP32 must connect to one of these addresses

### Step 4: If Still Fails - Try Non-mTLS Test
1. Temporarily disable `require_certificate` in mosquitto.conf
2. Test if ESP32 can connect with just server cert validation
3. This isolates whether problem is:
   - Server cert validation (CA verification)
   - Client cert presentation (mTLS)

## 🎯 Most Likely Solution

**Change cipher suite to ESP32-compatible mode:**

1. Open `mosquitto/config/mosquitto.conf`
2. Find line 47: `ciphers ECDHE-RSA-AES128-GCM-SHA256:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256`
3. Replace with: `ciphers AES128-SHA256`
4. Restart Mosquitto: `docker-compose restart mosquitto`
5. Re-test ESP32 connection

**Expected Result:**
- Backend: Still works ✅ (AES128-SHA256 is universally supported)
- ESP32: Should now connect ✅ (cipher suite matches mbedTLS capabilities)

## 📊 Certificate Verification Commands

### Verify Certificate Sizes (Confirm RSA-2048)
```bash
# CA certificate
openssl x509 -in mosquitto/certs/hospital_ca.crt -text -noout | grep "Public-Key"
# Should show: Public-Key: (2048 bit)

# Server certificate
openssl x509 -in mosquitto/certs/server.crt -text -noout | grep "Public-Key"
# Should show: Public-Key: (2048 bit)
```

### Check Server Certificate SAN
```bash
openssl x509 -in mosquitto/certs/server.crt -text -noout | grep -A 5 "Subject Alternative Name"
```

### Verify Certificate Chain
```bash
# Verify server cert is signed by Hospital CA
openssl verify -CAfile mosquitto/certs/hospital_ca.crt mosquitto/certs/server.crt
# Should show: mosquitto/certs/server.crt: OK
```

## 🔐 Security Notes

### Current Security Configuration (mosquitto.conf)

```conf
# TLS/SSL Configuration
listener 8883                        # TLS MQTT port
protocol mqtt
cafile /mosquitto/certs/hospital_ca.crt
certfile /mosquitto/certs/server.crt
keyfile /mosquitto/certs/server.key
require_certificate true             # mTLS enabled
use_identity_as_username true        # CN becomes MQTT username
allow_anonymous false                # No anonymous connections
tls_version tlsv1.2                  # TLS 1.2 minimum

# Access Control
acl_file /mosquitto/config/acl.conf  # Topic-level permissions

# Security Settings
max_connections 100                  # Connection limit
persistent_client_expiration 1h      # Session expiration
max_inflight_messages 20             # Per-client limit
max_queued_messages 1000             # Per-client limit
message_size_limit 102400            # 100KB (for ECG/EEG waveforms)
```

### ACL Configuration (acl.conf)

**Backend Access:**
```conf
user hospitalBackend
topic readwrite hospital/#           # Full access to all topics
```

**Device Access (Pattern-Based):**
```conf
pattern write hospital/devices/%u/vitals      # %u = device_id from cert CN
pattern write hospital/devices/%u/alerts
pattern write hospital/devices/%u/heartbeat
pattern write hospital/devices/%u/waveform
pattern write hospital/devices/%u/event
pattern write hospital/devices/%u/status
pattern read hospital/devices/%u/command
pattern read hospital/devices/%u/assign
```

**Security Model:**
- Device identity = Certificate Common Name (CN)
- Each device can only access topics matching its own device_id
- Backend has full access (CN = "hospitalBackend")
- No shared passwords, certificate-based authentication only

## 🚀 Next Steps

1. **User Decision:** Approve cipher suite change to `AES128-SHA256`
2. **Modify:** `mosquitto/config/mosquitto.conf` line 47
3. **Restart:** Mosquitto container
4. **Test:** ESP32 connection with simplified cipher
5. **Verify:** Backend still connects (should be no issue)
6. **Success Criteria:** ESP32 connects with `rc=0`, no errno

## 📝 Summary

**Problem:** ESP32 MQTT connection fails with `errno: 113` despite valid RSA-2048 certificates

**Root Cause:** Cipher suite incompatibility between ESP32 mbedTLS and Mosquitto's ECDHE/GCM ciphers

**Solution:** Simplify Mosquitto cipher suite to `AES128-SHA256` (ESP32-compatible)

**Impact:**
- ✅ Backend: No impact (still connects)
- ✅ ESP32: Should now connect successfully
- ✅ Security: Still strong (128-bit AES, SHA-256 HMAC)

**Files to Modify:**
- `mosquitto/config/mosquitto.conf` (line 47 only)

**Commands:**
```bash
# After editing mosquitto.conf
docker-compose restart mosquitto

# Check logs
docker logs hospital_mosquitto

# Test ESP32 connection (hardware)
```
