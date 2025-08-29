# Hospital Streaming Backend

A comprehensive backend system for managing hospital IoT devices, streaming real-time vital signs data, and handling device communications through MQTT and WebSocket protocols.

## Features

### 🏥 Device Management
- **Multi-device Support**: Watches, door scanners, vital monitors, ECG machines, tablets, sensors
- **Device Registration & Authentication**: Secure token-based authentication for all devices
- **Real-time Status Monitoring**: Track device health, battery levels, connectivity
- **Capability-based Access Control**: Devices can only access endpoints they're authorized for

### 📊 Real-time Data Streaming  
- **WebSocket Streams**: Live streaming of vitals, alerts, door events, device status
- **MQTT Integration**: IoT device communication via MQTT broker
- **Multi-channel Broadcasting**: Separate channels for different data types
- **Scalable Architecture**: Handles thousands of concurrent connections

### 💓 Vital Signs Processing
- **Comprehensive Vitals**: Heart rate, blood pressure, temperature, O2 sat, respiratory rate
- **Extended Monitoring**: ECG/EEG data, movement tracking, location data
- **Signal Quality Assessment**: Data validation and quality scoring
- **Batch Processing**: Efficient handling of multiple readings

### 🚪 Access Control & Security
- **Door Scanner Integration**: RFID/NFC card scanning and access logging  
- **Real-time Access Events**: Instant notification of door access attempts
- **Security Alerts**: Failed access attempts and security notifications
- **Audit Trail**: Complete logging of all access events

### 🔔 Alert System
- **Real-time Alerts**: Critical health alerts and device notifications
- **Severity Levels**: Low, medium, high, critical alert classification
- **Alert Acknowledgment**: Staff can acknowledge and manage alerts
- **Device Health Alerts**: Battery low, offline devices, signal issues

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   IoT Devices   │    │  Display Apps   │    │  Mobile Apps    │
│  (Watches, etc) │    │   (WebSocket)   │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │ MQTT                 │ WebSocket            │ REST API
          │                      │                      │
┌─────────▼──────────────────────▼──────────────────────▼───────┐
│               Hospital Streaming Backend                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐  │
│  │ MQTT Service│ │ WebSocket   │ │     REST API            │  │
│  │             │ │ Manager     │ │   (Device Management)   │  │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              Device Authentication                      │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────┬───────────────────────────────────────────────────┘
          │
┌─────────▼───────┐  ┌─────────────┐  ┌─────────────┐
│   PostgreSQL    │  │    Redis    │  │   MQTT      │
│   Database      │  │   Cache     │  │   Broker    │
└─────────────────┘  └─────────────┘  └─────────────┘
```

## Quick Start

### Using Docker (Recommended)

1. **Clone and navigate to directory:**
   ```bash
   cd hospital-streaming-backend
   ```

2. **Start all services:**
   ```bash
   docker-compose up -d
   ```

3. **Access the API:**
   - API: http://localhost:8001
   - API Docs: http://localhost:8001/docs
   - Database Admin: http://localhost:5050 (pgAdmin)

### Manual Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start services:**
   ```bash
   # Start PostgreSQL and MQTT broker
   # Then start the backend
   python start.py
   ```

## API Documentation

### Device Management

#### Register Device
```http
POST /api/v1/devices/
Content-Type: application/json

{
  "device_id": "WATCH_001",
  "name": "Patient Watch #1", 
  "device_type": "watch",
  "location": "ICU-101",
  "capabilities": {
    "vitals": true,
    "location": true,
    "battery": true
  }
}
```

#### Get Devices
```http
GET /api/v1/devices/?device_type=watch&status=online
```

### Data Ingestion

#### Send Vital Signs
```http
POST /api/v1/ingest/vitals
X-Device-Token: <device_token>
Content-Type: application/json

{
  "device_id": "WATCH_001",
  "patient_id": "PATIENT_123",
  "heart_rate": 75,
  "blood_pressure_systolic": 120,
  "blood_pressure_diastolic": 80,
  "temperature": 98.6,
  "oxygen_saturation": 98.5,
  "reading_timestamp": "2024-01-17T14:30:00Z"
}
```

#### Door Scan Event
```http
POST /api/v1/ingest/door-scan
X-Device-Token: <device_token>
Content-Type: application/json

{
  "device_id": "DOOR_001",
  "card_id": "CARD_123",
  "user_id": "STAFF_456",
  "access_granted": true,
  "door_location": "ICU-MAIN",
  "scan_timestamp": "2024-01-17T14:30:00Z"
}
```

### WebSocket Streaming

Connect to real-time streams:

```javascript
// Vital signs stream
const vitalsWs = new WebSocket('ws://localhost:8001/ws/vitals/client_123');

// Alerts stream  
const alertsWs = new WebSocket('ws://localhost:8001/ws/alerts/client_123');

// Door events stream
const doorWs = new WebSocket('ws://localhost:8001/ws/door_events/client_123');
```

### MQTT Topics

Devices can publish data to these MQTT topics:

```
hospital/devices/{device_id}/vitals     # Vital signs data
hospital/devices/{device_id}/door       # Door scanner events  
hospital/devices/{device_id}/heartbeat  # Device health status
hospital/devices/{device_id}/alerts     # Device alerts
```

## Device Types & Capabilities

| Device Type | Capabilities | Description |
|-------------|--------------|-------------|
| `watch` | vitals, location, battery | Patient monitoring watches |
| `door_scanner` | nfc, rfid, access_control | Door access scanners |
| `vital_monitor` | ecg, vitals, alarms | Bedside monitoring equipment |
| `ecg_machine` | ecg, vitals | ECG/EKG machines |
| `tablet` | display, input | Staff tablets and displays |
| `sensor` | environmental | Environmental sensors |

## Authentication

All devices must authenticate using one of these methods:

1. **Device Token** (Header: `X-Device-Token`)
2. **API Key** (Header: `X-API-Key`) 
3. **JWT Token** (Header: `Authorization: Bearer <token>`)

Tokens are generated during device registration and provide capability-based access control.

## Environment Configuration

Create `.env` file with:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/hospital_streaming

# Redis  
REDIS_URL=redis://localhost:6379

# MQTT
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_USERNAME=hospital_user
MQTT_PASSWORD=hospital_pass

# Security
JWT_SECRET_KEY=your-secret-key-here
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# API
API_HOST=0.0.0.0
API_PORT=8001
```

## Health Monitoring

Check system health:

```http
GET /api/v1/health/              # Overall system health
GET /api/v1/health/devices       # Device status summary  
GET /api/v1/health/streaming     # WebSocket connection stats
GET /api/v1/health/database      # Database connectivity
GET /api/v1/health/alerts        # Active alerts summary
```

## Sample Device Integration

### Python IoT Device Example

```python
import requests
import json
from datetime import datetime

class HospitalDevice:
    def __init__(self, device_token, base_url="http://localhost:8001"):
        self.device_token = device_token
        self.base_url = base_url
        self.headers = {
            "X-Device-Token": device_token,
            "Content-Type": "application/json"
        }
    
    def send_vitals(self, device_id, patient_id, vitals_data):
        data = {
            "device_id": device_id,
            "patient_id": patient_id,
            "reading_timestamp": datetime.utcnow().isoformat(),
            **vitals_data
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/ingest/vitals",
            headers=self.headers,
            json=data
        )
        return response.json()

# Usage
device = HospitalDevice("your-device-token")
result = device.send_vitals("WATCH_001", "PATIENT_123", {
    "heart_rate": 75,
    "temperature": 98.6,
    "oxygen_saturation": 98.5
})
```

## Production Deployment

For production deployment:

1. **Security**: Change default passwords, use proper JWT secrets
2. **SSL/TLS**: Enable HTTPS and secure WebSocket connections  
3. **Database**: Use managed PostgreSQL with proper backup
4. **MQTT**: Configure MQTT authentication and encryption
5. **Monitoring**: Set up logging, metrics, and alerting
6. **Scaling**: Use load balancers and horizontal scaling

## Support

For issues and questions:
- Check the API documentation at `/docs` 
- Review the health endpoints for system status
- Check logs for detailed error information

## License

This project is licensed under the MIT License - see the LICENSE file for details.