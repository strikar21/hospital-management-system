"""
Audit logging API endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import logging
from typing import Optional

from ...core.database import get_db_connection
from ...services.audit import log_audit_event

router = APIRouter()
logger = logging.getLogger(__name__)

class AuditLogRequest(BaseModel):
    userId: str
    action: str
    resourceType: str
    resourceId: Optional[str] = None
    details: Optional[str] = None
    ipAddress: Optional[str] = None
    userAgent: Optional[str] = None

@router.post("/log")
async def create_audit_log(audit_data: AuditLogRequest):
    """
    Create an audit log entry (frontend logging endpoint)
    """
    try:
        await log_audit_event(
            user_id=audit_data.userId,
            action=audit_data.action,
            resource_type=audit_data.resourceType,
            resource_id=audit_data.resourceId,
            details=audit_data.details,
            ip_address=audit_data.ipAddress,
            user_agent=audit_data.userAgent
        )
        
        logger.info(f"📝 Audit log created: {audit_data.action} by {audit_data.userId}")
        return {
            "success": True,
            "message": "Audit log created successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Create audit log error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create audit log")

@router.get("/logs")
async def get_audit_logs(
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100
):
    """
    Get audit logs with optional filtering
    """
    try:
        async with get_db_connection() as conn:
            query = "SELECT * FROM auditlog WHERE 1=1"
            params = []
            param_count = 0
            
            if user_id:
                param_count += 1
                query += f" AND userid = ${param_count}"
                params.append(user_id)
                
            if action:
                param_count += 1
                query += f" AND action = ${param_count}"
                params.append(action)
            
            query += " ORDER BY timestamp DESC"
            
            param_count += 1
            query += f" LIMIT ${param_count}"
            params.append(limit)
            
            rows = await conn.fetch(query, *params)
            
            logs = []
            for row in rows:
                log_dict = dict(row)
                logs.append({
                    'id': log_dict.get('id'),
                    'userId': log_dict.get('userid'),
                    'action': log_dict.get('action'),
                    'resourceType': log_dict.get('resourcetype'),
                    'resourceId': log_dict.get('resourceid'),
                    'details': log_dict.get('details'),
                    'ipAddress': log_dict.get('ipaddress'),
                    'userAgent': log_dict.get('useragent'),
                    'timestamp': log_dict.get('timestamp').isoformat() if log_dict.get('timestamp') else None
                })
            
            logger.info(f"📋 Retrieved {len(logs)} audit logs")
            return {"logs": logs, "total": len(logs)}
            
    except Exception as e:
        logger.error(f"❌ Get audit logs error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve audit logs")