"""
Check authentication fields for adm0001 user
"""
import asyncio
import asyncpg

async def check_admin():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        database='hospitaldb',
        user='hospital_user',
        password='hospital123'
    )

    try:
        print('\n[Checking ADM0001 authentication fields]')

        # Check ADM0001 specifically
        staff = await conn.fetchrow(
            'SELECT id, "firstName", "lastName", role, pin, password, "nfcCardId", "isActive" FROM staff WHERE id = $1',
            'ADM0001'
        )

        if staff:
            print(f"  Staff ID: {staff['id']}")
            print(f"  Name: {staff['firstName']} {staff['lastName']}")
            print(f"  Role: {staff['role']}")
            print(f"  Active: {staff['isActive']}")
            print(f"  PIN: {'SET' if staff['pin'] else 'NOT SET'}")
            print(f"  Password: {'SET' if staff['password'] else 'NOT SET'}")
            print(f"  NFC Card: {'SET' if staff['nfcCardId'] else 'NOT SET'}")

            # Show what auth type backend would return
            has_pin = bool(staff['pin'])
            has_password = bool(staff['password'])

            print(f"\n[Backend /auth/check-type response]")
            print(f"  hasPin: {has_pin}")
            print(f"  hasPassword: {has_password}")

            print(f"\n[Frontend HybridLogin.tsx logic for ADM prefix]")
            if has_password:
                print(f"  Would show: PASSWORD login (preferred)")
            elif has_pin:
                print(f"  Would show: PIN login (fallback)")
            else:
                print(f"  Would show: NO AUTH CONFIGURED!")
        else:
            print('  ADM0001 not found in database')

        # Check all admin users
        print('\n[All Administrator accounts]')
        admins = await conn.fetch(
            'SELECT id, "firstName", "lastName", pin, password FROM staff WHERE role = $1',
            'Administrator'
        )

        for admin in admins:
            pin_status = 'PIN' if admin['pin'] else 'NO-PIN'
            pwd_status = 'PWD' if admin['password'] else 'NO-PWD'
            print(f"  {admin['id']}: {admin['firstName']} {admin['lastName']} - {pin_status}, {pwd_status}")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_admin())
