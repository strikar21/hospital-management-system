"""
ESP32 HMAC-SHA256 Authentication Middleware
Validates device signatures to prevent spoofing attacks

Security Model:
- Factory secret shared across all ESP32 devices (embedded in firmware)
- Each device has unique MAC address (hardware identifier)
- HMAC signature = HMAC-SHA256(secret, MAC + timestamp + endpoint)
- Timestamp validation prevents replay attacks (5-minute window)
"""

import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from fastapi import HTTPException, Header
import logging
import re

logger = logging.getLogger(__name__)


class ESP32HMACAuth:
    """HMAC-based authentication for ESP32 devices"""

    def __init__(self, factory_secret: str, timestamp_window: int = 300):
        """
        Initialize HMAC authenticator

        Args:
            factory_secret: Shared secret key for HMAC computation
            timestamp_window: Maximum age of timestamp in seconds (default: 5 minutes)
        """
        self.factory_secret = factory_secret.encode('utf-8')
        self.timestamp_window = timestamp_window

    def validate_timestamp(self, timestamp_str: str) -> bool:
        """
        Validate timestamp is recent (within allowed window)
        Prevents replay attacks

        Args:
            timestamp_str: ISO 8601 timestamp string

        Returns:
            True if timestamp is valid and recent
        """
        try:
            # Parse ISO 8601 timestamp
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

            # Get current time (UTC)
            now = datetime.now(timezone.utc)

            # Check timestamp is not from future (allow 60 second clock skew)
            if timestamp > now + timedelta(seconds=60):
                logger.warning(f"⚠️ Timestamp from future: {timestamp_str}")
                return False

            # Check timestamp is not too old
            age_seconds = (now - timestamp).total_seconds()
            if age_seconds > self.timestamp_window:
                logger.warning(f"⚠️ Timestamp too old: {timestamp_str} (age: {age_seconds}s)")
                return False

            return True

        except Exception as e:
            logger.warning(f"⚠️ Invalid timestamp format: {timestamp_str} - {e}")
            return False

    def compute_signature(self, mac_address: str, timestamp: str, endpoint: str) -> str:
        """
        Compute HMAC-SHA256 signature for device request

        Args:
            mac_address: Device MAC address (AA:BB:CC:DD:EE:FF)
            timestamp: ISO 8601 timestamp
            endpoint: API endpoint path (e.g., "/api/v1/esp32/vitals")

        Returns:
            Hex-encoded HMAC signature (64 characters)
        """
        # Construct message: MAC + timestamp + endpoint
        message = f"{mac_address}{timestamp}{endpoint}"

        # Compute HMAC-SHA256
        signature = hmac.new(
            self.factory_secret,
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return signature

    def validate_signature(
        self,
        mac_address: str,
        signature: str,
        timestamp: str,
        endpoint: str
    ) -> bool:
        """
        Validate device HMAC signature

        Args:
            mac_address: Device MAC address
            signature: HMAC signature from device
            timestamp: Timestamp from device
            endpoint: API endpoint being accessed

        Returns:
            True if signature is valid
        """
        # Compute expected signature
        expected_signature = self.compute_signature(mac_address, timestamp, endpoint)

        # Constant-time comparison (prevents timing attacks)
        return hmac.compare_digest(signature.lower(), expected_signature.lower())

    def authenticate_device(
        self,
        device_mac: Optional[str],
        device_signature: Optional[str],
        device_timestamp: Optional[str],
        endpoint: str
    ) -> Tuple[bool, str, str]:
        """
        Authenticate ESP32 device request

        Args:
            device_mac: X-Device-MAC header value
            device_signature: X-Device-Signature header value
            device_timestamp: X-Timestamp header value
            endpoint: API endpoint path

        Returns:
            Tuple of (is_valid, mac_address, error_message)
        """
        # Check all required headers present
        if not device_mac:
            return False, "", "Missing X-Device-MAC header"

        if not device_signature:
            return False, device_mac, "Missing X-Device-Signature header"

        if not device_timestamp:
            return False, device_mac, "Missing X-Timestamp header"

        # Validate MAC address format (basic check)
        if not self._validate_mac_format(device_mac):
            return False, device_mac, "Invalid MAC address format"

        # Validate timestamp freshness
        if not self.validate_timestamp(device_timestamp):
            return False, device_mac, "Invalid or expired timestamp"

        # Validate HMAC signature
        if not self.validate_signature(device_mac, device_signature, device_timestamp, endpoint):
            logger.warning(f"❌ Invalid HMAC signature for device {device_mac}")
            return False, device_mac, "Invalid device signature"

        # Authentication successful
        return True, device_mac, ""

    def _validate_mac_format(self, mac: str) -> bool:
        """Validate MAC address format (XX:XX:XX:XX:XX:XX)"""
        pattern = r'^([0-9A-Fa-f]{2}[:]){5}([0-9A-Fa-f]{2})$'
        return bool(re.match(pattern, mac))


# FastAPI dependency for HMAC authentication
async def verify_esp32_hmac(
    device_mac: Optional[str] = Header(None, alias="X-Device-MAC"),
    device_signature: Optional[str] = Header(None, alias="X-Device-Signature"),
    device_timestamp: Optional[str] = Header(None, alias="X-Timestamp"),
    request_path: str = None  # Injected by endpoint
) -> str:
    """
    FastAPI dependency to validate ESP32 HMAC authentication

    Returns:
        Validated MAC address

    Raises:
        HTTPException: If authentication fails
    """
    from ..core.config import settings

    authenticator = ESP32HMACAuth(
        factory_secret=settings.esp32FactorySecret,
        timestamp_window=settings.esp32TimestampWindow
    )

    is_valid, mac_address, error_message = authenticator.authenticate_device(
        device_mac,
        device_signature,
        device_timestamp,
        request_path
    )

    if not is_valid:
        logger.warning(f"❌ ESP32 authentication failed: {error_message} (MAC: {mac_address})")
        raise HTTPException(
            status_code=401,
            detail=f"Device authentication failed: {error_message}"
        )

    logger.info(f"✅ ESP32 authenticated: {mac_address}")
    return mac_address
