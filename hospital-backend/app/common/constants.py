"""
System-wide constants.
Single source of truth for configuration values used across services.
"""

# Edit window for medical records (hours)
EDIT_WINDOW_HOURS = 24

# Alert deduplication window (minutes)
ALERT_DEDUPLICATION_MINUTES = 5

# Pagination defaults
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# WebSocket settings
WEBSOCKET_HEARTBEAT_INTERVAL_SECONDS = 30
WEBSOCKET_MESSAGE_QUEUE_SIZE = 1000

# MQTT settings
MQTT_QOS = 1
MQTT_KEEPALIVE_SECONDS = 60

# Vital signs sampling
VITALS_SAMPLING_RATE_HZ = 10
WAVEFORM_SAMPLING_RATE_HZ = 50

# Alert severity levels
ALERT_SEVERITY_LOW = 'low'
ALERT_SEVERITY_MEDIUM = 'medium'
ALERT_SEVERITY_HIGH = 'high'
ALERT_SEVERITY_CRITICAL = 'critical'

# Alert statuses
ALERT_STATUS_ACTIVE = 'active'
ALERT_STATUS_ACKNOWLEDGED = 'acknowledged'
ALERT_STATUS_RESOLVED = 'resolved'

# Patient statuses
PATIENT_STATUS_ACTIVE = 'active'
PATIENT_STATUS_DISCHARGED = 'discharged'
PATIENT_STATUS_PENDING_DISCHARGE = 'pendingDischarge'

# Staff roles
ROLE_DOCTOR = 'Doctor'
ROLE_NURSE = 'Nurse'
ROLE_ADMINISTRATOR = 'Administrator'
ROLE_TECHNICIAN = 'Technician'
ROLE_PROVISIONER = 'Provisioner'

# Medical record types
RECORD_TYPE_MEDICATION = 'medication'
RECORD_TYPE_INVESTIGATION = 'investigation'
RECORD_TYPE_THERAPY = 'therapy'
RECORD_TYPE_NOTE = 'note'
RECORD_TYPE_ALERT = 'alert'

# Vital types (for alerts)
VITAL_TYPE_HEART_RATE = 'heartrate'
VITAL_TYPE_OXYGEN_SATURATION = 'oxygensaturation'
VITAL_TYPE_BLOOD_PRESSURE_SYSTOLIC = 'bloodpressuresystolic'
VITAL_TYPE_BLOOD_PRESSURE_DIASTOLIC = 'bloodpressurediastolic'
VITAL_TYPE_TEMPERATURE = 'temperature'
VITAL_TYPE_RESPIRATORY_RATE = 'respiratoryrate'
