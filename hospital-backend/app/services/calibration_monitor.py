"""
Calibration Monitor - Background service for device calibration tracking
STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case

Monitors device calibration schedules and triggers alerts for:
- Calibration due soon
- Calibration overdue
- Sensor drift detection
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from app.services.calibration_service import calibrationService
from app.services.device_health_service import deviceHealthService

logger = logging.getLogger(__name__)

class CalibrationMonitor:
    """Background monitor for device calibration and sensor drift"""

    def __init__(self):
        self.calibrationWarningDays = 7  # Alert 7 days before due
        self.checkIntervalSeconds = 3600  # Check every hour
        self.isRunning = False

    async def checkCalibrationStatus(self) -> List[Dict[str, Any]]:
        """
        Check all devices for calibration requirements

        Returns:
            List of calibration alerts to be raised
        """
        alerts = []

        try:
            # Get devices needing calibration (within warning threshold)
            devicesDueSoon = await calibrationService.getDevicesNeedingCalibration(
                daysThreshold=self.calibrationWarningDays
            )

            for device in devicesDueSoon:
                deviceId = device.get('deviceId')
                calibrationDueDate = device.get('calibrationDueDate')
                daysUntilDue = device.get('daysUntilDue')

                if not deviceId or not calibrationDueDate:
                    continue

                # Check if overdue
                if daysUntilDue < 0:
                    alerts.append({
                        'alertType': 'calibrationOverdue',
                        'severity': 'high',
                        'deviceId': deviceId,
                        'daysOverdue': abs(daysUntilDue),
                        'calibrationDueDate': calibrationDueDate,
                        'message': f'CALIBRATION OVERDUE - Device {deviceId} calibration {abs(daysUntilDue)} days overdue'
                    })
                elif daysUntilDue <= self.calibrationWarningDays:
                    alerts.append({
                        'alertType': 'calibrationRequired',
                        'severity': 'medium',
                        'deviceId': deviceId,
                        'daysUntilDue': daysUntilDue,
                        'calibrationDueDate': calibrationDueDate,
                        'message': f'CALIBRATION DUE - Device {deviceId} calibration due in {daysUntilDue} days'
                    })

            logger.info(f"Calibration check complete: {len(alerts)} calibration alerts generated")

        except Exception as e:
            logger.error(f"Error checking calibration status: {e}")

        return alerts

    async def checkSensorDrift(self, deviceId: str, vitalsData: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for sensor drift on incoming vitals data

        Args:
            deviceId: Device identifier
            vitalsData: Current vitals readings

        Returns:
            List of sensor drift alerts
        """
        alerts = []

        try:
            # Check each sensor type for drift
            sensorChecks = [
                ('heartRate', vitalsData.get('heartRate')),
                ('spo2', vitalsData.get('oxygenSaturation')),
                ('temperature', vitalsData.get('temperature')),
                ('systolicBp', vitalsData.get('bloodPressureSystolic')),
                ('diastolicBp', vitalsData.get('bloodPressureDiastolic'))
            ]

            for sensorType, reading in sensorChecks:
                if reading is None:
                    continue

                isDrift = await deviceHealthService.detectSensorDrift(
                    deviceId=deviceId,
                    sensorType=sensorType,
                    currentReading=reading
                )

                if isDrift:
                    alerts.append({
                        'alertType': 'sensorDrift',
                        'severity': 'medium',
                        'deviceId': deviceId,
                        'sensorType': sensorType,
                        'reading': reading,
                        'message': f'SENSOR DRIFT - Device {deviceId} {sensorType} sensor reading abnormal - CALIBRATION REQUIRED'
                    })

        except Exception as e:
            logger.error(f"Error checking sensor drift for device {deviceId}: {e}")

        return alerts

    async def monitorLoop(self):
        """Background monitoring loop for calibration checks"""
        self.isRunning = True
        logger.info("🔧 Calibration monitoring started")

        while self.isRunning:
            try:
                # Check calibration status periodically
                await self.checkCalibrationStatus()

                # Sleep until next check
                await asyncio.sleep(self.checkIntervalSeconds)

            except asyncio.CancelledError:
                logger.info("🔧 Calibration monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Error in calibration monitor loop: {e}")
                await asyncio.sleep(60)  # Sleep 1 minute on error

        self.isRunning = False
        logger.info("🔧 Calibration monitoring stopped")

    def stop(self):
        """Stop the monitoring loop"""
        self.isRunning = False

# Singleton instance
calibrationMonitor = CalibrationMonitor()
