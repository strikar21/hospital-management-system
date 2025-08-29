-- Test clinical data for existing patient CHUCK (P2508271105)

-- Add medications for patient CHUCK
INSERT INTO patient_medications (patient_id, medication_name, dosage, frequency, route, status, start_date, prescribed_by, notes, created_at, updated_at) VALUES
('P2508271105', 'Aspirin', '81mg', 'Once daily', 'PO', 'active', '2025-08-25', 'Dr. Emily Rodriguez', 'For cardiac protection', NOW(), NOW()),
('P2508271105', 'Metoprolol', '25mg', 'Twice daily', 'PO', 'active', '2025-08-25', 'Dr. Emily Rodriguez', 'Beta blocker for BP control', NOW(), NOW()),
('P2508271105', 'Simvastatin', '20mg', 'Once daily at bedtime', 'PO', 'active', '2025-08-26', 'Dr. Emily Rodriguez', 'Cholesterol management', NOW(), NOW());

-- Add investigations for patient CHUCK
INSERT INTO investigations (patient_id, type, name, priority, status, notes, ordered_by, ordered_date, scheduled_date, results, completed_date, created_at, updated_at) VALUES
('P2508271105', 'Blood Work', 'Complete Blood Count', 'routine', 'completed', 'Routine monitoring', 'Dr. Emily Rodriguez', '2025-08-25', '2025-08-25', 'WBC: 7.2, RBC: 4.5, Hgb: 14.2, Hct: 42%, Platelets: 250k', '2025-08-25', NOW(), NOW()),
('P2508271105', 'Imaging', 'Chest X-Ray', 'urgent', 'completed', 'Check for complications', 'Dr. Emily Rodriguez', '2025-08-25', '2025-08-25', 'Clear lungs, no acute findings', '2025-08-25', NOW(), NOW()),
('P2508271105', 'Blood Work', 'Cardiac Enzymes', 'urgent', 'completed', 'Rule out MI', 'Dr. Emily Rodriguez', '2025-08-25', '2025-08-25', 'Troponin I: 0.02 ng/mL (normal), CK-MB: 3.1 ng/mL', '2025-08-25', NOW(), NOW()),
('P2508271105', 'Blood Work', 'Lipid Panel', 'routine', 'scheduled', 'Monitoring cholesterol', 'Dr. Emily Rodriguez', '2025-08-27', '2025-08-28', NULL, NULL, NOW(), NOW());

-- Add therapies for patient CHUCK
INSERT INTO therapies (patient_id, type, description, frequency, duration, prescribed_by, start_date, status, notes, created_at, updated_at) VALUES
('P2508271105', 'Physical Therapy', 'Cardiac rehabilitation exercises', 'Daily', '30 minutes', 'Dr. Emily Rodriguez', '2025-08-26', 'active', 'Progressive ambulation and strengthening', NOW(), NOW()),
('P2508271105', 'Respiratory Therapy', 'Incentive spirometry', 'Every 2 hours while awake', '10 breaths', 'Dr. Emily Rodriguez', '2025-08-25', 'active', 'Prevent pneumonia', NOW(), NOW());

-- Add notes for patient CHUCK
INSERT INTO patient_notes (patient_id, content, note_type, author_id, author_name, author_role, created_at, updated_at) VALUES
('P2508271105', 'Patient admitted with chest pain. Initial workup negative for acute MI. Started on standard cardiac medications.', 'admission', 'DOC0001', 'Dr. Emily Rodriguez', 'Doctor', '2025-08-25 08:30:00', '2025-08-25 08:30:00'),
('P2508271105', 'Patient stable overnight. No complaints of chest pain. Vitals stable. Plan to continue current medications and start cardiac rehab.', 'progress', 'NURSE001', 'Maria Garcia', 'Nurse', '2025-08-26 06:00:00', '2025-08-26 06:00:00'),
('P2508271105', 'Physical therapy initiated. Patient tolerated well. Ambulating without assistance. Good compliance with incentive spirometry.', 'therapy', 'PHYS001', 'Kevin Park', 'Physical Therapist', '2025-08-26 14:00:00', '2025-08-26 14:00:00'),
('P2508271105', 'Reviewing discharge planning. Patient education provided on medications and lifestyle modifications. Family involved in care plan.', 'discharge_planning', 'DOC0001', 'Dr. Emily Rodriguez', 'Doctor', '2025-08-27 10:00:00', '2025-08-27 10:00:00');

-- Add case sheet entries for patient CHUCK
INSERT INTO case_sheet_entries (patient_id, entry_type, content, author_id, author_name, author_role, vitals_snapshot, created_at, updated_at) VALUES
('P2508271105', 'assessment', 'Patient presents with atypical chest pain. EKG shows normal sinus rhythm. No signs of acute coronary syndrome.', 'DOC0001', 'Dr. Emily Rodriguez', 'Doctor', '{"heartRate": 78, "bloodPressure": "128/82", "temperature": 98.4, "oxygenSat": 97}', '2025-08-25 08:45:00', '2025-08-25 08:45:00'),
('P2508271105', 'plan', 'Continue cardiac monitoring. Serial cardiac enzymes. Start dual antiplatelet therapy. Cardiology consult if symptoms persist.', 'DOC0001', 'Dr. Emily Rodriguez', 'Doctor', '{"heartRate": 76, "bloodPressure": "125/80", "temperature": 98.2, "oxygenSat": 98}', '2025-08-25 09:00:00', '2025-08-25 09:00:00'),
('P2508271105', 'progress', 'Patient reports feeling much better. No chest pain in past 24 hours. Appetite returning. Sleeping well.', 'NURSE001', 'Maria Garcia', 'Nurse', '{"heartRate": 72, "bloodPressure": "122/78", "temperature": 98.6, "oxygenSat": 99}', '2025-08-26 12:00:00', '2025-08-26 12:00:00'),
('P2508271105', 'medication_change', 'Added Simvastatin 20mg daily for cholesterol management per lipid panel results from yesterday.', 'DOC0001', 'Dr. Emily Rodriguez', 'Doctor', '{"heartRate": 68, "bloodPressure": "118/75", "temperature": 98.4, "oxygenSat": 98}', '2025-08-27 09:30:00', '2025-08-27 09:30:00');

-- Add some simulated vital readings to TimescaleDB (if the table exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'vital_readings_timeseries') THEN
        -- Insert sample vital readings for the past few hours
        INSERT INTO vital_readings_timeseries (patient_id, device_id, vital_type, value, unit, timestamp, quality, created_at) VALUES
        ('P2508271105', 'WATCH001', 'heart_rate', 72, 'bpm', NOW() - INTERVAL '30 minutes', 'good', NOW()),
        ('P2508271105', 'WATCH001', 'heart_rate', 75, 'bpm', NOW() - INTERVAL '25 minutes', 'good', NOW()),
        ('P2508271105', 'WATCH001', 'heart_rate', 68, 'bpm', NOW() - INTERVAL '20 minutes', 'good', NOW()),
        ('P2508271105', 'WATCH001', 'heart_rate', 70, 'bpm', NOW() - INTERVAL '15 minutes', 'good', NOW()),
        ('P2508271105', 'WATCH001', 'heart_rate', 73, 'bpm', NOW() - INTERVAL '10 minutes', 'good', NOW()),
        ('P2508271105', 'WATCH001', 'heart_rate', 71, 'bpm', NOW() - INTERVAL '5 minutes', 'good', NOW()),
        
        ('P2508271105', 'BP_CUFF001', 'blood_pressure_systolic', 118, 'mmHg', NOW() - INTERVAL '30 minutes', 'good', NOW()),
        ('P2508271105', 'BP_CUFF001', 'blood_pressure_diastolic', 75, 'mmHg', NOW() - INTERVAL '30 minutes', 'good', NOW()),
        ('P2508271105', 'BP_CUFF001', 'blood_pressure_systolic', 122, 'mmHg', NOW() - INTERVAL '15 minutes', 'good', NOW()),
        ('P2508271105', 'BP_CUFF001', 'blood_pressure_diastolic', 78, 'mmHg', NOW() - INTERVAL '15 minutes', 'good', NOW()),
        
        ('P2508271105', 'TEMP001', 'temperature', 98.4, '°F', NOW() - INTERVAL '60 minutes', 'good', NOW()),
        ('P2508271105', 'TEMP001', 'temperature', 98.6, '°F', NOW() - INTERVAL '30 minutes', 'good', NOW()),
        
        ('P2508271105', 'PULSE_OX001', 'oxygen_saturation', 98, '%', NOW() - INTERVAL '45 minutes', 'good', NOW()),
        ('P2508271105', 'PULSE_OX001', 'oxygen_saturation', 99, '%', NOW() - INTERVAL '25 minutes', 'good', NOW()),
        ('P2508271105', 'PULSE_OX001', 'oxygen_saturation', 97, '%', NOW() - INTERVAL '10 minutes', 'good', NOW());
    END IF;
END $$;

COMMIT;