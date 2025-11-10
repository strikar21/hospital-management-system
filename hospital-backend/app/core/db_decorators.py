"""
Database Connection Decorators

Provides decorators for automatic database connection management, transactions,
and retry logic with exponential backoff.

Usage Examples:

    # Automatic connection management
    @with_db_connection()
    async def get_patient(patient_id: str, conn):
        return await conn.fetchrow("SELECT * FROM patients WHERE id = $1", patient_id)

    # With transaction (auto-rollback on error)
    @with_transaction()
    async def create_patient_with_records(patient_data: dict, conn):
        patient = await conn.fetchrow("INSERT INTO patients ...")
        await conn.execute("INSERT INTO medical_records ...")
        return patient

    # With retry (3 retries with exponential backoff)
    @with_retry(max_attempts=3, base_delay=0.5)
    async def update_patient_vitals(patient_id: str, vitals: dict):
        async with getDbConnection() as conn:
            await conn.execute("UPDATE vitals ...")

    # Combine decorators (transaction with retry)
    @with_retry(max_attempts=3)
    @with_transaction()
    async def complex_operation(patient_id: str, conn):
        # Atomic operation with automatic retry on failure
        pass
"""

from functools import wraps
from typing import Callable, Optional, Any
import asyncio
import logging

from .database import getDbConnection, getTimescaleConnection
from .errors import DatabaseError, DatabaseConnectionError

logger = logging.getLogger(__name__)


def with_db_connection(use_timescale: bool = False):
    """
    Decorator to automatically provide database connection to function

    Args:
        use_timescale: If True, use TimescaleDB connection instead of PostgreSQL

    Usage:
        @with_db_connection()
        async def my_function(patient_id: str, conn):
            return await conn.fetchrow("SELECT * FROM patients WHERE id = $1", patient_id)

    Note:
        - Function must accept 'conn' as keyword argument or last positional argument
        - Connection is automatically acquired and released
        - Errors are wrapped in DatabaseError
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Choose connection based on database type
            get_connection = getTimescaleConnection if use_timescale else getDbConnection

            try:
                async with get_connection() as conn:
                    # Check if function already has conn parameter
                    if 'conn' in kwargs:
                        raise ValueError(
                            f"Function {func.__name__} should not receive 'conn' parameter when using @with_db_connection. "
                            "The decorator provides the connection automatically."
                        )

                    # Inject connection as keyword argument
                    kwargs['conn'] = conn
                    return await func(*args, **kwargs)

            except Exception as e:
                logger.error(f"❌ Database error in {func.__name__}: {e}", exc_info=True)
                raise DatabaseError(
                    message=f"Database operation failed in {func.__name__}",
                    operation=func.__name__
                ) from e

        return wrapper
    return decorator


def with_transaction(use_timescale: bool = False):
    """
    Decorator to wrap function in database transaction

    Args:
        use_timescale: If True, use TimescaleDB connection instead of PostgreSQL

    Usage:
        @with_transaction()
        async def create_patient_record(patient_data: dict, conn):
            patient = await conn.fetchrow("INSERT INTO patients ...")
            await conn.execute("INSERT INTO medical_records ...")
            return patient

    Note:
        - Function must accept 'conn' as keyword argument or last positional argument
        - Transaction is automatically committed on success
        - Transaction is automatically rolled back on error
        - Connection is provided by the decorator
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Choose connection based on database type
            get_connection = getTimescaleConnection if use_timescale else getDbConnection

            try:
                async with get_connection() as conn:
                    # Check if function already has conn parameter
                    if 'conn' in kwargs:
                        raise ValueError(
                            f"Function {func.__name__} should not receive 'conn' parameter when using @with_transaction. "
                            "The decorator provides the connection automatically."
                        )

                    # Start transaction
                    async with conn.transaction():
                        # Inject connection as keyword argument
                        kwargs['conn'] = conn
                        result = await func(*args, **kwargs)

                        logger.debug(f"✅ Transaction committed for {func.__name__}")
                        return result

            except Exception as e:
                logger.error(f"❌ Transaction rolled back in {func.__name__}: {e}", exc_info=True)
                raise DatabaseError(
                    message=f"Transaction failed in {func.__name__}",
                    operation=func.__name__
                ) from e

        return wrapper
    return decorator


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    exponential_base: float = 2.0
):
    """
    Decorator to retry function on failure with exponential backoff

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay between retries in seconds (default: 0.5)
        max_delay: Maximum delay between retries in seconds (default: 10.0)
        exponential_base: Base for exponential backoff calculation (default: 2.0)

    Usage:
        @with_retry(max_attempts=3, base_delay=0.5)
        async def unreliable_operation():
            # This will retry up to 3 times with exponential backoff
            async with getDbConnection() as conn:
                return await conn.fetchrow("SELECT ...")

    Retry Schedule (default):
        - Attempt 1: Execute immediately
        - Attempt 2: Wait 0.5s (base_delay * 2^0)
        - Attempt 3: Wait 1.0s (base_delay * 2^1)
        - Attempt 4: Wait 2.0s (base_delay * 2^2)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)

                except Exception as e:
                    last_exception = e

                    if attempt == max_attempts:
                        logger.error(
                            f"❌ {func.__name__} failed after {max_attempts} attempts: {e}",
                            exc_info=True
                        )
                        raise DatabaseError(
                            message=f"Operation failed after {max_attempts} attempts",
                            operation=func.__name__
                        ) from e

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)

                    logger.warning(
                        f"⚠️ {func.__name__} failed (attempt {attempt}/{max_attempts}), "
                        f"retrying in {delay:.2f}s: {e}"
                    )

                    await asyncio.sleep(delay)

            # Should never reach here, but raise last exception if it does
            raise last_exception

        return wrapper
    return decorator


# ================================
# SPECIALIZED DECORATORS
# ================================

def with_connection_pool_check():
    """
    Decorator to verify connection pool health before executing function

    Usage:
        @with_connection_pool_check()
        async def critical_operation():
            # This will only execute if connection pool is healthy
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Quick connection pool health check
                async with getDbConnection() as conn:
                    await conn.fetchval("SELECT 1")

                return await func(*args, **kwargs)

            except Exception as e:
                logger.error(f"❌ Connection pool health check failed: {e}", exc_info=True)
                raise DatabaseConnectionError(
                    database="PostgreSQL"
                ) from e

        return wrapper
    return decorator


# ================================
# UTILITY FUNCTIONS
# ================================

async def execute_with_retry(
    operation: Callable,
    max_attempts: int = 3,
    base_delay: float = 0.5
) -> Any:
    """
    Execute an async operation with retry logic (functional approach)

    Args:
        operation: Async callable to execute
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds

    Returns:
        Result of the operation

    Usage:
        result = await execute_with_retry(
            lambda: conn.fetchrow("SELECT * FROM patients WHERE id = $1", patient_id),
            max_attempts=3
        )
    """
    @with_retry(max_attempts=max_attempts, base_delay=base_delay)
    async def _execute():
        return await operation()

    return await _execute()
