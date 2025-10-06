"""
Error Response Models for Hospital Management System
Provides structured Pydantic models for consistent error responses
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime


class ErrorDetail(BaseModel):
    """
    Individual error detail for validation errors

    Used when multiple fields have validation errors
    """

    field: Optional[str] = Field(
        None,
        description="Field name that caused the error"
    )

    message: str = Field(
        ...,
        description="Human-readable error message"
    )

    errorCode: Optional[str] = Field(
        None,
        description="Machine-readable error code for this specific error"
    )

    value: Optional[Any] = Field(
        None,
        description="The invalid value (if safe to expose)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "field": "dosage",
                "message": "Dosage must be positive",
                "errorCode": "INVALID_DOSAGE",
                "value": "-500mg"
            }
        }


class ErrorResponse(BaseModel):
    """
    Standard error response format for all API errors

    Provides consistent error structure for frontend consumption
    """

    success: bool = Field(
        False,
        description="Always false for error responses"
    )

    errorCode: str = Field(
        ...,
        description="Machine-readable error code (e.g., VALIDATION_ERROR, NOT_FOUND)"
    )

    message: str = Field(
        ...,
        description="Human-readable error message"
    )

    details: Optional[List[ErrorDetail]] = Field(
        None,
        description="Array of specific field errors (for validation errors)"
    )

    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + 'Z',
        description="ISO 8601 timestamp when error occurred"
    )

    requestId: Optional[str] = Field(
        None,
        description="Optional request tracking ID for debugging"
    )

    path: Optional[str] = Field(
        None,
        description="API endpoint path where error occurred"
    )

    statusCode: int = Field(
        ...,
        description="HTTP status code"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "errorCode": "VALIDATION_ERROR",
                "message": "Input validation failed",
                "details": [
                    {
                        "field": "dosage",
                        "message": "Dosage must be positive",
                        "errorCode": "INVALID_DOSAGE"
                    },
                    {
                        "field": "prescribedBy",
                        "message": "Invalid prescriber ID format",
                        "errorCode": "INVALID_ID_FORMAT"
                    }
                ],
                "timestamp": "2025-10-05T10:30:00.000Z",
                "requestId": "req_123abc",
                "path": "/api/v2/medications/patient/PAT0001",
                "statusCode": 422
            }
        }


class SuccessResponse(BaseModel):
    """
    Standard success response format

    Used for operations that don't return specific data
    """

    success: bool = Field(
        True,
        description="Always true for success responses"
    )

    message: str = Field(
        ...,
        description="Success message"
    )

    data: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional response data"
    )

    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + 'Z',
        description="ISO 8601 timestamp"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Patient discharged successfully",
                "data": {
                    "patientId": "PAT0001",
                    "dischargedAt": "2025-10-05T10:30:00.000Z"
                },
                "timestamp": "2025-10-05T10:30:00.000Z"
            }
        }
