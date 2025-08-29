-- Test user data for hospital system
-- Insert test staff members with various roles

INSERT INTO staff (staff_id, name, role, department, nfc_id, password_hash, pin_hash, created_at, updated_at) VALUES
-- Administrators (password-based login)
('ADMIN001', 'Dr. Sarah Johnson', 'Administrator', 'Administration', 'NFC_ADMIN_001', '$2b$12$LQv3c5c5c5c5c5c5c5c5c5O6hDhO6hDhO6hDhO6hDhO6hDhO6hDhO6', NULL, NOW(), NOW()),
('ADMIN002', 'Michael Chen', 'Admin', 'IT', 'NFC_ADMIN_002', '$2b$12$LQv3c5c5c5c5c5c5c5c5c5O6hDhO6hDhO6hDhO6hDhO6hDhO6hDhO6', NULL, NOW(), NOW()),

-- Provisioners (password-based login)  
('PROV001', 'Jennifer Martinez', 'Provisioner', 'Equipment', 'NFC_PROV_001', '$2b$12$LQv3c5c5c5c5c5c5c5c5c5O6hDhO6hDhO6hDhO6hDhO6hDhO6hDhO6', NULL, NOW(), NOW()),
('PROV002', 'David Wilson', 'Provisioner', 'IT Support', 'NFC_PROV_002', '$2b$12$LQv3c5c5c5c5c5c5c5c5c5O6hDhO6hDhO6hDhO6hDhO6hDhO6hDhO6', NULL, NOW(), NOW()),

-- Doctors (PIN-based login)
('DOC001', 'Dr. Emily Rodriguez', 'Doctor', 'Cardiology', 'NFC_DOC_001', NULL, '$2b$12$1234567890123456789012.ABCDEFGHIJKLMNOPQRSTUVWXYZ123456', NOW(), NOW()),
('DOC002', 'Dr. James Thompson', 'Doctor', 'Emergency', 'NFC_DOC_002', NULL, '$2b$12$1234567890123456789012.ABCDEFGHIJKLMNOPQRSTUVWXYZ123457', NOW(), NOW()),
('DOC003', 'Dr. Lisa Wang', 'Doctor', 'Pediatrics', 'NFC_DOC_003', NULL, '$2b$12$1234567890123456789012.ABCDEFGHIJKLMNOPQRSTUVWXYZ123458', NOW(), NOW()),

-- Nurses (PIN-based login)
('NURSE001', 'Maria Garcia', 'Nurse', 'ICU', 'NFC_NURSE_001', NULL, '$2b$12$1234567890123456789012.ABCDEFGHIJKLMNOPQRSTUVWXYZ123459', NOW(), NOW()),
('NURSE002', 'Robert Brown', 'Nurse', 'Emergency', 'NFC_NURSE_002', NULL, '$2b$12$1234567890123456789012.ABCDEFGHIJKLMNOPQRSTUVWXYZ123460', NOW(), NOW()),
('NURSE003', 'Amanda Davis', 'Nurse', 'Pediatrics', 'NFC_NURSE_003', NULL, '$2b$12$1234567890123456789012.ABCDEFGHIJKLMNOPQRSTUVWXYZ123461', NOW(), NOW()),

-- Technicians (PIN-based login)
('TECH001', 'Kevin Park', 'Technician', 'Radiology', 'NFC_TECH_001', NULL, '$2b$12$1234567890123456789012.ABCDEFGHIJKLMNOPQRSTUVWXYZ123462', NOW(), NOW()),
('TECH002', 'Susan Lee', 'Technician', 'Laboratory', 'NFC_TECH_002', NULL, '$2b$12$1234567890123456789012.ABCDEFGHIJKLMNOPQRSTUVWXYZ123463', NOW(), NOW());

-- Test patients for development
INSERT INTO patients (patient_id, name, age, gender, bed_number, ward, room, department, assigned_doctor, diagnosis, admission_date, status, created_at, updated_at) VALUES
('PAT001', 'John Smith', 45, 'M', 'A101', 'ICU', 'Room 101', 'Cardiology', 'Dr. Emily Rodriguez', 'Acute Myocardial Infarction', '2025-08-25', 'stable', NOW(), NOW()),
('PAT002', 'Mary Johnson', 62, 'F', 'B205', 'General', 'Room 205', 'Pediatrics', 'Dr. Lisa Wang', 'Pneumonia', '2025-08-26', 'stable', NOW(), NOW()),
('PAT003', 'Carlos Hernandez', 38, 'M', 'C301', 'Emergency', 'Room 301', 'Emergency', 'Dr. James Thompson', 'Multiple Trauma', '2025-08-27', 'critical', NOW(), NOW()),
('PAT004', 'Sarah Wilson', 29, 'F', 'A102', 'ICU', 'Room 102', 'Cardiology', 'Dr. Emily Rodriguez', 'Post-Operative Care', '2025-08-26', 'stable', NOW(), NOW());

-- Test login credentials (for reference):
-- Administrators/Provisioners: password = "hospital123"
-- Doctors/Nurses/Technicians: PIN = "1234", "2468", "1357", "9876", "5678", "2469", "1470", "3691" respectively