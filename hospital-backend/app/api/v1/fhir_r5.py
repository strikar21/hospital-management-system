"""
FHIR R5 REST API Router - Standard HL7 FHIR endpoints

Implements standard FHIR R5 RESTful API:

CRUD Operations:
- GET /fhir/r5/{resourceType} - Search resources
- POST /fhir/r5/{resourceType}/_search - Search resources (POST method)
- GET /fhir/r5/{resourceType}/{id} - Read resource
- POST /fhir/r5/{resourceType} - Create resource
- PUT /fhir/r5/{resourceType}/{id} - Update resource
- DELETE /fhir/r5/{resourceType}/{id} - Delete resource

History Operations:
- GET /fhir/r5/{resourceType}/{id}/_history - Instance-level history
- GET /fhir/r5/{resourceType}/_history - Type-level history
- GET /fhir/r5/_history - System-level history

Metadata:
- GET /fhir/r5/metadata - CapabilityStatement

Pagination (FHIR R5 standard):
- _page: Page number (1-based, standard)
- _count: Results per page
- _offset: Result offset (0-based, convenience)

Supported Resources:
- Patient, Observation, Device, DeviceAssociation
- Medication, MedicationAdministration, Practitioner
- Encounter, Condition, Procedure, AllergyIntolerance, DiagnosticReport
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Request, Depends
from fastapi.responses import JSONResponse

from app.core.database import getDbConnection
from app.core.auth_dependencies import require_any_staff, get_current_active_user
from app.services.fhir.fhir_resource_service import FhirResourceService
from app.services.fhir.fhir_search_service import FhirSearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fhir/r5", tags=["FHIR R5"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def get_fhir_resource_service() -> FhirResourceService:
    """Get FHIR resource service instance"""
    pool = await getDbConnection()
    return FhirResourceService(pool)


async def get_fhir_search_service() -> FhirSearchService:
    """Get FHIR search service instance"""
    pool = await getDbConnection()
    return FhirSearchService(pool)


def build_operation_outcome(
    severity: str,
    code: str,
    diagnostics: str
) -> Dict[str, Any]:
    """
    Build FHIR OperationOutcome resource for errors

    Args:
        severity: fatal, error, warning, information
        code: FHIR issue type code
        diagnostics: Human-readable error message

    Returns:
        FHIR OperationOutcome resource
    """
    return {
        "resourceType": "OperationOutcome",
        "issue": [{
            "severity": severity,
            "code": code,
            "diagnostics": diagnostics
        }]
    }


# ============================================================================
# SEARCH (GET /fhir/r5/{resourceType})
# ============================================================================

@router.get("/{resource_type}")
async def search_resources(
    resource_type: str,
    request: Request,
    current_user: Dict = Depends(require_any_staff)
):
    """
    Search FHIR resources

    Standard FHIR search:
    - GET /fhir/r5/Patient?name=John&_sort=-birthdate&_count=10
    - GET /fhir/r5/Observation?patient=PAT0001&code=8867-4&_sort=-date
    - GET /fhir/r5/Device?identifier=fit-00001

    Returns:
        FHIR Bundle (searchset) with matching resources
    """
    logger.info(f"FHIR search: {resource_type} by user {current_user.get('id', 'unknown')}")

    try:
        # Get query parameters
        params = dict(request.query_params)

        # Get search service
        search_service = await get_fhir_search_service()

        # Execute search
        bundle = await search_service.search(resource_type, params)

        return JSONResponse(content=bundle, status_code=200)

    except ValueError as e:
        logger.warning(f"Invalid search request: {e}")
        outcome = build_operation_outcome("error", "invalid", str(e))
        return JSONResponse(content=outcome, status_code=400)

    except Exception as e:
        logger.error(f"Search failed for {resource_type}: {e}", exc_info=True)
        outcome = build_operation_outcome("error", "exception", f"Internal server error: {str(e)}")
        return JSONResponse(content=outcome, status_code=500)


# ============================================================================
# POST SEARCH (POST /fhir/r5/{resourceType}/_search) - FHIR R5 Standard
# ============================================================================

@router.post("/{resource_type}/_search")
async def post_search_resources(
    resource_type: str,
    request: Request,
    current_user: Dict = Depends(require_any_staff)
):
    """
    Search FHIR resources using POST (FHIR R5 standard)

    Standard FHIR POST search:
    - POST /fhir/r5/Patient/_search
      Body (form data): name=John&_sort=-birthdate&_count=10

    This is equivalent to GET search but allows for:
    - Longer search parameters (no URL length limits)
    - Parameters in request body instead of query string

    Returns:
        FHIR Bundle (searchset) with matching resources
    """
    logger.info(f"FHIR POST search: {resource_type} by user {current_user.get('id', 'unknown')}")

    try:
        # Get parameters from form data (POST body)
        form_data = await request.form()
        params = dict(form_data)

        # Get search service
        search_service = await get_fhir_search_service()

        # Execute search
        bundle = await search_service.search(resource_type, params)

        return JSONResponse(content=bundle, status_code=200)

    except ValueError as e:
        logger.warning(f"Invalid POST search request: {e}")
        outcome = build_operation_outcome("error", "invalid", str(e))
        return JSONResponse(content=outcome, status_code=400)

    except Exception as e:
        logger.error(f"POST search failed for {resource_type}: {e}", exc_info=True)
        outcome = build_operation_outcome("error", "exception", f"Internal server error: {str(e)}")
        return JSONResponse(content=outcome, status_code=500)


# ============================================================================
# READ (GET /fhir/r5/{resourceType}/{id})
# ============================================================================

@router.get("/{resource_type}/{resource_id}")
async def read_resource(
    resource_type: str,
    resource_id: str,
    current_user: Dict = Depends(require_any_staff)
):
    """
    Read a single FHIR resource by ID

    Standard FHIR read:
    - GET /fhir/r5/Patient/PAT0001
    - GET /fhir/r5/Observation/OBS-12345
    - GET /fhir/r5/Device/fit-00001

    Returns:
        FHIR resource or 404 if not found
    """
    logger.info(f"FHIR read: {resource_type}/{resource_id} by user {current_user.get('id', 'unknown')}")

    try:
        # Get resource service
        resource_service = await get_fhir_resource_service()

        # Read resource
        resource = await resource_service.read(resource_type, resource_id)

        if not resource:
            outcome = build_operation_outcome(
                "error",
                "not-found",
                f"{resource_type}/{resource_id} not found"
            )
            return JSONResponse(content=outcome, status_code=404)

        return JSONResponse(content=resource, status_code=200)

    except ValueError as e:
        logger.warning(f"Invalid resource ID: {e}")
        outcome = build_operation_outcome("error", "invalid", str(e))
        return JSONResponse(content=outcome, status_code=400)

    except Exception as e:
        logger.error(f"Read failed for {resource_type}/{resource_id}: {e}", exc_info=True)
        outcome = build_operation_outcome("error", "exception", f"Internal server error: {str(e)}")
        return JSONResponse(content=outcome, status_code=500)


# ============================================================================
# CREATE (POST /fhir/r5/{resourceType})
# ============================================================================

@router.post("/{resource_type}")
async def create_resource(
    resource_type: str,
    resource: Dict[str, Any],
    current_user: Dict = Depends(require_any_staff)
):
    """
    Create a new FHIR resource

    Standard FHIR create:
    - POST /fhir/r5/Patient
      Body: {"resourceType": "Patient", "id": "PAT0001", ...}

    Returns:
        Created resource with metadata (Location header)
    """
    logger.info(f"FHIR create: {resource_type} by user {current_user.get('id', 'unknown')}")

    try:
        # Validate resource type matches URL
        if resource.get('resourceType') != resource_type:
            raise ValueError(
                f"Resource type mismatch: URL says {resource_type}, body says {resource.get('resourceType')}"
            )

        # Get resource service
        resource_service = await get_fhir_resource_service()

        # Create resource
        created_by = current_user.get('id', 'system')
        created_resource = await resource_service.create(resource, created_by=created_by)

        # Build Location header
        location = f"/fhir/r5/{resource_type}/{created_resource['id']}"

        return JSONResponse(
            content=created_resource,
            status_code=201,
            headers={"Location": location}
        )

    except ValueError as e:
        logger.warning(f"Invalid resource: {e}")
        outcome = build_operation_outcome("error", "invalid", str(e))
        return JSONResponse(content=outcome, status_code=400)

    except Exception as e:
        logger.error(f"Create failed for {resource_type}: {e}", exc_info=True)
        outcome = build_operation_outcome("error", "exception", f"Internal server error: {str(e)}")
        return JSONResponse(content=outcome, status_code=500)


# ============================================================================
# UPDATE (PUT /fhir/r5/{resourceType}/{id})
# ============================================================================

@router.put("/{resource_type}/{resource_id}")
async def update_resource(
    resource_type: str,
    resource_id: str,
    resource: Dict[str, Any],
    current_user: Dict = Depends(require_any_staff)
):
    """
    Update an existing FHIR resource

    Standard FHIR update:
    - PUT /fhir/r5/Patient/PAT0001
      Body: {"resourceType": "Patient", "id": "PAT0001", ...}

    Returns:
        Updated resource with new version
    """
    logger.info(f"FHIR update: {resource_type}/{resource_id} by user {current_user.get('id', 'unknown')}")

    try:
        # Validate resource type and ID match URL
        if resource.get('resourceType') != resource_type:
            raise ValueError(
                f"Resource type mismatch: URL says {resource_type}, body says {resource.get('resourceType')}"
            )

        if resource.get('id') != resource_id:
            raise ValueError(
                f"Resource ID mismatch: URL says {resource_id}, body says {resource.get('id')}"
            )

        # Get resource service
        resource_service = await get_fhir_resource_service()

        # Update resource
        created_by = current_user.get('id', 'system')
        updated_resource = await resource_service.update(resource, created_by=created_by)

        return JSONResponse(content=updated_resource, status_code=200)

    except ValueError as e:
        logger.warning(f"Invalid resource: {e}")
        outcome = build_operation_outcome("error", "invalid", str(e))
        return JSONResponse(content=outcome, status_code=400)

    except Exception as e:
        logger.error(f"Update failed for {resource_type}/{resource_id}: {e}", exc_info=True)
        outcome = build_operation_outcome("error", "exception", f"Internal server error: {str(e)}")
        return JSONResponse(content=outcome, status_code=500)


# ============================================================================
# DELETE (DELETE /fhir/r5/{resourceType}/{id})
# ============================================================================

@router.delete("/{resource_type}/{resource_id}")
async def delete_resource(
    resource_type: str,
    resource_id: str,
    current_user: Dict = Depends(require_any_staff)
):
    """
    Delete a FHIR resource (soft delete)

    Standard FHIR delete:
    - DELETE /fhir/r5/Patient/PAT0001

    Returns:
        204 No Content on success, 404 if not found
    """
    logger.info(f"FHIR delete: {resource_type}/{resource_id} by user {current_user.get('id', 'unknown')}")

    try:
        # Get resource service
        resource_service = await get_fhir_resource_service()

        # Delete resource
        deleted_by = current_user.get('id', 'system')
        deleted = await resource_service.delete(resource_type, resource_id, deleted_by=deleted_by)

        if not deleted:
            outcome = build_operation_outcome(
                "error",
                "not-found",
                f"{resource_type}/{resource_id} not found"
            )
            return JSONResponse(content=outcome, status_code=404)

        return JSONResponse(content=None, status_code=204)

    except ValueError as e:
        logger.warning(f"Invalid resource ID: {e}")
        outcome = build_operation_outcome("error", "invalid", str(e))
        return JSONResponse(content=outcome, status_code=400)

    except Exception as e:
        logger.error(f"Delete failed for {resource_type}/{resource_id}: {e}", exc_info=True)
        outcome = build_operation_outcome("error", "exception", f"Internal server error: {str(e)}")
        return JSONResponse(content=outcome, status_code=500)


# ============================================================================
# INSTANCE-LEVEL HISTORY (GET /fhir/r5/{resourceType}/{id}/_history)
# ============================================================================

@router.get("/{resource_type}/{resource_id}/_history")
async def get_resource_history(
    resource_type: str,
    resource_id: str,
    current_user: Dict = Depends(require_any_staff)
):
    """
    Get version history for a FHIR resource (instance-level)

    Standard FHIR history:
    - GET /fhir/r5/Patient/PAT0001/_history

    Returns:
        FHIR Bundle (history) with all versions of this specific resource
    """
    logger.info(f"FHIR instance history: {resource_type}/{resource_id} by user {current_user.get('id', 'unknown')}")

    try:
        # Get resource service
        resource_service = await get_fhir_resource_service()

        # Get history
        history = await resource_service.history(resource_type, resource_id)

        # Build Bundle
        entries = []
        for resource in history:
            entries.append({
                "fullUrl": f"urn:uuid:{resource['id']}",
                "resource": resource,
                "request": {
                    "method": "PUT",
                    "url": f"{resource_type}/{resource_id}"
                }
            })

        bundle = {
            "resourceType": "Bundle",
            "type": "history",
            "total": len(entries),
            "entry": entries
        }

        return JSONResponse(content=bundle, status_code=200)

    except ValueError as e:
        logger.warning(f"Invalid resource ID: {e}")
        outcome = build_operation_outcome("error", "invalid", str(e))
        return JSONResponse(content=outcome, status_code=400)

    except Exception as e:
        logger.error(f"Instance history failed for {resource_type}/{resource_id}: {e}", exc_info=True)
        outcome = build_operation_outcome("error", "exception", f"Internal server error: {str(e)}")
        return JSONResponse(content=outcome, status_code=500)


# ============================================================================
# TYPE-LEVEL HISTORY (GET /fhir/r5/{resourceType}/_history) - FHIR R5 Standard
# ============================================================================

@router.get("/{resource_type}/_history")
async def get_type_history(
    resource_type: str,
    request: Request,
    current_user: Dict = Depends(require_any_staff)
):
    """
    Get version history for all resources of a type (type-level)

    Standard FHIR type-level history:
    - GET /fhir/r5/Patient/_history
    - GET /fhir/r5/Observation/_history?_count=50

    Returns all changes for ALL resources of the given type
    (e.g., all Patient changes, all Observation changes)

    Query parameters:
    - _count: Number of entries per page (default 20)
    - _page: Page number (1-based, FHIR standard)
    - _offset: Offset for pagination (0-based, convenience)

    Returns:
        FHIR Bundle (history) with all versions of all resources of this type
    """
    logger.info(f"FHIR type-level history: {resource_type} by user {current_user.get('id', 'unknown')}")

    try:
        # Get pagination parameters
        params = dict(request.query_params)
        count = int(params.get('_count', 20))

        # Support both _page (FHIR standard) and _offset (convenience)
        if '_page' in params:
            page = int(params['_page'])
            if page < 1:
                page = 1
            offset = (page - 1) * count
        else:
            offset = int(params.get('_offset', 0))

        # Get resource service
        resource_service = await get_fhir_resource_service()

        # Get type-level history
        history, total = await resource_service.type_history(resource_type, count, offset)

        # Build Bundle entries
        entries = []
        for resource in history:
            entries.append({
                "fullUrl": f"urn:uuid:{resource['id']}",
                "resource": resource,
                "request": {
                    "method": "PUT",
                    "url": f"{resource_type}/{resource['id']}"
                }
            })

        # Build pagination links
        base_url = f"/fhir/r5/{resource_type}/_history"
        current_page = (offset // count) + 1
        links = []

        # Self link
        links.append({
            "relation": "self",
            "url": f"{base_url}?_page={current_page}&_count={count}"
        })

        # Next link
        if offset + count < total:
            links.append({
                "relation": "next",
                "url": f"{base_url}?_page={current_page + 1}&_count={count}"
            })

        # Previous link
        if offset > 0:
            links.append({
                "relation": "previous",
                "url": f"{base_url}?_page={max(1, current_page - 1)}&_count={count}"
            })

        bundle = {
            "resourceType": "Bundle",
            "type": "history",
            "total": total,
            "link": links,
            "entry": entries
        }

        return JSONResponse(content=bundle, status_code=200)

    except ValueError as e:
        logger.warning(f"Invalid type history request: {e}")
        outcome = build_operation_outcome("error", "invalid", str(e))
        return JSONResponse(content=outcome, status_code=400)

    except Exception as e:
        logger.error(f"Type history failed for {resource_type}: {e}", exc_info=True)
        outcome = build_operation_outcome("error", "exception", f"Internal server error: {str(e)}")
        return JSONResponse(content=outcome, status_code=500)


# ============================================================================
# SYSTEM-LEVEL HISTORY (GET /fhir/r5/_history) - FHIR R5 Standard
# ============================================================================

@router.get("/_history")
async def get_system_history(
    request: Request,
    current_user: Dict = Depends(require_any_staff)
):
    """
    Get version history for all resources in the system (system-level)

    Standard FHIR system-level history:
    - GET /fhir/r5/_history
    - GET /fhir/r5/_history?_count=100

    Returns changes for ALL resources across ALL types
    (complete audit trail of the entire FHIR system)

    Query parameters:
    - _count: Number of entries per page (default 20)
    - _page: Page number (1-based, FHIR standard)
    - _offset: Offset for pagination (0-based, convenience)

    Returns:
        FHIR Bundle (history) with all versions of all resources
    """
    logger.info(f"FHIR system-level history by user {current_user.get('id', 'unknown')}")

    try:
        # Get pagination parameters
        params = dict(request.query_params)
        count = int(params.get('_count', 20))

        # Support both _page (FHIR standard) and _offset (convenience)
        if '_page' in params:
            page = int(params['_page'])
            if page < 1:
                page = 1
            offset = (page - 1) * count
        else:
            offset = int(params.get('_offset', 0))

        # Get resource service
        resource_service = await get_fhir_resource_service()

        # Get system-level history
        history, total = await resource_service.system_history(count, offset)

        # Build Bundle entries
        entries = []
        for resource in history:
            entries.append({
                "fullUrl": f"urn:uuid:{resource['id']}",
                "resource": resource,
                "request": {
                    "method": "PUT",
                    "url": f"{resource['resourceType']}/{resource['id']}"
                }
            })

        # Build pagination links
        base_url = "/fhir/r5/_history"
        current_page = (offset // count) + 1
        links = []

        # Self link
        links.append({
            "relation": "self",
            "url": f"{base_url}?_page={current_page}&_count={count}"
        })

        # Next link
        if offset + count < total:
            links.append({
                "relation": "next",
                "url": f"{base_url}?_page={current_page + 1}&_count={count}"
            })

        # Previous link
        if offset > 0:
            links.append({
                "relation": "previous",
                "url": f"{base_url}?_page={max(1, current_page - 1)}&_count={count}"
            })

        bundle = {
            "resourceType": "Bundle",
            "type": "history",
            "total": total,
            "link": links,
            "entry": entries
        }

        return JSONResponse(content=bundle, status_code=200)

    except ValueError as e:
        logger.warning(f"Invalid system history request: {e}")
        outcome = build_operation_outcome("error", "invalid", str(e))
        return JSONResponse(content=outcome, status_code=400)

    except Exception as e:
        logger.error(f"System history failed: {e}", exc_info=True)
        outcome = build_operation_outcome("error", "exception", f"Internal server error: {str(e)}")
        return JSONResponse(content=outcome, status_code=500)


# ============================================================================
# METADATA (GET /fhir/r5/metadata)
# ============================================================================

@router.get("/metadata")
async def get_capability_statement():
    """
    Get FHIR CapabilityStatement (server metadata)

    Standard FHIR:
    - GET /fhir/r5/metadata

    Returns:
        CapabilityStatement describing server capabilities
    """
    capability_statement = {
        "resourceType": "CapabilityStatement",
        "status": "active",
        "date": "2025-11-19",
        "kind": "instance",
        "software": {
            "name": "Hospital Management System FHIR R5 Server",
            "version": "1.0.0"
        },
        "implementation": {
            "description": "FHIR R5 server for hospital management with ABDM integration",
            "url": "https://localhost:8001/fhir/r5"
        },
        "fhirVersion": "5.0.0",
        "format": ["application/fhir+json"],
        "rest": [{
            "mode": "server",
            "interaction": [
                {"code": "search-system"},
                {"code": "history-system"}
            ],
            "searchParam": [
                {"name": "_page", "type": "number", "documentation": "Page number for pagination (1-based, FHIR standard)"},
                {"name": "_count", "type": "number", "documentation": "Number of results per page (default 20)"},
                {"name": "_offset", "type": "number", "documentation": "Result offset for pagination (0-based, convenience parameter)"}
            ],
            "resource": [
                {
                    "type": "Patient",
                    "interaction": [
                        {"code": "read"},
                        {"code": "search-type"},
                        {"code": "create"},
                        {"code": "update"},
                        {"code": "delete"},
                        {"code": "history-instance"},
                        {"code": "history-type"}
                    ],
                    "versioning": "versioned",
                    "readHistory": True,
                    "searchParam": [
                        {"name": "_id", "type": "token"},
                        {"name": "identifier", "type": "token"},
                        {"name": "name", "type": "string"},
                        {"name": "gender", "type": "token"},
                        {"name": "birthdate", "type": "date"},
                        {"name": "_page", "type": "number"},
                        {"name": "_count", "type": "number"},
                        {"name": "_offset", "type": "number"}
                    ]
                },
                {
                    "type": "Observation",
                    "interaction": [
                        {"code": "read"},
                        {"code": "search-type"},
                        {"code": "create"},
                        {"code": "update"},
                        {"code": "delete"},
                        {"code": "history-instance"},
                        {"code": "history-type"}
                    ],
                    "versioning": "versioned",
                    "readHistory": True,
                    "searchParam": [
                        {"name": "_id", "type": "token"},
                        {"name": "patient", "type": "reference"},
                        {"name": "code", "type": "token"},
                        {"name": "date", "type": "date"},
                        {"name": "category", "type": "token"},
                        {"name": "status", "type": "token"},
                        {"name": "_page", "type": "number"},
                        {"name": "_count", "type": "number"},
                        {"name": "_offset", "type": "number"}
                    ]
                },
                {
                    "type": "Device",
                    "interaction": [
                        {"code": "read"},
                        {"code": "search-type"},
                        {"code": "create"},
                        {"code": "update"},
                        {"code": "delete"},
                        {"code": "history-instance"},
                        {"code": "history-type"}
                    ],
                    "versioning": "versioned",
                    "readHistory": True,
                    "searchParam": [
                        {"name": "_id", "type": "token"},
                        {"name": "identifier", "type": "token"},
                        {"name": "type", "type": "token"},
                        {"name": "status", "type": "token"},
                        {"name": "_page", "type": "number"},
                        {"name": "_count", "type": "number"},
                        {"name": "_offset", "type": "number"}
                    ]
                },
                {
                    "type": "Medication",
                    "interaction": [
                        {"code": "read"},
                        {"code": "search-type"},
                        {"code": "create"},
                        {"code": "update"},
                        {"code": "history-instance"},
                        {"code": "history-type"}
                    ],
                    "versioning": "versioned",
                    "readHistory": True,
                    "searchParam": [
                        {"name": "_id", "type": "token"},
                        {"name": "code", "type": "token"},
                        {"name": "status", "type": "token"},
                        {"name": "_page", "type": "number"},
                        {"name": "_count", "type": "number"},
                        {"name": "_offset", "type": "number"}
                    ]
                },
                {
                    "type": "MedicationAdministration",
                    "interaction": [
                        {"code": "read"},
                        {"code": "search-type"},
                        {"code": "create"},
                        {"code": "update"},
                        {"code": "history-instance"},
                        {"code": "history-type"}
                    ],
                    "versioning": "versioned",
                    "readHistory": True,
                    "searchParam": [
                        {"name": "_id", "type": "token"},
                        {"name": "patient", "type": "reference"},
                        {"name": "status", "type": "token"},
                        {"name": "effective-time", "type": "date"},
                        {"name": "_page", "type": "number"},
                        {"name": "_count", "type": "number"},
                        {"name": "_offset", "type": "number"}
                    ]
                }
            ]
        }]
    }

    return JSONResponse(content=capability_statement, status_code=200)
