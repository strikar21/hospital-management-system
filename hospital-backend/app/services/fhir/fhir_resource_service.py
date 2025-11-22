"""
FHIR Resource Service - Generic CRUD operations for all FHIR R5 resources

This is the core service that handles CREATE, READ, UPDATE, DELETE, SEARCH
operations for ALL FHIR resource types (Patient, Observation, Device, etc.)

All resources are stored in the unified `fhir_resources` table.
"""

import re
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncpg
from uuid import UUID

logger = logging.getLogger(__name__)


class FhirResourceService:
    """
    Generic FHIR R5 resource service

    Handles all FHIR resources in a unified way.
    Validates FHIR resources before storage.
    Automatically extracts search fields (identifiers, references).
    """

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize FHIR resource service

        Args:
            pool: PostgreSQL connection pool
        """
        self.pool = pool

    # ========================================================================
    # VALIDATION
    # ========================================================================

    def validate_fhir_id(self, resource_type: str, resource_id: str) -> None:
        """
        Validate FHIR resource ID format

        FHIR Spec:
        - Must be alphanumeric + dash/underscore only
        - Max length 64 characters
        - Case-sensitive

        Args:
            resource_type: FHIR resource type
            resource_id: Resource ID to validate

        Raises:
            ValueError: If ID is invalid
        """
        # Check not empty
        if not resource_id:
            raise ValueError(f"Resource ID cannot be empty")

        # Check alphanumeric + dash/underscore only
        if not re.match(r'^[A-Za-z0-9\-_.]+$', resource_id):
            raise ValueError(
                f"Invalid FHIR ID '{resource_id}': must contain only alphanumeric, dash, underscore, or period"
            )

        # Check length (FHIR spec: max 64 chars)
        if len(resource_id) > 64:
            raise ValueError(
                f"Invalid FHIR ID '{resource_id}': exceeds maximum length of 64 characters"
            )

    def validate_fhir_resource(self, resource: Dict[str, Any]) -> None:
        """
        Validate FHIR resource structure

        Args:
            resource: FHIR resource dict

        Raises:
            ValueError: If resource is invalid
        """
        # Check required fields
        if not resource.get('resourceType'):
            raise ValueError("FHIR resource missing 'resourceType'")

        if not resource.get('id'):
            raise ValueError(f"{resource['resourceType']} resource missing 'id'")

        # Validate ID format
        self.validate_fhir_id(resource['resourceType'], resource['id'])

        # Resource-specific validation
        resource_type = resource['resourceType']

        if resource_type == 'Patient':
            self._validate_patient(resource)
        elif resource_type == 'Observation':
            self._validate_observation(resource)
        elif resource_type == 'Device':
            self._validate_device(resource)
        # Add more resource-specific validation as needed

    def _validate_patient(self, resource: Dict[str, Any]) -> None:
        """Validate Patient resource"""
        # Patient must have identifier
        if not resource.get('identifier'):
            raise ValueError("Patient must have at least one identifier (MRN, ABHA, etc.)")

    def _validate_observation(self, resource: Dict[str, Any]) -> None:
        """Validate Observation resource"""
        # Observation must have status
        if not resource.get('status'):
            raise ValueError("Observation must have status")

        # Observation must have code
        if not resource.get('code'):
            raise ValueError("Observation must have code (LOINC, SNOMED, etc.)")

        # Observation must have subject (patient reference)
        if not resource.get('subject'):
            raise ValueError("Observation must have subject (patient reference)")

    def _validate_device(self, resource: Dict[str, Any]) -> None:
        """Validate Device resource"""
        # Device must have identifier
        if not resource.get('identifier'):
            raise ValueError("Device must have identifier")

    def validate_reference(self, reference: Dict[str, Any]) -> None:
        """
        Validate FHIR reference format

        FHIR reference must be: ResourceType/id
        Examples: Patient/PAT0001, Device/fit-00001

        Args:
            reference: FHIR reference dict with 'reference' field

        Raises:
            ValueError: If reference is invalid
        """
        if not reference.get('reference'):
            raise ValueError("Reference missing 'reference' field")

        ref_string = reference['reference']

        # Check format: ResourceType/id
        if '/' not in ref_string:
            raise ValueError(
                f"Invalid reference format '{ref_string}': must be 'ResourceType/id'"
            )

        parts = ref_string.split('/')
        if len(parts) != 2:
            raise ValueError(
                f"Invalid reference format '{ref_string}': must be 'ResourceType/id'"
            )

        resource_type, resource_id = parts

        # Validate resource type (starts with capital letter)
        if not resource_type[0].isupper():
            raise ValueError(
                f"Invalid reference '{ref_string}': ResourceType must start with capital letter"
            )

        # Validate ID
        self.validate_fhir_id(resource_type, resource_id)

    # ========================================================================
    # CREATE
    # ========================================================================

    async def create(
        self,
        resource: Dict[str, Any],
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new FHIR resource

        Args:
            resource: Complete FHIR R5 resource
            created_by: Optional user/system that created this resource

        Returns:
            Created resource with metadata

        Raises:
            ValueError: If resource is invalid
            Exception: If database operation fails
        """
        # Validate resource
        self.validate_fhir_resource(resource)

        resource_type = resource['resourceType']
        resource_id = resource['id']

        logger.info(f"Creating FHIR {resource_type}/{resource_id}")

        try:
            async with self.pool.acquire() as conn:
                # Check if resource already exists
                exists = await conn.fetchval("""
                    SELECT EXISTS(
                        SELECT 1 FROM fhir_resources
                        WHERE resourceType = $1 AND resourceId = $2
                        AND deleted = false
                    )
                """, resource_type, resource_id)

                if exists:
                    raise ValueError(
                        f"{resource_type}/{resource_id} already exists"
                    )

                # Insert resource
                # Triggers will auto-extract identifiers, references, status
                result = await conn.fetchrow("""
                    INSERT INTO fhir_resources (
                        resourceType, resourceId, resource, createdBy
                    )
                    VALUES ($1, $2, $3::jsonb, $4)
                    RETURNING id, version, lastupdated
                """, resource_type, resource_id, json.dumps(resource), created_by)

                logger.info(
                    f"Created {resource_type}/{resource_id} "
                    f"(version {result['version']}, db_id {result['id']})"
                )

                # Return resource with metadata
                return {
                    **resource,
                    'meta': {
                        'versionId': str(result['version']),
                        'lastUpdated': result['lastupdated'].isoformat()
                    }
                }

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to create {resource_type}/{resource_id}: {e}")
            raise

    # ========================================================================
    # READ
    # ========================================================================

    async def read(
        self,
        resource_type: str,
        resource_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Read a FHIR resource by type and ID

        Args:
            resource_type: FHIR resource type (Patient, Observation, etc.)
            resource_id: Resource ID

        Returns:
            FHIR resource dict, or None if not found
        """
        self.validate_fhir_id(resource_type, resource_id)

        logger.debug(f"Reading {resource_type}/{resource_id}")

        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow("""
                    SELECT resource, version, lastupdated
                    FROM fhir_resources_active
                    WHERE resourceType = $1 AND resourceId = $2
                """, resource_type, resource_id)

                if not result:
                    logger.debug(f"{resource_type}/{resource_id} not found")
                    return None

                # Add metadata to resource
                resource = dict(result['resource'])
                resource['meta'] = {
                    'versionId': str(result['version']),
                    'lastUpdated': result['lastupdated'].isoformat()
                }

                return resource

        except Exception as e:
            logger.error(f"Failed to read {resource_type}/{resource_id}: {e}")
            raise

    # ========================================================================
    # UPDATE
    # ========================================================================

    async def update(
        self,
        resource: Dict[str, Any],
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing FHIR resource

        Args:
            resource: Complete FHIR R5 resource with updated fields
            created_by: Optional user/system that updated this resource

        Returns:
            Updated resource with new version

        Raises:
            ValueError: If resource is invalid
            Exception: If resource not found or database operation fails
        """
        # Validate resource
        self.validate_fhir_resource(resource)

        resource_type = resource['resourceType']
        resource_id = resource['id']

        logger.info(f"Updating FHIR {resource_type}/{resource_id}")

        try:
            async with self.pool.acquire() as conn:
                # Update resource (increments version automatically)
                # Triggers will auto-extract identifiers, references, status
                result = await conn.fetchrow("""
                    UPDATE fhir_resources
                    SET resource = $3::jsonb,
                        version = version + 1,
                        createdBy = $4
                    WHERE resourceType = $1 AND resourceId = $2
                    AND deleted = false
                    RETURNING id, version, lastupdated
                """, resource_type, resource_id, json.dumps(resource), created_by)

                if not result:
                    raise ValueError(f"{resource_type}/{resource_id} not found")

                logger.info(
                    f"Updated {resource_type}/{resource_id} to version {result['version']}"
                )

                # Return resource with metadata
                return {
                    **resource,
                    'meta': {
                        'versionId': str(result['version']),
                        'lastUpdated': result['lastupdated'].isoformat()
                    }
                }

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to update {resource_type}/{resource_id}: {e}")
            raise

    # ========================================================================
    # DELETE (Soft)
    # ========================================================================

    async def delete(
        self,
        resource_type: str,
        resource_id: str,
        deleted_by: Optional[str] = None
    ) -> bool:
        """
        Soft delete a FHIR resource

        FHIR requires maintaining history, so we never truly delete.
        Instead, we mark as deleted.

        Args:
            resource_type: FHIR resource type
            resource_id: Resource ID
            deleted_by: Optional user/system that deleted this resource

        Returns:
            True if deleted, False if not found
        """
        self.validate_fhir_id(resource_type, resource_id)

        logger.info(f"Deleting {resource_type}/{resource_id}")

        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("""
                    UPDATE fhir_resources
                    SET deleted = true,
                        deletedAt = NOW(),
                        deletedBy = $3
                    WHERE resourceType = $1 AND resourceId = $2
                    AND deleted = false
                    RETURNING id
                """, resource_type, resource_id, deleted_by)

                if result:
                    logger.info(f"Deleted {resource_type}/{resource_id}")
                    return True
                else:
                    logger.warning(f"{resource_type}/{resource_id} not found for deletion")
                    return False

        except Exception as e:
            logger.error(f"Failed to delete {resource_type}/{resource_id}: {e}")
            raise

    # ========================================================================
    # HISTORY
    # ========================================================================

    async def history(
        self,
        resource_type: str,
        resource_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get version history for a resource (instance-level)

        FHIR endpoint: GET [base]/[type]/[id]/_history

        Args:
            resource_type: FHIR resource type
            resource_id: Resource ID

        Returns:
            List of resource versions (newest first)
        """
        self.validate_fhir_id(resource_type, resource_id)

        logger.debug(f"Getting history for {resource_type}/{resource_id}")

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT resource, version, timestamp, operation, performedBy
                    FROM fhir_resource_history
                    WHERE resourceType = $1 AND resourceId = $2
                    ORDER BY version DESC
                """, resource_type, resource_id)

                history = []
                for row in rows:
                    resource = dict(row['resource'])
                    resource['meta'] = {
                        'versionId': str(row['version']),
                        'lastUpdated': row['timestamp'].isoformat()
                    }
                    history.append(resource)

                return history

        except Exception as e:
            logger.error(f"Failed to get history for {resource_type}/{resource_id}: {e}")
            raise

    async def type_history(
        self,
        resource_type: str,
        count: int = 20,
        offset: int = 0
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Get version history for all resources of a type (type-level)

        FHIR endpoint: GET [base]/[type]/_history

        Returns changes for ALL resources of the given type
        (e.g., all Patient changes, all Observation changes)

        Args:
            resource_type: FHIR resource type (Patient, Observation, etc.)
            count: Number of history entries to return
            offset: Offset for pagination

        Returns:
            Tuple of (history entries list, total count)
        """
        logger.debug(f"Getting type-level history for {resource_type}")

        try:
            async with self.pool.acquire() as conn:
                # Get total count
                total = await conn.fetchval("""
                    SELECT COUNT(*)
                    FROM fhir_resource_history
                    WHERE resourceType = $1
                """, resource_type)

                # Get history entries
                rows = await conn.fetch("""
                    SELECT resource, version, timestamp, operation, performedBy, resourceId
                    FROM fhir_resource_history
                    WHERE resourceType = $1
                    ORDER BY timestamp DESC
                    LIMIT $2 OFFSET $3
                """, resource_type, count, offset)

                history = []
                for row in rows:
                    resource = dict(row['resource'])
                    resource['meta'] = {
                        'versionId': str(row['version']),
                        'lastUpdated': row['timestamp'].isoformat()
                    }
                    history.append(resource)

                return history, total

        except Exception as e:
            logger.error(f"Failed to get type-level history for {resource_type}: {e}")
            raise

    async def system_history(
        self,
        count: int = 20,
        offset: int = 0
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Get version history for all resources in the system (system-level)

        FHIR endpoint: GET [base]/_history

        Returns changes for ALL resources across ALL types
        (complete audit trail of the entire system)

        Args:
            count: Number of history entries to return
            offset: Offset for pagination

        Returns:
            Tuple of (history entries list, total count)
        """
        logger.debug(f"Getting system-level history")

        try:
            async with self.pool.acquire() as conn:
                # Get total count
                total = await conn.fetchval("""
                    SELECT COUNT(*)
                    FROM fhir_resource_history
                """)

                # Get history entries
                rows = await conn.fetch("""
                    SELECT resource, version, timestamp, operation, performedBy, resourceType, resourceId
                    FROM fhir_resource_history
                    ORDER BY timestamp DESC
                    LIMIT $1 OFFSET $2
                """, count, offset)

                history = []
                for row in rows:
                    resource = dict(row['resource'])
                    resource['meta'] = {
                        'versionId': str(row['version']),
                        'lastUpdated': row['timestamp'].isoformat()
                    }
                    history.append(resource)

                return history, total

        except Exception as e:
            logger.error(f"Failed to get system-level history: {e}")
            raise

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    @staticmethod
    def create_reference(resource_type: str, resource_id: str) -> Dict[str, str]:
        """
        Create a standard FHIR reference

        Args:
            resource_type: FHIR resource type
            resource_id: Resource ID

        Returns:
            FHIR reference dict
        """
        return {
            "reference": f"{resource_type}/{resource_id}",
            "type": resource_type
        }

    @staticmethod
    def parse_reference(reference: str) -> tuple[str, str]:
        """
        Parse a FHIR reference string

        Args:
            reference: Reference string (ResourceType/id)

        Returns:
            Tuple of (resource_type, resource_id)

        Raises:
            ValueError: If reference format is invalid
        """
        if '/' not in reference:
            raise ValueError(f"Invalid reference format: {reference}")

        parts = reference.split('/')
        if len(parts) != 2:
            raise ValueError(f"Invalid reference format: {reference}")

        return parts[0], parts[1]
