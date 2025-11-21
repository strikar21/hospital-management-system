"""
Audit Logging Middleware
Automatically logs all FHIR API access for DPDP + HIPAA compliance
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import asyncpg
import re
from typing import Optional, Tuple
import time

from ..handlers.audit_event_handler import AuditEventHandler


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically log all API access

    Logs:
    - All CRUD operations on FHIR resources
    - Who accessed what resource
    - When the access occurred
    - IP address and user agent
    - Success/failure outcome
    """

    def __init__(self, app: ASGIApp, db_pool: asyncpg.Pool):
        super().__init__(app)
        self.db_pool = db_pool
        self.handler = AuditEventHandler(db_pool)

        # Regex patterns to extract resource info from paths
        self.resource_pattern = re.compile(r'/fhir/R5/(\w+)(?:/([^/?]+))?')

    async def dispatch(self, request: Request, call_next):
        """
        Process request and log audit event
        """
        # Skip audit logging for certain paths
        if self._should_skip_audit(request.path):
            return await call_next(request)

        # Extract resource info from path
        resource_type, resource_id = self._extract_resource_info(request.path)

        if not resource_type:
            # Not a FHIR resource endpoint, skip audit
            return await call_next(request)

        # Determine action from HTTP method
        action = self._map_method_to_action(request.method)

        # Get staff info from request (assuming JWT or session)
        agent_id, agent_role = await self._get_agent_info(request)

        # Get IP address and user agent
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get('user-agent')

        # Record start time
        start_time = time.time()

        # Process request
        try:
            response = await call_next(request)
            outcome = 'success' if response.status_code < 400 else 'failure'

            # Log successful access
            if agent_id and resource_type:
                entity_id = resource_id or 'search'

                # Don't await - fire and forget for performance
                # (consider using a background task queue in production)
                try:
                    await self.handler.log_access(
                        action=action,
                        agent_id=agent_id,
                        agent_role=agent_role,
                        entity_type=resource_type,
                        entity_id=entity_id,
                        outcome=outcome,
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                except Exception as e:
                    # Don't fail the request if audit logging fails
                    print(f"Audit logging failed: {e}")

            return response

        except Exception as e:
            # Log failed access
            if agent_id and resource_type:
                entity_id = resource_id or 'unknown'

                try:
                    await self.handler.log_access(
                        action=action,
                        agent_id=agent_id,
                        agent_role=agent_role,
                        entity_type=resource_type,
                        entity_id=entity_id,
                        outcome='failure',
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                except:
                    pass  # Silently fail audit logging

            # Re-raise the original exception
            raise

    def _should_skip_audit(self, path: str) -> bool:
        """Check if this path should skip audit logging"""
        skip_paths = [
            '/fhir/R5/metadata',  # Capability statement
            '/health',
            '/metrics',
            '/docs',
            '/openapi.json'
        ]

        return any(path.startswith(skip) for skip in skip_paths)

    def _extract_resource_info(self, path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract resource type and ID from path

        Examples:
            /fhir/R5/Patient/PAT001 -> ('Patient', 'PAT001')
            /fhir/R5/Device -> ('Device', None)
            /fhir/R5/Observation/$stats -> ('Observation', None)
        """
        match = self.resource_pattern.search(path)

        if match:
            resource_type = match.group(1)
            resource_id = match.group(2) if match.group(2) and not match.group(2).startswith('$') else None
            return resource_type, resource_id

        return None, None

    def _map_method_to_action(self, method: str) -> str:
        """Map HTTP method to FHIR action code"""
        method_map = {
            'POST': 'C',    # Create
            'GET': 'R',     # Read
            'PUT': 'U',     # Update
            'PATCH': 'U',   # Update
            'DELETE': 'D'   # Delete
        }

        return method_map.get(method.upper(), 'E')  # E = Execute (default)

    async def _get_agent_info(self, request: Request) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract agent (staff) info from request

        In production, this would:
        1. Extract JWT token from Authorization header
        2. Decode token to get staff ID and role
        3. Return (staff_id, role)

        For now, we'll check for headers or return a default
        """
        # Check for custom headers (for testing)
        staff_id = request.headers.get('X-Staff-ID')
        staff_role = request.headers.get('X-Staff-Role', 'admin')

        # In production, extract from JWT:
        # auth_header = request.headers.get('Authorization')
        # if auth_header and auth_header.startswith('Bearer '):
        #     token = auth_header[7:]
        #     payload = decode_jwt(token)
        #     staff_id = payload.get('sub')
        #     staff_role = payload.get('role')

        # Default for testing (should be removed in production)
        if not staff_id:
            staff_id = 'STF000001'  # Default admin for testing
            staff_role = 'admin'

        return staff_id, staff_role
