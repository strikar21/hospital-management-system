#!/bin/bash
# Script to apply field rename fixes
# Run this when frontend dev server is stopped

echo "==================================================================="
echo "APPLYING FIELD RENAME FIX - Frontend to match Backend"
echo "==================================================================="

cd hospital-display-app/src

echo ""
echo "[1/5] Updating PatientTypes.ts vitals interface..."
sed -i 's/systolicPressure: number; \/\/ Always integer - systolic pressure in mmHg/bloodPressureSystolic: number; \/\/ mmHg (backend field name)/g' types/PatientTypes.ts
sed -i 's/diastolicPressure: number; \/\/ Always integer - diastolic pressure in mmHg/bloodPressureDiastolic: number; \/\/ mmHg (backend field name)/g' types/PatientTypes.ts
sed -i 's/bioelectricalImpedance: number; \/\/ Ohms - bioelectrical impedance/bioimpedance: number; \/\/ Ohms (backend field name)/g' types/PatientTypes.ts
sed -i 's/tremorIntensity: number; \/\/ 0-10 scale tremor intensity/tremor: number; \/\/ 0-10 scale (backend field name)\n    imuFallRisk: number; \/\/ 0-10 scale from ESP32 IMU (backend field name)/g' types/PatientTypes.ts
sed -i 's/fallRisk: .low. | .medium. | .high.; \/\/ Fall risk assessment/fallRisk: '\''low'\'' | '\''medium'\'' | '\''high'\''; \/\/ Calculated from imuFallRisk/g' types/PatientTypes.ts

echo "[2/5] Updating PatientTypes.ts vitalhistory interface..."
sed -i 's/systolicPressure: number; \/\/ systolic pressure in mmHg/bloodPressureSystolic: number; \/\/ mmHg (backend name)/g' types/PatientTypes.ts
sed -i 's/diastolicPressure: number; \/\/ diastolic pressure in mmHg/bloodPressureDiastolic: number; \/\/ mmHg (backend name)/g' types/PatientTypes.ts
sed -i 's/bioelectricalImpedance: number;$/bioimpedance: number; \/\/ Ohms (backend name)/g' types/PatientTypes.ts
sed -i 's/tremorIntensity: number;$/tremor: number; \/\/ 0-10 scale (backend name)/g' types/PatientTypes.ts

echo "[3/5] Updating PatientTypes.ts vitaltype alias..."
sed -i "s/'systolicPressure'/'bloodPressureSystolic'/g" types/PatientTypes.ts
sed -i "s/'diastolicPressure'/'bloodPressureDiastolic'/g" types/PatientTypes.ts
sed -i "s/'bioelectricalImpedance'/'bioimpedance'/g" types/PatientTypes.ts
sed -i "s/'tremorIntensity'/'tremor'/g" types/PatientTypes.ts

echo "[4/5] Updating VitalTransformer.ts..."
# This is more complex - create a backup first
cp utils/transformers/VitalTransformer.ts utils/transformers/VitalTransformer.ts.backup

# Replace field names in transformVitals method
sed -i 's/vitals\.systolicPressure/vitals.bloodPressureSystolic/g' utils/transformers/VitalTransformer.ts
sed -i 's/vitals\.diastolicPressure/vitals.bloodPressureDiastolic/g' utils/transformers/VitalTransformer.ts
sed -i 's/systolicPressure:/bloodPressureSystolic:/g' utils/transformers/VitalTransformer.ts
sed -i 's/diastolicPressure:/bloodPressureDiastolic:/g' utils/transformers/VitalTransformer.ts
sed -i 's/bioelectricalImpedance:/bioimpedance:/g' utils/transformers/VitalTransformer.ts
sed -i 's/tremorIntensity:/tremor:/g' utils/transformers/VitalTransformer.ts
sed -i "s/'bioelectricalImpedance'/'bioimpedance'/g" utils/transformers/VitalTransformer.ts
sed -i "s/'tremorIntensity'/'tremor'/g" utils/transformers/VitalTransformer.ts
sed -i "s/'systolicPressure'/'bloodPressureSystolic'/g" utils/transformers/VitalTransformer.ts
sed -i "s/'diastolicPressure'/'bloodPressureDiastolic'/g" utils/transformers/VitalTransformer.ts

echo "[5/5] Finding React components that need updates..."
echo ""
echo "Files using old field names:"
grep -r "systolicPressure\|diastolicPressure\|bioelectricalImpedance\|tremorIntensity" --include="*.tsx" --include="*.ts" . | grep -v "node_modules" | grep -v ".backup"

echo ""
echo "==================================================================="
echo "FIELD RENAME COMPLETE!"
echo "==================================================================="
echo ""
echo "Next steps:"
echo "1. Review the changes"
echo "2. Run: npm run build"
echo "3. Fix any TypeScript errors in components"
echo "4. Test with live ESP32 data"
echo ""
echo "Backup created: utils/transformers/VitalTransformer.ts.backup"
echo "==================================================================="
