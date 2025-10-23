"""
Hospital Management System - Certificate Authority Generator
Generates all required certificates for MQTT mTLS authentication

This script creates:
1. Hospital CA Certificate (Root CA)
2. Mosquitto MQTT Server Certificate
3. Backend MQTT Client Certificate
4. Copies CA to ESP32 data folder

All certificates use consistent organizational details:
- Country: IN
- State: Telangana
- Locality: Hyderabad
- Organization: Symbiot
- Organizational Unit: SymHMS Development
"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

# Organizational details (consistent across all certificates)
ORG_DETAILS = {
    'country': 'IN',
    'state': 'Telangana',
    'locality': 'Hyderabad',
    'organization': 'Symbiot',
    'organizational_unit': 'SymHMS Development'
}

# Paths (relative to this script's location)
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
MOSQUITTO_CERTS_DIR = PROJECT_ROOT / 'mosquitto' / 'certs'
ESP32_DATA_DIR = PROJECT_ROOT / 'esp32_hospital_watch_complete' / 'data'
BACKUPS_DIR = MOSQUITTO_CERTS_DIR / 'backups'


def print_header(title):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def create_backup_dir():
    """Create backups directory if it doesn't exist"""
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


def backup_existing_certificates():
    """Backup existing certificates before regeneration"""
    print("[BACKUP] Backing up existing certificates...")

    create_backup_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_subdir = BACKUPS_DIR / f"backup_{timestamp}"
    backup_subdir.mkdir(exist_ok=True)

    files_to_backup = [
        'hospital_ca.crt',
        'hospital_ca.key',
        'server.crt',
        'server.key',
        'server.csr',
        'backend.crt',
        'backend.key',
        'backend.csr'
    ]

    backed_up = 0
    for filename in files_to_backup:
        source = MOSQUITTO_CERTS_DIR / filename
        if source.exists():
            dest = backup_subdir / filename
            shutil.copy2(source, dest)
            backed_up += 1

    print(f"[OK] Backed up {backed_up} existing certificates to {backup_subdir}\n")


def generate_hospital_ca():
    """Generate Hospital CA certificate and private key"""
    print("[CA] Generating Hospital CA Certificate...")

    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,  # ESP32 hardware acceleration compatible (was 4096)
        backend=default_backend()
    )

    # Create subject/issuer (same for self-signed CA)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, ORG_DETAILS['country']),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, ORG_DETAILS['state']),
        x509.NameAttribute(NameOID.LOCALITY_NAME, ORG_DETAILS['locality']),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, ORG_DETAILS['organization']),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, ORG_DETAILS['organizational_unit']),
        x509.NameAttribute(NameOID.COMMON_NAME, "Symbiot Hospital CA"),
    ])

    # Build certificate
    cert_builder = x509.CertificateBuilder()
    cert_builder = cert_builder.subject_name(subject)
    cert_builder = cert_builder.issuer_name(issuer)
    cert_builder = cert_builder.public_key(private_key.public_key())
    cert_builder = cert_builder.serial_number(x509.random_serial_number())

    # Validity: 10 years
    not_valid_before = datetime.utcnow()
    not_valid_after = not_valid_before + timedelta(days=3650)
    cert_builder = cert_builder.not_valid_before(not_valid_before)
    cert_builder = cert_builder.not_valid_after(not_valid_after)

    # CA extensions
    cert_builder = cert_builder.add_extension(
        x509.BasicConstraints(ca=True, path_length=None),
        critical=True
    )
    cert_builder = cert_builder.add_extension(
        x509.KeyUsage(
            digital_signature=True,
            key_cert_sign=True,
            crl_sign=True,
            content_commitment=False,
            key_encipherment=False,
            data_encipherment=False,
            key_agreement=False,
            encipher_only=False,
            decipher_only=False
        ),
        critical=True
    )
    cert_builder = cert_builder.add_extension(
        x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
        critical=False
    )
    cert_builder = cert_builder.add_extension(
        x509.AuthorityKeyIdentifier.from_issuer_public_key(private_key.public_key()),
        critical=False
    )

    # Sign certificate
    certificate = cert_builder.sign(
        private_key=private_key,
        algorithm=hashes.SHA256(),
        backend=default_backend()
    )

    # Save certificate
    cert_path = MOSQUITTO_CERTS_DIR / 'hospital_ca.crt'
    with open(cert_path, 'wb') as f:
        f.write(certificate.public_bytes(serialization.Encoding.PEM))

    # Save private key
    key_path = MOSQUITTO_CERTS_DIR / 'hospital_ca.key'
    with open(key_path, 'wb') as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    print(f"[OK] Hospital CA generated:")
    print(f"   - Certificate: {cert_path}")
    print(f"   - Private Key: {key_path}")
    print(f"   - Valid: {not_valid_before.strftime('%Y-%m-%d')} to {not_valid_after.strftime('%Y-%m-%d')}\n")

    return certificate, private_key


def generate_server_certificate(ca_cert, ca_key):
    """Generate Mosquitto server certificate signed by Hospital CA"""
    print("[SERVER] Generating Mosquitto Server Certificate...")

    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,  # ESP32 hardware acceleration compatible (was 4096)
        backend=default_backend()
    )

    # Create subject
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, ORG_DETAILS['country']),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, ORG_DETAILS['state']),
        x509.NameAttribute(NameOID.LOCALITY_NAME, ORG_DETAILS['locality']),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, ORG_DETAILS['organization']),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, ORG_DETAILS['organizational_unit']),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])

    # Build certificate
    cert_builder = x509.CertificateBuilder()
    cert_builder = cert_builder.subject_name(subject)
    cert_builder = cert_builder.issuer_name(ca_cert.subject)
    cert_builder = cert_builder.public_key(private_key.public_key())
    cert_builder = cert_builder.serial_number(x509.random_serial_number())

    # Validity: 10 years
    not_valid_before = datetime.utcnow()
    not_valid_after = not_valid_before + timedelta(days=3650)
    cert_builder = cert_builder.not_valid_before(not_valid_before)
    cert_builder = cert_builder.not_valid_after(not_valid_after)

    # Subject Alternative Names
    san = x509.SubjectAlternativeName([
        x509.DNSName("localhost"),
        x509.DNSName("hospital-mosquitto"),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        x509.IPAddress(ipaddress.IPv4Address("192.168.0.113")),
    ])
    cert_builder = cert_builder.add_extension(san, critical=False)

    # Server extensions
    cert_builder = cert_builder.add_extension(
        x509.BasicConstraints(ca=False, path_length=None),
        critical=True
    )
    cert_builder = cert_builder.add_extension(
        x509.KeyUsage(
            digital_signature=True,
            key_encipherment=True,
            content_commitment=False,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=False,
            crl_sign=False,
            encipher_only=False,
            decipher_only=False
        ),
        critical=True
    )
    cert_builder = cert_builder.add_extension(
        x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
        critical=True
    )
    cert_builder = cert_builder.add_extension(
        x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
        critical=False
    )
    cert_builder = cert_builder.add_extension(
        x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
        critical=False
    )

    # Sign with CA key
    certificate = cert_builder.sign(
        private_key=ca_key,
        algorithm=hashes.SHA256(),
        backend=default_backend()
    )

    # Save certificate
    cert_path = MOSQUITTO_CERTS_DIR / 'server.crt'
    with open(cert_path, 'wb') as f:
        f.write(certificate.public_bytes(serialization.Encoding.PEM))

    # Save private key
    key_path = MOSQUITTO_CERTS_DIR / 'server.key'
    with open(key_path, 'wb') as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # Create CSR (for reference)
    csr = x509.CertificateSigningRequestBuilder().subject_name(subject).sign(
        private_key, hashes.SHA256(), default_backend()
    )
    csr_path = MOSQUITTO_CERTS_DIR / 'server.csr'
    with open(csr_path, 'wb') as f:
        f.write(csr.public_bytes(serialization.Encoding.PEM))

    print(f"[OK] Mosquitto Server Certificate generated:")
    print(f"   - Certificate: {cert_path}")
    print(f"   - Private Key: {key_path}")
    print(f"   - CN: localhost")
    print(f"   - SAN: DNS:localhost, DNS:hospital-mosquitto, IP:127.0.0.1, IP:192.168.0.113\n")

    return certificate, private_key


def generate_backend_certificate(ca_cert, ca_key):
    """Generate Backend MQTT client certificate signed by Hospital CA"""
    print("[CLIENT] Generating Backend MQTT Client Certificate...")

    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,  # 2048 is sufficient for client certs
        backend=default_backend()
    )

    # Create subject
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, ORG_DETAILS['country']),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, ORG_DETAILS['state']),
        x509.NameAttribute(NameOID.LOCALITY_NAME, ORG_DETAILS['locality']),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, ORG_DETAILS['organization']),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, ORG_DETAILS['organizational_unit']),
        x509.NameAttribute(NameOID.COMMON_NAME, "hospitalBackend"),
    ])

    # Build certificate
    cert_builder = x509.CertificateBuilder()
    cert_builder = cert_builder.subject_name(subject)
    cert_builder = cert_builder.issuer_name(ca_cert.subject)
    cert_builder = cert_builder.public_key(private_key.public_key())
    cert_builder = cert_builder.serial_number(x509.random_serial_number())

    # Validity: 10 years
    not_valid_before = datetime.utcnow()
    not_valid_after = not_valid_before + timedelta(days=3650)
    cert_builder = cert_builder.not_valid_before(not_valid_before)
    cert_builder = cert_builder.not_valid_after(not_valid_after)

    # Client extensions
    cert_builder = cert_builder.add_extension(
        x509.BasicConstraints(ca=False, path_length=None),
        critical=True
    )
    cert_builder = cert_builder.add_extension(
        x509.KeyUsage(
            digital_signature=True,
            key_encipherment=True,
            content_commitment=False,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=False,
            crl_sign=False,
            encipher_only=False,
            decipher_only=False
        ),
        critical=True
    )
    cert_builder = cert_builder.add_extension(
        x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]),
        critical=True
    )
    cert_builder = cert_builder.add_extension(
        x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
        critical=False
    )
    cert_builder = cert_builder.add_extension(
        x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
        critical=False
    )

    # Sign with CA key
    certificate = cert_builder.sign(
        private_key=ca_key,
        algorithm=hashes.SHA256(),
        backend=default_backend()
    )

    # Save certificate
    cert_path = MOSQUITTO_CERTS_DIR / 'backend.crt'
    with open(cert_path, 'wb') as f:
        f.write(certificate.public_bytes(serialization.Encoding.PEM))

    # Save private key
    key_path = MOSQUITTO_CERTS_DIR / 'backend.key'
    with open(key_path, 'wb') as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # Create CSR (for reference)
    csr = x509.CertificateSigningRequestBuilder().subject_name(subject).sign(
        private_key, hashes.SHA256(), default_backend()
    )
    csr_path = MOSQUITTO_CERTS_DIR / 'backend.csr'
    with open(csr_path, 'wb') as f:
        f.write(csr.public_bytes(serialization.Encoding.PEM))

    print(f"[OK] Backend Client Certificate generated:")
    print(f"   - Certificate: {cert_path}")
    print(f"   - Private Key: {key_path}")
    print(f"   - CN: hospitalBackend\n")

    return certificate, private_key


def copy_ca_to_esp32():
    """Copy Hospital CA certificate to ESP32 data folder"""
    print("[COPY] Copying CA to ESP32 data folder...")

    source = MOSQUITTO_CERTS_DIR / 'hospital_ca.crt'
    dest = ESP32_DATA_DIR / 'ca.crt'

    # Create ESP32 data directory if it doesn't exist
    ESP32_DATA_DIR.mkdir(parents=True, exist_ok=True)

    shutil.copy2(source, dest)
    print(f"[OK] CA certificate copied to {dest}\n")


def validate_certificates(ca_cert):
    """Validate all generated certificates"""
    print("[VALIDATE] Validating certificate chains...")

    import subprocess

    # Validate server certificate
    result = subprocess.run(
        ['openssl', 'verify', '-CAfile',
         str(MOSQUITTO_CERTS_DIR / 'hospital_ca.crt'),
         str(MOSQUITTO_CERTS_DIR / 'server.crt')],
        capture_output=True,
        text=True
    )
    if 'OK' in result.stdout:
        print("[OK] Mosquitto server certificate: VALID (signed by Hospital CA)")
    else:
        print(f"[ERROR] Mosquitto server certificate: INVALID\n{result.stdout}{result.stderr}")

    # Validate backend certificate
    result = subprocess.run(
        ['openssl', 'verify', '-CAfile',
         str(MOSQUITTO_CERTS_DIR / 'hospital_ca.crt'),
         str(MOSQUITTO_CERTS_DIR / 'backend.crt')],
        capture_output=True,
        text=True
    )
    if 'OK' in result.stdout:
        print("[OK] Backend client certificate: VALID (signed by Hospital CA)")
    else:
        print(f"[ERROR] Backend client certificate: INVALID\n{result.stdout}{result.stderr}")


def main():
    """Main execution function"""
    print_header("Hospital Certificate Authority Generator")

    try:
        # Step 1: Backup existing certificates
        backup_existing_certificates()

        # Step 2: Generate Hospital CA
        ca_cert, ca_key = generate_hospital_ca()

        # Step 3: Generate Mosquitto server certificate
        server_cert, server_key = generate_server_certificate(ca_cert, ca_key)

        # Step 4: Generate Backend client certificate
        backend_cert, backend_key = generate_backend_certificate(ca_cert, ca_key)

        # Step 5: Copy CA to ESP32 data folder
        copy_ca_to_esp32()

        # Step 6: Validate all certificates
        validate_certificates(ca_cert)

        # Success summary
        print_header("SUCCESS - All Certificates Generated!")
        print("Next steps:")
        print("1. Upload SPIFFS to ESP32 (Tools -> ESP32 Sketch Data Upload)")
        print("2. Restart Mosquitto: docker restart hospital_mosquitto")
        print("3. Restart Backend")
        print("4. Re-provision ESP32 with new PIN")
        print()

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


# Import ipaddress module
import ipaddress

if __name__ == '__main__':
    exit(main())
