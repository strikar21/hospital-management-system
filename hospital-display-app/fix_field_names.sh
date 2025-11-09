#!/bin/bash
# Script to rename sensor field names across frontend

# Find and replace bioelectricalImpedance → bioimpedance
find src -type f \( -name "*.ts" -o -name "*.tsx" \) -exec sed -i 's/bioelectricalImpedance/bioimpedance/g' {} +

# Find and replace tremorIntensity → tremor
find src -type f \( -name "*.ts" -o -name "*.tsx" \) -exec sed -i 's/tremorIntensity/tremor/g' {} +

# Find and replace fallRisk → imuFallRisk (in patient.vitals context only)
find src -type f \( -name "*.ts" -o -name "*.tsx" \) -exec sed -i 's/\.fallRisk/.imuFallRisk/g' {} +

echo "Field name replacements complete!"
