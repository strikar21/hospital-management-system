import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect("postgresql://hospital_user:hospital123@localhost:5432/hospitaldb")
    result = await conn.fetch("SELECT * FROM deviceassignments WHERE \"deviceId\" = $1 AND status = $2", "fit-00001", "active")
    for row in result:
        deviceId = row["deviceId"]
        patientId = row["patientId"]
        status = row["status"]
        print(f"Device: {deviceId}, Patient: {patientId}, Status: {status}")
    if len(result) == 0:
        print("NO ACTIVE ASSIGNMENT FOUND for fit-00001")
    await conn.close()

asyncio.run(check())
