"""
FHIR R5 REST API Endpoints
Standard FHIR REST API implementation
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncpg

from .handlers import (
    PatientHandler,
    DeviceHandler,
    ObservationHandler,
    DeviceAssociationHandler
)
from .repository import FHIRResourceRepository


# Router for all FHIR R5 endpoints
fhir_router = APIRouter(prefix="/fhir/R5", tags=["FHIR R5"])


# Dependency to get database pool (will be injected from main app)
async def get_db_pool() -> asyncpg.Pool:
    """Get database connection pool"""
    # This will be replaced with actual dependency injection
    raise HTTPException(500, "Database pool not configured")


# ============================================================================
# Patient Endpoints
# ============================================================================

@fhir_router.get("/Patient/{patient_id}")
async def get_patient(
    patient_id: str,
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Get patient by ID (from HMS or cache)"""
    repository = FHIRResourceRepository(pool)
    handler = PatientHandler(repository)

    patient = await handler.get_patient(patient_id)

    if not patient:
        raise HTTPException(404, f"Patient {patient_id} not found")

    return patient


@fhir_router.get("/Patient")
async def search_patients(
    identifier: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    _count: int = Query(100, alias="_count"),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Search patients"""
    repository = FHIRResourceRepository(pool)
    handler = PatientHandler(repository)

    patients = await handler.search_patients(
        identifier=identifier,
        name=name,
        limit=_count
    )

    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(patients),
        "entry": [{"resource": p} for p in patients]
    }


# ============================================================================
# Device Endpoints
# ============================================================================

@fhir_router.post("/Device")
async def create_device(
    device: Dict[str, Any],
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Create a new device"""
    repository = FHIRResourceRepository(pool)
    handler = DeviceHandler(repository)

    try:
        created_device = await handler.create_device(device)
        return created_device
    except ValueError as e:
        raise HTTPException(400, str(e))


@fhir_router.get("/Device/{device_id}")
async def get_device(
    device_id: str,
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Get device by ID"""
    repository = FHIRResourceRepository(pool)
    handler = DeviceHandler(repository)

    device = await handler.get_device(device_id)

    if not device:
        raise HTTPException(404, f"Device {device_id} not found")

    return device


@fhir_router.patch("/Device/{device_id}")
async def update_device(
    device_id: str,
    updates: Dict[str, Any],
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Update device (partial update)"""
    repository = FHIRResourceRepository(pool)
    handler = DeviceHandler(repository)

    try:
        updated_device = await handler.update_device(device_id, updates)
        return updated_device
    except ValueError as e:
        raise HTTPException(404, str(e))


@fhir_router.get("/Device")
async def search_devices(
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    _count: int = Query(100, alias="_count"),
    _offset: int = Query(0, alias="_offset"),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Search devices"""
    repository = FHIRResourceRepository(pool)
    handler = DeviceHandler(repository)

    devices = await handler.search_devices(
        status=status,
        device_type=type,
        limit=_count,
        offset=_offset
    )

    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(devices),
        "entry": [{"resource": d} for d in devices]
    }


# ============================================================================
# Observation Endpoints
# ============================================================================

@fhir_router.post("/Observation")
async def create_observation(
    observation: Dict[str, Any],
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Create a new observation"""
    handler = ObservationHandler(pool)

    try:
        created_obs = await handler.create_observation(observation)
        return created_obs
    except ValueError as e:
        raise HTTPException(400, str(e))


@fhir_router.get("/Observation")
async def search_observations(
    patient: Optional[str] = Query(None),
    code: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    device: Optional[str] = Query(None),
    date_ge: Optional[str] = Query(None, alias="date"),  # date=ge2025-11-21
    _count: int = Query(100, alias="_count"),
    _offset: int = Query(0, alias="_offset"),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Search observations"""
    handler = ObservationHandler(pool)

    # Parse patient ID from reference
    patient_id = patient.replace('Patient/', '') if patient else None

    # Parse device ID from reference
    device_id = device.replace('Device/', '') if device else None

    # Parse date filter (simplified - just handle "ge" prefix)
    start_time = None
    if date_ge:
        if date_ge.startswith('ge'):
            date_str = date_ge[2:]
            start_time = datetime.fromisoformat(date_str.replace('Z', '+00:00'))

    observations = await handler.get_observations(
        patient_id=patient_id,
        code=code,
        category=category,
        device_id=device_id,
        start_time=start_time,
        limit=_count,
        offset=_offset
    )

    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(observations),
        "entry": [{"resource": o} for o in observations]
    }


@fhir_router.get("/Observation/$stats")
async def get_observation_stats(
    patient: str = Query(...),
    code: str = Query(...),
    date_ge: Optional[str] = Query(None),
    date_le: Optional[str] = Query(None),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Get observation statistics (custom operation)"""
    handler = ObservationHandler(pool)

    # Parse patient ID
    patient_id = patient.replace('Patient/', '')

    # Parse dates
    start_time = None
    end_time = None

    if date_ge:
        start_time = datetime.fromisoformat(date_ge.replace('Z', '+00:00'))

    if date_le:
        end_time = datetime.fromisoformat(date_le.replace('Z', '+00:00'))

    stats = await handler.get_observation_stats(
        patient_id=patient_id,
        code=code,
        start_time=start_time,
        end_time=end_time
    )

    return {
        "resourceType": "Parameters",
        "parameter": [
            {"name": "count", "valueInteger": stats['count']},
            {"name": "min", "valueDecimal": stats['min']},
            {"name": "max", "valueDecimal": stats['max']},
            {"name": "avg", "valueDecimal": stats['avg']}
        ]
    }


# ============================================================================
# DeviceAssociation Endpoints
# ============================================================================

@fhir_router.post("/DeviceAssociation")
async def create_device_association(
    association: Dict[str, Any],
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Create a new device-patient association"""
    repository = FHIRResourceRepository(pool)
    handler = DeviceAssociationHandler(repository)

    try:
        created_assoc = await handler.create_association(association)
        return created_assoc
    except ValueError as e:
        raise HTTPException(400, str(e))


@fhir_router.get("/DeviceAssociation/{association_id}")
async def get_device_association(
    association_id: str,
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Get device association by ID"""
    repository = FHIRResourceRepository(pool)
    handler = DeviceAssociationHandler(repository)

    association = await handler.get_association(association_id)

    if not association:
        raise HTTPException(404, f"DeviceAssociation {association_id} not found")

    return association


@fhir_router.patch("/DeviceAssociation/{association_id}")
async def update_device_association(
    association_id: str,
    updates: Dict[str, Any],
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Update device association"""
    repository = FHIRResourceRepository(pool)
    handler = DeviceAssociationHandler(repository)

    try:
        updated_assoc = await handler.update_association(association_id, updates)
        return updated_assoc
    except ValueError as e:
        raise HTTPException(404, str(e))


@fhir_router.get("/DeviceAssociation")
async def search_device_associations(
    subject: Optional[str] = Query(None),
    device: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    _count: int = Query(100, alias="_count"),
    _offset: int = Query(0, alias="_offset"),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Search device associations"""
    repository = FHIRResourceRepository(pool)
    handler = DeviceAssociationHandler(repository)

    # Parse patient ID from subject
    patient_id = subject.replace('Patient/', '') if subject else None

    # Parse device ID from device
    device_id = device.replace('Device/', '') if device else None

    associations = await handler.search_associations(
        patient_id=patient_id,
        device_id=device_id,
        status=status,
        limit=_count,
        offset=_offset
    )

    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(associations),
        "entry": [{"resource": a} for a in associations]
    }


# ============================================================================
# Capability Statement (FHIR Metadata)
# ============================================================================

@fhir_router.get("/metadata")
async def get_capability_statement():
    """Get FHIR server capability statement"""
    return {
        "resourceType": "CapabilityStatement",
        "fhirVersion": "5.0.0",
        "status": "active",
        "date": "2025-11-21",
        "kind": "instance",
        "software": {
            "name": "Hospital IoT FHIR R5 Server",
            "version": "1.0.0"
        },
        "implementation": {
            "description": "Hospital Management System FHIR R5 API"
        },
        "format": ["json"],
        "rest": [
            {
                "mode": "server",
                "resource": [
                    {
                        "type": "Patient",
                        "interaction": [{"code": "read"}, {"code": "search-type"}]
                    },
                    {
                        "type": "Device",
                        "interaction": [{"code": "create"}, {"code": "read"},
                                      {"code": "update"}, {"code": "search-type"}]
                    },
                    {
                        "type": "Observation",
                        "interaction": [{"code": "create"}, {"code": "search-type"}]
                    },
                    {
                        "type": "DeviceAssociation",
                        "interaction": [{"code": "create"}, {"code": "read"},
                                      {"code": "update"}, {"code": "search-type"}]
                    }
                ]
            }
        ]
    }
