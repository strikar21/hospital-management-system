"""
Bootstrap Provisioning API Endpoints
Handles automatic device provisioning during first connection.
"""

from fastapi import APIRouter, HTTPException, Header, Depends, status
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.bootstrap_provisioning_service import (
    BootstrapProvisioningService,
    InvalidAPIKeyError,
    InvalidCodeError,
    DeviceAlreadyProvisionedError
)
from app.services.certificate_service import CertificateService
import os

router = APIRouter(prefix="/bootstrap", tags=["Bootstrap Provisioning"])


# Pydantic schemas for request/response
class ProvisionRequest(BaseModel):
    """Request payload for device bootstrap provisioning"""
    uuid: str = Field(..., description="Device UUID (derived from MAC address)", min_length=12, max_length=50)
    macAddress: str = Field(..., description="Device MAC address", regex=r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
    code: str = Field(..., description="6-digit provisioning PIN", min_length=6, max_length=6, regex=r'^\d{6}$')
    deviceType: str = Field(..., description="Device type (watch, scanner)")

    class Config:
        json_schema_extra = {
            "example": {
                "uuid": "F4CE3600187C",
                "macAddress": "F4:CE:36:00:18:7C",
                "code": "123456",
                "deviceType": "watch"
            }
        }


class ProvisionResponse(BaseModel):
    """Response payload with device credentials and certificate"""
    serialNumber: str = Field(..., description="Assigned serial number (W00001, S00001)")
    deviceId: str = Field(..., description="Device identifier (WATCH/UUID)")
    certificatePem: str = Field(..., description="PEM-encoded device certificate for mTLS")
    privateKeyPem: str = Field(..., description="PEM-encoded private key (sent only once!)")
    caCertificatePem: str = Field(..., description="PEM-encoded CA certificate")
    mqttBroker: str = Field(..., description="MQTT broker hostname or IP")
    mqttPort: int = Field(..., description="MQTT broker port (8883 for TLS)")
    mqttUsername: str = Field(..., description="MQTT username for authentication")
    mqttPassword: str = Field(..., description="MQTT password (sent only once!)")

    class Config:
        json_schema_extra = {
            "example": {
                "serialNumber": "W00001",
                "deviceId": "WATCH/F4CE3600187C",
                "certificatePem": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
                "privateKeyPem": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----",
                "caCertificatePem": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
                "mqttBroker": "192.168.0.65",
                "mqttPort": 8883,
                "mqttUsername": "W00001",
                "mqttPassword": "Xy8Kp2Nm4Qr6Tv9Wz3Bc5Df7Gh1Jk0Mn"
            }
        }


class GenerateCodesRequest(BaseModel):
    """Request to generate provisioning codes"""
    deviceType: str = Field(..., description="Device type (watch, scanner)")
    count: int = Field(..., description="Number of codes to generate", ge=1, le=100)
    validityHours: int = Field(default=48, description="Validity period in hours", ge=1, le=168)

    class Config:
        json_schema_extra = {
            "example": {
                "deviceType": "watch",
                "count": 10,
                "validityHours": 48
            }
        }


class GenerateCodesResponse(BaseModel):
    """Response with generated provisioning codes"""
    codes: list = Field(..., description="List of generated codes with expiration")

    class Config:
        json_schema_extra = {
            "example": {
                "codes": [
                    {"code": "123456", "device_type": "watch", "expires_at": "2025-05-14T12:00:00Z"},
                    {"code": "789012", "device_type": "watch", "expires_at": "2025-05-14T12:00:00Z"}
                ]
            }
        }


def get_cert_service() -> CertificateService:
    """
    Dependency to get certificate service instance.
    In production, CA cert/key paths should come from environment variables.
    """
    # TODO: Get paths from environment variables or config
    ca_cert_path = os.getenv("CA_CERT_PATH", "C:/Users/Srika/OneDrive/Desktop/hospital-management-system/mosquitto/certs/ca.crt")
    ca_key_path = os.getenv("CA_KEY_PATH", "C:/Users/Srika/OneDrive/Desktop/hospital-management-system/mosquitto/certs/ca.key")

    return CertificateService(ca_cert_path, ca_key_path)


@router.post(
    "/provision",
    response_model=ProvisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Bootstrap provision a device",
    description=(
        "Provision a new device with mTLS certificate and MQTT credentials. "
        "This endpoint is called by the device during its first connection after WiFi provisioning. "
        "Requires factory bootstrap API key in X-Device-API-Key header."
    ),
    responses={
        200: {"description": "Device successfully provisioned with certificate and credentials"},
        400: {"description": "Invalid request data"},
        401: {"description": "Invalid bootstrap API key"},
        403: {"description": "Invalid or expired provisioning code"},
        409: {"description": "Device already provisioned"},
        500: {"description": "Certificate generation failed"}
    }
)
async def provision_device(
    request: ProvisionRequest,
    x_device_api_key: str = Header(..., description="Factory bootstrap API key"),
    db: Session = Depends(get_db),
    cert_service: CertificateService = Depends(get_cert_service)
):
    """
    Bootstrap provision a device with mTLS certificate.

    Flow:
    1. Validate bootstrap API key (factory credential)
    2. Validate 6-digit provisioning PIN
    3. Assign sequential serial number
    4. Generate X.509 certificate
    5. Generate MQTT credentials
    6. Return provisioning data

    Security Notes:
    - This is a one-time provisioning process
    - Private key and MQTT password are sent ONLY during this request
    - Device must save credentials securely in NVS
    - Provisioning code is single-use and time-limited
    """
    try:
        # Initialize provisioning service
        provisioning_service = BootstrapProvisioningService(db, cert_service)

        # Perform provisioning
        result = provisioning_service.provision_device(
            uuid=request.uuid,
            mac_address=request.macAddress,
            code=request.code,
            device_type=request.deviceType,
            api_key=x_device_api_key
        )

        return ProvisionResponse(**result)

    except InvalidAPIKeyError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except InvalidCodeError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except DeviceAlreadyProvisionedError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Certificate generation failed: {str(e)}"
        )


@router.post(
    "/codes",
    response_model=GenerateCodesResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate provisioning codes",
    description=(
        "Generate one-time provisioning codes for device deployment. "
        "These 6-digit PINs are used by field staff during BLE provisioning. "
        "Admin authentication required."
    ),
    responses={
        200: {"description": "Codes generated successfully"},
        400: {"description": "Invalid request data"},
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"}
    }
)
async def generate_codes(
    request: GenerateCodesRequest,
    db: Session = Depends(get_db),
    cert_service: CertificateService = Depends(get_cert_service)
    # TODO: Add admin authentication dependency
):
    """
    Generate provisioning codes for device deployment.

    Each code:
    - Is 6 digits numeric
    - Is single-use only
    - Expires after specified hours (default 48h)
    - Is tied to specific device type

    Usage:
    1. Hospital IT generates codes before deployment
    2. Codes are given to field staff
    3. Staff enters code during BLE provisioning
    4. Device uses code to authenticate bootstrap request
    5. Code is marked as used and cannot be reused
    """
    try:
        provisioning_service = BootstrapProvisioningService(db, cert_service)

        codes = provisioning_service.generate_provisioning_codes(
            device_type=request.deviceType,
            count=request.count,
            validity_hours=request.validityHours,
            created_by_staff=None  # TODO: Get from auth context
        )

        return GenerateCodesResponse(codes=codes)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate codes: {str(e)}"
        )


@router.get(
    "/health",
    summary="Health check for bootstrap service",
    description="Verify that certificate service is available and CA certificate can be loaded"
)
async def health_check(cert_service: CertificateService = Depends(get_cert_service)):
    """
    Health check endpoint for bootstrap provisioning service.

    Verifies:
    - CA certificate is accessible
    - Certificate service is initialized
    - Ready to provision devices
    """
    try:
        # Try to access CA cert to verify service is working
        ca_subject = cert_service.ca_cert.subject
        return {
            "status": "healthy",
            "service": "bootstrap_provisioning",
            "ca_loaded": True,
            "ca_issuer": str(ca_subject)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Certificate service unavailable: {str(e)}"
        )
