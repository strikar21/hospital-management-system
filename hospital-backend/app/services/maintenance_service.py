"""
Maintenance Service - Device maintenance event tracking and scheduling
STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case

Manages device maintenance history, schedules preventive maintenance,
and tracks maintenance due dates for medical device compliance.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MaintenanceRecord:
    """Maintenance record data class"""
    maintenanceId: int
    deviceId: str
    maintenanceType: str
    performedAt: datetime
    performedBy: Optional[str]
    notes: Optional[str]
    nextMaintenanceDue: Optional[datetime]
    cost: Optional[float]
    createdAt: datetime

class MaintenanceService:
    """Service for managing device maintenance tracking"""

    def __init__(self):
        # Maintenance schedule defaults (days)
        self.maintenanceSchedules = {
            'calibration': 30,
            'inspection': 90,
            'cleaning': 30,
            'battery_replacement': 365,
            'firmware_update': 180,
            'repair': None  # As needed
        }

    async def recordMaintenance(
        self,
        deviceId: str,
        maintenanceType: str,
        performedBy: str,
        notes: Optional[str] = None,
        cost: Optional[float] = None
    ) -> bool:
        """
        Record a maintenance event for a device

        Args:
            deviceId: Device identifier
            maintenanceType: Type of maintenance performed
            performedBy: Staff ID who performed maintenance
            notes: Additional notes
            cost: Cost of maintenance (optional)

        Returns:
            True if successful, False otherwise
        """
        from app.core.database import getDbConnection

        try:
            performedAt = datetime.now()

            # Calculate next maintenance due date based on type
            nextDue = None
            if maintenanceType in self.maintenanceSchedules:
                days = self.maintenanceSchedules[maintenanceType]
                if days:
                    nextDue = performedAt + timedelta(days=days)

            async with getDbConnection() as conn:
                await conn.execute("""
                    INSERT INTO "deviceMaintenanceHistory" (
                        "deviceId", "maintenanceType", "performedAt",
                        "performedBy", notes, "nextMaintenanceDue", cost
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, deviceId, maintenanceType, performedAt, performedBy, notes, nextDue, cost)

                logger.info(
                    f"Maintenance recorded: device={deviceId}, type={maintenanceType}, "
                    f"by={performedBy}, nextDue={nextDue.date() if nextDue else 'N/A'}"
                )

            return True

        except Exception as e:
            logger.error(f"Error recording maintenance for device {deviceId}: {e}")
            return False

    async def getMaintenanceHistory(
        self,
        deviceId: str,
        limit: int = 10
    ) -> List[MaintenanceRecord]:
        """
        Get maintenance history for a device

        Args:
            deviceId: Device identifier
            limit: Maximum number of records to return

        Returns:
            List of MaintenanceRecord objects
        """
        from app.core.database import getDbConnection

        try:
            async with getDbConnection() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM "deviceMaintenanceHistory"
                    WHERE "deviceId" = $1
                    ORDER BY "performedAt" DESC
                    LIMIT $2
                """, deviceId, limit)

                return [
                    MaintenanceRecord(
                        maintenanceId=row['maintenanceId'],
                        deviceId=row['deviceId'],
                        maintenanceType=row['maintenanceType'],
                        performedAt=row['performedAt'],
                        performedBy=row['performedBy'],
                        notes=row['notes'],
                        nextMaintenanceDue=row['nextMaintenanceDue'],
                        cost=float(row['cost']) if row['cost'] else None,
                        createdAt=row['createdAt']
                    )
                    for row in rows
                ]

        except Exception as e:
            logger.error(f"Error retrieving maintenance history for device {deviceId}: {e}")
            return []

    async def getDevicesDueMaintenance(
        self,
        maintenanceType: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of devices due for maintenance

        Args:
            maintenanceType: Filter by maintenance type (optional)

        Returns:
            List of device dictionaries with maintenance info
        """
        from app.core.database import getDbConnection

        try:
            async with getDbConnection() as conn:
                if maintenanceType:
                    query = """
                        SELECT DISTINCT ON (d.id)
                            d.id as "deviceId",
                            d.name,
                            d.type,
                            d.location,
                            mh."maintenanceType",
                            mh."nextMaintenanceDue",
                            EXTRACT(DAY FROM (NOW() - mh."nextMaintenanceDue")) as "daysOverdue"
                        FROM devices d
                        INNER JOIN "deviceMaintenanceHistory" mh ON d.id = mh."deviceId"
                        WHERE mh."nextMaintenanceDue" < NOW()
                          AND mh."maintenanceType" = $1
                        ORDER BY d.id, mh."nextMaintenanceDue" ASC
                    """
                    rows = await conn.fetch(query, maintenanceType)
                else:
                    query = """
                        SELECT DISTINCT ON (d.id)
                            d.id as "deviceId",
                            d.name,
                            d.type,
                            d.location,
                            mh."maintenanceType",
                            mh."nextMaintenanceDue",
                            EXTRACT(DAY FROM (NOW() - mh."nextMaintenanceDue")) as "daysOverdue"
                        FROM devices d
                        INNER JOIN "deviceMaintenanceHistory" mh ON d.id = mh."deviceId"
                        WHERE mh."nextMaintenanceDue" < NOW()
                        ORDER BY d.id, mh."nextMaintenanceDue" ASC
                    """
                    rows = await conn.fetch(query)

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error retrieving devices due maintenance: {e}")
            return []

    async def scheduleNextMaintenance(
        self,
        deviceId: str,
        maintenanceType: str,
        daysUntilDue: int
    ) -> bool:
        """
        Schedule next maintenance for a device

        Args:
            deviceId: Device identifier
            maintenanceType: Type of maintenance to schedule
            daysUntilDue: Days until maintenance is due

        Returns:
            True if successful, False otherwise
        """
        from app.core.database import getDbConnection

        try:
            nextDue = datetime.now() + timedelta(days=daysUntilDue)

            async with getDbConnection() as conn:
                # Update the most recent maintenance record of this type
                await conn.execute("""
                    UPDATE "deviceMaintenanceHistory"
                    SET "nextMaintenanceDue" = $1
                    WHERE "deviceId" = $2
                      AND "maintenanceType" = $3
                      AND "performedAt" = (
                          SELECT MAX("performedAt")
                          FROM "deviceMaintenanceHistory"
                          WHERE "deviceId" = $2 AND "maintenanceType" = $3
                      )
                """, nextDue, deviceId, maintenanceType)

            logger.info(f"Scheduled {maintenanceType} for device {deviceId}: due {nextDue.date()}")
            return True

        except Exception as e:
            logger.error(f"Error scheduling maintenance for device {deviceId}: {e}")
            return False

    async def getLastMaintenance(
        self,
        deviceId: str,
        maintenanceType: Optional[str] = None
    ) -> Optional[MaintenanceRecord]:
        """
        Get the most recent maintenance record for a device

        Args:
            deviceId: Device identifier
            maintenanceType: Filter by maintenance type (optional)

        Returns:
            MaintenanceRecord if found, None otherwise
        """
        from app.core.database import getDbConnection

        try:
            async with getDbConnection() as conn:
                if maintenanceType:
                    row = await conn.fetchrow("""
                        SELECT * FROM "deviceMaintenanceHistory"
                        WHERE "deviceId" = $1 AND "maintenanceType" = $2
                        ORDER BY "performedAt" DESC
                        LIMIT 1
                    """, deviceId, maintenanceType)
                else:
                    row = await conn.fetchrow("""
                        SELECT * FROM "deviceMaintenanceHistory"
                        WHERE "deviceId" = $1
                        ORDER BY "performedAt" DESC
                        LIMIT 1
                    """, deviceId)

                if not row:
                    return None

                return MaintenanceRecord(
                    maintenanceId=row['maintenanceId'],
                    deviceId=row['deviceId'],
                    maintenanceType=row['maintenanceType'],
                    performedAt=row['performedAt'],
                    performedBy=row['performedBy'],
                    notes=row['notes'],
                    nextMaintenanceDue=row['nextMaintenanceDue'],
                    cost=float(row['cost']) if row['cost'] else None,
                    createdAt=row['createdAt']
                )

        except Exception as e:
            logger.error(f"Error retrieving last maintenance for device {deviceId}: {e}")
            return None

    async def getMaintenanceCosts(
        self,
        deviceId: Optional[str] = None,
        startDate: Optional[datetime] = None,
        endDate: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get maintenance cost summary

        Args:
            deviceId: Filter by device (optional)
            startDate: Start date for period (optional)
            endDate: End date for period (optional)

        Returns:
            Dictionary with cost summary
        """
        from app.core.database import getDbConnection

        try:
            async with getDbConnection() as conn:
                query = """
                    SELECT
                        COUNT(*) as "totalEvents",
                        SUM(cost) as "totalCost",
                        AVG(cost) as "averageCost",
                        MIN(cost) as "minCost",
                        MAX(cost) as "maxCost"
                    FROM "deviceMaintenanceHistory"
                    WHERE cost IS NOT NULL
                """

                params = []
                if deviceId:
                    query += " AND \"deviceId\" = $1"
                    params.append(deviceId)

                if startDate:
                    query += f" AND \"performedAt\" >= ${len(params) + 1}"
                    params.append(startDate)

                if endDate:
                    query += f" AND \"performedAt\" <= ${len(params) + 1}"
                    params.append(endDate)

                row = await conn.fetchrow(query, *params)

                return {
                    'totalEvents': row['totalEvents'] if row else 0,
                    'totalCost': float(row['totalCost']) if row and row['totalCost'] else 0.0,
                    'averageCost': float(row['averageCost']) if row and row['averageCost'] else 0.0,
                    'minCost': float(row['minCost']) if row and row['minCost'] else 0.0,
                    'maxCost': float(row['maxCost']) if row and row['maxCost'] else 0.0
                }

        except Exception as e:
            logger.error(f"Error calculating maintenance costs: {e}")
            return {}

    async def getMaintenanceStats(self) -> Dict[str, Any]:
        """
        Get overall maintenance statistics

        Returns:
            Dictionary with maintenance statistics
        """
        from app.core.database import getDbConnection

        try:
            async with getDbConnection() as conn:
                now = datetime.now()

                stats = await conn.fetchrow("""
                    SELECT
                        COUNT(DISTINCT "deviceId") as "devicesWithMaintenance",
                        COUNT(*) as "totalMaintenanceEvents",
                        COUNT(CASE WHEN "nextMaintenanceDue" < $1 THEN 1 END) as "overdueMaintenance",
                        COUNT(CASE WHEN "nextMaintenanceDue" BETWEEN $1 AND $2 THEN 1 END) as "dueSoon"
                    FROM "deviceMaintenanceHistory"
                """, now, now + timedelta(days=7))

                typeStats = await conn.fetch("""
                    SELECT
                        "maintenanceType",
                        COUNT(*) as count
                    FROM "deviceMaintenanceHistory"
                    GROUP BY "maintenanceType"
                    ORDER BY count DESC
                """)

                return {
                    'devicesWithMaintenance': stats['devicesWithMaintenance'] if stats else 0,
                    'totalEvents': stats['totalMaintenanceEvents'] if stats else 0,
                    'overdue': stats['overdueMaintenance'] if stats else 0,
                    'dueSoon': stats['dueSoon'] if stats else 0,
                    'byType': [dict(row) for row in typeStats] if typeStats else []
                }

        except Exception as e:
            logger.error(f"Error retrieving maintenance stats: {e}")
            return {}

# Singleton instance
maintenanceService = MaintenanceService()
