"""
Database utility functions for PostgreSQL
"""

from typing import Any, List, Optional, Tuple, Union
import logging

from .config import settings

logger = logging.getLogger(__name__)

async def executeQuery(
    conn,
    query: str,
    params: Optional[Tuple] = None
) -> Any:
    """
    Execute query for PostgreSQL
    """
    try:
        # PostgreSQL - convert ? placeholders to $1, $2, etc.
        if params:
            # Convert ? placeholders to $1, $2, $3, etc.
            pgQuery = query
            for i in range(len(params)):
                pgQuery = pgQuery.replace('?', f'${i+1}', 1)
            return await conn.execute(pgQuery, *params)
        else:
            return await conn.execute(query)
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        logger.error(f"Query: {query}")
        logger.error(f"Params: {params}")
        raise

async def fetchAll(conn, query: str, params: Optional[Tuple] = None) -> List[Any]:
    """
    Fetch all rows from a query with PostgreSQL
    """
    try:
        # PostgreSQL - convert ? placeholders and fetch directly
        if params:
            pgQuery = query
            for i in range(len(params)):
                pgQuery = pgQuery.replace('?', f'${i+1}', 1)
            return await conn.fetch(pgQuery, *params)
        else:
            return await conn.fetch(query)
    except Exception as e:
        logger.error(f"Database fetchAll failed: {e}")
        logger.error(f"Query: {query}")
        logger.error(f"Params: {params}")
        raise

async def fetchOne(conn, query: str, params: Optional[Tuple] = None) -> Optional[Any]:
    """
    Fetch one row from a query with PostgreSQL
    """
    try:
        # PostgreSQL - convert ? placeholders and fetch directly
        if params:
            pgQuery = query
            for i in range(len(params)):
                pgQuery = pgQuery.replace('?', f'${i+1}', 1)
            return await conn.fetchrow(pgQuery, *params)
        else:
            return await conn.fetchrow(query)
    except Exception as e:
        logger.error(f"Database fetchOne failed: {e}")
        logger.error(f"Query: {query}")
        logger.error(f"Params: {params}")
        raise

async def fetchVal(conn, query: str, params: Optional[Tuple] = None) -> Any:
    """
    Fetch a single value from a query with PostgreSQL
    """
    try:
        # PostgreSQL - convert ? placeholders and fetch directly
        if params:
            pgQuery = query
            for i in range(len(params)):
                pgQuery = pgQuery.replace('?', f'${i+1}', 1)
            return await conn.fetchval(pgQuery, *params)
        else:
            return await conn.fetchval(query)
    except Exception as e:
        logger.error(f"Database fetchVal failed: {e}")
        logger.error(f"Query: {query}")
        logger.error(f"Params: {params}")
        raise