"""
FHIR Resource Repository - Core CRUD operations with versioning
Handles all FHIR R5 resources in the fhirResources table
"""

import asyncpg
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import json
import uuid


class FHIRResourceRepository:
    """
    Universal repository for all FHIR R5 resources
    Supports: CRUD, search, versioning, soft delete
    """

    def __init__(self, db_pool: asyncpg.Pool):
        self.pool = db_pool

    async def create(
        self,
        resource_type: str,
        resource_id: str,
        resource: Dict[str, Any],
        status: Optional[str] = None,
        subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new FHIR resource

        Args:
            resource_type: Type of resource (Patient, Device, Observation, etc.)
            resource_id: Business ID (PAT001, DEV001, etc.)
            resource: Full FHIR R5 resource as dict
            status: Resource status for indexing
            subject: Patient reference for indexing (e.g., "Patient/PAT001")

        Returns:
            Created resource with metadata
        """
        async with self.pool.acquire() as conn:
            # Check if resource already exists
            existing = await conn.fetchrow("""
                SELECT id FROM fhirResources
                WHERE resourceType = $1 AND resourceId = $2 AND deleted = false
            """, resource_type, resource_id)

            if existing:
                raise ValueError(f"Resource {resource_type}/{resource_id} already exists")

            # Insert new resource
            row = await conn.fetchrow("""
                INSERT INTO fhirResources
                (resourceType, resourceId, resource, status, subject, versionId, deleted, createdAt, updatedAt)
                VALUES ($1, $2, $3, $4, $5, 1, false, NOW(), NOW())
                RETURNING id, resourceType, resourceId, resource, status, subject,
                          versionId, deleted, createdAt, updatedAt
            """, resource_type, resource_id, json.dumps(resource), status, subject)

            return self._row_to_dict(row)

    async def read(
        self,
        resource_type: str,
        resource_id: str,
        include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Read a FHIR resource by type and ID

        Args:
            resource_type: Type of resource
            resource_id: Resource ID
            include_deleted: Whether to include soft-deleted resources

        Returns:
            Resource dict or None if not found
        """
        async with self.pool.acquire() as conn:
            if include_deleted:
                row = await conn.fetchrow("""
                    SELECT id, resourceType, resourceId, resource, status, subject,
                           versionId, deleted, createdAt, updatedAt
                    FROM fhirResources
                    WHERE resourceType = $1 AND resourceId = $2
                    ORDER BY versionId DESC
                    LIMIT 1
                """, resource_type, resource_id)
            else:
                row = await conn.fetchrow("""
                    SELECT id, resourceType, resourceId, resource, status, subject,
                           versionId, deleted, createdAt, updatedAt
                    FROM fhirResources
                    WHERE resourceType = $1 AND resourceId = $2 AND deleted = false
                """, resource_type, resource_id)

            return self._row_to_dict(row) if row else None

    async def update(
        self,
        resource_type: str,
        resource_id: str,
        resource: Dict[str, Any],
        status: Optional[str] = None,
        subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update a FHIR resource (creates new version)

        Args:
            resource_type: Type of resource
            resource_id: Resource ID
            resource: Updated FHIR R5 resource
            status: Updated status
            subject: Updated subject reference

        Returns:
            Updated resource with new version
        """
        async with self.pool.acquire() as conn:
            # Get current version
            current = await conn.fetchrow("""
                SELECT versionId FROM fhirResources
                WHERE resourceType = $1 AND resourceId = $2 AND deleted = false
            """, resource_type, resource_id)

            if not current:
                raise ValueError(f"Resource {resource_type}/{resource_id} not found")

            new_version = current['versionid'] + 1

            # Update resource with new version
            row = await conn.fetchrow("""
                UPDATE fhirResources
                SET resource = $3,
                    status = $4,
                    subject = $5,
                    versionId = $6,
                    updatedAt = NOW()
                WHERE resourceType = $1 AND resourceId = $2 AND deleted = false
                RETURNING id, resourceType, resourceId, resource, status, subject,
                          versionId, deleted, createdAt, updatedAt
            """, resource_type, resource_id, json.dumps(resource), status, subject, new_version)

            return self._row_to_dict(row)

    async def delete(
        self,
        resource_type: str,
        resource_id: str,
        hard_delete: bool = False
    ) -> bool:
        """
        Delete a FHIR resource (soft delete by default)

        Args:
            resource_type: Type of resource
            resource_id: Resource ID
            hard_delete: If True, permanently delete; if False, soft delete

        Returns:
            True if deleted, False if not found
        """
        async with self.pool.acquire() as conn:
            if hard_delete:
                result = await conn.execute("""
                    DELETE FROM fhirResources
                    WHERE resourceType = $1 AND resourceId = $2
                """, resource_type, resource_id)
            else:
                result = await conn.execute("""
                    UPDATE fhirResources
                    SET deleted = true, updatedAt = NOW()
                    WHERE resourceType = $1 AND resourceId = $2 AND deleted = false
                """, resource_type, resource_id)

            return result != "UPDATE 0" and result != "DELETE 0"

    async def search(
        self,
        resource_type: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search FHIR resources with filters

        Args:
            resource_type: Type of resource to search
            filters: Search filters (status, subject, etc.)
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of matching resources
        """
        async with self.pool.acquire() as conn:
            query = """
                SELECT id, resourceType, resourceId, resource, status, subject,
                       versionId, deleted, createdAt, updatedAt
                FROM fhirResources
                WHERE resourceType = $1 AND deleted = false
            """
            params = [resource_type]
            param_counter = 2

            # Add filters
            if filters:
                if 'status' in filters:
                    query += f" AND status = ${param_counter}"
                    params.append(filters['status'])
                    param_counter += 1

                if 'subject' in filters:
                    query += f" AND subject = ${param_counter}"
                    params.append(filters['subject'])
                    param_counter += 1

                # JSONB search for other fields
                for key, value in filters.items():
                    if key not in ['status', 'subject']:
                        query += f" AND resource->>'{key}' = ${param_counter}"
                        params.append(str(value))
                        param_counter += 1

            query += f" ORDER BY createdAt DESC LIMIT ${param_counter} OFFSET ${param_counter + 1}"
            params.extend([limit, offset])

            rows = await conn.fetch(query, *params)
            return [self._row_to_dict(row) for row in rows]

    async def count(
        self,
        resource_type: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count FHIR resources matching filters

        Args:
            resource_type: Type of resource
            filters: Search filters

        Returns:
            Count of matching resources
        """
        async with self.pool.acquire() as conn:
            query = "SELECT COUNT(*) FROM fhirResources WHERE resourceType = $1 AND deleted = false"
            params = [resource_type]
            param_counter = 2

            if filters:
                if 'status' in filters:
                    query += f" AND status = ${param_counter}"
                    params.append(filters['status'])
                    param_counter += 1

                if 'subject' in filters:
                    query += f" AND subject = ${param_counter}"
                    params.append(filters['subject'])
                    param_counter += 1

            return await conn.fetchval(query, *params)

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert database row to dict"""
        if not row:
            return None

        return {
            'id': str(row['id']),
            'resourceType': row['resourcetype'],
            'resourceId': row['resourceid'],
            'resource': json.loads(row['resource']) if isinstance(row['resource'], str) else row['resource'],
            'status': row['status'],
            'subject': row['subject'],
            'versionId': row['versionid'],
            'deleted': row['deleted'],
            'createdAt': row['createdat'].isoformat() if row['createdat'] else None,
            'updatedAt': row['updatedat'].isoformat() if row['updatedat'] else None
        }
