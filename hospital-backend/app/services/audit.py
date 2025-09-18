"""
Audit logging service
"""

from datetime import datetime
import logging
from typing import Optional

from ..core.database import get_db_connection
from ..core.db_utils import execute_query

logger = logging.getLogger(__name__)

async def log_audit_event(
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """
    Log an audit event to the database
    """
    try:
        async with get_db_connection() as conn:
            query = """
                INSERT INTO auditLog (
                    userId, action, resourceType, resourceId, details,
                    ipAddress, userAgent, timestamp
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """
            
            await conn.execute(query,
                user_id, action, resource_type, resource_id, details,
                ip_address, user_agent, datetime.now()
            )
                
    except Exception as e:
        logger.error(f"❌ Failed to log audit event: {e}")
        # Don't raise exception for audit logging failures