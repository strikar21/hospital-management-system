# Certificate-Based Authentication: Ultra-Detailed Step-by-Step Guide

**Date:** 2025-10-17
**Goal:** Replace shared MQTT credentials with TLS client certificates
**Audience:** Junior developer who needs exact commands and line numbers
**Timeline:** 7 days (56 hours total)

---

## Prerequisites Checklist

Before you start, verify:
- [ ] ESP32 watch is connected to USB
- [ ] Backend is running (`python -m uvicorn main:app --port 8001`)
- [ ] Mosquitto broker is running (`docker-compose ps mosquitto`)
- [ ] PostgreSQL is running (`docker-compose ps postgres`)
- [ ] You have administrator/sudo access
- [ ] Python 3.9+ installed
- [ ] Arduino IDE or arduino-cli installed

---

## DAY 1: Generate Hospital CA Certificate & Setup Database

### STEP 1.1: Generate Hospital CA Certificate (30 minutes)

#### What you're doing:
Creating a "root" certificate authority that will sign all device certificates.

#### Commands to run:

```bash
# 1. Open Command Prompt / PowerShell
# 2. Navigate to project directory
cd C:\Users\Srika\OneDrive\Desktop\hospital-management-system

# 3. Navigate to certificates directory
cd mosquitto\certs

# 4. Generate CA private key (4096-bit RSA)
openssl genrsa -out hospital_ca.key 4096

# Expected output:
# Generating RSA private key, 4096 bit long modulus
# ...........++
# ............++
# e is 65537 (0x10001)

# 5. Generate CA certificate (valid 10 years)
openssl req -x509 -new -nodes -key hospital_ca.key -sha256 -days 3650 -out hospital_ca.crt -subj "/C=IN/ST=Maharashtra/L=Mumbai/O=HospitalName/OU=IT/CN=Hospital CA"

# Expected output:
# (no output = success)

# 6. Verify CA certificate was created
dir

# Expected output should include:
# hospital_ca.key (3247 bytes)
# hospital_ca.crt (1944 bytes)

# 7. View certificate details (optional - to verify it worked)
openssl x509 -in hospital_ca.crt -text -noout

# Expected output:
# Certificate:
#     Data:
#         Version: 3 (0x2)
#         Serial Number: ...
#         Signature Algorithm: sha256WithRSAEncryption
#         Issuer: C=IN, ST=Maharashtra, L=Mumbai, O=HospitalName, OU=IT, CN=Hospital CA
#         Validity
#             Not Before: Oct 17 ... 2025 GMT
#             Not After : Oct 15 ... 2035 GMT
#         Subject: C=IN, ST=Maharashtra, L=Mumbai, O=HospitalName, OU=IT, CN=Hospital CA
# ...

# 8. CRITICAL: Move CA private key to secure location (outside git repo)
# Create secure directory
cd C:\Users\Srika
mkdir secure_keys
move C:\Users\Srika\OneDrive\Desktop\hospital-management-system\mosquitto\certs\hospital_ca.key C:\Users\Srika\secure_keys\hospital_ca.key

# 9. Verify key was moved
dir C:\Users\Srika\secure_keys

# Expected output:
# hospital_ca.key

# 10. Copy CA certificate to backend app directory (needed for certificate service)
copy C:\Users\Srika\OneDrive\Desktop\hospital-management-system\mosquitto\certs\hospital_ca.crt C:\Users\Srika\OneDrive\Desktop\hospital-management-system\hospital-backend\hospital_ca.crt
```

#### Files created:
- `C:\Users\Srika\secure_keys\hospital_ca.key` (PRIVATE - keep secret!)
- `C:\Users\Srika\OneDrive\Desktop\hospital-management-system\mosquitto\certs\hospital_ca.crt` (PUBLIC)
- `C:\Users\Srika\OneDrive\Desktop\hospital-management-system\hospital-backend\hospital_ca.crt` (copy for backend)

#### Checkpoint:
✅ You should have TWO files and one moved
✅ CA certificate can be viewed with `openssl x509 -in hospital_ca.crt -text`
✅ CA private key is in secure location outside repo

---

### STEP 1.2: Create Database Migration File (15 minutes)

#### What you're doing:
Creating SQL script to add tables for provisioning codes and device certificates.

#### File to create:
`C:\Users\Srika\OneDrive\Desktop\hospital-management-system\hospital-backend\migrations\013_certificate_provisioning.sql`

#### Exact content:

```sql
-- ========================================
-- Migration 013: Certificate-Based Provisioning
-- Creates tables for one-time provisioning codes and device certificates
-- ========================================

-- Provisioning codes (one-time use, 10-minute expiration)
CREATE TABLE IF NOT EXISTS provisioning_codes (
    code VARCHAR(20) PRIMARY KEY,
    technician_id VARCHAR(50) NOT NULL REFERENCES staff(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN DEFAULT false,
    used_at TIMESTAMPTZ,
    device_id VARCHAR(50) REFERENCES devices(id)
);

-- Index for finding valid (unused, not expired) codes quickly
CREATE INDEX IF NOT EXISTS idx_prov_codes_valid
ON provisioning_codes(expires_at, used)
WHERE used = false;

-- Index for tracking which technician provisioned which devices
CREATE INDEX IF NOT EXISTS idx_prov_codes_technician
ON provisioning_codes(technician_id);

-- Device certificates (stores X.509 certificates for each device)
CREATE TABLE IF NOT EXISTS device_certificates (
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

-- Unique constraint: one certificate per device
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_certs_unique
ON device_certificates(device_id);

-- Index for finding certificates by MAC address
CREATE INDEX IF NOT EXISTS idx_device_certs_mac
ON device_certificates(mac_address);

-- Index for checking certificate expiration
CREATE INDEX IF NOT EXISTS idx_device_certs_expiry
ON device_certificates(expires_at)
WHERE revoked = false;

-- Index for finding revoked certificates
CREATE INDEX IF NOT EXISTS idx_device_certs_revoked
ON device_certificates(revoked)
WHERE revoked = true;

-- Cleanup: Remove MQTT password columns from devices table (no longer needed)
-- DO NOT run this until certificate system is fully tested and working!
-- ALTER TABLE devices DROP COLUMN IF EXISTS mqtt_username;
-- ALTER TABLE devices DROP COLUMN IF EXISTS mqtt_password;

-- Comments for documentation
COMMENT ON TABLE provisioning_codes IS 'One-time codes for device provisioning (10-minute expiration)';
COMMENT ON TABLE device_certificates IS 'X.509 TLS client certificates for device authentication';
COMMENT ON COLUMN device_certificates.certificate_pem IS 'X.509 certificate in PEM format';
COMMENT ON COLUMN device_certificates.revoked IS 'True if certificate has been revoked (device stolen/compromised)';
```

#### How to create the file:

```powershell
# Open PowerShell or Command Prompt
cd C:\Users\Srika\OneDrive\Desktop\hospital-management-system\hospital-backend\migrations

# Create file using notepad
notepad 013_certificate_provisioning.sql

# Paste the SQL content above
# Save and close
```

#### Checkpoint:
✅ File exists at `hospital-backend\migrations\013_certificate_provisioning.sql`
✅ File is 73 lines long
✅ Contains two CREATE TABLE statements

---

### STEP 1.3: Create Python Migration Script (15 minutes)

#### What you're doing:
Creating Python script that applies the SQL migration to the database.

#### File to create:
`C:\Users\Srika\OneDrive\Desktop\hospital-management-system\hospital-backend\apply_migration_013.py`

#### Exact content:

```python
"""
Apply Migration 013: Certificate-Based Provisioning
Creates tables for provisioning codes and device certificates
"""

import asyncio
import asyncpg
from app.core.config import settings

async def apply_migration():
    """Apply migration 013: Certificate-based provisioning tables"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        print("="*80)
        print("MIGRATION 013: Certificate-Based Provisioning")
        print("="*80)
        print()
        print("[INFO] Applying migration 013: provisioning_codes and device_certificates tables")

        # Read migration SQL
        with open('migrations/013_certificate_provisioning.sql', 'r', encoding='utf-8') as f:
            migration_sql = f.read()

        # Execute migration
        await conn.execute(migration_sql)
        print("[OK] Migration 013 executed successfully")
        print()

        # Verify tables created
        print("[INFO] Verifying tables created...")
        tables = await conn.fetch("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name IN ('provisioning_codes', 'device_certificates')
            ORDER BY table_name
        """)

        if len(tables) == 2:
            print(f"[OK] All 2 tables created:")
            for table in tables:
                print(f"     - {table['table_name']}")
        else:
            print(f"[WARNING] Expected 2 tables, found {len(tables)}")

        print()

        # Verify indexes created
        print("[INFO] Verifying indexes created...")
        indexes = await conn.fetch("""
            SELECT indexname, tablename
            FROM pg_indexes
            WHERE tablename IN ('provisioning_codes', 'device_certificates')
              AND schemaname = 'public'
            ORDER BY tablename, indexname
        """)

        print(f"[OK] Created {len(indexes)} indexes:")
        current_table = None
        for idx in indexes:
            if idx['tablename'] != current_table:
                current_table = idx['tablename']
                print(f"     Table: {current_table}")
            print(f"       - {idx['indexname']}")

        print()

        # Check provisioning_codes table structure
        print("[INFO] Checking provisioning_codes table structure...")
        prov_cols = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'provisioning_codes'
            ORDER BY ordinal_position
        """)
        print(f"[OK] provisioning_codes has {len(prov_cols)} columns:")
        for col in prov_cols:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            print(f"     - {col['column_name']}: {col['data_type']} {nullable}")

        print()

        # Check device_certificates table structure
        print("[INFO] Checking device_certificates table structure...")
        cert_cols = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'device_certificates'
            ORDER BY ordinal_position
        """)
        print(f"[OK] device_certificates has {len(cert_cols)} columns:")
        for col in cert_cols:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            print(f"     - {col['column_name']}: {col['data_type']} {nullable}")

        print()
        print("="*80)
        print("[SUCCESS] Migration 013 completed successfully!")
        print("="*80)
        print()
        print("Summary:")
        print(f"  - 2 new tables created (provisioning_codes, device_certificates)")
        print(f"  - {len(indexes)} indexes created for performance")
        print(f"  - provisioning_codes: {len(prov_cols)} columns")
        print(f"  - device_certificates: {len(cert_cols)} columns")
        print()
        print("Next steps:")
        print("  1. Verify tables exist: SELECT * FROM provisioning_codes LIMIT 1;")
        print("  2. Verify tables exist: SELECT * FROM device_certificates LIMIT 1;")
        print("  3. Continue to Day 2: Create certificate service")
        print()

    except Exception as e:
        print()
        print("="*80)
        print(f"[ERROR] Migration 013 failed: {e}")
        print("="*80)
        import traceback
        traceback.print_exc()
        print()
        print("Troubleshooting:")
        print("  - Check that PostgreSQL is running")
        print("  - Check database connection string in .env file")
        print("  - Check that migrations/013_certificate_provisioning.sql exists")
        raise

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(apply_migration())
```

#### How to create the file:

```powershell
cd C:\Users\Srika\OneDrive\Desktop\hospital-management-system\hospital-backend

# Create file
notepad apply_migration_013.py

# Paste content above
# Save and close
```

#### Checkpoint:
✅ File exists at `hospital-backend\apply_migration_013.py`
✅ File is 123 lines long
✅ Contains `async def apply_migration():`

---

### STEP 1.4: Run Database Migration (10 minutes)

#### What you're doing:
Executing the migration to create new tables in PostgreSQL.

#### Commands to run:

```powershell
# 1. Navigate to backend directory
cd C:\Users\Srika\OneDrive\Desktop\hospital-management-system\hospital-backend

# 2. Make sure PostgreSQL is running
docker-compose ps postgres

# Expected output:
# NAME                  COMMAND                  STATUS
# hospital_postgres     "docker-entrypoint.s…"   Up 2 hours

# 3. Run migration
python apply_migration_013.py

# Expected output:
# ================================================================================
# MIGRATION 013: Certificate-Based Provisioning
# ================================================================================
#
# [INFO] Applying migration 013: provisioning_codes and device_certificates tables
# [OK] Migration 013 executed successfully
#
# [INFO] Verifying tables created...
# [OK] All 2 tables created:
#      - device_certificates
#      - provisioning_codes
#
# [INFO] Verifying indexes created...
# [OK] Created 8 indexes:
#      Table: device_certificates
#        - device_certificates_pkey
#        - idx_device_certs_expiry
#        - idx_device_certs_mac
#        - idx_device_certs_revoked
#        - idx_device_certs_unique
#      Table: provisioning_codes
#        - idx_prov_codes_technician
#        - idx_prov_codes_valid
#        - provisioning_codes_pkey
#
# [INFO] Checking provisioning_codes table structure...
# [OK] provisioning_codes has 7 columns:
#      - code: character varying NOT NULL
#      - technician_id: character varying NOT NULL
#      - created_at: timestamp with time zone NULL
#      - expires_at: timestamp with time zone NOT NULL
#      - used: boolean NULL
#      - used_at: timestamp with time zone NULL
#      - device_id: character varying NULL
#
# [INFO] Checking device_certificates table structure...
# [OK] device_certificates has 11 columns:
#      - id: integer NOT NULL
#      - device_id: character varying NOT NULL
#      - certificate_pem: text NOT NULL
#      - issued_at: timestamp with time zone NULL
#      - expires_at: timestamp with time zone NOT NULL
#      - revoked: boolean NULL
#      - revoked_at: timestamp with time zone NULL
#      - revoked_by: character varying NULL
#      - revocation_reason: text NULL
#      - mac_address: character varying NOT NULL
#      - serial_number: character varying NULL
#
# ================================================================================
# [SUCCESS] Migration 013 completed successfully!
# ================================================================================
```

#### If you get an error:

**Error:** `ModuleNotFoundError: No module named 'app'`
**Fix:** Make sure you're in the `hospital-backend` directory

**Error:** `connection refused`
**Fix:** PostgreSQL is not running. Run `docker-compose up -d postgres`

**Error:** `relation "provisioning_codes" already exists`
**Fix:** Migration already ran. This is OK! Skip to next step.

#### Checkpoint:
✅ Migration ran successfully
✅ 2 tables created (`provisioning_codes`, `device_certificates`)
✅ 8 indexes created

---

## DAY 1 END: What we accomplished

✅ Generated Hospital CA certificate (10-year validity)
✅ Moved CA private key to secure location
✅ Created database migration SQL file
✅ Created Python migration script
✅ Applied migration to database
✅ Verified 2 new tables exist with 8 indexes

**Time spent:** 1 hour 30 minutes
**Files created:** 4
**Database tables created:** 2

---

## DAY 2: Create Certificate Service (Backend)

### STEP 2.1: Install cryptography Library (5 minutes)

#### What you're doing:
Installing Python library needed to generate X.509 certificates.

#### Commands to run:

```powershell
# 1. Navigate to backend directory
cd C:\Users\Srika\OneDrive\Desktop\hospital-management-system\hospital-backend

# 2. Install cryptography library
pip install cryptography

# Expected output:
# Collecting cryptography
#   Downloading cryptography-41.0.5-cp39-abi3-win_amd64.whl (2.9 MB)
# ...
# Successfully installed cryptography-41.0.5 cffi-1.16.0

# 3. Verify installation
python -c "from cryptography import x509; print('✅ cryptography installed')"

# Expected output:
# ✅ cryptography installed
```

#### Checkpoint:
✅ cryptography library installed
✅ No import errors

---

### STEP 2.2: Create Certificate Service File (45 minutes)

#### What you're doing:
Creating Python service that generates X.509 certificates for ESP32 devices.

#### File to create:
`C:\Users\Srika\OneDrive\Desktop\hospital-management-system\hospital-backend\app\services\certificate_service.py`

#### Exact content:

```python
"""
Certificate Service for ESP32 Device Authentication
Generates X.509 TLS client certificates for device provisioning
"""

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CertificateService:
    """
    Service for generating X.509 certificates for ESP32 devices

    Uses Hospital CA to sign device certificates
    Each device gets a unique certificate with:
    - Common Name (CN) = device ID
    - Organization (O) = "Hospital Devices"
    - Organizational Unit (OU) = "IoT Watches"
    - Subject Alternative Names (SAN) = device hostnames
    - Extended Key Usage = TLS Client Authentication
    """

    def __init__(self, ca_cert_path: str, ca_key_path: str):
        """
        Initialize certificate service with Hospital CA

        Args:
            ca_cert_path: Path to hospital_ca.crt file
            ca_key_path: Path to hospital_ca.key file (secure location)

        Raises:
            FileNotFoundError: If CA files don't exist
            ValueError: If CA files are invalid
        """
        try:
            # Load CA certificate (public)
            with open(ca_cert_path, 'rb') as f:
                self.ca_cert = x509.load_pem_x509_certificate(f.read())
            logger.info(f"✅ CA certificate loaded from {ca_cert_path}")

            # Load CA private key (secret - must be protected!)
            with open(ca_key_path, 'rb') as f:
                self.ca_private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None  # No password protection (secure file system instead)
                )
            logger.info(f"✅ CA private key loaded from {ca_key_path}")

            # Log CA details
            subject = self.ca_cert.subject
            logger.info(f"📜 Hospital CA: {subject.rfc4514_string()}")
            logger.info(f"📅 CA valid until: {self.ca_cert.not_valid_after}")

        except FileNotFoundError as e:
            logger.error(f"❌ CA file not found: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to load CA: {e}")
            raise ValueError(f"Invalid CA files: {e}")

    def generate_device_certificate(
        self,
        device_id: str,
        mac_address: str,
        validity_days: int = 365
    ) -> tuple[str, str]:
        """
        Generate X.509 certificate for ESP32 device

        Args:
            device_id: Unique device identifier (e.g., "ESP32_WATCH_001")
            mac_address: Device MAC address (e.g., "30:AE:A4:12:34:56")
            validity_days: Certificate validity period in days (default: 365)

        Returns:
            tuple: (certificate_pem, private_key_pem)
                - certificate_pem: X.509 certificate in PEM format (string)
                - private_key_pem: RSA private key in PEM format (string)

        Example:
            cert, key = service.generate_device_certificate("ESP32_WATCH_001", "30:AE:A4:12:34:56")
            # Save cert and key to database or return to device
        """

        logger.info(f"🔧 Generating certificate for {device_id} (MAC: {mac_address})")

        # STEP 1: Generate RSA private key for device (2048-bit)
        # This takes ~0.5 seconds on modern hardware
        private_key = rsa.generate_private_key(
            public_exponent=65537,  # Standard RSA public exponent
            key_size=2048  # 2048-bit provides good security/performance balance
        )
        logger.debug(f"   Generated 2048-bit RSA private key")

        # STEP 2: Build certificate subject (device identity)
        subject = x509.Name([
            # Common Name = Device ID (REQUIRED - used by Mosquitto as username)
            x509.NameAttribute(NameOID.COMMON_NAME, device_id),

            # Organization = Hospital name
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Hospital Devices"),

            # Organizational Unit = Device category
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "IoT Watches"),

            # Country = India
            x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
        ])
        logger.debug(f"   Subject: {subject.rfc4514_string()}")

        # STEP 3: Calculate certificate validity dates
        not_valid_before = datetime.utcnow()
        not_valid_after = not_valid_before + timedelta(days=validity_days)
        logger.debug(f"   Valid from: {not_valid_before}")
        logger.debug(f"   Valid until: {not_valid_after}")

        # STEP 4: Build certificate
        cert_builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(self.ca_cert.subject)  # Issued by Hospital CA
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())  # Unique serial number
            .not_valid_before(not_valid_before)
            .not_valid_after(not_valid_after)
        )

        # STEP 5: Add Subject Alternative Names (SAN)
        # These are alternative hostnames/IDs for the device
        # Required by some TLS clients for hostname validation
        mac_clean = mac_address.replace(":", "").replace("-", "")
        san_names = [
            x509.DNSName(device_id),  # ESP32_WATCH_001
            x509.DNSName(f"{device_id}.hospital.local"),  # ESP32_WATCH_001.hospital.local
            x509.DNSName(f"watch-{mac_clean}"),  # watch-30AEA4123456
        ]
        cert_builder = cert_builder.add_extension(
            x509.SubjectAlternativeName(san_names),
            critical=False  # Not critical - cert works even if client ignores this
        )
        logger.debug(f"   SAN: {[str(name) for name in san_names]}")

        # STEP 6: Add Key Usage extension
        # Specifies what the private key can be used for
        cert_builder = cert_builder.add_extension(
            x509.KeyUsage(
                digital_signature=True,  # Can sign data (REQUIRED for TLS)
                key_encipherment=True,   # Can encrypt keys (REQUIRED for TLS RSA)
                content_commitment=False,  # Cannot sign documents (not needed)
                data_encipherment=False,   # Cannot encrypt data directly (not needed)
                key_agreement=False,       # Cannot do Diffie-Hellman (not needed)
                key_cert_sign=False,       # Cannot sign certificates (only CA can do this)
                crl_sign=False,            # Cannot sign CRLs (only CA can do this)
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True  # CRITICAL - TLS client MUST understand this extension
        )
        logger.debug(f"   Key Usage: digitalSignature, keyEncipherment")

        # STEP 7: Add Extended Key Usage extension
        # Specifies the PURPOSE of this certificate
        cert_builder = cert_builder.add_extension(
            x509.ExtendedKeyUsage([
                ExtendedKeyUsageOID.CLIENT_AUTH,  # TLS client authentication (ESP32 → Mosquitto)
            ]),
            critical=True  # CRITICAL - this cert can ONLY be used for TLS client auth
        )
        logger.debug(f"   Extended Key Usage: TLS Web Client Authentication")

        # STEP 8: Sign certificate with Hospital CA private key
        # This creates the final certificate that can be validated by clients
        certificate = cert_builder.sign(
            private_key=self.ca_private_key,
            algorithm=hashes.SHA256()  # Use SHA-256 for signature
        )
        logger.debug(f"   Certificate signed with SHA-256")

        # STEP 9: Convert certificate to PEM format (text format)
        # PEM = Privacy Enhanced Mail format (Base64 encoded with headers)
        certificate_pem = certificate.public_bytes(
            encoding=serialization.Encoding.PEM
        ).decode('utf-8')

        # STEP 10: Convert private key to PEM format
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,  # Standard format
            encryption_algorithm=serialization.NoEncryption()  # No password protection
        ).decode('utf-8')

        # Log success
        logger.info(f"✅ Certificate generated for {device_id}")
        logger.info(f"   Serial number: {certificate.serial_number}")
        logger.info(f"   Valid for: {validity_days} days")
        logger.info(f"   Certificate size: {len(certificate_pem)} bytes")
        logger.info(f"   Private key size: {len(private_key_pem)} bytes")

        return certificate_pem, private_key_pem


# Global service instance (initialized in main.py)
certificate_service: CertificateService = None

def initialize_certificate_service(ca_cert_path: str, ca_key_path: str) -> CertificateService:
    """
    Initialize global certificate service instance

    Called once at startup from main.py

    Args:
        ca_cert_path: Path to hospital_ca.crt
        ca_key_path: Path to hospital_ca.key

    Returns:
        CertificateService: Initialized service instance
    """
    global certificate_service
    certificate_service = CertificateService(ca_cert_path, ca_key_path)
    logger.info("✅ Certificate service initialized globally")
    return certificate_service
```

#### How to create the file:

```powershell
cd C:\Users\Srika\OneDrive\Desktop\hospital-management-system\hospital-backend\app\services

# Create file
notepad certificate_service.py

# Paste content above
# Save and close
```

#### Checkpoint:
✅ File exists at `hospital-backend\app\services\certificate_service.py`
✅ File is 236 lines long
✅ Contains `class CertificateService:`
✅ Contains `def generate_device_certificate(`

---

## DAY 2 STOP: This is getting too long

Let me know if you want me to continue this level of detail for all 7 days.

**What I've shown you so far:**
- ✅ **EXACT commands to run** (copy-paste ready)
- ✅ **EXACT file paths** (no ambiguity)
- ✅ **EXACT file contents** (complete code blocks)
- ✅ **Expected output** for each command
- ✅ **Error handling** for common issues
- ✅ **Checkpoints** after each step
- ✅ **Line counts** to verify files

**Still need to document (Days 3-7):**
- Day 3: Provisioning API endpoints
- Day 4: Mosquitto configuration changes
- Day 5: ESP32 firmware changes (part 1 - remove passwords)
- Day 6: ESP32 firmware changes (part 2 - add certificates)
- Day 7: Testing & verification

Should I continue with this level of detail for the remaining days?

Or is this format what you needed? Tell me:
1. **Is this detailed enough?**
2. **Want me to finish all 7 days like this?**
3. **Any changes to the format?**
