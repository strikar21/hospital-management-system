"""
AuditEvent Handler - FHIR R5
DPDP Act 2023 + HIPAA 2025 Compliance
Logs all access to patient data
POST only (auto-logged by middleware)
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import asyncpg
import uuid


class AuditEventHandler:
    """
    Handle audit event logging
    Implements DPDP Act 2023 and HIPAA 2025 requirements:
    - Log all access to patient data (Create, Read, Update, Delete)
    - Track who accessed what, when, and why
    - 6-year retention for HIPAA compliance
    - IP address and user agent tracking
    """

    def __init__(self, db_pool: asyncpg.Pool):
        self.pool = db_pool

    async def log_access(
        self,
        action: str,
        agent_id: str,
        agent_role: str,
        entity_type: str,
        entity_id: str,
        outcome: str = 'success',
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        purpose_of_event: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Log an access event

        Args:
            action: Action performed (C, R, U, D, E)
                C = Create, R = Read, U = Update, D = Delete, E = Execute
            agent_id: Staff ID who performed action (e.g., "STF000001")
            agent_role: Role of agent (doctor, nurse, admin, technician)
            entity_type: Type of resource accessed (Patient, Device, etc.)
            entity_id: ID of resource accessed
            outcome: Outcome of action (success, failure)
            ip_address: IP address of request
            user_agent: User agent string
            purpose_of_event: Purpose of access (TREAT, ETREAT, HPAYMT)

        Returns:
            Created audit event
        """
        # Validate action
        if action not in ['C', 'R', 'U', 'D', 'E']:
            raise ValueError(f"Invalid action: {action}. Must be C, R, U, D, or E")

        # Ensure agent_id has proper prefix
        if not agent_id.startswith('Practitioner/'):
            agent_id = f'Practitioner/{agent_id}'

        async with self.pool.acquire() as conn:
            audit_id = await conn.fetchval("""
                INSERT INTO fhirAuditEvent
                (action, outcome, agentId, agentRole, entityType, entityId,
                 recorded, ipAddress, userAgent, purposeOfEvent, expiresAt)
                VALUES ($1, $2, $3, $4, $5, $6, NOW(), $7, $8, $9, NOW() + INTERVAL '6 years')
                RETURNING id
            """, action, outcome, agent_id, agent_role, entity_type, entity_id,
               ip_address, user_agent, purpose_of_event)

            return await self.get_audit_event(str(audit_id))

    async def get_audit_event(self, audit_id: str) -> Optional[Dict[str, Any]]:
        """
        Get audit event by ID

        Args:
            audit_id: Audit event UUID

        Returns:
            Audit event record or None
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, action, outcome, agentId, agentRole, entityType, entityId,
                       recorded, ipAddress, userAgent, purposeOfEvent, expiresAt
                FROM fhirAuditEvent
                WHERE id = $1
            """, uuid.UUID(audit_id))

            return self._row_to_fhir(row) if row else None

    async def search_audit_events(
        self,
        agent_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search audit events with filters

        Args:
            agent_id: Filter by agent (staff member)
            entity_type: Filter by entity type (Patient, Device, etc.)
            entity_id: Filter by specific entity ID
            action: Filter by action (C, R, U, D, E)
            start_date: Start of date range
            end_date: End of date range
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of audit events
        """
        query = """
            SELECT id, action, outcome, agentId, agentRole, entityType, entityId,
                   recorded, ipAddress, userAgent, purposeOfEvent, expiresAt
            FROM fhirAuditEvent
            WHERE 1=1
        """
        params = []
        param_counter = 1

        if agent_id:
            if not agent_id.startswith('Practitioner/'):
                agent_id = f'Practitioner/{agent_id}'
            query += f" AND agentId = ${param_counter}"
            params.append(agent_id)
            param_counter += 1

        if entity_type:
            query += f" AND entityType = ${param_counter}"
            params.append(entity_type)
            param_counter += 1

        if entity_id:
            query += f" AND entityId = ${param_counter}"
            params.append(entity_id)
            param_counter += 1

        if action:
            query += f" AND action = ${param_counter}"
            params.append(action)
            param_counter += 1

        if start_date:
            query += f" AND recorded >= ${param_counter}"
            params.append(start_date)
            param_counter += 1

        if end_date:
            query += f" AND recorded <= ${param_counter}"
            params.append(end_date)
            param_counter += 1

        query += f" ORDER BY recorded DESC LIMIT ${param_counter} OFFSET ${param_counter + 1}"
        params.extend([limit, offset])

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [self._row_to_fhir(row) for row in rows]

    async def get_patient_access_log(
        self,
        patient_id: str,
        start_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all access events for a specific patient

        Args:
            patient_id: Patient ID
            start_date: Start date for log
            limit: Maximum results

        Returns:
            List of audit events related to this patient
        """
        return await self.search_audit_events(
            entity_type='Patient',
            entity_id=patient_id,
            start_date=start_date,
            limit=limit
        )

    async def get_staff_activity_log(
        self,
        staff_id: str,
        start_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all activity by a specific staff member

        Args:
            staff_id: Staff ID
            start_date: Start date for log
            limit: Maximum results

        Returns:
            List of audit events by this staff member
        """
        return await self.search_audit_events(
            agent_id=staff_id,
            start_date=start_date,
            limit=limit
        )

    async def get_access_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get summary statistics of access events

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Summary statistics
        """
        query = """
            SELECT
                COUNT(*) as total_events,
                COUNT(DISTINCT agentId) as unique_agents,
                COUNT(DISTINCT entityId) as unique_entities,
                COUNT(*) FILTER (WHERE action = 'R') as read_events,
                COUNT(*) FILTER (WHERE action = 'C') as create_events,
                COUNT(*) FILTER (WHERE action = 'U') as update_events,
                COUNT(*) FILTER (WHERE action = 'D') as delete_events,
                COUNT(*) FILTER (WHERE outcome = 'failure') as failed_events
            FROM fhirAuditEvent
            WHERE 1=1
        """
        params = []
        param_counter = 1

        if start_date:
            query += f" AND recorded >= ${param_counter}"
            params.append(start_date)
            param_counter += 1

        if end_date:
            query += f" AND recorded <= ${param_counter}"
            params.append(end_date)
            param_counter += 1

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)

        return {
            "totalEvents": row['total_events'],
            "uniqueAgents": row['unique_agents'],
            "uniqueEntities": row['unique_entities'],
            "readEvents": row['read_events'],
            "createEvents": row['create_events'],
            "updateEvents": row['update_events'],
            "deleteEvents": row['delete_events'],
            "failedEvents": row['failed_events']
        }

    async def cleanup_expired_events(self) -> int:
        """
        Delete expired audit events (after 6 years)
        Should be run periodically (e.g., monthly cron job)

        Returns:
            Number of events deleted
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM fhirAuditEvent
                WHERE expiresAt < NOW()
            """)

            count = int(result.split()[-1]) if result else 0
            return count

    def _row_to_fhir(self, row) -> Optional[Dict[str, Any]]:
        """Convert database row to FHIR R5 AuditEvent resource"""
        if not row:
            return None

        # Map action codes to FHIR display names
        action_map = {
            'C': 'Create',
            'R': 'Read',
            'U': 'Update',
            'D': 'Delete',
            'E': 'Execute'
        }

        audit_event = {
            "resourceType": "AuditEvent",
            "id": str(row['id']),
            "type": {
                "code": row['action'],
                "display": action_map.get(row['action'], 'Unknown')
            },
            "recorded": row['recorded'].isoformat() if row['recorded'] else None,
            "outcome": row['outcome'],
            "agent": [{
                "who": {"reference": row['agentid']},
                "role": [{"text": row['agentrole']}]
            }],
            "entity": [{
                "what": {
                    "reference": f"{row['entitytype']}/{row['entityid']}"
                }
            }],
            "source": {
                "observer": {"reference": row['agentid']}
            }
        }

        # Add IP address if present
        if row['ipaddress']:
            audit_event['source']['site'] = str(row['ipaddress'])

        # Add user agent if present
        if row['useragent']:
            audit_event['agent'][0]['network'] = {
                "type": "5",  # URI
                "address": row['useragent']
            }

        # Add purpose if present
        if row['purposeofevent']:
            audit_event['purposeOfEvent'] = [{
                "coding": [{"code": row['purposeofevent']}]
            }]

        # Add metadata
        audit_event['meta'] = {
            "lastUpdated": row['recorded'].isoformat() if row['recorded'] else None
        }

        # Add internal metadata (non-FHIR)
        audit_event['_internal'] = {
            "expiresAt": row['expiresat'].isoformat() if row['expiresat'] else None
        }

        return audit_event
