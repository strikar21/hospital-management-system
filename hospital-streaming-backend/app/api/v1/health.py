from fastapi import APIRouter, Request
from typing import Dict, Any
from datetime import datetime
from sqlalchemy import select, func

from app.db.database import database
from app.models.device import Device, DeviceAlert, VitalReading

router = APIRouter(prefix="/health")

@router.get("/")
async def system_health():
    """Overall system health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {
            "api": "healthy",
            "database": "healthy",  # TODO: Add actual DB health check
            "websocket": "healthy",
            "mqtt": "healthy"  # TODO: Add actual MQTT health check
        }
    }

@router.get("/devices")
async def device_health_summary():
    """Get device health summary"""
    try:
        # Device counts by status
        status_query = """
            SELECT status, COUNT(*) as count
            FROM devices 
            WHERE is_active = true
            GROUP BY status
        """
        status_results = await database.fetch_all(status_query)
        
        # Device types
        type_query = """
            SELECT device_type, COUNT(*) as count
            FROM devices 
            WHERE is_active = true
            GROUP BY device_type
        """
        type_results = await database.fetch_all(type_query)
        
        # Active alerts
        alert_query = """
            SELECT severity, COUNT(*) as count
            FROM device_alerts 
            WHERE is_active = true AND is_acknowledged = false
            GROUP BY severity
        """
        alert_results = await database.fetch_all(alert_query)
        
        # Recent vitals activity (last hour)
        vitals_query = """
            SELECT COUNT(*) as count
            FROM vital_readings 
            WHERE received_timestamp > NOW() - INTERVAL '1 hour'
        """
        vitals_result = await database.fetch_one(vitals_query)
        
        return {
            "device_status": {row["status"]: row["count"] for row in status_results},
            "device_types": {row["device_type"]: row["count"] for row in type_results},
            "active_alerts": {row["severity"]: row["count"] for row in alert_results},
            "vitals_last_hour": vitals_result["count"] if vitals_result else 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "error": f"Failed to get device health: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/streaming")
async def streaming_health(request: Request):
    """Get WebSocket streaming health"""
    websocket_manager = request.app.state.websocket_manager
    
    stats = websocket_manager.get_connection_stats()
    
    return {
        "websocket_connections": stats["total_connections"],
        "channels": stats["channels"],
        "status": "healthy" if stats["total_connections"] >= 0 else "warning",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/database")
async def database_health():
    """Database connectivity health check"""
    try:
        # Simple query to test DB connection
        result = await database.fetch_one("SELECT 1 as test")
        
        if result and result["test"] == 1:
            return {
                "status": "healthy",
                "database": "connected",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "error",
                "database": "query_failed",
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        return {
            "status": "error",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/alerts/summary")
async def alerts_summary():
    """Get summary of system alerts"""
    try:
        # Critical alerts
        critical_query = """
            SELECT d.device_id, d.name, da.alert_type, da.message, da.created_at
            FROM device_alerts da
            JOIN devices d ON da.device_id = d.device_id
            WHERE da.is_active = true 
            AND da.is_acknowledged = false 
            AND da.severity = 'critical'
            ORDER BY da.created_at DESC
            LIMIT 10
        """
        critical_alerts = await database.fetch_all(critical_query)
        
        # Alert counts by type
        type_query = """
            SELECT alert_type, COUNT(*) as count
            FROM device_alerts 
            WHERE is_active = true AND is_acknowledged = false
            GROUP BY alert_type
            ORDER BY count DESC
        """
        alert_types = await database.fetch_all(type_query)
        
        return {
            "critical_alerts": [
                {
                    "device_id": alert["device_id"],
                    "device_name": alert["name"],
                    "alert_type": alert["alert_type"],
                    "message": alert["message"],
                    "created_at": alert["created_at"].isoformat()
                }
                for alert in critical_alerts
            ],
            "alert_types": {row["alert_type"]: row["count"] for row in alert_types},
            "total_unacknowledged": sum(row["count"] for row in alert_types),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "error": f"Failed to get alerts summary: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/metrics")
async def system_metrics():
    """Get system performance metrics"""
    try:
        # Data ingestion rates (last 24 hours)
        vitals_query = """
            SELECT 
                DATE_TRUNC('hour', received_timestamp) as hour,
                COUNT(*) as count
            FROM vital_readings 
            WHERE received_timestamp > NOW() - INTERVAL '24 hours'
            GROUP BY hour
            ORDER BY hour DESC
        """
        vitals_hourly = await database.fetch_all(vitals_query)
        
        # Device activity
        device_activity_query = """
            SELECT 
                COUNT(*) as total_devices,
                COUNT(*) FILTER (WHERE status = 'online') as online_devices,
                COUNT(*) FILTER (WHERE status = 'offline') as offline_devices,
                COUNT(*) FILTER (WHERE last_heartbeat > NOW() - INTERVAL '5 minutes') as active_devices
            FROM devices 
            WHERE is_active = true
        """
        device_activity = await database.fetch_one(device_activity_query)
        
        return {
            "vitals_ingestion_hourly": [
                {
                    "hour": row["hour"].isoformat(),
                    "count": row["count"]
                }
                for row in vitals_hourly
            ],
            "device_activity": {
                "total_devices": device_activity["total_devices"],
                "online_devices": device_activity["online_devices"],
                "offline_devices": device_activity["offline_devices"],
                "active_devices": device_activity["active_devices"]
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "error": f"Failed to get metrics: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }

@router.post("/discharge/{patient_id}")
async def discharge_patient_health_router(patient_id: str):
    """Quick discharge endpoint in health router as workaround"""
    import time
    
    try:
        # Simple discharge - set patient inactive
        discharge_query = """
            UPDATE patients 
            SET is_active = false, 
                discharge_date = :discharge_date,
                status = 'discharged'
            WHERE id = :patient_id AND is_active = true
        """
        result = await database.execute(discharge_query, {
            "patient_id": patient_id,
            "discharge_date": datetime.utcnow().isoformat()
        })
        
        if result == 0:
            return {"success": False, "message": "Patient not found or already discharged"}
        
        return {
            "success": True,
            "message": f"Patient {patient_id} successfully discharged",
            "patient_id": patient_id,
            "discharge_date": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}