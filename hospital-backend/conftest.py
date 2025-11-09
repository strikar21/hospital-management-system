"""
Pytest configuration and fixtures for Hospital Management System tests
"""

import pytest
import asyncio
from typing import AsyncGenerator

# Database connection imports
from app.core.database import getDbConnection, getTimescaleConnection


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for async tests
    Scope: session - one loop for entire test session
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_connection():
    """
    Provide PostgreSQL database connection for tests
    Automatically closes connection after test completes

    Usage:
        async def test_something(db_connection):
            result = await db_connection.fetchval("SELECT COUNT(*) FROM patients")
    """
    async with getDbConnection() as conn:
        yield conn


@pytest.fixture
async def timescale_connection():
    """
    Provide TimescaleDB connection for vitals tests
    Automatically closes connection after test completes

    Usage:
        async def test_vitals(timescale_connection):
            result = await timescale_connection.fetch("SELECT * FROM vitals_timeseries LIMIT 1")
    """
    async with getTimescaleConnection() as conn:
        yield conn


@pytest.fixture
async def test_patient_id(db_connection) -> str:
    """
    Get a real patient ID from database for testing
    Returns first active patient, or None if no patients exist

    Usage:
        async def test_patient_data(test_patient_id):
            assert test_patient_id is not None
    """
    result = await db_connection.fetchval(
        "SELECT id FROM patients WHERE status = 'active' LIMIT 1"
    )
    return result


@pytest.fixture
async def test_device_id(db_connection) -> str:
    """
    Get a real device ID from database for testing
    Returns first device, or None if no devices exist
    """
    result = await db_connection.fetchval(
        "SELECT id FROM devices LIMIT 1"
    )
    return result


@pytest.fixture
async def test_staff_id(db_connection) -> str:
    """
    Get a real staff ID from database for testing
    Returns first active staff member
    """
    result = await db_connection.fetchval(
        'SELECT id FROM staff WHERE "isActive" = true LIMIT 1'
    )
    return result


# Mark all tests in this session
def pytest_configure(config):
    """Configure pytest with custom settings"""
    config.addinivalue_line(
        "markers", "critical: Critical path tests (P0 - blocking production)"
    )
    config.addinivalue_line(
        "markers", "security: Security-related tests"
    )
    config.addinivalue_line(
        "markers", "compliance: Compliance validation tests"
    )
