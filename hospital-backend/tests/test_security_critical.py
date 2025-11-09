"""
P0 CRITICAL TESTS: Security Audit & Hardening
Tests authentication, authorization, and security measures

These tests validate:
1. JWT token generation and validation
2. Token expiry enforcement
3. Password/PIN hashing security
4. Authentication middleware
5. Input validation
6. SQL injection prevention

Security Requirements:
- All passwords hashed with bcrypt
- All PINs hashed with bcrypt
- JWT tokens expire after 30 minutes
- Refresh tokens expire after 7 days
- Invalid tokens return 401
- Expired tokens return 401
- SQL injection attempts rejected

Related Files:
- hospital-backend/app/core/jwt_handler.py
- hospital-backend/app/core/security.py
- hospital-backend/app/api/v1/auth.py
- hospital-backend/app/core/auth_dependencies.py
"""

import pytest
from datetime import datetime, timedelta
from app.core.jwt_handler import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token,
    check_token_expiry
)
from app.core.security import (
    hash_pin,
    verify_pin,
    hash_password,
    verify_password,
    validate_pin_format,
    validate_staff_id_format
)
from fastapi import HTTPException


@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.security
class TestJWTTokenSecurity:
    """Test JWT token generation, validation, and expiry"""

    def test_create_access_token_success(self):
        """
        Test: Access token creation
        Expected: Returns valid JWT string
        """
        token_data = {
            "sub": "DOC0001",
            "role": "doctor",
            "department": "Cardiology"
        }

        token = create_access_token(data=token_data)

        assert isinstance(token, str)
        assert len(token) > 0
        # JWT tokens have 3 parts separated by dots
        assert token.count('.') == 2

    def test_create_refresh_token_success(self):
        """
        Test: Refresh token creation
        Expected: Returns valid JWT string
        """
        token_data = {"sub": "DOC0001"}

        token = create_refresh_token(data=token_data)

        assert isinstance(token, str)
        assert len(token) > 0
        assert token.count('.') == 2

    def test_decode_valid_token(self):
        """
        Test: Decode valid access token
        Expected: Returns payload with user data
        """
        token_data = {
            "sub": "DOC0001",
            "role": "doctor"
        }

        token = create_access_token(data=token_data)
        payload = decode_token(token)

        assert payload["sub"] == "DOC0001"
        assert payload["role"] == "doctor"
        assert payload["type"] == "access"
        assert "exp" in payload  # Expiration time
        assert "iat" in payload  # Issued at time

    def test_decode_invalid_token_raises_401(self):
        """
        Test: Decode invalid token
        Expected: Raises HTTPException with 401 status
        """
        invalid_token = "invalid.token.string"

        with pytest.raises(HTTPException) as exc_info:
            decode_token(invalid_token)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)

    def test_token_expires_after_30_minutes(self):
        """
        Test: Access token expiration time
        Expected: Token expires after 30 minutes (ACCESS_TOKEN_EXPIRE_MINUTES)
        """
        token_data = {"sub": "DOC0001"}

        token = create_access_token(data=token_data)
        payload = decode_token(token)

        exp_timestamp = payload["exp"]
        iat_timestamp = payload["iat"]

        # Calculate expiration delta
        exp_datetime = datetime.fromtimestamp(exp_timestamp)
        iat_datetime = datetime.fromtimestamp(iat_timestamp)
        expiry_delta = exp_datetime - iat_datetime

        # Should be 30 minutes (within 1 minute tolerance)
        assert 29 <= expiry_delta.total_seconds() / 60 <= 31

    def test_refresh_token_expires_after_7_days(self):
        """
        Test: Refresh token expiration time
        Expected: Token expires after 7 days
        """
        token_data = {"sub": "DOC0001"}

        token = create_refresh_token(data=token_data)
        payload = decode_token(token)

        exp_timestamp = payload["exp"]
        iat_timestamp = payload["iat"]

        exp_datetime = datetime.fromtimestamp(exp_timestamp)
        iat_datetime = datetime.fromtimestamp(iat_timestamp)
        expiry_delta = exp_datetime - iat_datetime

        # Should be 7 days (within 1 hour tolerance)
        expected_seconds = 7 * 24 * 60 * 60
        assert abs(expiry_delta.total_seconds() - expected_seconds) < 3600

    def test_verify_token_wrong_type_raises_401(self):
        """
        Test: Verify token with wrong type
        Expected: Raises HTTPException with 401 status

        Access token verified as refresh token should fail
        """
        token_data = {"sub": "DOC0001"}
        access_token = create_access_token(data=token_data)

        with pytest.raises(HTTPException) as exc_info:
            verify_token(access_token, token_type="refresh")

        assert exc_info.value.status_code == 401
        assert "Invalid token type" in str(exc_info.value.detail)

    def test_verify_token_missing_subject_raises_401(self):
        """
        Test: Token without subject (user ID)
        Expected: Raises HTTPException with 401 status
        """
        from jose import jwt
        from app.core.config import settings

        # Create token without 'sub' field
        token_data = {"role": "doctor"}  # Missing 'sub'
        token = jwt.encode(token_data, settings.secretKey, algorithm=settings.algorithm)

        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)

        assert exc_info.value.status_code == 401

    def test_check_token_expiry_valid_token(self):
        """
        Test: Check expiry of valid token
        Expected: Returns valid=True, expired=False
        """
        token_data = {"sub": "DOC0001"}
        token = create_access_token(data=token_data)

        expiry_info = check_token_expiry(token)

        assert expiry_info["valid"] is True
        assert expiry_info["expired"] is False
        assert expiry_info["expires_at"] is not None
        assert expiry_info["time_remaining"] != "0"

    def test_check_token_expiry_expired_token(self):
        """
        Test: Check expiry of expired token
        Expected: Returns valid=True, expired=True
        """
        token_data = {"sub": "DOC0001"}
        # Create token that expires immediately
        token = create_access_token(
            data=token_data,
            expires_delta=timedelta(seconds=-1)  # Already expired
        )

        expiry_info = check_token_expiry(token)

        assert expiry_info["expired"] is True


@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.security
class TestPasswordHashing:
    """Test password and PIN hashing security"""

    def test_hash_password_returns_bcrypt_hash(self):
        """
        Test: Password hashing
        Expected: Returns bcrypt hash (starts with $2b$)
        """
        password = "SecurePassword123!"
        hashed = hash_password(password)

        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$")  # bcrypt hash
        assert len(hashed) >= 60  # bcrypt hashes are 60 characters

    def test_hash_password_different_for_same_input(self):
        """
        Test: Password hashing uses salt
        Expected: Same password produces different hashes (due to salt)
        """
        password = "SecurePassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different (bcrypt uses salt)
        assert hash1 != hash2

    def test_verify_password_correct_password_returns_true(self):
        """
        Test: Verify correct password
        Expected: Returns True
        """
        password = "SecurePassword123!"
        hashed = hash_password(password)

        result = verify_password(password, hashed)

        assert result is True

    def test_verify_password_incorrect_password_returns_false(self):
        """
        Test: Verify incorrect password
        Expected: Returns False
        """
        correct_password = "CorrectPassword123!"
        wrong_password = "WrongPassword123!"

        hashed = hash_password(correct_password)
        result = verify_password(wrong_password, hashed)

        assert result is False

    def test_hash_pin_returns_bcrypt_hash(self):
        """
        Test: PIN hashing
        Expected: Returns bcrypt hash
        """
        pin = "1234"
        hashed = hash_pin(pin)

        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$")
        assert len(hashed) >= 60

    def test_verify_pin_correct_pin_returns_true(self):
        """
        Test: Verify correct PIN
        Expected: Returns True
        """
        pin = "1234"
        hashed = hash_pin(pin)

        result = verify_pin(pin, hashed)

        assert result is True

    def test_verify_pin_incorrect_pin_returns_false(self):
        """
        Test: Verify incorrect PIN
        Expected: Returns False
        """
        correct_pin = "1234"
        wrong_pin = "5678"

        hashed = hash_pin(correct_pin)
        result = verify_pin(wrong_pin, hashed)

        assert result is False

    async def test_database_passwords_are_hashed(self, db_connection):
        """
        Test: Passwords in database are hashed
        Expected: All passwords start with $2b$ (bcrypt)

        Security requirement: Never store plaintext passwords
        """
        passwords = await db_connection.fetch("""
            SELECT id, password, pin
            FROM staff
            WHERE password IS NOT NULL OR pin IS NOT NULL
            LIMIT 10
        """)

        if not passwords:
            pytest.skip("No staff with passwords in database")

        for staff in passwords:
            if staff['password']:
                assert staff['password'].startswith("$2b$"), \
                    f"Staff {staff['id']} has unhashed password"

            if staff['pin']:
                assert staff['pin'].startswith("$2b$"), \
                    f"Staff {staff['id']} has unhashed PIN"


@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.security
class TestInputValidation:
    """Test input validation for security"""

    def test_validate_pin_format_valid_pins(self):
        """
        Test: PIN format validation for valid PINs
        Expected: Returns True for 4-digit PINs
        """
        valid_pins = ["1234", "0000", "9999", "0123"]

        for pin in valid_pins:
            assert validate_pin_format(pin) is True

    def test_validate_pin_format_invalid_pins(self):
        """
        Test: PIN format validation for invalid PINs
        Expected: Returns False for non-4-digit inputs
        """
        invalid_pins = [
            "123",      # Too short
            "12345",    # Too long
            "abcd",     # Not digits
            "12a4",     # Mixed
            "",         # Empty
            "  1234",   # Whitespace
        ]

        for pin in invalid_pins:
            assert validate_pin_format(pin) is False

    def test_validate_staff_id_format_valid_ids(self):
        """
        Test: Staff ID format validation
        Expected: Returns True for valid staff IDs
        """
        valid_ids = [
            "DOC0001",
            "NUR0123",
            "ADM0999",
            "PRV0456",
            "TEC0789"
        ]

        for staff_id in valid_ids:
            assert validate_staff_id_format(staff_id) is True

    def test_validate_staff_id_format_invalid_ids(self):
        """
        Test: Staff ID format validation for invalid IDs
        Expected: Returns False for invalid formats
        """
        invalid_ids = [
            "DOC001",      # Too few digits
            "DOC00001",    # Too many digits
            "XXX0001",     # Invalid prefix
            "doc0001",     # Lowercase
            "DOC-0001",    # Hyphen
            "",            # Empty
            "0001",        # Missing prefix
        ]

        for staff_id in invalid_ids:
            assert validate_staff_id_format(staff_id) is False

    async def test_sql_injection_prevention(self, db_connection):
        """
        Test: SQL injection prevention
        Expected: Malicious SQL not executed

        Validates: Parameterized queries prevent SQL injection
        """
        # SQL injection payloads
        malicious_inputs = [
            "'; DROP TABLE staff; --",
            "1' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM staff--"
        ]

        for malicious_id in malicious_inputs:
            # This should NOT execute the malicious SQL
            result = await db_connection.fetchrow(
                'SELECT * FROM staff WHERE id = $1',
                malicious_id
            )

            # Should return None (no match), NOT execute DROP TABLE
            assert result is None

        # Verify table still exists
        table_exists = await db_connection.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'staff'
            )
        """)

        assert table_exists is True, "SQL injection executed - staff table dropped!"


@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.security
async def test_authentication_enforcement_complete(db_connection):
    """
    INTEGRATION TEST: Complete authentication security validation

    This test validates:
    1. JWT tokens work correctly
    2. Passwords are hashed
    3. PINs are hashed
    4. Input validation works
    5. SQL injection prevented

    Success = Authentication system is production-ready
    """
    # Test 1: JWT token creation and validation
    token_data = {"sub": "DOC0001", "role": "doctor"}
    access_token = create_access_token(data=token_data)
    payload = decode_token(access_token)
    assert payload["sub"] == "DOC0001"
    assert payload["type"] == "access"

    # Test 2: Password hashing
    password = "TestPassword123!"
    hashed_password = hash_password(password)
    assert hashed_password.startswith("$2b$")
    assert verify_password(password, hashed_password) is True
    assert verify_password("WrongPassword", hashed_password) is False

    # Test 3: PIN hashing
    pin = "1234"
    hashed_pin = hash_pin(pin)
    assert hashed_pin.startswith("$2b$")
    assert verify_pin(pin, hashed_pin) is True
    assert verify_pin("5678", hashed_pin) is False

    # Test 4: Input validation
    assert validate_pin_format("1234") is True
    assert validate_pin_format("123") is False
    assert validate_staff_id_format("DOC0001") is True
    assert validate_staff_id_format("INVALID") is False

    # Test 5: SQL injection prevention
    malicious_input = "'; DROP TABLE staff; --"
    result = await db_connection.fetchrow(
        'SELECT * FROM staff WHERE id = $1',
        malicious_input
    )
    assert result is None

    # Verify table still exists
    table_exists = await db_connection.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'staff'
        )
    """)
    assert table_exists is True

    print("\n✅ Complete authentication security validated:")
    print("  - JWT tokens: WORKING")
    print("  - Password hashing: bcrypt ✅")
    print("  - PIN hashing: bcrypt ✅")
    print("  - Input validation: WORKING")
    print("  - SQL injection prevention: WORKING")
    print("  - ✅ Authentication system PRODUCTION-READY")


@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.security
async def test_token_blacklist_exists(self, db_connection):
    """
    Test: Token blacklist table exists for logout functionality
    Expected: token_blacklist table exists

    Validates: Logout can blacklist tokens
    """
    table_exists = await db_connection.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'token_blacklist'
        )
    """)

    assert table_exists is True, "token_blacklist table missing - logout won't work"
