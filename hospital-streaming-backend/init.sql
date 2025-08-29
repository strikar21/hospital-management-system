-- Hospital Streaming Backend Database Initialization

-- Create devices table
CREATE TABLE IF NOT EXISTS devices (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    device_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'offline',
    location VARCHAR(255),
    mac_address VARCHAR(17) UNIQUE,
    ip_address VARCHAR(45),
    capabilities JSONB,
    configuration JSONB,
    firmware_version VARCHAR(50),
    device_token VARCHAR(255) UNIQUE,
    api_key VARCHAR(255) UNIQUE,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_heartbeat TIMESTAMP WITH TIME ZONE,
    battery_level FLOAT,
    signal_strength INTEGER,
    assignment_status VARCHAR(20) DEFAULT 'free',
    assigned_to VARCHAR(255),
    assigned_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE
);

-- Create vital_readings table
CREATE TABLE IF NOT EXISTS vital_readings (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) REFERENCES devices(device_id) ON DELETE CASCADE,
    patient_id VARCHAR(255),
    heart_rate INTEGER,
    blood_pressure_systolic INTEGER,
    blood_pressure_diastolic INTEGER,
    temperature FLOAT,
    oxygen_saturation FLOAT,
    respiratory_rate INTEGER,
    ecg_data JSONB,
    eeg_data JSONB,
    movement_data JSONB,
    location_data JSONB,
    raw_data JSONB,
    processed_data JSONB,
    signal_quality FLOAT,
    is_valid BOOLEAN DEFAULT TRUE,
    reading_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    received_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create door_scan_events table
CREATE TABLE IF NOT EXISTS door_scan_events (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) REFERENCES devices(device_id) ON DELETE CASCADE,
    card_id VARCHAR(255),
    user_id VARCHAR(255),
    access_granted BOOLEAN NOT NULL,
    door_location VARCHAR(255) NOT NULL,
    scan_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    received_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    event_data JSONB
);

-- Create device_alerts table
CREATE TABLE IF NOT EXISTS device_alerts (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) REFERENCES devices(device_id) ON DELETE CASCADE,
    alert_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(255),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    alert_data JSONB
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_devices_device_id ON devices(device_id);
CREATE INDEX IF NOT EXISTS idx_devices_type ON devices(device_type);
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_location ON devices(location);

CREATE INDEX IF NOT EXISTS idx_vital_readings_device_id ON vital_readings(device_id);
CREATE INDEX IF NOT EXISTS idx_vital_readings_patient_id ON vital_readings(patient_id);
CREATE INDEX IF NOT EXISTS idx_vital_readings_timestamp ON vital_readings(reading_timestamp);

CREATE INDEX IF NOT EXISTS idx_door_events_device_id ON door_scan_events(device_id);
CREATE INDEX IF NOT EXISTS idx_door_events_timestamp ON door_scan_events(scan_timestamp);

CREATE INDEX IF NOT EXISTS idx_alerts_device_id ON device_alerts(device_id);
CREATE INDEX IF NOT EXISTS idx_alerts_active ON device_alerts(is_active);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON device_alerts(severity);

-- Create patient management tables
CREATE TABLE IF NOT EXISTS patients (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    bed_number VARCHAR(50) NOT NULL,
    ward VARCHAR(100) NOT NULL,
    room VARCHAR(100) NOT NULL,
    department VARCHAR(100) NOT NULL,
    assigned_doctor VARCHAR(255) NOT NULL,
    age INTEGER NOT NULL,
    gender VARCHAR(20) NOT NULL,
    weight FLOAT,
    diagnosis TEXT NOT NULL,
    admission_date VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'stable',
    current_vitals JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS patient_medications (
    id VARCHAR(255) PRIMARY KEY,
    patient_id VARCHAR(255) REFERENCES patients(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    dosage VARCHAR(100) NOT NULL,
    frequency VARCHAR(100) NOT NULL,
    route VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    start_date VARCHAR(50) NOT NULL,
    end_date VARCHAR(50),
    prescribed_by VARCHAR(255) NOT NULL,
    prescribed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    modified_by VARCHAR(255),
    modified_at TIMESTAMP WITH TIME ZONE,
    can_edit BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS medication_history (
    id VARCHAR(255) PRIMARY KEY,
    medication_id VARCHAR(255) REFERENCES patient_medications(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    performed_by VARCHAR(255) NOT NULL,
    changes JSONB
);

CREATE TABLE IF NOT EXISTS patient_notes (
    id VARCHAR(255) PRIMARY KEY,
    patient_id VARCHAR(255) REFERENCES patients(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    author_id VARCHAR(255) NOT NULL,
    author_name VARCHAR(255) NOT NULL,
    author_role VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    edited_at TIMESTAMP WITH TIME ZONE,
    can_edit BOOLEAN DEFAULT TRUE,
    is_edited BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS patient_case_entries (
    id VARCHAR(255) PRIMARY KEY,
    patient_id VARCHAR(255) REFERENCES patients(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    entry_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    performed_by VARCHAR(255) NOT NULL,
    can_edit BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS patient_alerts (
    id VARCHAR(255) PRIMARY KEY,
    patient_id VARCHAR(255) REFERENCES patients(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(255),
    acknowledged_by_name VARCHAR(255),
    acknowledged_by_role VARCHAR(50),
    acknowledged_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS staff (
    id VARCHAR(255) PRIMARY KEY,
    staff_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    department VARCHAR(100) NOT NULL,
    nfc_id VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255),
    phone VARCHAR(20),
    email VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS patient_device_mappings (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(255) REFERENCES patients(id) ON DELETE CASCADE,
    device_id VARCHAR(255) NOT NULL,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    assigned_by VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- Create indexes for patient tables
CREATE INDEX IF NOT EXISTS idx_patients_ward ON patients(ward);
CREATE INDEX IF NOT EXISTS idx_patients_department ON patients(department);
CREATE INDEX IF NOT EXISTS idx_patients_status ON patients(status);

CREATE INDEX IF NOT EXISTS idx_patient_medications_patient ON patient_medications(patient_id);
CREATE INDEX IF NOT EXISTS idx_patient_notes_patient ON patient_notes(patient_id);
CREATE INDEX IF NOT EXISTS idx_patient_alerts_patient ON patient_alerts(patient_id);
CREATE INDEX IF NOT EXISTS idx_staff_staff_id ON staff(staff_id);
CREATE INDEX IF NOT EXISTS idx_staff_nfc_id ON staff(nfc_id);

-- Create device assignments table for tracking assignment history
CREATE TABLE IF NOT EXISTS device_assignments (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) REFERENCES devices(device_id) ON DELETE CASCADE,
    patient_id VARCHAR(255) REFERENCES patients(id) ON DELETE CASCADE,
    assigned_by VARCHAR(255) REFERENCES staff(staff_id) ON DELETE SET NULL,
    assignment_reason VARCHAR(100) DEFAULT 'patient_admission',
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    unassigned_at TIMESTAMP WITH TIME ZONE,
    unassigned_by VARCHAR(255) REFERENCES staff(staff_id) ON DELETE SET NULL,
    unassignment_reason VARCHAR(100),
    new_device_id VARCHAR(255), -- For reassignment tracking
    status VARCHAR(20) DEFAULT 'active', -- active, completed, cancelled
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for device assignments
CREATE INDEX IF NOT EXISTS idx_device_assignments_device_id ON device_assignments(device_id);
CREATE INDEX IF NOT EXISTS idx_device_assignments_patient_id ON device_assignments(patient_id);
CREATE INDEX IF NOT EXISTS idx_device_assignments_status ON device_assignments(status);
CREATE INDEX IF NOT EXISTS idx_device_assignments_assigned_at ON device_assignments(assigned_at);
CREATE INDEX IF NOT EXISTS idx_devices_assignment_status ON devices(assignment_status);

-- Database initialized with empty tables ready for real data