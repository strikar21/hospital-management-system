"""
System Alert Scheduler
Periodic task to run system-level alert detection (Component 2)

Refactored to use AlertPipeline from domain layer instead of deprecated alert_detection_service.
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Global flag to control scheduler lifecycle
_scheduler_running = False
_alert_pipeline: Optional['AlertPipeline'] = None  # type: ignore


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
    global _scheduler_running, _alert_pipeline

    if _scheduler_running:
        logger.warning("System alert scheduler already running")
        return

    _scheduler_running = True
    logger.info("🚀 System alert scheduler starting - will check every 5 minutes")

    # Import here to avoid circular dependencies
    from app.domain.alerts import AlertPipeline
    from app.services.websocket_manager import connectionManager
    from app.core.database import getConnectionPool

    # Initialize AlertPipeline
    try:
        db_pool = await getConnectionPool()
        _alert_pipeline = AlertPipeline(pool=db_pool)
        logger.info("✅ AlertPipeline initialized for system alerts")
    except Exception as e:
        logger.error(f"❌ Failed to initialize AlertPipeline: {e}")
        _scheduler_running = False
        return

    # Initial delay before first check (30 seconds after startup)
    await asyncio.sleep(30)

    while _scheduler_running:
        try:
            logger.info("🔍 Running system-level alert detection...")

            # Run system-level alert detection using AlertPipeline
            alert_records = await _alert_pipeline.detect_system_level_alerts()

            if alert_records:
                logger.warning(f"🚨 Detected {len(alert_records)} system-level alerts")

                # Process and broadcast each alert
                for alert_record in alert_records:
                    # Insert alert into database
                    alert_id = await _alert_pipeline.process_alert(alert_record)

                    # Create payload for WebSocket broadcast
                    alert_payload = {
                        'id': alert_id,
                        'type': alert_record['type'],
                        'severity': alert_record['severity'],
                        'message': alert_record['message'],
                        'status': alert_record['status'],
                        'timestamp': alert_record['createdAt'].isoformat(),
                        'patientId': alert_record['patientId'],
                        'source': alert_record.get('createdBy', 'system')
                    }

                    # Send to system-wide channel (all staff)
                    await connectionManager.broadcastSystemAlert(alert_payload)

                    logger.warning(
                        f"   → [{alert_record['severity'].upper()}] {alert_record['type']}: {alert_record['message']}"
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
