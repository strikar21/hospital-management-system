# Complete Mosquitto & ESP32 mTLS Configuration Info

**Date**: October 20, 2025
**For**: Debugging with other AI tools

---

## Mosquitto Configuration

### Version & Image
- **Docker Image**: `eclipse-mosquitto:1.6`
- **Mosquitto Version**: `1.6.15`
- **Container Name**: `hospital_mosquitto`
- **Port**: `8883` (TLS MQTT only)

### TLS Configuration
**File**: `mosquitto/config/mosquitto.conf`

```conf
# TLS Listener
listener 8883
protocol mqtt

# Certificates
cafile /mosquitto/certs/hospital_ca.crt          # Hospital CA to verify client certs
certfile /mosquitto/certs/server.crt             # Mosquitto server certificate
keyfile /mosquitto/certs/server.key              # Mosquitto server private key

# Client Certificate Requirement
require_certificate true                          # ✅ ENABLED - Requires client certificates
use_identity_as_username true                     # ✅ ENABLED - Extracts username from cert CN

# TLS Version
tls_version tlsv1.2                               # Force TLS 1.2 only (ESP32 compatible)

# Authentication
allow_anonymous false                             # ✅ DISABLED - No anonymous connections

# ACL
acl_file /mosquitto/config/acl.conf               # Topic permissions
```

### Current Error in Logs
```
OpenSSL Error[0]: error:140360B2:SSL routines:ACCEPT_SR_CERT:no certificate returned
Socket error on client <unknown>, disconnecting.
```

**This means**: Mosquitto is NOT receiving any client certificate during TLS handshake.

---

## ESP32 Configuration

### Hardware & Software
- **Board**: Node32s (ESP32)
- **Arduino ESP32 Core**: `3.2.0`
- **ESP-IDF**: `v5.4.1-1-g2f7dcd862a-dirty`
- **TLS Library**: NetworkClientSecure (wrapper around mbedTLS)
- **MQTT Library**: PubSubClient 2.8

### Current Firmware Version
- **Version**: `5.0.2` (certificate-based auth)
- **File**: `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`

### Certificate Loading Method (CURRENT)
```cpp
// Global String variables (lines 46-48)
String caCertificate = "";      // Loaded from SPIFFS /ca.crt
String deviceCertificate = "";  // Loaded from SPIFFS /device.crt
String devicePrivateKey = "";   // Loaded from SPIFFS /device.key

// In setupMQTT() function (lines 1016-1018)
wifiClient.setCACert(caCertificate.c_str());
wifiClient.setCertificate(deviceCertificate.c_str());
wifiClient.setPrivateKey(devicePrivateKey.c_str());
```

### TLS Connection Flow
1. **WiFi connects** → IP: 192.168.0.148
2. **NTP sync** → Gets current time (required for cert validation)
3. **Load certs from SPIFFS** → Into global String variables
4. **setupMQTT()** → Calls `setCertificate()` with `.c_str()`
5. **connectToMQTT()** → Calls `mqttClient.connect(clientId)`
6. **PubSubClient → NetworkClientSecure → mbedTLS** → TLS handshake
7. **ERROR -30592**: "SSL - A fatal alert message was received from our peer"

### Verbose Logs Show
```
[  7073][V][ssl_client.cpp:269] start_ssl_client(): Loading CRT cert
[  7084][V][ssl_client.cpp:278] start_ssl_client(): Loading private key
[  7879][E][ssl_client.cpp:36] _handle_error(): (-30592) SSL - A fatal alert message was received from our peer
```

**This means**: mbedTLS IS loading the certificate into memory, but NOT sending it during TLS handshake.

---

## Certificate Details

### Certificate Files Location
```
mosquitto/certs/
├── hospital_ca.crt       # CA certificate (1436 bytes)
├── hospital_ca.key       # CA private key
├── server.crt            # Mosquitto server cert (2164 bytes)
├── server.key            # Mosquitto server key (3324 bytes)
└── backend.crt/.key      # Backend client cert (for backend → Mosquitto)

hospital-backend/ssl/devices/
└── ESP32-WATCH-{MAC}/
    ├── device.crt        # Device client cert (1619 bytes)
    └── device.key        # Device private key (1704 bytes)
```

### Certificate Chain
```
Hospital CA (self-signed)
├── server.crt (CN=localhost, SAN: 192.168.0.113, localhost)
├── backend.crt (CN=hospitalBackend)
└── device.crt (CN=ESP32-WATCH-A0:A3:B3:AA:13:B0)
```

### Device Certificate Info
- **Common Name (CN)**: `ESP32-WATCH-A0:A3:B3:AA:13:B0` (MAC address)
- **Organization**: Symbiot
- **Validity**: Valid until 2026
- **Key Type**: RSA-2048
- **Signature**: SHA256withRSA
- **Verified**: ✅ `openssl verify -CAfile hospital_ca.crt device.crt` → OK

### ESP32 Certificate Storage
- **Filesystem**: SPIFFS (128KB partition)
- **Files**:
  - `/ca.crt` - Hospital CA certificate (1436 bytes)
  - `/device.crt` - Device client certificate (1619 bytes)
  - `/device.key` - Device private key (1704 bytes)

---

## What Works ✅

1. **Python client with mTLS** → Connects successfully to Mosquitto
   ```python
   context.load_cert_chain("device.crt", "device.key")
   context.load_verify_locations("hospital_ca.crt")
   ```

2. **ESP32 with setInsecure()** → Connects when Mosquitto has `require_certificate false`

3. **ESP32 server validation** → Successfully validates Mosquitto's server certificate

4. **Certificate validity** → All certificates verified with openssl

5. **Network connectivity** → Windows Firewall configured, port 8883 accessible

---

## What Doesn't Work ❌

1. **ESP32 mTLS authentication** → Error -30592, Mosquitto says "no certificate returned"

2. **Both certificate methods fail**:
   - `setCertificate()` with String.c_str() → No cert sent
   - `loadCertificate()` with file streams → No cert sent + heap corruption

---

## The Bug

### Root Cause
NetworkClientSecure in Arduino ESP32 Core 3.2.0 has a bug where:
- Client certificates ARE loaded into mbedTLS structures (verbose logs confirm)
- But certificates are NOT transmitted during TLS handshake (Mosquitto never receives them)

### Evidence
1. **mbedTLS verbose logs** show certificate loading at ssl_client.cpp:269 and :278
2. **Mosquitto logs** show "no certificate returned" during SSL_accept()
3. **Python client works** with same certificates → proves Mosquitto config is correct
4. **ESP32 validates server cert** → proves TLS connection works
5. **Only client cert transmission fails** → library-specific bug

### Possible Library Issues
- `mbedtls_ssl_conf_own_cert()` not called correctly
- TLS handshake not sending CertificateVerify message
- Client certificate list empty during SSL_write()
- Pointer invalidation between setCertificate() and actual TLS handshake

---

## Network Details

### ESP32
- **IP**: 192.168.0.148 (DHCP)
- **Gateway**: 192.168.0.1
- **WiFi SSID**: NETGEAR05
- **Signal**: -62 to -66 dBm

### Mosquitto Server
- **IP**: 192.168.0.113 (host machine)
- **Port**: 8883
- **Container IP**: 172.20.0.1 (Docker bridge network)

### Firewall
- **Windows Firewall Rule**: Added for port 8883 TCP inbound
- **Command**: `netsh advfirewall firewall add rule name="Mosquitto MQTT TLS" dir=in action=allow protocol=TCP localport=8883`

---

## Backend Working Connection

The backend successfully connects to Mosquitto with mTLS using Python:

```python
# hospital-backend/app/services/mqtt_service.py
client.tls_set(
    ca_certs="hospital-backend/ssl/mosquitto_ca.crt",
    certfile="hospital-backend/ssl/mqtt_client.crt",
    keyfile="hospital-backend/ssl/mqtt_client.key",
    tls_version=ssl.PROTOCOL_TLSv1_2
)
client.connect("localhost", 8883, 60)
```

**Status**: ✅ Backend connects successfully and receives data

---

## Code Files for Reference

### ESP32 Firmware
**File**: `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`
- **setupMQTT()**: Lines 984-1067 (certificate loading)
- **connectToMQTT()**: Lines 1069-1139 (connection attempt)
- **Certificate globals**: Lines 46-48

### Mosquitto Config
**File**: `mosquitto/config/mosquitto.conf` (164 lines)
**File**: `mosquitto/config/acl.conf` (topic permissions)

### Docker Compose
**File**: `docker-compose.yml`
- Mosquitto service: Lines 41-57

---

## Testing Commands

### Test Mosquitto from Windows
```bash
# Test with Python (WORKS ✅)
python test_mqtt_simple.py

# Test with openssl s_client
openssl s_client -connect 192.168.0.113:8883 -tls1_2 -showcerts \
  -CAfile mosquitto/certs/hospital_ca.crt \
  -cert hospital-backend/ssl/devices/ESP32-WATCH-A0_A3_B3_AA_13_B0/device.crt \
  -key hospital-backend/ssl/devices/ESP32-WATCH-A0_A3_B3_AA_13_B0/device.key
```

### Verify Certificates
```bash
# Verify device certificate
openssl verify -CAfile mosquitto/certs/hospital_ca.crt \
  hospital-backend/ssl/devices/ESP32-WATCH-A0_A3_B3_AA_13_B0/device.crt

# Check certificate details
openssl x509 -in device.crt -noout -text
```

### Docker Commands
```bash
# Check Mosquitto logs
docker logs hospital_mosquitto --tail 50

# Restart Mosquitto
docker restart hospital_mosquitto

# Check Mosquitto config
docker exec hospital_mosquitto cat /mosquitto/config/mosquitto.conf
```

---

## Summary for Other AI

**Problem**: ESP32 cannot send client certificate to Mosquitto during mTLS handshake.

**Evidence**:
- mbedTLS logs show cert is loaded
- Mosquitto says "no certificate returned"
- Python client works with same certs
- This is a NetworkClientSecure library bug

**Need**: Either fix NetworkClientSecure to properly send client certs, OR switch to alternative authentication method (username/password with TLS).

**Current workaround**: Revert code back to setCertificate() approach (already done), but connection still fails due to library bug.
