"""
State Monitor Service - Background monitoring for patient state-based alerts
STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case

This service runs as a background task to monitor patient states and detect:
- noVitalsReceived: When a patient hasn't sent vitals in >10 minutes

Medical-grade continuous monitoring with automatic alert generation.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from app.models.alert import Alert
from app.services.state_manager import stateManager

logger = logging.getLogger(__name__)

class StateMonitor:
    """Background monitor for patient state-based alerts"""

    def __init__(self):
        self.isRunning = False
        self.monitorTask: Optional[asyncio.Task] = None

        # Configuration
        self.checkIntervalSeconds = 60  # Check every 60 seconds
        self.vitalsTimeoutMinutes = 10  # Alert if no vitals for >10 minutes

    async def start(self):
        """Start the background monitoring task"""
        if self.isRunning:
            logger.warning("State monitor is already running")
            return

        self.isRunning = True
        self.monitorTask = asyncio.create_task(self._monitorLoop())
        logger.info("State monitor started - checking every %d seconds", self.checkIntervalSeconds)

    async def stop(self):
        """Stop the background monitoring task"""
        if not self.isRunning:
            return

        self.isRunning = False

        if self.monitorTask:
            self.monitorTask.cancel()
            try:
                await self.monitorTask
            except asyncio.CancelledError:
                pass

        logger.info("State monitor stopped")

    async def _monitorLoop(self):
        """Main monitoring loop - runs continuously"""
        while self.isRunning:
            try:
                await self._checkPatientStates()
            except Exception as e:
                logger.error(f"Error in state monitor loop: {e}", exc_info=True)

            # Wait before next check
            await asyncio.sleep(self.checkIntervalSeconds)

    async def _checkPatientStates(self):
        """Check all patient states and generate alerts for issues"""
        from app.core.database import getDbConnection

        try:
            async with getDbConnection() as conn:
                # Find patients with no vitals for >10 minutes who haven't been alerted yet
                cutoffTime = datetime.now() - timedelta(minutes=self.vitalsTimeoutMinutes)

                query = """
                    SELECT
                        ps.patientId,
                        ps.lastVitalsTimestamp,
                        ps.noVitalsAlertSent,
                        p.firstName,
                        p.lastName,
                        da.deviceId
                    FROM patientStates ps
                    INNER JOIN patients p ON ps.patientId = p.id
                    LEFT JOIN deviceAssignments da ON ps.patientId = da.patientId
                    WHERE ps.lastVitalsTimestamp < $1
                      AND ps.noVitalsAlertSent = FALSE
                      AND da.unassignedAt IS NULL
                """

                rows = await conn.fetch(query, cutoffTime)

                if rows:
                    logger.info(f"Found {len(rows)} patients with vitals timeout")

                    for row in rows:
                        await self._generateNoVitalsAlert(row)

        except Exception as e:
            logger.error(f"Error checking patient states: {e}", exc_info=True)

    async def _generateNoVitalsAlert(self, patientData):
        """Generate and broadcast a noVitalsReceived alert"""
        from app.services.websocket_manager import connectionManager

        try:
            patientId = patientData['patientid']
            lastVitalsTime = patientData['lastvitalstimestamp']
            deviceId = patientData['deviceid'] or 'unknown'
            firstName = patientData['firstname']
            lastName = patientData['lastname']

            # Calculate time since last vitals
            timeSinceVitals = datetime.now() - lastVitalsTime
            minutesSinceVitals = timeSinceVitals.total_seconds() / 60

            # Create alert
            alert = Alert(
                alertType='noVitalsReceived',
                severity='high',
                message=f'NO VITALS RECEIVED - Patient {firstName} {lastName} - No data for {minutesSinceVitals:.0f} minutes',
                source='Backend',
                confidence=0.95,
                patientId=patientId,
                deviceId=deviceId,
                timestamp=datetime.now(),
                context={
                    'minutesSinceLastVitals': minutesSinceVitals,
                    'lastVitalsTimestamp': lastVitalsTime.isoformat(),
                    'patientName': f'{firstName} {lastName}'
                },
                category='network'
            )

            # Broadcast alert to connected clients
            await connectionManager.sendAlert(alert)

            # Mark alert as sent in database
            await stateManager.updatePatientState(patientId, {
                'noVitalsAlertSent': True
            })

            logger.info(
                f"Generated noVitalsReceived alert for patient {patientId} "
                f"({minutesSinceVitals:.0f} minutes since last vitals)"
            )

        except Exception as e:
            logger.error(f"Error generating noVitalsReceived alert: {e}", exc_info=True)

# Singleton instance
stateMonitor = StateMonitor()
