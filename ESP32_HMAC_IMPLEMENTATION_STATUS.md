# ESP32 HMAC Authentication - Implementation Status

**Date:** 2025-10-14
**Status:** In Progress
**Phase:** Backend Implementation Complete, Testing Pending

---

## Implementation Progress

### ✅ Completed

#### 1. Backend Configuration
- **File:** `hospital-backend/app/core/config.py`
- **Changes:**
  - Added `esp32FactorySecret` config (default: needs to be set in production)
  - Added `esp32TimestampWindow` config (default: 300 seconds / 5 minutes)
- **Environment Variables:**
  ```bash
  ESP32_FACTORY_SECRET="your-64-char-secret-key-here"
  ESP32_TIMESTAMP_WINDOW=300
  ```

#### 2. HMAC Authentication Middleware
- **File:** `hospital-backend/app/middleware/esp32_hmac_auth.py` (NEW)
- **Features:**
  - `ESP32HMACAuth` class for HMAC-SHA256 validation
  - Timestamp validation (prevents replay attacks)
  - MAC address format validation
  - Signature computation and verification
  - FastAPI dependency: `verify_esp32_hmac()`
- **Security:**
  - Constant-time comparison (prevents timing attacks)
  - 5-minute timestamp window
  - HMAC-SHA256 cryptographic signature

#### 3. Provisioning Endpoint Updated
- **File:** `hospital-backend/app/api/v1/esp32.py`
- **Changes:**
  - Removed `deviceKey` generation from INSERT statement
  - Removed `deviceKey` from response JSON
  - Added `macAddress` to response (for ESP32 reference)
  - Updated message: "Device provisioned successfully (HMAC authentication)"
- **Authentication Flow (UNCHANGED - WORKING):**
  1. Technician provides: Provisioner ID + Password
  2. Backend validates: Staff ID exists, password matches (bcrypt), role is Technician/Provisioner
  3. Backend creates device record with MAC address
  4. Backend returns: deviceId, serialNumber, macAddress, provisionedBy

---

### ⏳ In Progress

#### 4. ESP32 Runtime Endpoints - HMAC Authentication
- **Status:** Needs implementation
- **Endpoints to Update:**
  - `/register` - Device registration (first contact after provisioning)
  - `/{deviceId}/heartbeat` - Periodic status updates
  - `/{deviceId}/vitals/{patientId}` - Vital signs data
  - `/{deviceId}/alert` - Emergency alerts

**Required Changes Per Endpoint:**
```python
# OLD (Device Key):
device_key: str = Header(None, alias="X-Device-Key")
# Validate deviceKey from database

# NEW (HMAC):
device_mac: str = Header(None, alias="X-Device-MAC"),
device_signature: str = Header(None, alias="X-Device-Signature"),
device_timestamp: str = Header(None, alias="X-Timestamp")
# Validate HMAC signature using middleware
```

---

### 📋 Pending

#### 5. Database Migration
- **File:** `hospital-backend/migrations/009_remove_device_key.sql` (NEW)
- **Changes:**
  - `ALTER TABLE devices DROP COLUMN "deviceKey"`
  - Add index on `macAddress` for fast lookups
- **Rollback:** `009_rollback.sql`
  - Re-add `deviceKey` column if needed

#### 6. HMAC Authentication Test Suite
- **File:** `hospital-backend/test_esp32_hmac_auth.py` (NEW)
- **Test Cases:**
  1. Device provisioning with valid staff credentials
  2. Device registration with valid HMAC signature
  3. Registration blocked without signature (401)
  4. Registration blocked with invalid signature (403)
  5. Registration blocked with expired timestamp (401)
  6. Heartbeat with valid HMAC
  7. Vitals upload with valid HMAC
  8. Emergency alert with valid HMAC
  9. Spoofing attack prevention
  10. MAC address mismatch detection

#### 7. Documentation Updates
- **File:** `ESP32_SCALABLE_AUTHENTICATION_DESIGN.md`
- **Updates Needed:**
  - Clarify two-phase provisioning (WiFi → Staff Auth → Provisioning)
  - Add ESP32 firmware pseudocode for HMAC computation
  - Add hospital deployment step-by-step guide
  - Add security analysis section

#### 8. End-to-End Testing
- Restart backend with new configuration
- Run HMAC test suite
- Verify provisioning workflow
- Verify runtime authentication
- Performance testing

---

## Authenticated Provisioning Workflow (CLARIFIED)

### Phase 1: WiFi Configuration (No Authentication)
1. ESP32 creates WiFi AP: "ESP32-WATCH-XXXXX"
2. Technician connects phone to ESP32 WiFi
3. Web portal opens: `http://192.168.4.1`
4. Technician enters:
   - Hospital WiFi SSID
   - Hospital WiFi Password
   - Backend Server URL
5. ESP32 saves config to NVS, connects to hospital WiFi

### Phase 2: Device Provisioning (REQUIRES STAFF AUTHENTICATION)
1. ESP32 starts web server: `http://192.168.1.205`
2. Technician opens provisioning form in browser
3. Form displays:
   - Device MAC address (read-only, auto-detected)
   - **Provisioner ID field** (e.g., TEC0001)
   - **Provisioner Password field** (masked input)
4. Technician enters staff credentials
5. ESP32 sends to backend:
   ```json
   POST /api/v1/esp32/provision
   {
     "macaddress": "AA:BB:CC:DD:EE:FF",
     "devicetype": "watch",
     "firmwareversion": "1.0.0",
     "provisionerid": "TEC0001",
     "provisionerpassword": "tech123"
   }
   ```
6. Backend validates:
   - Provisioner ID exists ✓
   - Password matches (bcrypt) ✓
   - Role is Technician or Provisioner ✓
   - MAC not already provisioned ✓
7. Backend creates device record (without deviceKey)
8. Backend returns success with deviceId, serialNumber
9. ESP32 saves deviceId to NVS
10. Device ready for HMAC-authenticated operation

### Phase 3: Runtime Operation (HMAC Authentication)
1. ESP32 reads: MAC address (hardware), factory secret (firmware), deviceId (NVS)
2. For each API call:
   - Get current timestamp (NTP)
   - Compute: `signature = HMAC-SHA256(secret, MAC + timestamp + endpoint)`
   - Send headers: `X-Device-MAC`, `X-Device-Signature`, `X-Timestamp`
3. Backend validates HMAC signature
4. Backend processes request

---

## Security Model

### Authentication Layers:
1. **Provisioning:** Staff ID + Password (bcrypt validation)
2. **Runtime:** HMAC-SHA256 with factory secret + MAC address
3. **Replay Protection:** Timestamp validation (5-minute window)
4. **MAC Binding:** Device MAC address stored during provisioning

### Key Security Properties:
- ✅ Only authorized staff can provision devices
- ✅ Factory secret never transmitted (used for HMAC only)
- ✅ Each device has unique MAC address (hardware identifier)
- ✅ Signatures expire after 5 minutes (prevents replay)
- ✅ Constant-time comparison (prevents timing attacks)
- ✅ Audit trail (who provisioned which device, when)

---

## Next Steps

### Immediate (Today):
1. **Update ESP32 runtime endpoints** with HMAC authentication
   - Register endpoint
   - Heartbeat endpoint
   - Vitals endpoint
   - Alert endpoint

2. **Create database migration** to remove deviceKey column

3. **Create HMAC test suite** to verify all authentication flows

4. **Run end-to-end tests**

### Short-term (This Week):
1. **Document ESP32 firmware requirements** (HMAC computation, WiFi provisioning)
2. **Create hospital deployment guide** (step-by-step with screenshots)
3. **Performance testing** (HMAC overhead, throughput)
4. **Security audit** (penetration testing)

### Medium-term (Next Week):
1. **ESP32 firmware development** (C++ implementation)
2. **WiFi provisioning portal** (HTML/JavaScript)
3. **Provisioning web form** (staff authentication)
4. **Integration testing** with actual ESP32 hardware

---

## Technical Decisions Made

### 1. Why HMAC-SHA256 instead of per-device keys?
- **Scalability:** Same firmware binary for all devices
- **Factory-friendly:** No per-device configuration needed
- **Secure:** HMAC with shared secret + unique MAC is cryptographically strong
- **Practical:** 500+ devices can't have unique keys flashed at factory

### 2. Why two-phase provisioning (WiFi → Staff Auth)?
- **Security:** Prevents unauthorized device provisioning
- **Audit Trail:** Tracks which staff member provisioned which device
- **Role-Based Access:** Only Technician/Provisioner roles allowed
- **Compliance:** Meets medical device tracking requirements

### 3. Why 5-minute timestamp window?
- **Balance:** Long enough for clock skew, short enough to prevent replays
- **Medical Context:** Vital signs updates every 5 seconds, 5-minute window is safe
- **NTP Sync:** ESP32 syncs time with NTP server at boot

### 4. Why MAC address as device identifier?
- **Hardware Unique:** ESP32 MAC is burned into chip at factory
- **Immutable:** Cannot be easily changed without hardware modification
- **Accessible:** ESP32 firmware can read MAC via `WiFi.macAddress()`
- **No Configuration:** No need to store unique ID in firmware

---

## Open Questions

### 1. Factory Secret Management
**Question:** How should factory secret be stored in ESP32 firmware?
**Options:**
- A. Plain text in firmware (easy, less secure)
- B. ESP32 flash encryption (secure, more complex)
- C. ESP32 secure boot + flash encryption (most secure, complex setup)

**Recommendation:** Start with Option A for development, move to Option B for production.

### 2. Secret Rotation
**Question:** How to rotate factory secret if compromised?
**Answer:**
- Generate new secret
- Update backend config
- Flash new firmware to all devices
- Devices re-provision with new secret

**Note:** This is a nuclear option - avoid by protecting secret properly.

### 3. Multi-Hospital Deployment
**Question:** Should each hospital have different factory secret?
**Answer:**
- **NO:** Same secret for all hospitals (simpler firmware)
- **Isolation:** Each hospital has separate backend server
- **Security:** Devices configured per hospital (WiFi + backend URL)

---

## Implementation Timeline

| Phase | Task | Duration | Status |
|-------|------|----------|--------|
| 1 | Backend Config | 30 min | ✅ Complete |
| 2 | HMAC Middleware | 2 hours | ✅ Complete |
| 3 | Provisioning Update | 1 hour | ✅ Complete |
| 4 | Runtime Endpoints | 3 hours | ⏳ In Progress |
| 5 | Database Migration | 30 min | 📋 Pending |
| 6 | Test Suite | 2 hours | 📋 Pending |
| 7 | Documentation | 2 hours | 📋 Pending |
| 8 | End-to-End Testing | 2 hours | 📋 Pending |
| **Total** | | **13 hours** | **38% Complete** |

---

## Files Created/Modified

### Created:
- `hospital-backend/app/middleware/esp32_hmac_auth.py` - HMAC authentication
- `ESP32_HMAC_IMPLEMENTATION_STATUS.md` - This document

### Modified:
- `hospital-backend/app/core/config.py` - Added ESP32 config
- `hospital-backend/app/api/v1/esp32.py` - Updated provisioning endpoint

### To Be Created:
- `hospital-backend/migrations/009_remove_device_key.sql`
- `hospital-backend/migrations/009_rollback.sql`
- `hospital-backend/test_esp32_hmac_auth.py`

### To Be Modified:
- `hospital-backend/app/api/v1/esp32.py` - Update runtime endpoints
- `ESP32_SCALABLE_AUTHENTICATION_DESIGN.md` - Add authenticated provisioning flow

---

## Contact & Support

**Implementation Lead:** Claude Code
**Date Started:** 2025-10-14
**Target Completion:** 2025-10-15
**Status Updates:** This document

---

**Last Updated:** 2025-10-14 11:45 UTC
**Next Update:** After runtime endpoints implementation
