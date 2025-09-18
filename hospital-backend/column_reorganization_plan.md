# Column Reorganization Plan

## Current Problems
- Columns added/dropped randomly, creating messy order
- firstname/lastname scattered at end instead of beginning
- patientid in middle of tables instead of logical position
- Demographics mixed with system fields

## Target Column Order

### 1. PATIENTS Table (22 columns)
**Current messy order:** id, gender, emergencycontactname, emergencycontactphone, bloodtype, allergies, medicalhistory, admissiondate, dischargedate, roomnumber, bednumber, assigneddeviceid, attendingphysician, nurseincharge, status, createdat, updatedat, firstname, lastname, dateofbirth, phonenumber, recommendedfrom

**Target logical order:**
1. **Identity** (5): id, firstname, lastname, dateofbirth, gender
2. **Contact** (3): phonenumber, emergencycontactname, emergencycontactphone  
3. **Medical** (3): bloodtype, allergies, medicalhistory
4. **Admission** (3): admissiondate, dischargedate, status
5. **Location** (3): roomnumber, bednumber, assigneddeviceid
6. **Staff** (2): attendingphysician, nurseincharge
7. **System** (3): createdat, updatedat, recommendedfrom

### 2. MEDICATIONS Table (12 columns)
**Current order:** id, name, dosage, frequency, route, status, duration, patientid, startdate, prescribedby, createdat, updatedat

**Target logical order:**
1. **Identity** (2): id, patientid
2. **Medication** (6): name, dosage, frequency, route, duration, status
3. **Timeline** (1): startdate
4. **Staff** (1): prescribedby
5. **System** (2): createdat, updatedat

### 3. THERAPY Table (12 columns) 
**Current order:** id, type, description, frequency, duration, status, notes, patientid, startdate, performedby, createdat, updatedat

**Target logical order:**
1. **Identity** (2): id, patientid
2. **Therapy** (5): type, description, frequency, duration, status
3. **Timeline** (1): startdate
4. **Staff** (1): performedby
5. **Additional** (1): notes
6. **System** (2): createdat, updatedat

### 4. INVESTIGATIONS Table (13 columns)
**Current order:** id, type, name, priority, status, results, notes, patientid, scheduledat, completedat, performedby, createdat, updatedat

**Target logical order:**
1. **Identity** (2): id, patientid
2. **Investigation** (4): type, name, priority, status
3. **Timeline** (2): scheduledat, completedat
4. **Staff** (1): performedby
5. **Results** (2): results, notes
6. **System** (2): createdat, updatedat

### 5. Other Patient-Specific Tables

**CASESHEETENTRIES** - needs patientid moved to position 2
**DEVICEASSIGNMENTS** - needs patientid moved to position 2  
**PATIENTNOTES** - needs patientid moved to position 2

## Implementation Strategy

**Method:** Recreate tables with proper structure
1. Create new table with correct column order
2. Copy data from old table
3. Drop old table
4. Rename new table

**Risk:** Data migration required, potential downtime
**Benefit:** Clean, logical column structure for development

## Tables to Fix Priority
1. **HIGH:** PATIENTS (most important, most messy)
2. **MEDIUM:** MEDICATIONS, THERAPY, INVESTIGATIONS (patient medical records)  
3. **LOW:** CASESHEETENTRIES, DEVICEASSIGNMENTS, PATIENTNOTES (simple fixes)

## Files to Create
1. `reorganize_patients_table.py` - Fix patients table structure
2. `reorganize_medical_tables.py` - Fix medications/therapy/investigations
3. `reorganize_other_tables.py` - Fix remaining patient-specific tables
4. `verify_reorganization.py` - Verify data integrity after changes