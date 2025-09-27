"""
Audit logging service
"""

from datetime import datetime
import logging
from typing import Optional

from ..core.database import getDbConnection

logger = logging.getLogger(__name__)

async def logAuditEvent(
    userId: str,
    action: str,
    resourceType: str,
    resourceId: Optional[str] = None,
    details: Optional[str] = None,
    ipAddress: Optional[str] = None,
    userAgent: Optional[str] = None
):
    """
    Log an audit event to the database
    """
    try:
        async with getDbConnection() as conn:
            query = """
                INSERT INTO auditlog (
                    "userId", action, "resourceType", "resourceId", details,
                    "ipAddress", "userAgent", timestamp
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """
            
            await conn.execute(query,
                userId, action, resourceType, resourceId, details,
                ipAddress, userAgent, datetime.now()
            )

            logger.info(f"✅ Audit event logged: {action} on {resourceType} by {userId}")
            return True

    except Exception as e:
        logger.error(f"❌ Failed to log audit event: {e}")
        # Don't raise exception for audit logging failures
        return False