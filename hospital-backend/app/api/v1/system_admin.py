"""
System Administration API endpoints
Consolidated admin utilities and audit logging functionality
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from datetime import datetime
import logging
import json
from typing import Optional

from ...core.database import getDbConnection, resetConnectionPools
from ...services.audit import logAuditEvent

router = APIRouter()
logger = logging.getLogger(__name__)

# ================================
# SYSTEM UTILITIES
# ================================

@router.post("/reset-connections")
async def resetConnections():
    """Reset database connection pools to force fresh connections"""
    try:
        await resetConnectionPools()
        return {"message": "Connection pools reset successfully", "status": "success"}
    except Exception as e:
        return {"error": str(e), "status": "error"}

@router.get("/health")
async def healthCheck():
    """System health check"""
    return {"status": "healthy", "message": "System Admin API is working"}

# ================================
# AUDIT LOGGING
# ================================

class AuditLogRequest(BaseModel):
    userId: str
    action: str
    resourcetype: str
    resourceid: Optional[str] = None
    details: Optional[str] = None
    ipAddress: Optional[str] = None
    userAgent: Optional[str] = None

@router.post("/audit/log")
async def createAuditLog(request: Request):
    """
    Create an audit log entry (frontend logging endpoint) - handles lowercase fields
    """
    try:
        # Parse raw request body to handle lowercase field names from frontend
        body = await request.body()
        requestData = json.loads(body.decode('utf-8'))
        logger.info(f"📝 Audit log request: {requestData}")

        # Create AuditLogRequest object with lowercase field mapping
        auditData = AuditLogRequest(
            userId=requestData.get('userId') or requestData.get('userid') or 'unknown',
            action=requestData.get('action') or 'unknown',
            resourcetype=requestData.get('resourcetype') or requestData.get('resourceType') or 'unknown',
            resourceid=requestData.get('resourceid') or requestData.get('resourceId'),
            details=requestData.get('details'),
            ipAddress=requestData.get('ipAddress') or requestData.get('ipaddress'),
            userAgent=requestData.get('userAgent') or requestData.get('useragent')
        )

        await logAuditEvent(
            userId=auditData.userId,
            action=auditData.action,
            resourceType=auditData.resourcetype,
            resourceId=auditData.resourceid,
            details=auditData.details,
            ipAddress=auditData.ipAddress,
            userAgent=auditData.userAgent
        )

        logger.info(f"📝 Audit log created: {auditData.action} by {auditData.userId}")
        return {
            "success": True,
            "message": "Audit log created successfully",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Create audit log error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create audit log: {str(e)}")

@router.get("/audit/logs")
async def getAuditLogs(
    userId: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100
):
    """
    Get audit logs with optional filtering
    """
    try:
        async with getDbConnection() as conn:
            query = "SELECT * FROM auditlog WHERE 1=1"
            params = []
            paramCount = 0

            if userId:
                paramCount += 1
                query += f' AND userId = ${paramCount}'
                params.append(userId)

            if action:
                paramCount += 1
                query += f" AND action = ${paramCount}"
                params.append(action)

            query += " ORDER BY timestamp DESC"

            paramCount += 1
            query += f" LIMIT ${paramCount}"
            params.append(limit)

            rows = await conn.fetch(query, *params)

            logs = []
            for row in rows:
                logDict = dict(row)
                logs.append({
                    'id': logDict.get('id'),
                    'userId': logDict.get('userId'),
                    'action': logDict.get('action'),
                    'resourcetype': logDict.get('resourcetype'),
                    'resourceid': logDict.get('resourceid'),
                    'details': logDict.get('details'),
                    'ipAddress': logDict.get('ipAddress'),
                    'userAgent': logDict.get('userAgent'),
                    'timestamp': logDict.get('timestamp').isoformat() if logDict.get('timestamp') else None
                })

            logger.info(f"📋 Retrieved {len(logs)} audit logs")
            return {"logs": logs, "total": len(logs)}

    except Exception as e:
        logger.error(f"❌ Get audit logs error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve audit logs")

# ================================
# BACKWARD COMPATIBILITY ALIASES
# ================================

# Keep old audit endpoints working during transition
@router.post("/log")
async def createAuditLogAlias(request: Request):
    """Backward compatibility alias for /audit/log"""
    return await createAuditLog(request)

@router.get("/logs")
async def getAuditLogsAlias(
    userId: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100
):
    """Backward compatibility alias for /audit/logs"""
    return await getAuditLogs(userId, action, limit)