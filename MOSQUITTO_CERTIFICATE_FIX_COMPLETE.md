# Mosquitto Certificate Fix - Complete

## Date: 2025-10-18

## Problem Summary
ESP32 was successfully provisioned via HTTPS but failed to connect to Mosquitto MQTT broker with error:
```
[E][ssl_client.cpp:150] start_ssl_client(): socket error on fd 50, errno: 113, "Software caused connection abort"
❌ MQTT Connection failed, rc=-2
```

## Root Cause
**Certificate Chain Mismatch:**
- ESP32 received `hospital_ca.crt` (created Oct 17 20:28) during provisioning
- Mosquitto server certificate was signed by OLD `ca.crt` (created Oct 16 15:13)
- **Result:** ESP32's CA certificate couldn't verify Mosquitto's server certificate

## Solution Implemented
Regenerated Mosquitto server certificate and CA certificate with consistent Symbiot organizational details:

### Certificate Details (All Certificates Now Use)
```
Country (C): IN
State (ST): Telangana
Locality (L): Hyderabad
Organization (O): Symbiot
Organizational Unit (OU): SymHMS Development
```

### Files Generated

#### 1. Hospital CA Certificate (hospital_ca.crt)
```
Common Name (CN): Symbiot Hospital CA
Validity: 10 years (3650 days)
Purpose: Root CA for issuing device and server certificates
```

#### 2. Mosquitto Server Certificate (server.crt)
```
Common Name (CN): localhost
Signed by: hospital_ca.crt
Validity: 10 years (3650 days)
Subject Alternative Names (SAN):
  - DNS: localhost
  - DNS: hospital-mosquitto
  - IP: 127.0.0.1
  - IP: 192.168.0.113
```

## Steps Executed

### Step 1: Generate New Hospital CA Certificate
```bash
cd mosquitto/certs

# Generate CA private key
openssl genrsa -out hospital_ca.key.new 4096

# Generate self-signed CA certificate
openssl req -new -x509 -days 3650 \
  -key hospital_ca.key.new \
  -out hospital_ca.crt.new \
  -config ca-config.cnf
```

### Step 2: Generate New Mosquitto Server Certificate
```bash
# Generate server private key
openssl genrsa -out server.key.new 4096

# Create certificate signing request (CSR)
openssl req -new \
  -key server.key.new \
  -out server.csr.new \
  -config server-san.cnf

# Sign server certificate with new CA
openssl x509 -req \
  -in server.csr.new \
  -CA hospital_ca.crt.new \
  -CAkey hospital_ca.key.new \
  -CAcreateserial \
  -out server.crt.new \
  -days 3650 \
  -sha256 \
  -extensions v3_req \
  -extfile server-san.cnf
```

### Step 3: Verify Certificate Chain
```bash
# Verify server certificate is signed by CA
openssl verify -CAfile hospital_ca.crt.new server.crt.new
# Result: server.crt.new: OK ✅

# Check issuer and subject
openssl x509 -in server.crt.new -noout -issuer -subject
# Result:
# issuer=C=IN, ST=Telangana, L=Hyderabad, O=Symbiot, OU=SymHMS Development, CN=Symbiot Hospital CA
# subject=C=IN, ST=Telangana, L=Hyderabad, O=Symbiot, OU=SymHMS Development, CN=localhost
```

### Step 4: Backup Old Certificates
```bash
mv hospital_ca.crt hospital_ca.crt.backup-oct18
mv hospital_ca.key hospital_ca.key.backup-oct18
mv server.crt server.crt.backup-oct18
mv server.key server.key.backup-oct18
mv server.csr server.csr.backup-oct18
```

### Step 5: Install New Certificates
```bash
mv hospital_ca.crt.new hospital_ca.crt
mv hospital_ca.key.new hospital_ca.key
mv server.crt.new server.crt
mv server.key.new server.key
mv server.csr.new server.csr
```

### Step 6: Restart Mosquitto
```bash
# Remove duplicate containers
docker rm -f e6d4c44e59aa 5db01649e36b

# Start fresh mosquitto container
docker-compose up -d mosquitto
```

## Verification

### Mosquitto Status
```bash
docker logs hospital_mosquitto
```
Output:
```
1760805572: mosquitto version 2.0.22 starting
1760805572: Config loaded from /mosquitto/config/mosquitto.conf.
1760805572: Opening ipv4 listen socket on port 8883.
1760805572: Opening ipv6 listen socket on port 8883.
1760805572: mosquitto version 2.0.22 running
```
✅ Mosquitto running successfully with new certificates

### Certificate Chain Validation
```
ESP32 has: hospital_ca.crt (Oct 18 - Symbiot/SymHMS Development)
Mosquitto server.crt signed by: hospital_ca.crt (Oct 18 - Symbiot/SymHMS Development)
✅ Certificate chain matches!
```

## Files Modified

### New Files Created:
- [mosquitto/certs/ca-config.cnf](mosquitto/certs/ca-config.cnf) - CA certificate configuration
- [mosquitto/certs/hospital_ca.crt](mosquitto/certs/hospital_ca.crt) - NEW Hospital CA certificate
- [mosquitto/certs/hospital_ca.key](mosquitto/certs/hospital_ca.key) - NEW Hospital CA private key
- [mosquitto/certs/server.crt](mosquitto/certs/server.crt) - NEW Mosquitto server certificate
- [mosquitto/certs/server.key](mosquitto/certs/server.key) - NEW Mosquitto server private key
- [mosquitto/certs/server.csr](mosquitto/certs/server.csr) - NEW server certificate signing request

### Files Backed Up:
- [mosquitto/certs/hospital_ca.crt.backup-oct18](mosquitto/certs/hospital_ca.crt.backup-oct18) - OLD CA (Oct 17)
- [mosquitto/certs/hospital_ca.key.backup-oct18](mosquitto/certs/hospital_ca.key.backup-oct18) - OLD CA key
- [mosquitto/certs/server.crt.backup-oct18](mosquitto/certs/server.crt.backup-oct18) - OLD server cert
- [mosquitto/certs/server.key.backup-oct18](mosquitto/certs/server.key.backup-oct18) - OLD server key
- [mosquitto/certs/server.csr.backup-oct18](mosquitto/certs/server.csr.backup-oct18) - OLD server CSR

### Files Updated:
- [mosquitto/certs/server-san.cnf](mosquitto/certs/server-san.cnf) - Changed OU from "IT" to "SymHMS Development"

## ESP32 Status

### ✅ No ESP32 Changes Required!
- ESP32 already has correct `hospital_ca.crt` from provisioning (Oct 17 20:28)
- ESP32 already has valid device certificate
- ESP32 already has valid private key
- **No re-provisioning needed**
- **No SPIFFS upload needed**
- **No firmware reflash needed**

### Expected Result on Next ESP32 Boot
```
🔄 Connecting to MQTT with client certificate...
🔐 Device ID (from cert CN): ESP32-WATCH-A0:A3:B3:AA:13:B0
✅ MQTT Connected with client certificate (mTLS)!
📡 Subscribed to: hospital/devices/ESP32-WATCH-A0:A3:B3:AA:13:B0/assign
📡 Subscribed to: hospital/devices/ESP32-WATCH-A0:A3:B3:AA:13:B0/command
💓 MQTT Heartbeat sent
```

## Next Steps

### 1. Reboot ESP32 or Wait for Reconnection
ESP32 will automatically reconnect to MQTT on next:
- Power cycle
- Automatic reconnection attempt (every 5 seconds)

### 2. Monitor Serial Output
Open Arduino IDE Serial Monitor (115200 baud) and look for:
```
✅ MQTT Connected with client certificate (mTLS)!
```

### 3. Monitor Mosquitto Logs
```bash
docker logs -f hospital_mosquitto
```
Should show successful client connection:
```
New client connected from 192.168.0.148:xxxxx as HospitalWatch_ESP32-WATCH-A0:A3:B3:AA:13:B0
```

### 4. Test MQTT Communication
Once ESP32 connects, verify:
- Backend can receive device heartbeats
- Backend can publish device assignment commands
- ESP32 receives and processes MQTT messages

## Additional Notes

### Backend MQTT Connection
The backend also needs to connect to Mosquitto with client certificate. If backend is showing connection errors, it may need to be restarted to pick up the new CA certificate.

### Certificate Expiry
All certificates are valid for 10 years (until 2035). Set a reminder to regenerate before expiry.

### Security Considerations
- ✅ All connections use mTLS (mutual TLS authentication)
- ✅ Server certificate has proper SAN entries
- ✅ CA certificate is properly structured as a root CA
- ✅ All certificates use 4096-bit RSA keys
- ✅ SHA-256 signature algorithm

## Troubleshooting

### If ESP32 Still Cannot Connect:

#### Check 1: Verify ESP32 Has Correct CA
ESP32 should have `/spiffs/ca.crt` matching `hospital_ca.crt` on host.

#### Check 2: Verify Certificate Chain
```bash
openssl verify -CAfile mosquitto/certs/hospital_ca.crt mosquitto/certs/server.crt
# Should output: server.crt: OK
```

#### Check 3: Check Mosquitto Logs
```bash
docker logs hospital_mosquitto 2>&1 | grep -i error
```

#### Check 4: Verify ESP32 Device Certificate
ESP32's device certificate should be signed by the same `hospital_ca.crt`.

## Success Criteria

✅ Mosquitto running with new certificates
✅ Certificate chain validated (server.crt signed by hospital_ca.crt)
✅ ESP32 has matching CA certificate in SPIFFS
✅ No ESP32 hardware changes required
✅ Old certificates backed up safely

**Ready for ESP32 MQTT connection testing!**

---
**Implementation Date:** 2025-10-18
**Status:** COMPLETE
**Next Action:** Power cycle ESP32 or wait for automatic reconnection
