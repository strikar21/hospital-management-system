-- Multi-Level Discharge Workflow Schema
-- Creates proper discharge approval chain: Doctor -> Admin -> Nurse

-- Add discharge workflow columns to patients table
ALTER TABLE patients 
ADD COLUMN IF NOT EXISTS discharge_request_date TIMESTAMP,
ADD COLUMN IF NOT EXISTS discharge_requested_by VARCHAR(100),
ADD COLUMN IF NOT EXISTS discharge_reason TEXT,
ADD COLUMN IF NOT EXISTS discharge_notes TEXT,
ADD COLUMN IF NOT EXISTS admin_approval_date TIMESTAMP,
ADD COLUMN IF NOT EXISTS admin_approved_by VARCHAR(100),
ADD COLUMN IF NOT EXISTS admin_approval_notes TEXT,
ADD COLUMN IF NOT EXISTS final_discharge_date TIMESTAMP,
ADD COLUMN IF NOT EXISTS discharged_by VARCHAR(100),
ADD COLUMN IF NOT EXISTS discharge_summary_generated BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS discharge_status VARCHAR(50) DEFAULT 'active'; -- active, requested, admin_approved, discharged

-- Create discharge approvals tracking table
CREATE TABLE IF NOT EXISTS discharge_approvals (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(20) NOT NULL,
    approval_stage VARCHAR(20) NOT NULL, -- 'doctor_request', 'admin_approval', 'nurse_discharge'
    staff_id VARCHAR(100) NOT NULL,
    staff_role VARCHAR(50) NOT NULL,
    approval_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    status VARCHAR(20) DEFAULT 'pending', -- pending, approved, rejected
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

-- Create discharge summary table
CREATE TABLE IF NOT EXISTS discharge_summaries (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(20) NOT NULL,
    admission_date DATE,
    discharge_date DATE,
    length_of_stay INTEGER,
    primary_diagnosis TEXT,
    secondary_diagnoses TEXT[],
    procedures_performed TEXT[],
    medications_on_admission JSONB,
    medications_on_discharge JSONB,
    medications_to_continue JSONB,
    vital_signs_summary JSONB,
    lab_results_summary JSONB,
    therapy_sessions JSONB,
    follow_up_instructions TEXT,
    next_appointment_date DATE,
    next_appointment_with VARCHAR(100),
    discharge_condition VARCHAR(100),
    discharge_disposition VARCHAR(100), -- home, nursing_facility, rehabilitation, etc
    generated_by VARCHAR(100),
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_by VARCHAR(100),
    approved_at TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

-- Insert sample discharge workflow data
INSERT INTO discharge_approvals (patient_id, approval_stage, staff_id, staff_role, notes, status) VALUES
('P25082350', 'doctor_request', 'DOC001', 'Senior Consultant', 'Patient recovered well, ready for discharge', 'approved'),
('P25082350', 'admin_approval', 'ADM001', 'Hospital Administrator', 'Insurance cleared, discharge approved', 'approved');

COMMIT;