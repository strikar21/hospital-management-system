"""
Global Exception Handlers for Hospital Management System
Provides centralized error handling for all API endpoints
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import logging
import traceback
import asyncpg
from typing import Union

from .exceptions import BaseAppException, DatabaseException
from ..models.error_response import ErrorResponse, ErrorDetail

logger = logging.getLogger(__name__)


async def base_app_exception_handler(request: Request, exc: BaseAppException) -> JSONResponse:
    """
    Handle custom application exceptions

    Converts BaseAppException and all subclasses to structured ErrorResponse
    """
    logger.error(
        f"App exception: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "details": exc.details
        }
    )

    # Build error response
    error_response = ErrorResponse(
        errorCode=exc.error_code,
        message=exc.message,
        statusCode=exc.status_code,
        path=request.url.path
    )

    # Add details if present
    if exc.details:
        # Convert dict details to ErrorDetail objects if needed
        if isinstance(exc.details, dict):
            # For simple dict details, add as a single ErrorDetail
            error_response.details = [
                ErrorDetail(
                    field=key,
                    message=str(value)
                ) for key, value in exc.details.items()
            ]

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(exclude_none=True)
    )


async def validation_exception_handler(
    request: Request,
    exc: Union[RequestValidationError, ValidationError]
) -> JSONResponse:
    """
    Handle Pydantic validation errors

    Converts Pydantic validation errors to structured ErrorResponse
    with field-level error details
    """
    # Convert Pydantic errors to our ErrorDetail format
    details = []

    for error in exc.errors():
        # Extract field path (e.g., ["body", "dosage"] -> "dosage")
        field_path = ".".join(str(loc) for loc in error["loc"] if loc not in ["body", "query", "path"])

        details.append(ErrorDetail(
            field=field_path if field_path else None,
            message=error["msg"],
            errorCode="VALIDATION_ERROR"
        ))

    error_response = ErrorResponse(
        errorCode="VALIDATION_ERROR",
        message="Input validation failed",
        statusCode=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details=details,
        path=request.url.path
    )

    logger.warning(
        f"Validation error on {request.url.path}: {len(details)} errors",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_count": len(details),
            "errors": [detail.model_dump() for detail in details]
        }
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(exclude_none=True)
    )


async def database_exception_handler(request: Request, exc: asyncpg.PostgresError) -> JSONResponse:
    """
    Handle PostgreSQL database exceptions

    Sanitizes database errors to prevent schema leakage
    Logs full error details for debugging
    """
    # Log full database error details (for debugging)
    logger.error(
        f"Database error: {type(exc).__name__} - {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__
        }
    )

    # Determine user-friendly error message based on error type
    if isinstance(exc, asyncpg.UniqueViolationError):
        message = "A record with this identifier already exists"
        error_code = "DUPLICATE_RECORD"
        status_code = status.HTTP_409_CONFLICT

    elif isinstance(exc, asyncpg.ForeignKeyViolationError):
        message = "Referenced record does not exist"
        error_code = "INVALID_REFERENCE"
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

    elif isinstance(exc, asyncpg.NotNullViolationError):
        message = "Required field is missing"
        error_code = "REQUIRED_FIELD_MISSING"
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

    elif isinstance(exc, asyncpg.CheckViolationError):
        message = "Data validation failed"
        error_code = "VALIDATION_ERROR"
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

    else:
        # Generic database error (don't leak details)
        message = "A database error occurred. Please try again later."
        error_code = "DATABASE_ERROR"
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    error_response = ErrorResponse(
        errorCode=error_code,
        message=message,
        statusCode=status_code,
        path=request.url.path
    )

    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump(exclude_none=True)
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for unhandled exceptions

    Logs full error details for debugging
    Returns generic error to user (security)
    """
    # Log full exception with stack trace
    logger.error(
        f"Unhandled exception: {type(exc).__name__} - {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__,
            "traceback": traceback.format_exc()
        }
    )

    # Generic error response (don't leak implementation details)
    error_response = ErrorResponse(
        errorCode="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred. Please try again later.",
        statusCode=status.HTTP_500_INTERNAL_SERVER_ERROR,
        path=request.url.path
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(exclude_none=True)
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle FastAPI HTTPException

    Converts FastAPI HTTPException to structured ErrorResponse
    """
    from fastapi import HTTPException

    if not isinstance(exc, HTTPException):
        # Not an HTTPException, pass to generic handler
        return await generic_exception_handler(request, exc)

    logger.warning(
        f"HTTP exception: {exc.status_code} - {exc.detail}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code
        }
    )

    error_response = ErrorResponse(
        errorCode=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
        statusCode=exc.status_code,
        path=request.url.path
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(exclude_none=True)
    )
