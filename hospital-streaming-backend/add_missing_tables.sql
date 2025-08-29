-- Add missing tables for investigations and therapies

-- Create patientInvestigations table
CREATE TABLE IF NOT EXISTS patientInvestigations (
    id VARCHAR(255) PRIMARY KEY,
    patientId VARCHAR(255) REFERENCES patients(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL, -- lab, imaging, biopsy, culture
    status VARCHAR(20) DEFAULT 'ordered', -- ordered, in_progress, completed, cancelled
    priority VARCHAR(20) DEFAULT 'routine', -- routine, urgent, stat
    orderedAt VARCHAR(50) NOT NULL,
    createdBy VARCHAR(255) NOT NULL,
    completedAt VARCHAR(50),
    results TEXT,
    notes TEXT,
    canEdit BOOLEAN DEFAULT TRUE,
    createdAt TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updatedAt TIMESTAMP WITH TIME ZONE
);

-- Create patientTherapies table
CREATE TABLE IF NOT EXISTS patientTherapies (
    id VARCHAR(255) PRIMARY KEY,
    patientId VARCHAR(255) REFERENCES patients(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL, -- physiotherapy, occupational, speech, respiratory
    description TEXT NOT NULL,
    frequency VARCHAR(100), -- e.g., "3x per week"
    duration VARCHAR(100), -- e.g., "4 weeks"
    status VARCHAR(20) DEFAULT 'active', -- active, completed, cancelled
    startedAt VARCHAR(50) NOT NULL,
    endedAt VARCHAR(50),
    createdBy VARCHAR(255) NOT NULL,
    therapist VARCHAR(255),
    canEdit BOOLEAN DEFAULT TRUE,
    createdAt TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updatedAt TIMESTAMP WITH TIME ZONE
);

-- Create therapySessions table (optional for detailed session tracking)
CREATE TABLE IF NOT EXISTS therapySessions (
    id VARCHAR(255) PRIMARY KEY,
    therapyId VARCHAR(255) REFERENCES patientTherapies(id) ON DELETE CASCADE,
    date VARCHAR(50) NOT NULL,
    duration INTEGER, -- in minutes
    notes TEXT,
    therapist VARCHAR(255),
    patientResponse TEXT,
    createdAt TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create vitalHistory table for detailed vital tracking
CREATE TABLE IF NOT EXISTS vitalHistory (
    id SERIAL PRIMARY KEY,
    patientId VARCHAR(255) REFERENCES patients(id) ON DELETE CASCADE,
    heartRate INTEGER,
    bloodPressureSystolic INTEGER,
    bloodPressureDiastolic INTEGER,
    temperature FLOAT,
    oxygenSaturation FLOAT,
    respiratoryRate INTEGER,
    ecgValue INTEGER,
    eegValue INTEGER,
    bioimpedance INTEGER,
    tremor FLOAT,
    fallRisk VARCHAR(20),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_patientInvestigations_patient ON patientInvestigations(patientId);
CREATE INDEX IF NOT EXISTS idx_patientInvestigations_status ON patientInvestigations(status);
CREATE INDEX IF NOT EXISTS idx_patientInvestigations_type ON patientInvestigations(type);

CREATE INDEX IF NOT EXISTS idx_patientTherapies_patient ON patientTherapies(patientId);
CREATE INDEX IF NOT EXISTS idx_patientTherapies_status ON patientTherapies(status);
CREATE INDEX IF NOT EXISTS idx_patientTherapies_type ON patientTherapies(type);

CREATE INDEX IF NOT EXISTS idx_therapySessions_therapy ON therapySessions(therapyId);
CREATE INDEX IF NOT EXISTS idx_vitalHistory_patient ON vitalHistory(patientId);
CREATE INDEX IF NOT EXISTS idx_vitalHistory_timestamp ON vitalHistory(timestamp);

-- Insert some sample data to populate case sheets
INSERT INTO patientCaseEntries (id, patientId, timestamp, entryType, description, createdBy, canEdit)
SELECT 
    'case_' || patients.id || '_admission',
    patients.id,
    NOW() - INTERVAL '2 days',
    'admission',
    'Patient admitted to ' || patients.ward || ' ward - ' || patients.diagnosis,
    patients.assignedDoctor,
    false
FROM patients 
WHERE isActive = true
ON CONFLICT (id) DO NOTHING;

-- Insert some sample medications for each patient
INSERT INTO patientMedications (id, patientId, name, dosage, frequency, route, status, startedAt, createdBy, createdAt, canEdit)
SELECT 
    'med_' || patients.id || '_01',
    patients.id,
    CASE 
        WHEN patients.diagnosis LIKE '%cardiac%' OR patients.diagnosis LIKE '%heart%' THEN 'Metoprolol'
        WHEN patients.diagnosis LIKE '%diabetes%' THEN 'Metformin'
        WHEN patients.diagnosis LIKE '%infection%' THEN 'Amoxicillin'
        ELSE 'Acetaminophen'
    END,
    CASE 
        WHEN patients.diagnosis LIKE '%cardiac%' OR patients.diagnosis LIKE '%heart%' THEN '25mg'
        WHEN patients.diagnosis LIKE '%diabetes%' THEN '500mg'
        WHEN patients.diagnosis LIKE '%infection%' THEN '500mg'
        ELSE '650mg'
    END,
    'Twice daily',
    'PO',
    'active',
    CURRENT_DATE::text,
    patients.assignedDoctor,
    NOW() - INTERVAL '1 day',
    true
FROM patients 
WHERE isActive = true
ON CONFLICT (id) DO NOTHING;

-- Insert case entries for the medications
INSERT INTO patientCaseEntries (id, patientId, timestamp, entryType, description, createdBy, canEdit)
SELECT 
    'case_' || meds.patientId || '_med_' || meds.id,
    meds.patientId,
    meds.createdAt,
    'medication',
    meds.name || ' ' || meds.dosage || ' prescribed by ' || meds.createdBy,
    meds.createdBy,
    false
FROM patientMedications meds
WHERE meds.id LIKE 'med_%_01'
ON CONFLICT (id) DO NOTHING;

-- Insert some sample vital history for patients
INSERT INTO vitalHistory (patientId, heartRate, bloodPressureSystolic, bloodPressureDiastolic, temperature, oxygenSaturation, respiratoryRate, ecgValue, eegValue, bioimpedance, tremor, fallRisk, timestamp)
SELECT 
    patients.id,
    75 + (random() * 20)::int - 10, -- heart rate 65-85
    120 + (random() * 30)::int - 15, -- systolic 105-135
    80 + (random() * 20)::int - 10, -- diastolic 70-90
    98.6 + (random() * 2) - 1, -- temperature 97.6-99.6
    98 + (random() * 3)::int - 1, -- oxygen sat 97-100
    16 + (random() * 8)::int - 4, -- respiratory rate 12-20
    120 + (random() * 40)::int - 20, -- ecg 100-140
    45 + (random() * 20)::int - 10, -- eeg 35-55
    500 + (random() * 100)::int - 50, -- bioimpedance 450-550
    (random() * 2)::numeric(3,1), -- tremor 0-2
    CASE WHEN random() < 0.1 THEN 'high' WHEN random() < 0.3 THEN 'medium' ELSE 'low' END,
    NOW() - INTERVAL '1 hour'
FROM patients 
WHERE isActive = true
ON CONFLICT DO NOTHING;

COMMIT;