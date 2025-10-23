# Certificate-Based Authentication Implementation Progress

**Started:** 2025-10-17
**Status:** Days 1-2 Complete (2/7 phases done)

## Overview
Implementing certificate-based authentication (mTLS) to replace hardcoded shared MQTT credentials for ESP32 devices.

---

## ✅ Day 1: Hospital CA Certificate & Database Setup (COMPLETED)

### What Was Done:
1. **Generated Hospital CA Certificate** (4096-bit RSA)
   - Location: `mosquitto/certs/hospital_ca.crt` (public certificate)
   - Location: `mosquitto/certs/hospital_ca.key` (private key - SECURE!)
   - Valid for 10 years (2025-2035)
   - Subject: CN=Hospital CA, O=HospitalName, L=Mumbai, ST=Maharashtra, C=IN

2. **Created Migration 013** - Certificate Provisioning Infrastructure
   - File: `hospital-backend/migrations/013_certificate_provisioning.sql`
   - Tables created:
     - **provisioning_codes**: One-time codes for device provisioning (10 min validity)
     - **device_certificates**: X.509 certificate metadata storage
   - Indexes created for performance (6 indexes total)
   - Applied successfully to hospitaldb database

### Files Created:
- `mosquitto/certs/hospital_ca.crt` (2082 bytes)
- `mosquitto/certs/hospital_ca.key` (3324 bytes)
- `hospital-backend/migrations/013_certificate_provisioning.sql`
- `hospital-backend/apply_migration_013.py`

### Database Tables:
```sql
-- provisioning_codes table
CREATE TABLE provisioning_codes (
    code VARCHAR(20) PRIMARY KEY,
    technician_id VARCHAR(50) NOT NULL REFERENCES staff(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN DEFAULT false,
    used_at TIMESTAMPTZ,
    device_id VARCHAR(50) REFERENCES devices(id)
);

-- device_certificates table
CREATE TABLE device_certificates (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL REFERENCES devices(id) UNIQUE,
    certificate_pem TEXT NOT NULL,
    issued_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked BOOLEAN DEFAULT false,
    revoked_at TIMESTAMPTZ,
    revoked_by VARCHAR(50) REFERENCES staff(id),
    revocation_reason TEXT,
    mac_address VARCHAR(17) NOT NULL,
    serial_number VARCHAR(50)
);
```

---

## ✅ Day 2: Certificate Service (COMPLETED)

### What Was Done:
1. **Created CertificateService Class** (236 lines)
   - File: `hospital-backend/app/services/certificate_service.py`
   - Functionality:
     - `generate_device_certificate()`: Generate signed X.509 certificates for devices
     - `verify_certificate()`: Verify certificate was signed by Hospital CA
     - `extract_device_id()`: Extract device ID from certificate CN

2. **Integrated into FastAPI Application**
   - Modified: `hospital-backend/main.py` (lines 308-316)
   - Certificate service initialized on startup
   - Available globally via `app.state.certificate_service`

### Certificate Details:
- **Device Certificates**: 2048-bit RSA (ESP32 compatible)
- **Validity**: 1 year (configurable)
- **Signature Algorithm**: SHA-256
- **Extensions**:
  - Subject Alternative Name (SAN): device ID + MAC address
  - Key Usage: Digital Signature + Key Encipherment
  - Extended Key Usage: CLIENT_AUTH only (not server auth)
  - Basic Constraints: ca=false (not a CA certificate)
  - Authority Key Identifier: Links to Hospital CA
  - Subject Key Identifier: Unique per certificate

### Files Created:
- `hospital-backend/app/services/certificate_service.py`

### Files Modified:
- `hospital-backend/main.py` (added certificate service initialization)

---

## 🔄 Day 3: Provisioning API Endpoints (PENDING)

### Planned Work:
1. Create `hospital-backend/app/api/v1/provisioning.py` with 4 endpoints:
   - `POST /generate-code`: Generate 10-minute provisioning code
   - `POST /provision-with-certificate`: Issue device certificate using code
   - `POST /revoke-certificate/{device_id}`: Revoke compromised certificate
   - `GET /codes`: List recent provisioning codes
2. Register provisioning router in main.py
3. Test via Swagger UI

### Expected Completion Time: 1h 30m

---

## 📋 Day 4: Mosquitto Configuration (PENDING)

### Planned Work:
1. Backup existing Mosquitto config
2. Update `mosquitto/config/mosquitto.conf`:
   - Enable `require_certificate true`
   - Set `use_identity_as_username true`
   - Add CA certificate path
3. Update `mosquitto/config/acl.conf` with pattern-based permissions
4. Delete `mosquitto/config/passwords.txt` (no longer needed)
5. Restart Mosquitto broker

### Expected Completion Time: 55m

---

## 📋 Day 5: ESP32 Firmware - Remove Passwords (PENDING)

### Planned Work:
1. Remove hardcoded credentials from ESP32 firmware
   - Delete lines with `hospitalEsp32 / ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF/Q=`
2. Add HTTPClient library
3. Add certificate storage functions:
   - `hasCertificates()`
   - `loadDeviceCertificate()`
   - `saveCertificates()`

### Expected Completion Time: 50m

---

## 📋 Day 6: ESP32 Firmware - Add Certificates (PENDING)

### Planned Work:
1. Replace MQTT provisioning with HTTPS provisioning
2. Update `connectToMQTT()` to use client certificates
3. Update `setup()` to check for certificates
4. Flash updated firmware to ESP32

### Expected Completion Time: 1h 30m

---

## 📋 Day 7: End-to-End Testing (PENDING)

### Planned Work:
1. Test backend certificate service initialization
2. Generate provisioning code via API
3. Provision ESP32 device via captive portal
4. Verify certificate in database
5. Verify MQTT connection in logs
6. Send test vitals data
7. Test certificate revocation
8. Test device re-provisioning
9. Production deployment checklist

### Expected Completion Time: 1h 30m

---

## Security Improvements

### Before (Current State):
- ❌ All devices share same hardcoded credentials
- ❌ Credentials can be extracted via firmware dump (30 seconds)
- ❌ No way to revoke compromised device
- ❌ Insider threat: any staff can extract and reuse credentials
- ❌ HIPAA violation: no per-device authentication

### After (Target State):
- ✅ Each device has unique X.509 certificate
- ✅ Certificates generated on-demand during provisioning
- ✅ Certificates can be revoked if device is stolen
- ✅ One-time provisioning codes (10 min expiry)
- ✅ MQTT validates device identity via mTLS
- ✅ HIPAA compliant: strong device authentication

---

## Technical Architecture

### Current Authentication Flow:
```
ESP32 → MQTT Broker (username: hospitalEsp32, password: ahT...)
         ↓
      ✅ Connected (all devices use same credentials)
```

### New Authentication Flow (After Day 7):
```
Technician → Backend API: POST /generate-code
            ← code: "ABC123XYZ" (expires in 10 min)

ESP32 → WiFi Hotspot (captive portal)
     → Technician enters code
     → ESP32 → Backend API: POST /provision-with-certificate
               ← device_cert.pem + device_key.pem
     → ESP32 saves to SPIFFS

ESP32 → Mosquitto Broker (TLS with client certificate)
     → Mosquitto validates certificate against Hospital CA
     → Mosquitto extracts device_id from certificate CN
     → Mosquitto checks ACL permissions
         ↓
      ✅ Connected with unique device identity
```

---

## Next Steps

**Ready to continue with Day 3:**
- Create provisioning API endpoints
- Implement one-time code generation
- Implement certificate issuance endpoint
- Test via Swagger UI

**Estimated Time Remaining:** 5 hours 35 minutes (Days 3-7)

---

## Notes

- CA private key is stored in `mosquitto/certs/hospital_ca.key` - **must be kept secure** in production
- Device private keys are NOT stored in database - only sent to device once during provisioning
- Certificate expiry is set to 1 year - renewal workflow needed before 2026-10-17
- IDE warnings about missing type stubs are cosmetic only - functionality is not affected
