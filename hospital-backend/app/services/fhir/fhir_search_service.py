"""
FHIR Search Parameter Service - Standard FHIR REST API search support

Handles FHIR search parameters:
- Common parameters: _id, _lastUpdated, _sort, _count, _offset
- Resource-specific: identifier, patient, subject, code, status, etc.
- Date ranges: date, effectiveDateTime, etc.

Supports:
- Simple searches (exact match, prefix match)
- Sorting
- Pagination
- FHIR-compliant result bundles

Does NOT support (complex features):
- _include, _revinclude (graph expansion)
- Chained searches (patient.name)
- Advanced operators (:not, :above, :below)
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from urllib.parse import unquote
import asyncpg

logger = logging.getLogger(__name__)


class FhirSearchService:
    """
    FHIR R5 search parameter handler

    Converts FHIR query parameters to PostgreSQL queries on fhir_resources table.
    Returns results in FHIR Bundle format.
    """

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize FHIR search service

        Args:
            pool: PostgreSQL connection pool
        """
        self.pool = pool

    # ========================================================================
    # SEARCH PARAMETER PARSING
    # ========================================================================

    def parse_search_params(
        self,
        resource_type: str,
        params: Dict[str, Any]
    ) -> Tuple[str, List[Any], str, int, int]:
        """
        Parse FHIR search parameters into SQL query

        Args:
            resource_type: FHIR resource type (Patient, Observation, etc.)
            params: Query parameters from request

        Returns:
            Tuple of (where_clause, query_params, order_by, limit, offset)

        Examples:
            ?identifier=HMS2024000001
            ?patient=Patient/PAT0001
            ?code=8867-4&_sort=-date&_count=10
        """
        where_conditions = [
            "resourceType = $1",
            "deleted = false"
        ]
        query_params = [resource_type]
        param_index = 2

        # Common search parameters
        if '_id' in params:
            where_conditions.append(f"resourceId = ${param_index}")
            query_params.append(params['_id'])
            param_index += 1

        if '_lastUpdated' in params:
            # Support date prefixes: gt, lt, ge, le, eq
            date_value = params['_lastUpdated']
            prefix, date_str = self._parse_date_prefix(date_value)

            if prefix == 'gt':
                where_conditions.append(f"lastUpdated > ${param_index}")
                query_params.append(date_str)
                param_index += 1
            elif prefix == 'lt':
                where_conditions.append(f"lastUpdated < ${param_index}")
                query_params.append(date_str)
                param_index += 1
            elif prefix == 'ge':
                where_conditions.append(f"lastUpdated >= ${param_index}")
                query_params.append(date_str)
                param_index += 1
            elif prefix == 'le':
                where_conditions.append(f"lastUpdated <= ${param_index}")
                query_params.append(date_str)
                param_index += 1
            else:  # eq or no prefix
                where_conditions.append(f"lastUpdated >= ${param_index} AND lastUpdated < ${param_index + 1}")
                query_params.append(date_str)
                param_index += 1
                # Add end of day
                query_params.append(date_str + ' 23:59:59')
                param_index += 1

        # Identifier search (works for all resources)
        if 'identifier' in params:
            identifier_value = params['identifier']
            # Check if it's a system|value pair
            if '|' in identifier_value:
                system, value = identifier_value.split('|', 1)
                where_conditions.append(f"""
                    identifiers @> $${param_index}::jsonb
                """)
                query_params.append([{"system": system, "value": value}])
            else:
                # Just value, search any system
                where_conditions.append(f"""
                    EXISTS (
                        SELECT 1 FROM jsonb_array_elements(identifiers) AS ident
                        WHERE ident->>'value' = ${param_index}
                    )
                """)
                query_params.append(identifier_value)
            param_index += 1

        # Resource-specific parameters
        if resource_type == 'Patient':
            where_clause_part, query_params, param_index = self._parse_patient_params(
                params, where_conditions, query_params, param_index
            )
        elif resource_type == 'Observation':
            where_clause_part, query_params, param_index = self._parse_observation_params(
                params, where_conditions, query_params, param_index
            )
        elif resource_type == 'Device':
            where_clause_part, query_params, param_index = self._parse_device_params(
                params, where_conditions, query_params, param_index
            )
        elif resource_type == 'Medication':
            where_clause_part, query_params, param_index = self._parse_medication_params(
                params, where_conditions, query_params, param_index
            )
        elif resource_type == 'MedicationAdministration':
            where_clause_part, query_params, param_index = self._parse_med_admin_params(
                params, where_conditions, query_params, param_index
            )

        # Build WHERE clause
        where_clause = " AND ".join(where_conditions)

        # Sorting (_sort parameter)
        order_by = self._parse_sort_params(params, resource_type)

        # Pagination - FHIR R5 compliant
        # Support both _page (standard) and _offset (convenience)
        limit = int(params.get('_count', 20))  # Default 20 results

        if '_page' in params:
            # FHIR standard: _page parameter (1-based page number)
            page = int(params['_page'])
            if page < 1:
                page = 1
            offset = (page - 1) * limit
        else:
            # Legacy/convenience: _offset parameter (0-based offset)
            offset = int(params.get('_offset', 0))

        return where_clause, query_params, order_by, limit, offset

    def _parse_date_prefix(self, date_value: str) -> Tuple[str, str]:
        """
        Parse FHIR date prefix (gt, lt, ge, le, eq)

        Args:
            date_value: Date string with optional prefix (e.g., "gt2024-01-01")

        Returns:
            Tuple of (prefix, date_string)
        """
        prefixes = ['gt', 'lt', 'ge', 'le', 'eq']
        for prefix in prefixes:
            if date_value.startswith(prefix):
                return prefix, date_value[len(prefix):]
        return 'eq', date_value

    def _parse_patient_params(
        self,
        params: Dict[str, Any],
        where_conditions: List[str],
        query_params: List[Any],
        param_index: int
    ) -> Tuple[List[str], List[Any], int]:
        """Parse Patient-specific search parameters"""

        # Name search (searches all name fields)
        if 'name' in params:
            name_value = params['name'].lower()
            where_conditions.append(f"""
                (
                    resource->'name' @> $${param_index}::jsonb
                    OR EXISTS (
                        SELECT 1 FROM jsonb_array_elements(resource->'name') AS name
                        WHERE LOWER(name->>'family') LIKE $${param_index + 1}
                           OR LOWER(name->>'text') LIKE $${param_index + 1}
                           OR EXISTS (
                               SELECT 1 FROM jsonb_array_elements_text(name->'given') AS given
                               WHERE LOWER(given) LIKE $${param_index + 1}
                           )
                    )
                )
            """)
            query_params.append([{"family": name_value}])  # Exact match attempt
            query_params.append(f'%{name_value}%')  # Partial match
            param_index += 2

        # Gender
        if 'gender' in params:
            where_conditions.append(f"resource->>'gender' = ${param_index}")
            query_params.append(params['gender'])
            param_index += 1

        # Birth date
        if 'birthdate' in params:
            prefix, date_str = self._parse_date_prefix(params['birthdate'])
            if prefix == 'gt':
                where_conditions.append(f"resource->>'birthDate' > ${param_index}")
            elif prefix == 'lt':
                where_conditions.append(f"resource->>'birthDate' < ${param_index}")
            else:
                where_conditions.append(f"resource->>'birthDate' = ${param_index}")
            query_params.append(date_str)
            param_index += 1

        return where_conditions, query_params, param_index

    def _parse_observation_params(
        self,
        params: Dict[str, Any],
        where_conditions: List[str],
        query_params: List[Any],
        param_index: int
    ) -> Tuple[List[str], List[Any], int]:
        """Parse Observation-specific search parameters"""

        # Patient reference
        if 'patient' in params or 'subject' in params:
            patient_ref = params.get('patient') or params.get('subject')
            # Handle both "Patient/PAT0001" and "PAT0001"
            if not patient_ref.startswith('Patient/'):
                patient_ref = f'Patient/{patient_ref}'

            where_conditions.append(f"""
                resource->'subject'->>'reference' = ${param_index}
            """)
            query_params.append(patient_ref)
            param_index += 1

        # Code (LOINC, SNOMED, etc.)
        if 'code' in params:
            code_value = params['code']
            # Check if it's system|code pair
            if '|' in code_value:
                system, code = code_value.split('|', 1)
                where_conditions.append(f"""
                    resource->'code'->'coding' @> $${param_index}::jsonb
                """)
                query_params.append([{"system": system, "code": code}])
            else:
                # Just code, search any system
                where_conditions.append(f"""
                    EXISTS (
                        SELECT 1 FROM jsonb_array_elements(resource->'code'->'coding') AS coding
                        WHERE coding->>'code' = ${param_index}
                    )
                """)
                query_params.append(code_value)
            param_index += 1

        # Status
        if 'status' in params:
            where_conditions.append(f"resource->>'status' = ${param_index}")
            query_params.append(params['status'])
            param_index += 1

        # Date (effectiveDateTime)
        if 'date' in params:
            prefix, date_str = self._parse_date_prefix(params['date'])
            if prefix == 'gt':
                where_conditions.append(f"resource->>'effectiveDateTime' > ${param_index}")
            elif prefix == 'lt':
                where_conditions.append(f"resource->>'effectiveDateTime' < ${param_index}")
            elif prefix == 'ge':
                where_conditions.append(f"resource->>'effectiveDateTime' >= ${param_index}")
            elif prefix == 'le':
                where_conditions.append(f"resource->>'effectiveDateTime' <= ${param_index}")
            else:
                where_conditions.append(f"resource->>'effectiveDateTime' >= ${param_index}")
            query_params.append(date_str)
            param_index += 1

        # Category (vital-signs, laboratory, etc.)
        if 'category' in params:
            category_value = params['category']
            where_conditions.append(f"""
                EXISTS (
                    SELECT 1 FROM jsonb_array_elements(resource->'category') AS cat
                    WHERE EXISTS (
                        SELECT 1 FROM jsonb_array_elements(cat->'coding') AS coding
                        WHERE coding->>'code' = ${param_index}
                    )
                )
            """)
            query_params.append(category_value)
            param_index += 1

        return where_conditions, query_params, param_index

    def _parse_device_params(
        self,
        params: Dict[str, Any],
        where_conditions: List[str],
        query_params: List[Any],
        param_index: int
    ) -> Tuple[List[str], List[Any], int]:
        """Parse Device-specific search parameters"""

        # Device type
        if 'type' in params:
            type_value = params['type']
            where_conditions.append(f"""
                EXISTS (
                    SELECT 1 FROM jsonb_array_elements(resource->'type'->'coding') AS coding
                    WHERE coding->>'code' = ${param_index}
                )
            """)
            query_params.append(type_value)
            param_index += 1

        # Status
        if 'status' in params:
            where_conditions.append(f"resource->>'status' = ${param_index}")
            query_params.append(params['status'])
            param_index += 1

        # Manufacturer
        if 'manufacturer' in params:
            where_conditions.append(f"resource->>'manufacturer' ILIKE ${param_index}")
            query_params.append(f'%{params["manufacturer"]}%')
            param_index += 1

        return where_conditions, query_params, param_index

    def _parse_medication_params(
        self,
        params: Dict[str, Any],
        where_conditions: List[str],
        query_params: List[Any],
        param_index: int
    ) -> Tuple[List[str], List[Any], int]:
        """Parse Medication-specific search parameters"""

        # Code (RxNorm, SNOMED, etc.)
        if 'code' in params:
            code_value = params['code']
            where_conditions.append(f"""
                EXISTS (
                    SELECT 1 FROM jsonb_array_elements(resource->'code'->'coding') AS coding
                    WHERE coding->>'code' = ${param_index}
                )
            """)
            query_params.append(code_value)
            param_index += 1

        # Status
        if 'status' in params:
            where_conditions.append(f"resource->>'status' = ${param_index}")
            query_params.append(params['status'])
            param_index += 1

        return where_conditions, query_params, param_index

    def _parse_med_admin_params(
        self,
        params: Dict[str, Any],
        where_conditions: List[str],
        query_params: List[Any],
        param_index: int
    ) -> Tuple[List[str], List[Any], int]:
        """Parse MedicationAdministration-specific search parameters"""

        # Patient/subject
        if 'patient' in params or 'subject' in params:
            patient_ref = params.get('patient') or params.get('subject')
            if not patient_ref.startswith('Patient/'):
                patient_ref = f'Patient/{patient_ref}'

            where_conditions.append(f"""
                resource->'subject'->>'reference' = ${param_index}
            """)
            query_params.append(patient_ref)
            param_index += 1

        # Status
        if 'status' in params:
            where_conditions.append(f"resource->>'status' = ${param_index}")
            query_params.append(params['status'])
            param_index += 1

        # Effective time
        if 'effective-time' in params:
            prefix, date_str = self._parse_date_prefix(params['effective-time'])
            if prefix == 'gt':
                where_conditions.append(f"resource->'occurenceDateTime' > ${param_index}")
            elif prefix == 'lt':
                where_conditions.append(f"resource->'occurenceDateTime' < ${param_index}")
            else:
                where_conditions.append(f"resource->'occurenceDateTime' >= ${param_index}")
            query_params.append(date_str)
            param_index += 1

        return where_conditions, query_params, param_index

    def _parse_sort_params(self, params: Dict[str, Any], resource_type: str) -> str:
        """
        Parse FHIR _sort parameter

        Examples:
            _sort=date (ascending)
            _sort=-date (descending)
            _sort=name,-birthdate (multiple)

        Args:
            params: Query parameters
            resource_type: FHIR resource type

        Returns:
            SQL ORDER BY clause
        """
        if '_sort' not in params:
            return "lastUpdated DESC"  # Default sort

        sort_fields = params['_sort'].split(',')
        order_clauses = []

        for field in sort_fields:
            field = field.strip()
            descending = field.startswith('-')
            if descending:
                field = field[1:]

            direction = "DESC" if descending else "ASC"

            # Map FHIR parameter to database field
            if field == '_id':
                order_clauses.append(f"resourceId {direction}")
            elif field == '_lastUpdated':
                order_clauses.append(f"lastUpdated {direction}")
            elif field == 'date':
                # For Observation: effectiveDateTime
                order_clauses.append(f"resource->>'effectiveDateTime' {direction}")
            elif field == 'name':
                # For Patient: name[0].family
                order_clauses.append(f"resource->'name'->0->>'family' {direction}")
            elif field == 'birthdate':
                # For Patient: birthDate
                order_clauses.append(f"resource->>'birthDate' {direction}")
            else:
                # Generic: try as top-level field
                order_clauses.append(f"resource->>'{field}' {direction}")

        return ", ".join(order_clauses) if order_clauses else "lastUpdated DESC"

    # ========================================================================
    # SEARCH EXECUTION
    # ========================================================================

    async def search(
        self,
        resource_type: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute FHIR search and return Bundle

        Args:
            resource_type: FHIR resource type
            params: Query parameters from request

        Returns:
            FHIR Bundle with search results
        """
        logger.info(f"Searching {resource_type} with params: {params}")

        try:
            # Parse search parameters
            where_clause, query_params, order_by, limit, offset = self.parse_search_params(
                resource_type, params
            )

            # Build query
            query = f"""
                SELECT resource, version, lastUpdated
                FROM fhir_resources_active
                WHERE {where_clause}
                ORDER BY {order_by}
                LIMIT ${len(query_params) + 1}
                OFFSET ${len(query_params) + 2}
            """
            query_params.extend([limit, offset])

            # Count total (for pagination)
            count_query = f"""
                SELECT COUNT(*)
                FROM fhir_resources_active
                WHERE {where_clause}
            """

            async with self.pool.acquire() as conn:
                # Get total count
                total = await conn.fetchval(count_query, *query_params[:-2])  # Exclude limit/offset

                # Get results
                rows = await conn.fetch(query, *query_params)

            # Build FHIR Bundle
            entries = []
            for row in rows:
                resource = dict(row['resource'])
                resource['meta'] = {
                    'versionId': str(row['version']),
                    'lastUpdated': row['lastUpdated'].isoformat()
                }
                entries.append({
                    'fullUrl': f"urn:uuid:{resource['id']}",
                    'resource': resource,
                    'search': {'mode': 'match'}
                })

            bundle = {
                'resourceType': 'Bundle',
                'type': 'searchset',
                'total': total,
                'entry': entries,
                'link': self._build_pagination_links(resource_type, params, total, offset, limit)
            }

            logger.info(f"Found {len(entries)} {resource_type} resources (total: {total})")
            return bundle

        except Exception as e:
            logger.error(f"Search failed for {resource_type}: {e}")
            raise

    def _build_pagination_links(
        self,
        resource_type: str,
        params: Dict[str, Any],
        total: int,
        offset: int,
        limit: int
    ) -> List[Dict[str, str]]:
        """
        Build FHIR Bundle pagination links (FHIR R5 compliant)

        Args:
            resource_type: FHIR resource type
            params: Query parameters
            total: Total result count
            offset: Current offset
            limit: Page size

        Returns:
            List of link objects (self, next, prev)
        """
        links = []
        base_url = f"/fhir/r5/{resource_type}"

        # Calculate current page (1-based)
        current_page = (offset // limit) + 1

        # Self link (use _page for standard compliance)
        self_params = {k: v for k, v in params.items() if k not in ['_page', '_offset']}
        self_params['_page'] = current_page
        self_params['_count'] = limit
        links.append({
            'relation': 'self',
            'url': f"{base_url}?{self._build_query_string(self_params)}"
        })

        # Next link
        if offset + limit < total:
            next_params = {k: v for k, v in params.items() if k not in ['_page', '_offset']}
            next_params['_page'] = current_page + 1
            next_params['_count'] = limit
            links.append({
                'relation': 'next',
                'url': f"{base_url}?{self._build_query_string(next_params)}"
            })

        # Previous link
        if offset > 0:
            prev_params = {k: v for k, v in params.items() if k not in ['_page', '_offset']}
            prev_params['_page'] = max(1, current_page - 1)
            prev_params['_count'] = limit
            links.append({
                'relation': 'previous',
                'url': f"{base_url}?{self._build_query_string(prev_params)}"
            })

        return links

    def _build_query_string(self, params: Dict[str, Any]) -> str:
        """Build URL query string from parameters"""
        parts = []
        for key, value in params.items():
            parts.append(f"{key}={value}")
        return "&".join(parts)
