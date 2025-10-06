"""
Day 5 Authentication Tests - JWT Token Generation and Validation
Tests JWT authentication flow, token refresh, and protected endpoints
"""

# CRITICAL: Set environment variables FIRST, before any other imports
# Note: Pydantic BaseSettings expects UPPERCASE env var names
import os
os.environ['DATABASEURL'] = 'postgresql://test:test@localhost:5432/test_db'
os.environ['DATABASEPASSWORD'] = 'test_password_for_testing'
os.environ['TIMESCALEDBURL'] = 'postgresql://test:test@localhost:5432/test_timescale'
os.environ['TIMESCALEDBPASSWORD'] = 'test_password_for_testing'
os.environ['SECRETKEY'] = 'test-secret-key-minimum-32-characters-long-for-jwt-signing'

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.jwt_handler import create_access_token, create_refresh_token, verify_token, decode_token, get_user_from_token
from app.core.config_secure import settings
from jose import jwt
from datetime import datetime, timedelta


class TestDay5Authentication:
    """Test Day 5 JWT authentication"""

    def __init__(self):
        self.results = []

    def test_access_token_generation(self):
        """Test: Access token is generated correctly"""
        try:
            token_data = {
                "sub": "DOC0001",
                "role": "Doctor",
                "department": "Cardiology"
            }

            token = create_access_token(data=token_data)

            if not token or len(token) < 50:
                print("[FAIL] Access token too short or empty")
                return False

            # Decode to verify structure
            payload = jwt.decode(token, settings.secretKey, algorithms=[settings.algorithm])

            # Check required fields
            if payload.get("sub") != "DOC0001":
                print(f"[FAIL] Wrong subject: {payload.get('sub')}")
                return False

            if payload.get("role") != "Doctor":
                print(f"[FAIL] Wrong role: {payload.get('role')}")
                return False

            if payload.get("type") != "access":
                print(f"[FAIL] Wrong token type: {payload.get('type')}")
                return False

            if "exp" not in payload:
                print("[FAIL] Missing expiration")
                return False

            if "iat" not in payload:
                print("[FAIL] Missing issued at")
                return False

            print("[PASS] Test PASSED: Access token generated correctly")
            return True

        except Exception as e:
            print(f"[FAIL] Test error: {e}")
            return False

    def test_refresh_token_generation(self):
        """Test: Refresh token is generated correctly"""
        try:
            token_data = {"sub": "DOC0001"}

            token = create_refresh_token(data=token_data)

            if not token or len(token) < 50:
                print("[FAIL] Refresh token too short or empty")
                return False

            # Decode to verify structure
            payload = jwt.decode(token, settings.secretKey, algorithms=[settings.algorithm])

            if payload.get("type") != "refresh":
                print(f"[FAIL] Wrong token type: {payload.get('type')}")
                return False

            # Check expiration is longer (7 days)
            exp_timestamp = payload.get("exp")
            iat_timestamp = payload.get("iat")

            duration = exp_timestamp - iat_timestamp
            expected_duration = 7 * 24 * 60 * 60  # 7 days in seconds

            # Allow 1 minute tolerance
            if abs(duration - expected_duration) > 60:
                print(f"[FAIL] Wrong expiration duration: {duration}s (expected ~{expected_duration}s)")
                return False

            print("[PASS] Test PASSED: Refresh token generated correctly")
            return True

        except Exception as e:
            print(f"[FAIL] Test error: {e}")
            return False

    def test_token_verification(self):
        """Test: Token verification works correctly"""
        try:
            # Create access token
            token_data = {"sub": "DOC0001", "role": "Doctor"}
            token = create_access_token(data=token_data)

            # Verify it
            payload = verify_token(token, token_type="access")

            if payload.get("sub") != "DOC0001":
                print("[FAIL] Verification failed - wrong subject")
                return False

            print("[PASS] Test PASSED: Token verification works")
            return True

        except Exception as e:
            print(f"[FAIL] Test error: {e}")
            return False

    def test_wrong_token_type_rejected(self):
        """Test: Using refresh token as access token is rejected"""
        try:
            # Create refresh token
            token = create_refresh_token(data={"sub": "DOC0001"})

            # Try to verify as access token - should fail
            try:
                verify_token(token, token_type="access")
                print("[FAIL] Should have rejected wrong token type")
                return False
            except Exception:
                # Expected to fail
                print("[PASS] Test PASSED: Wrong token type rejected")
                return True

        except Exception as e:
            print(f"[FAIL] Test error: {e}")
            return False

    def test_expired_token_rejected(self):
        """Test: Expired token is rejected"""
        try:
            # Create token with negative expiration (already expired)
            token_data = {"sub": "DOC0001"}
            expired_token = create_access_token(
                data=token_data,
                expires_delta=timedelta(seconds=-10)
            )

            # Try to verify - should fail
            try:
                verify_token(expired_token, token_type="access")
                print("[FAIL] Should have rejected expired token")
                return False
            except Exception as e:
                # HTTPException has a detail attribute
                error_msg = str(getattr(e, 'detail', str(e))).lower()
                if "expired" in error_msg:
                    print("[PASS] Test PASSED: Expired token rejected")
                    return True
                else:
                    print(f"[FAIL] Wrong error: {error_msg}")
                    return False

        except Exception as e:
            print(f"[FAIL] Test error: {e}")
            return False

    def test_invalid_token_rejected(self):
        """Test: Invalid/tampered token is rejected"""
        try:
            # Create valid token
            token = create_access_token(data={"sub": "DOC0001"})

            # Tamper with it
            tampered_token = token[:-10] + "TAMPERED!!"

            # Try to verify - should fail
            try:
                decode_token(tampered_token)
                print("[FAIL] Should have rejected tampered token")
                return False
            except Exception:
                print("[PASS] Test PASSED: Invalid token rejected")
                return True

        except Exception as e:
            print(f"[FAIL] Test error: {e}")
            return False

    def test_user_extraction(self):
        """Test: User info is correctly extracted from token"""
        try:
            token_data = {
                "sub": "DOC0001",
                "role": "Doctor",
                "department": "Cardiology",
                "permissions": ["read", "write"]
            }

            token = create_access_token(data=token_data)
            user_info = get_user_from_token(token)

            if user_info.get("id") != "DOC0001":
                print(f"[FAIL] Wrong user ID: {user_info.get('id')}")
                return False

            if user_info.get("role") != "Doctor":
                print(f"[FAIL] Wrong role: {user_info.get('role')}")
                return False

            if user_info.get("department") != "Cardiology":
                print(f"[FAIL] Wrong department: {user_info.get('department')}")
                return False

            print("[PASS] Test PASSED: User info extracted correctly")
            return True

        except Exception as e:
            print(f"[FAIL] Test error: {e}")
            return False

    def run_all_tests(self):
        """Run all Day 5 tests"""
        print("\n" + "=" * 60)
        print("DAY 5 AUTHENTICATION TESTS - JWT TOKENS")
        print("=" * 60 + "\n")

        print("--- Testing Token Generation ---")
        print("\nTest 1: Access Token Generation")
        test1 = self.test_access_token_generation()

        print("\nTest 2: Refresh Token Generation")
        test2 = self.test_refresh_token_generation()

        print("\n--- Testing Token Validation ---")
        print("\nTest 3: Token Verification")
        test3 = self.test_token_verification()

        print("\nTest 4: Wrong Token Type Rejection")
        test4 = self.test_wrong_token_type_rejected()

        print("\nTest 5: Expired Token Rejection")
        test5 = self.test_expired_token_rejected()

        print("\nTest 6: Invalid Token Rejection")
        test6 = self.test_invalid_token_rejected()

        print("\nTest 7: User Info Extraction")
        test7 = self.test_user_extraction()

        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        all_passed = all([test1, test2, test3, test4, test5, test6, test7])

        if all_passed:
            print("[PASS] ALL TESTS PASSED")
            print("\nDay 5 JWT authentication is working correctly!")
            print("Tokens are being generated, validated, and secured properly.")
        else:
            print("[FAIL] SOME TESTS FAILED")
            print("\nPlease review the failures above.")

        print("=" * 60 + "\n")

        return all_passed


def main():
    """Main test runner"""
    tester = TestDay5Authentication()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
