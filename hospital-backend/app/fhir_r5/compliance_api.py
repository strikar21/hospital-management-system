"""
FHIR R5 Compliance API Endpoints
Consent and AuditEvent endpoints for DPDP Act 2023 + HIPAA 2025 compliance
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, Dict, Any
from datetime import datetime
import asyncpg

from .handlers import ConsentHandler, AuditEventHandler


# Router for compliance endpoints
compliance_router = APIRouter(prefix="/fhir/R5", tags=["FHIR R5 Compliance"])


# Dependency to get database pool
async def get_db_pool() -> asyncpg.Pool:
    """Get database connection pool"""
    raise HTTPException(500, "Database pool not configured")


# ============================================================================
# Consent Endpoints (DPDP Act 2023)
# ============================================================================

@compliance_router.post("/Consent")
async def create_consent(
    patient_id: str = Query(..., description="Patient ID"),
    scope: str = Query(..., description="Consent scope (patient-privacy, research, treatment)"),
    category: str = Query(..., description="Comma-separated categories (IDSCL,RESEARCH)"),
    purpose_of_use: str = Query(..., description="Comma-separated purposes (TREAT,ETREAT,HPAYMT)"),
    effective_start: str = Query(..., description="ISO datetime when consent starts"),
    effective_end: Optional[str] = Query(None, description="ISO datetime when consent ends"),
    grantor_signature: Optional[str] = Query(None, description="Base64 patient signature"),
    witness_signature: Optional[str] = Query(None, description="Base64 witness signature"),
    created_by: str = Query(..., description="Staff ID creating consent"),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Create a new patient consent (DPDP Act 2023 compliance)"""
    handler = ConsentHandler(pool)

    # Parse dates
    start_date = datetime.fromisoformat(effective_start.replace('Z', '+00:00'))
    end_date = datetime.fromisoformat(effective_end.replace('Z', '+00:00')) if effective_end else None

    # Parse comma-separated lists
    category_list = [c.strip() for c in category.split(',')]
    purpose_list = [p.strip() for p in purpose_of_use.split(',')]

    try:
        consent = await handler.create_consent(
            patient_id=patient_id,
            scope=scope,
            category=category_list,
            purpose_of_use=purpose_list,
            effective_start=start_date,
            effective_end=end_date,
            grantor_signature=grantor_signature,
            witness_signature=witness_signature,
            created_by=created_by
        )
        return consent
    except ValueError as e:
        raise HTTPException(400, str(e))


@compliance_router.get("/Consent/{consent_id}")
async def get_consent(
    consent_id: str,
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Get consent by ID"""
    handler = ConsentHandler(pool)

    consent = await handler.get_consent(consent_id)

    if not consent:
        raise HTTPException(404, f"Consent {consent_id} not found")

    return consent


@compliance_router.get("/Consent")
async def search_consents(
    patient: Optional[str] = Query(None, description="Patient ID or reference"),
    status: Optional[str] = Query(None, description="Consent status (active, withdrawn, expired)"),
    _count: int = Query(100, alias="_count"),
    _offset: int = Query(0, alias="_offset"),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Search consents"""
    handler = ConsentHandler(pool)

    # Parse patient reference
    patient_id = patient.replace('Patient/', '') if patient else None

    consents = await handler.search_consents(
        patient_id=patient_id,
        status=status,
        limit=_count,
        offset=_offset
    )

    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(consents),
        "entry": [{"resource": c} for c in consents]
    }


@compliance_router.patch("/Consent/{consent_id}")
async def withdraw_consent(
    consent_id: str,
    withdrawn_by: str = Query(..., description="Staff ID who processed withdrawal"),
    reason: Optional[str] = Query(None, description="Reason for withdrawal"),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Withdraw a consent (DPDP Act 2023 right to withdraw)"""
    handler = ConsentHandler(pool)

    try:
        consent = await handler.withdraw_consent(
            consent_id=consent_id,
            withdrawn_by=withdrawn_by,
            reason=reason
        )
        return consent
    except ValueError as e:
        raise HTTPException(404, str(e))


@compliance_router.get("/Consent/$check")
async def check_consent(
    patient: str = Query(..., description="Patient ID"),
    purpose: str = Query(..., description="Purpose code (TREAT, ETREAT, etc.)"),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Check if patient has active consent for a specific purpose (custom operation)"""
    handler = ConsentHandler(pool)

    has_consent = await handler.check_consent(patient, purpose)

    return {
        "resourceType": "Parameters",
        "parameter": [
            {"name": "patient", "valueString": patient},
            {"name": "purpose", "valueString": purpose},
            {"name": "hasConsent", "valueBoolean": has_consent}
        ]
    }


# ============================================================================
# AuditEvent Endpoints (DPDP + HIPAA)
# ============================================================================

@compliance_router.get("/AuditEvent")
async def search_audit_events(
    agent: Optional[str] = Query(None, description="Staff ID or reference"),
    entity_type: Optional[str] = Query(None, description="Resource type (Patient, Device, etc.)"),
    entity_id: Optional[str] = Query(None, description="Resource ID"),
    action: Optional[str] = Query(None, description="Action code (C, R, U, D, E)"),
    date_ge: Optional[str] = Query(None, alias="date", description="Start date (ge2025-11-21)"),
    _count: int = Query(100, alias="_count"),
    _offset: int = Query(0, alias="_offset"),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Search audit events (DPDP + HIPAA compliance)"""
    handler = AuditEventHandler(pool)

    # Parse agent reference
    agent_id = agent.replace('Practitioner/', '') if agent else None

    # Parse date filter
    start_date = None
    if date_ge and date_ge.startswith('ge'):
        date_str = date_ge[2:]
        start_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))

    events = await handler.search_audit_events(
        agent_id=agent_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        start_date=start_date,
        limit=_count,
        offset=_offset
    )

    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(events),
        "entry": [{"resource": e} for e in events]
    }


@compliance_router.get("/AuditEvent/$patient-log")
async def get_patient_access_log(
    patient: str = Query(..., description="Patient ID"),
    date_ge: Optional[str] = Query(None, description="Start date"),
    _count: int = Query(100, alias="_count"),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Get access log for a specific patient (custom operation)"""
    handler = AuditEventHandler(pool)

    # Parse date
    start_date = None
    if date_ge:
        start_date = datetime.fromisoformat(date_ge.replace('Z', '+00:00'))

    events = await handler.get_patient_access_log(
        patient_id=patient.replace('Patient/', ''),
        start_date=start_date,
        limit=_count
    )

    return {
        "resourceType": "Bundle",
        "type": "history",
        "total": len(events),
        "entry": [{"resource": e} for e in events]
    }


@compliance_router.get("/AuditEvent/$staff-activity")
async def get_staff_activity_log(
    staff: str = Query(..., description="Staff ID"),
    date_ge: Optional[str] = Query(None, description="Start date"),
    _count: int = Query(100, alias="_count"),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Get activity log for a specific staff member (custom operation)"""
    handler = AuditEventHandler(pool)

    # Parse date
    start_date = None
    if date_ge:
        start_date = datetime.fromisoformat(date_ge.replace('Z', '+00:00'))

    events = await handler.get_staff_activity_log(
        staff_id=staff.replace('Practitioner/', ''),
        start_date=start_date,
        limit=_count
    )

    return {
        "resourceType": "Bundle",
        "type": "history",
        "total": len(events),
        "entry": [{"resource": e} for e in events]
    }


@compliance_router.get("/AuditEvent/$summary")
async def get_audit_summary(
    date_ge: Optional[str] = Query(None, description="Start date"),
    date_le: Optional[str] = Query(None, description="End date"),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Get audit event summary statistics (custom operation)"""
    handler = AuditEventHandler(pool)

    # Parse dates
    start_date = None
    end_date = None

    if date_ge:
        start_date = datetime.fromisoformat(date_ge.replace('Z', '+00:00'))

    if date_le:
        end_date = datetime.fromisoformat(date_le.replace('Z', '+00:00'))

    summary = await handler.get_access_summary(
        start_date=start_date,
        end_date=end_date
    )

    return {
        "resourceType": "Parameters",
        "parameter": [
            {"name": "totalEvents", "valueInteger": summary['totalEvents']},
            {"name": "uniqueAgents", "valueInteger": summary['uniqueAgents']},
            {"name": "uniqueEntities", "valueInteger": summary['uniqueEntities']},
            {"name": "readEvents", "valueInteger": summary['readEvents']},
            {"name": "createEvents", "valueInteger": summary['createEvents']},
            {"name": "updateEvents", "valueInteger": summary['updateEvents']},
            {"name": "deleteEvents", "valueInteger": summary['deleteEvents']},
            {"name": "failedEvents", "valueInteger": summary['failedEvents']}
        ]
    }
