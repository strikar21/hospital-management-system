# Complete Certificate Audit - Hospital Management System

## Date: 2025-10-18

## Certificate Inventory

### 1. ESP32 Data Folder

#### `esp32_hospital_watch_complete/data/ca.crt`
- **Purpose:** Hospital CA certificate for ESP32 to verify Mosquitto server certificate
- **Type:** CA Certificate (Root)
- **Details:**
  ```
  Issuer: C=IN, ST=Telangana, L=Hyderabad, O=Symbiot, OU=SymHMS Development, CN=Symbiot Hospital CA
  Subject: C=IN, ST=Telangana, L=Hyderabad, O=Symbiot, OU=SymHMS Development, CN=Symbiot Hospital CA
  Valid: Oct 18 2025 - Oct 16 2035 (10 years)
  Size: 2164 bytes
  ```
- **Status:** ✅ CORRECT - Updated Oct 18 with proper Symbiot details
- **Used By:** ESP32 firmware (uploaded to SPIFFS, then loaded at runtime)
- **Note:** This is uploaded to ESP32 SPIFFS at `/spiffs/ca.crt`

---

### 2. Backend SSL Certificates (HTTPS API)

#### `hospital-backend/ssl/cert.pem`
- **Purpose:** Backend HTTPS API server certificate
- **Type:** Server Certificate (Self-signed for development)
- **Details:**
  ```
  Issuer: C=IN, ST=Telangana, L=Hyderabad, O=Symbiot, OU=SymHMS Development, CN=192.168.0.113
  Subject: C=IN, ST=Telangana, L=Hyderabad, O=Symbiot, OU=SymHMS Development, CN=192.168.0.113
  SAN: IP:192.168.0.113, IP:127.0.0.1, DNS:localhost, DNS:*.local
  ```
- **Status:** ✅ CORRECT - Self-signed certificate for backend HTTPS
- **Used By:** Backend main.py (Uvicorn HTTPS server on port 8001)

#### `hospital-backend/ssl/key.pem`
- **Purpose:** Private key for backend SSL certificate
- **Status:** ✅ CORRECT
- **Used By:** Backend main.py (Uvicorn HTTPS server)

---

### 3. Mosquitto MQTT Broker Certificates

#### `mosquitto/certs/hospital_ca.crt` ⭐ PRIMARY CA
- **Purpose:** Hospital CA certificate (Root CA for all device and server certificates)
- **Type:** CA Certificate (Root) - Self-signed
- **Details:**
  ```
  Issuer: C=IN, ST=Telangana, L=Hyderabad, O=Symbiot, OU=SymHMS Development, CN=Symbiot Hospital CA
  Subject: C=IN, ST=Telangana, L=Hyderabad, O=Symbiot, OU=SymHMS Development, CN=Symbiot Hospital CA
  Valid: Oct 18 2025 - Oct 16 2035 (10 years)
  Size: 2164 bytes
  Key Size: 4096-bit RSA
  ```
- **Status:** ✅ CORRECT - Regenerated Oct 18 with proper Symbiot details
- **Used By:**
  - Mosquitto broker (to verify client certificates)
  - Backend CertificateService (to sign device certificates)
  - ESP32 devices (to verify server certificate)
  - Backend MQTT service (should use this to verify Mosquitto server cert)

#### `mosquitto/certs/hospital_ca.key` ⭐ PRIMARY CA PRIVATE KEY
- **Purpose:** Private key for Hospital CA (signs device and server certificates)
- **Type:** CA Private Key
- **Status:** ✅ CORRECT - Generated Oct 18
- **Used By:** Backend CertificateService (to sign device certificates)
- **⚠️ CRITICAL:** Must be kept secure - anyone with this key can create valid device certificates

#### `mosquitto/certs/server.crt`
- **Purpose:** Mosquitto MQTT broker server certificate
- **Type:** Server Certificate
- **Details:**
  ```
  Issuer: C=IN, ST=Telangana, L=Hyderabad, O=Symbiot, OU=SymHMS Development, CN=Symbiot Hospital CA
  Subject: C=IN, ST=Telangana, L=Hyderabad, O=Symbiot, OU=SymHMS Development, CN=localhost
  SAN: DNS:localhost, DNS:hospital-mosquitto, IP:127.0.0.1, IP:192.168.0.113
  Valid: Oct 18 2025 - Oct 16 2035 (10 years)
  Signed by: hospital_ca.crt
  ```
- **Status:** ✅ CORRECT - Regenerated Oct 18, signed by new Hospital CA
- **Used By:** Mosquitto broker (presented to clients during TLS handshake)
- **Verified By:** All MQTT clients using `hospital_ca.crt`

#### `mosquitto/certs/server.key`
- **Purpose:** Private key for Mosquitto server certificate
- **Status:** ✅ CORRECT - Generated Oct 18
- **Used By:** Mosquitto broker

#### `mosquitto/certs/ca.crt` ❌ OLD/DEPRECATED
- **Purpose:** OLD Hospital CA certificate (from Oct 16)
- **Type:** CA Certificate (Root) - Obsolete
- **Details:**
  ```
  Issuer: C=IN, ST=Maharashtra, L=Mumbai, O=HospitalName, OU=IT, CN=Hospital CA (OLD)
  Subject: C=IN, ST=Maharashtra, L=Mumbai, O=HospitalName, OU=IT, CN=Hospital CA (OLD)
  ```
- **Status:** ❌ DEPRECATED - Should NOT be used
- **Currently Used By:** Backend MQTT service (WRONG! This is the bug!)
- **Action Needed:** Remove or rename to `ca.crt.old` to avoid confusion

#### `mosquitto/certs/ca.key` ❌ OLD/DEPRECATED
- **Purpose:** OLD Hospital CA private key
- **Status:** ❌ DEPRECATED - Should NOT be used
- **Action Needed:** Remove or rename to `ca.key.old`

---

### 4. Backend Alternative Cert Location (Duplicate)

#### `hospital-backend/certs/cert.pem`
- **Status:** ❓ UNKNOWN - Duplicate of `ssl/cert.pem`?
- **Action Needed:** Check if this is a duplicate and remove if unnecessary

#### `hospital-backend/certs/key.pem`
- **Status:** ❓ UNKNOWN - Duplicate of `ssl/key.pem`?
- **Action Needed:** Check if this is a duplicate and remove if unnecessary

---

## Certificates Needed But Missing

### 1. Backend MQTT Client Certificate ❌ MISSING
- **Purpose:** Backend needs client certificate to connect to Mosquitto with mTLS
- **Type:** Client Certificate
- **Should be:** `mosquitto/certs/backend.crt` and `backend.key`
- **Details:**
  ```
  Should have:
  Issuer: CN=Symbiot Hospital CA
  Subject: CN=hospitalBackend (or similar)
  Signed by: hospital_ca.crt
  ```
- **Status:** ❌ DOES NOT EXIST
- **Impact:** Backend cannot connect to Mosquitto when `require_certificate true`
- **Solution Options:**
  - Generate backend client certificate
  - OR temporarily disable `require_certificate` in Mosquitto config

### 2. ESP32 Device Certificates (Dynamic) ✅ GENERATED AT RUNTIME
- **Purpose:** Unique certificate for each ESP32 device
- **Type:** Client Certificate
- **Stored:** ESP32 SPIFFS at `/spiffs/device.crt` and `/spiffs/device.key`
- **Generation:** Created by backend during provisioning, sent to ESP32 via HTTPS
- **Details:**
  ```
  Issuer: CN=Symbiot Hospital CA
  Subject: CN=ESP32-WATCH-<MAC_ADDRESS>
  Organization: C=IN, ST=Telangana, L=Hyderabad, O=Symbiot, OU=SymHMS Development
  Validity: 365 days
  Key Size: 2048-bit RSA (ESP32 compatible)
  Signed by: hospital_ca.crt (using hospital_ca.key)
  ```
- **Status:** ✅ CORRECT - Backend generates with updated Symbiot details after code fix
- **Note:** NOT stored in project files - only in database and ESP32 SPIFFS

---

## Certificate Chain Diagrams

### Current mTLS Certificate Chain (After Fixes)

```
Hospital CA (hospital_ca.crt) - Self-signed Root CA
│
├─→ Mosquitto Server Certificate (server.crt)
│   └─ Presented by Mosquitto to clients
│   └─ Verified by: ESP32, Backend (using hospital_ca.crt)
│
├─→ ESP32 Device Certificates (device.crt) - One per device
│   └─ Generated during provisioning
│   └─ Stored in ESP32 SPIFFS
│   └─ Presented to Mosquitto during connection
│   └─ Verified by: Mosquitto (using hospital_ca.crt)
│
└─→ Backend Client Certificate (backend.crt) ❌ MISSING!
    └─ Should be generated for backend MQTT service
    └─ Presented to Mosquitto during connection
    └─ Verified by: Mosquitto (using hospital_ca.crt)
```

### Backend HTTPS API (Separate from MQTT)

```
Backend SSL Certificate (ssl/cert.pem) - Self-signed
└─ Purpose: Secure HTTPS API on port 8001
└─ Used by: ESP32 provisioning, Frontend API calls
└─ Verification: Self-signed, clients must trust or use insecure mode
└─ Independent from MQTT mTLS chain
```

---

## Configuration Files Using Certificates

### 1. Mosquitto Config
**File:** `mosquitto/config/mosquitto.conf`

```conf
# Line 28: CA certificate to verify client certificates
cafile /mosquitto/certs/hospital_ca.crt  ✅ CORRECT

# Line 31: Server certificate
certfile /mosquitto/certs/server.crt  ✅ CORRECT

# Line 32: Server private key
keyfile /mosquitto/certs/server.key  ✅ CORRECT

# Line 36: Require client certificates (mTLS)
require_certificate true  ⚠️ BLOCKS backend connection (no backend cert)
```

### 2. Backend Main.py (HTTPS)
**File:** `hospital-backend/main.py`

```python
# Lines ~542-544: HTTPS SSL configuration
ssl_keyfile="ssl/key.pem",    ✅ CORRECT
ssl_certfile="ssl/cert.pem",  ✅ CORRECT
```

### 3. Backend MQTT Service
**File:** `hospital-backend/app/services/mqtt_service.py`

```python
# Line 48: CA certificate for server verification
'ca_certs': 'C:/Users/Srika/.../mosquitto/certs/ca.crt'  ❌ WRONG! Should be hospital_ca.crt

# Lines 84-86: Client certificate configuration
certfile=None,  ❌ MISSING! Should point to backend client cert
keyfile=None,   ❌ MISSING! Should point to backend client key
```

### 4. Backend Certificate Service
**File:** `hospital-backend/main.py` lines 315-317

```python
ca_cert_path = os.path.join(..., "mosquitto", "certs", "hospital_ca.crt")  ✅ CORRECT
ca_key_path = os.path.join(..., "mosquitto", "certs", "hospital_ca.key")   ✅ CORRECT
app.state.certificate_service = CertificateService(ca_cert_path, ca_key_path)  ✅ CORRECT
```

### 5. Backend Provisioning Endpoint
**File:** `hospital-backend/app/api/v1/provisioning.py` lines 321-325

```python
# Loads CA cert to send to ESP32
ca_cert_path = os.path.join(..., "mosquitto", "certs", "hospital_ca.crt")  ✅ CORRECT
with open(ca_cert_path, 'r') as f:
    ca_certificate_pem = f.read()  ✅ CORRECT
```

### 6. ESP32 Firmware
**File:** `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`

```cpp
// Loaded from SPIFFS at runtime
String caCertificate;  // Loaded from /spiffs/ca.crt  ✅ CORRECT (after SPIFFS upload)
String deviceCert;     // Loaded from /spiffs/device.crt  ✅ CORRECT (from provisioning)
String deviceKey;      // Loaded from /spiffs/device.key  ✅ CORRECT (from provisioning)

// Lines 1009-1011: mTLS configuration
wifiClient.setCACert(caCertificate.c_str());      ✅ CORRECT
wifiClient.setCertificate(deviceCert.c_str());    ✅ CORRECT
wifiClient.setPrivateKey(deviceKey.c_str());      ✅ CORRECT
```

---

## Issues Found

### Issue 1: Backend MQTT Service Using Wrong CA Certificate ❌ CRITICAL
**File:** `hospital-backend/app/services/mqtt_service.py` line 48

**Current (WRONG):**
```python
'ca_certs': '.../mosquitto/certs/ca.crt'  # OLD CA from Oct 16
```

**Should be:**
```python
'ca_certs': '.../mosquitto/certs/hospital_ca.crt'  # NEW CA from Oct 18
```

**Impact:** Backend cannot verify Mosquitto server certificate → TLS handshake failure

---

### Issue 2: Backend Has No Client Certificate ❌ CRITICAL
**File:** `hospital-backend/app/services/mqtt_service.py` lines 84-86

**Current:**
```python
certfile=None,  # No client certificate
keyfile=None,   # No private key
```

**Impact:** Mosquitto rejects connection when `require_certificate true`

**Solution Options:**
1. **Generate backend client certificate** (proper solution)
2. **Disable client cert requirement temporarily** (quick fix)

---

### Issue 3: Old CA Certificates Still Present ⚠️ CLEANUP NEEDED
**Files:**
- `mosquitto/certs/ca.crt` (OLD - Oct 16)
- `mosquitto/certs/ca.key` (OLD - Oct 16)

**Impact:** Confusing, could be used accidentally (as in Issue #1!)

**Solution:** Rename to `ca.crt.old` and `ca.key.old`

---

## Recommendations

### Immediate Fixes (To Get System Working):

1. **Fix Backend MQTT CA Path** - Change `ca.crt` → `hospital_ca.crt`
2. **Temporarily Disable Mosquitto Client Cert** - Set `require_certificate false`
3. **Restart Services** - Restart backend and Mosquitto

### Future Improvements (Proper mTLS):

1. **Generate Backend Client Certificate:**
   ```bash
   # Use backend CertificateService or manual openssl
   # Save to mosquitto/certs/backend.crt and backend.key
   ```

2. **Update Backend MQTT Service:**
   ```python
   certfile='mosquitto/certs/backend.crt',
   keyfile='mosquitto/certs/backend.key',
   ```

3. **Re-enable Mosquitto Client Cert:**
   ```conf
   require_certificate true
   ```

4. **Clean Up Old Certificates:**
   ```bash
   mv ca.crt ca.crt.old
   mv ca.key ca.key.old
   ```

---

## Certificate Lifecycle

### CA Certificate (hospital_ca.crt):
- **Lifespan:** 10 years (until Oct 2035)
- **Renewal:** Must regenerate all device and server certificates after renewal
- **Backup:** Critical - store securely

### Server Certificate (server.crt):
- **Lifespan:** 10 years (until Oct 2035)
- **Renewal:** Can be renewed independently, signed by same CA

### Device Certificates:
- **Lifespan:** 365 days (1 year)
- **Renewal:** Automatic via re-provisioning
- **Revocation:** Supported via database flag (`revoked=true`)

### Backend SSL Certificate (ssl/cert.pem):
- **Lifespan:** Self-signed, no expiry tracking
- **Renewal:** Manual regeneration when needed
- **Purpose:** Development only - production should use proper SSL

---

## Summary

### ✅ Working Correctly:
- Hospital CA certificate (hospital_ca.crt)
- Mosquitto server certificate (server.crt)
- Device certificate generation (CertificateService)
- ESP32 SPIFFS CA certificate (ca.crt)
- Backend SSL HTTPS certificate
- Backend provisioning endpoint certificate delivery

### ❌ Needs Fixing:
- Backend MQTT service CA path (using old `ca.crt`)
- Backend MQTT client certificate (doesn't exist)
- Mosquitto client cert requirement (blocks backend)

### ⚠️ Cleanup Needed:
- Old `ca.crt` and `ca.key` files (deprecated)
- Duplicate `hospital-backend/certs/*` files (if any)

---

**Next Action:** Fix the two critical issues to enable MQTT connectivity for both backend and ESP32 devices.
