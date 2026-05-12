"""
Bootstrap Provisioning Service for Medical Devices
Handles the complete device bootstrap provisioning workflow.
"""

from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import bcrypt
from typing import Optional

from app.models import Device, BootstrapCode, DeviceCertificate, DeviceSerial, BootstrapCodeStatus
from app.services.certificate_service import CertificateService


class BootstrapProvisioningError(Exception):
    """Base exception for provisioning errors"""
    pass


class InvalidAPIKeyError(BootstrapProvisioningError):
    """Raised when bootstrap API key is invalid"""
    pass


class InvalidCodeError(BootstrapProvisioningError):
    """Raised when provisioning code is invalid or expired"""
    pass


class DeviceAlreadyProvisionedError(BootstrapProvisioningError):
    """Raised when device is already provisioned"""
    pass


class BootstrapProvisioningService:
    """
    Service for handling device bootstrap provisioning.

    Workflow:
    1. Validate bootstrap API key (factory credential)
    2. Validate provisioning code (one-time PIN)
    3. Assign sequential serial number (W00001, S00001, etc.)
    4. Generate X.509 certificate for mTLS
    5. Generate MQTT username/password
    6. Save device and certificate to database
    7. Return provisioning response to device
    """

    # Bootstrap API keys (per device type)
    # In production, these should be stored in secure configuration or environment variables
    BOOTSTRAP_KEYS = {
        "watch": "WATCH_BOOTSTRAP_KEY_7x9k2p4n6m8q1w3e5r7t9y",
        "scanner": "SCANNER_BOOTSTRAP_KEY_5a8f3g1h9j2k4l6m8n0p2q"
    }

    def __init__(self, db: Session, cert_service: CertificateService):
        """
        Initialize bootstrap provisioning service.

        Args:
            db: SQLAlchemy database session
            cert_service: Certificate service for generating mTLS certificates
        """
        self.db = db
        self.cert_service = cert_service

    def provision_device(
        self,
        uuid: str,
        mac_address: str,
        code: str,
        device_type: str,
        api_key: str
    ) -> dict:
        """
        Complete device provisioning flow.

        Args:
            uuid: Device UUID (derived from MAC address)
            mac_address: Device MAC address
            code: 6-digit provisioning PIN
            device_type: Device type ('watch', 'scanner')
            api_key: Bootstrap API key (factory credential)

        Returns:
            Dictionary containing:
                - serialNumber: Assigned serial number (W00001, S00001)
                - deviceId: Device identifier (WATCH/UUID)
                - certificatePem: Device certificate
                - privateKeyPem: Device private key
                - caCertificatePem: CA certificate
                - mqttBroker: MQTT broker hostname/IP
                - mqttPort: MQTT broker port
                - mqttUsername: MQTT username
                - mqttPassword: MQTT password (sent only once!)

        Raises:
            InvalidAPIKeyError: If bootstrap API key is invalid
            InvalidCodeError: If provisioning code is invalid/expired
            DeviceAlreadyProvisionedError: If device already provisioned
        """

        # Step 1: Validate bootstrap API key
        if not self._validate_api_key(api_key, device_type):
            raise InvalidAPIKeyError(f"Invalid bootstrap API key for device type: {device_type}")

        # Step 2: Check if device already provisioned
        existing_device = self.db.query(Device).filter(
            (Device.uuid == uuid) | (Device.macAddress == mac_address)
        ).first()

        if existing_device and existing_device.serial_number:
            raise DeviceAlreadyProvisionedError(
                f"Device already provisioned with serial: {existing_device.serial_number}"
            )

        # Step 3: Validate provisioning code
        code_entry = self.db.query(BootstrapCode).filter(
            BootstrapCode.code == code,
            BootstrapCode.status == BootstrapCodeStatus.ACTIVE,
            BootstrapCode.device_type == device_type,
            BootstrapCode.expires_at > datetime.now(timezone.utc)
        ).first()

        if not code_entry:
            raise InvalidCodeError("Invalid, expired, or already used provisioning code")

        # Step 4: Assign sequential serial number
        serial_number = self._assign_serial_number(device_type)

        # Step 5: Generate X.509 certificate for mTLS
        cert_data = self.cert_service.generate_device_certificate(
            serial_number=serial_number,
            device_type=device_type,
            validity_days=365
        )

        # Step 6: Generate MQTT credentials (defense in depth)
        mqtt_creds = self.cert_service.generate_mqtt_credentials(serial_number)

        # Step 7: Hash MQTT password for storage
        mqtt_password_hash = bcrypt.hashpw(
            mqtt_creds['password'].encode(),
            bcrypt.gensalt()
        ).decode()

        # Step 8: Save or update device in database
        if existing_device:
            # Update existing device entry
            existing_device.uuid = uuid
            existing_device.serial_number = serial_number
            existing_device.deviceId = f"{device_type.upper()}/{uuid}"
            existing_device.deviceType = device_type
            existing_device.name = f"{device_type.title()} {serial_number}"
            existing_device.macAddress = mac_address
            existing_device.provisioned_at = datetime.now(timezone.utc)
            existing_device.provisioning_code = code
            existing_device.mqtt_username = mqtt_creds['username']
            existing_device.mqtt_password_hash = mqtt_password_hash
            existing_device.status = "provisioned"
            device = existing_device
        else:
            # Create new device entry
            device = Device(
                uuid=uuid,
                serial_number=serial_number,
                deviceId=f"{device_type.upper()}/{uuid}",
                deviceType=device_type,
                name=f"{device_type.title()} {serial_number}",
                macAddress=mac_address,
                status="provisioned",
                provisioned_at=datetime.now(timezone.utc),
                provisioning_code=code,
                mqtt_username=mqtt_creds['username'],
                mqtt_password_hash=mqtt_password_hash
            )
            self.db.add(device)

        # Step 9: Save certificate to database
        cert_record = DeviceCertificate(
            serial_number=serial_number,
            certificate_pem=cert_data['certificate'],
            issued_at=datetime.now(timezone.utc),
            expires_at=cert_data['expires_at']
        )
        self.db.add(cert_record)

        # Step 10: Mark provisioning code as used
        code_entry.status = BootstrapCodeStatus.USED
        code_entry.used_at = datetime.now(timezone.utc)
        code_entry.used_by_device = serial_number

        # Commit all changes
        self.db.commit()

        # Step 11: Return provisioning response
        # NOTE: This is the ONLY time the private key and MQTT password are sent in plaintext
        # Device must save them securely in NVS
        return {
            "serialNumber": serial_number,
            "deviceId": f"{device_type.upper()}/{uuid}",
            "certificatePem": cert_data['certificate'],
            "privateKeyPem": cert_data['private_key'],
            "caCertificatePem": cert_data['ca_certificate'],
            "mqttBroker": "192.168.0.65",  # TODO: Get from config
            "mqttPort": 8883,
            "mqttUsername": mqtt_creds['username'],
            "mqttPassword": mqtt_creds['password']  # Sent only once!
        }

    def _assign_serial_number(self, device_type: str) -> str:
        """
        Assign next sequential serial number for device type.

        Args:
            device_type: Device type ('watch', 'scanner')

        Returns:
            Next sequential serial number (W00001, S00001, etc.)
        """
        # Lock row for update to prevent race conditions
        serial_record = self.db.query(DeviceSerial).filter(
            DeviceSerial.device_type == device_type
        ).with_for_update().first()

        if not serial_record:
            # Initialize if not exists
            serial_record = DeviceSerial(
                device_type=device_type,
                last_sequence=0
            )
            self.db.add(serial_record)
            self.db.flush()

        # Increment sequence
        serial_record.last_sequence += 1
        next_seq = serial_record.last_sequence

        # Format serial number: W00001, S00001
        prefix = 'W' if device_type == 'watch' else 'S'
        serial_number = f"{prefix}{next_seq:05d}"

        return serial_number

    def _validate_api_key(self, api_key: str, device_type: str) -> bool:
        """
        Validate factory bootstrap API key.

        Args:
            api_key: Bootstrap API key from device
            device_type: Device type ('watch', 'scanner')

        Returns:
            True if API key is valid for the device type
        """
        expected_key = self.BOOTSTRAP_KEYS.get(device_type)
        return api_key == expected_key

    def generate_provisioning_codes(
        self,
        device_type: str,
        count: int,
        validity_hours: int = 48,
        created_by_staff: Optional[int] = None
    ) -> list:
        """
        Generate provisioning codes for device deployment.

        Args:
            device_type: Device type ('watch', 'scanner')
            count: Number of codes to generate
            validity_hours: Validity period in hours (default: 48)
            created_by_staff: Staff member ID who generated codes

        Returns:
            List of generated codes with expiration timestamps
        """
        import secrets
        import string

        codes = []
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=validity_hours)

        for _ in range(count):
            # Generate 6-digit numeric code
            code = ''.join(secrets.choice(string.digits) for _ in range(6))

            # Ensure uniqueness
            while self.db.query(BootstrapCode).filter(BootstrapCode.code == code).first():
                code = ''.join(secrets.choice(string.digits) for _ in range(6))

            # Create code entry
            code_entry = BootstrapCode(
                code=code,
                device_type=device_type,
                status=BootstrapCodeStatus.ACTIVE,
                created_at=now,
                expires_at=expires_at,
                created_by_staff=created_by_staff
            )
            self.db.add(code_entry)
            codes.append({
                "code": code,
                "device_type": device_type,
                "expires_at": expires_at.isoformat()
            })

        self.db.commit()
        return codes
