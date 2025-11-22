"""
ABDM (Ayushman Bharat Digital Mission) API Client
Real ABDM integration - NOT a mock

Documentation: https://sandbox.abdm.gov.in/docs
API Version: v1, v2 (encrypted)
"""

import httpx
import os
import logging
import base64
from typing import Dict, Optional
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

from app.core.database import getDbConnection

logger = logging.getLogger(__name__)


class AbdmApiClient:
    """
    Real ABDM API Client

    Supports both sandbox and production environments
    """

    # Environment configuration
    SANDBOX_BASE_URL = "https://phrsbx.abdm.gov.in"
    PRODUCTION_BASE_URL = "https://phr.abdm.gov.in"

    # Use sandbox by default (switch to production when ready)
    USE_SANDBOX = os.getenv("ABDM_USE_SANDBOX", "true").lower() == "true"
    BASE_URL = SANDBOX_BASE_URL if USE_SANDBOX else PRODUCTION_BASE_URL

    # ABDM Credentials (from environment variables)
    CLIENT_ID = os.getenv("ABDM_CLIENT_ID", "SBX_002806")  # Replace with your Client ID
    CLIENT_SECRET = os.getenv("ABDM_CLIENT_SECRET", "")  # Replace with your secret

    # Gateway session token (cached)
    _gateway_token: Optional[str] = None
    _gateway_token_expires_at: Optional[datetime] = None

    # Public key for v2 encryption (cached)
    _public_key: Optional[rsa.RSAPublicKey] = None

    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0, verify=True)

    async def _get_gateway_token(self) -> str:
        """
        Get ABDM gateway session token

        The gateway token is required for all ABDM API calls
        Tokens expire after ~30 minutes
        """
        # Return cached token if still valid
        if self._gateway_token and self._gateway_token_expires_at:
            if datetime.utcnow() < self._gateway_token_expires_at:
                return self._gateway_token

        # Get new gateway token
        logger.info("🔄 Fetching new ABDM gateway token...")

        try:
            response = await self.http_client.post(
                f"{self.BASE_URL}/api/v1/auth/session",
                json={
                    "clientId": self.CLIENT_ID,
                    "clientSecret": self.CLIENT_SECRET
                },
                headers={"Content-Type": "application/json"}
            )

            response.raise_for_status()
            data = response.json()

            self._gateway_token = data["accessToken"]
            expires_in = data.get("expiresIn", 1800)  # Default 30 minutes
            self._gateway_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)

            logger.info(f"✅ ABDM gateway token obtained (expires in {expires_in}s)")
            return self._gateway_token

        except httpx.HTTPError as e:
            logger.error(f"❌ Failed to get ABDM gateway token: {e}")
            raise Exception(f"ABDM authentication failed: {str(e)}")

    async def _get_abdm_headers(self) -> Dict[str, str]:
        """Get required headers for ABDM API calls"""
        gateway_token = await self._get_gateway_token()

        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {gateway_token}",
            "X-CM-ID": self.CLIENT_ID
        }

    async def _encrypt_data(self, data: str) -> str:
        """
        Encrypt sensitive data using ABDM public key (for v2 APIs)

        ABDM v2 APIs require encryption of sensitive fields like:
        - Aadhaar number
        - OTP
        - Mobile number
        """
        # TODO: Fetch ABDM public key from /v2/auth/cert endpoint
        # For now, return base64 encoded (switch to encryption when implementing v2)
        return base64.b64encode(data.encode()).decode()

    # ========================================
    # ABHA Authentication APIs (M1)
    # ========================================

    async def init_auth(
        self,
        abha_address: str,
        auth_method: str = "MOBILE_OTP"
    ) -> Dict[str, any]:
        """
        Initialize ABHA authentication (sends OTP)

        Real ABDM Endpoint: POST /v1/auth/init

        Args:
            abha_address: ABHA Address (e.g., rajesh.kumar@abdm)
            auth_method: MOBILE_OTP | AADHAAR_OTP | PASSWORD

        Returns:
            {
                "txnId": "uuid",
                "authMode": "MOBILE_OTP",
                "message": "OTP sent to registered mobile"
            }
        """
        logger.info(f"🔐 Initiating ABDM auth for {abha_address}")

        headers = await self._get_abdm_headers()

        try:
            response = await self.http_client.post(
                f"{self.BASE_URL}/v1/auth/init",
                json={
                    "authMethod": auth_method,
                    "healthid": abha_address
                },
                headers=headers
            )

            response.raise_for_status()
            data = response.json()

            logger.info(f"✅ ABDM OTP sent for {abha_address}, txnId: {data.get('txnId')}")
            return data

        except httpx.HTTPError as e:
            logger.error(f"❌ ABDM auth init failed: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            raise Exception(f"Failed to send ABHA OTP: {str(e)}")

    async def confirm_otp(
        self,
        txn_id: str,
        otp: str
    ) -> Dict[str, any]:
        """
        Verify OTP and get ABHA auth token

        Real ABDM Endpoint: POST /v1/auth/confirmWithMobileOTP

        Args:
            txn_id: Transaction ID from init_auth
            otp: 6-digit OTP from patient's mobile

        Returns:
            {
                "token": "jwt-token",
                "expiresIn": 1800,
                "refreshToken": "refresh-token",
                "refreshExpiresIn": 7200,
                "healthIdNumber": "12-3456-7890-1234",
                "healthId": "rajesh.kumar@abdm"
            }
        """
        logger.info(f"🔐 Verifying ABDM OTP for txn: {txn_id}")

        headers = await self._get_abdm_headers()

        try:
            response = await self.http_client.post(
                f"{self.BASE_URL}/v1/auth/confirmWithMobileOTP",
                json={
                    "txnId": txn_id,
                    "otp": otp
                },
                headers=headers
            )

            response.raise_for_status()
            data = response.json()

            logger.info(f"✅ ABDM OTP verified, ABHA: {data.get('healthId')}")
            return data

        except httpx.HTTPError as e:
            logger.error(f"❌ ABDM OTP verification failed: {e}")
            if hasattr(e, 'response') and e.response:
                error_data = e.response.json() if e.response.text else {}
                error_message = error_data.get('message', str(e))
                logger.error(f"Error: {error_message}")
                raise ValueError(error_message)
            raise Exception(f"Failed to verify ABHA OTP: {str(e)}")

    async def refresh_token(
        self,
        refresh_token: str
    ) -> Dict[str, any]:
        """
        Refresh expired ABHA auth token

        Real ABDM Endpoint: POST /v1/auth/refreshToken

        Args:
            refresh_token: Refresh token from previous auth

        Returns:
            {
                "token": "new-jwt-token",
                "expiresIn": 1800,
                "refreshToken": "new-refresh-token",
                "refreshExpiresIn": 7200
            }
        """
        headers = await self._get_abdm_headers()

        try:
            response = await self.http_client.post(
                f"{self.BASE_URL}/v1/auth/refreshToken",
                json={"refreshToken": refresh_token},
                headers=headers
            )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"❌ ABDM token refresh failed: {e}")
            raise Exception(f"Failed to refresh ABHA token: {str(e)}")

    # ========================================
    # ABHA Profile APIs
    # ========================================

    async def get_abha_profile(
        self,
        auth_token: str
    ) -> Dict[str, any]:
        """
        Get ABHA user profile

        Real ABDM Endpoint: GET /v1/account/profile

        Args:
            auth_token: User's ABHA auth token

        Returns:
            {
                "healthIdNumber": "12-3456-7890-1234",
                "healthId": "rajesh.kumar@abdm",
                "mobile": "9876543210",
                "firstName": "Rajesh",
                "lastName": "Kumar",
                "gender": "M",
                "yearOfBirth": "1985",
                ...
            }
        """
        headers = await self._get_abdm_headers()
        headers["X-Token"] = f"Bearer {auth_token}"

        try:
            response = await self.http_client.get(
                f"{self.BASE_URL}/v1/account/profile",
                headers=headers
            )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"❌ Failed to get ABHA profile: {e}")
            raise Exception(f"Failed to get ABHA profile: {str(e)}")

    # ========================================
    # Helper Methods
    # ========================================

    async def link_abha_to_patient(
        self,
        patient_id: str,
        abha_data: Dict[str, any],
        auth_token: str,
        refresh_token: str
    ) -> bool:
        """
        Store ABHA session in database after successful OTP verification

        Args:
            patient_id: Internal HMS patient ID
            abha_data: Data from confirm_otp response
            auth_token: ABHA auth token
            refresh_token: ABHA refresh token

        Returns:
            True if successful
        """
        async with getDbConnection() as conn:
            # Calculate token expiry
            expires_in = abha_data.get('expiresIn', 1800)
            token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            # Upsert ABHA session
            await conn.execute("""
                INSERT INTO abha_sessions (
                    "patientId", "abhaNumber", "abhaAddress",
                    "authToken", "refreshToken", "tokenExpiresAt",
                    status, "otpVerifiedAt", "linkedAt"
                ) VALUES ($1, $2, $3, $4, $5, $6, 'active', NOW(), NOW())
                ON CONFLICT ("patientId")
                WHERE status = 'active'
                DO UPDATE SET
                    "abhaNumber" = EXCLUDED."abhaNumber",
                    "abhaAddress" = EXCLUDED."abhaAddress",
                    "authToken" = EXCLUDED."authToken",
                    "refreshToken" = EXCLUDED."refreshToken",
                    "tokenExpiresAt" = EXCLUDED."tokenExpiresAt",
                    "otpVerifiedAt" = NOW(),
                    "updatedAt" = NOW()
            """,
                patient_id,
                abha_data.get('healthIdNumber'),  # 14-digit ABHA number
                abha_data.get('healthId'),  # ABHA address (username@abdm)
                auth_token,
                refresh_token,
                token_expires_at
            )

            logger.info(f"✅ ABHA session linked for patient {patient_id}")
            return True

    async def get_active_session(
        self,
        patient_id: str
    ) -> Optional[Dict[str, any]]:
        """
        Get active ABHA session for patient

        Returns None if no active session or token expired
        """
        async with getDbConnection() as conn:
            session = await conn.fetchrow("""
                SELECT "patientId", "abhaNumber", "abhaAddress",
                       "authToken", "refreshToken", "tokenExpiresAt",
                       status, "linkedAt", "lastPushAt"
                FROM abha_sessions
                WHERE "patientId" = $1
                  AND status = 'active'
                ORDER BY "linkedAt" DESC
                LIMIT 1
            """, patient_id)

            if not session:
                return None

            # Check if token expired
            if session['tokenExpiresAt'] and datetime.utcnow() > session['tokenExpiresAt']:
                # Try to refresh token
                try:
                    new_tokens = await self.refresh_token(session['refreshToken'])

                    # Update session with new tokens
                    expires_in = new_tokens.get('expiresIn', 1800)
                    new_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

                    await conn.execute("""
                        UPDATE abha_sessions
                        SET "authToken" = $1,
                            "refreshToken" = $2,
                            "tokenExpiresAt" = $3
                        WHERE "patientId" = $4
                    """,
                        new_tokens['token'],
                        new_tokens['refreshToken'],
                        new_expires_at,
                        patient_id
                    )

                    # Refresh session data
                    session = dict(session)
                    session['authToken'] = new_tokens['token']
                    session['tokenExpiresAt'] = new_expires_at

                    logger.info(f"✅ ABHA token refreshed for patient {patient_id}")

                except Exception as e:
                    logger.error(f"❌ Failed to refresh ABHA token: {e}")
                    # Mark session as expired
                    await conn.execute("""
                        UPDATE abha_sessions
                        SET status = 'expired'
                        WHERE "patientId" = $1
                    """, patient_id)
                    return None

            return dict(session)

    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()


# Singleton instance
abdm_client = AbdmApiClient()
