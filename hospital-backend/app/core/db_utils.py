"""
Database utility functions for PostgreSQL
"""

from typing import Any, List, Optional, Tuple, Union
import logging

from .config import settings

logger = logging.getLogger(__name__)

async def execute_query(
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
            pg_query = query
            for i in range(len(params)):
                pg_query = pg_query.replace('?', f'${i+1}', 1)
            return await conn.execute(pg_query, *params)
        else:
            return await conn.execute(query)
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        logger.error(f"Query: {query}")
        logger.error(f"Params: {params}")
        raise

async def fetch_all(conn, query: str, params: Optional[Tuple] = None) -> List[Any]:
    """
    Fetch all rows from a query with PostgreSQL
    """
    try:
        # PostgreSQL - convert ? placeholders and fetch directly
        if params:
            pg_query = query
            for i in range(len(params)):
                pg_query = pg_query.replace('?', f'${i+1}', 1)
            return await conn.fetch(pg_query, *params)
        else:
            return await conn.fetch(query)
    except Exception as e:
        logger.error(f"Database fetch_all failed: {e}")
        logger.error(f"Query: {query}")
        logger.error(f"Params: {params}")
        raise

async def fetch_one(conn, query: str, params: Optional[Tuple] = None) -> Optional[Any]:
    """
    Fetch one row from a query with PostgreSQL
    """
    try:
        # PostgreSQL - convert ? placeholders and fetch directly
        if params:
            pg_query = query
            for i in range(len(params)):
                pg_query = pg_query.replace('?', f'${i+1}', 1)
            return await conn.fetchrow(pg_query, *params)
        else:
            return await conn.fetchrow(query)
    except Exception as e:
        logger.error(f"Database fetch_one failed: {e}")
        logger.error(f"Query: {query}")
        logger.error(f"Params: {params}")
        raise

async def fetch_val(conn, query: str, params: Optional[Tuple] = None) -> Any:
    """
    Fetch a single value from a query with PostgreSQL
    """
    try:
        # PostgreSQL - convert ? placeholders and fetch directly
        if params:
            pg_query = query
            for i in range(len(params)):
                pg_query = pg_query.replace('?', f'${i+1}', 1)
            return await conn.fetchval(pg_query, *params)
        else:
            return await conn.fetchval(query)
    except Exception as e:
        logger.error(f"Database fetch_val failed: {e}")
        logger.error(f"Query: {query}")
        logger.error(f"Params: {params}")
        raise