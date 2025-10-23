# mTLS Certificate Chain Verification Script - Complete

**Date:** 2025-10-19
**Script:** `verify-mtls-chain.sh`
**Status:** ✅ Created and tested successfully

---

## What Was Created

### File: `verify-mtls-chain.sh`

A comprehensive bash script that verifies the entire mTLS certificate chain for your Hospital Management System.

**Location:** Root of project directory

**Usage:**
```bash
bash verify-mtls-chain.sh
```

**Exit Codes:**
- `0` = All checks passed
- `1` = One or more failures detected

---

## What the Script Checks

### Check 1: File Existence ✅
Verifies all required certificate and key files exist:
- `mosquitto/certs/hospital_ca.crt` + `.key`
- `mosquitto/certs/server.crt` + `.key`
- `mosquitto/certs/backend.crt` + `.key`
- `esp32_hospital_watch_complete/data/ca.crt`
- `hospital-backend/ssl/cert.pem` + `key.pem`

**Why:** Catches missing files before attempting verification

### Check 2: CA Fingerprint Comparison ✅
Compares SHA256 fingerprints of:
- `mosquitto/certs/hospital_ca.crt`
- `esp32_hospital_watch_complete/data/ca.crt`

**Current Result:**
```
Mosquitto CA: 7A:49:15:A7:49:4E:26:22:1F:C8:E9:B6:F4:50:27:75:12:14:F3:04:20:61:D3:8B:E7:71:49:1E:E8:EF:A2:BC
ESP32 CA:     7A:49:15:A7:49:4E:26:22:1F:C8:E9:B6:F4:50:27:75:12:14:F3:04:20:61:D3:8B:E7:71:49:1E:E8:EF:A2:BC
[OK] CA fingerprints match
```

**Why:** Most critical check - if CAs don't match, ESP32 will reject Mosquitto's server certificate

### Check 3: Certificate Chain Validation ✅
Uses `openssl verify` to confirm:
- `server.crt` is signed by `hospital_ca.crt`
- `backend.crt` is signed by `hospital_ca.crt`

**Current Result:**
```
[OK] server.crt signed by Hospital CA
[OK] backend.crt signed by Hospital CA
```

**Why:** Ensures all certificates were issued by the same trusted CA

### Check 4: Key-Certificate Modulus Matching ✅
Compares MD5 hashes of modulus values to verify:
- `server.crt` matches `server.key`
- `backend.crt` matches `backend.key`
- `hospital_ca.crt` matches `hospital_ca.key`

**Current Result:**
```
[OK] server.crt ↔ server.key modulus match
[OK] backend.crt ↔ backend.key modulus match
[OK] hospital_ca.crt ↔ hospital_ca.key modulus match
```

**Why:** Catches accidental key/cert pair mismatches (e.g., using old key with new cert)

### Check 5: Certificate Details Display ✅
Shows for each certificate:
- **Subject CN:** Device/server identity
- **Issuer:** Who signed the certificate
- **Not Before/After:** Validity period
- **Key Size:** Bit strength (should be 2048)
- **Expiration Status:** Valid or expired

**Example Output:**
```
Certificate: Mosquitto Server Certificate
────────────────────────────────────────────────────
Subject:    C=IN, ST=Telangana, L=Hyderabad, O=Symbiot, OU=SymHMS Development, CN=localhost
Issuer:     C=IN, ST=Telangana, L=Hyderabad, O=Symbiot, OU=SymHMS Development, CN=Symbiot Hospital CA
Not Before: Oct 19 04:00:22 2025 GMT
Not After:  Oct 17 04:00:22 2035 GMT
Key Size:   2048 bit
Status:     Valid (not expired)
```

**Why:** Human-readable verification of certificate contents

---

## Current Test Results

**Date Tested:** 2025-10-19

```
======================================================
  VERIFICATION SUMMARY
======================================================

✅ ALL CHECKS PASSED

Certificate chain is valid and ready for mTLS:
  • All certificate files exist
  • CA certificates match (Mosquitto ↔ ESP32)
  • Server and backend certs signed by Hospital CA
  • All private keys match their certificates
  • All certificates are valid (not expired)

ESP32 should be able to connect to Mosquitto.
======================================================
```

**Exit Code:** 0 (success)

---

## When to Use This Script

### 1. Before Flashing ESP32 Firmware
```bash
bash verify-mtls-chain.sh
```
Ensures certificates are in sync before deploying to devices.

### 2. After Re-generating Certificates
```bash
python hospital-backend/generate_all_certificates.py
bash verify-mtls-chain.sh
```
Verifies new certificates were created correctly.

### 3. Debugging mTLS Connection Failures
```bash
bash verify-mtls-chain.sh
```
Identifies exactly which part of the certificate chain is broken.

### 4. In CI/CD Pipeline
```bash
#!/bin/bash
bash verify-mtls-chain.sh || exit 1
docker-compose up -d
```
Prevents deployment if certificates are invalid.

---

## What Problems This Solves

### ❌ Before (Manual Debugging)
```bash
# Developer has to run 20+ openssl commands manually:
openssl x509 -in mosquitto/certs/hospital_ca.crt -noout -fingerprint -sha256
openssl x509 -in esp32_hospital_watch_complete/data/ca.crt -noout -fingerprint -sha256
# ... compare manually ...

openssl verify -CAfile mosquitto/certs/hospital_ca.crt mosquitto/certs/server.crt
# ... check output ...

openssl x509 -noout -modulus -in mosquitto/certs/server.crt | openssl md5
openssl rsa -noout -modulus -in mosquitto/certs/server.key | openssl md5
# ... compare manually ...

# Takes 15-20 minutes, error-prone, easy to miss issues
```

### ✅ After (One Command)
```bash
bash verify-mtls-chain.sh

# Takes 2 seconds
# Color-coded output
# Clear pass/fail results
# Exit code for automation
```

---

## Common Issues Detected

### Issue 1: CA Mismatch
```
[FAIL] CA fingerprints DO NOT match!
WARNING: ESP32 will reject Mosquitto server certificate!
```

**Fix:**
```bash
cp mosquitto/certs/hospital_ca.crt esp32_hospital_watch_complete/data/ca.crt
```

### Issue 2: Invalid Certificate Chain
```
[FAIL] server.crt NOT signed by Hospital CA
```

**Fix:**
```bash
cd hospital-backend
python generate_all_certificates.py
```

### Issue 3: Key-Certificate Mismatch
```
[FAIL] server.crt ↔ server.key modulus MISMATCH (wrong key?)
```

**Fix:** Ensure cert and key are from the same generation (don't mix old keys with new certs)

### Issue 4: Expired Certificate
```
Status: EXPIRED
```

**Fix:**
```bash
cd hospital-backend
python generate_all_certificates.py
docker-compose restart mosquitto
```

---

## Script Features

### ✅ Color-Coded Output
- 🟢 Green `[OK]` = Check passed
- 🔴 Red `[FAIL]` = Check failed
- 🟡 Yellow `[WARNING]` = Potential issue
- 🔵 Blue `[CHECK N]` = Section headers

### ✅ Automation-Ready
- Exit code 0 = success
- Exit code 1 = failure
- Works in CI/CD pipelines

### ✅ Comprehensive Diagnostics
- Tests all certificate files
- Verifies entire trust chain
- Checks key-cert pairing
- Shows expiration status

### ✅ Production-Safe
- Read-only operations
- No file modifications
- No side effects
- Safe to run anytime

---

## Technical Details

### OpenSSL Commands Used

**Fingerprint Extraction:**
```bash
openssl x509 -in <cert> -noout -fingerprint -sha256
```

**Chain Verification:**
```bash
openssl verify -CAfile <ca_cert> <cert_to_verify>
```

**Modulus Extraction (Certificate):**
```bash
openssl x509 -noout -modulus -in <cert> | openssl md5
```

**Modulus Extraction (Key):**
```bash
openssl rsa -noout -modulus -in <key> | openssl md5
```

**Certificate Details:**
```bash
openssl x509 -in <cert> -noout -subject -issuer -dates -text
```

**Expiration Check:**
```bash
openssl x509 -in <cert> -noout -checkend 0
```

### Requirements
- **Bash:** Git Bash on Windows, or any Unix shell
- **OpenSSL:** Version 3.x (tested with 3.2.4)
- **No other dependencies**

---

## Verification Workflow

```
START
  ↓
[1] Check all certificate files exist
  ↓ (if any missing → EXIT 1)
[2] Compare CA fingerprints (Mosquitto ↔ ESP32)
  ↓ (if mismatch → mark FAIL, continue)
[3] Verify server.crt and backend.crt signed by CA
  ↓ (if invalid → mark FAIL, continue)
[4] Verify cert-key modulus matching
  ↓ (if mismatch → mark FAIL, continue)
[5] Display certificate details
  ↓
SUMMARY
  ↓
EXIT (0 if all OK, 1 if any FAIL)
```

---

## Integration Examples

### Pre-Deployment Check
```bash
#!/bin/bash
echo "Verifying certificates before deployment..."
bash verify-mtls-chain.sh || {
    echo "Certificate verification failed! Fix issues before deploying."
    exit 1
}

echo "Certificates OK. Deploying..."
docker-compose up -d
```

### CI/CD Pipeline (GitHub Actions)
```yaml
- name: Verify mTLS Certificates
  run: bash verify-mtls-chain.sh

- name: Start Services
  if: success()
  run: docker-compose up -d
```

### ESP32 Flash Script
```bash
#!/bin/bash
echo "Step 1: Verify certificates..."
bash verify-mtls-chain.sh || exit 1

echo "Step 2: Upload firmware to ESP32..."
platformio run --target upload
```

---

## Maintenance

### When Certificates Are Regenerated
1. Run the script to verify new certificates
2. Check that all dates updated
3. Verify CA fingerprints still match
4. Confirm all chains valid

### Before Certificate Expiration (2035)
1. Generate new certificates
2. Run script to verify
3. Re-provision all ESP32 devices
4. Update ESP32 SPIFFS with new CA

---

## Summary

**Created:** `verify-mtls-chain.sh` (273 lines)

**Verified:**
- ✅ All certificate files exist
- ✅ CA fingerprints match (Mosquitto ↔ ESP32)
- ✅ Certificate chains valid (all signed by Hospital CA)
- ✅ All key-cert pairs match
- ✅ All certificates valid until 2035

**Result:** Certificate infrastructure is correctly configured and ready for ESP32 mTLS connections.

**Next Steps:**
1. Use this script before every ESP32 firmware flash
2. Add to pre-deployment checklist
3. Run after any certificate regeneration
4. Bookmark for troubleshooting mTLS issues

---

**Script is production-ready and tested.** ✅
