"""
Audit Service - Comprehensive logging for hospital IoT system
Handles audit logging for ESP32 watches, door scanners, frontend actions, and backend events
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging
import json
from fastapi import Request

from app.db.database import timescale_db, timescale_metadata
import sqlalchemy as sa

logger = logging.getLogger(__name__)

# Define audit_logs table using the existing database pattern
audit_logs = sa.Table(
    'audit_logs',
    timescale_metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
    sa.Column('eventType', sa.String(50), nullable=False),
    sa.Column('eventCategory', sa.String(50), nullable=False),
    sa.Column('action', sa.String(100), nullable=False),
    sa.Column('severity', sa.String(20), nullable=False),
    sa.Column('userId', sa.String(50)),
    sa.Column('patientId', sa.String(50)),
    sa.Column('deviceId', sa.String(50)),
    sa.Column('sessionId', sa.String(100)),
    sa.Column('description', sa.Text, nullable=False),
    sa.Column('sourceIp', sa.String(45)),
    sa.Column('userAgent', sa.String(500)),
    sa.Column('endpoint', sa.String(200)),
    sa.Column('httpMethod', sa.String(10)),
    sa.Column('httpStatus', sa.Integer),
    sa.Column('requestData', sa.JSON),
    sa.Column('responseData', sa.JSON),
    sa.Column('deviceMetadata', sa.JSON),
    sa.Column('additionalContext', sa.JSON),
    sa.Column('executionTimeMs', sa.Integer),
    sa.Column('success', sa.Boolean, default=True),
    sa.Column('errorMessage', sa.Text),
    sa.Column('dataClassification', sa.String(20)),
    sa.Column('retentionPolicy', sa.String(50)),
    sa.Column('hipaaRelevant', sa.Boolean, default=False)
)

class AuditService:
    """Centralized audit logging service for all hospital system components"""
    
    @staticmethod
    async def log_event(
        event_type: str,
        event_category: str,
        action: str,
        description: str,
        severity: str = "info",
        user_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        device_id: Optional[str] = None,
        session_id: Optional[str] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        http_method: Optional[str] = None,
        http_status: Optional[int] = None,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        device_metadata: Optional[Dict[str, Any]] = None,
        additional_context: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        data_classification: str = "internal",
        retention_policy: str = "standard_7yr",
        hipaa_relevant: bool = False
    ) -> bool:
        """Log an audit event to TimescaleDB"""
        try:
            # Sanitize sensitive data
            sanitized_request = AuditService._sanitize_data(request_data) if request_data else None
            sanitized_response = AuditService._sanitize_data(response_data) if response_data else None
            
            # Create audit entry using the existing database pattern
            query = audit_logs.insert().values(
                eventType=event_type,
                eventCategory=event_category,
                action=action,
                severity=severity,
                userId=user_id,
                patientId=patient_id,
                deviceId=device_id,
                sessionId=session_id,
                description=description,
                sourceIp=source_ip,
                userAgent=user_agent,
                endpoint=endpoint,
                httpMethod=http_method,
                httpStatus=http_status,
                requestData=sanitized_request,
                responseData=sanitized_response,
                deviceMetadata=device_metadata,
                additionalContext=additional_context,
                executionTimeMs=execution_time_ms,
                success=success,
                errorMessage=error_message,
                dataClassification=data_classification,
                retentionPolicy=retention_policy,
                hipaaRelevant=hipaa_relevant
            )
            
            # Execute using the existing timescale database connection
            await timescale_db.execute(query)
            return True
                
        except Exception as e:
            logger.error(f"Failed to log audit event: {str(e)}")
            return False
    
    @staticmethod
    def _sanitize_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove sensitive information from audit data
        
        Args:
            data: Data dictionary to sanitize
            
        Returns:
            Dict: Sanitized data with sensitive fields removed/masked
        """
        if not isinstance(data, dict):
            return data
            
        sensitive_fields = {
            'password', 'token', 'secret', 'key', 'credential', 
            'ssn', 'social_security', 'credit_card', 'bank_account'
        }
        
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            
            # Check if key contains sensitive field names
            if any(sensitive in key_lower for sensitive in sensitive_fields):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = AuditService._sanitize_data(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    AuditService._sanitize_data(item) if isinstance(item, dict) else item 
                    for item in value
                ]
            else:
                sanitized[key] = value
                
        return sanitized
    
    @staticmethod
    async def log_esp32_event(
        device_id: str,
        action: str,
        description: str,
        patient_id: Optional[str] = None,
        severity: str = "info",
        device_metadata: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> bool:
        """Log ESP32 watch specific events"""
        return await AuditService.log_event(
            event_type="device_event",
            event_category="esp32_watch",
            action=action,
            description=description,
            severity=severity,
            patient_id=patient_id,
            device_id=device_id,
            device_metadata=device_metadata,
            success=success,
            error_message=error_message,
            hipaa_relevant=bool(patient_id)  # HIPAA relevant if patient data involved
        )
    
    @staticmethod
    async def log_door_scanner_event(
        device_id: str,
        action: str,
        description: str,
        severity: str = "info",
        device_metadata: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> bool:
        """Log door scanner specific events"""
        return await AuditService.log_event(
            event_type="device_event",
            event_category="door_scanner",
            action=action,
            description=description,
            severity=severity,
            device_id=device_id,
            device_metadata=device_metadata,
            success=success,
            error_message=error_message
        )
    
    @staticmethod
    async def log_user_action(
        user_id: str,
        action: str,
        description: str,
        patient_id: Optional[str] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None,
        severity: str = "info"
    ) -> bool:
        """Log frontend user actions"""
        return await AuditService.log_event(
            event_type="user_action",
            event_category="frontend",
            action=action,
            description=description,
            severity=severity,
            user_id=user_id,
            patient_id=patient_id,
            source_ip=source_ip,
            user_agent=user_agent,
            session_id=session_id,
            additional_context=additional_context,
            hipaa_relevant=bool(patient_id)
        )
    
    @staticmethod
    async def log_api_request(
        endpoint: str,
        http_method: str,
        http_status: int,
        user_id: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> bool:
        """Log API request events"""
        severity = "error" if http_status >= 400 else "info"
        description = f"{http_method} {endpoint} - {http_status}"
        
        return await AuditService.log_event(
            event_type="api_request",
            event_category="backend",
            action=f"{http_method.lower()}_request",
            description=description,
            severity=severity,
            user_id=user_id,
            source_ip=source_ip,
            user_agent=user_agent,
            endpoint=endpoint,
            http_method=http_method,
            http_status=http_status,
            request_data=request_data,
            response_data=response_data,
            execution_time_ms=execution_time_ms,
            success=success,
            error_message=error_message
        )
    
    @staticmethod
    async def get_audit_logs(
        event_type: Optional[str] = None,
        event_category: Optional[str] = None,
        user_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        device_id: Optional[str] = None,
        severity: Optional[str] = None,
        hours_back: int = 24,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Retrieve audit logs with filters"""
        try:
            # Build query using existing database pattern
            query = sa.select([audit_logs]).order_by(audit_logs.c.timestamp.desc()).limit(limit)
            
            # Apply time filter
            if hours_back > 0:
                cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
                query = query.where(audit_logs.c.timestamp >= cutoff_time)
            
            # Apply filters
            if event_type:
                query = query.where(audit_logs.c.eventType == event_type)
            if event_category:
                query = query.where(audit_logs.c.eventCategory == event_category)
            if user_id:
                query = query.where(audit_logs.c.userId == user_id)
            if patient_id:
                query = query.where(audit_logs.c.patientId == patient_id)
            if device_id:
                query = query.where(audit_logs.c.deviceId == device_id)
            if severity:
                query = query.where(audit_logs.c.severity == severity)
            
            # Execute query
            result = await timescale_db.fetch_all(query)
            
            return [
                {
                    "id": row["id"],
                    "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None,
                    "event_type": row["eventType"],
                    "event_category": row["eventCategory"],
                    "action": row["action"],
                    "severity": row["severity"],
                    "user_id": row["userId"],
                    "patient_id": row["patientId"],
                    "device_id": row["deviceId"],
                    "description": row["description"],
                    "success": row["success"],
                    "error_message": row["errorMessage"],
                    "endpoint": row["endpoint"],
                    "http_method": row["httpMethod"],
                    "http_status": row["httpStatus"],
                    "execution_time_ms": row["executionTimeMs"],
                    "source_ip": row["sourceIp"],
                    "hipaa_relevant": row["hipaaRelevant"]
                }
                for row in result
            ]
                
        except Exception as e:
            logger.error(f"Failed to retrieve audit logs: {str(e)}")
            return []