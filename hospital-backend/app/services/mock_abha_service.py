"""
Mock ABHA/ABDM OTP Service
Purpose: Simulate ABDM API for testing (until sandbox credentials are available)
"""

import secrets
import string
from datetime import datetime, timedelta
from typing import Dict, Optional
import asyncpg
from app.core.database import getDbConnection
import logging

logger = logging.getLogger(__name__)

class MockAbhaService:
    """
    Mock ABHA OTP service for testing

    In production, this will be replaced with real ABDM API calls
    """

    # In-memory OTP storage (for mock testing)
    _otp_store: Dict[str, Dict[str, any]] = {}

    @classmethod
    async def send_otp(cls, patient_id: str, abha_number: str) -> Dict[str, any]:
        """
        Send OTP to ABHA-registered mobile

        Args:
            patient_id: Patient ID (e.g., PAT0001)
            abha_number: 14-digit ABHA number (with or without hyphens)

        Returns:
            {
                "txnId": "abc123-def456",
                "message": "OTP sent to XXXX1234",
                "expiresIn": 300  # seconds
            }

        Mock Behavior:
            - Generates random 6-digit OTP
            - Stores in memory for verification
            - In production: Calls ABDM API POST /v0.5/users/auth/init
        """

        # Clean ABHA number (remove hyphens)
        abha_clean = abha_number.replace('-', '').replace(' ', '')

        # Generate transaction ID
        txn_id = cls._generate_txn_id()

        # Generate 6-digit OTP
        otp = cls._generate_otp()

        # Store OTP (expires in 5 minutes)
        cls._otp_store[txn_id] = {
            'otp': otp,
            'abhaNumber': abha_clean,
            'patientId': patient_id,
            'expiresAt': datetime.utcnow() + timedelta(minutes=5),
            'attempts': 0
        }

        # Get patient phone number (for display)
        async with getDbConnection() as conn:
            phone = await conn.fetchval("""
                SELECT "phoneNumber"
                FROM patients
                WHERE id = $1
            """, patient_id)

        masked_phone = cls._mask_phone(phone) if phone else "XXXX1234"

        logger.info(f"[MOCK ABHA] OTP sent for {patient_id} ({abha_number})")
        logger.info(f"[MOCK ABHA] Transaction ID: {txn_id}")
        logger.info(f"[MOCK ABHA] OTP: {otp} (FOR TESTING ONLY)")

        # Update abha_sessions with txnId
        async with getDbConnection() as conn:
            await conn.execute("""
                UPDATE abha_sessions
                SET "otpTxnId" = $1,
                    "otpSentAt" = NOW(),
                    status = 'pending'
                WHERE "patientId" = $2
                  AND "abhaNumber" = $3
            """, txn_id, patient_id, abha_clean)

        return {
            'txnId': txn_id,
            'message': f'OTP sent to {masked_phone}',
            'expiresIn': 300,
            'mockOtp': otp  # ONLY for testing! Remove in production
        }

    @classmethod
    async def verify_otp(
        cls,
        txn_id: str,
        otp: str,
        patient_id: str
    ) -> Dict[str, any]:
        """
        Verify OTP and activate ABHA session

        Args:
            txn_id: Transaction ID from send_otp
            otp: 6-digit OTP entered by user
            patient_id: Patient ID for validation

        Returns:
            {
                "status": "verified",
                "authToken": "mock-jwt-token-abc123",
                "expiresIn": 1800
            }

        Raises:
            ValueError: If OTP is invalid, expired, or too many attempts

        Mock Behavior:
            - Checks OTP against stored value
            - Marks session as 'active'
            - In production: Calls ABDM API POST /v0.5/users/auth/confirm
        """

        # Check if txnId exists
        if txn_id not in cls._otp_store:
            raise ValueError('Invalid or expired transaction ID')

        otp_data = cls._otp_store[txn_id]

        # Check expiry
        if datetime.utcnow() > otp_data['expiresAt']:
            del cls._otp_store[txn_id]
            raise ValueError('OTP expired. Please request a new OTP')

        # Check attempts (max 3)
        if otp_data['attempts'] >= 3:
            del cls._otp_store[txn_id]
            raise ValueError('Too many invalid attempts. Please request a new OTP')

        # Verify OTP
        if otp != otp_data['otp']:
            cls._otp_store[txn_id]['attempts'] += 1
            remaining = 3 - cls._otp_store[txn_id]['attempts']
            raise ValueError(f'Invalid OTP. {remaining} attempts remaining')

        # Verify patient ID matches
        if patient_id != otp_data['patientId']:
            raise ValueError('Patient ID mismatch')

        # Generate mock auth token
        auth_token = cls._generate_auth_token()
        refresh_token = cls._generate_refresh_token()
        expires_at = datetime.utcnow() + timedelta(minutes=30)

        # Update abha_sessions
        async with getDbConnection() as conn:
            await conn.execute("""
                UPDATE abha_sessions
                SET status = 'active',
                    "authToken" = $1,
                    "refreshToken" = $2,
                    "tokenExpiresAt" = $3,
                    "otpVerifiedAt" = NOW(),
                    "lastVerifiedAt" = NOW()
                WHERE "otpTxnId" = $4
                  AND "patientId" = $5
            """, auth_token, refresh_token, expires_at, txn_id, patient_id)

        # Clean up OTP store
        del cls._otp_store[txn_id]

        logger.info(f"[MOCK ABHA] OTP verified for {patient_id}")
        logger.info(f"[MOCK ABHA] Session activated")

        return {
            'status': 'verified',
            'authToken': auth_token,
            'refreshToken': refresh_token,
            'expiresIn': 1800  # 30 minutes
        }

    @classmethod
    async def get_active_session(cls, patient_id: str) -> Optional[Dict[str, any]]:
        """
        Get active ABHA session for patient

        Args:
            patient_id: Patient ID

        Returns:
            Session data or None if no active session
        """
        async with getDbConnection() as conn:
            session = await conn.fetchrow("""
                SELECT "patientId", "abhaNumber", "abhaAddress",
                       "authToken", "tokenExpiresAt", status, "linkedAt"
                FROM abha_sessions
                WHERE "patientId" = $1
                  AND status = 'active'
                  AND "tokenExpiresAt" > NOW()
                ORDER BY "linkedAt" DESC
                LIMIT 1
            """, patient_id)

        return dict(session) if session else None

    @staticmethod
    def _generate_txn_id() -> str:
        """Generate mock transaction ID"""
        return f"TXN-{''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16))}"

    @staticmethod
    def _generate_otp() -> str:
        """Generate 6-digit OTP"""
        return ''.join(secrets.choice(string.digits) for _ in range(6))

    @staticmethod
    def _generate_auth_token() -> str:
        """Generate mock JWT auth token"""
        return f"MOCK-AUTH-{''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))}"

    @staticmethod
    def _generate_refresh_token() -> str:
        """Generate mock refresh token"""
        return f"MOCK-REFRESH-{''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))}"

    @staticmethod
    def _mask_phone(phone: str) -> str:
        """Mask phone number for display"""
        if not phone:
            return "XXXX1234"

        # Remove non-digits
        digits = ''.join(c for c in phone if c.isdigit())

        if len(digits) >= 4:
            return f"XXXX{digits[-4:]}"
        return "XXXX1234"


# Singleton instance
mock_abha_service = MockAbhaService()
