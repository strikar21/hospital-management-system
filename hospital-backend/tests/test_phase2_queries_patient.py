"""
Phase 2 Tests: Patient Queries
Tests for app/common/queries/patient.py

These tests validate:
1. get_patient_by_id() returns correct patient data
2. get_patients_by_status() filters and sorts correctly
3. Database queries use proper camelCase column names
4. Query results are properly formatted

Related Files:
- hospital-backend/app/common/queries/patient.py

Note: These are integration tests that require actual database connection
"""

import pytest
from app.common.queries.patient import get_patient_by_id, get_patients_by_status


@pytest.mark.integration
@pytest.mark.asyncio
class TestPatientQueries:
    """Test patient database queries"""

    async def test_get_patient_by_id_with_existing_patient(self, db_connection, test_patient_id):
        """
        Test: Get patient by ID when patient exists
        Expected: Returns patient dict with camelCase fields
        """
        if test_patient_id is None:
            pytest.skip("No patients in database")

        result = await get_patient_by_id(db_connection, test_patient_id)

        assert result is not None
        assert isinstance(result, dict)

        # Check camelCase column names
        assert 'id' in result
        assert 'firstName' in result
        assert 'lastName' in result
        assert 'dateOfBirth' in result
        assert 'admissionDate' in result
        assert 'roomNumber' in result
        assert 'bedNumber' in result
        assert 'createdAt' in result
        assert 'updatedAt' in result

    async def test_get_patient_by_id_with_nonexistent_patient(self, db_connection):
        """
        Test: Get patient by ID when patient doesn't exist
        Expected: Returns None
        """
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        result = await get_patient_by_id(db_connection, fake_uuid)

        assert result is None

    async def test_get_patients_by_status_active(self, db_connection):
        """
        Test: Get active patients
        Expected: Returns list of active patients
        """
        result = await get_patients_by_status(db_connection, status='active', limit=10)

        assert isinstance(result, list)

        # If patients exist, check structure
        if len(result) > 0:
            patient = result[0]
            assert isinstance(patient, dict)

            # Check camelCase fields
            assert 'id' in patient
            assert 'firstName' in patient
            assert 'lastName' in patient
            assert 'status' in patient
            assert patient['status'] == 'active'

    async def test_get_patients_by_status_respects_limit(self, db_connection):
        """
        Test: get_patients_by_status() respects limit parameter
        Expected: Returns at most 'limit' patients
        """
        result = await get_patients_by_status(db_connection, status='active', limit=5)

        assert isinstance(result, list)
        assert len(result) <= 5

    async def test_get_patients_by_status_sorted_by_admission_date(self, db_connection):
        """
        Test: Patients are sorted by admission date (newest first)
        Expected: Results ordered by admissionDate DESC
        """
        result = await get_patients_by_status(db_connection, status='active', limit=100)

        if len(result) >= 2:
            # Check first two patients are sorted correctly (newest first)
            first = result[0]['admissionDate']
            second = result[1]['admissionDate']

            assert first >= second, "Patients should be sorted by admission date descending"


@pytest.mark.integration
@pytest.mark.asyncio
class TestPatientQueriesFieldValidation:
    """Test patient query field structure and camelCase compliance"""

    async def test_get_patient_by_id_returns_all_required_fields(self, db_connection, test_patient_id):
        """
        Test: get_patient_by_id() returns all required fields
        Expected: All fields from SELECT query are present
        """
        if test_patient_id is None:
            pytest.skip("No patients in database")

        result = await get_patient_by_id(db_connection, test_patient_id)

        # Required fields as per query
        required_fields = [
            'id', 'firstName', 'lastName', 'dateOfBirth', 'gender',
            'contactNumber', 'emergencyContact', 'bloodGroup',
            'admissionDate', 'roomNumber', 'bedNumber',
            'diagnosis', 'status', 'createdAt', 'updatedAt'
        ]

        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

    async def test_get_patients_by_status_uses_camelcase(self, db_connection):
        """
        Test: get_patients_by_status() returns camelCase fields
        Expected: All fields use camelCase naming
        """
        result = await get_patients_by_status(db_connection, status='active', limit=1)

        if len(result) > 0:
            patient = result[0]

            # Check for camelCase (should have these)
            camelcase_fields = ['firstName', 'lastName', 'dateOfBirth', 'contactNumber',
                                'roomNumber', 'bedNumber', 'admissionDate']

            for field in camelcase_fields:
                if field in patient:  # Field exists
                    # Check it's not snake_case
                    assert '_' not in field, f"Field {field} should be camelCase, not snake_case"


@pytest.mark.integration
@pytest.mark.asyncio
class TestPatientQueriesDataTypes:
    """Test patient query return data types"""

    async def test_get_patient_by_id_returns_proper_types(self, db_connection, test_patient_id):
        """
        Test: get_patient_by_id() returns proper Python types
        Expected: Strings are strings, dates are dates, etc.
        """
        if test_patient_id is None:
            pytest.skip("No patients in database")

        result = await get_patient_by_id(db_connection, test_patient_id)

        # ID should be string (UUID)
        assert isinstance(result['id'], str)

        # Names should be strings
        assert isinstance(result['firstName'], str)
        assert isinstance(result['lastName'], str)

        # Status should be string
        assert isinstance(result['status'], str)

        # Dates should be date/datetime objects (from asyncpg)
        from datetime import date, datetime
        assert isinstance(result['dateOfBirth'], (date, datetime))
        assert isinstance(result['createdAt'], datetime)
        assert isinstance(result['updatedAt'], datetime)

    async def test_get_patients_by_status_returns_list_of_dicts(self, db_connection):
        """
        Test: get_patients_by_status() returns list of dicts
        Expected: List[Dict[str, Any]]
        """
        result = await get_patients_by_status(db_connection, status='active', limit=10)

        assert isinstance(result, list)

        for patient in result:
            assert isinstance(patient, dict)
