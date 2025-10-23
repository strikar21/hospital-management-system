"""
Patient State Manager
Manages persistent state for duration-based alert tracking (Component 4)
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import json

logger = logging.getLogger(__name__)


@dataclass
class PatientState:
    """Patient state for duration-based alert tracking"""
    patientId: str

    # Tachycardia state
    tachycardiaStartTime: Optional[datetime] = None
    tachycardiaAlertSent: bool = False

    # Bradycardia state
    bradycardiaStartTime: Optional[datetime] = None
    bradycardiaAlertSent: bool = False

    # Hypotension state
    hypotensionStartTime: Optional[datetime] = None
    hypotensionAlertSent: bool = False

    # Hypoxia state
    hypoxiaStartTime: Optional[datetime] = None
    hypoxiaAlertSent: bool = False

    # Fever state
    feverStartTime: Optional[datetime] = None
    feverAlertSent: bool = False

    # Hypothermia state
    hypothermiaStartTime: Optional[datetime] = None
    hypothermiaAlertSent: bool = False

    # Last vitals tracking
    lastVitalsTimestamp: Optional[datetime] = None
    noVitalsAlertSent: bool = False

    # Connection drops
    connectionDrops: List[datetime] = field(default_factory=list)

    # Timestamps
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class StateManager:
    """Manages persistent patient state for duration-based alerts"""

    async def getPatientState(self, patientId: str) -> Optional[PatientState]:
        """
        Retrieve patient state from database
        Returns None if patient state doesn't exist
        """
        from app.core.database import getDbConnection

        try:
            async with getDbConnection() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM patientStates
                    WHERE patientId = $1
                """, patientId)

                if not row:
                    return None

                # Parse connection drops JSON
                connectionDrops = []
                if row['connectiondrops']:
                    dropsData = json.loads(row['connectiondrops']) if isinstance(row['connectiondrops'], str) else row['connectiondrops']
                    connectionDrops = [datetime.fromisoformat(ts) for ts in dropsData]

                # Create PatientState object
                return PatientState(
                    patientId=row['patientid'],
                    tachycardiaStartTime=row['tachycardiastarttime'],
                    tachycardiaAlertSent=row['tachycardiaalertsent'],
                    bradycardiaStartTime=row['bradycardiastarttime'],
                    bradycardiaAlertSent=row['bradycardiaalertsent'],
                    hypotensionStartTime=row['hypotensionstarttime'],
                    hypotensionAlertSent=row['hypotensionalertsent'],
                    hypoxiaStartTime=row['hypoxiastarttime'],
                    hypoxiaAlertSent=row['hypoxiaalertsent'],
                    feverStartTime=row['feverstarttime'],
                    feverAlertSent=row['feveralertsent'],
                    hypothermiaStartTime=row['hypothermiastarttime'],
                    hypothermiaAlertSent=row['hypothermiaalertsent'],
                    lastVitalsTimestamp=row['lastvitalstimestamp'],
                    noVitalsAlertSent=row['novitalsalertsent'],
                    connectionDrops=connectionDrops,
                    createdAt=row['createdat'],
                    updatedAt=row['updatedat']
                )

        except Exception as e:
            logger.error(f"Error retrieving patient state for {patientId}: {e}")
            return None

    async def initializePatientState(self, patientId: str) -> bool:
        """
        Initialize state tracking for a new patient
        Returns True if successful, False if already exists
        """
        from app.core.database import getDbConnection

        try:
            async with getDbConnection() as conn:
                await conn.execute("""
                    INSERT INTO patientStates (patientId, lastVitalsTimestamp)
                    VALUES ($1, NOW())
                    ON CONFLICT (patientId) DO NOTHING
                """, patientId)

                logger.info(f"Initialized state tracking for patient {patientId}")
                return True

        except Exception as e:
            logger.error(f"Error initializing patient state for {patientId}: {e}")
            return False

    async def updatePatientState(self, patientId: str, stateUpdates: Dict[str, Any]) -> bool:
        """
        Update specific state fields for a patient

        Args:
            patientId: Patient ID
            stateUpdates: Dictionary of field names and values to update

        Example:
            await stateManager.updatePatientState(
                'PAT001',
                {
                    'tachycardiaStartTime': datetime.now(),
                    'tachycardiaAlertSent': False
                }
            )
        """
        from app.core.database import getDbConnection

        if not stateUpdates:
            return False

        try:
            # Build SET clause dynamically
            setClauses = []
            values = [patientId]
            paramIndex = 2

            for key, value in stateUpdates.items():
                # Convert camelCase to snake_case for database
                dbKey = ''.join(['_' + c.lower() if c.isupper() else c for c in key]).lstrip('_')
                setClauses.append(f'"{dbKey}" = ${paramIndex}')
                values.append(value)
                paramIndex += 1

            setClause = ', '.join(setClauses)

            query = f"""
                UPDATE patientStates
                SET {setClause}
                WHERE patientId = $1
            """

            async with getDbConnection() as conn:
                await conn.execute(query, *values)

            logger.debug(f"Updated patient state for {patientId}: {list(stateUpdates.keys())}")
            return True

        except Exception as e:
            logger.error(f"Error updating patient state for {patientId}: {e}")
            return False

    async def resetConditionState(self, patientId: str, condition: str) -> bool:
        """
        Reset specific condition tracking (called when condition resolves)

        Args:
            patientId: Patient ID
            condition: One of: 'tachycardia', 'bradycardia', 'hypotension',
                      'hypoxia', 'fever', 'hypothermia', 'noVitals'
        """
        conditionFields = {
            'tachycardia': {'tachycardiaStartTime': None, 'tachycardiaAlertSent': False},
            'bradycardia': {'bradycardiaStartTime': None, 'bradycardiaAlertSent': False},
            'hypotension': {'hypotensionStartTime': None, 'hypotensionAlertSent': False},
            'hypoxia': {'hypoxiaStartTime': None, 'hypoxiaAlertSent': False},
            'fever': {'feverStartTime': None, 'feverAlertSent': False},
            'hypothermia': {'hypothermiaStartTime': None, 'hypothermiaAlertSent': False},
            'noVitals': {'noVitalsAlertSent': False}
        }

        if condition not in conditionFields:
            logger.warning(f"Unknown condition type: {condition}")
            return False

        return await self.updatePatientState(patientId, conditionFields[condition])

    async def recordConnectionDrop(self, patientId: str) -> bool:
        """
        Record a connection drop event
        Maintains list of connection drop timestamps for tracking frequency
        """
        from app.core.database import getDbConnection

        try:
            async with getDbConnection() as conn:
                # Add new timestamp to connectionDrops JSONB array
                await conn.execute("""
                    UPDATE patientStates
                    SET connectionDrops = connectionDrops || $2::jsonb
                    WHERE patientId = $1
                """, patientId, json.dumps([datetime.now().isoformat()]))

                logger.info(f"Recorded connection drop for patient {patientId}")
                return True

        except Exception as e:
            logger.error(f"Error recording connection drop for {patientId}: {e}")
            return False

    async def getConnectionDropCount(self, patientId: str, windowMinutes: int = 60) -> int:
        """
        Count connection drops within specified time window

        Args:
            patientId: Patient ID
            windowMinutes: Time window in minutes (default 60)

        Returns:
            Number of connection drops in the time window
        """
        state = await self.getPatientState(patientId)

        if not state or not state.connectionDrops:
            return 0

        # Filter drops within time window
        cutoffTime = datetime.now()
        cutoffTime = cutoffTime.replace(second=cutoffTime.second - (windowMinutes * 60))

        recentDrops = [
            drop for drop in state.connectionDrops
            if drop > cutoffTime
        ]

        return len(recentDrops)

    async def cleanOldConnectionDrops(self, patientId: str, keepHours: int = 24) -> bool:
        """
        Remove connection drop records older than specified hours
        This prevents the connectionDrops array from growing indefinitely

        Args:
            patientId: Patient ID
            keepHours: How many hours of history to keep (default 24)
        """
        from app.core.database import getDbConnection

        try:
            state = await self.getPatientState(patientId)

            if not state or not state.connectionDrops:
                return True

            # Filter to keep only recent drops
            cutoffTime = datetime.now()
            cutoffTime = cutoffTime.replace(hour=cutoffTime.hour - keepHours)

            recentDrops = [
                drop.isoformat() for drop in state.connectionDrops
                if drop > cutoffTime
            ]

            # Update database with filtered list
            async with getDbConnection() as conn:
                await conn.execute("""
                    UPDATE patientStates
                    SET connectionDrops = $2::jsonb
                    WHERE patientId = $1
                """, patientId, json.dumps(recentDrops))

            logger.debug(f"Cleaned old connection drops for {patientId}: kept {len(recentDrops)} recent events")
            return True

        except Exception as e:
            logger.error(f"Error cleaning connection drops for {patientId}: {e}")
            return False


# Singleton instance
stateManager = StateManager()
