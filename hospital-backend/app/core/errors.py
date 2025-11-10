"""
Centralized Error Definitions for Hospital Management System

All error classes inherit from BaseHospitalError which provides:
- HTTP status code
- Error code (for frontend error handling)
- User-friendly message
- Optional technical details
- Automatic logging

Usage:
    raise PatientNotFoundError(patient_id="PAT123")
    raise ValidationError("Invalid email format", field="email")
"""

from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class BaseHospitalError(Exception):
    """Base class for all hospital management system errors"""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

        # Auto-log errors
        logger.error(
            f"[{self.error_code}] {self.message}",
            extra={"status_code": self.status_code, "details": self.details}
        )


# ================================
# 400 CLIENT ERRORS
# ================================

class ValidationError(BaseHospitalError):
    """Invalid input data (400 Bad Request)"""
    def __init__(self, message: str, field: Optional[str] = None, **details):
        super().__init__(
            message=message,
            status_code=400,
            error_code="VALIDATION_ERROR",
            details={"field": field, **details} if field else details
        )


class MissingFieldError(BaseHospitalError):
    """Required field missing (400 Bad Request)"""
    def __init__(self, field: str, **details):
        super().__init__(
            message=f"Required field '{field}' is missing",
            status_code=400,
            error_code="MISSING_FIELD",
            details={"field": field, **details}
        )


class InvalidFormatError(BaseHospitalError):
    """Invalid data format (400 Bad Request)"""
    def __init__(self, field: str, expected_format: str, **details):
        super().__init__(
            message=f"Invalid format for '{field}'. Expected: {expected_format}",
            status_code=400,
            error_code="INVALID_FORMAT",
            details={"field": field, "expected_format": expected_format, **details}
        )


class DuplicateRecordError(BaseHospitalError):
    """Duplicate record exists (400 Bad Request)"""
    def __init__(self, resource_type: str, field: str, value: str, **details):
        super().__init__(
            message=f"{resource_type} with {field}='{value}' already exists",
            status_code=400,
            error_code="DUPLICATE_RECORD",
            details={"resource_type": resource_type, "field": field, "value": value, **details}
        )


class BusinessLogicError(BaseHospitalError):
    """Business rule violation (400 Bad Request)"""
    def __init__(self, message: str, rule: Optional[str] = None, **details):
        super().__init__(
            message=message,
            status_code=400,
            error_code="BUSINESS_LOGIC_ERROR",
            details={"rule": rule, **details} if rule else details
        )


# ================================
# 401/403 AUTHENTICATION/AUTHORIZATION ERRORS
# ================================

class AuthenticationError(BaseHospitalError):
    """Authentication failed (401 Unauthorized)"""
    def __init__(self, message: str = "Authentication required", **details):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
            details=details
        )


class InvalidCredentialsError(BaseHospitalError):
    """Invalid credentials (401 Unauthorized)"""
    def __init__(self, **details):
        super().__init__(
            message="Invalid credentials provided",
            status_code=401,
            error_code="INVALID_CREDENTIALS",
            details=details
        )


class AuthorizationError(BaseHospitalError):
    """Insufficient permissions (403 Forbidden)"""
    def __init__(self, message: str = "Insufficient permissions", required_role: Optional[str] = None, **details):
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_ERROR",
            details={"required_role": required_role, **details} if required_role else details
        )


# ================================
# 404 NOT FOUND ERRORS
# ================================

class ResourceNotFoundError(BaseHospitalError):
    """Generic resource not found (404 Not Found)"""
    def __init__(self, resource_type: str, resource_id: str, **details):
        super().__init__(
            message=f"{resource_type} with ID '{resource_id}' not found",
            status_code=404,
            error_code="RESOURCE_NOT_FOUND",
            details={"resource_type": resource_type, "resource_id": resource_id, **details}
        )


class PatientNotFoundError(BaseHospitalError):
    """Patient not found (404 Not Found)"""
    def __init__(self, patient_id: str, **details):
        super().__init__(
            message=f"Patient '{patient_id}' not found",
            status_code=404,
            error_code="PATIENT_NOT_FOUND",
            details={"patient_id": patient_id, **details}
        )


class DeviceNotFoundError(BaseHospitalError):
    """Device not found (404 Not Found)"""
    def __init__(self, device_id: str, **details):
        super().__init__(
            message=f"Device '{device_id}' not found",
            status_code=404,
            error_code="DEVICE_NOT_FOUND",
            details={"device_id": device_id, **details}
        )


class StaffNotFoundError(BaseHospitalError):
    """Staff member not found (404 Not Found)"""
    def __init__(self, staff_id: str, **details):
        super().__init__(
            message=f"Staff member '{staff_id}' not found",
            status_code=404,
            error_code="STAFF_NOT_FOUND",
            details={"staff_id": staff_id, **details}
        )


class MedicationNotFoundError(BaseHospitalError):
    """Medication record not found (404 Not Found)"""
    def __init__(self, medication_id: str, **details):
        super().__init__(
            message=f"Medication record '{medication_id}' not found",
            status_code=404,
            error_code="MEDICATION_NOT_FOUND",
            details={"medication_id": medication_id, **details}
        )


class AlertNotFoundError(BaseHospitalError):
    """Alert not found (404 Not Found)"""
    def __init__(self, alert_id: str, **details):
        super().__init__(
            message=f"Alert '{alert_id}' not found",
            status_code=404,
            error_code="ALERT_NOT_FOUND",
            details={"alert_id": alert_id, **details}
        )


# ================================
# 409 CONFLICT ERRORS
# ================================

class ResourceConflictError(BaseHospitalError):
    """Resource conflict (409 Conflict)"""
    def __init__(self, message: str, resource_type: str, **details):
        super().__init__(
            message=message,
            status_code=409,
            error_code="RESOURCE_CONFLICT",
            details={"resource_type": resource_type, **details}
        )


class DeviceAlreadyAssignedError(BaseHospitalError):
    """Device already assigned to another patient (409 Conflict)"""
    def __init__(self, device_id: str, current_patient_id: str, **details):
        super().__init__(
            message=f"Device '{device_id}' is already assigned to patient '{current_patient_id}'",
            status_code=409,
            error_code="DEVICE_ALREADY_ASSIGNED",
            details={"device_id": device_id, "current_patient_id": current_patient_id, **details}
        )


class PatientAlreadyAdmittedError(BaseHospitalError):
    """Patient already has active admission (409 Conflict)"""
    def __init__(self, patient_id: str, **details):
        super().__init__(
            message=f"Patient '{patient_id}' already has an active admission",
            status_code=409,
            error_code="PATIENT_ALREADY_ADMITTED",
            details={"patient_id": patient_id, **details}
        )


# ================================
# 422 UNPROCESSABLE ENTITY ERRORS
# ================================

class OperationNotAllowedError(BaseHospitalError):
    """Operation not allowed in current state (422 Unprocessable Entity)"""
    def __init__(self, message: str, operation: str, current_state: Optional[str] = None, **details):
        super().__init__(
            message=message,
            status_code=422,
            error_code="OPERATION_NOT_ALLOWED",
            details={"operation": operation, "current_state": current_state, **details}
        )


# ================================
# 500 INTERNAL SERVER ERRORS
# ================================

class DatabaseError(BaseHospitalError):
    """Database operation failed (500 Internal Server Error)"""
    def __init__(self, message: str = "Database operation failed", operation: Optional[str] = None, **details):
        super().__init__(
            message=message,
            status_code=500,
            error_code="DATABASE_ERROR",
            details={"operation": operation, **details} if operation else details
        )


class ExternalServiceError(BaseHospitalError):
    """External service unavailable (500 Internal Server Error)"""
    def __init__(self, service_name: str, message: Optional[str] = None, **details):
        super().__init__(
            message=message or f"External service '{service_name}' is unavailable",
            status_code=500,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service_name": service_name, **details}
        )


class ConfigurationError(BaseHospitalError):
    """System configuration error (500 Internal Server Error)"""
    def __init__(self, message: str, config_key: Optional[str] = None, **details):
        super().__init__(
            message=message,
            status_code=500,
            error_code="CONFIGURATION_ERROR",
            details={"config_key": config_key, **details} if config_key else details
        )


# ================================
# 503 SERVICE UNAVAILABLE ERRORS
# ================================

class ServiceUnavailableError(BaseHospitalError):
    """Service temporarily unavailable (503 Service Unavailable)"""
    def __init__(self, message: str = "Service temporarily unavailable", retry_after: Optional[int] = None, **details):
        super().__init__(
            message=message,
            status_code=503,
            error_code="SERVICE_UNAVAILABLE",
            details={"retry_after": retry_after, **details} if retry_after else details
        )


class DatabaseConnectionError(BaseHospitalError):
    """Cannot connect to database (503 Service Unavailable)"""
    def __init__(self, database: str = "PostgreSQL", **details):
        super().__init__(
            message=f"Cannot connect to {database} database",
            status_code=503,
            error_code="DATABASE_CONNECTION_ERROR",
            details={"database": database, **details}
        )
