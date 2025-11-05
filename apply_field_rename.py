"""
Apply field rename fixes to align frontend with backend
Run this script to fix the data visibility issue
"""
import os
import re

# Change to project root
os.chdir(r'C:\Users\Srika\OneDrive\Desktop\hospital-management-system\hospital-display-app\src')

print("="*70)
print("APPLYING FIELD RENAME FIX - Frontend to match Backend/ESP32")
print("="*70)

# Files to modify
files_to_modify = {
    'types/PatientTypes.ts': [
        ('systolicPressure: number; // Always integer - systolic pressure in mmHg',
         'bloodPressureSystolic: number; // mmHg (backend field name)'),
        ('diastolicPressure: number; // Always integer - diastolic pressure in mmHg',
         'bloodPressureDiastolic: number; // mmHg (backend field name)'),
        ('bioelectricalImpedance: number; // Ohms - bioelectrical impedance',
         'bioimpedance: number; // Ohms (backend field name)'),
        ('tremorIntensity: number; // 0-10 scale tremor intensity',
         'tremor: number; // 0-10 scale (backend field name)'),
        ("fallRisk: 'low' | 'medium' | 'high'; // Fall risk assessment",
         "imuFallRisk: number; // 0-10 scale from ESP32 IMU (backend field name)\n    fallRisk: 'low' | 'medium' | 'high'; // Calculated from imuFallRisk"),
        # vitalhistory interface
        ('systolicPressure: number; // systolic pressure in mmHg',
         'bloodPressureSystolic: number; // mmHg (backend name)'),
        ('diastolicPressure: number; // diastolic pressure in mmHg',
         'bloodPressureDiastolic: number; // mmHg (backend name)'),
        ('bioelectricalImpedance: number;',
         'bioimpedance: number; // Ohms (backend name)'),
        ('tremorIntensity: number;',
         'tremor: number; // 0-10 scale (backend name)'),
        # vitaltype alias
        ("'systolicPressure'", "'bloodPressureSystolic'"),
        ("'diastolicPressure'", "'bloodPressureDiastolic'"),
        ("'bioelectricalImpedance'", "'bioimpedance'"),
        ("'tremorIntensity'", "'tremor'"),
    ],
    'utils/transformers/VitalTransformer.ts': [
        ('vitals.systolicPressure', 'vitals.bloodPressureSystolic'),
        ('vitals.diastolicPressure', 'vitals.bloodPressureDiastolic'),
        ('systolicPressure:', 'bloodPressureSystolic:'),
        ('diastolicPressure:', 'bloodPressureDiastolic:'),
        ('bioelectricalImpedance:', 'bioimpedance:'),
        ('tremorIntensity:', 'tremor:'),
        ("'bioelectricalImpedance'", "'bioimpedance'"),
        ("'tremorIntensity'", "'tremor'"),
        ("'systolicPressure'", "'bloodPressureSystolic'"),
        ("'diastolicPressure'", "'bloodPressureDiastolic'"),
        ('item.systolicPressure', 'item.bloodPressureSystolic'),
        ('item.diastolicPressure', 'item.bloodPressureDiastolic'),
        ('item.bioelectricalImpedance', 'item.bioimpedance'),
        ('item.tremorIntensity', 'item.tremor'),
        ('d.systolicPressure', 'd.bloodPressureSystolic'),
    ]
}

# Apply changes
for file_path, replacements in files_to_modify.items():
    print(f"\n[*] Processing {file_path}...")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        changes_made = 0

        for old, new in replacements:
            if old in content:
                content = content.replace(old, new)
                changes_made += 1

        if changes_made > 0:
            # Create backup
            backup_path = file_path + '.backup'
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)

            # Write updated content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"    ✅ Applied {changes_made} changes")
            print(f"    📄 Backup saved to {backup_path}")
        else:
            print(f"    ⚠️ No changes needed (already updated?)")

    except FileNotFoundError:
        print(f"    ❌ File not found: {file_path}")
    except Exception as e:
        print(f"    ❌ Error: {e}")

print("\n" + "="*70)
print("FIELD RENAME COMPLETE!")
print("="*70)
print("\nNext steps:")
print("1. Check that files were updated correctly")
print("2. The hot-reload should pick up changes automatically")
print("3. Check browser console - vitals should now display")
print("4. If you see TypeScript errors in other files, update them too")
print("\nBackups created with .backup extension")
print("="*70)
