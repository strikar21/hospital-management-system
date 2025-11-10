"""
Phase 1 Foundation Components - Quick Verification Tests

Tests the basic functionality of:
1. Centralized Error Classes
2. Database Decorators
3. Standardized API Response Models

Run: python -m pytest test_phase1_foundation.py -v
"""

import pytest
import asyncio
from datetime import datetime

# Test Error Classes
from app.core.errors import (
    PatientNotFoundError,
    ValidationError,
    DeviceAlreadyAssignedError,
    DatabaseError
)

# Test Database Decorators
from app.core.db_decorators import with_retry, execute_with_retry

# Test API Response Models
from app.models.api_response import (
    SuccessResponse,
    ListResponse,
    ErrorResponse,
    create_success_response,
    create_list_response,
    create_error_response
)


# ================================
# ERROR CLASS TESTS
# ================================

def test_patient_not_found_error():
    """Test PatientNotFoundError creates proper error structure"""
    error = PatientNotFoundError(patient_id="PAT123")

    assert error.status_code == 404
    assert error.error_code == "PATIENT_NOT_FOUND"
    assert "PAT123" in error.message
    assert error.details["patient_id"] == "PAT123"


def test_validation_error():
    """Test ValidationError with field information"""
    error = ValidationError("Invalid email format", field="email")

    assert error.status_code == 400
    assert error.error_code == "VALIDATION_ERROR"
    assert error.details["field"] == "email"


def test_device_already_assigned_error():
    """Test DeviceAlreadyAssignedError with conflict details"""
    error = DeviceAlreadyAssignedError(
        device_id="DEV001",
        current_patient_id="PAT456"
    )

    assert error.status_code == 409
    assert error.error_code == "DEVICE_ALREADY_ASSIGNED"
    assert error.details["device_id"] == "DEV001"
    assert error.details["current_patient_id"] == "PAT456"


def test_database_error():
    """Test DatabaseError with operation context"""
    error = DatabaseError(message="Connection timeout", operation="get_patient")

    assert error.status_code == 500
    assert error.error_code == "DATABASE_ERROR"
    assert error.details["operation"] == "get_patient"


# ================================
# DATABASE DECORATOR TESTS
# ================================

@pytest.mark.asyncio
async def test_with_retry_success_first_attempt():
    """Test @with_retry succeeds on first attempt"""
    call_count = 0

    @with_retry(max_attempts=3, base_delay=0.1)
    async def successful_operation():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await successful_operation()

    assert result == "success"
    assert call_count == 1


@pytest.mark.asyncio
async def test_with_retry_success_after_failures():
    """Test @with_retry succeeds after 2 failures"""
    call_count = 0

    @with_retry(max_attempts=3, base_delay=0.1)
    async def flaky_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Temporary failure")
        return "success"

    result = await flaky_operation()

    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_with_retry_max_attempts_exceeded():
    """Test @with_retry raises DatabaseError after max attempts"""
    call_count = 0

    @with_retry(max_attempts=3, base_delay=0.1)
    async def failing_operation():
        nonlocal call_count
        call_count += 1
        raise Exception("Persistent failure")

    with pytest.raises(DatabaseError) as exc_info:
        await failing_operation()

    assert call_count == 3
    assert "failed after 3 attempts" in str(exc_info.value.message)


@pytest.mark.asyncio
async def test_execute_with_retry():
    """Test execute_with_retry utility function"""
    call_count = 0

    async def operation():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise Exception("Temporary failure")
        return "success"

    result = await execute_with_retry(operation, max_attempts=3, base_delay=0.1)

    assert result == "success"
    assert call_count == 2


# ================================
# API RESPONSE MODEL TESTS
# ================================

def test_success_response_model():
    """Test SuccessResponse Pydantic model"""
    response = SuccessResponse(
        data={"id": "PAT123", "firstName": "John"},
        message="Patient retrieved successfully"
    )

    assert response.success is True
    assert response.data["id"] == "PAT123"
    assert response.message == "Patient retrieved successfully"
    assert isinstance(response.meta.timestamp, datetime)


def test_list_response_model():
    """Test ListResponse Pydantic model"""
    patients = [
        {"id": "PAT123", "firstName": "John"},
        {"id": "PAT124", "firstName": "Jane"}
    ]

    response = ListResponse(
        data=patients,
        total=100,
        count=2,
        limit=10,
        offset=0,
        hasMore=True
    )

    assert response.success is True
    assert len(response.data) == 2
    assert response.total == 100
    assert response.count == 2
    assert response.hasMore is True


def test_error_response_model():
    """Test ErrorResponse Pydantic model"""
    from app.models.api_response import ErrorDetails

    error_details = ErrorDetails(
        code="PATIENT_NOT_FOUND",
        message="Patient 'PAT123' not found",
        details={"patient_id": "PAT123"}
    )

    response = ErrorResponse(error=error_details)

    assert response.success is False
    assert response.error.code == "PATIENT_NOT_FOUND"
    assert response.error.details["patient_id"] == "PAT123"


def test_create_success_response_helper():
    """Test create_success_response utility function"""
    response = create_success_response(
        data={"id": "PAT123"},
        message="Success"
    )

    assert response["success"] is True
    assert response["data"]["id"] == "PAT123"
    assert response["message"] == "Success"
    assert "meta" in response
    assert "timestamp" in response["meta"]


def test_create_list_response_helper():
    """Test create_list_response utility function"""
    data = [{"id": "PAT123"}, {"id": "PAT124"}]

    response = create_list_response(
        data=data,
        total=100,
        limit=10,
        offset=0
    )

    assert response["success"] is True
    assert response["count"] == 2
    assert response["total"] == 100
    assert response["hasMore"] is True


def test_create_error_response_helper():
    """Test create_error_response utility function"""
    response = create_error_response(
        code="VALIDATION_ERROR",
        message="Invalid input",
        details={"field": "email"}
    )

    assert response["success"] is False
    assert response["error"]["code"] == "VALIDATION_ERROR"
    assert response["error"]["details"]["field"] == "email"


# ================================
# INTEGRATION TESTS
# ================================

def test_error_to_response_conversion():
    """Test converting error to response format"""
    error = PatientNotFoundError(patient_id="PAT123")

    # Simulate what error_handler.py does
    response = create_error_response(
        code=error.error_code,
        message=error.message,
        details=error.details
    )

    assert response["success"] is False
    assert response["error"]["code"] == "PATIENT_NOT_FOUND"
    assert response["error"]["details"]["patient_id"] == "PAT123"


def test_response_model_serialization():
    """Test that response models can be serialized to JSON"""
    response = SuccessResponse(
        data={"id": "PAT123", "firstName": "John"}
    )

    # Convert to dict (FastAPI does this automatically)
    response_dict = response.model_dump()

    assert response_dict["success"] is True
    assert response_dict["data"]["id"] == "PAT123"
    assert "meta" in response_dict


# ================================
# RUN TESTS
# ================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
