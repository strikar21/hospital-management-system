"""
Consent Handler - FHIR R5
DPDP Act 2023 Compliance
Manages patient consent for data processing
Supports: GET, POST, PATCH (withdraw)
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import asyncpg
import uuid


class ConsentHandler:
    """
    Handle patient consent management
    Implements DPDP Act 2023 requirements:
    - Digital consent with signatures
    - Consent scope and purpose tracking
    - Consent withdrawal support
    - Audit trail of all consent actions
    """

    def __init__(self, db_pool: asyncpg.Pool):
        self.pool = db_pool

    async def create_consent(
        self,
        patient_id: str,
        scope: str,
        category: List[str],
        purpose_of_use: List[str],
        effective_start: datetime,
        effective_end: Optional[datetime] = None,
        grantor_signature: Optional[str] = None,
        witness_signature: Optional[str] = None,
        created_by: str = None
    ) -> Dict[str, Any]:
        """
        Create a new patient consent

        Args:
            patient_id: Patient reference (e.g., "Patient/PAT001")
            scope: Consent scope (patient-privacy, research, treatment)
            category: Consent categories (e.g., ["IDSCL", "RESEARCH"])
            purpose_of_use: Purpose codes (e.g., ["TREAT", "ETREAT"])
            effective_start: When consent becomes effective
            effective_end: When consent expires (optional)
            grantor_signature: Patient's digital signature (base64)
            witness_signature: Staff witness signature (base64)
            created_by: Staff ID who created consent

        Returns:
            Created consent record
        """
        # Validate patient_id format
        if not patient_id.startswith('Patient/'):
            patient_id = f'Patient/{patient_id}'

        # Validate staff reference
        if created_by and not created_by.startswith('Practitioner/'):
            created_by = f'Practitioner/{created_by}'

        async with self.pool.acquire() as conn:
            # Check for existing active consent
            existing = await conn.fetchrow("""
                SELECT id FROM fhirConsent
                WHERE patientId = $1
                  AND status = 'active'
                  AND (effectiveEnd IS NULL OR effectiveEnd > NOW())
            """, patient_id)

            if existing:
                raise ValueError(
                    f"Active consent already exists for patient {patient_id}. "
                    "Withdraw existing consent before creating a new one."
                )

            # Insert new consent
            consent_id = await conn.fetchval("""
                INSERT INTO fhirConsent
                (patientId, status, scope, category, purposeOfUse,
                 effectiveStart, effectiveEnd, grantorSignature, witnessSignature,
                 createdAt, createdBy)
                VALUES ($1, 'active', $2, $3, $4, $5, $6, $7, $8, NOW(), $9)
                RETURNING id
            """, patient_id, scope, category, purpose_of_use,
               effective_start, effective_end, grantor_signature,
               witness_signature, created_by)

            # Return created consent
            return await self.get_consent(str(consent_id))

    async def get_consent(self, consent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get consent by ID

        Args:
            consent_id: Consent UUID

        Returns:
            Consent record or None
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, patientId, status, scope, category, purposeOfUse,
                       effectiveStart, effectiveEnd, grantorSignature, witnessSignature,
                       createdAt, createdBy, withdrawnAt, withdrawnBy
                FROM fhirConsent
                WHERE id = $1
            """, uuid.UUID(consent_id))

            return self._row_to_dict(row) if row else None

    async def get_active_consent(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """
        Get active consent for a patient

        Args:
            patient_id: Patient ID (with or without "Patient/" prefix)

        Returns:
            Active consent or None
        """
        if not patient_id.startswith('Patient/'):
            patient_id = f'Patient/{patient_id}'

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, patientId, status, scope, category, purposeOfUse,
                       effectiveStart, effectiveEnd, grantorSignature, witnessSignature,
                       createdAt, createdBy, withdrawnAt, withdrawnBy
                FROM fhirConsent
                WHERE patientId = $1
                  AND status = 'active'
                  AND effectiveStart <= NOW()
                  AND (effectiveEnd IS NULL OR effectiveEnd > NOW())
                ORDER BY createdAt DESC
                LIMIT 1
            """, patient_id)

            return self._row_to_dict(row) if row else None

    async def search_consents(
        self,
        patient_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search consents with filters

        Args:
            patient_id: Filter by patient
            status: Filter by status (active, withdrawn, expired)
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of consent records
        """
        query = """
            SELECT id, patientId, status, scope, category, purposeOfUse,
                   effectiveStart, effectiveEnd, grantorSignature, witnessSignature,
                   createdAt, createdBy, withdrawnAt, withdrawnBy
            FROM fhirConsent
            WHERE 1=1
        """
        params = []
        param_counter = 1

        if patient_id:
            if not patient_id.startswith('Patient/'):
                patient_id = f'Patient/{patient_id}'
            query += f" AND patientId = ${param_counter}"
            params.append(patient_id)
            param_counter += 1

        if status:
            query += f" AND status = ${param_counter}"
            params.append(status)
            param_counter += 1

        query += f" ORDER BY createdAt DESC LIMIT ${param_counter} OFFSET ${param_counter + 1}"
        params.extend([limit, offset])

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [self._row_to_dict(row) for row in rows]

    async def withdraw_consent(
        self,
        consent_id: str,
        withdrawn_by: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Withdraw a consent (DPDP Act 2023 right to withdraw)

        Args:
            consent_id: Consent UUID
            withdrawn_by: Staff ID who processed withdrawal
            reason: Optional reason for withdrawal

        Returns:
            Updated consent record
        """
        if not withdrawn_by.startswith('Practitioner/'):
            withdrawn_by = f'Practitioner/{withdrawn_by}'

        async with self.pool.acquire() as conn:
            # Update consent status
            result = await conn.execute("""
                UPDATE fhirConsent
                SET status = 'withdrawn',
                    withdrawnAt = NOW(),
                    withdrawnBy = $2
                WHERE id = $1 AND status = 'active'
            """, uuid.UUID(consent_id), withdrawn_by)

            if result == "UPDATE 0":
                raise ValueError(
                    f"Consent {consent_id} not found or already withdrawn"
                )

            return await self.get_consent(consent_id)

    async def check_consent(
        self,
        patient_id: str,
        purpose: str
    ) -> bool:
        """
        Check if patient has active consent for a specific purpose

        Args:
            patient_id: Patient ID
            purpose: Purpose code (TREAT, ETREAT, HPAYMT, etc.)

        Returns:
            True if consent exists and is active, False otherwise
        """
        if not patient_id.startswith('Patient/'):
            patient_id = f'Patient/{patient_id}'

        async with self.pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM fhirConsent
                    WHERE patientId = $1
                      AND status = 'active'
                      AND effectiveStart <= NOW()
                      AND (effectiveEnd IS NULL OR effectiveEnd > NOW())
                      AND $2 = ANY(purposeOfUse)
                )
            """, patient_id, purpose)

            return result

    async def expire_old_consents(self) -> int:
        """
        Mark expired consents as 'expired'
        Should be run periodically (e.g., daily cron job)

        Returns:
            Number of consents expired
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE fhirConsent
                SET status = 'expired'
                WHERE status = 'active'
                  AND effectiveEnd IS NOT NULL
                  AND effectiveEnd < NOW()
            """)

            # Parse result like "UPDATE 5"
            count = int(result.split()[-1]) if result else 0
            return count

    def _row_to_dict(self, row) -> Optional[Dict[str, Any]]:
        """Convert database row to FHIR Consent resource"""
        if not row:
            return None

        # Build FHIR R5 Consent resource
        consent = {
            "resourceType": "Consent",
            "id": str(row['id']),
            "status": row['status'],
            "scope": {
                "coding": [{"code": row['scope']}]
            },
            "category": [
                {"coding": [{"code": cat}]} for cat in row['category']
            ],
            "patient": {
                "reference": row['patientid']
            },
            "dateTime": row['createdat'].isoformat() if row['createdat'] else None,
            "provision": {
                "type": "permit",
                "period": {
                    "start": row['effectivestart'].isoformat() if row['effectivestart'] else None,
                    "end": row['effectiveend'].isoformat() if row['effectiveend'] else None
                },
                "purpose": [
                    {"code": purpose} for purpose in row['purposeofuse']
                ]
            }
        }

        # Add signatures if present
        if row['grantorsignature']:
            consent['signature'] = consent.get('signature', [])
            consent['signature'].append({
                "type": [{"code": "1.2.840.10065.1.12.1.7"}],  # Consent signature
                "when": row['createdat'].isoformat() if row['createdat'] else None,
                "who": {"reference": row['patientid']},
                "data": row['grantorsignature']
            })

        if row['witnesssignature']:
            consent['signature'] = consent.get('signature', [])
            consent['signature'].append({
                "type": [{"code": "1.2.840.10065.1.12.1.16"}],  # Witness signature
                "when": row['createdat'].isoformat() if row['createdat'] else None,
                "who": {"reference": row['createdby']},
                "data": row['witnesssignature']
            })

        # Add withdrawal info if withdrawn
        if row['withdrawnat']:
            consent['verification'] = [{
                "verified": False,
                "verificationDate": row['withdrawnat'].isoformat(),
                "verifiedBy": {"reference": row['withdrawnby']}
            }]

        # Add metadata
        consent['meta'] = {
            "lastUpdated": row['createdat'].isoformat() if row['createdat'] else None
        }

        # Add internal metadata (non-FHIR)
        consent['_internal'] = {
            "createdBy": row['createdby'],
            "withdrawnAt": row['withdrawnat'].isoformat() if row['withdrawnat'] else None,
            "withdrawnBy": row['withdrawnby']
        }

        return consent
