"""
Custom Exception Classes for Hospital Management System
Provides structured exception hierarchy for consistent error handling
"""

from typing import Optional, Dict, Any


class BaseAppException(Exception):
    """
    Base exception for all application-specific exceptions

    All custom exceptions inherit from this class to enable
    centralized exception handling
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_SERVER_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response"""
        return {
            "errorCode": self.error_code,
            "message": self.message,
            "statusCode": self.status_code,
            "details": self.details
        }


class ValidationException(BaseAppException):
    """
    Input validation error (HTTP 400)

    Raised when user input fails validation checks
    Examples: empty required fields, invalid formats, out-of-range values
    """

    def __init__(self, message: str, field: Optional[str] = None):
        details = {"field": field} if field else {}
        super().__init__(
            message=message,
            status_code=400,
            error_code="VALIDATION_ERROR",
            details=details
        )


class NotFoundException(BaseAppException):
    """
    Resource not found error (HTTP 404)

    Raised when a requested resource doesn't exist in the database
    Examples: patient not found, staff not found, medication not found
    """

    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            message=f"{resource} with ID '{resource_id}' not found",
            status_code=404,
            error_code="NOT_FOUND",
            details={"resource": resource, "resourceId": resource_id}
        )


class PermissionDeniedException(BaseAppException):
    """
    Permission denied error (HTTP 403)

    Raised when user doesn't have permission to perform an action
    Examples: non-doctor trying to prescribe medication, editing expired notes
    """

    def __init__(self, message: str = "Permission denied", required_role: Optional[str] = None):
        details = {"requiredRole": required_role} if required_role else {}
        super().__init__(
            message=message,
            status_code=403,
            error_code="PERMISSION_DENIED",
            details=details
        )


class DatabaseException(BaseAppException):
    """
    Database operation error (HTTP 500)

    Raised when database operations fail
    Note: Original error message is logged but NOT sent to user (security)
    """

    def __init__(self, operation: str, original_error: Optional[str] = None):
        # User-facing message (generic, safe)
        user_message = f"Database operation failed: {operation}. Please try again later."

        super().__init__(
            message=user_message,
            status_code=500,
            error_code="DATABASE_ERROR",
            details={"operation": operation}
        )

        # Store original error for logging (NOT sent to user)
        self.original_error = original_error


class ConflictException(BaseAppException):
    """
    Resource conflict error (HTTP 409)

    Raised when operation conflicts with existing data
    Examples: duplicate patient ID, concurrent modification, unique constraint violation
    """

    def __init__(self, message: str, resource: Optional[str] = None):
        details = {"resource": resource} if resource else {}
        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT",
            details=details
        )


class BusinessRuleException(BaseAppException):
    """
    Business rule violation error (HTTP 422)

    Raised when operation violates business logic rules
    Examples: discharging a critical patient, deleting patient with active medications
    """

    def __init__(self, message: str, rule: Optional[str] = None):
        details = {"rule": rule} if rule else {}
        super().__init__(
            message=message,
            status_code=422,
            error_code="BUSINESS_RULE_VIOLATION",
            details=details
        )


class AuthenticationException(BaseAppException):
    """
    Authentication error (HTTP 401)

    Raised when authentication fails
    Examples: invalid credentials, expired token, missing token
    """

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_FAILED"
        )


class ExternalServiceException(BaseAppException):
    """
    External service error (HTTP 503)

    Raised when external service calls fail
    Examples: MQTT broker unavailable, email service down, third-party API error
    """

    def __init__(self, service: str, message: str = "External service unavailable"):
        super().__init__(
            message=message,
            status_code=503,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service}
        )


class RateLimitException(BaseAppException):
    """
    Rate limit exceeded error (HTTP 429)

    Raised when user exceeds rate limits
    Examples: too many login attempts, excessive API calls
    """

    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        details = {"retryAfter": retry_after} if retry_after else {}
        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details
        )


class DataIntegrityException(BaseAppException):
    """
    Data integrity error (HTTP 422)

    Raised when operation would violate data integrity
    Examples: deleting parent record with child records, invalid foreign key
    """

    def __init__(self, message: str, constraint: Optional[str] = None):
        details = {"constraint": constraint} if constraint else {}
        super().__init__(
            message=message,
            status_code=422,
            error_code="DATA_INTEGRITY_ERROR",
            details=details
        )
