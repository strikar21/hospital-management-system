"""
Centralized Error Handler for FastAPI

Automatically converts BaseHospitalError exceptions into properly formatted
HTTP responses with consistent structure across all endpoints.

Usage:
    # In main.py:
    from app.core.error_handler import register_error_handlers
    register_error_handlers(app)

Response Format:
    {
        "success": false,
        "error": {
            "code": "PATIENT_NOT_FOUND",
            "message": "Patient 'PAT123' not found",
            "details": {"patient_id": "PAT123"}
        }
    }
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from typing import Union
import logging

from .errors import BaseHospitalError

logger = logging.getLogger(__name__)


async def hospital_error_handler(request: Request, exc: BaseHospitalError) -> JSONResponse:
    """
    Convert BaseHospitalError exceptions to JSON responses

    Args:
        request: FastAPI request object
        exc: BaseHospitalError exception

    Returns:
        JSONResponse with standardized error format
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions (fallback handler)

    Args:
        request: FastAPI request object
        exc: Generic exception

    Returns:
        JSONResponse with generic error message
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please contact support.",
                "details": {}
            }
        }
    )


def register_error_handlers(app: FastAPI) -> None:
    """
    Register all error handlers with FastAPI application

    Args:
        app: FastAPI application instance
    """
    # Register hospital error handler
    app.add_exception_handler(BaseHospitalError, hospital_error_handler)

    # Register generic exception handler as fallback
    # NOTE: Commented out to avoid overriding FastAPI's default handling
    # Uncomment when ready to use centralized error handling everywhere
    # app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("✅ Error handlers registered successfully")
