"""
Door Scanner Service - Modular Location Tracking Service
Handles BLE detection processing and device location tracking

Architecture: Matches watch service pattern - modular, testable, single responsibility
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DoorScannerService:
    """
    Service for door scanner location tracking

    Responsibilities:
    - Process BLE scan data from door scanners
    - Update real-time device locations
    - Track room entry/exit events
    - Handle stale device cleanup
    """

    @staticmethod
    async def process_scan_data(
        conn,
        scanner_id: str,
        room_id: str,
        detected_devices: List[Dict[str, Any]],
        scan_timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Process BLE scan data from door scanner

        Args:
            conn: Database connection
            scanner_id: Door scanner device ID (e.g., door-00001)
            room_id: Room where scanner is installed (e.g., ICU-101)
            detected_devices: List of detected BLE devices
            scan_timestamp: When scan occurred (default: now)

        Returns:
            Dict with processing stats:
            {
                "devicesProcessed": 5,
                "newEntries": 2,
                "roomChanges": 1,
                "updates": 2
            }

        Workflow:
            1. Record all detections in scannerReadings
            2. Update deviceLocations (real-time)
            3. Handle room entry/exit events
            4. Update roomPresenceHistory
        """

        if scan_timestamp is None:
            scan_timestamp = datetime.utcnow()

        stats = {
            "devicesProcessed": 0,
            "newEntries": 0,
            "roomChanges": 0,
            "updates": 0
        }

        for device in detected_devices:
            device_id = device.get('deviceId')
            if not device_id:
                logger.warning(f"⚠️ Skipping device without deviceId: {device}")
                continue

            rssi = device.get('rssi')
            device_address = device.get('address') or device.get('deviceAddress')
            device_name = device.get('name') or device.get('deviceName')
            device_type = device.get('type') or device.get('deviceType')

            try:
                # 1. Record scan in history
                await conn.execute(
                    '''INSERT INTO "scannerReadings"
                       ("scannerId", "roomId", "deviceId", "deviceAddress",
                        "deviceName", "deviceType", rssi, "scanTimestamp")
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8)''',
                    scanner_id, room_id, device_id,
                    device_address, device_name, device_type,
                    rssi, scan_timestamp
                )

                # 2. Get current location
                current_location = await conn.fetchrow(
                    '''SELECT "currentRoom", "lastSeen"
                       FROM "deviceLocations"
                       WHERE "deviceId" = $1''',
                    device_id
                )

                if not current_location:
                    # First time seeing this device - create entry
                    await DoorScannerService._handle_first_detection(
                        conn, device_id, room_id, scanner_id, rssi, scan_timestamp
                    )
                    stats["newEntries"] += 1
                    logger.info(f"📍 Device {device_id} first detected in {room_id}")

                elif current_location['currentRoom'] != room_id:
                    # Device changed rooms - room transition
                    await DoorScannerService._handle_room_change(
                        conn, device_id, room_id, scanner_id, rssi,
                        current_location['currentRoom'], scan_timestamp
                    )
                    stats["roomChanges"] += 1
                    logger.info(
                        f"📍 Device {device_id} moved: "
                        f"{current_location['currentRoom']} → {room_id}"
                    )

                else:
                    # Same room - just update last seen
                    await conn.execute(
                        '''UPDATE "deviceLocations"
                           SET "lastSeen" = $1, rssi = $2, "updatedAt" = NOW()
                           WHERE "deviceId" = $3''',
                        scan_timestamp, rssi, device_id
                    )
                    stats["updates"] += 1

                stats["devicesProcessed"] += 1

            except Exception as e:
                logger.error(f"❌ Error processing device {device_id}: {e}")
                continue

        return stats

    @staticmethod
    async def _handle_first_detection(
        conn,
        device_id: str,
        room_id: str,
        scanner_id: str,
        rssi: int,
        scan_timestamp: datetime
    ):
        """Handle first-time detection of a device"""

        # Create location record
        await conn.execute(
            '''INSERT INTO "deviceLocations"
               ("deviceId", "currentRoom", "currentScanner", "lastSeen",
                rssi, "roomChangedAt", "updatedAt")
               VALUES ($1, $2, $3, $4, $5, $6, NOW())''',
            device_id, room_id, scanner_id, scan_timestamp,
            rssi, scan_timestamp
        )

        # Create room entry event
        await conn.execute(
            '''INSERT INTO "roomPresenceHistory"
               ("deviceId", "roomId", "enteredAt", "enteredViaScanner")
               VALUES ($1, $2, $3, $4)''',
            device_id, room_id, scan_timestamp, scanner_id
        )

    @staticmethod
    async def _handle_room_change(
        conn,
        device_id: str,
        new_room_id: str,
        new_scanner_id: str,
        rssi: int,
        previous_room: str,
        scan_timestamp: datetime
    ):
        """Handle device moving from one room to another"""

        # Update location to new room
        await conn.execute(
            '''UPDATE "deviceLocations"
               SET "currentRoom" = $1,
                   "currentScanner" = $2,
                   "lastSeen" = $3,
                   rssi = $4,
                   "previousRoom" = $5,
                   "roomChangedAt" = $3,
                   "updatedAt" = NOW()
               WHERE "deviceId" = $6''',
            new_room_id, new_scanner_id, scan_timestamp,
            rssi, previous_room, device_id
        )

        # Close previous room presence (set exitedAt)
        await conn.execute(
            '''UPDATE "roomPresenceHistory"
               SET "exitedAt" = $1, "exitedViaScanner" = $2
               WHERE "deviceId" = $3 AND "exitedAt" IS NULL''',
            scan_timestamp, new_scanner_id, device_id
        )

        # Create new room entry
        await conn.execute(
            '''INSERT INTO "roomPresenceHistory"
               ("deviceId", "roomId", "enteredAt", "enteredViaScanner")
               VALUES ($1, $2, $3, $4)''',
            device_id, new_room_id, scan_timestamp, new_scanner_id
        )

    @staticmethod
    async def handle_stale_devices(
        conn,
        stale_threshold_minutes: int = 5
    ) -> int:
        """
        Mark devices as exited if not seen for X minutes

        Args:
            conn: Database connection
            stale_threshold_minutes: Minutes of inactivity before marking as exited

        Returns:
            Number of devices marked as stale

        This should be called periodically (e.g., every minute) to clean up
        devices that have left rooms but weren't detected leaving.
        """

        stale_cutoff = datetime.utcnow() - timedelta(minutes=stale_threshold_minutes)

        # Find devices not seen recently
        stale_devices = await conn.fetch(
            '''SELECT "deviceId", "currentRoom"
               FROM "deviceLocations"
               WHERE "lastSeen" < $1 AND "currentRoom" IS NOT NULL''',
            stale_cutoff
        )

        count = 0
        for device in stale_devices:
            device_id = device['deviceId']
            current_room = device['currentRoom']

            # Close room presence
            await conn.execute(
                '''UPDATE "roomPresenceHistory"
                   SET "exitedAt" = $1
                   WHERE "deviceId" = $2 AND "exitedAt" IS NULL''',
                stale_cutoff, device_id
            )

            # Clear current location
            await conn.execute(
                '''UPDATE "deviceLocations"
                   SET "currentRoom" = NULL,
                       "currentScanner" = NULL,
                       "updatedAt" = NOW()
                   WHERE "deviceId" = $1''',
                device_id
            )

            logger.info(
                f"📍 Device {device_id} marked as exited from {current_room} "
                f"(not seen for {stale_threshold_minutes}+ min)"
            )
            count += 1

        return count

    @staticmethod
    async def get_room_occupancy(conn, room_id: str) -> Dict[str, Any]:
        """
        Get current devices in a specific room

        Args:
            conn: Database connection
            room_id: Room ID (e.g., ICU-101)

        Returns:
            {
                "roomId": "ICU-101",
                "deviceCount": 3,
                "devices": [
                    {
                        "deviceId": "fit-00001",
                        "lastSeen": "2025-11-14T12:30:00Z",
                        "rssi": -45,
                        "duration": "01:23:45"
                    }
                ]
            }
        """

        devices = await conn.fetch(
            '''SELECT
                   dl."deviceId",
                   dl."lastSeen",
                   dl.rssi,
                   rph."enteredAt",
                   NOW() - rph."enteredAt" as duration
               FROM "deviceLocations" dl
               LEFT JOIN "roomPresenceHistory" rph
                   ON dl."deviceId" = rph."deviceId"
                   AND rph."exitedAt" IS NULL
               WHERE dl."currentRoom" = $1
               ORDER BY dl."lastSeen" DESC''',
            room_id
        )

        device_list = []
        for device in devices:
            device_list.append({
                "deviceId": device['deviceId'],
                "lastSeen": device['lastSeen'].isoformat() if device['lastSeen'] else None,
                "rssi": device['rssi'],
                "enteredAt": device['enteredAt'].isoformat() if device.get('enteredAt') else None,
                "duration": str(device['duration']) if device.get('duration') else None
            })

        return {
            "roomId": room_id,
            "deviceCount": len(device_list),
            "devices": device_list
        }

    @staticmethod
    async def get_device_location(conn, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current location of a specific device

        Args:
            conn: Database connection
            device_id: Device ID (e.g., fit-00001)

        Returns:
            {
                "deviceId": "fit-00001",
                "currentRoom": "ICU-101",
                "currentScanner": "door-00001",
                "lastSeen": "2025-11-14T12:30:00Z",
                "rssi": -45,
                "enteredAt": "2025-11-14T11:00:00Z",
                "duration": "01:30:00"
            }
            or None if device not found
        """

        location = await conn.fetchrow(
            '''SELECT
                   dl."deviceId",
                   dl."currentRoom",
                   dl."currentScanner",
                   dl."lastSeen",
                   dl.rssi,
                   rph."enteredAt",
                   NOW() - rph."enteredAt" as duration
               FROM "deviceLocations" dl
               LEFT JOIN "roomPresenceHistory" rph
                   ON dl."deviceId" = rph."deviceId"
                   AND rph."exitedAt" IS NULL
               WHERE dl."deviceId" = $1''',
            device_id
        )

        if not location:
            return None

        return {
            "deviceId": location['deviceId'],
            "currentRoom": location['currentRoom'],
            "currentScanner": location['currentScanner'],
            "lastSeen": location['lastSeen'].isoformat() if location['lastSeen'] else None,
            "rssi": location['rssi'],
            "enteredAt": location['enteredAt'].isoformat() if location.get('enteredAt') else None,
            "duration": str(location['duration']) if location.get('duration') else None
        }

    @staticmethod
    async def get_all_room_occupancy(conn) -> List[Dict[str, Any]]:
        """
        Get occupancy for all rooms

        Returns list of rooms with device counts
        """

        rooms = await conn.fetch(
            '''SELECT
                   ds."roomId",
                   ds."locationDescription",
                   ds.ward,
                   COUNT(dl."deviceId") as "deviceCount",
                   ds."lastScanTimestamp"
               FROM "doorScanners" ds
               LEFT JOIN "deviceLocations" dl ON dl."currentRoom" = ds."roomId"
               WHERE ds."isActive" = true
               GROUP BY ds."roomId", ds."locationDescription", ds.ward, ds."lastScanTimestamp"
               ORDER BY ds."roomId"'''
        )

        result = []
        for room in rooms:
            result.append({
                "roomId": room['roomId'],
                "locationDescription": room['locationDescription'],
                "ward": room['ward'],
                "deviceCount": room['deviceCount'],
                "lastScanTimestamp": room['lastScanTimestamp'].isoformat() if room['lastScanTimestamp'] else None
            })

        return result
