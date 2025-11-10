"""
Base Service Pattern - Business logic layer
Works with repositories to provide clean business operations
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar
from datetime import datetime, timedelta
import logging

from ..repositories.base_repository import BaseRepository
from ..common.datetime import now_utc

T = TypeVar('T')

class BaseService(ABC):
    """
    Abstract base service providing common business operations
    All service classes should inherit from this to ensure consistency
    """

    def __init__(self, repository: BaseRepository):
        self.repository = repository
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # ================================
    # BUSINESS LOGIC OPERATIONS
    # ================================

    async def create(self, data: Dict[str, Any], created_by: Optional[str] = None) -> Dict[str, Any]:
        """Create with business logic validation"""
        try:
            # Pre-creation validation
            await self.validate_create_data(data)

            # Create record
            result = await self.repository.create(data, created_by)

            # Post-creation processing
            if result:
                await self.post_create_processing(result, created_by)

            return result

        except Exception as e:
            self.logger.error(f"Service create error: {e}")
            raise

    async def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get with data transformation"""
        try:
            result = await self.repository.get_by_id(record_id)

            # Database already returns camelCase, return as-is
            return result

        except Exception as e:
            self.logger.error(f"Service get_by_id error: {e}")
            raise

    async def get_all(self, filters: Optional[Dict[str, Any]] = None,
                     limit: Optional[int] = None,
                     offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all with filtering and transformation"""
        try:
            # NOTE: Since our database uses camelCase columns, do NOT transform filters
            # Keep filters as-is (camelCase) to match database schema

            results = await self.repository.get_all(filters, limit, offset)

            # Results are already in camelCase from database, return as-is
            return results

        except Exception as e:
            self.logger.error(f"Service get_all error: {e}")
            raise

    async def update(self, record_id: str, data: Dict[str, Any],
                    updated_by: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Update with business logic validation"""
        try:
            # Pre-update validation
            await self.validate_update_data(record_id, data)

            # Database uses camelCase, keep data as-is
            result = await self.repository.update(record_id, data, updated_by)

            # Post-update processing
            if result:
                await self.post_update_processing(result, updated_by)

            return result

        except Exception as e:
            self.logger.error(f"Service update error: {e}")
            raise

    async def delete(self, record_id: str, deleted_by: Optional[str] = None) -> bool:
        """Delete with business logic validation"""
        try:
            # Pre-deletion validation
            await self.validate_delete(record_id, deleted_by)

            # Delete record
            success = await self.repository.delete(record_id, deleted_by)

            # Post-deletion processing
            if success:
                await self.post_delete_processing(record_id, deleted_by)

            return success

        except Exception as e:
            self.logger.error(f"Service delete error: {e}")
            raise

    async def exists(self, record_id: str) -> bool:
        """Check existence"""
        return await self.repository.exists(record_id)

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count with filtering"""
        if filters:
            filters = self.repository.transform_from_camel_case(filters)
        return await self.repository.count(filters)

    # ================================
    # VALIDATION METHODS
    # ================================

    async def validate_create_data(self, data: Dict[str, Any]) -> None:
        """Override in subclasses for specific validation logic"""
        pass

    async def validate_update_data(self, record_id: str, data: Dict[str, Any]) -> None:
        """Override in subclasses for specific validation logic"""
        pass

    async def validate_delete(self, record_id: str, deleted_by: Optional[str] = None) -> None:
        """Override in subclasses for specific validation logic"""
        pass

    # ================================
    # PROCESSING HOOKS
    # ================================

    async def post_create_processing(self, result: Dict[str, Any], created_by: Optional[str] = None) -> None:
        """Override in subclasses for post-creation logic"""
        pass

    async def post_update_processing(self, result: Dict[str, Any], updated_by: Optional[str] = None) -> None:
        """Override in subclasses for post-update logic"""
        pass

    async def post_delete_processing(self, record_id: str, deleted_by: Optional[str] = None) -> None:
        """Override in subclasses for post-deletion logic"""
        pass

    # ================================
    # UTILITY METHODS
    # ================================

    def can_edit_item(self, timestamp: str) -> bool:
        """Check if item can be edited based on timestamp (24-hour window)"""
        try:
            if not timestamp or not isinstance(timestamp, str):
                return False

            # Strip microseconds entirely - seconds precision is sufficient
            timestamp_cleaned = timestamp.replace('Z', '+00:00')
            if '.' in timestamp_cleaned:
                # Remove everything from the decimal point to the timezone
                base = timestamp_cleaned.split('.')[0]
                tz = '+00:00' if '+' in timestamp_cleaned else ''
                timestamp_cleaned = base + tz

            item_time = datetime.fromisoformat(timestamp_cleaned)
            now = now_utc()
            time_diff = now - item_time.replace(tzinfo=None)
            max_edit_window = timedelta(hours=24)

            return time_diff <= max_edit_window

        except Exception as e:
            self.logger.error(f"Error checking edit permission: {e}")
            return False

    def get_current_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get user context for business operations"""
        # This would typically fetch user details from a user service
        # For now, return basic context
        return {
            'userId': user_id,
            'timestamp': now_utc().isoformat()
        }

    # ================================
    # ABSTRACT METHODS
    # ================================

    @abstractmethod
    async def get_by_patient_id(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get records by patient ID - implemented by specific services"""
        pass