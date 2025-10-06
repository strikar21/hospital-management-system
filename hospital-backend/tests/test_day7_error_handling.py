"""
Day 7: Error Handling Tests
Tests custom exceptions, error responses, and error handling throughout the system
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.exceptions import (
    BaseAppException,
    ValidationException,
    NotFoundException,
    PermissionDeniedException,
    DatabaseException,
    ConflictException,
    BusinessRuleException,
    AuthenticationException,
    ExternalServiceException,
    RateLimitException,
    DataIntegrityException
)
from app.models.error_response import ErrorResponse, ErrorDetail, SuccessResponse


class TestDay7ErrorHandling:
    """Test suite for Day 7 error handling implementation"""

    # ==============================================
    # TEST 1-10: Custom Exception Classes
    # ==============================================

    def test_validation_exception(self):
        """Test 1: ValidationException creates proper 400 error"""
        print("\nTest 1: ValidationException [RUNNING]")

        exc = ValidationException("Invalid dosage", field="dosage")

        assert exc.message == "Invalid dosage"
        assert exc.status_code == 400
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.details.get("field") == "dosage"

        print("[PASS] Test 1: ValidationException")
        return True

    def test_not_found_exception(self):
        """Test 2: NotFoundException creates proper 404 error"""
        print("\nTest 2: NotFoundException [RUNNING]")

        exc = NotFoundException("Patient", "PAT0001")

        assert "PAT0001" in exc.message
        assert "Patient" in exc.message
        assert exc.status_code == 404
        assert exc.error_code == "NOT_FOUND"
        assert exc.details.get("resourceId") == "PAT0001"

        print("[PASS] Test 2: NotFoundException")
        return True

    def test_permission_denied_exception(self):
        """Test 3: PermissionDeniedException creates proper 403 error"""
        print("\nTest 3: PermissionDeniedException [RUNNING]")

        exc = PermissionDeniedException("Cannot edit note", required_role="doctor")

        assert exc.message == "Cannot edit note"
        assert exc.status_code == 403
        assert exc.error_code == "PERMISSION_DENIED"
        assert exc.details.get("requiredRole") == "doctor"

        print("[PASS] Test 3: PermissionDeniedException")
        return True

    def test_database_exception(self):
        """Test 4: DatabaseException creates proper 500 error with sanitized message"""
        print("\nTest 4: DatabaseException [RUNNING]")

        original_error = "duplicate key value violates unique constraint 'patients_pkey'"
        exc = DatabaseException("insert patient", original_error)

        # User-facing message should be generic (security)
        assert "Database operation failed" in exc.message
        assert "patients_pkey" not in exc.message  # No schema details leaked

        # Original error stored for logging
        assert exc.original_error == original_error
        assert exc.status_code == 500
        assert exc.error_code == "DATABASE_ERROR"

        print("[PASS] Test 4: DatabaseException")
        return True

    def test_conflict_exception(self):
        """Test 5: ConflictException creates proper 409 error"""
        print("\nTest 5: ConflictException [RUNNING]")

        exc = ConflictException("Patient ID already exists", resource="Patient")

        assert exc.message == "Patient ID already exists"
        assert exc.status_code == 409
        assert exc.error_code == "CONFLICT"
        assert exc.details.get("resource") == "Patient"

        print("[PASS] Test 5: ConflictException")
        return True

    def test_business_rule_exception(self):
        """Test 6: BusinessRuleException creates proper 422 error"""
        print("\nTest 6: BusinessRuleException [RUNNING]")

        exc = BusinessRuleException(
            "Cannot discharge critical patient",
            rule="no_critical_discharge"
        )

        assert exc.message == "Cannot discharge critical patient"
        assert exc.status_code == 422
        assert exc.error_code == "BUSINESS_RULE_VIOLATION"
        assert exc.details.get("rule") == "no_critical_discharge"

        print("[PASS] Test 6: BusinessRuleException")
        return True

    def test_authentication_exception(self):
        """Test 7: AuthenticationException creates proper 401 error"""
        print("\nTest 7: AuthenticationException [RUNNING]")

        exc = AuthenticationException("Invalid credentials")

        assert exc.message == "Invalid credentials"
        assert exc.status_code == 401
        assert exc.error_code == "AUTHENTICATION_FAILED"

        print("[PASS] Test 7: AuthenticationException")
        return True

    def test_rate_limit_exception(self):
        """Test 8: RateLimitException creates proper 429 error"""
        print("\nTest 8: RateLimitException [RUNNING]")

        exc = RateLimitException("Too many requests", retry_after=60)

        assert exc.message == "Too many requests"
        assert exc.status_code == 429
        assert exc.error_code == "RATE_LIMIT_EXCEEDED"
        assert exc.details.get("retryAfter") == 60

        print("[PASS] Test 8: RateLimitException")
        return True

    def test_exception_to_dict(self):
        """Test 9: Exception to_dict() method works"""
        print("\nTest 9: Exception to_dict() [RUNNING]")

        exc = ValidationException("Invalid input", field="dosage")
        exc_dict = exc.to_dict()

        assert exc_dict["errorCode"] == "VALIDATION_ERROR"
        assert exc_dict["message"] == "Invalid input"
        assert exc_dict["statusCode"] == 400
        assert "field" in exc_dict["details"]

        print("[PASS] Test 9: Exception to_dict()")
        return True

    def test_base_app_exception(self):
        """Test 10: BaseAppException can be used directly"""
        print("\nTest 10: BaseAppException [RUNNING]")

        exc = BaseAppException(
            message="Custom error",
            status_code=418,
            error_code="CUSTOM_ERROR",
            details={"custom": "data"}
        )

        assert exc.message == "Custom error"
        assert exc.status_code == 418
        assert exc.error_code == "CUSTOM_ERROR"
        assert exc.details.get("custom") == "data"

        print("[PASS] Test 10: BaseAppException")
        return True

    # ==============================================
    # TEST 11-15: Error Response Models
    # ==============================================

    def test_error_detail_model(self):
        """Test 11: ErrorDetail model validates correctly"""
        print("\nTest 11: ErrorDetail model [RUNNING]")

        detail = ErrorDetail(
            field="dosage",
            message="Dosage must be positive",
            errorCode="INVALID_DOSAGE",
            value="-500mg"
        )

        assert detail.field == "dosage"
        assert detail.message == "Dosage must be positive"
        assert detail.errorCode == "INVALID_DOSAGE"
        assert detail.value == "-500mg"

        print("[PASS] Test 11: ErrorDetail model")
        return True

    def test_error_response_model(self):
        """Test 12: ErrorResponse model validates correctly"""
        print("\nTest 12: ErrorResponse model [RUNNING]")

        error_response = ErrorResponse(
            errorCode="VALIDATION_ERROR",
            message="Input validation failed",
            statusCode=422,
            path="/api/v2/medications/patient/PAT0001",
            details=[
                ErrorDetail(field="dosage", message="Dosage must be positive")
            ]
        )

        assert error_response.success is False
        assert error_response.errorCode == "VALIDATION_ERROR"
        assert error_response.message == "Input validation failed"
        assert error_response.statusCode == 422
        assert error_response.path == "/api/v2/medications/patient/PAT0001"
        assert len(error_response.details) == 1
        assert error_response.timestamp is not None  # Auto-generated

        print("[PASS] Test 12: ErrorResponse model [PASS]")
        return True

    def test_error_response_serialization(self):
        """Test 13: ErrorResponse can be serialized to JSON"""
        print("\nTest 13: ErrorResponse serialization [RUNNING]")

        error_response = ErrorResponse(
            errorCode="NOT_FOUND",
            message="Patient not found",
            statusCode=404
        )

        # Serialize to dict (for JSON response)
        response_dict = error_response.model_dump(exclude_none=True)

        assert response_dict["success"] is False
        assert response_dict["errorCode"] == "NOT_FOUND"
        assert response_dict["message"] == "Patient not found"
        assert "timestamp" in response_dict

        print("[PASS] Test 13: ErrorResponse serialization [PASS]")
        return True

    def test_success_response_model(self):
        """Test 14: SuccessResponse model validates correctly"""
        print("\nTest 14: SuccessResponse model [RUNNING]")

        success_response = SuccessResponse(
            message="Patient discharged successfully",
            data={"patientId": "PAT0001"}
        )

        assert success_response.success is True
        assert success_response.message == "Patient discharged successfully"
        assert success_response.data.get("patientId") == "PAT0001"
        assert success_response.timestamp is not None

        print("[PASS] Test 14: SuccessResponse model [PASS]")
        return True

    def test_error_response_without_details(self):
        """Test 15: ErrorResponse works without details field"""
        print("\nTest 15: ErrorResponse without details [RUNNING]")

        error_response = ErrorResponse(
            errorCode="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
            statusCode=500
        )

        # Should work without details
        response_dict = error_response.model_dump(exclude_none=True)

        assert "details" not in response_dict  # Excluded when None
        assert response_dict["errorCode"] == "INTERNAL_SERVER_ERROR"

        print("[PASS] Test 15: ErrorResponse without details [PASS]")
        return True

    # ==============================================
    # TEST 16-20: Secure Error Messages
    # ==============================================

    def test_database_error_sanitization(self):
        """Test 16: Database errors don't leak schema details"""
        print("\nTest 16: Database error sanitization [RUNNING]")

        # Simulate database error with schema details
        original_error = """
        ERROR: duplicate key value violates unique constraint "patients_pkey"
        DETAIL: Key (id)=(PAT0001) already exists.
        """

        exc = DatabaseException("create patient", original_error)

        # User-facing message should be generic
        assert "patients_pkey" not in exc.message
        assert "constraint" not in exc.message.lower()
        assert "duplicate key" not in exc.message.lower()
        assert "Database operation failed" in exc.message

        # Original error is stored but NOT in message
        assert "patients_pkey" in exc.original_error

        print("[PASS] Test 16: Database error sanitization [PASS]")
        return True

    def test_sql_not_in_error_message(self):
        """Test 17: SQL queries not exposed in error messages"""
        print("\nTest 17: SQL not in error messages [RUNNING]")

        original_error = """
        ERROR: syntax error at or near "SELECT"
        LINE 1: SELECT * FROM patients WHERE id = $1 INVALIDD
        """

        exc = DatabaseException("query patients", original_error)

        # SQL should NOT be in user-facing message
        assert "SELECT" not in exc.message
        assert "FROM patients" not in exc.message
        assert "Database operation failed" in exc.message

        print("[PASS] Test 17: SQL not in error messages [PASS]")
        return True

    def test_stack_trace_not_in_error(self):
        """Test 18: Stack traces not exposed to users"""
        print("\nTest 18: Stack traces not exposed [RUNNING]")

        # ErrorResponse doesn't include stack traces by default
        error_response = ErrorResponse(
            errorCode="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
            statusCode=500
        )

        response_dict = error_response.model_dump()

        # No stack trace fields
        assert "stackTrace" not in response_dict
        assert "traceback" not in response_dict

        print("[PASS] Test 18: Stack traces not exposed [PASS]")
        return True

    def test_generic_database_error_message(self):
        """Test 19: Generic database errors use safe messages"""
        print("\nTest 19: Generic database error messages [RUNNING]")

        exc = DatabaseException("unknown operation", "Some internal database error")

        # Should use generic message
        assert "Database operation failed" in exc.message
        assert "try again later" in exc.message.lower()
        assert "internal database error" not in exc.message

        print("[PASS] Test 19: Generic database error messages [PASS]")
        return True

    def test_error_code_consistency(self):
        """Test 20: Error codes are consistent and machine-readable"""
        print("\nTest 20: Error code consistency [RUNNING]")

        # All error codes should be uppercase with underscores
        exceptions = [
            ValidationException("test"),
            NotFoundException("Patient", "PAT001"),
            PermissionDeniedException(),
            DatabaseException("test", "error"),
            ConflictException("test"),
            BusinessRuleException("test"),
            AuthenticationException(),
            RateLimitException()
        ]

        for exc in exceptions:
            # Error codes should be uppercase
            assert exc.error_code.isupper()
            # Should contain underscores (not spaces or dashes)
            assert " " not in exc.error_code
            assert "-" not in exc.error_code

        print("[PASS] Test 20: Error code consistency [PASS]")
        return True


def run_all_tests():
    """Run all Day 7 error handling tests"""
    print("=" * 60)
    print("DAY 7 ERROR HANDLING TESTS - COMPREHENSIVE TEST SUITE")
    print("=" * 60)

    test_suite = TestDay7ErrorHandling()

    # Get all test methods
    test_methods = [
        method for method in dir(test_suite)
        if method.startswith('test_') and callable(getattr(test_suite, method))
    ]

    passed = 0
    failed = 0
    errors = []

    # Run each test
    for test_name in sorted(test_methods):
        try:
            test_method = getattr(test_suite, test_name)
            result = test_method()
            if result:
                passed += 1
            else:
                failed += 1
                errors.append(f"{test_name}: Test returned False")
        except AssertionError as e:
            failed += 1
            errors.append(f"{test_name}: {str(e)}")
            print(f"[FAIL] {test_name}: {str(e)}")
        except Exception as e:
            failed += 1
            errors.append(f"{test_name}: {str(e)}")
            print(f"[ERROR] {test_name}: {str(e)}")

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {len(test_methods)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/len(test_methods)*100):.1f}%")

    if failed > 0:
        print("\n[FAILED TESTS]:")
        for error in errors:
            print(f"  - {error}")
        print("\n[FAIL] Some tests failed")
        return False
    else:
        print("\n[PASS] ALL TESTS PASSED (20/20)")
        print("Day 7 error handling is working correctly!")
        return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
