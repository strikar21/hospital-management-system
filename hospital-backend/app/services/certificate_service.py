"""
Certificate Service for Device Authentication
Generates and manages X.509 certificates for ESP32 devices using mTLS
"""

import os
from datetime import datetime, timedelta
from typing import Tuple
from cryptography import x509
from ..common.datetime import now_utc
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature
import logging

logger = logging.getLogger(__name__)


class CertificateService:
    """
    Manages device certificate generation and signing
    Uses Hospital CA to sign device certificates for mTLS authentication
    """

    def __init__(self, ca_cert_path: str, ca_key_path: str):
        """
        Initialize certificate service with CA credentials

        Args:
            ca_cert_path: Path to Hospital CA certificate (PEM format)
            ca_key_path: Path to Hospital CA private key (PEM format)
        """
        self.ca_cert_path = ca_cert_path
        self.ca_key_path = ca_key_path

        # Load CA certificate
        logger.info(f"Loading Hospital CA certificate from {ca_cert_path}")
        with open(ca_cert_path, 'rb') as f:
            self.ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())

        # Load CA private key
        logger.info(f"Loading Hospital CA private key from {ca_key_path}")
        with open(ca_key_path, 'rb') as f:
            self.ca_private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,  # CA key is not password-protected
                backend=default_backend()
            )

        logger.info("CertificateService initialized successfully")

    def generate_device_certificate(
        self,
        device_id: str,
        mac_address: str,
        validity_days: int = 365
    ) -> Tuple[str, str]:
        """
        Generate a new device certificate signed by Hospital CA

        Args:
            device_id: Unique device identifier (from devices table)
            mac_address: Device MAC address (for Subject Alternative Name)
            validity_days: Certificate validity period (default: 365 days)

        Returns:
            Tuple of (certificate_pem, private_key_pem) as strings

        Note:
            The private key is returned to be sent to the device during provisioning.
            It is NOT stored in the database (only the public certificate is stored).
        """
        logger.info(f"Generating certificate for device {device_id} (MAC: {mac_address})")

        # Step 1: Generate device private key (2048-bit RSA)
        device_private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,  # 2048 bits for ESP32 compatibility (4096 would be better but slower)
            backend=default_backend()
        )
        logger.debug(f"Generated 2048-bit RSA private key for device {device_id}")

        # Step 2: Create certificate subject (device identity)
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Telangana"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Hyderabad"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Symbiot"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "SymHMS Development"),
            x509.NameAttribute(NameOID.COMMON_NAME, device_id),  # CRITICAL: device_id is used for MQTT authentication
        ])

        # Step 3: Build certificate
        cert_builder = x509.CertificateBuilder()

        # Set subject and issuer
        cert_builder = cert_builder.subject_name(subject)
        cert_builder = cert_builder.issuer_name(self.ca_cert.subject)

        # Set public key (from device private key)
        cert_builder = cert_builder.public_key(device_private_key.public_key())

        # Set serial number (unique for each certificate)
        serial_number = x509.random_serial_number()
        cert_builder = cert_builder.serial_number(serial_number)
        logger.debug(f"Certificate serial number: {serial_number}")

        # Set validity period
        not_valid_before = now_utc()
        not_valid_after = not_valid_before + timedelta(days=validity_days)
        cert_builder = cert_builder.not_valid_before(not_valid_before)
        cert_builder = cert_builder.not_valid_after(not_valid_after)
        logger.debug(f"Certificate valid from {not_valid_before} to {not_valid_after}")

        # Step 4: Add X.509 extensions

        # Subject Alternative Name (SAN) - includes MAC address for additional verification
        san = x509.SubjectAlternativeName([
            x509.DNSName(f"device-{device_id}.hospital.local"),
            x509.DNSName(f"mac-{mac_address.replace(':', '-')}.hospital.local"),
        ])
        cert_builder = cert_builder.add_extension(san, critical=False)

        # Key Usage - digital signature and key encipherment (for TLS)
        key_usage = x509.KeyUsage(
            digital_signature=True,
            key_encipherment=True,
            content_commitment=False,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=False,
            crl_sign=False,
            encipher_only=False,
            decipher_only=False
        )
        cert_builder = cert_builder.add_extension(key_usage, critical=True)

        # Extended Key Usage - TLS client authentication ONLY (not server)
        extended_key_usage = x509.ExtendedKeyUsage([
            ExtendedKeyUsageOID.CLIENT_AUTH  # This certificate is for client authentication only
        ])
        cert_builder = cert_builder.add_extension(extended_key_usage, critical=True)

        # Basic Constraints - this is NOT a CA certificate
        basic_constraints = x509.BasicConstraints(ca=False, path_length=None)
        cert_builder = cert_builder.add_extension(basic_constraints, critical=True)

        # Authority Key Identifier - links this cert to the CA
        authority_key_id = x509.AuthorityKeyIdentifier.from_issuer_public_key(
            self.ca_private_key.public_key()
        )
        cert_builder = cert_builder.add_extension(authority_key_id, critical=False)

        # Subject Key Identifier - unique identifier for this certificate's public key
        subject_key_id = x509.SubjectKeyIdentifier.from_public_key(
            device_private_key.public_key()
        )
        cert_builder = cert_builder.add_extension(subject_key_id, critical=False)

        # Step 5: Sign the certificate with Hospital CA private key
        device_cert = cert_builder.sign(
            private_key=self.ca_private_key,
            algorithm=hashes.SHA256(),  # SHA-256 for signing
            backend=default_backend()
        )
        logger.info(f"Certificate for device {device_id} signed by Hospital CA")

        # Step 6: Convert to PEM format (text-based encoding)
        certificate_pem = device_cert.public_bytes(
            encoding=serialization.Encoding.PEM
        ).decode('utf-8')

        private_key_pem = device_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,  # Standard PKCS#8 format (ESP32 compatible)
            encryption_algorithm=serialization.NoEncryption()  # No password protection
        ).decode('utf-8')

        logger.info(f"Device certificate generated successfully for {device_id}")
        logger.debug(f"Certificate size: {len(certificate_pem)} bytes, Key size: {len(private_key_pem)} bytes")

        return (certificate_pem, private_key_pem)

    def verify_certificate(self, certificate_pem: str) -> bool:
        """
        Verify that a certificate was signed by our Hospital CA

        Args:
            certificate_pem: PEM-encoded certificate to verify

        Returns:
            True if certificate is valid and signed by our CA, False otherwise
        """
        try:
            # Load the certificate
            cert = x509.load_pem_x509_certificate(
                certificate_pem.encode('utf-8'),
                default_backend()
            )

            # Verify signature using CA's public key
            # RSA signature verification with PKCS1v15 padding (standard for X.509)
            ca_public_key = self.ca_cert.public_key()
            ca_public_key.verify(
                cert.signature,
                cert.tbs_certificate_bytes,
                padding.PKCS1v15(),
                hashes.SHA256()
            )

            # Verify certificate is not expired
            now = now_utc()
            if now < cert.not_valid_before or now > cert.not_valid_after:
                logger.warning(f"Certificate is expired or not yet valid")
                return False

            logger.info("Certificate verification successful")
            return True

        except InvalidSignature:
            logger.error("Certificate signature verification failed - not signed by our CA")
            return False
        except Exception as e:
            logger.error(f"Certificate verification failed: {str(e)}")
            return False

    def extract_device_id(self, certificate_pem: str) -> str:
        """
        Extract device_id from certificate Common Name

        Args:
            certificate_pem: PEM-encoded certificate

        Returns:
            Device ID (Common Name from certificate subject)
        """
        cert = x509.load_pem_x509_certificate(
            certificate_pem.encode('utf-8'),
            default_backend()
        )

        # Extract CN from subject
        common_name = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        return common_name
