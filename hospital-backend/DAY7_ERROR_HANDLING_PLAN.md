# Day 7: Comprehensive Error Handling - Implementation Plan

**Date:** 2025-10-05
**Status:** In Progress
**Goal:** Implement production-ready error handling across the entire backend system

---

## Executive Summary

Day 7 focuses on implementing comprehensive error handling to ensure the backend provides:
- **Structured error responses** for frontend consumption
- **Custom exception classes** for different error types
- **Global exception handlers** to catch all errors
- **Secure error messages** that don't leak sensitive data
- **Comprehensive error logging** for debugging and monitoring

### Current State Analysis

**What exists:**
- Basic try-catch blocks in some service methods
- Generic exception logging with `logger.error()`
- HTTPException usage in some endpoints
- No structured error responses
- No custom exception types
- No global exception handlers
- Inconsistent error handling across services

**What's missing:**
- Custom exception hierarchy
- Structured error response models
- Global exception handlers
- Consistent error handling in all services
- Error logging with context (user, operation, etc.)
- Secure error sanitization
- Database error handling
- Validation error formatting

---

## Implementation Plan

### Phase 1: Custom Exception Classes

**File:** `app/core/exceptions.py`

Create exception hierarchy:

```python
class BaseAppException(Exception):
    """Base exception for all app exceptions"""
    def __init__(self, message: str, status_code: int = 500, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)

class ValidationException(BaseAppException):
    """Validation error (400)"""
    def __init__(self, message: str):
        super().__init__(message, status_code=400, error_code="VALIDATION_ERROR")

class NotFoundException(BaseAppException):
    """Resource not found (404)"""
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            f"{resource} with ID {resource_id} not found",
            status_code=404,
            error_code="NOT_FOUND"
        )

class PermissionDeniedException(BaseAppException):
    """Permission denied (403)"""
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, status_code=403, error_code="PERMISSION_DENIED")

class DatabaseException(BaseAppException):
    """Database operation error (500)"""
    def __init__(self, message: str):
        super().__init__(
            "Database operation failed",
            status_code=500,
            error_code="DATABASE_ERROR"
        )
        self.original_message = message  # Store for logging, not user

class ConflictException(BaseAppException):
    """Resource conflict (409)"""
    def __init__(self, message: str):
        super().__init__(message, status_code=409, error_code="CONFLICT")

class BusinessRuleException(BaseAppException):
    """Business rule violation (422)"""
    def __init__(self, message: str):
        super().__init__(message, status_code=422, error_code="BUSINESS_RULE_VIOLATION")
```

**Exception Types:**
1. `ValidationException` - Input validation failures (400)
2. `NotFoundException` - Resource not found (404)
3. `PermissionDeniedException` - Authorization failures (403)
4. `DatabaseException` - Database errors (500)
5. `ConflictException` - Resource conflicts (409)
6. `BusinessRuleException` - Business logic violations (422)

---

### Phase 2: Error Response Models

**File:** `app/models/error_response.py`

Create Pydantic models for structured error responses:

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime

class ErrorDetail(BaseModel):
    """Individual error detail"""
    field: Optional[str] = None
    message: str
    errorCode: Optional[str] = None

class ErrorResponse(BaseModel):
    """Standard error response format"""
    success: bool = False
    errorCode: str
    message: str
    details: Optional[List[ErrorDetail]] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    requestId: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "errorCode": "VALIDATION_ERROR",
                "message": "Invalid input data",
                "details": [
                    {
                        "field": "dosage",
                        "message": "Dosage must be positive",
                        "errorCode": "INVALID_DOSAGE"
                    }
                ],
                "timestamp": "2025-10-05T10:30:00Z"
            }
        }
```

**Response Structure:**
- `success`: Always false for errors
- `errorCode`: Machine-readable error code
- `message`: Human-readable error message
- `details`: Array of specific field errors (for validation)
- `timestamp`: When error occurred
- `requestId`: Optional request tracking ID

---

### Phase 3: Global Exception Handlers

**File:** `app/core/error_handlers.py`

Create FastAPI exception handlers:

```python
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import logging
from .exceptions import BaseAppException
from ..models.error_response import ErrorResponse, ErrorDetail

logger = logging.getLogger(__name__)

async def base_app_exception_handler(request: Request, exc: BaseAppException):
    """Handle custom app exceptions"""
    logger.error(
        f"App exception: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "path": request.url.path
        }
    )

    error_response = ErrorResponse(
        errorCode=exc.error_code,
        message=exc.message
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict()
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    # Convert Pydantic errors to our format
    details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        details.append(ErrorDetail(
            field=field,
            message=error["msg"],
            errorCode="VALIDATION_ERROR"
        ))

    error_response = ErrorResponse(
        errorCode="VALIDATION_ERROR",
        message="Input validation failed",
        details=details
    )

    logger.warning(
        f"Validation error on {request.url.path}: {len(details)} errors"
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.dict()
    )

async def database_exception_handler(request: Request, exc: Exception):
    """Handle database exceptions"""
    logger.error(
        f"Database error: {str(exc)}",
        exc_info=True,
        extra={"path": request.url.path}
    )

    # Sanitize database error for user (don't leak schema info)
    error_response = ErrorResponse(
        errorCode="DATABASE_ERROR",
        message="A database error occurred. Please try again later."
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.dict()
    )

async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions"""
    logger.error(
        f"Unhandled exception: {str(exc)}",
        exc_info=True,
        extra={"path": request.url.path}
    )

    error_response = ErrorResponse(
        errorCode="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred. Please try again later."
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.dict()
    )
```

**Handlers:**
1. Custom app exceptions → structured responses
2. Pydantic validation errors → formatted with field details
3. Database exceptions → sanitized (no schema leaks)
4. Generic exceptions → catch-all with logging

---

### Phase 4: Service Layer Error Handling

**Files to Update:**
- `app/services/patient_service.py`
- `app/services/medical_action_service.py`
- `app/services/base_service.py`

**Pattern to implement:**

```python
async def get_patient(self, patient_id: str) -> Dict[str, Any]:
    """Get patient by ID with comprehensive error handling"""
    try:
        # Validate input
        if not patient_id or not patient_id.strip():
            raise ValidationException("Patient ID is required")

        # Check existence
        patient = await self.patient_repository.get_by_id(patient_id)
        if not patient:
            raise NotFoundException("Patient", patient_id)

        # Business logic
        result = self.patient_repository.transform_to_camel_case(patient)
        return result

    except BaseAppException:
        # Re-raise custom exceptions
        raise
    except asyncpg.PostgresError as e:
        # Database errors
        self.logger.error(f"Database error getting patient {patient_id}: {e}")
        raise DatabaseException(str(e))
    except Exception as e:
        # Unexpected errors
        self.logger.error(f"Unexpected error getting patient {patient_id}: {e}")
        raise
```

**Service Method Updates:**
- Wrap all public methods with try-catch
- Use custom exceptions for known error cases
- Convert database exceptions to DatabaseException
- Log with context (patient_id, staff_id, operation)

---

### Phase 5: Error Logging System

**File:** `app/core/logging_config.py`

Create structured logging configuration:

```python
import logging
import sys
from pythonjsonlogger import jsonlogger

def configure_logging():
    """Configure structured JSON logging"""

    # Create JSON formatter
    json_formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s',
        rename_fields={
            'levelname': 'level',
            'asctime': 'timestamp'
        }
    )

    # Console handler with JSON format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    # App-specific logger
    app_logger = logging.getLogger('app')
    app_logger.setLevel(logging.INFO)

    return app_logger
```

**Logging Enhancements:**
- Structured JSON logging
- Context fields (user_id, patient_id, operation)
- Error severity levels
- Stack traces for exceptions
- Request tracking IDs

---

### Phase 6: Update main.py

**File:** `main.py`

Register global exception handlers:

```python
from app.core.error_handlers import (
    base_app_exception_handler,
    validation_exception_handler,
    database_exception_handler,
    generic_exception_handler
)
from app.core.exceptions import BaseAppException
from fastapi.exceptions import RequestValidationError
import asyncpg

# Register exception handlers
app.add_exception_handler(BaseAppException, base_app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(asyncpg.PostgresError, database_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)
```

---

## Testing Strategy

### Test File: `tests/test_day7_error_handling.py`

**Test Cases:**

1. **Custom Exceptions:**
   - ✅ ValidationException returns 400
   - ✅ NotFoundException returns 404
   - ✅ PermissionDeniedException returns 403
   - ✅ DatabaseException returns 500
   - ✅ ConflictException returns 409
   - ✅ BusinessRuleException returns 422

2. **Error Response Format:**
   - ✅ Error response has required fields
   - ✅ Validation errors include field details
   - ✅ Timestamp is ISO format
   - ✅ Error codes are consistent

3. **Global Handlers:**
   - ✅ Pydantic validation errors formatted
   - ✅ Database errors sanitized
   - ✅ Generic exceptions caught
   - ✅ No sensitive data in error messages

4. **Service Layer:**
   - ✅ Empty patient ID raises ValidationException
   - ✅ Non-existent patient raises NotFoundException
   - ✅ Database errors caught and wrapped
   - ✅ Error logging includes context

5. **Secure Error Messages:**
   - ✅ No SQL in error messages
   - ✅ No schema details leaked
   - ✅ No stack traces in production
   - ✅ Generic messages for sensitive errors

**Expected Test Count:** 15-20 comprehensive tests

---

## Security Improvements

### Error Message Sanitization:

**Before (INSECURE):**
```python
# Raw database error exposed
raise Exception(f"INSERT failed: duplicate key value violates unique constraint 'patients_pkey'")
```

**After (SECURE):**
```python
# Sanitized error message
raise ConflictException("A patient with this ID already exists")
```

### Sensitive Data Protection:

**What NOT to include in errors:**
- Database schema details
- SQL queries
- Stack traces (in production)
- User passwords/tokens
- Internal system paths
- IP addresses (unless needed for debugging)

**What TO include:**
- Human-readable error description
- Machine-readable error code
- Field-level validation errors
- Suggested actions (if applicable)

---

## Files to Create

1. ✅ `app/core/exceptions.py` - Custom exception classes
2. ✅ `app/models/error_response.py` - Error response models
3. ✅ `app/core/error_handlers.py` - Global exception handlers
4. ✅ `app/core/logging_config.py` - Structured logging setup
5. ✅ `tests/test_day7_error_handling.py` - Comprehensive tests
6. ✅ `DAY7_COMPLETION_SUMMARY.md` - Documentation

---

## Files to Modify

1. ✅ `main.py` - Register global exception handlers
2. ✅ `app/services/patient_service.py` - Add error handling to all methods
3. ✅ `app/services/medical_action_service.py` - Add error handling to all methods
4. ✅ `app/services/base_service.py` - Add error handling to base methods
5. ✅ `app/repositories/patient_repository.py` - Database error handling

---

## Audit Issues Resolved

### From COMPREHENSIVE_ERROR_DETECTION_AUDIT.md:

**Issue #39: No Structured Error Handling** ✅
- **Original:** Generic exceptions, inconsistent responses
- **Resolution:** Custom exception hierarchy + global handlers
- **Status:** Day 7 target

**Issue #40: Error Messages Leak Sensitive Data** ✅
- **Original:** Raw database errors exposed to users
- **Resolution:** Error message sanitization
- **Status:** Day 7 target

**Issue #42: No Error Logging** ✅
- **Original:** Minimal logging, no context
- **Resolution:** Structured logging with context fields
- **Status:** Day 7 target

---

## Success Criteria

### Day 7 Complete When:

1. ✅ All custom exception classes created and documented
2. ✅ Error response models defined with Pydantic
3. ✅ Global exception handlers registered in main.py
4. ✅ All service methods have proper error handling
5. ✅ Database errors sanitized and wrapped
6. ✅ Structured logging configured
7. ✅ 15-20 error handling tests passing (100%)
8. ✅ No sensitive data in error messages
9. ✅ Documentation complete

---

## Implementation Checklist

### Phase 1: Foundation
- [ ] Create `app/core/exceptions.py`
- [ ] Create `app/models/error_response.py`
- [ ] Create `app/core/error_handlers.py`
- [ ] Create `app/core/logging_config.py`

### Phase 2: Integration
- [ ] Update `main.py` to register handlers
- [ ] Update `app/services/base_service.py`
- [ ] Update `app/services/patient_service.py`
- [ ] Update `app/services/medical_action_service.py`

### Phase 3: Testing
- [ ] Create `tests/test_day7_error_handling.py`
- [ ] Test custom exceptions
- [ ] Test error response format
- [ ] Test global handlers
- [ ] Test service layer error handling
- [ ] Test secure error messages

### Phase 4: Documentation
- [ ] Create `DAY7_COMPLETION_SUMMARY.md`
- [ ] Update `BASELINE_IMPLEMENTATION_PROGRESS.md`

---

## Expected Outcome

**Impact:**
- **Security:** No sensitive data leaked in errors
- **Debugging:** Comprehensive error logging with context
- **Frontend:** Structured, predictable error responses
- **Maintainability:** Consistent error handling patterns
- **Production Readiness:** Proper error handling for all scenarios

**Test Results:** 15-20 tests passing (100%)
**Audit Issues Resolved:** 3 critical issues (#39, #40, #42)
**Production Ready:** Yes - comprehensive error handling complete

---

**Created:** 2025-10-05
**Status:** Plan ready for implementation
**Next Step:** Begin Phase 1 - Create custom exception classes
