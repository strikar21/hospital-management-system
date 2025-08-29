"""
Audit Compliance and Data Retention Service
Handles HIPAA compliance, data retention policies, and audit data governance
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, func, text
import logging
import json
from enum import Enum

from app.db.database import get_timescale_session
from app.models.timescale import AuditLog

logger = logging.getLogger(__name__)

class DataClassification(Enum):
    """Data classification levels for audit records"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

class RetentionPolicy(Enum):
    """Audit data retention policies"""
    SHORT_TERM = "short_term_30d"      # 30 days for system logs
    STANDARD = "standard_7yr"          # 7 years for HIPAA compliance
    LONG_TERM = "long_term_10yr"       # 10 years for critical security events
    PERMANENT = "permanent"            # Permanent retention for legal holds

class AuditComplianceService:
    """Service for managing audit compliance and data retention"""
    
    # Retention periods mapping
    RETENTION_PERIODS = {
        RetentionPolicy.SHORT_TERM: timedelta(days=30),
        RetentionPolicy.STANDARD: timedelta(days=2557),  # 7 years
        RetentionPolicy.LONG_TERM: timedelta(days=3653), # 10 years
        RetentionPolicy.PERMANENT: None  # Never delete
    }
    
    # Event classification rules
    CLASSIFICATION_RULES = {
        # HIPAA-relevant events are always confidential or restricted
        "patient_interaction": DataClassification.RESTRICTED,
        "vitals_access": DataClassification.RESTRICTED,
        "medical_record_access": DataClassification.RESTRICTED,
        
        # Device events are internal unless they involve patient data
        "esp32_vitals": DataClassification.CONFIDENTIAL,
        "door_scanner": DataClassification.INTERNAL,
        
        # System events are typically internal
        "api_request": DataClassification.INTERNAL,
        "user_action": DataClassification.CONFIDENTIAL,
        "system_event": DataClassification.INTERNAL,
        
        # Security events are highly sensitive
        "authentication": DataClassification.CONFIDENTIAL,
        "authorization": DataClassification.CONFIDENTIAL,
        "security_alert": DataClassification.RESTRICTED
    }
    
    # Retention policy rules
    RETENTION_RULES = {
        # HIPAA-relevant events require 7-year retention minimum
        "hipaa_relevant": RetentionPolicy.STANDARD,
        
        # Security events require long-term retention
        "security_critical": RetentionPolicy.LONG_TERM,
        
        # System performance logs can be shorter
        "system_performance": RetentionPolicy.SHORT_TERM,
        
        # Default for most events
        "default": RetentionPolicy.STANDARD
    }
    
    @staticmethod
    async def classify_audit_event(
        event_type: str,
        event_category: str,
        action: str,
        patient_id: Optional[str] = None,
        device_metadata: Optional[Dict] = None
    ) -> Tuple[DataClassification, RetentionPolicy]:
        """
        Automatically classify an audit event and determine retention policy
        
        Args:
            event_type: Type of event
            event_category: Event category
            action: Specific action
            patient_id: Patient ID if relevant
            device_metadata: Device metadata if relevant
            
        Returns:
            Tuple of (data_classification, retention_policy)
        """
        
        # Determine data classification
        classification = DataClassification.INTERNAL  # Default
        
        # HIPAA-relevant events (involve patient data)
        if patient_id or "patient" in action.lower():
            classification = DataClassification.RESTRICTED
        
        # ESP32 vitals data
        elif event_category == "esp32_watch" and "vital" in action.lower():
            classification = DataClassification.CONFIDENTIAL
            
        # User authentication/authorization
        elif "login" in action.lower() or "auth" in action.lower():
            classification = DataClassification.CONFIDENTIAL
            
        # Security alerts
        elif "security" in action.lower() or "alert" in action.lower():
            classification = DataClassification.RESTRICTED
            
        # Check classification rules
        for pattern, cls in AuditComplianceService.CLASSIFICATION_RULES.items():
            if pattern in action.lower() or pattern in event_category.lower():
                classification = cls
                break
        
        # Determine retention policy
        retention = RetentionPolicy.STANDARD  # Default 7 years for HIPAA
        
        # HIPAA-relevant events
        if patient_id or classification in [DataClassification.RESTRICTED, DataClassification.CONFIDENTIAL]:
            if "security" in action.lower() or "critical" in action.lower():
                retention = RetentionPolicy.LONG_TERM  # 10 years for critical events
            else:
                retention = RetentionPolicy.STANDARD  # 7 years for HIPAA
                
        # System performance logs
        elif event_category in ["backend", "database"] and "performance" in action.lower():
            retention = RetentionPolicy.SHORT_TERM  # 30 days
            
        # Door scanner logs (non-patient)
        elif event_category == "door_scanner" and not patient_id:
            retention = RetentionPolicy.SHORT_TERM  # 30 days
            
        return classification, retention
    
    @staticmethod
    async def apply_retention_policies() -> Dict[str, int]:
        """
        Apply retention policies and clean up expired audit logs
        
        Returns:
            Dictionary with cleanup statistics
        """
        stats = {
            "total_processed": 0,
            "deleted_records": 0,
            "archived_records": 0,
            "policies_applied": 0
        }
        
        try:
            async with get_timescale_session() as session:
                # Get all distinct retention policies
                result = await session.execute(
                    select(AuditLog.retention_policy, func.count(AuditLog.id))
                    .group_by(AuditLog.retention_policy)
                )
                
                for retention_policy, count in result:
                    stats["total_processed"] += count
                    
                    if not retention_policy:
                        continue
                    
                    try:
                        policy = RetentionPolicy(retention_policy)
                        retention_period = AuditComplianceService.RETENTION_PERIODS.get(policy)
                        
                        if retention_period is None:  # Permanent retention
                            continue
                        
                        # Calculate cutoff date
                        cutoff_date = datetime.utcnow() - retention_period
                        
                        # Delete expired records
                        delete_result = await session.execute(
                            delete(AuditLog)
                            .where(
                                and_(
                                    AuditLog.retention_policy == retention_policy,
                                    AuditLog.timestamp < cutoff_date
                                )
                            )
                        )
                        
                        deleted_count = delete_result.rowcount
                        stats["deleted_records"] += deleted_count
                        stats["policies_applied"] += 1
                        
                        if deleted_count > 0:
                            logger.info(f"Deleted {deleted_count} audit records with policy {retention_policy}")
                        
                    except ValueError:
                        logger.warning(f"Unknown retention policy: {retention_policy}")
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Failed to apply retention policies: {str(e)}")
            
        return stats
    
    @staticmethod
    async def generate_compliance_report(
        start_date: datetime,
        end_date: datetime,
        include_hipaa_only: bool = False
    ) -> Dict:
        """
        Generate audit compliance report for a given period
        
        Args:
            start_date: Report start date
            end_date: Report end date
            include_hipaa_only: Only include HIPAA-relevant events
            
        Returns:
            Compliance report dictionary
        """
        try:
            async with get_timescale_session() as session:
                # Base query
                base_query = select(
                    AuditLog.event_type,
                    AuditLog.event_category,
                    AuditLog.severity,
                    AuditLog.data_classification,
                    AuditLog.retention_policy,
                    AuditLog.hipaa_relevant,
                    func.count(AuditLog.id).label('event_count'),
                    func.count(AuditLog.id).filter(AuditLog.success == False).label('error_count'),
                    func.count(func.distinct(AuditLog.user_id)).label('unique_users'),
                    func.count(func.distinct(AuditLog.patient_id)).label('unique_patients'),
                    func.count(func.distinct(AuditLog.device_id)).label('unique_devices')
                ).where(
                    and_(
                        AuditLog.timestamp >= start_date,
                        AuditLog.timestamp <= end_date
                    )
                ).group_by(
                    AuditLog.event_type,
                    AuditLog.event_category,
                    AuditLog.severity,
                    AuditLog.data_classification,
                    AuditLog.retention_policy,
                    AuditLog.hipaa_relevant
                )
                
                if include_hipaa_only:
                    base_query = base_query.where(AuditLog.hipaa_relevant == True)
                
                result = await session.execute(base_query)
                
                # Process results
                events_summary = []
                total_events = 0
                total_errors = 0
                total_hipaa_events = 0
                
                for row in result:
                    event_data = {
                        "event_type": row.event_type,
                        "event_category": row.event_category,
                        "severity": row.severity,
                        "data_classification": row.data_classification,
                        "retention_policy": row.retention_policy,
                        "hipaa_relevant": row.hipaa_relevant,
                        "event_count": row.event_count,
                        "error_count": row.error_count,
                        "unique_users": row.unique_users,
                        "unique_patients": row.unique_patients,
                        "unique_devices": row.unique_devices
                    }
                    events_summary.append(event_data)
                    
                    total_events += row.event_count
                    total_errors += row.error_count
                    if row.hipaa_relevant:
                        total_hipaa_events += row.event_count
                
                # Get top users by activity
                top_users_result = await session.execute(
                    select(
                        AuditLog.user_id,
                        func.count(AuditLog.id).label('activity_count')
                    ).where(
                        and_(
                            AuditLog.timestamp >= start_date,
                            AuditLog.timestamp <= end_date,
                            AuditLog.user_id.isnot(None)
                        )
                    ).group_by(AuditLog.user_id)
                    .order_by(func.count(AuditLog.id).desc())
                    .limit(10)
                )
                
                top_users = [
                    {"user_id": row.user_id, "activity_count": row.activity_count}
                    for row in top_users_result
                ]
                
                return {
                    "report_period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "hipaa_only": include_hipaa_only
                    },
                    "summary": {
                        "total_events": total_events,
                        "total_errors": total_errors,
                        "total_hipaa_events": total_hipaa_events,
                        "error_rate_percent": round((total_errors / max(total_events, 1)) * 100, 2),
                        "hipaa_event_percent": round((total_hipaa_events / max(total_events, 1)) * 100, 2)
                    },
                    "events_by_category": events_summary,
                    "top_users": top_users,
                    "generated_at": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to generate compliance report: {str(e)}")
            return {"error": str(e), "generated_at": datetime.utcnow().isoformat()}
    
    @staticmethod
    async def check_compliance_violations() -> List[Dict]:
        """
        Check for potential compliance violations in audit data
        
        Returns:
            List of compliance violations found
        """
        violations = []
        
        try:
            async with get_timescale_session() as session:
                # Check for HIPAA events without proper classification
                hipaa_without_classification = await session.execute(
                    select(func.count(AuditLog.id))
                    .where(
                        and_(
                            AuditLog.hipaa_relevant == True,
                            AuditLog.data_classification.is_(None)
                        )
                    )
                )
                
                count = hipaa_without_classification.scalar()
                if count > 0:
                    violations.append({
                        "type": "missing_classification",
                        "description": f"{count} HIPAA-relevant events without data classification",
                        "severity": "high",
                        "count": count
                    })
                
                # Check for events without retention policy
                no_retention_policy = await session.execute(
                    select(func.count(AuditLog.id))
                    .where(AuditLog.retention_policy.is_(None))
                )
                
                count = no_retention_policy.scalar()
                if count > 0:
                    violations.append({
                        "type": "missing_retention_policy",
                        "description": f"{count} audit events without retention policy",
                        "severity": "medium",
                        "count": count
                    })
                
                # Check for high error rates by user
                high_error_users = await session.execute(
                    select(
                        AuditLog.user_id,
                        func.count(AuditLog.id).label('total_events'),
                        func.count(AuditLog.id).filter(AuditLog.success == False).label('error_events')
                    ).where(
                        and_(
                            AuditLog.user_id.isnot(None),
                            AuditLog.timestamp >= datetime.utcnow() - timedelta(days=7)
                        )
                    ).group_by(AuditLog.user_id)
                    .having(func.count(AuditLog.id) > 10)  # Users with > 10 events
                )
                
                for row in high_error_users:
                    error_rate = (row.error_events / row.total_events) * 100
                    if error_rate > 20:  # > 20% error rate
                        violations.append({
                            "type": "high_error_rate",
                            "description": f"User {row.user_id} has {error_rate:.1f}% error rate",
                            "severity": "medium",
                            "user_id": row.user_id,
                            "error_rate": error_rate,
                            "total_events": row.total_events,
                            "error_events": row.error_events
                        })
                
        except Exception as e:
            logger.error(f"Failed to check compliance violations: {str(e)}")
            violations.append({
                "type": "check_failed",
                "description": f"Compliance check failed: {str(e)}",
                "severity": "critical"
            })
        
        return violations
    
    @staticmethod
    async def export_audit_data(
        start_date: datetime,
        end_date: datetime,
        event_types: Optional[List[str]] = None,
        format: str = "json"
    ) -> Dict:
        """
        Export audit data for compliance or legal purposes
        
        Args:
            start_date: Export start date
            end_date: Export end date
            event_types: List of event types to include
            format: Export format (json, csv)
            
        Returns:
            Export result with data or file path
        """
        try:
            async with get_timescale_session() as session:
                query = select(AuditLog).where(
                    and_(
                        AuditLog.timestamp >= start_date,
                        AuditLog.timestamp <= end_date
                    )
                ).order_by(AuditLog.timestamp)
                
                if event_types:
                    query = query.where(AuditLog.event_type.in_(event_types))
                
                result = await session.execute(query)
                audit_logs = result.scalars().all()
                
                # Convert to dictionaries
                exported_data = []
                for log in audit_logs:
                    log_data = {
                        "id": log.id,
                        "timestamp": log.timestamp.isoformat(),
                        "event_type": log.event_type,
                        "event_category": log.event_category,
                        "action": log.action,
                        "severity": log.severity,
                        "user_id": log.user_id,
                        "patient_id": log.patient_id,
                        "device_id": log.device_id,
                        "session_id": log.session_id,
                        "description": log.description,
                        "source_ip": log.source_ip,
                        "user_agent": log.user_agent,
                        "endpoint": log.endpoint,
                        "http_method": log.http_method,
                        "http_status": log.http_status,
                        "execution_time_ms": log.execution_time_ms,
                        "success": log.success,
                        "error_message": log.error_message,
                        "data_classification": log.data_classification,
                        "retention_policy": log.retention_policy,
                        "hipaa_relevant": log.hipaa_relevant
                    }
                    exported_data.append(log_data)
                
                return {
                    "export_summary": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "record_count": len(exported_data),
                        "format": format,
                        "exported_at": datetime.utcnow().isoformat()
                    },
                    "data": exported_data if format == "json" else None,
                    "status": "success"
                }
                
        except Exception as e:
            logger.error(f"Failed to export audit data: {str(e)}")
            return {
                "export_summary": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "exported_at": datetime.utcnow().isoformat()
                },
                "status": "error",
                "error": str(e)
            }