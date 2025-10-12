"""
Middleware Package

Contains middleware components for request/response processing.
"""

from .staff_resolution_middleware import resolve_staff_in_response

__all__ = ['resolve_staff_in_response']
