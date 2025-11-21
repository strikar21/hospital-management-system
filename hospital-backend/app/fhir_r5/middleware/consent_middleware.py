"""
Consent Check Middleware
Validates patient consent before allowing data access (DPDP Act 2023)
"""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import asyncpg
import re
from typing import Optional

from ..handlers.consent_handler import ConsentHandler


class ConsentCheckMiddleware(BaseHTTPMiddleware):
    """
    Middleware to check patient consent before accessing data

    DPDP Act 2023 Requirements:
    - Patient data can only be accessed with active consent
    - Consent must specify the purpose of use
    - Consent must be within valid date range
    """

    def __init__(self, app: ASGIApp, db_pool: asyncpg.Pool, enforce: bool = True):
        super().__init__(app)
        self.db_pool = db_pool
        self.handler = ConsentHandler(db_pool)
        self.enforce = enforce  # Set to False to disable enforcement (for testing)

        # Patterns to extract patient ID from different resource types
        self.patient_pattern = re.compile(r'/fhir/R5/Patient/([^/?]+)')
        self.observation_pattern = re.compile(r'[?&]patient=Patient%2F([^&]+)')

    async def dispatch(self, request: Request, call_next):
        """
        Check consent before processing request
        """
        # Skip consent check for certain paths
        if self._should_skip_consent(request.path, request.method):
            return await call_next(request)

        # Don't enforce consent checks if disabled
        if not self.enforce:
            return await call_next(request)

        # Extract patient ID from request
        patient_id = await self._extract_patient_id(request)

        if not patient_id:
            # No patient ID found, allow request
            # (might be a search or non-patient resource)
            return await call_next(request)

        # Check for active consent
        consent = await self.handler.get_active_consent(patient_id)

        if not consent:
            raise HTTPException(
                status_code=403,
                detail={
                    "resourceType": "OperationOutcome",
                    "issue": [{
                        "severity": "error",
                        "code": "forbidden",
                        "details": {
                            "text": f"No active consent found for patient {patient_id}. "
                                   "Patient consent is required under DPDP Act 2023."
                        }
                    }]
                }
            )

        # Determine purpose from request headers or default to TREAT
        purpose = request.headers.get('X-Purpose-Of-Use', 'TREAT')

        # Check if consent allows this purpose
        consent_purposes = consent.get('provision', {}).get('purpose', [])
        allowed_purposes = [p.get('code') for p in consent_purposes]

        if purpose not in allowed_purposes:
            raise HTTPException(
                status_code=403,
                detail={
                    "resourceType": "OperationOutcome",
                    "issue": [{
                        "severity": "error",
                        "code": "forbidden",
                        "details": {
                            "text": f"Consent does not allow access for purpose '{purpose}'. "
                                   f"Allowed purposes: {', '.join(allowed_purposes)}"
                        }
                    }]
                }
            )

        # Consent is valid, proceed with request
        return await call_next(request)

    def _should_skip_consent(self, path: str, method: str) -> bool:
        """Check if this path should skip consent checking"""

        # Always skip consent check for consent endpoints themselves
        if '/Consent' in path:
            return True

        # Skip for metadata and non-patient resources
        skip_paths = [
            '/fhir/R5/metadata',
            '/fhir/R5/Device',
            '/fhir/R5/AuditEvent',
            '/health',
            '/metrics',
            '/docs',
            '/openapi.json'
        ]

        for skip_path in skip_paths:
            if path.startswith(skip_path):
                return True

        # Skip for POST creating new resources (consent checked during creation)
        if method == 'POST' and '/Patient' not in path:
            return False

        return False

    async def _extract_patient_id(self, request: Request) -> Optional[str]:
        """
        Extract patient ID from request

        Handles:
        - Direct patient access: /fhir/R5/Patient/PAT001
        - Observation queries: /fhir/R5/Observation?patient=Patient/PAT001
        - Request body (for POST/PATCH)
        """
        # Check URL path for patient ID
        match = self.patient_pattern.search(request.url.path)
        if match:
            return match.group(1)

        # Check query parameters
        query_string = str(request.url.query)
        match = self.observation_pattern.search(query_string)
        if match:
            return match.group(1)

        # Check for URL-decoded version
        if 'patient=Patient/' in query_string:
            parts = query_string.split('patient=Patient/')
            if len(parts) > 1:
                patient_id = parts[1].split('&')[0]
                return patient_id

        # For POST/PATCH, would need to parse body
        # (not implemented here to avoid consuming request body)

        return None
