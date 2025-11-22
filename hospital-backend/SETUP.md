# FHIR R5 Hospital IoT Backend - Setup Guide

## Local Development Setup

This guide will help you set up the FHIR R5 Hospital IoT Backend on your local machine for development.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Database Setup](#database-setup)
4. [Running the Application](#running-the-application)
5. [Testing](#testing)
6. [Development Workflow](#development-workflow)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

1. **Python 3.11+**
   - Windows: Download from [python.org](https://www.python.org/downloads/)
   - Ubuntu/Debian: `sudo apt install python3.11 python3.11-venv`
   - macOS: `brew install python@3.11`

2. **PostgreSQL 15+**
   - Windows: Download from [postgresql.org](https://www.postgresql.org/download/windows/)
   - Ubuntu/Debian: `sudo apt install postgresql-15`
   - macOS: `brew install postgresql@15`

3. **TimescaleDB 2.11+**
   - Follow installation guide: [TimescaleDB Installation](https://docs.timescale.com/install/latest/self-hosted/)

4. **Git**
   - Windows: Download from [git-scm.com](https://git-scm.com/)
   - Ubuntu/Debian: `sudo apt install git`
   - macOS: `brew install git`

### Optional Software

- **Redis** (for caching and rate limiting)
- **Docker** (for containerized development)
- **VS Code** (recommended IDE)

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/hospital-management-system.git
cd hospital-management-system/hospital-backend
```

### 2. Create Virtual Environment

**Windows:**
```powershell
python -m venv venv
venv\Scripts\activate
```

**Linux/macOS:**
```bash
python3.11 -m venv venv
source venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**requirements.txt:**
```
# Core
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# Database
asyncpg==0.29.0
psycopg2-binary==2.9.9

# Authentication
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
bcrypt==4.1.1

# Validation
pydantic==2.5.0
pydantic-settings==2.1.0

# MQTT (for ESP32)
paho-mqtt==1.6.1

# HTTP Client
httpx==0.25.1

# Utilities
python-dotenv==1.0.0
```

### 4. Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

**requirements-dev.txt:**
```
# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0

# Code Quality
black==23.11.0
flake8==6.1.0
mypy==1.7.1
pylint==3.0.2

# Documentation
mkdocs==1.5.3
mkdocs-material==9.5.0
```

---

## Database Setup

### 1. Start PostgreSQL

**Windows:**
```powershell
# PostgreSQL should start automatically after installation
# Check status in Services (services.msc)
```

**Linux:**
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**macOS:**
```bash
brew services start postgresql@15
```

### 2. Create Database and User

**Windows (PowerShell):**
```powershell
# Connect to PostgreSQL
psql -U postgres

# Run these commands in psql:
CREATE DATABASE hospital_iot;
CREATE USER hospital_user WITH ENCRYPTED PASSWORD 'dev_password_123';
GRANT ALL PRIVILEGES ON DATABASE hospital_iot TO hospital_user;

# Enable TimescaleDB
\c hospital_iot
CREATE EXTENSION IF NOT EXISTS timescaledb;

# Grant schema permissions
GRANT ALL ON SCHEMA public TO hospital_user;

# Exit
\q
```

**Linux/macOS:**
```bash
# Switch to postgres user
sudo -u postgres psql

# Run these commands in psql:
CREATE DATABASE hospital_iot;
CREATE USER hospital_user WITH ENCRYPTED PASSWORD 'dev_password_123';
GRANT ALL PRIVILEGES ON DATABASE hospital_iot TO hospital_user;

# Enable TimescaleDB
\c hospital_iot
CREATE EXTENSION IF NOT EXISTS timescaledb;

# Grant schema permissions
GRANT ALL ON SCHEMA public TO hospital_user;

# Exit
\q
```

### 3. Create Environment File

Create `.env` in the `hospital-backend` directory:

```env
# Database
DATABASE_URL=postgresql://hospital_user:dev_password_123@localhost:5432/hospital_iot

# JWT
JWT_SECRET_KEY=dev-secret-key-change-in-production-abcdef1234567890
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# HMS Integration (mock server)
HMS_BASE_URL=http://localhost:8001/api
HMS_API_KEY=dev-api-key

# CORS (allow all in development)
CORS_ORIGINS=["*"]

# Server
HOST=0.0.0.0
PORT=8000
RELOAD=true
LOG_LEVEL=debug

# TimescaleDB
TIMESCALEDB_RETENTION_DAYS=365

# Compliance
AUDIT_RETENTION_YEARS=6
CALIBRATION_RETENTION_YEARS=5

# Development
ENVIRONMENT=development
```

### 4. Run Database Migration

```bash
python migrate_to_fhir_r5.py
```

**Expected Output:**
```
[OK] Connecting to database...
[OK] Database connection successful
[OK] Starting FHIR R5 migration...
[OK] Dropped 18 legacy tables
[OK] Created 7 new FHIR R5 tables
[OK] Created TimescaleDB hypertables
[OK] Created indexes
[OK] Migration completed successfully!
```

### 5. Seed Initial Data

```bash
python seed_fhir_data.py
```

**Expected Output:**
```
[OK] Seeding initial data...
[OK] Created 2 staff records
[OK] Created 3 device records
[OK] Created 2 calibration records
[OK] Seeding completed!
```

### 6. Verify Database

```bash
python check_db_status.py
```

**Expected Output:**
```
========================================
DATABASE STATUS CHECK
========================================

Database: hospital_iot
Connected: [OK]

Tables:
  - fhirResources: 5 records
  - fhirObservations: 0 records
  - fhirConsent: 0 records
  - fhirAuditEvent: 0 records
  - deviceCalibration: 2 records
  - staff: 2 records
  - tokenBlacklist: 0 records

Staff:
  - STF000001 (NFC: NFC-DOC-001) - doctor
  - STF000002 (NFC: NFC-NURSE-001) - nurse

Devices:
  - DEV000001 (ESP32 Watch) - active
  - DEV000002 (ESP32 Watch) - active
  - DEV000003 (Door Scanner) - active

[OK] Database is healthy!
```

---

## Running the Application

### 1. Start Mock HMS Server (Terminal 1)

```bash
python mock_hms_server.py
```

**Output:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001
```

### 2. Start Main Backend Server (Terminal 2)

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Output:**
```
INFO:     Will watch for changes in these directories: ['c:\\...\\hospital-backend']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12346] using StatReload
INFO:     Started server process [12347]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 3. Access the API

- **API Base URL:** http://localhost:8000
- **API Documentation (Swagger):** http://localhost:8000/docs
- **Alternative Docs (ReDoc):** http://localhost:8000/redoc
- **Mock HMS:** http://localhost:8001/docs

### 4. Test Authentication

**Login:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"staffId": "STF000001", "pin": "1234"}'
```

**Response:**
```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "tokenType": "Bearer",
  "expiresIn": 86400,
  "staffId": "STF000001",
  "role": "doctor",
  "nfcBadgeId": "NFC-DOC-001"
}
```

**Use Token in Requests:**
```bash
export TOKEN="your-access-token-here"

curl -X GET http://localhost:8000/fhir/Patient/PAT000001 \
  -H "Authorization: Bearer $TOKEN"
```

---

## Testing

### 1. Run All Tests

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_consent_management.py

# Verbose output
pytest -v
```

### 2. Run Individual Test Modules

**Test FHIR Resources:**
```bash
python tests/test_fhir_resources.py
```

**Test Consent Management:**
```bash
python tests/test_consent_management.py
```

**Test Audit Logging:**
```bash
python tests/test_audit_logging.py
```

**Test HMS Integration:**
```bash
python tests/test_hms_integration.py
```

**Test ESP32 Watch Adapter:**
```bash
python tests/test_esp32_watch_adapter.py
```

**Test Door Scanner Adapter:**
```bash
python tests/test_door_scanner_adapter.py
```

### 3. Code Quality Checks

**Format Code (Black):**
```bash
black app/ tests/
```

**Lint Code (Flake8):**
```bash
flake8 app/ tests/ --max-line-length=100
```

**Type Check (MyPy):**
```bash
mypy app/
```

**Pylint:**
```bash
pylint app/
```

---

## Development Workflow

### 1. Create a New Feature Branch

```bash
git checkout -b feature/new-device-module
```

### 2. Make Changes

Edit files in your IDE (VS Code recommended):

**VS Code Extensions:**
- Python (Microsoft)
- Pylance (Microsoft)
- Python Test Explorer
- GitLens
- REST Client
- Docker

### 3. Test Your Changes

```bash
# Run related tests
pytest tests/test_your_feature.py -v

# Check code quality
black app/your_module.py
flake8 app/your_module.py
```

### 4. Commit Changes

```bash
git add .
git commit -m "feat: Add new device module for blood pressure monitor"
```

**Commit Message Format:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `test:` Tests
- `refactor:` Code refactoring
- `chore:` Maintenance

### 5. Push and Create Pull Request

```bash
git push origin feature/new-device-module
```

---

## WebSocket Development

### 1. Test WebSocket Connection

**Using JavaScript (browser console):**
```javascript
// Connect to global stream
const ws = new WebSocket('ws://localhost:8000/ws/vitals');

ws.onopen = () => {
  console.log('Connected to vitals stream');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};

ws.onclose = () => {
  console.log('Disconnected');
};

// Send ping
ws.send(JSON.stringify({type: 'ping', timestamp: new Date().toISOString()}));
```

**Using Python:**
```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws/vitals/PAT000001"

    async with websockets.connect(uri) as websocket:
        # Receive connection confirmation
        message = await websocket.recv()
        print(f"Received: {message}")

        # Send ping
        await websocket.send(json.dumps({
            "type": "ping",
            "timestamp": "2025-11-21T10:00:00Z"
        }))

        # Receive pong
        response = await websocket.recv()
        print(f"Response: {response}")

asyncio.run(test_websocket())
```

### 2. Simulate Device Data

**Create test script** `simulate_esp32_watch.py`:

```python
import asyncio
import json
import httpx
from datetime import datetime, timezone

async def simulate_vitals():
    """Simulate ESP32 watch sending vitals"""

    # Login to get token
    async with httpx.AsyncClient() as client:
        login_response = await client.post(
            "http://localhost:8000/auth/login",
            json={"staffId": "STF000001", "pin": "1234"}
        )
        token = login_response.json()["accessToken"]

        headers = {"Authorization": f"Bearer {token}"}

        # Send observation
        observation = {
            "resourceType": "Observation",
            "id": f"OBS-SIM-{datetime.now().timestamp()}",
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "vital-signs",
                    "display": "Vital Signs"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "8867-4",
                    "display": "Heart rate"
                }]
            },
            "subject": {"reference": "Patient/PAT000001"},
            "effectiveDateTime": datetime.now(timezone.utc).isoformat(),
            "issued": datetime.now(timezone.utc).isoformat(),
            "valueQuantity": {
                "value": 72,
                "unit": "beats/minute",
                "system": "http://unitsofmeasure.org",
                "code": "/min"
            },
            "device": {"reference": "Device/DEV000001"}
        }

        response = await client.post(
            "http://localhost:8000/fhir/Observation",
            headers=headers,
            json=observation
        )

        print(f"Created observation: {response.json()}")

asyncio.run(simulate_vitals())
```

---

## MQTT Development (ESP32 Integration)

### 1. Install MQTT Broker (Mosquitto)

**Windows:**
```powershell
# Download from https://mosquitto.org/download/
# Or use Docker:
docker run -d -p 1883:1883 -p 9001:9001 eclipse-mosquitto
```

**Linux:**
```bash
sudo apt install mosquitto mosquitto-clients
sudo systemctl start mosquitto
```

### 2. Test MQTT Pub/Sub

**Subscribe to topic:**
```bash
mosquitto_sub -h localhost -t "hospital/vitals/#" -v
```

**Publish test message:**
```bash
mosquitto_pub -h localhost -t "hospital/vitals/DEV000001" -m '{
  "deviceId": "DEV000001",
  "patientId": "PAT000001",
  "timestamp": "2025-11-21T10:00:00Z",
  "vitals": {
    "heartRate": 72,
    "spo2": 98,
    "temperature": 36.8
  },
  "battery": 85
}'
```

### 3. Create MQTT Consumer Service

**app/services/mqtt_consumer.py:**
```python
import paho.mqtt.client as mqtt
import json
from app.device_modules.esp32_watch.adapter import ESP32WatchAdapter

adapter = ESP32WatchAdapter()

def on_message(client, userdata, msg):
    payload = json.loads(msg.payload)
    observations = adapter.transform_to_fhir_observations(payload)

    # Send to FHIR API
    for obs in observations:
        # POST to /fhir/Observation
        print(f"Created observation: {obs['id']}")

client = mqtt.Client()
client.on_message = on_message
client.connect("localhost", 1883)
client.subscribe("hospital/vitals/#")
client.loop_forever()
```

---

## Docker Development

### 1. Create Docker Compose for Development

**docker-compose.dev.yml:**
```yaml
version: '3.8'

services:
  postgres:
    image: timescale/timescaledb:latest-pg15
    container_name: hospital-postgres-dev
    environment:
      POSTGRES_DB: hospital_iot
      POSTGRES_USER: hospital_user
      POSTGRES_PASSWORD: dev_password_123
      TIMESCALEDB_TELEMETRY: off
    ports:
      - "5432:5432"
    volumes:
      - postgres-dev-data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    container_name: hospital-redis-dev
    ports:
      - "6379:6379"

  mosquitto:
    image: eclipse-mosquitto
    container_name: hospital-mqtt-dev
    ports:
      - "1883:1883"
      - "9001:9001"
    volumes:
      - ./mosquitto.conf:/mosquitto/config/mosquitto.conf

volumes:
  postgres-dev-data:
```

### 2. Start Development Environment

```bash
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop environment
docker-compose -f docker-compose.dev.yml down
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Error

**Error:**
```
asyncpg.exceptions.InvalidCatalogNameError: database "hospital_iot" does not exist
```

**Solution:**
```bash
# Create database
psql -U postgres -c "CREATE DATABASE hospital_iot;"
```

#### 2. TimescaleDB Extension Not Found

**Error:**
```
ERROR: extension "timescaledb" is not available
```

**Solution:**
```bash
# Install TimescaleDB (Ubuntu)
sudo add-apt-repository ppa:timescale/timescaledb-ppa
sudo apt update
sudo apt install timescaledb-2-postgresql-15
sudo timescaledb-tune --quiet --yes
sudo systemctl restart postgresql
```

#### 3. Permission Denied on Schema

**Error:**
```
asyncpg.exceptions.InsufficientPrivilegeError: permission denied for schema public
```

**Solution:**
```sql
-- Connect as postgres user
psql -U postgres hospital_iot

-- Grant permissions
GRANT ALL ON SCHEMA public TO hospital_user;
GRANT ALL ON ALL TABLES IN SCHEMA public TO hospital_user;
```

#### 4. Port Already in Use

**Error:**
```
ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000): only one usage of each socket address
```

**Solution (Windows):**
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill process (replace PID)
taskkill /PID 12345 /F
```

**Solution (Linux/macOS):**
```bash
# Find and kill process
lsof -ti:8000 | xargs kill -9
```

#### 5. Module Import Errors

**Error:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

#### 6. Unicode Encoding Error (Windows)

**Error:**
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2713'
```

**Solution:**
```powershell
# Set UTF-8 encoding
$env:PYTHONIOENCODING = "utf-8"
chcp 65001
```

---

## IDE Configuration

### VS Code Settings

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/Scripts/python.exe",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "tests"
  ],
  "editor.formatOnSave": true,
  "editor.rulers": [100],
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true
  }
}
```

### VS Code Launch Configuration

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI: Main Backend",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--reload",
        "--host",
        "0.0.0.0",
        "--port",
        "8000"
      ],
      "jinja": true,
      "justMyCode": false
    },
    {
      "name": "FastAPI: Mock HMS",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "mock_hms_server:app",
        "--reload",
        "--host",
        "0.0.0.0",
        "--port",
        "8001"
      ]
    }
  ]
}
```

---

## Quick Reference

### Database

```bash
# Connect to database
psql -U hospital_user -d hospital_iot

# List tables
\dt

# Describe table
\d fhirResources

# Run migration
python migrate_to_fhir_r5.py

# Seed data
python seed_fhir_data.py

# Check status
python check_db_status.py
```

### Server

```bash
# Start main backend
uvicorn app.main:app --reload

# Start mock HMS
python mock_hms_server.py

# Start with workers
uvicorn app.main:app --workers 4
```

### Testing

```bash
# All tests
pytest

# Specific test
pytest tests/test_consent_management.py

# With coverage
pytest --cov=app

# Verbose
pytest -v -s
```

### Code Quality

```bash
# Format
black app/ tests/

# Lint
flake8 app/ tests/

# Type check
mypy app/
```

---

## Next Steps

After completing setup:

1. Read [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for API details
2. Read [DEVICE_MODULE_GUIDE.md](DEVICE_MODULE_GUIDE.md) for creating device adapters
3. Explore the codebase structure
4. Run all tests to ensure everything works
5. Create your first device module!

---

## Support

For setup issues:
- GitHub Issues: [hospital-management-system/issues](https://github.com/yourusername/hospital-management-system/issues)
- Email: dev@hospital.org
- Slack: #hospital-iot-dev
