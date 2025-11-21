import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='hospital',
        password='hospital123',
        database='hospitaldb'
    )

    print("\n=== Database Status ===\n")

    tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")

    for table in tables:
        table_name = table['tablename']
        count = await conn.fetchval(f'SELECT COUNT(*) FROM "{table_name}"')
        print(f"  {table_name}: {count} rows")

    print("\n=== Staff Details ===\n")
    staff = await conn.fetch("SELECT id, role, nfcbadgeid, status FROM staff ORDER BY id")
    for s in staff:
        print(f"  {s['id']}: {s['role']} (NFC: {s['nfcbadgeid']}, Status: {s['status']})")

    print("\n=== FHIR Resources ===\n")
    resources = await conn.fetch("SELECT resourcetype, resourceid, status FROM fhirresources ORDER BY resourcetype, resourceid")
    for r in resources:
        print(f"  {r['resourcetype']}/{r['resourceid']} (Status: {r['status']})")

    await conn.close()

asyncio.run(main())
