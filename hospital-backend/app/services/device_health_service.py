"""
Device Health Service - Device performance monitoring and baseline tracking
STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case

Calculates device baselines, detects sensor drift, tracks battery health,
and monitors device reliability metrics for medical device quality assurance.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import statistics

logger = logging.getLogger(__name__)

@dataclass
class DeviceBaseline:
    """Device baseline performance metrics"""
    baselineId: int
    deviceId: str
    batteryDrainRatePerHour: Optional[float]
    batteryHealthPercentage: int
    heartRateMean: Optional[float]
    heartRateStdDev: Optional[float]
    spo2Mean: Optional[float]
    spo2StdDev: Optional[float]
    temperatureMean: Optional[float]
    temperatureStdDev: Optional[float]
    systolicBpMean: Optional[float]
    systolicBpStdDev: Optional[float]
    diastolicBpMean: Optional[float]
    diastolicBpStdDev: Optional[float]
    baselineCalculatedAt: datetime
    baselineUpdatedAt: datetime
    sampleCount: int
    calculationPeriodDays: int

class DeviceHealthService:
    """Service for monitoring and tracking device health metrics"""

    def __init__(self):
        self.baselineCalculationDays = 7  # Use last 7 days for baseline
        self.sensorDriftThreshold = 2.0  # Standard deviations from baseline

    async def getBaseline(self, deviceId: str) -> Optional[DeviceBaseline]:
        """
        Get device baseline metrics

        Args:
            deviceId: Device identifier

        Returns:
            DeviceBaseline if exists, None otherwise
        """
        from app.core.database import getDbConnection

        try:
            async with getDbConnection() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM "deviceBaselines"
                    WHERE "deviceId" = $1
                """, deviceId)

                if not row:
                    return None

                return DeviceBaseline(
                    baselineId=row['baselineId'],
                    deviceId=row['deviceId'],
                    batteryDrainRatePerHour=row['batteryDrainRatePerHour'],
                    batteryHealthPercentage=row['batteryHealthPercentage'],
                    heartRateMean=row['heartRateMean'],
                    heartRateStdDev=row['heartRateStdDev'],
                    spo2Mean=row['spo2Mean'],
                    spo2StdDev=row['spo2StdDev'],
                    temperatureMean=row['temperatureMean'],
                    temperatureStdDev=row['temperatureStdDev'],
                    systolicBpMean=row['systolicBpMean'],
                    systolicBpStdDev=row['systolicBpStdDev'],
                    diastolicBpMean=row['diastolicBpMean'],
                    diastolicBpStdDev=row['diastolicBpStdDev'],
                    baselineCalculatedAt=row['baselineCalculatedAt'],
                    baselineUpdatedAt=row['baselineUpdatedAt'],
                    sampleCount=row['sampleCount'],
                    calculationPeriodDays=row['calculationPeriodDays']
                )

        except Exception as e:
            logger.error(f"Error retrieving baseline for device {deviceId}: {e}")
            return None

    async def calculateBaseline(self, deviceId: str) -> bool:
        """
        Calculate device baseline from historical vitals data

        Args:
            deviceId: Device identifier

        Returns:
            True if successful, False otherwise
        """
        from app.core.database import getTimescaleConnection

        try:
            # Get vitals data from last N days
            cutoffDate = datetime.now() - timedelta(days=self.baselineCalculationDays)

            async with getTimescaleConnection() as conn:
                rows = await conn.fetch("""
                    SELECT
                        "heartRate",
                        "oxygenSaturation",
                        temperature,
                        "bloodPressureSystolic",
                        "bloodPressureDiastolic"
                    FROM vitals
                    WHERE "deviceId" = $1
                      AND timestamp >= $2
                      AND "heartRate" IS NOT NULL
                      AND "oxygenSaturation" IS NOT NULL
                """, deviceId, cutoffDate)

            if len(rows) < 10:
                logger.warning(f"Insufficient data for baseline calculation: device {deviceId} has {len(rows)} samples")
                return False

            # Extract sensor data
            heartRates = [r['heartRate'] for r in rows if r['heartRate']]
            spo2Values = [r['oxygenSaturation'] for r in rows if r['oxygenSaturation']]
            temperatures = [r['temperature'] for r in rows if r['temperature']]
            systolicBps = [r['bloodPressureSystolic'] for r in rows if r['bloodPressureSystolic']]
            diastolicBps = [r['bloodPressureDiastolic'] for r in rows if r['bloodPressureDiastolic']]

            # Calculate statistics
            def calcStats(values):
                if len(values) < 2:
                    return None, None
                return statistics.mean(values), statistics.stdev(values)

            hrMean, hrStdDev = calcStats(heartRates)
            spo2Mean, spo2StdDev = calcStats(spo2Values)
            tempMean, tempStdDev = calcStats(temperatures)
            sysBpMean, sysBpStdDev = calcStats(systolicBps)
            diaBpMean, diaBpStdDev = calcStats(diastolicBps)

            # Calculate battery drain rate (placeholder - requires battery history)
            batteryDrainRate = await self._calculateBatteryDrainRate(deviceId)

            # Store baseline
            from app.core.database import getDbConnection
            async with getDbConnection() as conn:
                await conn.execute("""
                    INSERT INTO "deviceBaselines" (
                        "deviceId", "batteryDrainRatePerHour",
                        "heartRateMean", "heartRateStdDev",
                        "spo2Mean", "spo2StdDev",
                        "temperatureMean", "temperatureStdDev",
                        "systolicBpMean", "systolicBpStdDev",
                        "diastolicBpMean", "diastolicBpStdDev",
                        "sampleCount", "calculationPeriodDays"
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    ON CONFLICT ("deviceId") DO UPDATE SET
                        "batteryDrainRatePerHour" = EXCLUDED."batteryDrainRatePerHour",
                        "heartRateMean" = EXCLUDED."heartRateMean",
                        "heartRateStdDev" = EXCLUDED."heartRateStdDev",
                        "spo2Mean" = EXCLUDED."spo2Mean",
                        "spo2StdDev" = EXCLUDED."spo2StdDev",
                        "temperatureMean" = EXCLUDED."temperatureMean",
                        "temperatureStdDev" = EXCLUDED."temperatureStdDev",
                        "systolicBpMean" = EXCLUDED."systolicBpMean",
                        "systolicBpStdDev" = EXCLUDED."systolicBpStdDev",
                        "diastolicBpMean" = EXCLUDED."diastolicBpMean",
                        "diastolicBpStdDev" = EXCLUDED."diastolicBpStdDev",
                        "sampleCount" = EXCLUDED."sampleCount",
                        "calculationPeriodDays" = EXCLUDED."calculationPeriodDays",
                        "baselineUpdatedAt" = NOW()
                """, deviceId, batteryDrainRate,
                    hrMean, hrStdDev, spo2Mean, spo2StdDev,
                    tempMean, tempStdDev, sysBpMean, sysBpStdDev,
                    diaBpMean, diaBpStdDev, len(rows), self.baselineCalculationDays)

            logger.info(f"Baseline calculated for device {deviceId}: {len(rows)} samples over {self.baselineCalculationDays} days")
            return True

        except Exception as e:
            logger.error(f"Error calculating baseline for device {deviceId}: {e}")
            return False

    async def _calculateBatteryDrainRate(self, deviceId: str) -> Optional[float]:
        """
        Calculate battery drain rate from historical data

        Args:
            deviceId: Device identifier

        Returns:
            Battery drain rate (% per hour) or None
        """
        # Placeholder implementation - requires battery level tracking over time
        # In real implementation, would query battery levels from vitals/device history
        # and calculate drain rate: (battery_drop_percent / time_hours)

        # For now, return a default estimate
        return 2.5  # Assume 2.5% drain per hour as default

    async def detectSensorDrift(
        self,
        deviceId: str,
        sensorType: str,
        currentReading: float
    ) -> bool:
        """
        Detect if sensor reading shows drift from baseline

        Args:
            deviceId: Device identifier
            sensorType: Type of sensor ('heartRate', 'spo2', 'temperature', 'systolicBp', 'diastolicBp')
            currentReading: Current sensor reading

        Returns:
            True if drift detected, False otherwise
        """
        baseline = await self.getBaseline(deviceId)

        if not baseline:
            # No baseline yet, can't detect drift
            return False

        # Map sensor type to baseline fields
        sensorMap = {
            'heartRate': (baseline.heartRateMean, baseline.heartRateStdDev),
            'spo2': (baseline.spo2Mean, baseline.spo2StdDev),
            'temperature': (baseline.temperatureMean, baseline.temperatureStdDev),
            'systolicBp': (baseline.systolicBpMean, baseline.systolicBpStdDev),
            'diastolicBp': (baseline.diastolicBpMean, baseline.diastolicBpStdDev)
        }

        if sensorType not in sensorMap:
            logger.warning(f"Unknown sensor type: {sensorType}")
            return False

        mean, stdDev = sensorMap[sensorType]

        if mean is None or stdDev is None:
            # Insufficient baseline data for this sensor
            return False

        # Check if reading is outside threshold (e.g., 2 standard deviations)
        deviationsFromMean = abs(currentReading - mean) / stdDev if stdDev > 0 else 0

        isDrift = deviationsFromMean > self.sensorDriftThreshold

        if isDrift:
            logger.warning(
                f"Sensor drift detected: device={deviceId}, sensor={sensorType}, "
                f"reading={currentReading:.1f}, mean={mean:.1f}, stdDev={stdDev:.1f}, "
                f"deviations={deviationsFromMean:.2f}"
            )

        return isDrift

    async def recordDisconnect(self, deviceId: str) -> bool:
        """
        Record a device disconnect event

        Args:
            deviceId: Device identifier

        Returns:
            True if successful, False otherwise
        """
        from app.core.database import getDbConnection

        try:
            async with getDbConnection() as conn:
                await conn.execute("""
                    UPDATE devices
                    SET "totalDisconnects" = COALESCE("totalDisconnects", 0) + 1
                    WHERE id = $1
                """, deviceId)

            logger.debug(f"Disconnect recorded for device {deviceId}")
            return True

        except Exception as e:
            logger.error(f"Error recording disconnect for device {deviceId}: {e}")
            return False

    async def getDisconnectCount(
        self,
        deviceId: str,
        timeWindowHours: int = 24
    ) -> int:
        """
        Get disconnect count for device within time window

        Note: Currently returns total disconnects. In production, would need
        disconnect event logging with timestamps for accurate time-windowed counts.

        Args:
            deviceId: Device identifier
            timeWindowHours: Time window in hours

        Returns:
            Number of disconnects
        """
        from app.core.database import getDbConnection

        try:
            async with getDbConnection() as conn:
                row = await conn.fetchrow("""
                    SELECT "totalDisconnects"
                    FROM devices
                    WHERE id = $1
                """, deviceId)

                return row['totalDisconnects'] if row and row['totalDisconnects'] else 0

        except Exception as e:
            logger.error(f"Error getting disconnect count for device {deviceId}: {e}")
            return 0

    async def updateBatteryHealth(
        self,
        deviceId: str,
        currentBatteryLevel: int
    ) -> bool:
        """
        Update battery health percentage based on usage patterns

        Args:
            deviceId: Device identifier
            currentBatteryLevel: Current battery level (0-100)

        Returns:
            True if successful, False otherwise
        """
        from app.core.database import getDbConnection

        try:
            # Simple battery health model: degrades based on charge cycles
            # In production, would track charge cycles and battery age

            async with getDbConnection() as conn:
                # Get current battery health
                row = await conn.fetchrow("""
                    SELECT "batteryHealthPercentage"
                    FROM devices
                    WHERE id = $1
                """, deviceId)

                currentHealth = row['batteryHealthPercentage'] if row and row['batteryHealthPercentage'] else 100

                # Battery health degrades slowly over time
                # For now, keep it constant unless battery is critically low repeatedly
                newHealth = currentHealth

                if currentBatteryLevel < 5:
                    # Deep discharge damages battery health
                    newHealth = max(currentHealth - 1, 0)

                await conn.execute("""
                    UPDATE devices
                    SET "batteryHealthPercentage" = $1
                    WHERE id = $2
                """, newHealth, deviceId)

            return True

        except Exception as e:
            logger.error(f"Error updating battery health for device {deviceId}: {e}")
            return False

    async def checkDeviceResponsiveness(self, deviceId: str) -> Dict[str, Any]:
        """
        Check if device is responsive to commands

        Args:
            deviceId: Device identifier

        Returns:
            Dictionary with responsiveness status
        """
        from app.core.database import getDbConnection

        try:
            async with getDbConnection() as conn:
                row = await conn.fetchrow("""
                    SELECT
                        "lastCommandSentAt",
                        "lastCommandAckAt"
                    FROM devices
                    WHERE id = $1
                """, deviceId)

                if not row:
                    return {'responsive': None, 'reason': 'Device not found'}

                lastCommandSent = row['lastCommandSentAt']
                lastCommandAck = row['lastCommandAckAt']

                if not lastCommandSent:
                    return {'responsive': None, 'reason': 'No commands sent'}

                if not lastCommandAck:
                    minutesUnresponsive = (datetime.now() - lastCommandSent).total_seconds() / 60
                    return {
                        'responsive': False,
                        'reason': 'No acknowledgment received',
                        'minutesUnresponsive': minutesUnresponsive
                    }

                if lastCommandAck < lastCommandSent:
                    minutesUnresponsive = (datetime.now() - lastCommandSent).total_seconds() / 60
                    return {
                        'responsive': False,
                        'reason': 'Acknowledgment outdated',
                        'minutesUnresponsive': minutesUnresponsive
                    }

                return {'responsive': True, 'reason': 'Device responding normally'}

        except Exception as e:
            logger.error(f"Error checking device responsiveness for {deviceId}: {e}")
            return {'responsive': None, 'reason': f'Error: {str(e)}'}

    async def getDeviceHealthSummary(self, deviceId: str) -> Dict[str, Any]:
        """
        Get comprehensive health summary for a device

        Args:
            deviceId: Device identifier

        Returns:
            Dictionary with health metrics
        """
        baseline = await self.getBaseline(deviceId)
        responsiveness = await self.checkDeviceResponsiveness(deviceId)
        disconnects = await self.getDisconnectCount(deviceId, timeWindowHours=24)

        from app.core.database import getDbConnection
        async with getDbConnection() as conn:
            deviceInfo = await conn.fetchrow("""
                SELECT
                    "firmwareVersion",
                    "lastCalibrationDate",
                    "calibrationDueDate",
                    "batteryHealthPercentage",
                    "totalDisconnects"
                FROM devices
                WHERE id = $1
            """, deviceId)

        return {
            'deviceId': deviceId,
            'hasBaseline': baseline is not None,
            'baselineAge': (datetime.now() - baseline.baselineUpdatedAt).days if baseline else None,
            'batteryHealth': deviceInfo['batteryHealthPercentage'] if deviceInfo else None,
            'calibrationStatus': 'overdue' if deviceInfo and deviceInfo['calibrationDueDate'] and deviceInfo['calibrationDueDate'] < datetime.now() else 'current',
            'disconnects24h': disconnects,
            'responsive': responsiveness.get('responsive'),
            'firmwareVersion': deviceInfo['firmwareVersion'] if deviceInfo else None
        }

# Singleton instance
deviceHealthService = DeviceHealthService()
