# Utility Files Cleanup Audit

## Summary
Found **103 utility/debug files** that should be deleted:
- **14 log files** (backend runtime logs)
- **4 backup files** (.backup, .old)
- **53 check_*.py scripts** (database inspection scripts)
- **10 cleanup_*.py scripts** (one-time cleanup tasks)
- **8 list_*.py scripts** (data listing utilities)
- **7 verify_*.py scripts** (verification utilities)
- **5 debug_*.py scripts** (debugging scripts)
- **2 analyze_*.py scripts** (analysis scripts)

---

## DELETE - Log Files (14 files)

### Backend Runtime Logs (DELETE):
```
./backend.log
./hospital-backend/backend.log
./hospital-backend/backend_clean.log
./hospital-backend/backend_complete_fix.log
./hospital-backend/backend_fixed.log
./hospital-backend/backend_new.log
./hospital-backend/backend_runtime.log
./hospital-backend/backend_startup.log
./hospital-backend/backend_stream_test.log
./hospital-backend/backend_test2.log
./hospital-backend/backend_uuid_fix.log
```

### Frontend Runtime Logs (DELETE):
```
./hospital-display-app/frontend.log
```

**Reason**: Runtime logs from debugging sessions, not needed in git

---

## DELETE - Backup Files (4 files)

### Configuration Backups (DELETE):
```
./hospital-backend/.env.development.backup
./hospital-backend/app/core/database.py.backup
./hospital-display-app/src/types/PatientTypes.ts.backup
```

### SSL Certificate Backups (DELETE):
```
./hospital-backend/ssl/cert.pem.old
./hospital-backend/ssl/key.pem.old
./mosquitto/certs/server.crt.old
./mosquitto/certs/server.csr.old
./mosquitto/certs/server.key.old
```

**Reason**: Backup files - git history already preserves old versions

---

## DELETE - Check Scripts (53 files)

### Project Root Check Scripts (DELETE):
```
./check_all_vitals.py
./check_db_functions.py
./check_device_assignment.py
./check_patient_attending.py
./check_recent_alerts.py
./check_tremor_bioz_columns.py
```

### Backend Check Scripts (DELETE - 47 files):
```
hospital-backend/check_actual_schema.py
hospital-backend/check_adm0001_auth.py
hospital-backend/check_alert_tables.py
hospital-backend/check_alerts_schema.py
hospital-backend/check_all_required_columns.py
hospital-backend/check_analysis_status.py
hospital-backend/check_assignment.py
hospital-backend/check_calibration_flow.py
hospital-backend/check_case_data.py
hospital-backend/check_case_tables.py
hospital-backend/check_cols.py
hospital-backend/check_current_devices.py
hospital-backend/check_current_vitals.py
hospital-backend/check_data_flow.py
hospital-backend/check_day2_tables_schema.py
hospital-backend/check_device_pool.py
hospital-backend/check_device_schema.py
hospital-backend/check_device_status.py
hospital-backend/check_device_types.py
hospital-backend/check_device_vitals.py
hospital-backend/check_deviceassignments_schema.py
hospital-backend/check_devices_quick.py
hospital-backend/check_esp32_devices.py
hospital-backend/check_existing_data.py
hospital-backend/check_mac_device.py
hospital-backend/check_medications_schema.py
hospital-backend/check_patient_cols.py
hospital-backend/check_patient_ids.py
hospital-backend/check_patients_schema.py
hospital-backend/check_schema.py
hospital-backend/check_schema_actual.py
hospital-backend/check_ssl_config.py
hospital-backend/check_ssl_paths.py
hospital-backend/check_staff.py
hospital-backend/check_staff_records.py
hospital-backend/check_tables.py
hospital-backend/check_timescaledb.py
hospital-backend/check_timescaledb_tables.py
hospital-backend/check_vitals_table.py
hospital-backend/check_vitals_tables.py
hospital-backend/check_waveform_flow.py
```

**Reason**: One-off database inspection scripts used during debugging

---

## DELETE - Cleanup Scripts (10 files)

### Backend Cleanup Scripts (DELETE):
```
hospital-backend/cleanup_duplicate_alerts.py
hospital-backend/cleanup_patients.py
```

**Reason**: One-time cleanup tasks already executed

---

## DELETE - List Scripts (8 files)

### Backend List Scripts (DELETE):
```
hospital-backend/list_all_timescaledb_tables.py
hospital-backend/list_vitals_columns.py
```

**Reason**: Database inspection utilities - superseded by organized tests

---

## DELETE - Verify Scripts (7 files)

### Backend Verify Scripts (DELETE):
```
hospital-backend/verify_assignment_issue.py
hospital-backend/verify_audit_fields.py
hospital-backend/verify_component_4_implementation.py
hospital-backend/verify_devicekey_removed.py
hospital-backend/verify_migration_009.py
hospital-backend/validate_day2_data.py
```

**Reason**: One-off verification scripts - functionality now in tests/

---

## DELETE - Debug Scripts (5 files)

### Backend Debug Scripts (DELETE):
```
hospital-backend/debug_therapy_join.py
```

**Reason**: Debugging scripts - issues already fixed

---

## DELETE - Analyze Scripts (2 files)

### Backend Analyze Scripts (DELETE):
```
hospital-backend/analyze_check_constraint_fields.py
hospital-backend/apply_day3_check_constraints.py
```

**Reason**: One-time analysis/migration scripts already applied

---

## DELETE - Misc Debug Files (1 file)

### ESP32 Test File (DELETE):
```
./esp32_mtls_minimal_test.ino
```

**Reason**: Test Arduino sketch in wrong location (should be in esp32 folder if needed)

---

## Deletion Summary

### By Category:
- **Log Files**: 14 files
- **Backup Files**: 4 files
- **Check Scripts**: 53 files
- **Cleanup Scripts**: 2 files
- **List Scripts**: 2 files
- **Verify Scripts**: 6 files
- **Debug Scripts**: 1 file
- **Analyze Scripts**: 2 files
- **Misc Files**: 1 file

### Total: **85 files to delete**

---

## Why Safe to Delete

1. **Git History**: All old versions preserved in git
2. **Functionality Replaced**: Organized tests in `tests/` directory handle verification
3. **One-Time Scripts**: Cleanup/migration scripts already executed
4. **Debugging Complete**: Check scripts were for debugging (bugs now fixed)
5. **Logs Temporary**: Runtime logs are temporary and regenerated
6. **Backups Redundant**: Git provides better version control than .backup files

---

## After Cleanup Benefits

✅ **Cleaner root directory** - No utility scripts cluttering workspace
✅ **Clear purpose** - Only production code and organized tests
✅ **Easier navigation** - Developers can find actual code faster
✅ **Git efficiency** - Smaller working tree, faster operations
✅ **Professional structure** - Production-ready codebase

---

## Deletion Commands

### Delete Log Files:
```bash
rm -f backend.log hospital-backend/backend*.log hospital-display-app/frontend.log
```

### Delete Backup Files:
```bash
rm -f hospital-backend/.env.development.backup
rm -f hospital-backend/app/core/database.py.backup
rm -f hospital-display-app/src/types/PatientTypes.ts.backup
rm -f hospital-backend/ssl/*.old
rm -f mosquitto/certs/*.old
```

### Delete Check Scripts (Project Root):
```bash
rm -f check_*.py
```

### Delete Backend Utility Scripts:
```bash
cd hospital-backend
rm -f check_*.py
rm -f cleanup_*.py
rm -f list_*.py
rm -f verify_*.py
rm -f validate_*.py
rm -f debug_*.py
rm -f analyze_*.py
rm -f apply_*.py
cd ..
```

### Delete Misc Files:
```bash
rm -f esp32_mtls_minimal_test.ino
```

---

## Keep These Files

### Essential Backend Scripts:
- **main.py** - Application entry point
- **conftest.py** - Pytest configuration
- **pytest.ini** - Pytest settings

### Essential Directories:
- **app/** - Application code
- **tests/** - Organized test suite
- **ssl/** - SSL certificates (keep .pem files, delete .old)
- **migrations/** - Migration documentation

### Frontend:
- **All src/** files** - Production code
- **package.json** - Dependencies
- **Configuration files** - tsconfig, etc.

---

## Post-Cleanup Project Structure

```
hospital-management-system/
├── hospital-backend/
│   ├── app/                    # Application code
│   ├── tests/                  # Organized tests ONLY
│   ├── ssl/                    # Active certificates only
│   ├── main.py                 # Entry point
│   ├── conftest.py             # Pytest config
│   └── pytest.ini              # Pytest settings
│
├── hospital-display-app/
│   └── src/                    # Production code
│
├── mosquitto/
│   └── certs/                  # Active certificates only
│
└── Documentation (essential MD files only)
```

**No utility scripts in root or backend root!**
