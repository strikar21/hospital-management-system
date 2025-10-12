"""
Audit API Endpoints
Provides audit logging functionality for frontend
"""

from fastapi import APIRouter, HTTPException, Depends
import logging
from typing import Dict, Any

from ...services.audit import logAuditEvent
from ...core.auth_dependencies import require_any_staff

router = APIRouter(dependencies=[Depends(require_any_staff)])
logger = logging.getLogger(__name__)


@router.post("/log")
async def log_audit_event(audit_data: Dict[str, Any]):
    """Log an audit event"""
    try:
        # Extract required fields with defaults
        action = audit_data.get('action', 'unknown_action')
        resource = audit_data.get('resource', 'unknown_resource')
        user_id = audit_data.get('userId', 'system')
        details = str(audit_data.get('details', {}))
        ip_address = audit_data.get('ipAddress', '0.0.0.0')
        user_agent = audit_data.get('userAgent', 'unknown')

        # Log the audit event using the function
        success = await logAuditEvent(
            userId=user_id,
            action=action,
            resourceType=resource,
            resourceId=None,
            details=details,
            ipAddress=ip_address,
            userAgent=user_agent
        )

        if success:
            logger.info(f"✅ Logged audit event: {action} on {resource} by {user_id}")
            return {"success": True, "message": "Audit event logged successfully"}
        else:
            logger.warning(f"⚠️ Failed to log audit event: {action} on {resource}")
            return {"success": False, "message": "Failed to log audit event"}

    except Exception as e:
        logger.error(f"❌ Error logging audit event: {e}")
        # Always return success to avoid blocking frontend functionality
        # Audit logging failures should be transparent to frontend
        return {"success": True, "message": "Audit event received"}


@router.get("/events")
async def get_audit_events(
    limit: int = 100,
    offset: int = 0,
    user_id: str = None,
    action: str = None
):
    """Get audit events with optional filtering"""
    try:
        # Simple stub implementation - audit event retrieval not implemented yet
        logger.info("✅ Audit events retrieval requested (not yet implemented)")
        return {"events": [], "count": 0, "message": "Audit events retrieval not implemented"}

    except Exception as e:
        logger.error(f"❌ Error retrieving audit events: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve audit events: {str(e)}")


@router.get("/events/{event_id}")
async def get_audit_event(event_id: str):
    """Get a specific audit event by ID"""
    try:
        # Simple stub implementation - audit event retrieval not implemented yet
        logger.info(f"✅ Audit event {event_id} retrieval requested (not yet implemented)")
        raise HTTPException(status_code=404, detail="Audit event retrieval not implemented")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error retrieving audit event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve audit event: {str(e)}")