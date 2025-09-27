"""
Base Repository Pattern - Foundation for all data access operations
Implements common CRUD operations and database connection management
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic, Union
from datetime import datetime
import logging
import uuid

from ..core.database import getDbConnection
from ..core.db_utils import fetchOne, fetchAll
from ..services.audit import logAuditEvent

T = TypeVar('T')

class BaseRepository(ABC, Generic[T]):
    """
    Abstract base repository providing common database operations
    All repository classes should inherit from this to ensure consistency
    """

    def __init__(self, table_name: str, model_class: type):
        self.table_name = table_name
        self.model_class = model_class
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # ================================
    # CORE CRUD OPERATIONS
    # ================================

    async def create(self, data: Dict[str, Any], created_by: Optional[str] = None) -> Dict[str, Any]:
        """Create a new record with audit logging"""
        try:
            # Add standard fields
            record_id = str(uuid.uuid4())
            now = datetime.utcnow()

            data.update({
                'id': record_id,
                'createdAt': now,
                'updatedAt': now
            })

            # Build insert query with quoted column names for camelCase
            columns = list(data.keys())
            quoted_columns = [f'"{col}"' if any(c.isupper() for c in col) else col for col in columns]
            placeholders = [f'${i+1}' for i in range(len(columns))]
            values = list(data.values())

            query = f"""
                INSERT INTO {self.table_name} ({', '.join(quoted_columns)})
                VALUES ({', '.join(placeholders)})
                RETURNING *
            """

            async with getDbConnection() as conn:
                result = await conn.fetchrow(query, *values)

                # Audit logging
                if created_by:
                    await logAuditEvent(
                        userId=created_by,
                        action=f"create_{self.table_name.rstrip('s')}",
                        resourceType=self.table_name.rstrip('s'),
                        resourceId=record_id,
                        details=f"Created {self.table_name.rstrip('s')} with ID: {record_id}"
                    )

                self.logger.info(f"Created {self.table_name.rstrip('s')}: {record_id}")
                return dict(result) if result else None

        except Exception as e:
            self.logger.error(f"Error creating {self.table_name.rstrip('s')}: {e}")
            raise

    async def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get single record by ID"""
        try:
            query = f"SELECT * FROM {self.table_name} WHERE id = $1"

            async with getDbConnection() as conn:
                result = await conn.fetchrow(query, record_id)
                return dict(result) if result else None

        except Exception as e:
            self.logger.error(f"Error fetching {self.table_name.rstrip('s')} {record_id}: {e}")
            raise

    async def get_all(self, filters: Optional[Dict[str, Any]] = None,
                     limit: Optional[int] = None,
                     offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get multiple records with optional filtering"""
        try:
            where_conditions = []
            params = []
            param_count = 0

            # Exclude soft-deleted records if table has deletedAt column
            # Note: Not all tables have soft delete functionality

            if filters:
                for key, value in filters.items():
                    if value is not None:
                        param_count += 1
                        # Quote camelCase column names
                        quoted_key = f'"{key}"' if any(c.isupper() for c in key) else key
                        where_conditions.append(f"{quoted_key} = ${param_count}")
                        params.append(value)

            # Start with basic SELECT
            query = f"SELECT * FROM {self.table_name}"

            # Add WHERE conditions if any exist
            if where_conditions:
                query += f" WHERE {' AND '.join(where_conditions)}"

            # Add ORDER BY clause - always quote column names for camelCase
            query += ' ORDER BY "createdAt" DESC'

            if limit:
                param_count += 1
                query += f" LIMIT ${param_count}"
                params.append(limit)

            if offset:
                param_count += 1
                query += f" OFFSET ${param_count}"
                params.append(offset)

            async with getDbConnection() as conn:
                results = await conn.fetch(query, *params)
                return [dict(row) for row in results]

        except Exception as e:
            self.logger.error(f"Error fetching {self.table_name}: {e}")
            raise

    async def update(self, record_id: str, data: Dict[str, Any],
                    updated_by: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Update record by ID with audit logging"""
        try:
            # Add standard fields
            data['updatedAt'] = datetime.utcnow()

            # Build update query
            set_clauses = []
            params = []
            param_count = 0

            for key, value in data.items():
                param_count += 1
                # Quote camelCase column names
                quoted_key = f'"{key}"' if any(c.isupper() for c in key) else key
                set_clauses.append(f"{quoted_key} = ${param_count}")
                params.append(value)

            param_count += 1
            params.append(record_id)

            query = f"""
                UPDATE {self.table_name}
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count}
                RETURNING *
            """

            async with getDbConnection() as conn:
                result = await conn.fetchrow(query, *params)

                # Audit logging
                if updated_by and result:
                    await logAuditEvent(
                        userId=updated_by,
                        action=f"update_{self.table_name.rstrip('s')}",
                        resourceType=self.table_name.rstrip('s'),
                        resourceId=record_id,
                        details=f"Updated {self.table_name.rstrip('s')} with ID: {record_id}"
                    )

                self.logger.info(f"Updated {self.table_name.rstrip('s')}: {record_id}")
                return dict(result) if result else None

        except Exception as e:
            self.logger.error(f"Error updating {self.table_name.rstrip('s')} {record_id}: {e}")
            raise

    async def delete(self, record_id: str, deleted_by: Optional[str] = None) -> bool:
        """Soft delete record by ID with audit logging"""
        try:
            query = f"""
                UPDATE {self.table_name}
                SET "deletedAt" = $1, "updatedAt" = $1
                WHERE id = $2 AND "deletedAt" IS NULL
                RETURNING id
            """

            now = datetime.utcnow().isoformat()

            async with getDbConnection() as conn:
                result = await conn.fetchrow(query, now, record_id)

                if result and deleted_by:
                    await logAuditEvent(
                        userId=deleted_by,
                        action=f"delete_{self.table_name.rstrip('s')}",
                        resourceType=self.table_name.rstrip('s'),
                        resourceId=record_id,
                        details=f"Deleted {self.table_name.rstrip('s')} with ID: {record_id}"
                    )

                success = result is not None
                if success:
                    self.logger.info(f"Deleted {self.table_name.rstrip('s')}: {record_id}")
                return success

        except Exception as e:
            self.logger.error(f"Error deleting {self.table_name.rstrip('s')} {record_id}: {e}")
            raise

    async def exists(self, record_id: str) -> bool:
        """Check if record exists and is not deleted"""
        try:
            query = f"SELECT 1 FROM {self.table_name} WHERE id = $1 LIMIT 1"

            async with getDbConnection() as conn:
                result = await conn.fetchrow(query, record_id)
                return result is not None

        except Exception as e:
            self.logger.error(f"Error checking existence of {self.table_name.rstrip('s')} {record_id}: {e}")
            raise

    # ================================
    # ADVANCED QUERY METHODS
    # ================================

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records with optional filtering"""
        try:
            where_conditions = []
            params = []
            param_count = 0

            # Exclude soft-deleted records if table has deletedAt column
            # Note: Not all tables have soft delete functionality

            if filters:
                for key, value in filters.items():
                    if value is not None:
                        param_count += 1
                        # Quote camelCase column names
                        quoted_key = f'"{key}"' if any(c.isupper() for c in key) else key
                        where_conditions.append(f"{quoted_key} = ${param_count}")
                        params.append(value)

            query = f"SELECT COUNT(*) FROM {self.table_name} WHERE {' AND '.join(where_conditions)}"

            async with getDbConnection() as conn:
                result = await conn.fetchval(query, *params)
                return result or 0

        except Exception as e:
            self.logger.error(f"Error counting {self.table_name}: {e}")
            raise

    async def execute_custom_query(self, query: str, params: List[Any] = None) -> List[Dict[str, Any]]:
        """Execute custom query for complex operations"""
        try:
            async with getDbConnection() as conn:
                if params:
                    results = await conn.fetch(query, *params)
                else:
                    results = await conn.fetch(query)
                return [dict(row) for row in results]

        except Exception as e:
            self.logger.error(f"Error executing custom query: {e}")
            raise

    # ================================
    # DATA TRANSFORMATION UTILITIES
    # ================================

    def transform_to_camel_case(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform snake_case keys to camelCase for frontend consistency"""
        def to_camel_case(snake_str: str) -> str:
            components = snake_str.split('_')
            return components[0] + ''.join(word.capitalize() for word in components[1:])

        transformed = {}
        for key, value in data.items():
            camel_key = to_camel_case(key)
            transformed[camel_key] = value

        return transformed

    def transform_from_camel_case(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform camelCase keys to snake_case for database consistency"""
        def to_snake_case(camel_str: str) -> str:
            import re
            s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_str)
            return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

        transformed = {}
        for key, value in data.items():
            snake_key = to_snake_case(key)
            transformed[snake_key] = value

        return transformed

    # ================================
    # ABSTRACT METHODS FOR SPECIALIZATION
    # ================================

    @abstractmethod
    async def get_by_patient_id(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get records by patient ID - implemented by specific repositories"""
        pass