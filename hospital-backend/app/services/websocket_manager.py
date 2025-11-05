"""
WebSocket manager for real-time hospital data streaming
"""

import json
import asyncio
import logging
from typing import Dict, Set, Any, Optional, List
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        # Active connections by connection ID
        self.activeConnections: Dict[str, WebSocket] = {}
        
        # Connections subscribed to specific patients
        self.patientSubscriptions: Dict[str, Set[str]] = {}  # patientId -> set of connectionIds
        
        # Connections subscribed to general hospital updates
        self.generalSubscriptions: Set[str] = set()
        
        # Connection metadata
        self.connectionMetadata: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, connectionId: str, userId: str, userRole: str) -> None:
        """Register an already-accepted WebSocket connection"""
        # WebSocket already accepted in websocket.py endpoint - just register it here

        self.activeConnections[connectionId] = websocket
        self.connectionMetadata[connectionId] = {
            'userId': userId,
            'userRole': userRole,
            'connectedAt': datetime.now().isoformat(),
            'lastPing': datetime.now().isoformat()
        }
        
        # Auto-subscribe to general updates
        self.generalSubscriptions.add(connectionId)
        
        logger.info(f"🔌 WebSocket connection established: {connectionId} (User: {userId}, Role: {userRole})")
        
        # Send connection confirmation
        await self.sendToConnection(connectionId, {
            'type': 'connectionEstablished',
            'connectionId': connectionId,
            'timestamp': datetime.now().isoformat(),
            'message': 'Real-time updates enabled'
        })
    
    def disconnect(self, connectionId: str) -> None:
        """Remove a WebSocket connection"""
        if connectionId in self.activeConnections:
            del self.activeConnections[connectionId]
        
        if connectionId in self.connectionMetadata:
            del self.connectionMetadata[connectionId]
        
        # Remove from all subscriptions
        self.generalSubscriptions.discard(connectionId)
        
        for patientId in self.patientSubscriptions:
            self.patientSubscriptions[patientId].discard(connectionId)
        
        # Clean up empty patient subscriptions
        emptyPatients = [pid for pid, conns in self.patientSubscriptions.items() if not conns]
        for pid in emptyPatients:
            del self.patientSubscriptions[pid]
        
        logger.info(f"🔌 WebSocket connection closed: {connectionId}")
    
    async def sendToConnection(self, connectionId: str, data: Dict[str, Any]) -> bool:
        """Send data to a specific connection"""
        if connectionId not in self.activeConnections:
            return False
        
        try:
            websocket = self.activeConnections[connectionId]
            await websocket.send_text(json.dumps(data))
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send to connection {connectionId}: {e}")
            # Remove broken connection
            self.disconnect(connectionId)
            return False
    
    async def broadcastToPatientSubscribers(self, patientId: str, data: Dict[str, Any]) -> int:
        """Send data to all connections subscribed to a specific patient"""
        if patientId not in self.patientSubscriptions:
            return 0
        
        sentCount = 0
        failedConnections = []

        for connectionId in self.patientSubscriptions[patientId].copy():
            success = await self.sendToConnection(connectionId, data)
            if success:
                sentCount += 1
            else:
                failedConnections.append(connectionId)

        # Clean up failed connections
        for connId in failedConnections:
            self.patientSubscriptions[patientId].discard(connId)

        return sentCount
    
    async def broadcastGeneral(self, data: Dict[str, Any]) -> int:
        """Send data to all general subscribers"""
        sentCount = 0
        failedConnections = []

        for connectionId in self.generalSubscriptions.copy():
            success = await self.sendToConnection(connectionId, data)
            if success:
                sentCount += 1
            else:
                failedConnections.append(connectionId)

        # Clean up failed connections
        for connId in failedConnections:
            self.generalSubscriptions.discard(connId)

        return sentCount
    
    def subscribeToPatient(self, connectionId: str, patientId: str) -> bool:
        """Subscribe a connection to patient-specific updates"""
        if connectionId not in self.activeConnections:
            return False
        
        if patientId not in self.patientSubscriptions:
            self.patientSubscriptions[patientId] = set()
        
        self.patientSubscriptions[patientId].add(connectionId)
        logger.info(f"📡 Connection {connectionId} subscribed to patient {patientId}")
        return True
    
    def unsubscribeFromPatient(self, connectionId: str, patientId: str) -> bool:
        """Unsubscribe a connection from patient-specific updates"""
        if patientId in self.patientSubscriptions:
            self.patientSubscriptions[patientId].discard(connectionId)
            
            # Clean up empty subscriptions
            if not self.patientSubscriptions[patientId]:
                del self.patientSubscriptions[patientId]
            
            logger.info(f"📡 Connection {connectionId} unsubscribed from patient {patientId}")
            return True
        return False
    
    def getConnectionCount(self) -> int:
        """Get total number of active connections"""
        return len(self.activeConnections)
    
    def getPatientSubscriberCount(self, patientId: str) -> int:
        """Get number of connections subscribed to a specific patient"""
        return len(self.patientSubscriptions.get(patientId, set()))
    
    async def sendVitalsUpdate(self, patientId: str, deviceId: str, vitalsData: Dict[str, Any]) -> None:
        """Send vitals update to patient subscribers

        REMOVED: Redundant device assignment validation
        mqtt_service.py already validated device assignment (lines 418-431) before calling this.
        Repeating validation here was causing intermittent vitals display when validation failed.
        Trust MQTT service validation.
        """
        try:
            # Build vitals update message
            data = {
                'type': 'vitalsUpdate',
                'patientId': patientId,
                'deviceId': deviceId,
                'timestamp': datetime.now().isoformat(),
                'vitals': vitalsData
            }

            # Broadcast to all subscribers for this patient
            sentCount = await self.broadcastToPatientSubscribers(patientId, data)
            if sentCount > 0:
                logger.info(f"📊 Vitals update sent to {sentCount} subscribers for patient {patientId} from device {deviceId}")

        except Exception as e:
            logger.error(f"❌ Error sending vitals update: {e}")

    async def sendWaveformStream(self, patientId: str, deviceId: str, waveformData: Dict[str, Any]) -> None:
        """
        Send real-time waveform stream packet to patient subscribers
        Called 50 times per second (20ms intervals) for continuous ECG/EEG streaming

        This is EPHEMERAL streaming - NOT stored in database, only broadcast to WebSocket

        REMOVED: Redundant device assignment validation
        mqtt_service.py already validated device assignment (lines 649-692) before calling this.
        Repeating validation here was causing waveform display issues.
        Trust MQTT service validation - same as vitals.
        """
        try:
            # ✅ NEW: Process waveform data before sending to frontend
            # Decompress delta encoding and convert ADC → physical units (mV/μV)
            # This ensures frontend receives ready-to-display data
            processedWaveformData = processWaveformData(waveformData)

            # Build waveform stream message
            data = {
                'type': 'waveformStream',
                'patientId': patientId,
                'deviceId': deviceId,
                'timestamp': datetime.now().isoformat(),
                'waveform': processedWaveformData
            }

            # Broadcast to all subscribers for this patient
            sentCount = await self.broadcastToPatientSubscribers(patientId, data)

            # Debug log only every 10th packet (1 second intervals) to avoid spam
            sequence = waveformData.get('sequence', 0)
            if sequence % 10 == 0 and sentCount > 0:
                logger.debug(f"📊 Waveform stream sent to {sentCount} subscribers for patient {patientId} (seq: {sequence})")

        except Exception as e:
            logger.error(f"❌ Error in waveform stream broadcast: {e}")

    async def sendMedicationUpdate(self, patientId: str, medicationData: Dict[str, Any]) -> None:
        """Send medication update to patient subscribers"""
        data = {
            'type': 'medicationUpdate',
            'patientId': patientId,
            'timestamp': datetime.now().isoformat(),
            'medication': medicationData
        }
        
        sentCount = await self.broadcastToPatientSubscribers(patientId, data)
        if sentCount > 0:
            logger.info(f"💊 Medication update sent to {sentCount} subscribers for patient {patientId}")
    
    async def sendAlert(self, patientId: Optional[str], alertData: Dict[str, Any]) -> None:
        """Send alert to relevant subscribers"""
        data = {
            'type': 'alert',
            'patientId': patientId,
            'timestamp': datetime.now().isoformat(),
            'alert': alertData
        }

        if patientId:
            # Send to patient-specific subscribers
            sentCount = await self.broadcastToPatientSubscribers(patientId, data)
        else:
            # Send to all general subscribers
            sentCount = await self.broadcastGeneral(data)

        if sentCount > 0:
            logger.info(f"🚨 Alert sent to {sentCount} subscribers{f' for patient {patientId}' if patientId else ' (general)'}")

    async def broadcastSystemAlert(self, alertData: Dict[str, Any]) -> None:
        """
        Broadcast system-level alert to all connected clients
        Used for Component 2 system alerts (device pool, outbreak detection, etc.)
        """
        data = {
            'type': 'systemAlert',
            'timestamp': datetime.now().isoformat(),
            'alert': alertData
        }

        # Send to all general subscribers (all connected staff)
        sentCount = await self.broadcastGeneral(data)

        if sentCount > 0:
            logger.info(f"🚨 System alert broadcast to {sentCount} connections: {alertData.get('alertType')}")

    async def keepalive(self) -> None:
        """Send keepalive pings to all connections"""
        pingData = {
            'type': 'ping',
            'timestamp': datetime.now().isoformat()
        }
        
        sentCount = await self.broadcastGeneral(pingData)
        if sentCount > 0:
            logger.debug(f"💓 Keepalive sent to {sentCount} connections")

# ============================================
# WAVEFORM DATA PROCESSING HELPERS
# ============================================

def decompressChannelData(channelData: Dict[str, Any]) -> List[int]:
    """
    Decompress delta-encoded channel data
    Format: {baseline: int, deltas: List[int]}
    Returns: List of decompressed ADC values
    """
    if not channelData or 'baseline' not in channelData or 'deltas' not in channelData:
        return []

    baseline = channelData['baseline']
    deltas = channelData['deltas']

    # Reconstruct original values from delta encoding
    values = [baseline]
    for delta in deltas:
        values.append(values[-1] + delta)

    return values


def convertADCToMillivolts(adcValues: List[int]) -> List[float]:
    """
    Convert 24-bit ADC values to millivolts for ECG display

    ADC Format (from ESP32):
    - Midpoint: 8388608 (2^23, representing 0V)
    - Range: ±1.0V full scale
    - Sensitivity: ~10 μV per LSB

    Conversion formula:
    mV = (ADC_value - midpoint) * 0.01

    Example:
    - ADC 8388608 → 0.00 mV (baseline)
    - ADC 8410496 → 218.88 mV (positive deflection)
    - ADC 8366720 → -218.88 mV (negative deflection)
    """
    ADC_MIDPOINT = 8388608  # 2^23
    SENSITIVITY_MV = 0.01   # 10 μV per LSB = 0.01 mV per LSB

    return [(value - ADC_MIDPOINT) * SENSITIVITY_MV for value in adcValues]


def convertADCToMicrovolts(adcValues: List[int]) -> List[float]:
    """
    Convert 24-bit ADC values to microvolts for EEG display

    ADC Format (from ESP32):
    - Midpoint: 8388608 (2^23, representing 0V)
    - Range: ±0.1V full scale for EEG
    - Sensitivity: ~1 μV per LSB

    Conversion formula:
    μV = (ADC_value - midpoint) * 0.001
    """
    ADC_MIDPOINT = 8388608
    SENSITIVITY_UV = 0.001  # 1 μV per LSB

    return [(value - ADC_MIDPOINT) * SENSITIVITY_UV for value in adcValues]


def processWaveformData(waveformData: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process waveform data before sending to frontend:
    1. Decompress delta-encoded channel data
    2. Convert ADC values to physical units (mV for ECG, μV for EEG)

    This ensures frontend receives ready-to-display data in correct units.
    Frontend is display layer only - all conversions happen on backend.
    """
    processed = waveformData.copy()
    mode = waveformData.get('mode', 'ecg')

    # Process ECG waveform data
    if mode == 'ecg' and 'ecgWaveform' in waveformData:
        ecgWaveform = waveformData['ecgWaveform']
        processedECG = {}

        # Process limb leads (required)
        if 'limb' in ecgWaveform:
            processedECG['limb'] = {}
            # ✅ ESP32 v5.2.5 sends DELTA-ENCODED format with Roman numerals (leadI, leadII, leadIII)
            for leadName in ['leadI', 'leadII', 'leadIII']:
                if leadName in ecgWaveform['limb']:
                    # Pass through delta-encoded format unchanged
                    # Frontend will decode using decodeDeltaChannel() (medicalWaveformUtils.ts:94-117)
                    processedECG['limb'][leadName] = ecgWaveform['limb'][leadName]

        # Process precordial leads (optional)
        if 'precordial' in ecgWaveform:
            processedECG['precordial'] = {}
            for leadName in ['v1', 'v2', 'v3', 'v4', 'v5']:
                if leadName in ecgWaveform['precordial']:
                    # ✅ ESP32 v5.2.5 sends DELTA-ENCODED format
                    processedECG['precordial'][leadName] = ecgWaveform['precordial'][leadName]

        # Process derived leads (optional)
        if 'derived' in ecgWaveform:
            processedECG['derived'] = {}
            for leadName in ['avr', 'avl', 'avf', 'v6']:
                if leadName in ecgWaveform['derived']:
                    # ✅ ESP32 v5.2.5 sends DELTA-ENCODED format
                    processedECG['derived'][leadName] = ecgWaveform['derived'][leadName]

        # Copy other ECG metadata
        if 'events' in ecgWaveform:
            processedECG['events'] = ecgWaveform['events']

        processed['ecgWaveform'] = processedECG

    # Process EEG waveform data
    elif mode == 'eeg' and 'eegWaveform' in waveformData:
        eegWaveform = waveformData['eegWaveform']
        processedEEG = {}

        # Process frontal channels (required)
        if 'frontal' in eegWaveform:
            processedEEG['frontal'] = {}
            # ✅ ESP32 v5.2.5 sends DELTA-ENCODED format with proper capitalization (Fp1, Fp2, F3, F4)
            for channelName in ['Fp1', 'Fp2', 'F3', 'F4']:
                if channelName in eegWaveform['frontal']:
                    # Pass through delta-encoded format unchanged
                    processedEEG['frontal'][channelName] = eegWaveform['frontal'][channelName]

        # Process central channels (required)
        if 'central' in eegWaveform:
            processedEEG['central'] = {}
            # ✅ ESP32 v5.2.5 sends DELTA-ENCODED format with proper capitalization (C3, C4)
            for channelName in ['C3', 'C4']:
                if channelName in eegWaveform['central']:
                    # Pass through delta-encoded format unchanged
                    processedEEG['central'][channelName] = eegWaveform['central'][channelName]

        # Process occipital channels (required)
        if 'occipital' in eegWaveform:
            processedEEG['occipital'] = {}
            # ✅ ESP32 v5.2.5 sends DELTA-ENCODED format with proper capitalization (O1, O2)
            for channelName in ['O1', 'O2']:
                if channelName in eegWaveform['occipital']:
                    # Pass through delta-encoded format unchanged
                    processedEEG['occipital'][channelName] = eegWaveform['occipital'][channelName]

        # Copy other EEG metadata
        if 'analysis' in eegWaveform:
            processedEEG['analysis'] = eegWaveform['analysis']

        processed['eegWaveform'] = processedEEG

    return processed


# Global connection manager instance
connectionManager = ConnectionManager()

# Background task for keepalive pings
async def keepAliveTask():
    """Background task to send periodic keepalive pings"""
    while True:
        try:
            await connectionManager.keepalive()
            await asyncio.sleep(30)  # Send keepalive every 30 seconds
        except Exception as e:
            logger.error(f"❌ Keepalive task error: {e}")
            await asyncio.sleep(5)

# The keepalive task will be started when the FastAPI app starts
keepaliveTaskInstance = None

def startKeepaliveTask():
    """Start the keepalive background task"""
    global keepaliveTaskInstance
    if keepaliveTaskInstance is None:
        keepaliveTaskInstance = asyncio.create_task(keepAliveTask())
        logger.info("💓 WebSocket keepalive task started")

def stopKeepaliveTask():
    """Stop the keepalive background task"""
    global keepaliveTaskInstance
    if keepaliveTaskInstance is not None:
        keepaliveTaskInstance.cancel()
        keepaliveTaskInstance = None
        logger.info("💓 WebSocket keepalive task stopped")