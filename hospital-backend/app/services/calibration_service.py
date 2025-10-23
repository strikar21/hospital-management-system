"""
Calibration Service - Device calibration tracking and management
STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case

Manages device calibration schedules, records calibration events,
and tracks calibration expiry for medical device compliance.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CalibrationRecord:
    """Calibration record data class"""
    calibrationId: int
    deviceId: str
    calibratedAt: datetime
    calibratedBy: Optional[str]
    calibrationType: str  # 'full', 'sensor_specific', 'quick'
    sensorType: Optional[str]  # 'heartRate', 'spo2', 'temperature', 'bloodPressure', 'all'
    notes: Optional[str]
    expiresAt: datetime
    createdAt: datetime

class CalibrationService:
    """Service for managing device calibration tracking"""

    def __init__(self):
        self.calibrationExpiryDays = 30  # Standard calibration cycle

    async def recordCalibration(
        self,
        deviceId: str,
        calibratedBy: str,
        calibrationType: str = 'full',
        sensorType: str = 'all',
        notes: Optional[str] = None
    ) -> bool:
        """
        Record a calibration event for a device

        Args:
            deviceId: Device identifier
            calibratedBy: Staff ID who performed calibration
            calibrationType: Type of calibration ('full', 'sensor_specific', 'quick')
            sensorType: Sensor calibrated ('heartRate', 'spo2', 'temperature', 'bloodPressure', 'all')
            notes: Additional notes about calibration

        Returns:
            True if successful, False otherwise
        """
        from app.core.database import getDbConnection

        try:
            calibratedAt = datetime.now()
            expiresAt = calibratedAt + timedelta(days=self.calibrationExpiryDays)

            async with getDbConnection() as conn:
                # Insert calibration record
                await conn.execute("""
                    INSERT INTO "deviceCalibration" (
                        "deviceId", "calibratedAt", "calibratedBy",
                        "calibrationType", "sensorType", notes, "expiresAt"
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, deviceId, calibratedAt, calibratedBy, calibrationType, sensorType, notes, expiresAt)

                # Update devices table with calibration dates
                await conn.execute("""
                    UPDATE devices
                    SET "lastCalibrationDate" = $1,
                        "calibrationDueDate" = $2
                    WHERE id = $3
                """, calibratedAt, expiresAt, deviceId)

                logger.info(
                    f"Calibration recorded: device={deviceId}, type={calibrationType}, "
                    f"by={calibratedBy}, expires={expiresAt.date()}"
                )

            return True

        except Exception as e:
            logger.error(f"Error recording calibration for device {deviceId}: {e}")
            return False

    async def getLastCalibration(self, deviceId: str) -> Optional[CalibrationRecord]:
        """
        Get the most recent calibration record for a device

        Args:
            deviceId: Device identifier

        Returns:
            CalibrationRecord if found, None otherwise
        """
        from app.core.database import getDbConnection

        try:
            async with getDbConnection() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM "deviceCalibration"
                    WHERE "deviceId" = $1
                    ORDER BY "calibratedAt" DESC
                    LIMIT 1
                """, deviceId)

                if not row:
                    return None

                return CalibrationRecord(
                    calibrationId=row['calibrationId'],
                    deviceId=row['deviceId'],
                    calibratedAt=row['calibratedAt'],
                    calibratedBy=row['calibratedBy'],
                    calibrationType=row['calibrationType'],
                    sensorType=row['sensorType'],
                    notes=row['notes'],
                    expiresAt=row['expiresAt'],
                    createdAt=row['createdAt']
                )

        except Exception as e:
            logger.error(f"Error retrieving last calibration for device {deviceId}: {e}")
            return None

    async def getCalibrationHistory(
        self,
        deviceId: str,
        limit: int = 10
    ) -> List[CalibrationRecord]:
        """
        Get calibration history for a device

        Args:
            deviceId: Device identifier
            limit: Maximum number of records to return

        Returns:
            List of CalibrationRecord objects
        """
        from app.core.database import getDbConnection

        try:
            async with getDbConnection() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM "deviceCalibration"
                    WHERE "deviceId" = $1
                    ORDER BY "calibratedAt" DESC
                    LIMIT $2
                """, deviceId, limit)

                return [
                    CalibrationRecord(
                        calibrationId=row['calibrationId'],
                        deviceId=row['deviceId'],
                        calibratedAt=row['calibratedAt'],
                        calibratedBy=row['calibratedBy'],
                        calibrationType=row['calibrationType'],
                        sensorType=row['sensorType'],
                        notes=row['notes'],
                        expiresAt=row['expiresAt'],
                        createdAt=row['createdAt']
                    )
                    for row in rows
                ]

        except Exception as e:
            logger.error(f"Error retrieving calibration history for device {deviceId}: {e}")
            return []

    async def isCalibrationDue(self, deviceId: str, daysThreshold: int = 30) -> bool:
        """
        Check if device calibration is due

        Args:
            deviceId: Device identifier
            daysThreshold: Days before expiry to consider "due"

        Returns:
            True if calibration is due, False otherwise
        """
        from app.core.database import getDbConnection

        try:
            async with getDbConnection() as conn:
                row = await conn.fetchrow("""
                    SELECT "lastCalibrationDate", "calibrationDueDate"
                    FROM devices
                    WHERE id = $1
                """, deviceId)

                if not row:
                    return True  # No calibration record, definitely due

                if not row['lastCalibrationDate']:
                    return True  # Never calibrated

                # Check if calibration due date has passed or is within threshold
                calibrationDueDate = row['calibrationDueDate']
                if calibrationDueDate:
                    daysUntilDue = (calibrationDueDate - datetime.now()).days
                    return daysUntilDue <= daysThreshold

                # Fallback: calculate from last calibration date
                lastCalibration = row['lastCalibrationDate']
                daysSinceCalibration = (datetime.now() - lastCalibration).days
                return daysSinceCalibration >= (self.calibrationExpiryDays - daysThreshold)

        except Exception as e:
            logger.error(f"Error checking calibration due status for device {deviceId}: {e}")
            return True  # Err on the side of caution

    async def getOverdueDevices(self, daysOverdue: int = 45) -> List[Dict[str, Any]]:
        """
        Get list of devices with overdue calibrations

        Args:
            daysOverdue: Days past expiry to consider "overdue"

        Returns:
            List of device dictionaries with calibration info
        """
        from app.core.database import getDbConnection

        try:
            async with getDbConnection() as conn:
                cutoffDate = datetime.now() - timedelta(days=daysOverdue)

                rows = await conn.fetch("""
                    SELECT
                        d.id as "deviceId",
                        d.name,
                        d.type,
                        d.location,
                        d."lastCalibrationDate",
                        d."calibrationDueDate",
                        EXTRACT(DAY FROM (NOW() - d."lastCalibrationDate")) as "daysSinceCalibration"
                    FROM devices d
                    WHERE d."lastCalibrationDate" < $1
                      OR d."lastCalibrationDate" IS NULL
                    ORDER BY d."lastCalibrationDate" NULLS FIRST
                """, cutoffDate)

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error retrieving overdue devices: {e}")
            return []

    async def getDevicesNeedingCalibration(
        self,
        daysThreshold: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get list of devices needing calibration within threshold

        Args:
            daysThreshold: Days before expiry to flag as "needs calibration"

        Returns:
            List of device dictionaries
        """
        from app.core.database import getDbConnection

        try:
            async with getDbConnection() as conn:
                thresholdDate = datetime.now() + timedelta(days=daysThreshold)

                rows = await conn.fetch("""
                    SELECT
                        d.id as "deviceId",
                        d.name,
                        d.type,
                        d.location,
                        d."lastCalibrationDate",
                        d."calibrationDueDate",
                        EXTRACT(DAY FROM (d."calibrationDueDate" - NOW())) as "daysUntilDue"
                    FROM devices d
                    WHERE d."calibrationDueDate" < $1
                      OR d."calibrationDueDate" IS NULL
                    ORDER BY d."calibrationDueDate" NULLS FIRST
                """, thresholdDate)

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error retrieving devices needing calibration: {e}")
            return []

    async def calculateCalibrationDueDate(self, deviceId: str) -> Optional[datetime]:
        """
        Calculate when device calibration is next due

        Args:
            deviceId: Device identifier

        Returns:
            Datetime when calibration is due, or None if no calibration record
        """
        lastCalibration = await self.getLastCalibration(deviceId)

        if not lastCalibration:
            return None

        return lastCalibration.calibratedAt + timedelta(days=self.calibrationExpiryDays)

    async def getCalibrationStats(self) -> Dict[str, Any]:
        """
        Get overall calibration statistics for all devices

        Returns:
            Dictionary with calibration statistics
        """
        from app.core.database import getDbConnection

        try:
            async with getDbConnection() as conn:
                now = datetime.now()

                stats = await conn.fetchrow("""
                    SELECT
                        COUNT(*) as "totalDevices",
                        COUNT(CASE WHEN "lastCalibrationDate" IS NULL THEN 1 END) as "neverCalibrated",
                        COUNT(CASE WHEN "calibrationDueDate" < $1 THEN 1 END) as "overdue",
                        COUNT(CASE WHEN "calibrationDueDate" BETWEEN $1 AND $2 THEN 1 END) as "dueSoon",
                        COUNT(CASE WHEN "calibrationDueDate" > $2 THEN 1 END) as "current"
                    FROM devices
                """, now, now + timedelta(days=7))

                return dict(stats) if stats else {}

        except Exception as e:
            logger.error(f"Error retrieving calibration stats: {e}")
            return {}

# Singleton instance
calibrationService = CalibrationService()
