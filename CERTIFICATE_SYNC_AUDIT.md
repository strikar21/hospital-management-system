# Certificate Synchronization Audit

**Date:** 2025-10-19
**Status:** ✅ Certificates in sync (with cleanup needed)

---

## Certificate Inventory

### ✅ Active Certificates (RSA-2048, Oct 19, 2025)

| Location | File | Type | Key Size | Status | Purpose |
|----------|------|------|----------|--------|---------|
| `mosquitto/certs/` | `hospital_ca.crt` | CA | 2048 bit | ✅ ACTIVE | Mosquitto CA (mTLS verification) |
| `mosquitto/certs/` | `hospital_ca.key` | CA Key | 2048 bit | ✅ ACTIVE | CA private key (for signing) |
| `mosquitto/certs/` | `server.crt` | Server | 2048 bit | ✅ ACTIVE | Mosquitto server certificate |
| `mosquitto/certs/` | `server.key` | Server Key | 2048 bit | ✅ ACTIVE | Mosquitto server private key |
| `mosquitto/certs/` | `backend.crt` | Client | 2048 bit | ✅ ACTIVE | Backend client certificate |
| `mosquitto/certs/` | `backend.key` | Client Key | 2048 bit | ✅ ACTIVE | Backend client private key |
| `esp32_hospital_watch_complete/data/` | `ca.crt` | CA | 2048 bit | ✅ ACTIVE | ESP32 CA certificate (for SPIFFS) |

### ❌ Unused/Old Certificates (RSA-4096, Oct 16, 2025)

| Location | File | Type | Key Size | Status | Issue |
|----------|------|------|----------|--------|-------|
| `mosquitto/certs/` | `ca.crt` | CA | 4096 bit | ❌ UNUSED | Old RSA-4096 CA, replaced by `hospital_ca.crt` |
| `mosquitto/certs/` | `ca.key` | CA Key | 4096 bit | ❌ UNUSED | Old RSA-4096 CA key |

---

## Certificate Verification

### 1. ESP32 CA Certificate
```
File: esp32_hospital_watch_complete/data/ca.crt
Public-Key: (2048 bit)
Not Before: Oct 19 04:00:22 2025 GMT
Not After : Oct 17 04:00:22 2035 GMT
Status: ✅ RSA-2048, matches hospital_ca.crt
```

### 2. Mosquitto Hospital CA
```
File: mosquitto/certs/hospital_ca.crt
Public-Key: (2048 bit)
Not Before: Oct 19 04:00:22 2025 GMT
Not After : Oct 17 04:00:22 2035 GMT
Status: ✅ RSA-2048, ACTIVE (used by Mosquitto)
```

### 3. Mosquitto Old CA (UNUSED)
```
File: mosquitto/certs/ca.crt
Public-Key: (4096 bit)
Not Before: Oct 16 10:30:21 2025 GMT
Not After : Oct 14 10:30:21 2035 GMT
Status: ❌ RSA-4096, NOT used by Mosquitto config
```

### 4. Server Certificate
```
File: mosquitto/certs/server.crt
Public-Key: (2048 bit)
Not Before: Oct 19 04:00:22 2025 GMT
Not After : Oct 17 04:00:22 2035 GMT
Issuer: Hospital CA (RSA-2048)
Status: ✅ RSA-2048, signed by correct CA
```

### 5. Backend Client Certificate
```
File: mosquitto/certs/backend.crt
Public-Key: (2048 bit)
Not Before: Oct 19 04:00:22 2025 GMT
Not After : Oct 17 04:00:22 2035 GMT
Issuer: Hospital CA (RSA-2048)
Status: ✅ RSA-2048, signed by correct CA
```

---

## Mosquitto Configuration Verification

**File:** `mosquitto/config/mosquitto.conf`

```conf
# Hospital CA certificate (to verify client certificates)
cafile /mosquitto/certs/hospital_ca.crt  ✅ CORRECT (RSA-2048)

# Server certificate and key (for TLS encryption)
certfile /mosquitto/certs/server.crt    ✅ CORRECT (RSA-2048)
keyfile /mosquitto/certs/server.key     ✅ CORRECT (RSA-2048)
```

**Result:** Mosquitto is using the CORRECT RSA-2048 certificates.

---

## Backend Configuration Verification

**File:** `hospital-backend/app/services/mqtt_service.py`

```python
# Line 44-46
ca_cert_path = os.path.join(base_path, "..", "..", "..", "mosquitto", "certs", "hospital_ca.crt")
client_cert_path = os.path.join(base_path, "..", "..", "..", "mosquitto", "certs", "backend.crt")
client_key_path = os.path.join(base_path, "..", "..", "..", "mosquitto", "certs", "backend.key")
```

**Result:** Backend is using the CORRECT RSA-2048 certificates.

---

## ESP32 Certificate Source

**File:** `hospital-backend/app/services/certificate_service.py`

```python
# Lines 21-24
hospital_ca_cert_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "mosquitto", "certs", "hospital_ca.crt")
hospital_ca_key_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "mosquitto", "certs", "hospital_ca.key")
```

**Device certificates signed by:** `hospital_ca.crt` (RSA-2048) ✅

**ESP32 SPIFFS CA:** `esp32_hospital_watch_complete/data/ca.crt` matches `hospital_ca.crt` ✅

---

## Certificate Chain Validation

### Backend → Mosquitto

```
Backend Client Cert (backend.crt, RSA-2048)
    ↓ Signed by
Hospital CA (hospital_ca.crt, RSA-2048)
    ↓ Trusted by
Mosquitto (cafile = hospital_ca.crt)
```

**Status:** ✅ Valid chain

### ESP32 → Mosquitto

```
ESP32 Device Cert (generated dynamically, RSA-2048)
    ↓ Signed by
Hospital CA (hospital_ca.crt, RSA-2048)
    ↓ Trusted by
Mosquitto (cafile = hospital_ca.crt)

ESP32 validates server:
Server Cert (server.crt, RSA-2048)
    ↓ Signed by
Hospital CA (hospital_ca.crt, RSA-2048)
    ↓ Trusted by
ESP32 (ca.crt = hospital_ca.crt)
```

**Status:** ✅ Valid chain (assuming ESP32 SPIFFS uploaded)

---

## Issues Found

### 1. Unused Old CA Certificate

**File:** `mosquitto/certs/ca.crt` (RSA-4096, Oct 16)

**Issue:** This is the OLD certificate that was replaced during the RSA-2048 migration. It's not referenced anywhere but causes confusion.

**Impact:**
- ❌ Takes up disk space
- ❌ Confusing during troubleshooting
- ❌ Could be accidentally used if someone changes config

**Recommendation:** Delete `mosquitto/certs/ca.crt` and `mosquitto/certs/ca.key`

### 2. Old Hospital CA Backup Files

**Location:** `mosquitto/certs/`

**Files:**
- `hospital_ca.crt.backup-oct18` (RSA-4096)
- `hospital_ca.key.backup-oct18` (RSA-4096)
- `server.crt.backup-oct18` (RSA-4096)
- `server.csr.backup-oct18` (RSA-4096)
- `server.key.backup-oct18` (RSA-4096)

**Status:** These are intentional backups and should be kept for rollback purposes.

**Recommendation:** Keep in `mosquitto/certs/` or move to `mosquitto/certs/backups/` folder.

---

## Summary

### ✅ What's Working

1. **All active certificates are RSA-2048** (ESP32-compatible)
2. **Mosquitto using correct certificates** (hospital_ca.crt, server.crt)
3. **Backend using correct certificates** (hospital_ca.crt, backend.crt)
4. **ESP32 CA matches Hospital CA** (verified identical)
5. **All certificates have valid dates** (2025-2035)
6. **Certificate chains are valid** (all signed by same CA)

### 🔧 Cleanup Needed

1. **Delete:** `mosquitto/certs/ca.crt` (old RSA-4096 CA)
2. **Delete:** `mosquitto/certs/ca.key` (old RSA-4096 CA key)
3. **Optional:** Move backup files to dedicated backup folder

---

## Recommended Actions

### Action 1: Delete Unused Old CA

```bash
rm mosquitto/certs/ca.crt
rm mosquitto/certs/ca.key
```

**Why:** These RSA-4096 files are not used and cause confusion.

### Action 2: Verify ESP32 Connection

Once firmware is uploaded:
1. ESP32 should connect successfully
2. Mosquitto logs should show: `New client connected ... as HospitalWatch_ESP32-WATCH-xxx`
3. Check cipher used: `docker logs hospital_mosquitto | grep cipher`

### Action 3: Document Certificate Locations (For Future Reference)

**Active Certificates:**
- **Mosquitto:** `mosquitto/certs/hospital_ca.crt` (CA), `server.crt` (server), `backend.crt` (backend client)
- **ESP32 SPIFFS:** `esp32_hospital_watch_complete/data/ca.crt` (CA only)
- **Backend Python:** Points to `mosquitto/certs/` (no local copies)

**Certificate Generation:**
- Script: `hospital-backend/generate_all_certificates.py`
- Generates: Hospital CA, server cert, backend cert
- ESP32 device certs: Generated on-demand via `/api/v1/provisioning/provision-with-certificate`

---

## Certificate Renewal Plan (When Certificates Expire in 2035)

1. Run `hospital-backend/generate_all_certificates.py` to generate new RSA-2048 certificates
2. Restart Mosquitto: `docker-compose restart mosquitto`
3. Restart backend: Backend will reconnect automatically
4. Re-provision all ESP32 devices (new device certificates needed)
5. Update ESP32 SPIFFS with new CA certificate

**Note:** Device certificates are NOT automatically renewed. Each device must be re-provisioned when CA expires.

---

## Certificate Security Notes

### Current Security Posture

✅ **Strong:**
- RSA-2048 keys (industry standard for IoT)
- mTLS authentication (mutual certificate verification)
- No shared passwords
- Certificate-based device identity
- Topic-level ACLs based on device identity

✅ **Compliant:**
- Indian DPDP Act 2023 (strong encryption)
- HIPAA reference (encryption in transit)
- Clinical Establishments Act (data confidentiality)

### Potential Improvements (Future)

1. **Certificate Revocation:** Implement OCSP or CRL distribution
2. **Automatic Renewal:** Add Let's Encrypt-style auto-renewal for server cert
3. **Hardware Security:** Store CA private key in HSM or encrypted vault
4. **Monitoring:** Alert when certificates are close to expiration
5. **Audit Logging:** Log all certificate issuance and revocation events

---

## Conclusion

**Overall Status:** ✅ Certificates are in sync and correctly configured

**Cleanup Required:** Delete `mosquitto/certs/ca.crt` and `ca.key` (old RSA-4096 files)

**Ready for Testing:** ESP32 should connect successfully once firmware is uploaded

**Next Step:** Upload fixed ESP32 firmware and test MQTT connection
