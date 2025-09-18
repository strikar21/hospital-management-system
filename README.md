# Hospital Management System

A complete **hospital management system** with React frontend and FastAPI backend for real-time patient monitoring and medical workflows.

## 🚀 Quick Start

### Start Backend Services
```bash
cd hospital-backend
docker-compose up -d
python main.py
```

### Start Frontend
```bash
cd hospital-display-app
npm install
npm start
```

### Access System
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs
- **Login**: Use any Staff ID (e.g., "NURSE001", "DOC0001")

## 🏥 Complete System Architecture

### Frontend (React TypeScript)
- **Medical UI Components** for patient monitoring
- **Role-based Authentication** for staff access
- **Real-time vital signs displays**
- **Complete patient workflow interface**

### Backend (FastAPI Python)
- **PostgreSQL** for main data storage
- **TimescaleDB** for time-series vitals data
- **MQTT** for ESP32 device communication
- **WebSocket** for real-time updates

### Hardware Integration
- **ESP32 watches** for patient vital monitoring
- **BLE/WiFi connectivity** for data transmission
- **Door scanners** for room tracking

## 📋 API Endpoints

### 🔐 Authentication (`/api/v1/auth`)
- `POST /login` - Staff authentication
- `POST /simple-login` - Simplified login
- `POST /logout` - End session
- `GET /me/{staff_id}` - Get staff profile
- `POST /nfc-tap` - NFC authentication

### 👥 Staff Management (`/api/v1/staff`)
- `GET /` - List all staff
- `GET /{staff_id}` - Get staff details
- `POST /` - Create new staff member

### 🏥 Admission Workflow (`/api/v1/admission`)
- `POST /recommendations` - Create admission recommendation
- `GET /recommendations` - List pending recommendations
- `POST /process-admission` - Process patient admission
- `GET /available-beds` - Check bed availability
- `GET /available-devices` - List free devices
- `GET /bed-occupancy` - Current bed status

### 👤 Patient Management (`/api/v1/patients`)
- `GET /` - List all patients
- `GET /{patient_id}` - Get patient details
- `POST /` - Create new patient
- `PUT /{patient_id}` - Update patient info
- `POST /{patient_id}/discharge-request` - Request discharge
- `POST /{patient_id}/discharge-approve` - Approve discharge
- `POST /{patient_id}/discharge-complete` - Complete discharge
- `GET /{patient_id}/discharge-summary` - Get discharge summary

### 💊 Medical Records (`/api/v1/patients/{patient_id}`)
- `POST /medications` - Add medication
- `GET /medications` - List medications
- `PUT /medications/{med_id}` - Update medication
- `DELETE /medications/{med_id}` - Remove medication
- `POST /medications/{med_id}/administer` - Record administration

### 🔬 Investigations (`/api/v1/patients/{patient_id}`)
- `POST /investigations` - Order investigation
- `GET /investigations` - List investigations
- `PUT /investigations/{inv_id}` - Update investigation
- `DELETE /investigations/{inv_id}` - Cancel investigation

### 🏃 Therapy Management (`/api/v1/patients/{patient_id}`)
- `POST /therapies` - Add therapy session
- `GET /therapies` - List therapy sessions
- `PUT /therapies/{therapy_id}` - Update therapy
- `DELETE /therapies/{therapy_id}` - Cancel therapy

### 📝 Medical Notes (`/api/v1/patients/{patient_id}`)
- `POST /notes` - Add medical note
- `GET /notes` - List notes
- `PUT /notes/{note_id}` - Update note
- `DELETE /notes/{note_id}` - Delete note

### 📈 Vitals Monitoring (`/api/v1/patients/{patient_id}`)
- `GET /vitals` - Get vital signs history
- `POST /vitals` - Record vital signs
- `PUT /vitals` - Update vital signs
- `POST /vitals-test` - Test vitals endpoint

### 📱 Device Management (`/api/v1/devices`)
- `GET /` - List all devices
- `GET /{device_id}` - Get device details
- `POST /` - Register new device
- `PUT /{device_id}` - Update device
- `POST /assign` - Assign device to patient
- `POST /unassign/{device_id}` - Unassign device
- `GET /assignments/` - List device assignments

### 🔄 Device Assignment (`/api/v1/device-assignment`)
- `GET /free-devices` - List available devices
- `POST /assign` - Assign device to patient
- `POST /unassign/{device_id}` - Unassign device
- `GET /pool-status` - Device pool status
- `GET /history` - Assignment history

### 📡 ESP32 Integration (`/api/v1/esp32`)
- `POST /provision` - Provision ESP32 device
- `POST /online` - Mark device online
- `POST /register` - Register new ESP32
- `POST /{device_id}/heartbeat` - Device heartbeat
- `POST /{device_id}/vitals/{patient_id}` - Submit vitals data
- `POST /{device_id}/alert` - Send alert
- `POST /door-scanner/{scanner_id}/scan` - Door scanner input

### 🌐 WebSocket (`/api/v1/ws`)
- `GET /connections/status` - WebSocket status
- `POST /broadcast/vitals/{patient_id}` - Broadcast vitals
- `POST /broadcast/medication/{patient_id}` - Broadcast medication
- `POST /broadcast/alert` - Broadcast alert

### 🚪 Discharge Workflow (`/api/v1/discharge-workflow`)
- `POST /doctor-request` - Doctor discharge request
- `POST /nurse-approve` - Nurse approval
- `GET /pending` - List pending discharges

### 📱 Mobile & Proximity (`/api/v1/mobile`)
- `GET /room-proximity` - Room proximity data
- `POST /room-entry` - Record room entry
- `GET /device-locations` - Device location tracking

### 📊 Audit & Compliance (`/api/v1/audit`)
- `POST /log` - Create audit log
- `GET /logs` - List audit logs

### ❤️ System Health
- `GET /health` - System health check
- `GET /` - API information

## 🎯 Complete End-to-End Workflow

1. **Doctor creates admission recommendation** → `/admission/recommendations`
2. **Nurse processes admission & assigns bed** → `/admission/process-admission`
3. **System assigns ESP32 monitoring device** → `/device-assignment/assign`
4. **Doctor prescribes medications** → `/patients/{id}/medications`
5. **Staff orders investigations** → `/patients/{id}/investigations`
6. **ESP32 device sends real-time vitals** → `/esp32/{device}/vitals/{patient}`
7. **Medical staff add progress notes** → `/patients/{id}/notes`
8. **Therapy sessions scheduled** → `/patients/{id}/therapies`
9. **Discharge process initiated** → `/discharge-workflow/doctor-request`
10. **Device unassigned upon discharge** → `/device-assignment/unassign`

## 📋 Current Status

### ✅ Fully Working
- Complete patient admission workflow
- ESP32 device integration & vitals monitoring
- Device assignment and management
- Real-time WebSocket communication
- Authentication and staff management
- Investigation ordering and tracking
- Discharge workflow automation
- Audit logging and compliance

### 🔧 In Development
- Medications endpoint (database query optimization)
- Notes endpoint (PostgreSQL compatibility)
- Therapy management (endpoint validation)

## 🛠️ Technical Stack

- **Frontend**: React TypeScript, Modern UI Components
- **Backend**: FastAPI Python, Async/Await
- **Databases**: PostgreSQL + TimescaleDB
- **Real-time**: WebSocket + MQTT
- **Hardware**: ESP32 with WiFi/BLE
- **Security**: Role-based access, Audit logging
- **Deployment**: Docker containers

---

**A production-ready hospital management system with real-time monitoring and complete medical workflows.**