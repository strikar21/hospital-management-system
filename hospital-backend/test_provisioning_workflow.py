"""
Test Complete Provisioning Workflow
Tests the entire certificate-based provisioning flow
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
import os
import secrets
import string

async def test_provisioning_workflow():
    print('[TEST] Testing Complete Provisioning Workflow...')
    print('')

    # Import dependencies
    from app.core.database import getDbConnection
    from app.services.certificate_service import CertificateService

    # Initialize certificate service
    ca_cert = os.path.join('..', 'mosquitto', 'certs', 'hospital_ca.crt')
    ca_key = os.path.join('..', 'mosquitto', 'certs', 'hospital_ca.key')
    cert_service = CertificateService(ca_cert, ca_key)
    print('[OK] Certificate service initialized')

    # Test 1: Get a technician user ID
    async with getDbConnection() as conn:
        technician = await conn.fetchrow(
            """SELECT id, "firstName", "lastName", role FROM staff
               WHERE role IN ('Administrator', 'Technician')
               AND "isActive" = true
               LIMIT 1"""
        )
        if not technician:
            print('[ERR] No active technician found')
            sys.exit(1)
        full_name = f'{technician["firstName"]} {technician["lastName"]}'
        print(f'[OK] Using technician: {full_name} (Role: {technician["role"]})')

    # Test 2: Generate provisioning code (simulating API endpoint logic)
    code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    async with getDbConnection() as conn:
        await conn.execute(
            """INSERT INTO provisioning_codes
               (code, technician_id, expires_at, used)
               VALUES ($1, $2, $3, false)""",
            code, technician['id'], expires_at
        )
    print(f'[OK] Generated provisioning code: {code}')
    print(f'     Expires at: {expires_at} UTC')

    # Test 3: Verify code exists
    async with getDbConnection() as conn:
        stored_code = await conn.fetchrow(
            'SELECT * FROM provisioning_codes WHERE code = $1',
            code
        )
        if stored_code:
            print(f'[OK] Code stored in database (expires in 10 minutes)')
        else:
            print('[ERR] Code not found in database')
            sys.exit(1)

    # Test 4: Provision device (simulating API endpoint logic)
    device_id = 'ESP32-WATCH-TEST-002'
    mac_address = 'BB:BB:CC:DD:EE:FF'

    # Check if code is valid (not used, not expired)
    async with getDbConnection() as conn:
        code_check = await conn.fetchrow(
            """SELECT * FROM provisioning_codes
               WHERE code = $1
               AND used = false
               AND expires_at > NOW()""",
            code
        )
        if not code_check:
            print('[ERR] Code invalid, used, or expired')
            sys.exit(1)
        print('[OK] Code is valid and unused')

    # Generate certificate
    cert_pem, key_pem = cert_service.generate_device_certificate(device_id, mac_address)
    print(f'[OK] Certificate generated for {device_id}')
    print(f'     Certificate: {len(cert_pem)} bytes')
    print(f'     Private key: {len(key_pem)} bytes')

    # Store certificate metadata (without foreign key constraint for testing)
    async with getDbConnection() as conn:
        await conn.execute(
            """INSERT INTO device_certificates
               (device_id, certificate_pem, expires_at, mac_address, serial_number)
               VALUES ($1, $2, $3, $4, $5)
               ON CONFLICT (device_id) DO UPDATE
               SET certificate_pem = EXCLUDED.certificate_pem,
                   expires_at = EXCLUDED.expires_at,
                   issued_at = NOW(),
                   revoked = false""",
            device_id,
            cert_pem,
            datetime.now(timezone.utc) + timedelta(days=365),
            mac_address,
            f'SN-{mac_address}'
        )

    print('[OK] Certificate metadata stored in database')

    # Mark code as used
    async with getDbConnection() as conn:
        await conn.execute(
            """UPDATE provisioning_codes
               SET used = true, used_at = NOW(), device_id = $1
               WHERE code = $2""",
            device_id, code
        )
    print('[OK] Provisioning code marked as used')

    # Test 5: Verify certificate was stored
    async with getDbConnection() as conn:
        stored_cert = await conn.fetchrow(
            'SELECT * FROM device_certificates WHERE device_id = $1',
            device_id
        )
        if stored_cert:
            print('[OK] Certificate retrieved from database')
            print(f'     Issued at: {stored_cert["issued_at"]}')
            print(f'     Expires at: {stored_cert["expires_at"]}')
            print(f'     Revoked: {stored_cert["revoked"]}')
        else:
            print('[ERR] Certificate not found in database')
            sys.exit(1)

    # Test 6: Verify certificate can be validated
    is_valid = cert_service.verify_certificate(cert_pem)
    if is_valid:
        print('[OK] Certificate signature verified (signed by Hospital CA)')
    else:
        print('[ERR] Certificate verification failed')
        sys.exit(1)

    # Test 7: Test code reuse prevention
    async with getDbConnection() as conn:
        reuse_check = await conn.fetchrow(
            """SELECT * FROM provisioning_codes
               WHERE code = $1
               AND used = false
               AND expires_at > NOW()""",
            code
        )
        if reuse_check:
            print('[ERR] Code can be reused (security issue!)')
            sys.exit(1)
        else:
            print('[OK] Code cannot be reused (marked as used)')

    # Test 8: Test certificate revocation
    async with getDbConnection() as conn:
        await conn.execute(
            """UPDATE device_certificates
               SET revoked = true,
                   revoked_at = NOW(),
                   revocation_reason = 'Test revocation'
               WHERE device_id = $1""",
            device_id
        )
    print('[OK] Certificate revoked successfully')

    async with getDbConnection() as conn:
        revoked_cert = await conn.fetchrow(
            'SELECT * FROM device_certificates WHERE device_id = $1',
            device_id
        )
        if revoked_cert['revoked']:
            print(f'[OK] Certificate revocation verified')
            print(f'     Revoked at: {revoked_cert["revoked_at"]}')
            print(f'     Reason: {revoked_cert["revocation_reason"]}')

    print('')
    print('[SUCCESS] Complete Provisioning Workflow Test Passed!')
    print('')
    print('Workflow Tested:')
    print('1. Generate provisioning code -> WORKING')
    print('2. Store code in database -> WORKING')
    print('3. Validate code (unused, not expired) -> WORKING')
    print('4. Generate device certificate -> WORKING')
    print('5. Store certificate metadata -> WORKING')
    print('6. Mark code as used -> WORKING')
    print('7. Prevent code reuse -> WORKING')
    print('8. Revoke certificate -> WORKING')

if __name__ == '__main__':
    asyncio.run(test_provisioning_workflow())
