"""
Standardized API Response Models

Provides consistent response format across all API endpoints using Pydantic models.

Response Format:
    Success:
        {
            "success": true,
            "data": {...},
            "message": "Operation successful",
            "meta": {"timestamp": "2025-01-10T12:00:00Z"}
        }

    Error:
        {
            "success": false,
            "error": {
                "code": "PATIENT_NOT_FOUND",
                "message": "Patient 'PAT123' not found",
                "details": {"patient_id": "PAT123"}
            },
            "meta": {"timestamp": "2025-01-10T12:00:00Z"}
        }

Usage:
    # Success response
    return SuccessResponse(
        data=patient_data,
        message="Patient retrieved successfully"
    )

    # List response
    return ListResponse(
        data=patients,
        total=100,
        limit=10,
        offset=0
    )

    # Error response (usually handled by error_handler.py)
    raise PatientNotFoundError(patient_id="PAT123")
"""

from typing import Any, Dict, List, Optional, Generic, TypeVar
from pydantic import BaseModel, Field
from datetime import datetime

from ..common.datetime import now_utc

# Generic type for data payload
T = TypeVar('T')


# ================================
# BASE RESPONSE MODELS
# ================================

class ResponseMeta(BaseModel):
    """Metadata included in all responses"""
    timestamp: datetime = Field(default_factory=now_utc, description="Response timestamp (UTC)")
    requestId: Optional[str] = Field(None, description="Request trace ID for debugging")


class ErrorDetails(BaseModel):
    """Error details structure"""
    code: str = Field(..., description="Error code for frontend handling")
    message: str = Field(..., description="Human-readable error message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional error context")


# ================================
# SUCCESS RESPONSES
# ================================

class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response"""
    success: bool = Field(True, description="Operation success status")
    data: T = Field(..., description="Response payload")
    message: Optional[str] = Field(None, description="Optional success message")
    meta: ResponseMeta = Field(default_factory=ResponseMeta, description="Response metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"id": "PAT123", "firstName": "John", "lastName": "Doe"},
                "message": "Patient retrieved successfully",
                "meta": {"timestamp": "2025-01-10T12:00:00Z"}
            }
        }


class ListResponse(BaseModel, Generic[T]):
    """Standard list response with pagination metadata"""
    success: bool = Field(True, description="Operation success status")
    data: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items (before pagination)")
    count: int = Field(..., description="Number of items in current response")
    limit: Optional[int] = Field(None, description="Pagination limit")
    offset: Optional[int] = Field(None, description="Pagination offset")
    hasMore: Optional[bool] = Field(None, description="Whether more items exist")
    message: Optional[str] = Field(None, description="Optional success message")
    meta: ResponseMeta = Field(default_factory=ResponseMeta, description="Response metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": [
                    {"id": "PAT123", "firstName": "John"},
                    {"id": "PAT124", "firstName": "Jane"}
                ],
                "total": 100,
                "count": 2,
                "limit": 10,
                "offset": 0,
                "hasMore": True,
                "message": "Patients retrieved successfully",
                "meta": {"timestamp": "2025-01-10T12:00:00Z"}
            }
        }


class CreatedResponse(BaseModel, Generic[T]):
    """Response for resource creation (201 Created)"""
    success: bool = Field(True, description="Operation success status")
    data: T = Field(..., description="Created resource")
    resourceId: str = Field(..., description="ID of created resource")
    message: Optional[str] = Field(None, description="Optional success message")
    meta: ResponseMeta = Field(default_factory=ResponseMeta, description="Response metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"id": "PAT125", "firstName": "Alice", "lastName": "Smith"},
                "resourceId": "PAT125",
                "message": "Patient created successfully",
                "meta": {"timestamp": "2025-01-10T12:00:00Z"}
            }
        }


class UpdatedResponse(BaseModel, Generic[T]):
    """Response for resource update"""
    success: bool = Field(True, description="Operation success status")
    data: T = Field(..., description="Updated resource")
    message: Optional[str] = Field(None, description="Optional success message")
    meta: ResponseMeta = Field(default_factory=ResponseMeta, description="Response metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"id": "PAT123", "firstName": "John", "lastName": "Doe"},
                "message": "Patient updated successfully",
                "meta": {"timestamp": "2025-01-10T12:00:00Z"}
            }
        }


class DeletedResponse(BaseModel):
    """Response for resource deletion"""
    success: bool = Field(True, description="Operation success status")
    resourceId: str = Field(..., description="ID of deleted resource")
    message: Optional[str] = Field(None, description="Optional success message")
    meta: ResponseMeta = Field(default_factory=ResponseMeta, description="Response metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "resourceId": "PAT123",
                "message": "Patient deleted successfully",
                "meta": {"timestamp": "2025-01-10T12:00:00Z"}
            }
        }


class OperationResponse(BaseModel):
    """Generic operation response (no data payload)"""
    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Operation result message")
    meta: ResponseMeta = Field(default_factory=ResponseMeta, description="Response metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Alert acknowledged successfully",
                "meta": {"timestamp": "2025-01-10T12:00:00Z"}
            }
        }


# ================================
# ERROR RESPONSES
# ================================

class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = Field(False, description="Operation success status")
    error: ErrorDetails = Field(..., description="Error information")
    meta: ResponseMeta = Field(default_factory=ResponseMeta, description="Response metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "code": "PATIENT_NOT_FOUND",
                    "message": "Patient 'PAT123' not found",
                    "details": {"patient_id": "PAT123"}
                },
                "meta": {"timestamp": "2025-01-10T12:00:00Z"}
            }
        }


# ================================
# SPECIALIZED RESPONSES
# ================================

class HealthCheckResponse(BaseModel):
    """Health check endpoint response"""
    status: str = Field(..., description="Service status (healthy, degraded, unhealthy)")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(default_factory=now_utc, description="Current server time (UTC)")
    services: Dict[str, str] = Field(default_factory=dict, description="Status of dependent services")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2025-01-10T12:00:00Z",
                "services": {
                    "database": "connected",
                    "timescaledb": "connected",
                    "mqtt": "connected"
                }
            }
        }


class BatchOperationResponse(BaseModel, Generic[T]):
    """Response for batch operations"""
    success: bool = Field(True, description="Overall operation success status")
    results: List[T] = Field(..., description="Results for each item")
    totalProcessed: int = Field(..., description="Total number of items processed")
    successCount: int = Field(..., description="Number of successful operations")
    failureCount: int = Field(..., description="Number of failed operations")
    errors: List[ErrorDetails] = Field(default_factory=list, description="Errors encountered")
    message: Optional[str] = Field(None, description="Overall operation message")
    meta: ResponseMeta = Field(default_factory=ResponseMeta, description="Response metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "results": [
                    {"id": "PAT123", "status": "updated"},
                    {"id": "PAT124", "status": "updated"}
                ],
                "totalProcessed": 2,
                "successCount": 2,
                "failureCount": 0,
                "errors": [],
                "message": "Batch update completed successfully",
                "meta": {"timestamp": "2025-01-10T12:00:00Z"}
            }
        }


# ================================
# UTILITY FUNCTIONS
# ================================

def create_success_response(
    data: Any,
    message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized success response (dict format)

    Args:
        data: Response payload
        message: Optional success message

    Returns:
        Dictionary in standard success response format
    """
    return {
        "success": True,
        "data": data,
        "message": message,
        "meta": {"timestamp": now_utc().isoformat()}
    }


def create_list_response(
    data: List[Any],
    total: int,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized list response (dict format)

    Args:
        data: List of items
        total: Total number of items (before pagination)
        limit: Pagination limit
        offset: Pagination offset
        message: Optional success message

    Returns:
        Dictionary in standard list response format
    """
    count = len(data)
    has_more = None
    if limit is not None and offset is not None:
        has_more = (offset + count) < total

    return {
        "success": True,
        "data": data,
        "total": total,
        "count": count,
        "limit": limit,
        "offset": offset,
        "hasMore": has_more,
        "message": message,
        "meta": {"timestamp": now_utc().isoformat()}
    }


def create_operation_response(message: str) -> Dict[str, Any]:
    """
    Create a standardized operation response (dict format)

    Args:
        message: Operation result message

    Returns:
        Dictionary in standard operation response format
    """
    return {
        "success": True,
        "message": message,
        "meta": {"timestamp": now_utc().isoformat()}
    }


def create_error_response(
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized error response (dict format)

    Args:
        code: Error code
        message: Error message
        details: Additional error details

    Returns:
        Dictionary in standard error response format
    """
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {}
        },
        "meta": {"timestamp": now_utc().isoformat()}
    }
