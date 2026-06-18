"""
Bootstrap Provisioning API Endpoints (Simplified)
Handles automatic device provisioning during first connection.
"""

from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import secrets
import bcrypt

from app.db.database import database
from app.core.config import settings

router = APIRouter()

# Pydantic schemas
class ProvisionRequest(BaseModel):
    uuid: str
    macAddress: str
    code: str
    deviceType: str

class ProvisionResponse(BaseModel):
    serialNumber: str
    deviceId: str
    certificatePem: str
    privateKeyPem: str
    caCertificatePem: str
    mqttBroker: str
    mqttPort: int
    mqttUsername: str
    mqttPassword: str

@router.post("/provision", response_model=ProvisionResponse)
async def provision_device(
    request: ProvisionRequest,
    x_device_api_key: str = Header(..., alias="X-Device-API-Key")
):
    """Bootstrap device provisioning endpoint"""

    # Validate API key
    expected_key = settings.BOOTSTRAP_API_KEY_WATCH if request.deviceType == "watch" else settings.BOOTSTRAP_API_KEY_SCANNER
    if x_device_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Check if already provisioned
    existing = await database.fetch_one(
        "SELECT serial_number FROM devices WHERE uuid = :uuid",
        {"uuid": request.uuid}
    )
    if existing:
        raise HTTPException(status_code=409, detail="Device already provisioned")

    # Validate code (simplified - just check it's numeric for now)
    if not request.code.isdigit() or len(request.code) != 6:
        raise HTTPException(status_code=403, detail="Invalid provisioning code")

    # Assign serial number
    prefix = 'W' if request.deviceType == 'watch' else 'S'
    result = await database.fetch_one(
        f"UPDATE device_serials SET last_sequence = last_sequence + 1 WHERE device_type = :dtype RETURNING last_sequence",
        {"dtype": request.deviceType}
    )

    if not result:
        # Initialize if not exists
        await database.execute(
            "INSERT INTO device_serials (device_type, last_sequence) VALUES (:dtype, 1) ON CONFLICT (device_type) DO UPDATE SET last_sequence = device_serials.last_sequence + 1",
            {"dtype": request.deviceType}
        )
        seq = 1
    else:
        seq = result['last_sequence']

    serial_number = f"{prefix}{seq:05d}"

    # Generate certificate
    ca_cert_path = settings.CA_CERT_PATH
    ca_key_path = settings.CA_KEY_PATH

    # Load CA
    with open(ca_cert_path, 'rb') as f:
        ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())
    with open(ca_key_path, 'rb') as f:
        ca_key = serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())

    # Generate device key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # Build certificate
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Telangana"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Hyderabad"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Symbiot"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, f"Medical Devices"),
        x509.NameAttribute(NameOID.COMMON_NAME, serial_number),
    ])

    from datetime import timedelta
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(f"{serial_number}.devices.hospital.local"),
            ]),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256(), default_backend())
    )

    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    ca_cert_pem = ca_cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')

    # Generate MQTT credentials
    mqtt_password = secrets.token_urlsafe(32)
    mqtt_password_hash = bcrypt.hashpw(mqtt_password.encode(), bcrypt.gensalt()).decode()

    # Save to database
    await database.execute(
        """INSERT INTO devices (
            uuid, serial_number, mac_address, device_type, status,
            provisioned_at, provisioning_code, mqtt_username, mqtt_password_hash
        ) VALUES (
            :uuid, :serial, :mac, :dtype, 'provisioned',
            :provisioned_at, :code, :mqtt_user, :mqtt_pass_hash
        )""",
        {
            "uuid": request.uuid,
            "serial": serial_number,
            "mac": request.macAddress,
            "dtype": request.deviceType,
            "provisioned_at": datetime.now(timezone.utc),
            "code": request.code,
            "mqtt_user": serial_number,
            "mqtt_pass_hash": mqtt_password_hash
        }
    )

    return ProvisionResponse(
        serialNumber=serial_number,
        deviceId=f"{request.deviceType.upper()}/{request.uuid}",
        certificatePem=cert_pem,
        privateKeyPem=key_pem,
        caCertificatePem=ca_cert_pem,
        mqttBroker=settings.MQTT_BROKER_HOST,
        mqttPort=settings.MQTT_BROKER_PORT,
        mqttUsername=serial_number,
        mqttPassword=mqtt_password
    )
