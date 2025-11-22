"""
FHIR Base Service
Base class for FHIR R5 resource services with JSONB handling
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging
import json
from uuid import UUID

from ...core.database import getDbConnection, getTimescaleConnection


class FhirBaseService(ABC):
    """
    Abstract base service for FHIR R5 resources
    Handles JSONB storage, resource validation, and common FHIR operations
    """

    def __init__(self, table_name: str, use_timescale: bool = False):
        """
        Initialize FHIR service

        Args:
            table_name: Database table name (e.g., 'fhir_devices')
            use_timescale: True for TimescaleDB tables (observations)
        """
        self.table_name = table_name
        self.use_timescale = use_timescale
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def get_connection(self):
        """Get appropriate database connection"""
        if self.use_timescale:
            return getTimescaleConnection()
        return getDbConnection()

    # ================================
    # FHIR RESOURCE OPERATIONS
    # ================================

    async def create(self, resource: Dict[str, Any], **extracted_fields) -> Dict[str, Any]:
        """
        Create FHIR resource with JSONB storage

        Args:
            resource: Full FHIR R5 resource (stored in 'resource' JSONB column)
            **extracted_fields: Denormalized fields for fast queries

        Returns:
            Created resource with id and metadata
        """
        try:
            # Validate FHIR resource
            await self.validate_resource(resource)

            # Add metadata
            resource_with_meta = self._add_metadata(resource)

            async with self.get_connection() as conn:
                # Build INSERT query
                columns = ['resource'] + list(extracted_fields.keys())
                placeholders = [f'${i+1}' for i in range(len(columns))]

                query = f"""
                    INSERT INTO {self.table_name} ({', '.join(columns)})
                    VALUES ({', '.join(placeholders)})
                    RETURNING id, {', '.join(columns)}, "createdAt", "updatedAt"
                """

                values = [json.dumps(resource_with_meta)] + list(extracted_fields.values())

                result = await conn.fetchrow(query, *values)

                # Convert to dict and merge with resource
                result_dict = dict(result)
                result_dict['resource'] = json.loads(result_dict['resource'])

                self.logger.info(f"Created {self.table_name} resource: {result_dict['id']}")
                return result_dict

        except Exception as e:
            self.logger.error(f"Error creating {self.table_name}: {e}")
            raise

    async def get_by_id(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """
        Get FHIR resource by ID

        Args:
            resource_id: UUID or string ID

        Returns:
            FHIR resource with extracted fields
        """
        try:
            async with self.get_connection() as conn:
                query = f"""
                    SELECT * FROM {self.table_name}
                    WHERE id = $1
                """
                result = await conn.fetchrow(query, UUID(resource_id) if self._is_uuid(resource_id) else resource_id)

                if not result:
                    return None

                # Convert to dict and parse JSONB
                result_dict = dict(result)
                if 'resource' in result_dict:
                    result_dict['resource'] = json.loads(result_dict['resource']) if isinstance(result_dict['resource'], str) else result_dict['resource']

                return result_dict

        except Exception as e:
            self.logger.error(f"Error getting {self.table_name} by id: {e}")
            raise

    async def search(self, filters: Optional[Dict[str, Any]] = None,
                    limit: int = 100,
                    offset: int = 0) -> List[Dict[str, Any]]:
        """
        Search FHIR resources with filters

        Args:
            filters: Dictionary of field filters (uses extracted columns)
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            List of FHIR resources
        """
        try:
            async with self.get_connection() as conn:
                # Build WHERE clause from filters
                where_clauses = []
                values = []
                param_count = 1

                if filters:
                    for key, value in filters.items():
                        where_clauses.append(f'"{key}" = ${param_count}')
                        values.append(value)
                        param_count += 1

                where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

                query = f"""
                    SELECT * FROM {self.table_name}
                    {where_sql}
                    ORDER BY "createdAt" DESC
                    LIMIT ${param_count} OFFSET ${param_count + 1}
                """

                values.extend([limit, offset])

                results = await conn.fetch(query, *values)

                # Convert to list of dicts and parse JSONB
                result_list = []
                for row in results:
                    row_dict = dict(row)
                    if 'resource' in row_dict:
                        row_dict['resource'] = json.loads(row_dict['resource']) if isinstance(row_dict['resource'], str) else row_dict['resource']
                    result_list.append(row_dict)

                return result_list

        except Exception as e:
            self.logger.error(f"Error searching {self.table_name}: {e}")
            raise

    async def update(self, resource_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update FHIR resource (both JSONB and extracted fields)

        Args:
            resource_id: Resource ID
            updates: Dictionary with 'resource' (FHIR) and/or extracted field updates

        Returns:
            Updated resource
        """
        try:
            async with self.get_connection() as conn:
                # Build UPDATE SET clause
                set_clauses = []
                values = []
                param_count = 1

                for key, value in updates.items():
                    if key == 'resource':
                        # Update FHIR resource with metadata
                        updated_resource = self._update_metadata(value)
                        set_clauses.append(f'resource = ${param_count}')
                        values.append(json.dumps(updated_resource))
                    else:
                        # Update extracted field
                        set_clauses.append(f'"{key}" = ${param_count}')
                        values.append(value)
                    param_count += 1

                # Always update updatedAt
                set_clauses.append(f'"updatedAt" = ${param_count}')
                values.append(datetime.utcnow())
                param_count += 1

                # Add resource_id to values
                values.append(UUID(resource_id) if self._is_uuid(resource_id) else resource_id)

                query = f"""
                    UPDATE {self.table_name}
                    SET {', '.join(set_clauses)}
                    WHERE id = ${param_count}
                    RETURNING *
                """

                result = await conn.fetchrow(query, *values)

                if not result:
                    return None

                # Convert and parse
                result_dict = dict(result)
                if 'resource' in result_dict:
                    result_dict['resource'] = json.loads(result_dict['resource']) if isinstance(result_dict['resource'], str) else result_dict['resource']

                self.logger.info(f"Updated {self.table_name} resource: {resource_id}")
                return result_dict

        except Exception as e:
            self.logger.error(f"Error updating {self.table_name}: {e}")
            raise

    async def delete(self, resource_id: str) -> bool:
        """
        Delete FHIR resource

        Args:
            resource_id: Resource ID

        Returns:
            True if deleted, False if not found
        """
        try:
            async with self.get_connection() as conn:
                query = f"""
                    DELETE FROM {self.table_name}
                    WHERE id = $1
                """
                result = await conn.execute(query, UUID(resource_id) if self._is_uuid(resource_id) else resource_id)

                deleted = result == "DELETE 1"
                if deleted:
                    self.logger.info(f"Deleted {self.table_name} resource: {resource_id}")

                return deleted

        except Exception as e:
            self.logger.error(f"Error deleting {self.table_name}: {e}")
            raise

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count resources with optional filters"""
        try:
            async with self.get_connection() as conn:
                where_clauses = []
                values = []
                param_count = 1

                if filters:
                    for key, value in filters.items():
                        where_clauses.append(f'"{key}" = ${param_count}')
                        values.append(value)
                        param_count += 1

                where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

                query = f"SELECT COUNT(*) FROM {self.table_name} {where_sql}"

                result = await conn.fetchval(query, *values)
                return result

        except Exception as e:
            self.logger.error(f"Error counting {self.table_name}: {e}")
            raise

    # ================================
    # FHIR-SPECIFIC HELPERS
    # ================================

    def _add_metadata(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Add FHIR metadata to resource on creation"""
        resource_copy = resource.copy()

        if 'meta' not in resource_copy:
            resource_copy['meta'] = {}

        resource_copy['meta']['lastUpdated'] = datetime.utcnow().isoformat() + 'Z'
        resource_copy['meta']['versionId'] = '1'

        return resource_copy

    def _update_metadata(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Update FHIR metadata on resource update"""
        resource_copy = resource.copy()

        if 'meta' not in resource_copy:
            resource_copy['meta'] = {}

        resource_copy['meta']['lastUpdated'] = datetime.utcnow().isoformat() + 'Z'

        # Increment version if exists
        if 'versionId' in resource_copy['meta']:
            try:
                version = int(resource_copy['meta']['versionId'])
                resource_copy['meta']['versionId'] = str(version + 1)
            except:
                resource_copy['meta']['versionId'] = '1'
        else:
            resource_copy['meta']['versionId'] = '1'

        return resource_copy

    def _is_uuid(self, value: str) -> bool:
        """Check if string is a valid UUID"""
        try:
            UUID(value)
            return True
        except:
            return False

    # ================================
    # VALIDATION (Override in subclasses)
    # ================================

    @abstractmethod
    async def validate_resource(self, resource: Dict[str, Any]) -> None:
        """
        Validate FHIR resource structure
        Override in subclasses for resource-specific validation

        Args:
            resource: FHIR resource to validate

        Raises:
            ValueError: If resource is invalid
        """
        pass

    @abstractmethod
    def extract_searchable_fields(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract fields from FHIR resource for denormalized storage
        Override in subclasses

        Args:
            resource: FHIR resource

        Returns:
            Dictionary of extracted fields for table columns
        """
        pass
