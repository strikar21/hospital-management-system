"""
Check existing staff records to understand what we have
"""
import asyncio
import asyncpg
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from app.core.config import settings


async def check_staff():
    """Check existing staff records"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        print("=" * 60)
        print("EXISTING STAFF RECORDS")
        print("=" * 60)

        # Get all staff
        staff = await conn.fetch("""
            SELECT id, role, "firstName", "lastName", email
            FROM staff
            ORDER BY id
        """)

        print(f"\nTotal staff records: {len(staff)}\n")

        if staff:
            print("ID          | Role      | Name                   | Email")
            print("-" * 60)
            for s in staff:
                name = f"{s['firstName']} {s['lastName']}"
                print(f"{s['id']:<11} | {s['role']:<9} | {name:<22} | {s['email']}")
        else:
            print("No staff records found!")

        # Check if LAB001 and RAD001 exist
        print("\n" + "=" * 60)
        print("MISSING STAFF IDS")
        print("=" * 60)

        missing_ids = ['LAB001', 'RAD001']

        for staff_id in missing_ids:
            exists = await conn.fetchval("""
                SELECT EXISTS (SELECT 1 FROM staff WHERE id = $1)
            """, staff_id)

            if exists:
                print(f"\n{staff_id}: EXISTS")
            else:
                print(f"\n{staff_id}: MISSING")

                # Check for similar roles
                role = 'lab' if 'LAB' in staff_id else 'radiology' if 'RAD' in staff_id else None
                if role:
                    similar = await conn.fetch("""
                        SELECT id, role, "firstName", "lastName"
                        FROM staff
                        WHERE role ILIKE $1
                        LIMIT 3
                    """, f"%{role}%")

                    if similar:
                        print(f"  Similar staff with {role} role:")
                        for s in similar:
                            print(f"    - {s['id']}: {s['firstName']} {s['lastName']} ({s['role']})")
                    else:
                        print(f"  No similar staff with {role} role found")

        print("\n" + "=" * 60)

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(check_staff())
