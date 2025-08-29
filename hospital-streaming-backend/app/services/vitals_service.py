from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import text
from app.db.database import timescale_db
from app.models.timescale import VitalReading, DeviceAlertTS
import logging

logger = logging.getLogger(__name__)

class VitalsService:
    """Service for managing vital signs data in TimescaleDB"""
    
    @staticmethod
    async def store_vital_reading(
        device_id: str,
        patient_id: str,
        vital_type: str,
        value: float,
        unit: str = None,
        quality_indicator: str = None,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Store a vital reading in TimescaleDB"""
        try:
            query = """
                INSERT INTO vital_readings ("deviceId", "patientId", "vitalType", value, unit, "qualityIndicator", metadata)
                VALUES (:device_id, :patient_id, :vital_type, :value, :unit, :quality_indicator, :metadata)
            """
            
            await timescale_db.execute(
                query=query,
                values={
                    "device_id": device_id,
                    "patient_id": patient_id,
                    "vital_type": vital_type,
                    "value": value,
                    "unit": unit,
                    "quality_indicator": quality_indicator,
                    "metadata": metadata
                }
            )
            
            logger.debug(f"Stored vital reading: {device_id} - {vital_type}: {value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store vital reading: {e}")
            return False
    
    @staticmethod
    async def get_latest_vitals(patient_id: str) -> List[Dict[str, Any]]:
        """Get latest vital readings for a patient"""
        try:
            query = """
                SELECT DISTINCT ON ("vitalType")
                    "deviceId", "vitalType", value, unit, timestamp, "qualityIndicator"
                FROM vital_readings
                WHERE "patientId" = :patient_id
                ORDER BY "vitalType", timestamp DESC
            """
            
            results = await timescale_db.fetch_all(
                query=query,
                values={"patient_id": patient_id}
            )
            
            return [
                {
                    "device_id": row["deviceId"],
                    "vital_type": row["vitalType"],
                    "value": row["value"],
                    "unit": row["unit"],
                    "timestamp": row["timestamp"].isoformat(),
                    "quality_indicator": row["qualityIndicator"]
                }
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"Failed to get latest vitals: {e}")
            return []
    
    @staticmethod
    async def get_vital_history(
        patient_id: str,
        vital_type: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get vital reading history for a patient"""
        try:
            query = """
                SELECT "deviceId", value, unit, timestamp, "qualityIndicator"
                FROM vital_readings
                WHERE "patientId" = :patient_id 
                  AND "vitalType" = :vital_type
                  AND timestamp > NOW() - INTERVAL ':hours hours'
                ORDER BY timestamp ASC
            """
            
            results = await timescale_db.fetch_all(
                query=query,
                values={
                    "patient_id": patient_id,
                    "vital_type": vital_type,
                    "hours": hours
                }
            )
            
            return [
                {
                    "device_id": row["deviceId"],
                    "value": row["value"],
                    "unit": row["unit"],
                    "timestamp": row["timestamp"].isoformat(),
                    "quality_indicator": row["qualityIndicator"]
                }
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"Failed to get vital history: {e}")
            return []
    
    @staticmethod
    async def get_vital_statistics(
        patient_id: str,
        vital_type: str,
        hours: int = 24
    ) -> Optional[Dict[str, Any]]:
        """Get vital statistics (min, max, avg) for a patient"""
        try:
            query = """
                SELECT 
                    COUNT(*) as "readingCount",
                    MIN(value) as "minValue",
                    MAX(value) as "maxValue",
                    AVG(value) as "avgValue",
                    STDDEV(value) as "stddevValue"
                FROM vital_readings
                WHERE "patientId" = :patient_id 
                  AND "vitalType" = :vital_type
                  AND timestamp > NOW() - INTERVAL ':hours hours'
            """
            
            result = await timescale_db.fetch_one(
                query=query,
                values={
                    "patient_id": patient_id,
                    "vital_type": vital_type,
                    "hours": hours
                }
            )
            
            if result and result["readingCount"] > 0:
                return {
                    "reading_count": result["readingCount"],
                    "min_value": float(result["minValue"]) if result["minValue"] else None,
                    "max_value": float(result["maxValue"]) if result["maxValue"] else None,
                    "avg_value": float(result["avgValue"]) if result["avgValue"] else None,
                    "stddev_value": float(result["stddevValue"]) if result["stddevValue"] else None
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get vital statistics: {e}")
            return None
    
    @staticmethod
    async def store_device_alert(
        device_id: str,
        patient_id: str,
        alert_type: str,
        severity: str,
        message: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Store a device alert in TimescaleDB"""
        try:
            query = """
                INSERT INTO device_alerts_ts ("deviceId", "patientId", "alertType", severity, message, metadata)
                VALUES (:device_id, :patient_id, :alert_type, :severity, :message, :metadata)
            """
            
            await timescale_db.execute(
                query=query,
                values={
                    "device_id": device_id,
                    "patient_id": patient_id,
                    "alert_type": alert_type,
                    "severity": severity,
                    "message": message,
                    "metadata": metadata
                }
            )
            
            logger.info(f"Stored device alert: {device_id} - {severity} - {alert_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store device alert: {e}")
            return False
    
    @staticmethod
    async def get_active_alerts(patient_id: str = None) -> List[Dict[str, Any]]:
        """Get active alerts for a patient or all patients"""
        try:
            if patient_id:
                query = """
                    SELECT "deviceId", "alertType", severity, message, timestamp, metadata
                    FROM device_alerts_ts
                    WHERE "patientId" = :patient_id 
                      AND "resolvedAt" IS NULL
                      AND acknowledged = false
                    ORDER BY timestamp DESC
                """
                values = {"patient_id": patient_id}
            else:
                query = """
                    SELECT "deviceId", "patientId", "alertType", severity, message, timestamp, metadata
                    FROM device_alerts_ts
                    WHERE "resolvedAt" IS NULL
                      AND acknowledged = false
                    ORDER BY timestamp DESC
                    LIMIT 100
                """
                values = {}
            
            results = await timescale_db.fetch_all(query=query, values=values)
            
            return [
                {
                    "device_id": row["deviceId"],
                    "patient_id": row.get("patientId"),
                    "alert_type": row["alertType"],
                    "severity": row["severity"],
                    "message": row["message"],
                    "timestamp": row["timestamp"].isoformat(),
                    "metadata": row["metadata"]
                }
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"Failed to get active alerts: {e}")
            return []