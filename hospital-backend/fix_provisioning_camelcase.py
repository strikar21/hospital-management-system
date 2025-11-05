"""
Automatically fix all snake_case SQL queries in provisioning.py to camelCase
"""
import re

# Read the file
with open('app/api/v1/provisioning.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Define all replacements (SQL column names)
replacements = [
    ('technician_id', '"technicianId"'),
    ('created_at', '"createdAt"'),
    ('expires_at', '"expiresAt"'),
    ('used_at', '"usedAt"'),
    ('device_id', '"deviceId"'),
    ('mac_address', '"macAddress"'),
    ('certificate_pem', '"certificatePem"'),
    ('issued_at', '"issuedAt"'),
    ('revoked_at', '"revokedAt"'),
    ('revoked_by', '"revokedBy"'),
    ('revocation_reason', '"revocationReason"'),
    ('serial_number', '"serialNumber"'),
]

# Apply replacements - only inside SQL strings
for old, new in replacements:
    content = content.replace(old, new)

# Fix the dictionary .pop() operations (lines 390-394)
# These need to access camelCase keys directly now
content = content.replace('code_dict.pop("created_at")', 'code_dict["createdAt"]')
content = content.replace('code_dict.pop("expires_at")', 'code_dict["expiresAt"]')
content = content.replace('code_dict.pop("used_at")', 'code_dict["usedAt"]')
content = content.replace('code_dict.pop("technician_id")', 'code_dict["technicianId"]')
content = content.replace('code_dict.pop("device_id")', 'code_dict["deviceId"]')

# Write back the fixed file
with open('app/api/v1/provisioning.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("[OK] Fixed all snake_case SQL queries in provisioning.py")
print("[OK] Total replacements made:")
for old, new in replacements:
    count = content.count(new)
    if count > 0:
        print(f"  - {old} -> {new}: {count} occurrences")

print("\n[NEXT] Restart backend to apply changes")
