"""
Device Provisioning API - Certificate-Based Authentication
Manages one-time provisioning codes and device certificate issuance
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta, timezone
import secrets
import string
import logging

from app.core.auth_dependencies import get_current_user, RoleChecker
from app.core.database import getDbConnection

logger = logging.getLogger(__name__)

router = APIRouter()

# =====================================================
# REQUEST/RESPONSE MODELS
# =====================================================

class GenerateCodeRequest(BaseModel):
    """Request model for generating a provisioning code"""
    validityMinutes: int = Field(default=10, ge=1, le=60, description="Code validity in minutes (1-60)")

    model_config = {"json_schema_extra": {
        "example": {
            "validityMinutes": 10
        }
    }}


class ProvisioningCodeResponse(BaseModel):
    """Response model for provisioning code generation"""
    code: str = Field(..., description="6-digit numeric PIN code")
    expiresAt: str = Field(..., description="ISO 8601 timestamp when code expires")
    validityMinutes: int = Field(..., description="Validity period in minutes")
    technicianId: str = Field(..., description="ID of technician who generated the code")

    model_config = {"json_schema_extra": {
        "example": {
            "code": "ABC123XYZ789DEFG",
            "expiresAt": "2025-10-17T15:10:00Z",
            "validityMinutes": 10,
            "technicianId": "TECH001"
        }
    }}


class ProvisionDeviceRequest(BaseModel):
    """Request model for device provisioning (from ESP32)"""
    code: str = Field(..., min_length=6, max_length=6, description="Provisioning code from technician")
    deviceId: str = Field(..., min_length=1, max_length=50, description="Unique device identifier")
    macAddress: str = Field(..., pattern=r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", description="Device MAC address")
    serialNumber: Optional[str] = Field(None, max_length=50, description="Device serial number (optional)")

    model_config = {"json_schema_extra": {
        "example": {
            "code": "ABC123XYZ789DEFG",
            "deviceId": "ESP32-WATCH-001",
            "macAddress": "AA:BB:CC:DD:EE:FF",
            "serialNumber": "SN12345678"
        }
    }}


class DeviceCertificateResponse(BaseModel):
    """Response model for device certificate issuance"""
    deviceId: str = Field(..., description="Device identifier")
    certificatePem: str = Field(..., description="PEM-encoded X.509 certificate")
    privateKeyPem: str = Field(..., description="PEM-encoded private key (send to device ONCE)")
    caCertificatePem: str = Field(..., description="PEM-encoded Hospital CA certificate (for TLS verification)")
    expiresAt: str = Field(..., description="Certificate expiration timestamp")
    message: str = Field(..., description="Success message")

    model_config = {"json_schema_extra": {
        "example": {
            "deviceId": "ESP32-WATCH-001",
            "certificatePem": "-----BEGIN CERTIFICATE-----\n...",
            "privateKeyPem": "-----BEGIN RSA PRIVATE KEY-----\n...",
            "caCertificatePem": "-----BEGIN CERTIFICATE-----\n...",
            "expiresAt": "2026-10-17T15:00:00Z",
            "message": "Device provisioned successfully"
        }
    }}


class RevokeDeviceRequest(BaseModel):
    """Request model for certificate revocation"""
    reason: str = Field(..., min_length=10, max_length=500, description="Reason for revocation")

    model_config = {"json_schema_extra": {
        "example": {
            "reason": "Device stolen from ward 3 on 2025-10-15"
        }
    }}


class ProvisioningCodeListResponse(BaseModel):
    """Response model for listing provisioning codes"""
    codes: List[dict] = Field(..., description="List of provisioning codes")
    total: int = Field(..., description="Total number of codes")


# =====================================================
# ENDPOINT 1: GENERATE PROVISIONING CODE
# =====================================================

@router.post("/generate-code", response_model=ProvisioningCodeResponse)
async def generate_provisioning_code(
    request: GenerateCodeRequest,
    current_user: dict = Depends(RoleChecker(["Administrator", "Technician"]))
):
    """
    Generate a one-time provisioning code for device setup

    **Authorization:** Administrator or Technician only

    **Workflow:**
    1. IT staff generates a provisioning code via this endpoint
    2. Code is valid for specified minutes (default: 10)
    3. Technician enters code on ESP32 captive portal
    4. ESP32 uses code to request certificate from /provision-with-certificate

    **Security:**
    - Code expires after specified time (1-60 minutes)
    - Code can only be used once
    - Audit trail: tracks which technician generated each code
    """
    try:
        # Generate random 16-character alphanumeric code
        # Generate 6-digit numeric PIN
        code = ''.join(secrets.choice(string.digits) for _ in range(6))

        # Calculate expiration time
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=request.validityMinutes)

        # Store code in database
        async with getDbConnection() as conn:
            await conn.execute(
                """
                INSERT INTO provisioning_codes (code, technician_id, expires_at)
                VALUES ($1, $2, $3)
                """,
                code,
                current_user["id"],
                expires_at
            )

        logger.info(f"✅ Provisioning code generated by {current_user['id']}: {code} (expires at {expires_at})")

        return ProvisioningCodeResponse(
            code=code,
            expiresAt=expires_at.isoformat(),  # Already includes timezone info
            validityMinutes=request.validityMinutes,
            technicianId=current_user["id"]
        )

    except Exception as e:
        logger.error(f"❌ Error generating provisioning code: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate provisioning code: {str(e)}"
        )


# =====================================================
# ENDPOINT 2: PROVISION DEVICE WITH CERTIFICATE
# =====================================================

@router.post("/provision-with-certificate", response_model=DeviceCertificateResponse)
async def provision_device_with_certificate(
    request: ProvisionDeviceRequest,
    fastapi_request: Request
):
    """
    Provision a device by issuing an X.509 certificate (called by ESP32)

    **Authorization:** No JWT required (uses one-time provisioning code instead)

    **Workflow:**
    1. ESP32 submits provisioning code + device info
    2. Backend validates code (not used, not expired)
    3. Backend checks if device exists in devices table
    4. Backend generates X.509 certificate signed by Hospital CA
    5. Backend stores certificate metadata in device_certificates table
    6. Backend marks code as used
    7. Backend returns certificate + private key to ESP32
    8. ESP32 saves certificate to SPIFFS and connects to MQTT

    **Security:**
    - Code must be valid (not expired, not used)
    - Device must exist in devices table
    - Certificate includes device_id in Common Name
    - Private key is NOT stored in database (only sent to device once)
    """
    try:
        async with getDbConnection() as conn:
            # Step 1: Validate provisioning code
            code_row = await conn.fetchrow(
                """
                SELECT code, technician_id, expires_at, used, device_id
                FROM provisioning_codes
                WHERE code = $1
                """,
                request.code
            )

            if not code_row:
                logger.warning(f"❌ Invalid provisioning code attempted: {request.code}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid provisioning code"
                )

            # Check if code is already used
            if code_row["used"]:
                logger.warning(f"❌ Already-used provisioning code attempted: {request.code}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Provisioning code has already been used"
                )

            # Check if code is expired
            # Make both datetimes timezone-aware for comparison
            expires_at_aware = code_row["expires_at"].replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_at_aware:
                logger.warning(f"❌ Expired provisioning code attempted: {request.code}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Provisioning code has expired"
                )

            # Step 2: Assign sequential device ID based on MAC address
            # Check if MAC already has an assigned device ID
            mac_mapping = await conn.fetchrow(
                'SELECT device_id FROM device_mac_mapping WHERE mac_address = $1',
                request.macAddress
            )

            if mac_mapping:
                # MAC already mapped - use existing device ID
                device_id_to_use = mac_mapping["device_id"]
                logger.info(f"📍 MAC {request.macAddress} already mapped to {device_id_to_use}")
            else:
                # Generate new sequential device ID
                # Extract device type from request.deviceId (ESP32-WATCH-* → fit, ESP32-DOOR-* → door)
                if "WATCH" in request.deviceId.upper():
                    device_type = "fit"
                    device_name_prefix = "Fit Watch"
                elif "DOOR" in request.deviceId.upper():
                    device_type = "door"
                    device_name_prefix = "Door Scanner"
                else:
                    device_type = "device"
                    device_name_prefix = "Device"

                # Get next sequence number for this type
                last_device = await conn.fetchrow(
                    "SELECT id FROM devices WHERE id LIKE $1 ORDER BY id DESC LIMIT 1",
                    f"{device_type}-%"
                )

                if last_device:
                    # Extract number from "fit-00123" → 123
                    last_num = int(last_device["id"].split("-")[1])
                    next_num = last_num + 1
                else:
                    next_num = 1

                # Format: fit-00001
                device_id_to_use = f"{device_type}-{next_num:05d}"

                logger.info(f"🆕 Assigning new device ID: {device_id_to_use} for MAC {request.macAddress}")

                # Create device record
                await conn.execute(
                    '''INSERT INTO devices
                       (id, name, "deviceType", "serialNumber", status, "createdAt", "updatedAt")
                       VALUES ($1, $2, $3, $4, $5, NOW(), NOW())''',
                    device_id_to_use,
                    f"{device_name_prefix} {next_num:05d}",
                    "watch" if device_type == "fit" else "door",
                    request.serialNumber or f"SN-{request.macAddress}",
                    "available"
                )

                # Store MAC → Device ID mapping
                await conn.execute(
                    "INSERT INTO device_mac_mapping (mac_address, device_id) VALUES ($1, $2)",
                    request.macAddress,
                    device_id_to_use
                )

                logger.info(f"✅ Device {device_id_to_use} created and mapped to MAC {request.macAddress}")

            # Step 3: Check certificate status (for logging only - ON CONFLICT handles re-provisioning)
            existing_cert = await conn.fetchrow(
                'SELECT id, revoked FROM device_certificates WHERE device_id = $1',
                device_id_to_use
            )

            if existing_cert and not existing_cert["revoked"]:
                logger.info(f"♻️  Re-provisioning device {device_id_to_use} (replacing existing certificate)")
            elif existing_cert and existing_cert["revoked"]:
                logger.info(f"🔄 Re-provisioning device {device_id_to_use} (previous certificate was revoked)")
            else:
                logger.info(f"🆕 First-time provisioning for device {device_id_to_use}")

            # Step 4: Generate device certificate using CertificateService
            certificate_service = fastapi_request.app.state.certificate_service

            certificate_pem, private_key_pem = certificate_service.generate_device_certificate(
                device_id=device_id_to_use,  # Use backend-assigned ID (fit-00001)
                mac_address=request.macAddress,
                validity_days=365
            )

            # Calculate certificate expiration
            cert_expires_at = datetime.now(timezone.utc) + timedelta(days=365)

            # Step 5: Store certificate metadata in database
            await conn.execute(
                """
                INSERT INTO device_certificates
                (device_id, certificate_pem, expires_at, mac_address, serial_number)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (device_id)
                DO UPDATE SET
                    certificate_pem = EXCLUDED.certificate_pem,
                    expires_at = EXCLUDED.expires_at,
                    mac_address = EXCLUDED.mac_address,
                    serial_number = EXCLUDED.serial_number,
                    issued_at = NOW(),
                    revoked = false,
                    revoked_at = NULL,
                    revoked_by = NULL,
                    revocation_reason = NULL
                """,
                device_id_to_use,
                certificate_pem,
                cert_expires_at,
                request.macAddress,
                request.serialNumber
            )

            # Step 6: Mark provisioning code as used
            await conn.execute(
                """
                UPDATE provisioning_codes
                SET used = true, used_at = NOW(), device_id = $1
                WHERE code = $2
                """,
                device_id_to_use,
                request.code
            )

            # Step 7: Load Hospital CA certificate to send to device
            import os
            ca_cert_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "..", "mosquitto", "certs", "hospital_ca.crt"
            )
            with open(ca_cert_path, 'r') as f:
                ca_certificate_pem = f.read()

            logger.info(f"✅ Device {device_id_to_use} provisioned successfully with certificate")
            logger.info(f"   Technician: {code_row['technician_id']}, MAC: {request.macAddress}")

            return DeviceCertificateResponse(
                deviceId=device_id_to_use,  # Return backend-assigned ID (fit-00001)
                certificatePem=certificate_pem,
                privateKeyPem=private_key_pem,
                caCertificatePem=ca_certificate_pem,
                expiresAt=cert_expires_at.isoformat() + "Z",
                message="Device provisioned successfully. Save certificate and private key to SPIFFS."
            )

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"❌ Error provisioning device: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to provision device: {str(e)}"
        )


# =====================================================
# ENDPOINT 3: REVOKE DEVICE CERTIFICATE
# =====================================================

@router.post("/revoke-certificate/{device_id}")
async def revoke_device_certificate(
    device_id: str,
    request: RevokeDeviceRequest,
    current_user: dict = Depends(RoleChecker(["Administrator", "Technician"]))
):
    """
    Revoke a device certificate (for stolen/compromised devices)

    **Authorization:** Administrator or Technician only

    **Workflow:**
    1. IT staff calls this endpoint with device_id and reason
    2. Backend marks certificate as revoked in database
    3. Mosquitto will reject future connections from this device
    4. Device can be re-provisioned with a new certificate

    **Use Cases:**
    - Device stolen from hospital premises
    - Device compromised or tampered with
    - Device firmware corrupted
    - Device being decommissioned
    """
    try:
        async with getDbConnection() as conn:
            # Check if certificate exists
            cert_row = await conn.fetchrow(
                'SELECT id, revoked FROM device_certificates WHERE device_id = $1',
                device_id
            )

            if not cert_row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No certificate found for device {device_id}"
                )

            if cert_row["revoked"]:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Certificate for device {device_id} is already revoked"
                )

            # Revoke certificate
            await conn.execute(
                """
                UPDATE device_certificates
                SET revoked = true,
                    revoked_at = NOW(),
                    revoked_by = $1,
                    revocation_reason = $2
                WHERE device_id = $3
                """,
                current_user["id"],
                request.reason,
                device_id
            )

            logger.warning(f"⚠️ Certificate revoked for device {device_id}")
            logger.warning(f"   Revoked by: {current_user['id']}, Reason: {request.reason}")

            return {
                "status": "success",
                "message": f"Certificate for device {device_id} revoked successfully",
                "deviceId": device_id,
                "revokedBy": current_user["id"],
                "revokedAt": datetime.now(timezone.utc).isoformat() + "Z",
                "reason": request.reason
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error revoking certificate: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke certificate: {str(e)}"
        )


# =====================================================
# ENDPOINT 4: LIST PROVISIONING CODES
# =====================================================

@router.get("/codes", response_model=ProvisioningCodeListResponse)
async def list_provisioning_codes(
    current_user: dict = Depends(RoleChecker(["Administrator", "Technician"])),
    limit: int = 50
):
    """
    List recent provisioning codes (for audit trail)

    **Authorization:** Administrator or Technician only

    **Returns:**
    - Last 50 provisioning codes (default)
    - Shows which codes are used/expired
    - Shows which technician generated each code
    """
    try:
        async with getDbConnection() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    code,
                    technician_id,
                    created_at,
                    expires_at,
                    used,
                    used_at,
                    device_id
                FROM provisioning_codes
                ORDER BY created_at DESC
                LIMIT $1
                """,
                limit
            )

            codes = []
            for row in rows:
                code_dict = dict(row)
                # Add computed fields
                now = datetime.now(timezone.utc)
                # Make expires_at timezone-aware for comparison
                expires_at_aware = code_dict["expires_at"].replace(tzinfo=timezone.utc)
                code_dict["isExpired"] = now > expires_at_aware
                code_dict["status"] = (
                    "used" if code_dict["used"]
                    else "expired" if code_dict["isExpired"]
                    else "active"
                )
                # Convert timestamps to ISO strings
                code_dict["createdAt"] = code_dict.pop("created_at").isoformat() + "Z"
                code_dict["expiresAt"] = code_dict.pop("expires_at").isoformat() + "Z"
                code_dict["usedAt"] = code_dict.pop("used_at").isoformat() + "Z" if code_dict["used_at"] else None
                code_dict["technicianId"] = code_dict.pop("technician_id")
                code_dict["deviceId"] = code_dict.pop("device_id")

                codes.append(code_dict)

            return ProvisioningCodeListResponse(
                codes=codes,
                total=len(codes)
            )

    except Exception as e:
        logger.error(f"❌ Error listing provisioning codes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list provisioning codes: {str(e)}"
        )
