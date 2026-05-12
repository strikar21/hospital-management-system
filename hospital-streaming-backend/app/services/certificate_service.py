"""
Certificate Service for Medical Device Provisioning
Generates X.509 certificates for mTLS authentication with Mosquitto broker.
"""

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from datetime import datetime, timedelta, timezone
import secrets
import os
from pathlib import Path


class CertificateService:
    """
    Service for generating and managing device certificates.

    Responsibilities:
    - Generate device-specific X.509 certificates signed by Hospital CA
    - Create MQTT username/password credentials
    - Manage certificate lifecycle (issuance, renewal, revocation)
    """

    def __init__(self, ca_cert_path: str, ca_key_path: str, ca_key_password: str = None):
        """
        Initialize certificate service with Hospital CA credentials.

        Args:
            ca_cert_path: Path to CA certificate PEM file
            ca_key_path: Path to CA private key PEM file
            ca_key_password: Password for CA private key (if encrypted)
        """
        self.ca_cert = self._load_cert(ca_cert_path)
        self.ca_key = self._load_key(ca_key_path, ca_key_password)

    def _load_cert(self, cert_path: str) -> x509.Certificate:
        """Load X.509 certificate from PEM file"""
        with open(cert_path, 'rb') as f:
            cert_data = f.read()
            return x509.load_pem_x509_certificate(cert_data, default_backend())

    def _load_key(self, key_path: str, password: str = None):
        """Load RSA private key from PEM file"""
        with open(key_path, 'rb') as f:
            key_data = f.read()
            pwd = password.encode() if password else None
            return serialization.load_pem_private_key(key_data, password=pwd, backend=default_backend())

    def generate_device_certificate(
        self,
        serial_number: str,
        device_type: str,
        validity_days: int = 365
    ) -> dict:
        """
        Generate mTLS certificate for a device.

        Args:
            serial_number: Unique device serial number (e.g., W00001, S00001)
            device_type: Device type ('watch', 'scanner')
            validity_days: Certificate validity period in days (default: 365)

        Returns:
            Dictionary containing:
                - certificate: PEM-encoded device certificate
                - private_key: PEM-encoded private key
                - ca_certificate: PEM-encoded CA certificate
                - expires_at: Expiration timestamp
        """
        # Generate RSA 2048-bit private key for device
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        # Build X.509 certificate subject
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Telangana"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Hyderabad"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Symbiot Health Systems"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, f"Medical Devices - {device_type.title()}"),
            x509.NameAttribute(NameOID.COMMON_NAME, serial_number),
        ])

        # Set validity period
        not_valid_before = datetime.now(timezone.utc)
        not_valid_after = not_valid_before + timedelta(days=validity_days)

        # Build certificate
        cert_builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(self.ca_cert.subject)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(not_valid_before)
            .not_valid_after(not_valid_after)
        )

        # Add Subject Alternative Name (DNS name for device)
        cert_builder = cert_builder.add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(f"{serial_number}.devices.hospital.local"),
            ]),
            critical=False,
        )

        # Add Basic Constraints (not a CA)
        cert_builder = cert_builder.add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )

        # Add Key Usage (digital signature, key encipherment)
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
                decipher_only=False,
            ),
            critical=True,
        )

        # Add Extended Key Usage (TLS client authentication)
        cert_builder = cert_builder.add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=True,
        )

        # Sign certificate with Hospital CA
        cert = cert_builder.sign(self.ca_key, hashes.SHA256(), default_backend())

        # Serialize to PEM format
        cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')

        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        ca_cert_pem = self.ca_cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')

        return {
            "certificate": cert_pem,
            "private_key": key_pem,
            "ca_certificate": ca_cert_pem,
            "expires_at": not_valid_after
        }

    def generate_mqtt_credentials(self, serial_number: str) -> dict:
        """
        Generate MQTT username and password for defense-in-depth security.

        Args:
            serial_number: Device serial number (used as username)

        Returns:
            Dictionary containing:
                - username: MQTT username (same as serial_number)
                - password: Cryptographically secure random password
        """
        # Generate 32-byte random password (URL-safe base64 encoded)
        password = secrets.token_urlsafe(32)

        return {
            "username": serial_number,
            "password": password
        }

    def verify_certificate(self, cert_pem: str) -> dict:
        """
        Verify a certificate was signed by the Hospital CA.

        Args:
            cert_pem: PEM-encoded certificate to verify

        Returns:
            Dictionary containing:
                - valid: Boolean indicating if certificate is valid
                - serial_number: Device serial number from CN
                - expires_at: Expiration timestamp
                - days_until_expiry: Days remaining until expiration
        """
        try:
            # Load certificate
            cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())

            # Check if signed by our CA
            ca_public_key = self.ca_cert.public_key()
            try:
                ca_public_key.verify(
                    cert.signature,
                    cert.tbs_certificate_bytes,
                    # Note: verification method depends on signature algorithm
                )
                signed_by_ca = True
            except Exception:
                signed_by_ca = False

            # Extract serial number from CN
            common_name = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value

            # Check expiry
            now = datetime.now(timezone.utc)
            days_until_expiry = (cert.not_valid_after_utc - now).days

            is_valid = (
                signed_by_ca
                and cert.not_valid_before_utc <= now <= cert.not_valid_after_utc
            )

            return {
                "valid": is_valid,
                "serial_number": common_name,
                "expires_at": cert.not_valid_after_utc,
                "days_until_expiry": days_until_expiry
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
