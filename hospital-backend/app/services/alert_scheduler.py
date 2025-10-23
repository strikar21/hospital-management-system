"""
System Alert Scheduler
Periodic task to run system-level alert detection (Component 2)
"""

import asyncio
import logging
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)

# Global flag to control scheduler lifecycle
_scheduler_running = False


async def start_system_alert_scheduler():
    """
    Start the system alert scheduler that runs periodic checks every 5 minutes
    for system-level alerts (Component 2):
    - noDevicesAvailable
    - lowDeviceAvailability
    - multiplePatientsWithFever
    - spo2DeclineOutbreak
    - newAdmissionSurge
    """
    global _scheduler_running

    if _scheduler_running:
        logger.warning("System alert scheduler already running")
        return

    _scheduler_running = True
    logger.info("🚀 System alert scheduler starting - will check every 5 minutes")

    # Import here to avoid circular dependencies
    from app.services.alert_detection_service import completeAlertDetectionService
    from app.services.websocket_manager import connectionManager

    # Initial delay before first check (30 seconds after startup)
    await asyncio.sleep(30)

    while _scheduler_running:
        try:
            logger.info("🔍 Running system-level alert detection...")

            # Run system-level alert detection
            alerts = await completeAlertDetectionService.detectSystemLevelAlerts()

            if alerts:
                logger.warning(f"🚨 Detected {len(alerts)} system-level alerts")

                # Broadcast each alert via WebSocket to all connected clients
                for alert in alerts:
                    alertPayload = completeAlertDetectionService.createAlertPayload(alert)

                    # Send to system-wide channel (all staff)
                    await connectionManager.broadcastSystemAlert(alertPayload)

                    logger.warning(
                        f"   → [{alert.severity.upper()}] {alert.alertType}: {alert.message}"
                    )
            else:
                logger.debug("✅ No system-level alerts detected")

        except Exception as e:
            logger.error(f"❌ Error in system alert scheduler: {e}", exc_info=True)

        # Wait 5 minutes before next check (300 seconds)
        await asyncio.sleep(300)

    logger.info("🛑 System alert scheduler stopped")


async def stop_system_alert_scheduler():
    """Stop the system alert scheduler"""
    global _scheduler_running
    _scheduler_running = False
    logger.info("Stopping system alert scheduler...")
