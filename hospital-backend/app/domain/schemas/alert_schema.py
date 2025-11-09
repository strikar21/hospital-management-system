"""
Alert schema - Single source of truth for alert data structure.

This schema is mirrored in frontend:
    hospital-display-app/src/data/schemas/Alert.schema.ts

Any changes here MUST be reflected in frontend schema.

Usage:
    from app.domain.schemas import AlertRecord

    alert: AlertRecord = {
        'id': 'alert-uuid',
        'patientId': 'P001',
        'type': 'vital',
        'severity': 'critical',
        'message': 'Severe Tachycardia: 160 bpm',
        'status': 'active',
        'createdAt': datetime.now(timezone.utc)
    }
"""

from typing import TypedDict, Optional, Literal
from datetime import datetime


# Type aliases for better type safety
AlertType = Literal['vital', 'arrhythmia', 'device', 'system']
AlertSeverity = Literal['low', 'medium', 'high', 'critical']
AlertStatus = Literal['active', 'acknowledged', 'resolved']


class AlertRecord(TypedDict, total=False):
    """
    Complete alert data structure.

    Used for:
    - Patient vital alerts (threshold breaches)
    - Arrhythmia detection alerts
    - Device malfunction alerts
    - System-level alerts

    Frontend Mirror: hospital-display-app/src/data/schemas/Alert.schema.ts
    """

    # ========================================
    # CORE ALERT FIELDS (Required)
    # ========================================
    id: str                               # Alert UUID (REQUIRED)
    patientId: str                        # Patient UUID (REQUIRED)
    type: AlertType                       # Alert type (REQUIRED)
    message: str                          # Human-readable message (REQUIRED)
    severity: AlertSeverity               # Alert severity (REQUIRED)
    status: AlertStatus                   # Alert status (REQUIRED)
    createdAt: datetime                   # Creation timestamp (REQUIRED)

    # ========================================
    # VITAL ALERT SPECIFIC FIELDS (Optional)
    # ========================================
    vitalType: Optional[str]              # Type of vital that triggered alert
    vitalValue: Optional[float]           # Current vital value
    thresholdValue: Optional[float]       # Threshold that was breached

    # ========================================
    # ACKNOWLEDGMENT TRACKING
    # ========================================
    acknowledgedBy: Optional[str]         # Staff ID who acknowledged
    acknowledgedByName: Optional[str]     # Staff name (resolved by backend)
    acknowledgedByRole: Optional[str]     # Staff role (resolved by backend)
    acknowledgedAt: Optional[datetime]    # Acknowledgment timestamp

    # ========================================
    # RESOLUTION TRACKING
    # ========================================
    resolvedBy: Optional[str]             # Staff ID who resolved
    resolvedByName: Optional[str]         # Staff name (resolved by backend)
    resolvedAt: Optional[datetime]        # Resolution timestamp

    # ========================================
    # AUDIT TRAIL
    # ========================================
    createdBy: Optional[str]              # System or device that created alert
    deletedAt: Optional[datetime]         # Soft delete timestamp


class AlertDeduplicationWindow(TypedDict):
    """
    Configuration for alert deduplication logic.

    Prevents duplicate alerts for same patient + vital type within time window.
    """
    patientId: str                        # Patient UUID
    vitalType: str                        # Vital type to check
    windowMinutes: int                    # Deduplication window (default: 5 minutes)


class AlertAcknowledgment(TypedDict):
    """
    Alert acknowledgment request structure.

    Used when staff acknowledges an alert via UI.
    """
    alertId: str                          # Alert UUID to acknowledge
    acknowledgedBy: str                   # Staff ID
    acknowledgedAt: datetime              # Acknowledgment timestamp
    notes: Optional[str]                  # Optional acknowledgment notes


class AlertResolution(TypedDict):
    """
    Alert resolution request structure.

    Used when alert condition is resolved (e.g., vitals return to normal).
    """
    alertId: str                          # Alert UUID to resolve
    resolvedBy: str                       # Staff ID or 'system'
    resolvedAt: datetime                  # Resolution timestamp
    resolutionReason: Optional[str]       # Why alert was resolved
