"""
Device Calibration Service

Manages device calibration records for Medical Device Rules 2017 compliance
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import asyncpg


class DeviceCalibrationService:
    """
    Manages device calibration

    Medical Device Rules 2017 requirements:
    - Regular calibration tracking
    - Calibration due dates
    - Accuracy measurements
    - Calibration history
    """

    def __init__(self, db_pool: asyncpg.Pool):
        self.pool = db_pool

    async def log_calibration(
        self,
        device_id: str,
        calibration_type: str,
        performed_by: str,
        heart_rate_accuracy: Optional[float] = None,
        spo2_accuracy: Optional[float] = None,
        temperature_accuracy: Optional[float] = None,
        blood_pressure_accuracy: Optional[float] = None,
        status: str = "pass",
        notes: Optional[str] = None,
        next_calibration_months: int = 2
    ) -> Dict[str, Any]:
        """
        Log a device calibration

        Args:
            device_id: Device reference (e.g., "Device/DEV000001")
            calibration_type: Type (routine, post-repair, initial)
            performed_by: Staff reference who performed calibration
            heart_rate_accuracy: HR sensor accuracy %
            spo2_accuracy: SpO2 sensor accuracy %
            temperature_accuracy: Temperature sensor accuracy %
            blood_pressure_accuracy: BP sensor accuracy %
            status: Calibration result (pass, fail, conditional)
            notes: Additional notes
            next_calibration_months: Months until next calibration

        Returns:
            Calibration record
        """
        # Ensure proper references
        if not device_id.startswith('Device/'):
            device_id = f'Device/{device_id}'

        if not performed_by.startswith('Practitioner/'):
            performed_by = f'Practitioner/{performed_by}'

        # Calculate next calibration date
        next_due = datetime.now(timezone.utc) + timedelta(days=30 * next_calibration_months)

        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO deviceCalibration
                (time, deviceId, calibrationType, performedBy,
                 heartRateAccuracy, spo2Accuracy, temperatureAccuracy, bloodPressureAccuracy,
                 status, notes, nextCalibrationDue)
                VALUES (NOW(), $1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, device_id, calibration_type, performed_by,
               heart_rate_accuracy, spo2_accuracy, temperature_accuracy,
               blood_pressure_accuracy, status, notes, next_due)

        return {
            "deviceId": device_id,
            "calibrationType": calibration_type,
            "performedBy": performed_by,
            "status": status,
            "nextCalibrationDue": next_due.isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def get_calibration_history(
        self,
        device_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get calibration history for a device

        Args:
            device_id: Device ID
            limit: Maximum records to return

        Returns:
            List of calibration records
        """
        if not device_id.startswith('Device/'):
            device_id = f'Device/{device_id}'

        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT time, deviceId, calibrationType, performedBy,
                       heartRateAccuracy, spo2Accuracy, temperatureAccuracy,
                       bloodPressureAccuracy, status, notes, nextCalibrationDue
                FROM deviceCalibration
                WHERE deviceId = $1
                ORDER BY time DESC
                LIMIT $2
            """, device_id, limit)

        return [
            {
                "time": row['time'].isoformat(),
                "deviceId": row['deviceid'],
                "calibrationType": row['calibrationtype'],
                "performedBy": row['performedby'],
                "heartRateAccuracy": float(row['heartrateaccuracy']) if row['heartrateaccuracy'] else None,
                "spo2Accuracy": float(row['spo2accuracy']) if row['spo2accuracy'] else None,
                "temperatureAccuracy": float(row['temperatureaccuracy']) if row['temperatureaccuracy'] else None,
                "bloodPressureAccuracy": float(row['bloodpressureaccuracy']) if row['bloodpressureaccuracy'] else None,
                "status": row['status'],
                "notes": row['notes'],
                "nextCalibrationDue": row['nextcalibrationdue'].isoformat() if row['nextcalibrationdue'] else None
            }
            for row in rows
        ]

    async def get_devices_due_for_calibration(
        self,
        days_ahead: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get devices due for calibration

        Args:
            days_ahead: Number of days to look ahead

        Returns:
            List of devices due for calibration
        """
        cutoff_date = datetime.now(timezone.utc) + timedelta(days=days_ahead)

        async with self.pool.acquire() as conn:
            # Get the latest calibration for each device
            rows = await conn.fetch("""
                SELECT DISTINCT ON (deviceId)
                    deviceId,
                    nextCalibrationDue,
                    time as lastCalibration,
                    status as lastStatus
                FROM deviceCalibration
                WHERE nextCalibrationDue <= $1
                  AND status = 'pass'
                ORDER BY deviceId, time DESC
            """, cutoff_date)

        return [
            {
                "deviceId": row['deviceid'],
                "nextCalibrationDue": row['nextcalibrationdue'].isoformat(),
                "lastCalibration": row['lastcalibration'].isoformat(),
                "lastStatus": row['laststatus'],
                "daysUntilDue": (row['nextcalibrationdue'] - datetime.now(timezone.utc)).days
            }
            for row in rows
        ]

    async def is_device_calibrated(self, device_id: str) -> bool:
        """
        Check if device has valid calibration

        Args:
            device_id: Device ID

        Returns:
            True if device has valid calibration, False otherwise
        """
        if not device_id.startswith('Device/'):
            device_id = f'Device/{device_id}'

        async with self.pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM deviceCalibration
                    WHERE deviceId = $1
                      AND status = 'pass'
                      AND nextCalibrationDue > NOW()
                    ORDER BY time DESC
                    LIMIT 1
                )
            """, device_id)

        return result

    async def get_calibration_stats(self) -> Dict[str, Any]:
        """
        Get calibration statistics

        Returns:
            Statistics on calibrations
        """
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(DISTINCT deviceId) as total_devices,
                    COUNT(*) as total_calibrations,
                    COUNT(*) FILTER (WHERE status = 'pass') as passed,
                    COUNT(*) FILTER (WHERE status = 'fail') as failed,
                    COUNT(*) FILTER (WHERE nextCalibrationDue < NOW()) as overdue
                FROM deviceCalibration
            """)

        return {
            "totalDevices": stats['total_devices'],
            "totalCalibrations": stats['total_calibrations'],
            "passed": stats['passed'],
            "failed": stats['failed'],
            "overdue": stats['overdue']
        }
