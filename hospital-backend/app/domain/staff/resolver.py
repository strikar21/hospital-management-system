"""
StaffResolver - Single source of truth for staff name resolution (ID → Name + Role).

Replaces inline staff resolution logic scattered across:
- app/services/patient_service.py (get_patient_details, get_medications, etc.)
- app/repositories/patient_repository.py (resolve_staff_names)
- app/api/routes/patient_routes.py (multiple endpoints)

Usage:
    from app.domain.staff import StaffResolver

    resolver = StaffResolver(pool=db_pool)
    staff = await resolver.resolve_staff_id('DOC001')
    # Returns: {'id': 'DOC001', 'name': 'Dr. Jane Smith', 'role': 'Doctor', 'department': 'Cardiology'}

    # Batch resolution
    staff_map = await resolver.resolve_staff_batch(['DOC001', 'NUR002'])
"""

from typing import Dict, List, Optional
import logging
import asyncpg

from app.domain.schemas import StaffResolution, StaffRole

logger = logging.getLogger(__name__)


class StaffResolver:
    """
    Centralizes staff ID → Name + Role resolution.

    Responsibilities:
    1. Resolve single staff ID to name and role
    2. Batch resolve multiple staff IDs
    3. Cache frequently accessed staff records (optional optimization)
    4. Handle missing/invalid staff IDs gracefully
    """

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize staff resolver.

        Args:
            pool: Database connection pool
        """
        self.pool = pool
        self._cache: Dict[str, StaffResolution] = {}

    async def resolve_staff_id(
        self,
        staff_id: str,
        use_cache: bool = True
    ) -> Optional[StaffResolution]:
        """
        Resolve staff ID to full staff information.

        Args:
            staff_id: Staff ID to resolve
            use_cache: Use cached value if available

        Returns:
            StaffResolution with name and role, or None if not found
        """
        if not staff_id:
            return None

        # Check cache first
        if use_cache and staff_id in self._cache:
            return self._cache[staff_id]

        try:
            async with self.pool.acquire() as conn:
                query = """
                    SELECT id, "firstName", "lastName", role, department
                    FROM staff
                    WHERE id = $1 AND "isActive" = true
                """

                row = await conn.fetchrow(query, staff_id)

                if not row:
                    logger.warning(f"Staff ID not found or inactive: {staff_id}")
                    return None

                # Build full name
                first_name = row['firstName'] or ''
                last_name = row['lastName'] or ''
                full_name = f"{first_name} {last_name}".strip()

                if not full_name:
                    full_name = staff_id  # Fallback to ID if no name

                staff: StaffResolution = {
                    'id': row['id'],
                    'name': full_name,
                    'role': row['role'],
                    'department': row['department']
                }

                # Cache result
                self._cache[staff_id] = staff

                return staff

        except Exception as e:
            logger.error(f"Error resolving staff ID {staff_id}: {e}")
            return None

    async def resolve_staff_batch(
        self,
        staff_ids: List[str],
        use_cache: bool = True
    ) -> Dict[str, StaffResolution]:
        """
        Resolve multiple staff IDs in a single database query.

        Args:
            staff_ids: List of staff IDs to resolve
            use_cache: Use cached values if available

        Returns:
            Dictionary mapping staff ID → StaffResolution
        """
        if not staff_ids:
            return {}

        # Remove duplicates
        unique_ids = list(set(staff_ids))

        result: Dict[str, StaffResolution] = {}

        # Check cache first
        uncached_ids = []
        if use_cache:
            for staff_id in unique_ids:
                if staff_id in self._cache:
                    result[staff_id] = self._cache[staff_id]
                else:
                    uncached_ids.append(staff_id)
        else:
            uncached_ids = unique_ids

        # Query database for uncached IDs
        if uncached_ids:
            try:
                async with self.pool.acquire() as conn:
                    query = """
                        SELECT id, "firstName", "lastName", role, department
                        FROM staff
                        WHERE id = ANY($1::text[]) AND "isActive" = true
                    """

                    rows = await conn.fetch(query, uncached_ids)

                    for row in rows:
                        # Build full name
                        first_name = row['firstName'] or ''
                        last_name = row['lastName'] or ''
                        full_name = f"{first_name} {last_name}".strip()

                        if not full_name:
                            full_name = row['id']

                        staff: StaffResolution = {
                            'id': row['id'],
                            'name': full_name,
                            'role': row['role'],
                            'department': row['department']
                        }

                        # Add to result and cache
                        result[row['id']] = staff
                        self._cache[row['id']] = staff

            except Exception as e:
                logger.error(f"Error batch resolving staff IDs: {e}")

        return result

    async def enrich_record_with_staff(
        self,
        record: Dict,
        staff_fields: Dict[str, str]
    ) -> Dict:
        """
        Enrich a record with resolved staff names.

        Args:
            record: Record to enrich (e.g., medication, investigation)
            staff_fields: Mapping of ID field → name field
                         e.g., {'prescribedBy': 'prescribedByName', 'acknowledgedBy': 'acknowledgedByName'}

        Returns:
            Enriched record with staff names added
        """
        # Collect all staff IDs to resolve
        staff_ids = []
        for id_field in staff_fields.keys():
            if record.get(id_field):
                staff_ids.append(record[id_field])

        if not staff_ids:
            return record

        # Batch resolve
        staff_map = await self.resolve_staff_batch(staff_ids)

        # Add resolved names to record
        for id_field, name_field in staff_fields.items():
            staff_id = record.get(id_field)
            if staff_id and staff_id in staff_map:
                staff = staff_map[staff_id]
                record[name_field] = staff['name']

                # Also add role if field exists
                role_field = id_field + 'Role'
                if role_field not in record:
                    record[role_field] = staff['role']

        return record

    async def enrich_records_batch(
        self,
        records: List[Dict],
        staff_fields: Dict[str, str]
    ) -> List[Dict]:
        """
        Enrich multiple records with resolved staff names (batch operation).

        Args:
            records: List of records to enrich
            staff_fields: Mapping of ID field → name field

        Returns:
            List of enriched records
        """
        if not records:
            return records

        # Collect all unique staff IDs from all records
        all_staff_ids = set()
        for record in records:
            for id_field in staff_fields.keys():
                if record.get(id_field):
                    all_staff_ids.add(record[id_field])

        if not all_staff_ids:
            return records

        # Single batch resolve for all staff IDs
        staff_map = await self.resolve_staff_batch(list(all_staff_ids))

        # Enrich each record
        for record in records:
            for id_field, name_field in staff_fields.items():
                staff_id = record.get(id_field)
                if staff_id and staff_id in staff_map:
                    staff = staff_map[staff_id]
                    record[name_field] = staff['name']

                    # Also add role if field exists
                    role_field = id_field + 'Role'
                    if role_field not in record:
                        record[role_field] = staff['role']

        return records

    def clear_cache(self):
        """Clear the staff resolution cache."""
        self._cache.clear()
        logger.info("Staff resolver cache cleared")

    async def refresh_cache(self, staff_ids: Optional[List[str]] = None):
        """
        Refresh cache for specific staff IDs or all cached staff.

        Args:
            staff_ids: List of staff IDs to refresh, or None to refresh all
        """
        if staff_ids is None:
            staff_ids = list(self._cache.keys())

        if not staff_ids:
            return

        # Re-fetch from database (bypass cache)
        fresh_data = await self.resolve_staff_batch(staff_ids, use_cache=False)

        # Update cache
        self._cache.update(fresh_data)

        logger.info(f"Refreshed cache for {len(fresh_data)} staff members")
