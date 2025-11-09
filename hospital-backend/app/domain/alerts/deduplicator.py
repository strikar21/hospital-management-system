"""
AlertDeduplicator - Prevents duplicate alerts within time windows.

Replaces inline deduplication logic scattered across:
- app/services/vital_alert_service.py
- app/services/alert_manager_service.py

Usage:
    from app.domain.alerts import AlertDeduplicator

    deduplicator = AlertDeduplicator(pool=db_pool)
    is_duplicate = await deduplicator.is_duplicate_alert(
        patient_id='P001',
        vital_type='heartrate',
        window_minutes=5
    )
"""

from typing import Optional
from datetime import datetime, timedelta
import logging
import asyncpg

from app.common import to_utc_now, ALERT_DEDUPLICATION_MINUTES

logger = logging.getLogger(__name__)


class AlertDeduplicator:
    """
    Handles alert deduplication logic.

    Prevents creation of duplicate alerts for:
    - Same patient + vital type within time window
    - Same patient + arrhythmia type within time window
    - Same patient + device issue within time window
    """

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize deduplicator.

        Args:
            pool: Database connection pool
        """
        self.pool = pool
        self.default_window_minutes = ALERT_DEDUPLICATION_MINUTES

    async def is_duplicate_alert(
        self,
        patient_id: str,
        vital_type: Optional[str] = None,
        alert_type: str = 'vital',
        window_minutes: Optional[int] = None
    ) -> bool:
        """
        Check if alert is a duplicate within time window.

        Args:
            patient_id: Patient UUID
            vital_type: Vital type (for vital alerts)
            alert_type: Alert type ('vital', 'arrhythmia', 'device')
            window_minutes: Deduplication window in minutes

        Returns:
            True if duplicate exists, False otherwise
        """
        if window_minutes is None:
            window_minutes = self.default_window_minutes

        # Calculate time window
        now = to_utc_now()
        window_start = now - timedelta(minutes=window_minutes)

        try:
            async with self.pool.acquire() as conn:
                # For vital alerts, check patient + vital type + time window
                if alert_type == 'vital' and vital_type:
                    query = """
                        SELECT id
                        FROM patient_alerts
                        WHERE "patientId" = $1
                          AND type = 'vital'
                          AND "vitalType" = $2
                          AND "createdAt" >= $3
                          AND status IN ('active', 'acknowledged')
                        LIMIT 1
                    """

                    result = await conn.fetchval(
                        query,
                        patient_id,
                        vital_type,
                        window_start
                    )

                    if result:
                        logger.debug(
                            f"Duplicate vital alert found for patient {patient_id}, "
                            f"vital {vital_type} within {window_minutes} minutes"
                        )
                        return True

                # For other alert types, check patient + type + time window
                else:
                    query = """
                        SELECT id
                        FROM patient_alerts
                        WHERE "patientId" = $1
                          AND type = $2
                          AND "createdAt" >= $3
                          AND status IN ('active', 'acknowledged')
                        LIMIT 1
                    """

                    result = await conn.fetchval(
                        query,
                        patient_id,
                        alert_type,
                        window_start
                    )

                    if result:
                        logger.debug(
                            f"Duplicate {alert_type} alert found for patient {patient_id} "
                            f"within {window_minutes} minutes"
                        )
                        return True

                return False

        except Exception as e:
            logger.error(f"Error checking for duplicate alerts: {e}")
            # On error, allow alert creation (fail open)
            return False

    async def cleanup_old_alerts(self, days_to_keep: int = 30) -> int:
        """
        Clean up old resolved/acknowledged alerts beyond retention period.

        Args:
            days_to_keep: Number of days to keep alerts

        Returns:
            Number of alerts deleted
        """
        try:
            cutoff_date = to_utc_now() - timedelta(days=days_to_keep)

            async with self.pool.acquire() as conn:
                query = """
                    DELETE FROM patient_alerts
                    WHERE status = 'resolved'
                      AND "resolvedAt" < $1
                """

                result = await conn.execute(query, cutoff_date)

                # Extract count from result (e.g., "DELETE 42" -> 42)
                count = int(result.split()[-1]) if result else 0

                logger.info(f"Cleaned up {count} old resolved alerts")
                return count

        except Exception as e:
            logger.error(f"Error cleaning up old alerts: {e}")
            return 0

    async def get_active_alerts_count(self, patient_id: str) -> int:
        """
        Get count of active/acknowledged alerts for a patient.

        Args:
            patient_id: Patient UUID

        Returns:
            Count of active alerts
        """
        try:
            async with self.pool.acquire() as conn:
                query = """
                    SELECT COUNT(*)
                    FROM patient_alerts
                    WHERE "patientId" = $1
                      AND status IN ('active', 'acknowledged')
                """

                count = await conn.fetchval(query, patient_id)
                return count or 0

        except Exception as e:
            logger.error(f"Error getting active alerts count: {e}")
            return 0
